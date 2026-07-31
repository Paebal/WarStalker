# game/world.py
import pygame
import os
import math
from constants import COLOR_DARK_GRAY

class Camera:
    def __init__(self, width, height):
        self.x = 0
        self.y = 0
        self.width = width
        self.height = height

    def update(self, target, map_width, map_height):
        self.x = target.x - self.width // 2
        self.y = target.y - self.height // 2
        if self.x < 0:
            self.x = 0
        if self.y < 0:
            self.y = 0
        if self.x + self.width > map_width:
            self.x = map_width - self.width
        if self.y + self.height > map_height:
            self.y = map_height - self.height
        if map_width <= self.width:
            self.x = (map_width - self.width) // 2
        if map_height <= self.height:
            self.y = (map_height - self.height) // 2


class TileMap:
    def __init__(self, tile_dir, tile_size=256, scale=1.0):
        self.tile_dir = tile_dir
        self.tile_size = tile_size
        self.scale = scale
        self.cache = {}
        self.load_queue = []
        self.max_loads_per_frame = 3

    def get_tile(self, col, row, force=False):
        key = (col, row)
        if key in self.cache:
            return self.cache[key]
        if force:
            surface = self._load_tile(col, row)
            self.cache[key] = surface
            return surface
        else:
            if key not in self.load_queue and key not in self.cache:
                self.load_queue.append(key)
            return None

    def _load_tile(self, col, row):
        path = os.path.join(self.tile_dir, f"tile_{col}_{row}.png")
        try:
            surface = pygame.image.load(path).convert_alpha()
            if self.scale != 1.0:
                new_size = (int(surface.get_width() * self.scale),
                            int(surface.get_height() * self.scale))
                surface = pygame.transform.scale(surface, new_size)
            return surface
        except FileNotFoundError:
            return None

    def process_queue(self):
        loaded = 0
        while self.load_queue and loaded < self.max_loads_per_frame:
            col, row = self.load_queue.pop(0)
            if (col, row) not in self.cache:
                surface = self._load_tile(col, row)
                self.cache[(col, row)] = surface
            loaded += 1

    def draw(self, screen, camera):
        tile_size_scaled = int(self.tile_size * self.scale)
        start_col = int(camera.x // tile_size_scaled)
        end_col = int((camera.x + camera.width) // tile_size_scaled) + 1
        start_row = int(camera.y // tile_size_scaled)
        end_row = int((camera.y + camera.height) // tile_size_scaled) + 1

        visible_tiles = set()
        for col in range(start_col, end_col):
            for row in range(start_row, end_row):
                tile = self.get_tile(col, row, force=True)
                visible_tiles.add((col, row))
                if tile:
                    screen_x = col * tile_size_scaled - camera.x
                    screen_y = row * tile_size_scaled - camera.y
                    screen.blit(tile, (screen_x, screen_y))

        n = 1
        for col in range(start_col - n, end_col + n):
            for row in range(start_row - n, end_row + n):
                if (col, row) not in visible_tiles:
                    self.get_tile(col, row, force=False)


class World:
    def __init__(self, map_data, scale=1.0, chunk_size=500):
        self.scale = scale
        self.base_width = map_data.get("width", 3000) if map_data else 3000
        self.base_height = map_data.get("height", 3000) if map_data else 3000
        self.width = int(self.base_width * scale)
        self.height = int(self.base_height * scale)
        self.chunk_size = chunk_size
        self.chunks = {}  # (cx, cy) -> list of objects
        self.objects = []  # flat list for backward compatibility
        self.objects_data = map_data.get("objects") if map_data and map_data.get("objects") is not None else []
        self.tile_map = TileMap("assets/tiles", tile_size=256, scale=scale)
        self._load_objects()

    def _get_chunk_key(self, x, y):
        cx = int(x // self.chunk_size)
        cy = int(y // self.chunk_size)
        return (cx, cy)

    def _add_object_to_chunk(self, obj):
        key = self._get_chunk_key(obj["x"], obj["y"])
        if key not in self.chunks:
            self.chunks[key] = []
        self.chunks[key].append(obj)

    def _load_objects(self):
        if not self.objects_data:
            print("[WORLD] Нет объектов для загрузки")
            return
        print(f"[WORLD] Загрузка {len(self.objects_data)} объектов")
        for idx, obj in enumerate(self.objects_data):
            try:
                x = obj.get("x", 0)
                y = obj.get("y", 0)
                width = obj.get("width", 0)
                height = obj.get("height", 0)
                radius = obj.get("radius", 0)
                angle = obj.get("angle", 0)
                shape = obj.get("shape", "rect")
                # Масштабируем координаты и размеры
                sx = x * self.scale
                sy = y * self.scale
                sw = width * self.scale
                sh = height * self.scale
                sr = radius * self.scale
                rect = pygame.Rect(sx - sw/2, sy - sh/2, sw, sh)
                base = {
                    "type": obj["type"],
                    "x": sx,
                    "y": sy,
                    "width": sw,
                    "height": sh,
                    "color": pygame.Color(obj["color"]),
                    "rect": rect,
                    "angle": angle,
                    "shape": shape,
                }
                if obj["type"] == "tree":
                    base["radius"] = sr
                if shape == "triangle":
                    base["a"] = obj.get("a", width) * self.scale
                    base["b"] = obj.get("b", height) * self.scale
                    base["alpha"] = obj.get("alpha", 60)
                    base["beta"] = obj.get("beta", 60)
                    base["gamma"] = obj.get("gamma", 60)
                self.objects.append(base)
                self._add_object_to_chunk(base)
                if idx < 3:
                    print(f"[WORLD] Загружен объект {idx}: {base}")
            except (KeyError, ValueError) as e:
                print(f"[WORLD] Ошибка загрузки объекта {idx}: {e}")

    def _get_visible_chunks(self, camera):
        # Определяем, какие чанки видны в камере (с учётом масштаба)
        # Чанки хранятся в координатах без масштаба (исходные), но камера использует масштабированные координаты.
        # Преобразуем границы камеры в координаты чанков (делим на chunk_size)
        left = camera.x
        right = camera.x + camera.width
        top = camera.y
        bottom = camera.y + camera.height
        # Преобразуем в координаты без масштаба (делим на scale)
        left_unscaled = left / self.scale
        right_unscaled = right / self.scale
        top_unscaled = top / self.scale
        bottom_unscaled = bottom / self.scale
        # Определяем индексы чанков
        cx_start = int(left_unscaled // self.chunk_size)
        cx_end = int(right_unscaled // self.chunk_size) + 1
        cy_start = int(top_unscaled // self.chunk_size)
        cy_end = int(bottom_unscaled // self.chunk_size) + 1
        visible = []
        for cx in range(cx_start, cx_end):
            for cy in range(cy_start, cy_end):
                visible.append((cx, cy))
        return visible

    def draw(self, screen, camera):
        self.tile_map.draw(screen, camera)
        visible_chunks = self._get_visible_chunks(camera)
        # Отрисовываем объекты из видимых чанков
        for key in visible_chunks:
            if key in self.chunks:
                for obj in self.chunks[key]:
                    if obj["rect"].colliderect(pygame.Rect(camera.x, camera.y, camera.width, camera.height)):
                        screen_x = obj["x"] - camera.x
                        screen_y = obj["y"] - camera.y
                        color = obj["color"]
                        angle = obj.get("angle", 0)

                        if obj["type"] == "tree":
                            r = obj["radius"]
                            pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), int(r))
                            pygame.draw.rect(screen, (101,67,33), (screen_x-3, screen_y + r//2, 6, r//2))
                        elif obj["type"] == "building":
                            shape = obj.get("shape", "rect")
                            if shape == "triangle":
                                a = obj.get("a", obj["width"])
                                b = obj.get("b", obj["height"])
                                alpha = obj.get("alpha", 60)
                                alpha_rad = math.radians(alpha)
                                A = (0,0); B = (a,0); C = (b*math.cos(alpha_rad), b*math.sin(alpha_rad))
                                cx = (A[0]+B[0]+C[0])/3; cy = (A[1]+B[1]+C[1])/3
                                verts = [(A[0]-cx, A[1]-cy), (B[0]-cx, B[1]-cy), (C[0]-cx, C[1]-cy)]
                                rad_angle = math.radians(angle)
                                transformed = []
                                for vx, vy in verts:
                                    rx = vx * math.cos(rad_angle) - vy * math.sin(rad_angle)
                                    ry = vx * math.sin(rad_angle) + vy * math.cos(rad_angle)
                                    transformed.append((screen_x + rx, screen_y + ry))
                                pygame.draw.polygon(screen, color, transformed)
                            else:
                                w = obj["width"]
                                h = obj["height"]
                                if angle != 0:
                                    surf = pygame.Surface((w, h), pygame.SRCALPHA)
                                    surf.fill((0,0,0,0))
                                    pygame.draw.rect(surf, color, (0,0,w,h))
                                    rot_surf = pygame.transform.rotate(surf, angle)
                                    screen.blit(rot_surf, (screen_x - rot_surf.get_width()/2, screen_y - rot_surf.get_height()/2))
                                else:
                                    rect = pygame.Rect(screen_x - w/2, screen_y - h/2, w, h)
                                    pygame.draw.rect(screen, color, rect)

    def get_collision_rects(self, camera=None):
        # Возвращает прямоугольники объектов в видимых чанках (или все, если камера не задана)
        if camera is None:
            return [obj["rect"] for obj in self.objects if obj["type"] in ("building", "house")]
        visible_chunks = self._get_visible_chunks(camera)
        rects = []
        for key in visible_chunks:
            if key in self.chunks:
                for obj in self.chunks[key]:
                    if obj["type"] in ("building", "house"):
                        rects.append(obj["rect"])
        return rects

    def get_map_size(self):
        return self.width, self.height

    def check_collision(self, rect, ignore_objects=None, camera=None):
        if ignore_objects is None:
            ignore_objects = []
        check_rects = self.get_collision_rects(camera)
        for r in check_rects:
            if r.colliderect(rect):
                return True
        return False

    def reload(self, new_scale):
        self.scale = new_scale
        self.width = int(self.base_width * new_scale)
        self.height = int(self.base_height * new_scale)
        self.objects = []
        self.chunks = {}
        self.tile_map = TileMap("assets/tiles", tile_size=256, scale=new_scale)
        self._load_objects()
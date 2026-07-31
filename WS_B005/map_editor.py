# map_editor.py
import sys
import os
import traceback

# Перенаправление ошибок в файл для отладки
sys.stderr = open("editor_error.log", "w")

try:
    # Проверка пути
    print("Добавляем путь...")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("Импортируем модули...")
    import pygame
    import json
    import math
    import subprocess
    import time
    from pygame.locals import *
    from game.config_loader import ConfigLoader
    from game.world import World, Camera
    from constants import COLOR_WHITE, COLOR_BLACK, COLOR_GRAY, COLOR_RED, COLOR_GREEN, COLOR_BLUE
    print("Импорт успешен.")
except Exception as e:
    print("Ошибка импорта:", e)
    traceback.print_exc()
    sys.exit(1)

EDITOR_SETTINGS_FILE = "editor_settings.json"

def color_to_hex(color):
    if isinstance(color, pygame.Color):
        r, g, b = color.r, color.g, color.b
    else:
        r, g, b = color[0], color[1], color[2]
    return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))

EDITOR_WIDTH = 1280
EDITOR_HEIGHT = 720
USERMAPS_DIR = "data/maps/usermaps"
MIN_ZOOM = 0.01
MAX_ZOOM = 100.0
ZOOM_STEP = 1.1

PALETTE_COLORS = [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),(0,255,255),(255,128,0),(128,255,0),(0,128,255),(128,0,255),(255,128,128),(128,255,128),(128,128,255),(255,255,128),(128,128,128),(255,255,255)]

class EditorObject:
    def __init__(self, obj_type, x, y, params, color=(255,0,0), angle=0, z_index=0):
        self.type = obj_type
        self.x = x
        self.y = y
        self.color = color
        self.angle = angle
        self.z_index = z_index
        self.selected = False
        self.valid = True
        if obj_type == 'rect':
            self.width = params.get('width', 50)
            self.height = params.get('height', 50)
            self.valid = True
        elif obj_type == 'circle':
            self.radius = params.get('radius', 30)
            self.valid = True
        elif obj_type == 'triangle':
            self.a = params.get('a', 50)
            self.alpha = params.get('alpha', 60)
            self.beta = params.get('beta', 60)
            self.gamma = params.get('gamma', 60)
            self._update_from_angles()
            self._check_valid()

    def _update_from_angles(self):
        if not (0 < self.alpha < 180 and 0 < self.beta < 180 and 0 < self.gamma < 180):
            self.b = 0; self.c = 0; return
        if abs(self.alpha + self.beta + self.gamma - 180) > 0.001:
            self.b = 0; self.c = 0; return
        alpha_rad = math.radians(self.alpha)
        if math.sin(alpha_rad) == 0:
            self.b = 0; self.c = 0; return
        factor = self.a / math.sin(alpha_rad)
        self.b = factor * math.sin(math.radians(self.beta))
        self.c = factor * math.sin(math.radians(self.gamma))
        if self.b <= 0 or self.c <= 0:
            self.b = 0; self.c = 0

    def _check_valid(self):
        if self.type != 'triangle':
            self.valid = True; return
        if self.a <= 0 or self.b <= 0 or self.c <= 0:
            self.valid = False; return
        if not (0 < self.alpha < 180 and 0 < self.beta < 180 and 0 < self.gamma < 180):
            self.valid = False; return
        if abs(self.alpha + self.beta + self.gamma - 180) > 0.001:
            self.valid = False; return
        self.valid = True

    def set_alpha(self, new_alpha):
        if not (0 < new_alpha < 180): return False
        self.alpha = new_alpha
        self._update_from_angles(); self._check_valid()
        return True

    def set_beta(self, new_beta):
        if not (0 < new_beta < 180): return False
        self.beta = new_beta
        self._update_from_angles(); self._check_valid()
        return True

    def set_gamma(self, new_gamma):
        if not (0 < new_gamma < 180): return False
        self.gamma = new_gamma
        self._update_from_angles(); self._check_valid()
        return True

    def set_a(self, new_a):
        if new_a <= 0: return False
        self.a = new_a
        self._update_from_angles(); self._check_valid()
        return True

    def get_triangle_vertices(self):
        if self.type != 'triangle' or not self.valid or self.b <= 0 or self.c <= 0:
            return [(0,0),(0,0),(0,0)]
        alpha_rad = math.radians(self.alpha)
        C = (self.b * math.cos(alpha_rad), self.b * math.sin(alpha_rad))
        cx = (0 + self.a + C[0]) / 3
        cy = (0 + 0 + C[1]) / 3
        return [(0-cx, 0-cy), (self.a-cx, 0-cy), (C[0]-cx, C[1]-cy)]

    def get_rect(self):
        if self.type == 'rect':
            return pygame.Rect(self.x - self.width/2, self.y - self.height/2, self.width, self.height)
        elif self.type == 'circle':
            return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius*2, self.radius*2)
        elif self.type == 'triangle':
            verts = self.get_triangle_vertices()
            if not self.valid or not verts or verts[0] == (0,0):
                return pygame.Rect(self.x-10, self.y-10, 20, 20)
            min_x = min(v[0] for v in verts); max_x = max(v[0] for v in verts)
            min_y = min(v[1] for v in verts); max_y = max(v[1] for v in verts)
            return pygame.Rect(self.x + min_x, self.y + min_y, max_x-min_x, max_y-min_y)

    def draw(self, screen, camera, zoom):
        if not self.valid:
            sx = (self.x - camera.x) * zoom; sy = (self.y - camera.y) * zoom
            pygame.draw.circle(screen, (255,0,0), (int(sx), int(sy)), 3); return
        sx = (self.x - camera.x) * zoom; sy = (self.y - camera.y) * zoom
        color = (255,255,0) if self.selected else self.color
        if self.type == 'rect':
            w = self.width * zoom; h = self.height * zoom
            if self.angle != 0:
                surf = pygame.Surface((w, h), pygame.SRCALPHA)
                surf.fill((0,0,0,0))
                pygame.draw.rect(surf, color, (0,0,w,h))
                rot_surf = pygame.transform.rotate(surf, self.angle)
                screen.blit(rot_surf, (sx - rot_surf.get_width()/2, sy - rot_surf.get_height()/2))
            else:
                rect = pygame.Rect(sx - w/2, sy - h/2, w, h)
                pygame.draw.rect(screen, color, rect)
        elif self.type == 'circle':
            r = self.radius * zoom
            pygame.draw.circle(screen, color, (int(sx), int(sy)), int(r))
        elif self.type == 'triangle':
            verts = self.get_triangle_vertices()
            if verts and verts[0] != (0,0):
                rad = math.radians(self.angle)
                transformed = []
                for vx, vy in verts:
                    vx *= zoom; vy *= zoom
                    rx = vx * math.cos(rad) - vy * math.sin(rad)
                    ry = vx * math.sin(rad) + vy * math.cos(rad)
                    transformed.append((sx + rx, sy + ry))
                pygame.draw.polygon(screen, color, transformed)

    def to_dict(self):
        data = {"type": self.type, "x": self.x, "y": self.y, "color": list(self.color), "angle": self.angle, "z_index": self.z_index}
        if self.type == 'rect':
            data["width"] = self.width; data["height"] = self.height
        elif self.type == 'circle':
            data["radius"] = self.radius
        elif self.type == 'triangle':
            data["a"] = self.a; data["alpha"] = self.alpha; data["beta"] = self.beta; data["gamma"] = self.gamma
        return data

    @staticmethod
    def from_dict(data):
        obj_type = data["type"]
        x = data["x"]; y = data["y"]
        color = tuple(data["color"])
        angle = data.get("angle", 0); z = data.get("z_index", 0)
        params = {}
        if obj_type == 'rect':
            params["width"] = data.get("width", 50); params["height"] = data.get("height", 50)
        elif obj_type == 'circle':
            params["radius"] = data.get("radius", 30)
        elif obj_type == 'triangle':
            params["a"] = data.get("a", 50); params["alpha"] = data.get("alpha", 60)
            params["beta"] = data.get("beta", 60); params["gamma"] = data.get("gamma", 60)
        return EditorObject(obj_type, x, y, params, color, angle, z)

class EditorApp:
    def __init__(self):
        print("Инициализация редактора...")
        try:
            pygame.init()
            print("pygame.init() выполнен.")
        except Exception as e:
            print("Ошибка pygame.init():", e)
            raise
        try:
            self.screen = pygame.display.set_mode((EDITOR_WIDTH, EDITOR_HEIGHT), pygame.RESIZABLE)
            pygame.display.set_caption("Редактор карты - War Stalker")
            print("Окно создано.")
        except Exception as e:
            print("Ошибка создания окна:", e)
            raise
        self.clock = pygame.time.Clock()
        self.running = True

        # Загрузка настроек редактора
        try:
            self.editor_settings = self.load_settings()
            self.zoom = self.editor_settings.get("zoom", 50.0)
            print(f"Настройки загружены: zoom={self.zoom}")
        except Exception as e:
            print("Ошибка загрузки настроек:", e)
            self.zoom = 50.0

        try:
            self.config_loader = ConfigLoader()
            self.current_map_name = "cordon"
            self.map_data = self.config_loader.load_map(self.current_map_name)
            self.world = World(self.map_data, scale=1.0)
            print("Карта загружена.")
        except Exception as e:
            print("Ошибка загрузки карты:", e)
            raise

        self.camera = Camera(EDITOR_WIDTH, EDITOR_HEIGHT)
        self.camera.x = 0; self.camera.y = 0

        try:
            with open("settings.json", "r") as f:
                settings_data = json.load(f)
                self.game_map_scale = settings_data.get("map_scale", 50.0)
        except:
            self.game_map_scale = 50.0

        self.editor_objects = []
        self.selected_objects = []
        self.load_objects()

        self.mode = "select"
        self.show_help = False
        self.show_create_menu = False
        self.show_resize_dialog = False
        self.show_save_dialog = False
        self.save_filename = ""
        self.save_dialog_active = False
        self.save_dialog_rect = None
        self.save_input_rect = None
        self.save_ok_rect = None
        self.save_cancel_rect = None

        # Меню настроек редактора
        self.show_editor_settings = False
        self.settings_input_active = False
        self.settings_input_text = str(self.zoom)
        self.settings_input_rect = None
        self.settings_ok_rect = None
        self.settings_cancel_rect = None

        self.selecting = False
        self.select_start = None
        self.select_end = None
        self.dragging_objects = False
        self.drag_start_mouse_world = None
        self.drag_objects_initial_positions = []
        self.panning = False
        self.pan_start = None

        self.last_click_time = 0
        self.editing_param = None
        self.editing_value = ""
        self.editing_obj = None
        self.old_value = None

        self.rgb_sliders = {'r': 255, 'g': 0, 'b': 0}
        self.slider_dragging = None
        self.slider_rects = {}

        self.error_message = ""
        self.error_timer = 0

        self.new_obj_type = "rect"
        self.new_color = (255,0,0)
        self.new_width = 50
        self.new_height = 50
        self.new_radius = 30
        self.new_a = 50
        self.new_alpha = 60
        self.new_beta = 60
        self.new_gamma = 60

        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.fps = 0

        self.spawn_x = 670
        self.spawn_y = 2469
        if self.map_data and "spawn" in self.map_data:
            self.spawn_x, self.spawn_y = self.map_data["spawn"]

        self.map_width = self.world.width
        self.map_height = self.world.height
        self.resize_input = ""
        self.resize_active = False

        self.smart_angle_editing = True
        self.smart_angle_rect = None

        self.angle_input_active = False
        self.angle_input_text = ""

        self.help_text = [
            "=== РЕДАКТОР КАРТЫ (F1 - справка) ===",
            "ЛКМ - панорамирование (инвертированное)",
            "ПКМ по объекту - выбрать объект (с Shift - добавить к выделению)",
            "ПКМ по выбранному объекту и перетаскивание - переместить объект(ы)",
            "ПКМ по пустому месту и перетаскивание - групповое выделение",
            "Двойной ЛКМ по параметру в панели свойств - редактировать параметр",
            "F3 - быстрое создание объекта (в центре курсора)",
            "C - открыть меню выбора типа, затем создать объект",
            "1,2,3 - быстрый выбор типа для F3 (прямоугольник, круг, треугольник)",
            "Num4 / Num6 - поворот на -5° / +5°",
            "Q / E - уменьшить/увеличить ширину (радиус / сторону a)",
            "R / T - уменьшить/увеличить высоту (сторону b)",
            "F2 - изменить размер карты",
            "F4 - настройки редактора",
            "F5 - запустить игру с текущей картой",
            "F6 - сохранить карту (с именем)",
            "F7 - перезаписать текущий файл карты",
            "ESC - выход, снять выделение"
        ]

        self.param_rects = {}
        print("Инициализация завершена.")

    def load_settings(self):
        try:
            with open(EDITOR_SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {"zoom": 50.0}

    def save_settings(self):
        with open(EDITOR_SETTINGS_FILE, "w") as f:
            json.dump({"zoom": self.zoom}, f, indent=4)

    def load_objects(self):
        try:
            with open("editor_objects.json", "r") as f:
                data = json.load(f)
                self.editor_objects = [EditorObject.from_dict(d) for d in data]
                self.editor_objects.sort(key=lambda o: o.z_index)
        except FileNotFoundError:
            pass

    def save_objects(self, filename="editor_objects.json"):
        data = [obj.to_dict() for obj in self.editor_objects]
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def save_map(self, filename, user=True):
        objects = []
        for obj in self.world.objects:
            hex_color = color_to_hex(obj["color"])
            obj_data = {"type": obj["type"], "x": int(obj["x"]), "y": int(obj["y"]), "width": int(obj["width"]), "height": int(obj["height"]), "color": hex_color}
            if obj["type"] == "tree":
                obj_data["radius"] = int(obj["radius"])
            if "shape" in obj:
                obj_data["shape"] = obj["shape"]
                if obj["shape"] == "triangle":
                    obj_data["a"] = obj.get("a", obj["width"])
                    obj_data["b"] = obj.get("b", obj["height"])
                    obj_data["alpha"] = obj.get("alpha", 60)
                    obj_data["beta"] = obj.get("beta", 60)
                    obj_data["gamma"] = obj.get("gamma", 60)
            objects.append(obj_data)

        for eobj in self.editor_objects:
            if not eobj.valid and eobj.type == 'triangle':
                continue
            hex_color = color_to_hex(eobj.color)
            if eobj.type == "rect":
                objects.append({"type": "building", "x": int(eobj.x), "y": int(eobj.y), "width": int(eobj.width), "height": int(eobj.height), "color": hex_color, "angle": eobj.angle})
            elif eobj.type == "circle":
                objects.append({"type": "tree", "x": int(eobj.x), "y": int(eobj.y), "radius": int(eobj.radius), "color": hex_color, "angle": eobj.angle})
            elif eobj.type == "triangle":
                objects.append({"type": "building", "x": int(eobj.x), "y": int(eobj.y), "width": int(eobj.a), "height": int(eobj.b), "color": hex_color, "angle": eobj.angle, "shape": "triangle", "a": eobj.a, "b": eobj.b, "alpha": eobj.alpha, "beta": eobj.beta, "gamma": eobj.gamma})

        map_data = {"name": "Custom Map", "width": self.map_width, "height": self.map_height, "background_color": "#3a3a3a", "objects": objects, "spawn": [self.spawn_x, self.spawn_y], "map_scale": self.game_map_scale}
        import yaml
        if user:
            path = os.path.join(USERMAPS_DIR, filename)
        else:
            path = os.path.join("data/maps", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(map_data, f, allow_unicode=True, sort_keys=False)
        print(f"Карта сохранена как {path}")

    def load_map(self, map_name):
        try:
            self.map_data = self.config_loader.load_map(map_name)
            self.world = World(self.map_data, scale=1.0)
            self.current_map_name = map_name
            self.map_width = self.world.width
            self.map_height = self.world.height
            self.editor_objects = []
            for obj in self.world.objects:
                if obj["type"] == "building":
                    if "shape" in obj and obj["shape"] == "triangle":
                        params = {"a": obj.get("a", obj["width"]), "b": obj.get("b", obj["height"]), "alpha": obj.get("alpha", 60), "beta": obj.get("beta", 60), "gamma": obj.get("gamma", 60)}
                        eobj = EditorObject("triangle", obj["x"], obj["y"], params, obj["color"], obj.get("angle", 0))
                    else:
                        params = {"width": obj["width"], "height": obj["height"]}
                        eobj = EditorObject("rect", obj["x"], obj["y"], params, obj["color"], obj.get("angle", 0))
                    self.editor_objects.append(eobj)
                elif obj["type"] == "tree":
                    params = {"radius": obj["radius"]}
                    eobj = EditorObject("circle", obj["x"], obj["y"], params, obj["color"], obj.get("angle", 0))
                    self.editor_objects.append(eobj)
            self.editor_objects.sort(key=lambda o: o.z_index)
            if self.map_data and "spawn" in self.map_data:
                self.spawn_x, self.spawn_y = self.map_data["spawn"]
        except Exception as e:
            print(f"Ошибка загрузки карты: {e}")

    def run_game(self):
        temp_file = "temp_map.yaml"
        self.save_map(temp_file, user=False)
        main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        subprocess.Popen([sys.executable, main_path, "--map", temp_file], cwd=os.getcwd())

    def create_object_at_cursor(self, obj_type=None):
        try:
            if obj_type is None: obj_type = self.new_obj_type
            mx, my = pygame.mouse.get_pos()
            wx = mx / self.zoom + self.camera.x
            wy = my / self.zoom + self.camera.y
            params = {}
            if obj_type == 'rect':
                params['width'] = self.new_width; params['height'] = self.new_height
            elif obj_type == 'circle':
                params['radius'] = self.new_radius
            elif obj_type == 'triangle':
                params['a'] = self.new_a; params['alpha'] = self.new_alpha; params['beta'] = self.new_beta; params['gamma'] = self.new_gamma
            new_obj = EditorObject(obj_type, wx, wy, params, self.new_color, 0, len(self.editor_objects))
            self.editor_objects.append(new_obj)
            self.selected_objects = [new_obj]
            new_obj.selected = True
        except Exception as e:
            self.show_error(f"Ошибка создания: {e}")

    def show_error(self, msg):
        self.error_message = msg; self.error_timer = 3.0

    def start_editing_param(self, obj, param_name):
        self.editing_obj = obj; self.editing_param = param_name
        if param_name == 'width': val = obj.width
        elif param_name == 'height': val = obj.height
        elif param_name == 'radius': val = obj.radius
        elif param_name == 'a': val = obj.a
        elif param_name == 'alpha': val = obj.alpha
        elif param_name == 'beta': val = obj.beta
        elif param_name == 'gamma': val = obj.gamma
        elif param_name == 'angle': val = obj.angle
        else: return
        self.editing_value = str(val); self.old_value = val

    def apply_editing(self):
        if self.editing_obj is None or self.editing_param is None: return
        try:
            new_val = float(self.editing_value)
            if self.editing_param in ('alpha','beta','gamma','angle'):
                if abs(new_val) < 0.01: new_val = 0.01
                new_val = round(new_val, 2)
            obj = self.editing_obj; old_val = self.old_value
            if self.editing_param in ('alpha','beta','gamma'):
                if not self.smart_angle_editing:
                    diff = new_val - old_val; half_diff = diff / 2.0
                    if self.editing_param == 'alpha':
                        new_beta = obj.beta - half_diff; new_gamma = obj.gamma - half_diff
                        obj.beta = new_beta; obj.gamma = new_gamma; obj.alpha = new_val
                        obj._update_from_angles(); obj._check_valid()
                    elif self.editing_param == 'beta':
                        new_alpha = obj.alpha - half_diff; new_gamma = obj.gamma - half_diff
                        obj.alpha = new_alpha; obj.gamma = new_gamma; obj.beta = new_val
                        obj._update_from_angles(); obj._check_valid()
                    elif self.editing_param == 'gamma':
                        new_alpha = obj.alpha - half_diff; new_beta = obj.beta - half_diff
                        obj.alpha = new_alpha; obj.beta = new_beta; obj.gamma = new_val
                        obj._update_from_angles(); obj._check_valid()
                    if not obj.valid: self.show_error("Недопустимый треугольник после коррекции")
                else:
                    if self.editing_param == 'alpha': obj.set_alpha(new_val)
                    elif self.editing_param == 'beta': obj.set_beta(new_val)
                    elif self.editing_param == 'gamma': obj.set_gamma(new_val)
                    if not obj.valid: self.show_error("Недопустимый треугольник (сумма != 180)")
            else:
                if self.editing_param == 'width': obj.width = max(1, new_val)
                elif self.editing_param == 'height': obj.height = max(1, new_val)
                elif self.editing_param == 'radius': obj.radius = max(1, new_val)
                elif self.editing_param == 'a':
                    obj.set_a(new_val)
                    if not obj.valid: self.show_error("Недопустимый треугольник после изменения a")
                elif self.editing_param == 'angle': obj.angle = new_val % 360
        except Exception as e: self.show_error(f"Ошибка ввода: {e}")
        self.editing_obj = None; self.editing_param = None; self.editing_value = ""; self.old_value = None

    def cancel_editing(self):
        self.editing_obj = None; self.editing_param = None; self.editing_value = ""; self.old_value = None

    def check_and_remove_invalid_selection(self):
        to_remove = []
        for obj in self.selected_objects:
            if obj.type == 'triangle' and not obj.valid: to_remove.append(obj)
        for obj in to_remove:
            self.selected_objects.remove(obj)
            if obj in self.editor_objects: self.editor_objects.remove(obj)
        if to_remove: self.show_error("Удалены невалидные треугольники")

    def clamp_camera(self):
        map_w = self.world.width; map_h = self.world.height
        screen_w = self.screen.get_width(); screen_h = self.screen.get_height()
        max_x = map_w * self.zoom - screen_w; max_y = map_h * self.zoom - screen_h
        if max_x < 0: self.camera.x = 0
        else: self.camera.x = max(0, min(self.camera.x, max_x))
        if max_y < 0: self.camera.y = 0
        else: self.camera.y = max(0, min(self.camera.y, max_y))

    def zoom_at(self, mouse_pos, factor):
        mx, my = mouse_pos
        wx = mx / self.zoom + self.camera.x
        wy = my / self.zoom + self.camera.y
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))
        if new_zoom == self.zoom: return
        self.zoom = new_zoom
        self.camera.x = wx - mx / self.zoom
        self.camera.y = wy - my / self.zoom
        self.clamp_camera()

    def draw_save_dialog(self):
        if not self.show_save_dialog: return
        width = 400; height = 150
        x = (self.screen.get_width() - width) // 2; y = (self.screen.get_height() - height) // 2
        self.save_dialog_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (50,50,50), self.save_dialog_rect)
        pygame.draw.rect(self.screen, (200,200,200), self.save_dialog_rect, 2)
        title = self.font.render("Введите имя карты (без .yaml):", True, COLOR_WHITE)
        self.screen.blit(title, (x+10, y+10))
        input_rect = pygame.Rect(x+10, y+50, width-20, 30)
        self.save_input_rect = input_rect
        pygame.draw.rect(self.screen, (100,100,100), input_rect)
        pygame.draw.rect(self.screen, (200,200,200), input_rect, 1)
        text_surf = self.font.render(self.save_filename, True, COLOR_WHITE)
        self.screen.blit(text_surf, (input_rect.x+5, input_rect.y+5))
        if self.save_dialog_active:
            cursor_x = input_rect.x+5+text_surf.get_width()
            pygame.draw.line(self.screen, COLOR_WHITE, (cursor_x, input_rect.y+5), (cursor_x, input_rect.y+25), 2)
        ok_rect = pygame.Rect(x+width-180, y+height-40, 80, 30); cancel_rect = pygame.Rect(x+width-90, y+height-40, 80, 30)
        self.save_ok_rect = ok_rect; self.save_cancel_rect = cancel_rect
        pygame.draw.rect(self.screen, (60,160,60), ok_rect); pygame.draw.rect(self.screen, (160,60,60), cancel_rect)
        self.screen.blit(self.font.render("OK", True, COLOR_WHITE), (ok_rect.x+28, ok_rect.y+5))
        self.screen.blit(self.font.render("Отмена", True, COLOR_WHITE), (cancel_rect.x+15, cancel_rect.y+5))

    def draw_settings_dialog(self):
        if not self.show_editor_settings: return
        width = 300; height = 150
        x = (self.screen.get_width() - width) // 2; y = (self.screen.get_height() - height) // 2
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (50,50,50), rect)
        pygame.draw.rect(self.screen, (200,200,200), rect, 2)
        title = self.font.render("Настройки редактора", True, COLOR_WHITE)
        self.screen.blit(title, (x+10, y+10))
        label = self.font.render("Масштаб (zoom):", True, COLOR_WHITE)
        self.screen.blit(label, (x+10, y+40))
        input_rect = pygame.Rect(x+10, y+65, 150, 30)
        self.settings_input_rect = input_rect
        pygame.draw.rect(self.screen, (100,100,100), input_rect)
        pygame.draw.rect(self.screen, (200,200,200), input_rect, 1)
        text_surf = self.font.render(self.settings_input_text, True, COLOR_WHITE)
        self.screen.blit(text_surf, (input_rect.x+5, input_rect.y+5))
        if self.settings_input_active:
            cursor_x = input_rect.x+5+text_surf.get_width()
            pygame.draw.line(self.screen, COLOR_WHITE, (cursor_x, input_rect.y+5), (cursor_x, input_rect.y+25), 2)
        # Кнопки
        ok_rect = pygame.Rect(x+width-180, y+height-40, 80, 30)
        cancel_rect = pygame.Rect(x+width-90, y+height-40, 80, 30)
        self.settings_ok_rect = ok_rect; self.settings_cancel_rect = cancel_rect
        pygame.draw.rect(self.screen, (60,160,60), ok_rect)
        pygame.draw.rect(self.screen, (160,60,60), cancel_rect)
        self.screen.blit(self.font.render("OK", True, COLOR_WHITE), (ok_rect.x+28, ok_rect.y+5))
        self.screen.blit(self.font.render("Отмена", True, COLOR_WHITE), (cancel_rect.x+15, cancel_rect.y+5))

    def handle_events(self):
        for event in pygame.event.get():
            try:
                if event.type == pygame.QUIT: self.running = False
                elif event.type == pygame.KEYDOWN: self.handle_keydown(event)
                elif event.type == pygame.MOUSEBUTTONDOWN: self.handle_mouse_down(event)
                elif event.type == pygame.MOUSEBUTTONUP: self.handle_mouse_up(event)
                elif event.type == pygame.MOUSEMOTION: self.handle_mouse_motion(event)
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.clamp_camera()
                elif event.type == pygame.MOUSEWHEEL:
                    mouse_pos = pygame.mouse.get_pos()
                    factor = ZOOM_STEP if event.y > 0 else 1.0 / ZOOM_STEP
                    self.zoom_at(mouse_pos, factor)
            except Exception as e:
                traceback.print_exc(); self.show_error(f"Ошибка: {e}")

    def handle_keydown(self, event):
        key = event.key
        if self.show_save_dialog:
            if self.save_dialog_active:
                if key == pygame.K_RETURN:
                    self.save_filename = self.save_filename.strip()
                    if not self.save_filename: self.save_filename = "modmap"
                    self.save_map(self.save_filename + ".yaml", user=True)
                    self.show_save_dialog = False; self.save_dialog_active = False; self.save_filename = ""
                elif key == pygame.K_ESCAPE:
                    self.show_save_dialog = False; self.save_dialog_active = False; self.save_filename = ""
                elif key == pygame.K_BACKSPACE: self.save_filename = self.save_filename[:-1]
                else:
                    if event.unicode and event.unicode.isprintable(): self.save_filename += event.unicode
                return
            else:
                return

        if self.show_editor_settings:
            if self.settings_input_active:
                if key == pygame.K_RETURN:
                    try:
                        new_zoom = float(self.settings_input_text)
                        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))
                        self.zoom = new_zoom
                        self.save_settings()
                        self.clamp_camera()
                    except:
                        pass
                    self.show_editor_settings = False
                    self.settings_input_active = False
                elif key == pygame.K_ESCAPE:
                    self.show_editor_settings = False
                    self.settings_input_active = False
                elif key == pygame.K_BACKSPACE:
                    self.settings_input_text = self.settings_input_text[:-1]
                else:
                    if event.unicode and event.unicode.isprintable():
                        self.settings_input_text += event.unicode
                return
            else:
                # Если окно настроек открыто, но поле не активно, клик активирует его
                pass

        if key in (pygame.K_F3, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_LALT, pygame.K_RALT):
            if key == pygame.K_F3: self.create_object_at_cursor(); return
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.editing_obj is not None: self.apply_editing(); return
                else: return
            elif key in (pygame.K_LALT, pygame.K_RALT): return

        if key == pygame.K_ESCAPE:
            if self.editing_obj is not None: self.cancel_editing()
            elif self.selected_objects:
                self.check_and_remove_invalid_selection(); self.selected_objects.clear()
            elif self.show_create_menu: self.show_create_menu = False
            elif self.show_resize_dialog: self.show_resize_dialog = False
            elif self.show_save_dialog:
                self.show_save_dialog = False; self.save_dialog_active = False; self.save_filename = ""
            elif self.show_editor_settings:
                self.show_editor_settings = False; self.settings_input_active = False
            else: self.running = False
        elif key == pygame.K_F1: self.show_help = not self.show_help
        elif key == pygame.K_F2:
            self.show_resize_dialog = not self.show_resize_dialog
            if self.show_resize_dialog: self.resize_input = f"{self.map_width}x{self.map_height}"
        elif key == pygame.K_F4:
            self.show_editor_settings = not self.show_editor_settings
            if self.show_editor_settings:
                self.settings_input_text = str(self.zoom)
                self.settings_input_active = True
        elif key == pygame.K_F5: self.run_game()
        elif key == pygame.K_F6:
            self.show_save_dialog = True; self.save_dialog_active = True; self.save_filename = ""
        elif key == pygame.K_F7:
            self.save_map(self.current_map_name + ".yaml", user=False); print(f"Карта {self.current_map_name} перезаписана")
        elif key == pygame.K_c:
            self.show_create_menu = not self.show_create_menu; if self.show_create_menu: self.mode = "select"
        elif key == pygame.K_1:
            self.new_obj_type = "rect"; self.mode = "add_rect"; self.show_create_menu = False
        elif key == pygame.K_2:
            self.new_obj_type = "circle"; self.mode = "add_circle"; self.show_create_menu = False
        elif key == pygame.K_3:
            self.new_obj_type = "triangle"; self.mode = "add_triangle"; self.show_create_menu = False
        elif key == pygame.K_KP4 or key == pygame.K_LEFT:
            for obj in self.selected_objects: obj.angle -= 5; if obj.angle < 0: obj.angle += 360
        elif key == pygame.K_KP6 or key == pygame.K_RIGHT:
            for obj in self.selected_objects: obj.angle += 5; if obj.angle >= 360: obj.angle -= 360
        elif key == pygame.K_q:
            for obj in self.selected_objects:
                if obj.type == 'rect': obj.width = max(5, obj.width - 5)
                elif obj.type == 'circle': obj.radius = max(5, obj.radius - 5)
                elif obj.type == 'triangle':
                    obj.a = max(5, obj.a - 5); obj._update_from_angles(); obj._check_valid()
                    if not obj.valid: self.show_error("Треугольник стал невалидным")
        elif key == pygame.K_e:
            for obj in self.selected_objects:
                if obj.type == 'rect': obj.width += 5
                elif obj.type == 'circle': obj.radius += 5
                elif obj.type == 'triangle':
                    obj.a += 5; obj._update_from_angles(); obj._check_valid()
                    if not obj.valid: self.show_error("Треугольник стал невалидным")
        elif key == pygame.K_r:
            for obj in self.selected_objects:
                if obj.type == 'rect': obj.height = max(5, obj.height - 5)
                elif obj.type == 'triangle':
                    obj.beta = min(179.9, obj.beta + 5); obj._update_from_angles(); obj._check_valid()
                    if not obj.valid: self.show_error("Треугольник стал невалидным")
        elif key == pygame.K_t:
            for obj in self.selected_objects:
                if obj.type == 'rect': obj.height += 5
                elif obj.type == 'triangle':
                    obj.beta = max(0.1, obj.beta - 5); obj._update_from_angles(); obj._check_valid()
                    if not obj.valid: self.show_error("Треугольник стал невалидным")

        if self.editing_obj is not None:
            if key == pygame.K_RETURN or key == pygame.K_KP_ENTER: self.apply_editing()
            elif key == pygame.K_ESCAPE: self.cancel_editing()
            elif key == pygame.K_BACKSPACE: self.editing_value = self.editing_value[:-1]
            else:
                if event.unicode in "0123456789.-": self.editing_value += event.unicode
            return

        if self.selected_objects and not self.show_resize_dialog:
            if key == pygame.K_RETURN and self.angle_input_active:
                try:
                    val = float(self.angle_input_text)
                    for obj in self.selected_objects: obj.angle = val % 360
                except: pass
                self.angle_input_active = False; self.angle_input_text = ""
            elif key == pygame.K_BACKSPACE and self.angle_input_active:
                self.angle_input_text = self.angle_input_text[:-1]
            elif self.angle_input_active:
                if event.unicode in "0123456789.-": self.angle_input_text += event.unicode
            else:
                if event.unicode in "0123456789.-": self.angle_input_active = True; self.angle_input_text = event.unicode

        if key == pygame.K_DELETE:
            if self.selected_objects:
                for obj in self.selected_objects:
                    if obj in self.editor_objects: self.editor_objects.remove(obj)
                self.selected_objects.clear()

    def handle_mouse_down(self, event):
        x, y = event.pos
        if self.show_save_dialog:
            if self.save_ok_rect and self.save_ok_rect.collidepoint(x, y):
                self.save_filename = self.save_filename.strip()
                if not self.save_filename: self.save_filename = "modmap"
                self.save_map(self.save_filename + ".yaml", user=True)
                self.show_save_dialog = False; self.save_dialog_active = False; self.save_filename = ""
                return
            elif self.save_cancel_rect and self.save_cancel_rect.collidepoint(x, y):
                self.show_save_dialog = False; self.save_dialog_active = False; self.save_filename = ""
                return
            elif self.save_input_rect and self.save_input_rect.collidepoint(x, y):
                self.save_dialog_active = True; return
            else: return

        if self.show_editor_settings:
            if self.settings_ok_rect and self.settings_ok_rect.collidepoint(x, y):
                try:
                    new_zoom = float(self.settings_input_text)
                    new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))
                    self.zoom = new_zoom
                    self.save_settings()
                    self.clamp_camera()
                except:
                    pass
                self.show_editor_settings = False
                self.settings_input_active = False
                return
            elif self.settings_cancel_rect and self.settings_cancel_rect.collidepoint(x, y):
                self.show_editor_settings = False
                self.settings_input_active = False
                return
            elif self.settings_input_rect and self.settings_input_rect.collidepoint(x, y):
                self.settings_input_active = True
                return
            else:
                return

        wx = x / self.zoom + self.camera.x; wy = y / self.zoom + self.camera.y
        if self.editing_obj is not None:
            self.apply_editing(); return

        if hasattr(self, 'smart_angle_rect') and self.smart_angle_rect and self.smart_angle_rect.collidepoint(x, y):
            self.smart_angle_editing = not self.smart_angle_editing; return

        if len(self.selected_objects) == 1 and hasattr(self, 'slider_rects'):
            for key, rect in self.slider_rects.items():
                if rect.collidepoint(x, y):
                    self.slider_dragging = key; self.update_slider_from_mouse(key, x, y); return

        if self.show_create_menu:
            menu_x = (self.screen.get_width() - 200) // 2; menu_y = (self.screen.get_height() - 150) // 2
            for i, obj_type in enumerate(['rect','circle','triangle']):
                btn_rect = pygame.Rect(menu_x+10, menu_y+40 + i*30, 180, 25)
                if btn_rect.collidepoint(x, y):
                    self.new_obj_type = obj_type; self.mode = f"add_{obj_type}"; self.show_create_menu = False
                    self.create_object_at_cursor(obj_type); return

        if self.show_resize_dialog:
            dialog_x = (self.screen.get_width() - 300)//2; dialog_y = (self.screen.get_height() - 150)//2
            apply_rect = pygame.Rect(dialog_x+10, dialog_y+90, 80, 30); cancel_rect = pygame.Rect(dialog_x+110, dialog_y+90, 80, 30)
            if apply_rect.collidepoint(x, y):
                try:
                    parts = self.resize_input.split('x')
                    if len(parts) == 2:
                        w = int(parts[0]); h = int(parts[1])
                        if w > 0 and h > 0:
                            self.map_width = w; self.map_height = h; self.world.width = w; self.world.height = h
                except: pass
                self.show_resize_dialog = False; return
            elif cancel_rect.collidepoint(x, y):
                self.show_resize_dialog = False; return
            input_rect = pygame.Rect(dialog_x+10, dialog_y+40, 280, 30)
            if input_rect.collidepoint(x, y): self.resize_active = True; return

        if len(self.selected_objects) == 1 and hasattr(self, 'color_rects'):
            for i, rect in enumerate(self.color_rects):
                if rect.collidepoint(x, y):
                    self.selected_objects[0].color = PALETTE_COLORS[i]
                    r,g,b = PALETTE_COLORS[i]; self.rgb_sliders['r'] = r; self.rgb_sliders['g'] = g; self.rgb_sliders['b'] = b
                    return

        current_time = time.time()
        if event.button == 1:
            if current_time - self.last_click_time < 0.5:
                for param_name, rect in self.param_rects.items():
                    if rect.collidepoint(x, y):
                        if len(self.selected_objects) == 1:
                            self.start_editing_param(self.selected_objects[0], param_name)
                        break
                self.last_click_time = 0
            else: self.last_click_time = current_time
            self.panning = True; self.pan_start = (x, y)

        elif event.button == 3:
            clicked_obj = None
            for obj in reversed(self.editor_objects):
                if obj.get_rect().collidepoint(wx, wy): clicked_obj = obj; break
            if clicked_obj is not None:
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    if clicked_obj not in self.selected_objects: self.selected_objects.append(clicked_obj)
                else: self.selected_objects = [clicked_obj]
                self.dragging_objects = True
                self.drag_start_mouse_world = (wx, wy)
                self.drag_objects_initial_positions = [(obj, obj.x, obj.y) for obj in self.selected_objects]
            else:
                self.selecting = True
                self.select_start = (wx, wy); self.select_end = (wx, wy)
                if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    self.check_and_remove_invalid_selection(); self.selected_objects.clear()

    def update_slider_from_mouse(self, key, mx, my):
        rect = self.slider_rects.get(key)
        if rect is None: return
        rel_x = mx - rect.x
        val = int((rel_x / rect.width) * 255); val = max(0, min(255, val))
        self.rgb_sliders[key] = val
        if len(self.selected_objects) == 1:
            self.selected_objects[0].color = (self.rgb_sliders['r'], self.rgb_sliders['g'], self.rgb_sliders['b'])

    def handle_mouse_up(self, event):
        if event.button == 1:
            self.panning = False; self.slider_dragging = None
        elif event.button == 3:
            if self.selecting:
                self.selecting = False
                if self.select_start and self.select_end:
                    rect = pygame.Rect(min(self.select_start[0], self.select_end[0]), min(self.select_start[1], self.select_end[1]), abs(self.select_start[0]-self.select_end[0]), abs(self.select_start[1]-self.select_end[1]))
                    for obj in self.editor_objects:
                        if obj.get_rect().colliderect(rect):
                            if obj not in self.selected_objects: self.selected_objects.append(obj)
                self.select_start = None; self.select_end = None
            self.dragging_objects = False; self.drag_objects_initial_positions = []

    def handle_mouse_motion(self, event):
        x, y = event.pos
        wx = x / self.zoom + self.camera.x; wy = y / self.zoom + self.camera.y
        if self.panning:
            dx = (x - self.pan_start[0]) / self.zoom; dy = (y - self.pan_start[1]) / self.zoom
            self.camera.x -= dx; self.camera.y -= dy; self.pan_start = (x, y)
        if self.selecting: self.select_end = (wx, wy)
        if self.dragging_objects:
            if self.drag_start_mouse_world:
                dx = wx - self.drag_start_mouse_world[0]; dy = wy - self.drag_start_mouse_world[1]
                for obj, orig_x, orig_y in self.drag_objects_initial_positions:
                    obj.x = orig_x + dx; obj.y = orig_y + dy
        if self.slider_dragging is not None:
            self.update_slider_from_mouse(self.slider_dragging, x, y)

    def draw(self):
        self.screen.fill((40,40,40))
        self.draw_grid()
        self.draw_world_with_zoom()
        for obj in self.editor_objects: obj.draw(self.screen, self.camera, self.zoom)
        if self.selecting and self.select_start and self.select_end:
            sx = (self.select_start[0] - self.camera.x) * self.zoom; sy = (self.select_start[1] - self.camera.y) * self.zoom
            ex = (self.select_end[0] - self.camera.x) * self.zoom; ey = (self.select_end[1] - self.camera.y) * self.zoom
            rect = pygame.Rect(min(sx, ex), min(sy, ey), abs(ex-sx), abs(ey-sy))
            pygame.draw.rect(self.screen, (255,255,255,128), rect, 1)
        sx = (self.spawn_x - self.camera.x) * self.zoom; sy = (self.spawn_y - self.camera.y) * self.zoom
        if 0 <= sx < self.screen.get_width() and 0 <= sy < self.screen.get_height():
            pygame.draw.circle(self.screen, (255,255,0), (int(sx), int(sy)), 8, 2)
            label = self.font.render("SPAWN", True, (255,255,0)); self.screen.blit(label, (sx+12, sy-8))
        self.draw_toolbar()
        if self.selected_objects: self.draw_properties_panel()
        if self.show_create_menu: self.draw_create_menu()
        if self.show_resize_dialog: self.draw_resize_dialog()
        if self.show_save_dialog: self.draw_save_dialog()
        if self.show_editor_settings: self.draw_settings_dialog()
        self.draw_info()
        if self.show_help: self.draw_help()
        if self.error_message and self.error_timer > 0:
            surf = self.font.render("ОШИБКА: " + self.error_message, True, (255,100,100))
            self.screen.blit(surf, (10, self.screen.get_height() - 60)); self.error_timer -= 1/60
        fps_text = f"FPS: {self.fps}"; fps_surf = self.font.render(fps_text, True, (255,255,0))
        self.screen.blit(fps_surf, (self.screen.get_width() - 100, 10))
        pygame.display.flip()

    def draw_world_with_zoom(self):
        tile_size = 256
        start_col = int(self.camera.x // tile_size); end_col = int((self.camera.x + self.camera.width / self.zoom) // tile_size) + 1
        start_row = int(self.camera.y // tile_size); end_row = int((self.camera.y + self.camera.height / self.zoom) // tile_size) + 1
        map_w = self.world.width; map_h = self.world.height
        start_col = max(0, start_col); end_col = min(map_w // tile_size, end_col)
        start_row = max(0, start_row); end_row = min(map_h // tile_size, end_row)
        for col in range(start_col, end_col):
            for row in range(start_row, end_row):
                tile = self.world.tile_map.get_tile(col, row, force=True)
                if tile:
                    if self.zoom != 1.0:
                        new_w = int(tile.get_width() * self.zoom); new_h = int(tile.get_height() * self.zoom)
                        scaled_tile = pygame.transform.scale(tile, (new_w, new_h))
                    else: scaled_tile = tile
                    screen_x = col * tile_size * self.zoom - self.camera.x * self.zoom
                    screen_y = row * tile_size * self.zoom - self.camera.y * self.zoom
                    self.screen.blit(scaled_tile, (screen_x, screen_y))

    def draw_grid(self):
        step = 50
        width = self.screen.get_width(); height = self.screen.get_height()
        start_x = int(self.camera.x / step) * step; start_y = int(self.camera.y / step) * step
        for x in range(int(start_x), int(start_x + width / self.zoom + step), step):
            sx = (x - self.camera.x) * self.zoom
            if 0 <= sx < width: pygame.draw.line(self.screen, (60,60,60), (sx,0), (sx,height))
        for y in range(int(start_y), int(start_y + height / self.zoom + step), step):
            sy = (y - self.camera.y) * self.zoom
            if 0 <= sy < height: pygame.draw.line(self.screen, (60,60,60), (0,sy), (width,sy))

    def draw_toolbar(self):
        y=10; x=10; btn_w=60; btn_h=30
        modes = [("select","Выбор"), ("add_rect","Квадр"), ("add_circle","Круг"), ("add_triangle","Треуг")]
        # Добавим кнопку настроек
        settings_btn = pygame.Rect(x + 4*(btn_w+5), y, btn_w, btn_h)
        pygame.draw.rect(self.screen, (80,80,200), settings_btn)
        self.screen.blit(self.font.render("Настр", True, COLOR_WHITE), (x+4*(btn_w+5)+10, y+5))
        for mode, label in modes:
            rect = pygame.Rect(x,y,btn_w,btn_h)
            color = (100,100,200) if self.mode == mode else (80,80,80)
            pygame.draw.rect(self.screen, color, rect)
            self.screen.blit(self.font.render(label, True, COLOR_WHITE), (x+10, y+5))
            x += btn_w + 5

    def draw_properties_panel(self):
        panel_width = 280; panel_x = self.screen.get_width() - panel_width - 10; panel_y = 50; panel_height = self.screen.get_height() - 100
        pygame.draw.rect(self.screen, (50,50,50), (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, (100,100,100), (panel_x, panel_y, panel_width, panel_height), 2)
        y = panel_y + 10
        self.screen.blit(self.font.render("Свойства объекта", True, COLOR_WHITE), (panel_x+10, y)); y += 25
        check_x = panel_x + panel_width - 40; check_y = panel_y + 10
        self.smart_angle_rect = pygame.Rect(check_x, check_y, 24, 24)
        pygame.draw.rect(self.screen, (80,80,80), self.smart_angle_rect); pygame.draw.rect(self.screen, (200,200,200), self.smart_angle_rect, 1)
        if self.smart_angle_editing:
            pts = [(check_x+4, check_y+12), (check_x+9, check_y+19), (check_x+20, check_y+5)]
            pygame.draw.lines(self.screen, (0,255,0), False, pts, 3)
        label = self.font.render("Тонкая", True, COLOR_WHITE); self.screen.blit(label, (check_x-50, check_y+4))
        self.param_rects = {}
        if len(self.selected_objects) == 1:
            obj = self.selected_objects[0]
            self.rgb_sliders['r'], self.rgb_sliders['g'], self.rgb_sliders['b'] = obj.color
            if obj.type == 'triangle' and not obj.valid:
                warn = self.font.render("НЕВАЛИДНЫЙ ТРЕУГОЛЬНИК", True, (255,100,100))
                self.screen.blit(warn, (panel_x+10, y)); y += 20
            self.screen.blit(self.font.render(f"Тип: {obj.type}", True, COLOR_WHITE), (panel_x+10, y)); y += 20
            self.screen.blit(self.font.render(f"X: {int(obj.x)}  Y: {int(obj.y)}", True, COLOR_WHITE), (panel_x+10, y)); y += 20
            angle_text = f"Поворот: {int(obj.angle)}°"
            self.screen.blit(self.font.render(angle_text, True, COLOR_WHITE), (panel_x+10, y))
            self.param_rects['angle'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
            if obj.type == 'rect':
                self.screen.blit(self.font.render(f"Ширина: {obj.width}", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['width'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
                self.screen.blit(self.font.render(f"Высота: {obj.height}", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['height'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
            elif obj.type == 'circle':
                self.screen.blit(self.font.render(f"Радиус: {obj.radius}", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['radius'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
            elif obj.type == 'triangle':
                self.screen.blit(self.font.render(f"a (основание): {obj.a:.2f}", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['a'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
                self.screen.blit(self.font.render(f"b (правая): {obj.b:.2f}", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['b'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
                self.screen.blit(self.font.render(f"c (левая): {obj.c:.2f}", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['c'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
                self.screen.blit(self.font.render(f"α (угол A): {obj.alpha:.1f}°", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['alpha'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
                self.screen.blit(self.font.render(f"β (угол B): {obj.beta:.1f}°", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['beta'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
                self.screen.blit(self.font.render(f"γ (угол C): {obj.gamma:.1f}°", True, COLOR_WHITE), (panel_x+10, y))
                self.param_rects['gamma'] = pygame.Rect(panel_x+10, y, 200, 20); y += 20
            if self.editing_obj == obj and self.editing_param is not None:
                param_rect = self.param_rects.get(self.editing_param)
                if param_rect:
                    pygame.draw.rect(self.screen, (50,50,50), param_rect); pygame.draw.rect(self.screen, (255,255,255), param_rect, 1)
                    text = self.editing_value + "_"; surf = self.font.render(text, True, COLOR_WHITE); self.screen.blit(surf, (param_rect.x+2, param_rect.y+2))
            self.screen.blit(self.font.render("Быстрый цвет:", True, COLOR_WHITE), (panel_x+10, y))
            color_x = panel_x + 120; color_y = y
            self.color_rects = []
            for i, col in enumerate(PALETTE_COLORS):
                rect = pygame.Rect(color_x + i*22, color_y, 20, 20)
                pygame.draw.rect(self.screen, col, rect)
                if obj.color == col: pygame.draw.rect(self.screen, COLOR_WHITE, rect, 2)
                self.color_rects.append(rect)
            y += 30
            self.screen.blit(self.font.render("RGB:", True, COLOR_WHITE), (panel_x+10, y))
            r_rect = pygame.Rect(panel_x+70, y, 180, 16)
            pygame.draw.rect(self.screen, (60,60,60), r_rect); fill = (self.rgb_sliders['r']/255)*r_rect.width
            pygame.draw.rect(self.screen, (255,0,0), (r_rect.x, r_rect.y, fill, r_rect.height)); pygame.draw.rect(self.screen, (200,200,200), r_rect, 1)
            self.slider_rects['r'] = r_rect; y += 22
            g_rect = pygame.Rect(panel_x+70, y, 180, 16); pygame.draw.rect(self.screen, (60,60,60), g_rect)
            fill = (self.rgb_sliders['g']/255)*g_rect.width; pygame.draw.rect(self.screen, (0,255,0), (g_rect.x, g_rect.y, fill, g_rect.height)); pygame.draw.rect(self.screen, (200,200,200), g_rect, 1)
            self.slider_rects['g'] = g_rect; y += 22
            b_rect = pygame.Rect(panel_x+70, y, 180, 16); pygame.draw.rect(self.screen, (60,60,60), b_rect)
            fill = (self.rgb_sliders['b']/255)*b_rect.width; pygame.draw.rect(self.screen, (0,0,255), (b_rect.x, b_rect.y, fill, b_rect.height)); pygame.draw.rect(self.screen, (200,200,200), b_rect, 1)
            self.slider_rects['b'] = b_rect; y += 22
            color_preview = pygame.Rect(panel_x+10, y, 30, 20); pygame.draw.rect(self.screen, obj.color, color_preview); pygame.draw.rect(self.screen, (200,200,200), color_preview, 1)
        else:
            self.screen.blit(self.font.render(f"Выбрано объектов: {len(self.selected_objects)}", True, COLOR_WHITE), (panel_x+10, y))

    def draw_create_menu(self):
        width=200; height=150
        x=(self.screen.get_width()-width)//2; y=(self.screen.get_height()-height)//2
        pygame.draw.rect(self.screen, (50,50,50), (x,y,width,height)); pygame.draw.rect(self.screen, (100,100,100), (x,y,width,height), 2)
        self.screen.blit(self.font.render("Выберите тип объекта", True, COLOR_WHITE), (x+10, y+10))
        options = ["Прямоугольник", "Круг", "Треугольник"]
        for i, opt in enumerate(options):
            color = (255,255,0) if self.mode == f"add_{['rect','circle','triangle'][i]}" else COLOR_WHITE
            text = self.font.render(opt, True, color); self.screen.blit(text, (x+10, y+40 + i*30))

    def draw_resize_dialog(self):
        width=300; height=150
        x=(self.screen.get_width()-width)//2; y=(self.screen.get_height()-height)//2
        pygame.draw.rect(self.screen, (50,50,50), (x,y,width,height)); pygame.draw.rect(self.screen, (100,100,100), (x,y,width,height), 2)
        self.screen.blit(self.font.render("Размер карты (WxH):", True, COLOR_WHITE), (x+10, y+10))
        input_rect = pygame.Rect(x+10, y+40, width-20, 30)
        pygame.draw.rect(self.screen, (200,200,200), input_rect, 1)
        if self.resize_active: pygame.draw.rect(self.screen, (255,255,255), input_rect, 2)
        self.screen.blit(self.font.render(self.resize_input, True, COLOR_WHITE), (x+15, y+45))
        apply_rect = pygame.Rect(x+10, y+90, 80, 30); cancel_rect = pygame.Rect(x+110, y+90, 80, 30)
        pygame.draw.rect(self.screen, (60,160,60), apply_rect); pygame.draw.rect(self.screen, (160,60,60), cancel_rect)
        self.screen.blit(self.font.render("Применить", True, COLOR_WHITE), (x+15, y+95)); self.screen.blit(self.font.render("Отмена", True, COLOR_WHITE), (x+120, y+95))

    def draw_info(self):
        mx, my = pygame.mouse.get_pos()
        wx = mx / self.zoom + self.camera.x; wy = my / self.zoom + self.camera.y
        info = f"Коорд: ({int(wx)}, {int(wy)})  Масштаб: {self.zoom:.2f}x  Объектов: {len(self.editor_objects)}"
        info_surf = self.font.render(info, True, (200,200,200)); self.screen.blit(info_surf, (10, self.screen.get_height() - 30))

    def draw_help(self):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height())); overlay.set_alpha(200); overlay.fill((0,0,0))
        self.screen.blit(overlay, (0,0)); y=50
        for line in self.help_text:
            surf = self.font.render(line, True, (255,255,255)); self.screen.blit(surf, (50, y)); y += 25

    def update(self):
        self.fps = int(self.clock.get_fps())
        if self.error_timer > 0:
            self.error_timer -= 1/60
            if self.error_timer < 0: self.error_timer = 0

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            try:
                self.handle_events()
                self.update()
                self.draw()
            except Exception as e:
                traceback.print_exc()
                self.show_error(f"Ошибка: {e}")
        pygame.quit(); sys.exit()

if __name__ == "__main__":
    try:
        app = EditorApp()
        app.run()
    except Exception as e:
        print("Критическая ошибка в редакторе:")
        traceback.print_exc()
        sys.exit(1)
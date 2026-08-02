#!/usr/bin/env python3
# map_editor.py — редактор карт WarStalker
# Полностью переработанная система групп:
# - Заглушка (dummy) — зелёный ромб, только координаты и поворот.
# - Главный объект группы (UNDGmain) может быть любым объектом (включая заглушку).
# - При смене главного объекта (Shift+ПКМ) локальные координаты пересчитываются.
# - Групповое перемещение: все выделенные объекты двигаются вместе.
# - При удалении заглушки новый главный назначается автоматически.

import pygame
import sys
import os
import math
import subprocess
import traceback
from pygame.locals import *

sys.path.insert(0, os.path.dirname(__file__))

# ====== Константы ======
COLOR_BG = (40, 40, 40)
COLOR_GRID = (60, 60, 60)
COLOR_PANEL = (30, 30, 30)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (128, 128, 128)
COLOR_LIGHT_GRAY = (200, 200, 200)
COLOR_ORANGE = (255, 165, 0)
COLOR_SELECT = (0, 100, 255)
COLOR_CURSOR = (255, 255, 255)
COLOR_HOVER = (255, 255, 0)
COLOR_RESIZE = (0, 255, 255)
COLOR_ANGLE = (255, 255, 0)
COLOR_LABEL = (200, 200, 200)
COLOR_MARKER = (0, 200, 255)
COLOR_TEMP = (100, 200, 255)
COLOR_RIGHT_PANEL_BG = (50, 50, 50)
COLOR_RIGHT_PANEL_BORDER = (100, 100, 100)
COLOR_RIGHT_PANEL_ITEM = (70, 70, 70)
COLOR_RIGHT_PANEL_ITEM_HOVER = (90, 90, 90)
COLOR_RIGHT_PANEL_ITEM_SELECTED = (0, 80, 200)
COLOR_RIGHT_PANEL_TEXT = (255, 255, 255)
COLOR_RIGHT_PANEL_TRIGGER = (80, 80, 80)
COLOR_GROUP_EXPAND = (200, 200, 0)
COLOR_DUMMY = (0, 255, 0)
COLOR_PLACEMENT_GHOST = (100, 200, 255)  # для призрака при размещении

PANEL_WIDTH = 220
ICON_SIZE = 32
COLOR_BOX_SIZE = 20
SLIDER_WIDTH = 100
SLIDER_HEIGHT = 6
RIGHT_PANEL_WIDTH = 230
RIGHT_PANEL_TRIGGER_WIDTH = 10
INDENT_WIDTH = 20

def rnd(v):
    return round(v, 2)

class Editor:
    def __init__(self):
        pygame.init()
        self.screen_width = 1400
        self.screen_height = 900
        self.fullscreen = False
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), RESIZABLE | DOUBLEBUF)
        pygame.display.set_caption("Редактор карт WarStalker")
        self.clock = pygame.time.Clock()
        self.running = True

        for dir_path in ["data/config", "data/maps", "data/maps/usermaps", "saves", "logs"]:
            os.makedirs(dir_path, exist_ok=True)

        from game.config_loader import ConfigLoader
        self.loader = ConfigLoader()

        self.map_data = {
            "name": "Новая карта",
            "width": 3000,
            "height": 3000,
            "background_color": "#3a3a3a",
            "objects": [],
            "spawn": [1500, 1500]
        }
        self.current_filename = None
        try:
            self.map_data = self.loader.load_map("cordon")
            self.current_filename = "cordon"
            print(f"Загружена карта: cordon, объектов: {len(self.map_data.get('objects', []))}")
        except Exception as e:
            print(f"Не удалось загрузить карту cordon: {e}. Создана пустая карта.")

        self.object_counter = 0
        self.group_counter = 0
        self.dummy_counter = 0

        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.dragging_camera = False
        self.camera_drag_start = (0, 0)

        self.selected_indices = []
        self.hover_index = -1
        self.dragging_object = False
        self.drag_offset = (0, 0)
        self.selection_rect_start = None
        self.selection_rect_end = None
        self.dragging_selection = False

        # Переменные для перетаскивания нескольких объектов
        self.drag_start_world = None          # (wx, wy) начальная позиция мыши в мире
        self.drag_initial_abs = {}            # idx -> (abs_x, abs_y) начальные абсолютные координаты
        self.drag_group_indices = []          # индексы всех объектов, перемещаемых вместе (если есть главный)

        self.resizing = False
        self.resize_type = None
        self.resize_index = -1
        self.resize_data = {}
        self.hover_resize = False
        self.hover_resize_type = None

        self.rotating = False
        self.rotate_index = -1
        self.rotate_start_angle = 0.0

        self.new_object_type = "circle"
        self.new_radius = 30
        self.new_width = 60
        self.new_height = 40
        self.new_a = 60.0
        self.new_b = 60.0
        self.new_c = 60.0
        self.new_alpha = 60.0
        self.new_beta = 60.0
        self.new_gamma = 60.0
        self.fine_tune = False

        self.base_colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (255, 255, 255), (128, 128, 128), (0, 0, 0)
        ]
        self.rgb_sliders = [255, 0, 0]
        self.slider_dragging = None           # индекс слайдера (0=R,1=G,2=B)
        self.slider_dragging_button = None    # 1 - левая, 3 - правая

        self.show_help = False
        self.resize_input_active = False
        self.resize_width_text = ""
        self.resize_height_text = ""
        self.save_as_active = False
        self.save_as_text = ""

        self.input_active = False
        self.input_text = ""
        self.input_param = None
        self.input_obj_index = -1

        self.last_click_time = 0
        self.last_click_pos = (0, 0)
        self.last_click_param = None

        self.right_panel_visible = False
        self.right_panel_scroll = 0
        self.right_panel_dragging = False
        self.right_panel_drag_index = -1
        self.right_panel_drag_start_y = 0
        self.right_panel_rename_index = -1
        self.right_panel_rename_text = ""
        self.right_panel_item_height = 28
        self.right_panel_padding = 5
        self.right_panel_mouse_down_pos = (0, 0)

        self.panel_scroll = 0

        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_bold = pygame.font.Font(None, 28)

        self.panel_rect = pygame.Rect(0, 0, PANEL_WIDTH, self.screen_height)
        self.right_panel_rect = pygame.Rect(self.screen_width - RIGHT_PANEL_WIDTH, 0, RIGHT_PANEL_WIDTH, self.screen_height)

        self.icon_rects = []
        self.color_rects = []
        self.slider_rects = []
        self.checkbox_rect = None
        self.button_rects = []
        self.param_rects = []

        self.create_child_dialog = False
        self.create_child_parent_idx = -1
        self.create_child_selected_type = "circle"
        self.create_child_dialog_rect = None
        self.create_child_buttons = []

        # Хранилище главных объектов групп: group_id -> main_idx
        self.group_main = {}

        # Режим размещения дочернего объекта
        self.placement_mode = False
        self.placement_parent_idx = -1
        self.placement_type = None
        self.placement_dummy = False
        self.placement_ghost_obj = None  # словарь-заготовка для отрисовки призрака

    # ====== Иерархические вычисления ======
    def get_group_main(self, group_id):
        """Возвращает индекс главного объекта группы."""
        if group_id in self.group_main:
            return self.group_main[group_id]
        # Если не найдено, ищем в объектах
        for i, obj in enumerate(self.map_data["objects"]):
            if obj.get("is_group") and obj.get("id") == group_id:
                # Главный — первый в children или тот, у кого есть флаг main
                children = obj.get("children", [])
                for child_idx in children:
                    child = self.map_data["objects"][child_idx]
                    if child.get("is_main", False):
                        self.group_main[group_id] = child_idx
                        return child_idx
                # Если нет флага, берём первый
                if children:
                    self.group_main[group_id] = children[0]
                    return children[0]
        return None

    def set_group_main(self, group_id, new_main_idx):
        """Устанавливает новый главный объект для группы."""
        old_main = self.get_group_main(group_id)
        if old_main is not None and old_main != new_main_idx:
            old_obj = self.map_data["objects"][old_main]
            old_obj["is_main"] = False
            # Переименовываем старого главного в UNDGobj
            old_name = old_obj.get("name", "Объект")
            if not old_name.startswith("UNDGobj:"):
                old_obj["name"] = f"UNDGobj: {old_name}"
        # Новый главный
        new_obj = self.map_data["objects"][new_main_idx]
        new_obj["is_main"] = True
        new_name = new_obj.get("name", "Объект")
        if not new_name.startswith("UNDGmain:"):
            new_obj["name"] = f"UNDGmain: {new_name}"
        self.group_main[group_id] = new_main_idx
        # Обновляем локальные координаты всех объектов группы относительно нового главного
        self.recalc_local_coords(group_id, new_main_idx)

    def recalc_local_coords(self, group_id, new_main_idx):
        """Пересчитывает локальные координаты всех объектов группы относительно нового главного."""
        main_obj = self.map_data["objects"][new_main_idx]
        px, py, pa = main_obj.get("x", 0), main_obj.get("y", 0), main_obj.get("angle", 0)
        for i, obj in enumerate(self.map_data["objects"]):
            if obj.get("group_id") == group_id and i != new_main_idx:
                # Абсолютные координаты до пересчёта
                if obj.get("group_id") is not None:
                    abs_x, abs_y, abs_a = self.get_abs_transform(i, force_main=new_main_idx)
                else:
                    abs_x, abs_y, abs_a = obj.get("x", 0), obj.get("y", 0), obj.get("angle", 0)
                # Вычисляем локальные
                dx = abs_x - px
                dy = abs_y - py
                angle_rad = math.radians(pa)
                local_x = dx * math.cos(-angle_rad) - dy * math.sin(-angle_rad)
                local_y = dx * math.sin(-angle_rad) + dy * math.cos(-angle_rad)
                local_angle = abs_a - pa
                obj["local_x"] = rnd(local_x)
                obj["local_y"] = rnd(local_y)
                obj["local_angle"] = rnd(local_angle)
                # Обновляем абсолютные координаты (они будут вычисляться через get_abs_transform)
                obj["x"] = abs_x
                obj["y"] = abs_y
                obj["angle"] = abs_a

    def get_abs_transform(self, obj_idx, force_main=None):
        """Возвращает абсолютные координаты и угол для объекта с учётом иерархии."""
        obj = self.map_data["objects"][obj_idx]
        if obj.get("group_id") is None or obj.get("is_group"):
            return obj.get("x", 0), obj.get("y", 0), obj.get("angle", 0)
        group_id = obj["group_id"]
        main_idx = force_main if force_main is not None else self.get_group_main(group_id)
        if main_idx is None:
            # Если главный не найден, используем самого себя как абсолют
            return obj.get("x", 0), obj.get("y", 0), obj.get("angle", 0)
        parent_obj = self.map_data["objects"][main_idx]
        px, py, pa = parent_obj.get("x", 0), parent_obj.get("y", 0), parent_obj.get("angle", 0)
        lx = obj.get("local_x", 0)
        ly = obj.get("local_y", 0)
        la = obj.get("local_angle", 0)
        angle_rad = math.radians(pa)
        abs_x = px + lx * math.cos(angle_rad) - ly * math.sin(angle_rad)
        abs_y = py + lx * math.sin(angle_rad) + ly * math.cos(angle_rad)
        abs_angle = pa + la
        return abs_x, abs_y, abs_angle

    def set_abs_position(self, idx, abs_x, abs_y):
        """Устанавливает абсолютные координаты объекта, обновляя локальные, если необходимо."""
        obj = self.map_data["objects"][idx]
        if obj.get("is_group"):
            # Главный объект группы – просто устанавливаем x,y
            obj["x"] = abs_x
            obj["y"] = abs_y
            return
        group_id = obj.get("group_id")
        if group_id is not None:
            # Дочерний объект – пересчитываем локальные координаты
            main_idx = self.get_group_main(group_id)
            if main_idx is not None:
                parent_obj = self.map_data["objects"][main_idx]
                px, py, pa = parent_obj.get("x", 0), parent_obj.get("y", 0), parent_obj.get("angle", 0)
                dx = abs_x - px
                dy = abs_y - py
                angle_rad = math.radians(pa)
                local_x = dx * math.cos(-angle_rad) - dy * math.sin(-angle_rad)
                local_y = dx * math.sin(-angle_rad) + dy * math.cos(-angle_rad)
                obj["local_x"] = rnd(local_x)
                obj["local_y"] = rnd(local_y)
                obj["x"] = abs_x
                obj["y"] = abs_y
            else:
                obj["x"] = abs_x
                obj["y"] = abs_y
        else:
            obj["x"] = abs_x
            obj["y"] = abs_y

    # ====== Геометрические преобразования ======
    def world_to_screen(self, wx, wy):
        sx = (wx - self.camera_x) * self.zoom + PANEL_WIDTH
        sy = (wy - self.camera_y) * self.zoom
        return int(sx), int(sy)

    def screen_to_world(self, sx, sy):
        wx = (sx - PANEL_WIDTH) / self.zoom + self.camera_x
        wy = sy / self.zoom + self.camera_y
        return wx, wy

    def get_world_pos(self, screen_pos):
        mx, my = screen_pos
        if mx < PANEL_WIDTH:
            return None
        return self.screen_to_world(mx, my)

    # ====== Треугольники: математика ======
    def validate_triangle_angles(self, alpha, beta, gamma):
        alpha = max(0.01, min(179.9, alpha))
        beta = max(0.01, min(179.9, beta))
        gamma = max(0.01, min(179.9, gamma))
        total = alpha + beta + gamma
        if abs(total - 180.0) > 0.01:
            return False, None
        return True, (rnd(alpha), rnd(beta), rnd(gamma))

    def compute_triangle_sides(self, a, alpha, beta, gamma):
        alpha_rad = math.radians(alpha)
        beta_rad = math.radians(beta)
        gamma_rad = math.radians(gamma)
        if abs(math.sin(alpha_rad)) < 1e-9:
            return None
        b = a * math.sin(beta_rad) / math.sin(alpha_rad)
        c = a * math.sin(gamma_rad) / math.sin(alpha_rad)
        return rnd(b), rnd(c)

    def update_triangle_from_angles(self, obj):
        a = obj.get("a", 60.0)
        alpha = obj.get("alpha", 60.0)
        beta = obj.get("beta", 60.0)
        gamma = obj.get("gamma", 60.0)
        valid, angles = self.validate_triangle_angles(alpha, beta, gamma)
        if not valid:
            obj["valid"] = False
            return False
        alpha, beta, gamma = angles
        sides = self.compute_triangle_sides(a, alpha, beta, gamma)
        if sides is None:
            obj["valid"] = False
            return False
        b, c = sides
        obj["a"] = rnd(a)
        obj["b"] = rnd(b)
        obj["c"] = rnd(c)
        obj["alpha"] = rnd(alpha)
        obj["beta"] = rnd(beta)
        obj["gamma"] = rnd(gamma)
        obj["valid"] = True
        return True

    def correct_angles(self, obj, changed_angle, delta):
        alpha = obj.get("alpha", 60.0)
        beta = obj.get("beta", 60.0)
        gamma = obj.get("gamma", 60.0)
        if changed_angle == "alpha":
            alpha += delta
            beta -= delta / 2
            gamma -= delta / 2
        elif changed_angle == "beta":
            beta += delta
            alpha -= delta / 2
            gamma -= delta / 2
        else:
            gamma += delta
            alpha -= delta / 2
            beta -= delta / 2
        alpha = max(0.01, min(179.9, alpha))
        beta = max(0.01, min(179.9, beta))
        gamma = max(0.01, min(179.9, gamma))
        total = alpha + beta + gamma
        if abs(total - 180.0) > 0.01:
            diff = 180.0 - total
            alpha += diff / 3
            beta += diff / 3
            gamma += diff / 3
            alpha = max(0.01, min(179.9, alpha))
            beta = max(0.01, min(179.9, beta))
            gamma = max(0.01, min(179.9, gamma))
        obj["alpha"] = rnd(alpha)
        obj["beta"] = rnd(beta)
        obj["gamma"] = rnd(gamma)
        self.update_triangle_from_angles(obj)

    def set_triangle_from_points(self, obj, points):
        if len(points) != 3:
            obj["valid"] = False
            return False
        p0, p1, p2 = points
        a = math.hypot(p1[0]-p2[0], p1[1]-p2[1])
        b = math.hypot(p2[0]-p0[0], p2[1]-p0[1])
        c = math.hypot(p0[0]-p1[0], p0[1]-p1[1])
        if a < 1 or b < 1 or c < 1:
            obj["valid"] = False
            return False
        try:
            cos_alpha = (b**2 + c**2 - a**2) / (2 * b * c)
            cos_alpha = max(-1, min(1, cos_alpha))
            alpha = math.degrees(math.acos(cos_alpha))
            cos_beta = (a**2 + c**2 - b**2) / (2 * a * c)
            cos_beta = max(-1, min(1, cos_beta))
            beta = math.degrees(math.acos(cos_beta))
            gamma = 180 - alpha - beta
        except:
            obj["valid"] = False
            return False
        valid, angles = self.validate_triangle_angles(alpha, beta, gamma)
        if not valid:
            obj["valid"] = False
            return False
        alpha, beta, gamma = angles

        cx = (p0[0] + p1[0] + p2[0]) / 3
        cy = (p0[1] + p1[1] + p2[1]) / 3

        dx_a = p2[0] - p1[0]
        dy_a = p2[1] - p1[1]
        angle = math.degrees(math.atan2(dy_a, dx_a))

        obj["x"] = rnd(cx)
        obj["y"] = rnd(cy)
        obj["angle"] = rnd(angle)
        obj["a"] = rnd(a)
        obj["b"] = rnd(b)
        obj["c"] = rnd(c)
        obj["alpha"] = rnd(alpha)
        obj["beta"] = rnd(beta)
        obj["gamma"] = rnd(gamma)
        obj["valid"] = True
        return True

    def get_triangle_vertices(self, obj):
        x = obj["x"]
        y = obj["y"]
        a = obj.get("a", 60)
        b = obj.get("b", 60)
        c = obj.get("c", 60)
        if a < 1 or b < 1 or c < 1:
            return None
        xC = (a**2 + c**2 - b**2) / (2 * a)
        yC = math.sqrt(max(0, c**2 - xC**2))
        cx = (0 + a + xC) / 3
        cy = (0 + 0 + yC) / 3
        A = (0 - cx, 0 - cy)
        B = (a - cx, 0 - cy)
        C = (xC - cx, yC - cy)
        angle = math.radians(obj.get("angle", 0))
        def rotate(p):
            px, py = p
            rx = px * math.cos(angle) - py * math.sin(angle)
            ry = px * math.sin(angle) + py * math.cos(angle)
            return rx, ry
        A_rot = rotate(A)
        B_rot = rotate(B)
        C_rot = rotate(C)
        return (x + A_rot[0], y + A_rot[1]), (x + B_rot[0], y + B_rot[1]), (x + C_rot[0], y + C_rot[1])

    def get_rect_corners(self, obj):
        x = obj["x"]
        y = obj["y"]
        w = obj.get("width", 60)
        h = obj.get("height", 40)
        angle = math.radians(obj.get("angle", 0))
        corners = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
        result = []
        for dx, dy in corners:
            rx = dx * math.cos(angle) - dy * math.sin(angle)
            ry = dx * math.sin(angle) + dy * math.cos(angle)
            result.append((x + rx, y + ry))
        return result

    def get_triangle_part_at_pos(self, wx, wy, threshold=20):
        for idx in self.selected_indices:
            obj = self.map_data["objects"][idx]
            if obj.get("type") != "triangle":
                continue
            if not obj.get("valid", True):
                continue
            if obj.get("group_id") is not None:
                abs_x, abs_y, _ = self.get_abs_transform(idx)
                orig_x, orig_y = obj.get("x", 0), obj.get("y", 0)
                obj["x"], obj["y"] = abs_x, abs_y
                vertices = self.get_triangle_vertices(obj)
                obj["x"], obj["y"] = orig_x, orig_y
            else:
                vertices = self.get_triangle_vertices(obj)
            if not vertices:
                continue
            for i, (vx, vy) in enumerate(vertices):
                if math.hypot(wx - vx, wy - vy) < threshold:
                    return idx, "vertex", i
            sides = [
                ((vertices[0][0]+vertices[1][0])/2, (vertices[0][1]+vertices[1][1])/2),
                ((vertices[1][0]+vertices[2][0])/2, (vertices[1][1]+vertices[2][1])/2),
                ((vertices[2][0]+vertices[0][0])/2, (vertices[2][1]+vertices[0][1])/2)
            ]
            for i, (sx, sy) in enumerate(sides):
                if math.hypot(wx - sx, wy - sy) < threshold:
                    return idx, "side", i
        return None, None, None

    # ====== Группы ======
    def get_group_members(self, group_id):
        members = []
        for i, obj in enumerate(self.map_data["objects"]):
            if obj.get("group_id") == group_id or (obj.get("is_group") and obj.get("id") == group_id):
                members.append(i)
        return members

    def select_object_with_children(self, idx):
        obj = self.map_data["objects"][idx]
        if obj.get("is_group"):
            group_id = obj.get("id")
            members = self.get_group_members(group_id)
            self.selected_indices = members
        else:
            self.selected_indices = [idx]
        if self.selected_indices:
            obj0 = self.map_data["objects"][self.selected_indices[0]]
            col = obj0.get("color", (255,0,0))
            if isinstance(col, str):
                col = pygame.Color(col)
            if isinstance(col, tuple):
                self.rgb_sliders = list(col[:3])

    def create_dummy_group(self, x, y):
        self.group_counter += 1
        group_id = self.group_counter
        self.dummy_counter += 1
        main_obj = {
            "type": "dummy",
            "x": x,
            "y": y,
            "color": (0, 255, 0),
            "angle": 0,
            "name": f"UNDGmain: Заглушка {self.dummy_counter}",
            "is_group": True,
            "id": group_id,
            "children": [],
            "collapsed": False,
            "local_x": 0,
            "local_y": 0,
            "local_angle": 0,
            "dummy": True,
            "is_main": True
        }
        self.map_data["objects"].append(main_obj)
        main_idx = len(self.map_data["objects"]) - 1
        self.group_main[group_id] = main_idx
        self.selected_indices = [main_idx]
        self.rgb_sliders = [0, 255, 0]
        return main_idx

    def create_group_from_parent(self, parent_idx, child_type, dummy=False):
        """
        Создаёт дочерний объект (типа child_type) внутри группы.
        Если родитель ещё не является группой, он становится главным (UNDGmain),
        а новый объект – дочерним (UNDGobj).
        Если родитель уже группа, новый объект добавляется как дочерний.
        """
        parent = self.map_data["objects"][parent_idx]

        # Определяем, является ли родитель уже группой
        if parent.get("is_group"):
            # Родитель уже группа – добавляем дочерний объект
            group_id = parent["id"]
            self.object_counter += 1
            new_obj = self._create_object_data(child_type, parent["x"], parent["y"], parent.get("color", (255,0,0)), dummy)
            new_obj["group_id"] = group_id
            new_obj["local_x"] = 0.0
            new_obj["local_y"] = 0.0
            new_obj["local_angle"] = 0.0
            new_obj["name"] = f"UNDGobj: {new_obj.get('name', 'Объект')}"
            new_obj["is_main"] = False
            self.map_data["objects"].append(new_obj)
            new_idx = len(self.map_data["objects"]) - 1
            parent["children"].append(new_idx)
            self.selected_indices = [new_idx]
            self.rgb_sliders = list(parent["color"][:3])
            return new_idx
        else:
            # Родитель не группа – превращаем его в группу, он становится главным
            self.group_counter += 1
            group_id = self.group_counter
            # Преобразуем родителя в группу
            parent["is_group"] = True
            parent["id"] = group_id
            parent["children"] = []
            parent["collapsed"] = False
            parent["is_main"] = True
            # Переименовываем родителя в UNDGmain
            old_name = parent.get("name", "Объект")
            if not old_name.startswith("UNDGmain:"):
                parent["name"] = f"UNDGmain: {old_name}"
            parent["local_x"] = 0.0
            parent["local_y"] = 0.0
            parent["local_angle"] = 0.0
            # Создаём новый дочерний объект
            self.object_counter += 1
            new_obj = self._create_object_data(child_type, parent["x"], parent["y"], parent.get("color", (255,0,0)), dummy)
            new_obj["group_id"] = group_id
            new_obj["local_x"] = 0.0
            new_obj["local_y"] = 0.0
            new_obj["local_angle"] = 0.0
            new_obj["name"] = f"UNDGobj: {new_obj.get('name', 'Объект')}"
            new_obj["is_main"] = False
            self.map_data["objects"].append(new_obj)
            new_idx = len(self.map_data["objects"]) - 1
            parent["children"].append(new_idx)
            self.group_main[group_id] = parent_idx
            self.selected_indices = [new_idx]
            self.rgb_sliders = list(parent["color"][:3])
            return new_idx

    def _create_object_data(self, obj_type, x, y, color, dummy=False):
        """Вспомогательная функция для создания словаря объекта."""
        obj = {
            "type": obj_type,
            "x": x,
            "y": y,
            "color": color,
            "angle": 0,
            "name": f"Объект {self.object_counter}",
            "children": [],
            "parent": None,
            "group_id": None,
            "is_group": False,
            "collapsed": False,
            "local_x": 0,
            "local_y": 0,
            "local_angle": 0,
            "dummy": dummy,
            "is_main": False
        }
        if dummy:
            obj["dummy"] = True
            obj["type"] = "dummy"
            obj["color"] = (0, 255, 0)
            obj["name"] = f"Заглушка {self.dummy_counter}"
            self.dummy_counter += 1
            return obj

        if obj_type in ("circle", "nocollide_circle"):
            obj["radius"] = self.new_radius
        elif obj_type in ("rect", "nocollide_rect"):
            obj["width"] = self.new_width
            obj["height"] = self.new_height
        elif obj_type == "triangle":
            obj["a"] = self.new_a
            obj["b"] = self.new_b
            obj["c"] = self.new_c
            obj["alpha"] = self.new_alpha
            obj["beta"] = self.new_beta
            obj["gamma"] = self.new_gamma
            valid, angles = self.validate_triangle_angles(self.new_alpha, self.new_beta, self.new_gamma)
            if valid:
                a = self.new_a
                alpha, beta, gamma = angles
                sides = self.compute_triangle_sides(a, alpha, beta, gamma)
                if sides is not None:
                    b, c = sides
                    obj["a"] = rnd(a)
                    obj["b"] = rnd(b)
                    obj["c"] = rnd(c)
                    obj["alpha"] = rnd(alpha)
                    obj["beta"] = rnd(beta)
                    obj["gamma"] = rnd(gamma)
                    obj["valid"] = True
                else:
                    obj["valid"] = False
            else:
                obj["valid"] = False
        return obj

    def get_display_name(self, obj):
        if obj.get("dummy"):
            return obj.get("name", "UNDGmain: Заглушка")
        if obj.get("is_group"):
            return obj.get("name", "UNDGmain")
        if obj.get("group_id") is not None:
            return obj.get("name", "UNDGobj")
        return obj.get("name", "Объект")

    # ====== Отрисовка ======
    def draw_object(self, obj, idx):
        # Заглушка рисуется только в редакторе (игнорируется при сохранении)
        if obj.get("dummy"):
            # Рисуем зелёный ромб
            if obj.get("group_id") is not None and not obj.get("is_group"):
                abs_x, abs_y, _ = self.get_abs_transform(idx)
            else:
                abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
            sx, sy = self.world_to_screen(abs_x, abs_y)
            # Ромб
            size = 12 * self.zoom
            points = [(sx, sy-size), (sx+size, sy), (sx, sy+size), (sx-size, sy)]
            pygame.draw.polygon(self.screen, COLOR_DUMMY, points, 2)
            # Свечение
            glow = pygame.Surface((int(size*2.5), int(size*2.5)), pygame.SRCALPHA)
            pygame.draw.polygon(glow, (0, 255, 0, 50), [(glow.get_width()/2, 0), (glow.get_width(), glow.get_height()/2), (glow.get_width()/2, glow.get_height()), (0, glow.get_height()/2)])
            self.screen.blit(glow, (sx - glow.get_width()/2, sy - glow.get_height()/2))
            # Выделение
            if idx in self.selected_indices:
                pygame.draw.circle(self.screen, COLOR_SELECT, (sx, sy), 8, 2)
            if idx == self.hover_index:
                pygame.draw.circle(self.screen, COLOR_HOVER, (sx, sy), 6, 1)
            return

        if obj.get("group_id") is not None and not obj.get("is_group"):
            abs_x, abs_y, abs_angle = self.get_abs_transform(idx)
            orig_x, orig_y, orig_angle = obj.get("x", 0), obj.get("y", 0), obj.get("angle", 0)
            obj["x"], obj["y"], obj["angle"] = abs_x, abs_y, abs_angle
            self._draw_object_raw(obj, idx)
            obj["x"], obj["y"], obj["angle"] = orig_x, orig_y, orig_angle
        else:
            self._draw_object_raw(obj, idx)

    def _draw_object_raw(self, obj, idx):
        x = obj["x"]
        y = obj["y"]
        sx, sy = self.world_to_screen(x, y)
        color = obj.get("color", (255, 0, 0))
        if isinstance(color, str):
            color = pygame.Color(color)
        if not isinstance(color, tuple):
            color = tuple(color)

        selected = (idx in self.selected_indices)
        hover = (idx == self.hover_index)
        obj_type = obj.get("type", "circle")
        angle = obj.get("angle", 0)

        is_nocollide = obj_type in ("nocollide_rect", "nocollide_circle")

        if obj_type == "circle":
            radius = obj.get("radius", 30) * self.zoom
            if radius > 1:
                pygame.draw.circle(self.screen, color, (sx, sy), int(radius))
                if selected and (self.hover_resize or self.resizing):
                    pygame.draw.circle(self.screen, COLOR_RESIZE, (sx, sy), int(radius), 2)
                if is_nocollide and not obj.get("image"):
                    pygame.draw.circle(self.screen, COLOR_SELECT, (sx, sy), int(radius)+2, 2)
        elif obj_type == "rect":
            w = obj.get("width", 60) * self.zoom
            h = obj.get("height", 40) * self.zoom
            if w > 1 and h > 1:
                if angle != 0:
                    surf = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
                    surf.fill((0,0,0,0))
                    pygame.draw.rect(surf, color, (0,0,int(w),int(h)))
                    rot_surf = pygame.transform.rotate(surf, -angle)
                    self.screen.blit(rot_surf, (sx - rot_surf.get_width()/2, sy - rot_surf.get_height()/2))
                else:
                    pygame.draw.rect(self.screen, color, (sx - w/2, sy - h/2, w, h))
                if is_nocollide and not obj.get("image"):
                    pygame.draw.rect(self.screen, COLOR_SELECT, (sx - w/2 - 2, sy - h/2 - 2, w+4, h+4), 2)
            if selected:
                corners = self.get_rect_corners(obj)
                top_center = ((corners[0][0]+corners[1][0])/2, (corners[0][1]+corners[1][1])/2)
                bottom_center = ((corners[3][0]+corners[2][0])/2, (corners[3][1]+corners[2][1])/2)
                left_center = ((corners[0][0]+corners[3][0])/2, (corners[0][1]+corners[3][1])/2)
                right_center = ((corners[1][0]+corners[2][0])/2, (corners[1][1]+corners[2][1])/2)
                for (cx, cy) in [top_center, bottom_center, left_center, right_center]:
                    scx, scy = self.world_to_screen(cx, cy)
                    pygame.draw.circle(self.screen, COLOR_MARKER, (int(scx), int(scy)), 5, 1)
                for (cx, cy) in [top_center, bottom_center]:
                    scx, scy = self.world_to_screen(cx, cy)
                    label = self.font_small.render("a", True, COLOR_LABEL)
                    self.screen.blit(label, (scx - 5, scy - 10))
                for (cx, cy) in [left_center, right_center]:
                    scx, scy = self.world_to_screen(cx, cy)
                    label = self.font_small.render("b", True, COLOR_LABEL)
                    self.screen.blit(label, (scx - 5, scy - 10))
        elif obj_type == "triangle":
            if not obj.get("valid", True):
                return
            vertices = self.get_triangle_vertices(obj)
            if not vertices:
                return
            sv = [self.world_to_screen(vx, vy) for vx, vy in vertices]
            pygame.draw.polygon(self.screen, color, sv)

            if selected and self.resizing and self.resize_type == "triangle_vertex" and self.resize_index == idx:
                temp_vx = self.resize_data.get("current_vx", vertices[0][0])
                temp_vy = self.resize_data.get("current_vy", vertices[0][1])
                other_vertices = [v for i, v in enumerate(vertices) if i != self.resize_data["vertex_idx"]]
                temp_points = []
                for p in [other_vertices[0], other_vertices[1], (temp_vx, temp_vy)]:
                    sp = self.world_to_screen(p[0], p[1])
                    temp_points.append(sp)
                if len(temp_points) == 3:
                    pygame.draw.polygon(self.screen, COLOR_TEMP, temp_points, 1)

            if selected:
                for (vx, vy) in sv:
                    pygame.draw.circle(self.screen, COLOR_ANGLE, (int(vx), int(vy)), 6, 2)
                A, B, C = vertices
                mid_ab = ((A[0]+B[0])/2, (A[1]+B[1])/2)
                mid_bc = ((B[0]+C[0])/2, (B[1]+C[1])/2)
                mid_ca = ((C[0]+A[0])/2, (C[1]+A[1])/2)
                for (label, (cx, cy)) in [("a", mid_ab), ("b", mid_bc), ("c", mid_ca)]:
                    scx, scy = self.world_to_screen(cx, cy)
                    pygame.draw.circle(self.screen, COLOR_MARKER, (int(scx), int(scy)), 5, 1)
                    lab = self.font_small.render(label, True, COLOR_LABEL)
                    self.screen.blit(lab, (scx - 5, scy - 10))
                angle_labels = [("α", A), ("β", B), ("γ", C)]
                for (label, (vx, vy)) in angle_labels:
                    scx, scy = self.world_to_screen(vx, vy)
                    offset_x, offset_y = 20, -20
                    lab = self.font_small.render(label, True, COLOR_LABEL)
                    self.screen.blit(lab, (scx + offset_x, scy + offset_y))
        elif obj_type == "nocollide_rect":
            w = obj.get("width", 60) * self.zoom
            h = obj.get("height", 40) * self.zoom
            if w > 1 and h > 1:
                if angle != 0:
                    surf = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
                    surf.fill((0,0,0,0))
                    pygame.draw.rect(surf, color, (0,0,int(w),int(h)))
                    rot_surf = pygame.transform.rotate(surf, -angle)
                    self.screen.blit(rot_surf, (sx - rot_surf.get_width()/2, sy - rot_surf.get_height()/2))
                else:
                    pygame.draw.rect(self.screen, color, (sx - w/2, sy - h/2, w, h))
                if not obj.get("image"):
                    pygame.draw.rect(self.screen, COLOR_SELECT, (sx - w/2 - 2, sy - h/2 - 2, w+4, h+4), 2)
            if selected:
                corners = self.get_rect_corners(obj)
                top_center = ((corners[0][0]+corners[1][0])/2, (corners[0][1]+corners[1][1])/2)
                bottom_center = ((corners[3][0]+corners[2][0])/2, (corners[3][1]+corners[2][1])/2)
                left_center = ((corners[0][0]+corners[3][0])/2, (corners[0][1]+corners[3][1])/2)
                right_center = ((corners[1][0]+corners[2][0])/2, (corners[1][1]+corners[2][1])/2)
                for (cx, cy) in [top_center, bottom_center, left_center, right_center]:
                    scx, scy = self.world_to_screen(cx, cy)
                    pygame.draw.circle(self.screen, COLOR_MARKER, (int(scx), int(scy)), 5, 1)
        elif obj_type == "nocollide_circle":
            radius = obj.get("radius", 30) * self.zoom
            if radius > 1:
                pygame.draw.circle(self.screen, color, (sx, sy), int(radius))
                if not obj.get("image"):
                    pygame.draw.circle(self.screen, COLOR_SELECT, (sx, sy), int(radius)+2, 2)
            if selected:
                pygame.draw.circle(self.screen, COLOR_MARKER, (sx, sy), 5, 1)

        if selected:
            pygame.draw.circle(self.screen, COLOR_SELECT, (sx, sy), 8, 2)
        if hover and not selected:
            pygame.draw.circle(self.screen, COLOR_HOVER, (sx, sy), 6, 1)

    def draw_grid(self):
        step = 50 * self.zoom
        left = self.camera_x
        top = self.camera_y
        right = left + (self.screen_width - PANEL_WIDTH - (RIGHT_PANEL_WIDTH if self.right_panel_visible else 0)) / self.zoom
        bottom = top + self.screen_height / self.zoom
        start_x = int(left // step) * step
        start_y = int(top // step) * step
        for x in range(int(start_x), int(right + step), int(step)):
            sx, sy = self.world_to_screen(x, 0)
            pygame.draw.line(self.screen, COLOR_GRID, (sx, 0), (sx, self.screen_height), 1)
        for y in range(int(start_y), int(bottom + step), int(step)):
            sx, sy = self.world_to_screen(0, y)
            pygame.draw.line(self.screen, COLOR_GRID, (0, sy), (self.screen_width, sy), 1)

        w, h = self.map_data["width"], self.map_data["height"]
        x1, y1 = self.world_to_screen(0, 0)
        x2, y2 = self.world_to_screen(w, h)
        pygame.draw.rect(self.screen, COLOR_WHITE, (x1, y1, x2-x1, y2-y1), 2)

    def draw_cursor(self):
        mx, my = pygame.mouse.get_pos()
        if mx < PANEL_WIDTH:
            return
        if mx > self.screen_width - RIGHT_PANEL_WIDTH and self.right_panel_visible:
            return
        size = 12
        gap = 4
        pygame.draw.line(self.screen, COLOR_CURSOR, (mx - size, my), (mx - gap, my), 1)
        pygame.draw.line(self.screen, COLOR_CURSOR, (mx + gap, my), (mx + size, my), 1)
        pygame.draw.line(self.screen, COLOR_CURSOR, (mx, my - size), (mx, my - gap), 1)
        pygame.draw.line(self.screen, COLOR_CURSOR, (mx, my + gap), (mx, my + size), 1)
        pygame.draw.circle(self.screen, COLOR_CURSOR, (mx, my), 2)

    def draw_right_panel(self):
        if not self.right_panel_visible:
            trigger_rect = pygame.Rect(self.screen_width - RIGHT_PANEL_TRIGGER_WIDTH, 0, RIGHT_PANEL_TRIGGER_WIDTH, self.screen_height)
            pygame.draw.rect(self.screen, COLOR_RIGHT_PANEL_TRIGGER, trigger_rect)
            return

        panel = self.right_panel_rect
        pygame.draw.rect(self.screen, COLOR_RIGHT_PANEL_BG, panel)
        pygame.draw.line(self.screen, COLOR_RIGHT_PANEL_BORDER, (panel.x, 0), (panel.x, self.screen_height), 2)

        title = self.font.render("Объекты", True, COLOR_WHITE)
        self.screen.blit(title, (panel.x + 10, 10))

        objects = self.map_data["objects"]
        if not objects:
            text = self.font_small.render("Нет объектов", True, COLOR_GRAY)
            self.screen.blit(text, (panel.x + 10, 50))
            return

        display_items = []
        for i, obj in enumerate(objects):
            if obj.get("is_group"):
                display_items.append((i, 0, True, obj.get("collapsed", False)))
                if not obj.get("collapsed", False):
                    children = obj.get("children", [])
                    for child_idx in children:
                        # Проверяем, что дочерний индекс существует в objects
                        if child_idx < len(objects):
                            display_items.append((child_idx, 1, False, False))
            else:
                if obj.get("group_id") is None:
                    display_items.append((i, 0, False, False))

        item_height = self.right_panel_item_height
        padding = self.right_panel_padding
        list_start_y = 40
        list_height = self.screen_height - list_start_y - 10
        max_visible = list_height // (item_height + padding)
        total_items = len(display_items)
        max_scroll = max(0, total_items - max_visible)
        scroll = max(0, min(max_scroll, self.right_panel_scroll))

        start_idx = scroll
        end_idx = min(total_items, start_idx + max_visible + 1)

        y = list_start_y
        for item_idx in range(start_idx, end_idx):
            if item_idx >= len(display_items):
                break
            idx, indent, is_group, is_collapsed = display_items[item_idx]
            if idx >= len(objects):
                continue  # пропускаем невалидный индекс
            obj = objects[idx]
            display_name = self.get_display_name(obj)
            prefix = "  " * indent
            full_name = f"{prefix}{display_name}"

            is_selected = (idx in self.selected_indices)
            is_hover = (idx == self.right_panel_drag_index)

            rect = pygame.Rect(panel.x + 5 + indent * INDENT_WIDTH, y, panel.width - 10 - indent * INDENT_WIDTH, item_height)
            if is_selected:
                pygame.draw.rect(self.screen, COLOR_RIGHT_PANEL_ITEM_SELECTED, rect)
            elif is_hover:
                pygame.draw.rect(self.screen, COLOR_RIGHT_PANEL_ITEM_HOVER, rect)
            else:
                pygame.draw.rect(self.screen, COLOR_RIGHT_PANEL_ITEM, rect)

            if is_group:
                arrow = "▼" if not is_collapsed else "▶"
                arrow_surf = self.font_small.render(arrow, True, COLOR_GROUP_EXPAND)
                self.screen.blit(arrow_surf, (rect.x + 5, rect.y + 4))
                text_x = rect.x + 25
            else:
                text_x = rect.x + 5

            if self.right_panel_rename_index == idx:
                input_rect = pygame.Rect(text_x, rect.y + 2, rect.width - (text_x - rect.x) - 10, item_height - 4)
                pygame.draw.rect(self.screen, COLOR_WHITE, input_rect, 1)
                rename_surf = self.font_small.render(self.right_panel_rename_text, True, COLOR_WHITE)
                self.screen.blit(rename_surf, (input_rect.x + 5, input_rect.y + 4))
            else:
                text_surf = self.font_small.render(full_name, True, COLOR_WHITE)
                self.screen.blit(text_surf, (text_x, rect.y + 4))

            y += item_height + padding

        if total_items > max_visible:
            scrollbar_height = list_height
            thumb_height = max(20, list_height * (max_visible / total_items))
            thumb_y = list_start_y + (list_height - thumb_height) * (scroll / max_scroll)
            pygame.draw.rect(self.screen, COLOR_GRAY, (panel.x + panel.width - 8, list_start_y, 4, list_height))
            pygame.draw.rect(self.screen, COLOR_WHITE, (panel.x + panel.width - 8, thumb_y, 4, thumb_height))

    def draw_panel(self):
        panel = self.panel_rect
        pygame.draw.rect(self.screen, COLOR_PANEL, panel)
        pygame.draw.line(self.screen, COLOR_GRAY, (panel.right, 0), (panel.right, self.screen_height), 2)

        y = 10
        title = self.font_bold.render("Редактор карт", True, COLOR_WHITE)
        self.screen.blit(title, (10, y))
        y += 35

        icon_types = [
            ("Круг", "circle", 1),
            ("Прямоугольник", "rect", 2),
            ("Треугольник", "triangle", 3),
            ("Прям. без колл.", "nocollide_rect", 4),
            ("Круг без колл.", "nocollide_circle", 5),
            ("Заглушка", "dummy", 6)
        ]
        x_icon = 10
        self.icon_rects = []
        for label, typ, key in icon_types:
            rect = pygame.Rect(x_icon, y, ICON_SIZE, ICON_SIZE)
            self.icon_rects.append((rect, typ))
            if self.new_object_type == typ:
                pygame.draw.rect(self.screen, COLOR_SELECT, rect)
            else:
                pygame.draw.rect(self.screen, COLOR_GRAY, rect)
            center = rect.center
            if typ == "circle":
                pygame.draw.circle(self.screen, COLOR_WHITE, center, 10, 2)
            elif typ == "rect":
                pygame.draw.rect(self.screen, COLOR_WHITE, (center[0]-12, center[1]-8, 24, 16), 2)
            elif typ == "triangle":
                pts = [(center[0], center[1]-12), (center[0]-12, center[1]+10), (center[0]+12, center[1]+10)]
                pygame.draw.polygon(self.screen, COLOR_WHITE, pts, 2)
            elif typ == "nocollide_rect":
                pygame.draw.rect(self.screen, COLOR_WHITE, (center[0]-12, center[1]-8, 24, 16), 2)
                pygame.draw.circle(self.screen, COLOR_SELECT, center, 4, 1)
            elif typ == "nocollide_circle":
                pygame.draw.circle(self.screen, COLOR_WHITE, center, 10, 2)
                pygame.draw.circle(self.screen, COLOR_SELECT, center, 4, 1)
            elif typ == "dummy":
                pygame.draw.rect(self.screen, COLOR_GRAY, (center[0]-10, center[1]-10, 20, 20))
                pygame.draw.line(self.screen, COLOR_WHITE, (center[0]-8, center[1]-8), (center[0]+8, center[1]+8), 2)
                pygame.draw.line(self.screen, COLOR_WHITE, (center[0]+8, center[1]-8), (center[0]-8, center[1]+8), 2)
            num_text = self.font_small.render(str(key), True, COLOR_YELLOW)
            self.screen.blit(num_text, (rect.x+2, rect.y+2))
            x_icon += ICON_SIZE + 5

        y += ICON_SIZE + 10
        pygame.draw.line(self.screen, COLOR_GRAY, (5, y), (panel.width-5, y), 1)
        y += 10

        menu_items = []
        if self.selected_indices:
            main_idx = self.selected_indices[0]
            if main_idx < len(self.map_data["objects"]):
                main_obj = self.map_data["objects"][main_idx]
                menu_items.append((main_obj, main_idx, True))
                if main_obj.get("is_group"):
                    children = main_obj.get("children", [])
                    for child_idx in children:
                        if child_idx < len(self.map_data["objects"]):
                            child_obj = self.map_data["objects"][child_idx]
                            menu_items.append((child_obj, child_idx, False))

        panel_scroll = self.panel_scroll
        item_height = 28
        spacing = 5
        total_height = 0
        for obj, idx, sel in menu_items:
            total_height += self.get_menu_height(obj)
        max_scroll = max(0, total_height - (self.screen_height - y - 50))
        panel_scroll = max(0, min(max_scroll, panel_scroll))

        self.collapse_buttons = []

        current_y = y - panel_scroll
        for obj, idx, is_selected in menu_items:
            header_rect = pygame.Rect(10, current_y, panel.width-20, 24)
            pygame.draw.rect(self.screen, COLOR_GRAY if not is_selected else COLOR_SELECT, header_rect)
            name = self.get_display_name(obj)
            name_surf = self.font_small.render(name, True, COLOR_WHITE)
            self.screen.blit(name_surf, (15, current_y+4))
            if obj.get("is_group"):
                collapse_rect = pygame.Rect(panel.width-30, current_y+2, 20, 20)
                self.collapse_buttons.append((collapse_rect, idx))
                if obj.get("collapsed", False):
                    arrow = "▶"
                else:
                    arrow = "▼"
                arrow_surf = self.font_small.render(arrow, True, COLOR_YELLOW)
                self.screen.blit(arrow_surf, (collapse_rect.x+4, collapse_rect.y+2))
            current_y += 24

            show_params = True
            if obj.get("is_group") and obj.get("collapsed", False) and not is_selected:
                show_params = False
            if show_params:
                self.draw_object_properties(obj, idx, current_y, panel)
                current_y += self.get_menu_height(obj) - 24

            current_y += spacing

        self.panel_scroll = panel_scroll

        # Кнопка "Создать дочерний объект" — перенесена в самый низ, перед нижними кнопками
        bottom_y = self.screen_height - 190

        if self.selected_indices:
            first_idx = self.selected_indices[0]
            if first_idx < len(self.map_data["objects"]):
                first_obj = self.map_data["objects"][first_idx]
                if (first_obj.get("group_id") is None and not first_obj.get("is_group")) or first_obj.get("is_group"):
                    btn_y = bottom_y - 40
                    btn_rect = pygame.Rect(10, btn_y, panel.width-20, 28)
                    self.button_rects.append((btn_rect, "create_child"))
                    pygame.draw.rect(self.screen, COLOR_GRAY, btn_rect)
                    if first_obj.get("is_group"):
                        label = "Создать дочерний объект"
                    else:
                        label = "Создать объект подгруппы"
                    self.draw_text(label, 15, btn_y+5, COLOR_WHITE)

        # Нижние кнопки (F1, F2, ...)
        y = bottom_y
        btn_labels = [
            ("F1 Справка", "help"),
            ("F2 Размер карты", "resize"),
            ("F5 Запустить игру", "run"),
            ("F6 Сохранить как", "saveas"),
            ("F7 Перезаписать", "overwrite"),
        ]
        for label, action in btn_labels:
            rect = pygame.Rect(10, y, 200, 28)
            self.button_rects.append((rect, action))
            pygame.draw.rect(self.screen, COLOR_GRAY, rect)
            self.draw_text(label, 15, y+5, COLOR_WHITE)
            y += 32

        exit_rect = pygame.Rect(10, y, 200, 28)
        self.button_rects.append((exit_rect, "exit"))
        pygame.draw.rect(self.screen, COLOR_RED, exit_rect)
        self.draw_text("Выход", 15, y+5, COLOR_WHITE)

    def get_menu_height(self, obj):
        if obj.get("dummy"):
            return 60
        if obj.get("is_group") and obj.get("collapsed", False):
            return 30
        height = 30
        obj_type = obj.get("type")
        if obj_type in ("circle", "nocollide_circle"):
            height += 25
        elif obj_type in ("rect", "nocollide_rect"):
            height += 50
        elif obj_type == "triangle":
            height += 150
        height += 60
        return height

    def draw_object_properties(self, obj, idx, y, panel):
        self.param_rects = []
        self.color_rects = []
        self.slider_rects = []
        self.checkbox_rect = None

        x = 10
        if obj.get("group_id") is not None and not obj.get("is_group"):
            lx = obj.get("local_x", 0)
            ly = obj.get("local_y", 0)
            self.draw_text(f"Лок. позиция: ({rnd(lx)}, {rnd(ly)})", x, y, COLOR_WHITE)
            y += 22
            self.draw_parameter("Лок. X", lx, x, y, "local_x", idx)
            y += 22
            self.draw_parameter("Лок. Y", ly, x, y, "local_y", idx)
            y += 22
            la = obj.get("local_angle", 0)
            self.draw_parameter("Лок. угол", la, x, y, "local_angle", idx)
            y += 22
        else:
            px = obj.get("x", 0)
            py = obj.get("y", 0)
            self.draw_text(f"Позиция: ({rnd(px)}, {rnd(py)})", x, y, COLOR_WHITE)
            y += 22
            angle_val = rnd(obj.get("angle", 0))
            self.draw_parameter("Угол", angle_val, x, y, "angle", idx)
            y += 22

        if not obj.get("dummy"):
            self.draw_text("Цвет:", x, y, COLOR_WHITE)
            y += 22
            bx = x
            self.color_rects = []
            for col in self.base_colors:
                rect = pygame.Rect(bx, y, COLOR_BOX_SIZE, COLOR_BOX_SIZE)
                self.color_rects.append((rect, col))
                pygame.draw.rect(self.screen, col, rect)
                pygame.draw.rect(self.screen, COLOR_WHITE, rect, 1)
                bx += COLOR_BOX_SIZE + 4
            y += COLOR_BOX_SIZE + 8

            self.draw_text("RGB:", x, y, COLOR_WHITE)
            y += 20
            self.slider_rects = []
            for i, label in enumerate(["R", "G", "B"]):
                val = self.rgb_sliders[i]
                self.draw_text(label, x, y, COLOR_WHITE)
                slider_rect = pygame.Rect(x+25, y+2, SLIDER_WIDTH, SLIDER_HEIGHT)
                self.slider_rects.append((slider_rect, i))
                pygame.draw.rect(self.screen, COLOR_GRAY, slider_rect)
                fill_w = int((val / 255) * SLIDER_WIDTH)
                fill_rect = pygame.Rect(slider_rect.x, slider_rect.y, fill_w, SLIDER_HEIGHT)
                col = [0,0,0]; col[i]=255
                pygame.draw.rect(self.screen, tuple(col), fill_rect)
                knob_x = slider_rect.x + fill_w - 3
                pygame.draw.circle(self.screen, COLOR_WHITE, (knob_x, slider_rect.centery), 5)
                param_key = f"r" if i==0 else "g" if i==1 else "b"
                self.draw_parameter("", val, x+130, y, param_key, idx)
                y += 20
            y += 5

        if not obj.get("dummy"):
            self.draw_text("Параметры:", x, y, COLOR_WHITE)
            y += 22
            obj_type = obj.get("type", "circle")
            if obj_type in ("circle", "nocollide_circle"):
                radius = rnd(obj.get("radius", 30))
                self.draw_parameter("Радиус", radius, x, y, "radius", idx)
                y += 22
            elif obj_type in ("rect", "nocollide_rect"):
                width = rnd(obj.get("width", 60))
                height = rnd(obj.get("height", 40))
                self.draw_parameter("Ширина", width, x, y, "width", idx)
                y += 22
                self.draw_parameter("Высота", height, x, y, "height", idx)
                y += 22
            elif obj_type == "triangle":
                a = rnd(obj.get("a", 60.0))
                b = rnd(obj.get("b", 60.0))
                c = rnd(obj.get("c", 60.0))
                alpha = rnd(obj.get("alpha", 60.0))
                beta = rnd(obj.get("beta", 60.0))
                gamma = rnd(obj.get("gamma", 60.0))
                self.draw_parameter("a", f"{a:.2f}", x, y, "a", idx)
                y += 22
                self.draw_parameter("b", f"{b:.2f}", x, y, "b", idx)
                y += 22
                self.draw_parameter("c", f"{c:.2f}", x, y, "c", idx)
                y += 22
                self.draw_parameter("α", f"{alpha:.2f}", x, y, "alpha", idx)
                y += 22
                self.draw_parameter("β", f"{beta:.2f}", x, y, "beta", idx)
                y += 22
                self.draw_parameter("γ", f"{gamma:.2f}", x, y, "gamma", idx)
                y += 22
                self.draw_text("Тонкая настройка", x, y, COLOR_WHITE)
                check_rect = pygame.Rect(x+130, y, 20, 20)
                self.checkbox_rect = check_rect
                pygame.draw.rect(self.screen, COLOR_WHITE, check_rect, 1)
                if self.fine_tune:
                    pts = [(x+135, y+6), (x+140, y+14), (x+150, y+4)]
                    pygame.draw.lines(self.screen, COLOR_GREEN, False, pts, 2)
                y += 30
        self.draw_text("Поворот: Num4 (-5°)  Num6 (+5°)", x, y, COLOR_GRAY)
        y += 30
        self._last_y = y

    def draw_text(self, text, x, y, color):
        surf = self.font_small.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def draw_parameter(self, label, value, x, y, param_key, obj_idx):
        text = f"{label}: {value}" if label else f"{value}"
        if (self.input_active and self.input_param == param_key and
            self.input_obj_index == obj_idx):
            rect = pygame.Rect(x, y-2, 50 if not label else 160, 22)
            self.input_rect = rect
            pygame.draw.rect(self.screen, COLOR_WHITE, rect, 1)
            input_surf = self.font_small.render(self.input_text, True, COLOR_WHITE)
            self.screen.blit(input_surf, (x+4, y))
        else:
            rect = pygame.Rect(x, y-2, 50 if not label else 160, 22)
            self.param_rects.append((rect, param_key, obj_idx))
            self.draw_text(text, x, y, COLOR_WHITE)

    # ====== Обработка событий ======
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == VIDEORESIZE:
                if not self.fullscreen:
                    self.screen_width, self.screen_height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), RESIZABLE | DOUBLEBUF)
                    self.panel_rect.height = self.screen_height
                    self.right_panel_rect = pygame.Rect(self.screen_width - RIGHT_PANEL_WIDTH, 0, RIGHT_PANEL_WIDTH, self.screen_height)
            elif event.type == KEYDOWN:
                self.handle_keydown(event)
            elif event.type == MOUSEBUTTONDOWN:
                self.handle_mouse_down(event)
            elif event.type == MOUSEBUTTONUP:
                self.handle_mouse_up(event)
            elif event.type == MOUSEMOTION:
                self.handle_mouse_motion(event)
            elif event.type == MOUSEWHEEL:
                self.handle_mouse_wheel(event)
            elif event.type == TEXTINPUT:
                if self.input_active:
                    self.input_text += event.text
                elif self.right_panel_rename_index >= 0:
                    self.right_panel_rename_text += event.text

    def handle_keydown(self, event):
        key = event.key
        if key == K_ESCAPE:
            if self.placement_mode:
                # Отмена размещения
                self.placement_mode = False
                self.placement_ghost_obj = None
                return
            if self.input_active:
                self.cancel_input()
            elif self.show_help:
                self.show_help = False
            elif self.resize_input_active:
                self.resize_input_active = False
            elif self.save_as_active:
                self.save_as_active = False
            elif self.right_panel_rename_index >= 0:
                self.right_panel_rename_index = -1
                self.right_panel_rename_text = ""
            elif self.create_child_dialog:
                self.create_child_dialog = False
            return

        if self.right_panel_rename_index >= 0:
            if key == K_RETURN:
                obj = self.map_data["objects"][self.right_panel_rename_index]
                old_name = obj.get("name", "")
                prefix = ""
                if old_name.startswith("UNDGmain:"):
                    prefix = "UNDGmain: "
                elif old_name.startswith("UNDGobj:"):
                    prefix = "UNDGobj: "
                new_text = self.right_panel_rename_text.strip()
                obj["name"] = prefix + new_text if prefix else new_text
                self.right_panel_rename_index = -1
                self.right_panel_rename_text = ""
            elif key == K_ESCAPE:
                self.right_panel_rename_index = -1
                self.right_panel_rename_text = ""
            elif key == K_BACKSPACE:
                self.right_panel_rename_text = self.right_panel_rename_text[:-1]
            return

        if key == K_1:
            self.new_object_type = "circle"
        elif key == K_2:
            self.new_object_type = "rect"
        elif key == K_3:
            self.new_object_type = "triangle"
        elif key == K_4:
            self.new_object_type = "nocollide_rect"
        elif key == K_5:
            self.new_object_type = "nocollide_circle"
        elif key == K_6:
            self.new_object_type = "dummy"
        elif key == K_F3:
            self.create_object()
        elif key == K_KP4:
            self.rotate_selected(-5)
        elif key == K_KP6:
            self.rotate_selected(5)
        elif key == K_F1:
            self.show_help = not self.show_help
        elif key == K_F2:
            self.start_resize()
        elif key == K_F5:
            self.run_game()
        elif key == K_F6:
            self.start_save_as()
        elif key == K_F7:
            self.save_overwrite()
        elif key == K_DELETE:
            self.delete_selected()
        elif key == K_F11:
            self.toggle_fullscreen()

        if self.input_active:
            if key == K_RETURN:
                self.apply_input()
            elif key == K_ESCAPE:
                self.cancel_input()
            elif key == K_BACKSPACE:
                self.input_text = self.input_text[:-1]

    def handle_mouse_down(self, event):
        mx, my = event.pos
        if event.button == 1:
            # Обработка диалогов
            if self.resize_input_active:
                dialog_rect = pygame.Rect(self.screen_width//2 - 150, self.screen_height//2 - 60, 300, 120)
                if dialog_rect.collidepoint(mx, my):
                    ok_rect = pygame.Rect(dialog_rect.x+40, dialog_rect.y+90, 80, 30)
                    cancel_rect = pygame.Rect(dialog_rect.x+180, dialog_rect.y+90, 80, 30)
                    if ok_rect.collidepoint(mx, my):
                        try:
                            w = int(self.resize_width_text)
                            h = int(self.resize_height_text)
                            if w > 10 and h > 10:
                                self.map_data["width"] = w
                                self.map_data["height"] = h
                                self.resize_input_active = False
                        except:
                            pass
                    elif cancel_rect.collidepoint(mx, my):
                        self.resize_input_active = False
                    return
                else:
                    return

            if self.save_as_active:
                dialog_rect = pygame.Rect(self.screen_width//2 - 150, self.screen_height//2 - 50, 300, 100)
                if dialog_rect.collidepoint(mx, my):
                    ok_rect = pygame.Rect(dialog_rect.x+40, dialog_rect.y+90, 80, 30)
                    cancel_rect = pygame.Rect(dialog_rect.x+180, dialog_rect.y+90, 80, 30)
                    if ok_rect.collidepoint(mx, my):
                        name = self.save_as_text.strip()
                        if name:
                            save_objects = [obj for obj in self.map_data["objects"] if not obj.get("dummy")]
                            orig_objects = self.map_data["objects"]
                            self.map_data["objects"] = save_objects
                            self.loader.save_map(self.map_data, name, user=True)
                            self.map_data["objects"] = orig_objects
                            self.current_filename = name
                            self.save_as_active = False
                            print(f"Карта сохранена как {name}")
                    elif cancel_rect.collidepoint(mx, my):
                        self.save_as_active = False
                    return
                else:
                    return

            if self.create_child_dialog:
                if self.create_child_dialog_rect and self.create_child_dialog_rect.collidepoint(mx, my):
                    for rect, typ in self.create_child_buttons:
                        if rect.collidepoint(mx, my):
                            if self.create_child_parent_idx >= 0:
                                self.placement_mode = True
                                self.placement_parent_idx = self.create_child_parent_idx
                                self.placement_type = typ
                                self.placement_dummy = (typ == "dummy")
                                parent = self.map_data["objects"][self.create_child_parent_idx]
                                color = parent.get("color", (255,0,0))
                                if self.placement_dummy:
                                    color = (0, 255, 0)
                                ghost = self._create_object_data(typ, 0, 0, color, self.placement_dummy)
                                ghost["x"] = 0
                                ghost["y"] = 0
                                self.placement_ghost_obj = ghost
                                self.create_child_dialog = False
                                return
                else:
                    self.create_child_dialog = False
                return

            if self.right_panel_visible and self.right_panel_rect.collidepoint(mx, my):
                objects = self.map_data["objects"]
                display_items = []
                for i, obj in enumerate(objects):
                    if obj.get("is_group"):
                        display_items.append((i, 0, True, obj.get("collapsed", False)))
                        if not obj.get("collapsed", False):
                            children = obj.get("children", [])
                            for child_idx in children:
                                if child_idx < len(objects):
                                    display_items.append((child_idx, 1, False, False))
                    else:
                        if obj.get("group_id") is None:
                            display_items.append((i, 0, False, False))
                item_height = self.right_panel_item_height
                padding = self.right_panel_padding
                list_start_y = 40
                scroll = self.right_panel_scroll
                rel_y = my - list_start_y
                item_idx = rel_y // (item_height + padding) + scroll
                if 0 <= item_idx < len(display_items):
                    idx, indent, is_group, is_collapsed = display_items[item_idx]
                    if idx >= len(objects):
                        return
                    if is_group:
                        rect = pygame.Rect(self.right_panel_rect.x + 5 + indent * INDENT_WIDTH, list_start_y + (item_idx - scroll) * (item_height + padding), 20, item_height)
                        if rect.collidepoint(mx, my):
                            obj = objects[idx]
                            obj["collapsed"] = not obj.get("collapsed", False)
                            return
                    if objects[idx].get("is_group"):
                        self.select_object_with_children(idx)
                    else:
                        self.selected_indices = [idx]
                        obj = objects[idx]
                        col = obj.get("color", (255,0,0))
                        if isinstance(col, str):
                            col = pygame.Color(col)
                        if isinstance(col, tuple):
                            self.rgb_sliders = list(col[:3])
                return

            if self.panel_rect.collidepoint(mx, my):
                for rect, idx in self.collapse_buttons:
                    if rect.collidepoint(mx, my):
                        if idx < len(self.map_data["objects"]):
                            obj = self.map_data["objects"][idx]
                            obj["collapsed"] = not obj.get("collapsed", False)
                        return
                clicked_param = None
                for rect, param_key, obj_idx in self.param_rects:
                    if rect.collidepoint(mx, my):
                        clicked_param = (param_key, obj_idx)
                        break
                if clicked_param:
                    now = pygame.time.get_ticks()
                    if (now - self.last_click_time < 500 and
                        abs(mx - self.last_click_pos[0]) < 10 and
                        abs(my - self.last_click_pos[1]) < 10 and
                        self.last_click_param == clicked_param):
                        param_key, obj_idx = clicked_param
                        if obj_idx < len(self.map_data["objects"]):
                            obj = self.map_data["objects"][obj_idx]
                            if param_key in ["r", "g", "b"]:
                                val = self.rgb_sliders[0 if param_key=="r" else 1 if param_key=="g" else 2]
                            else:
                                val = obj.get(param_key, 0)
                            self.input_active = True
                            self.input_text = str(val)
                            self.input_param = param_key
                            self.input_obj_index = obj_idx
                            self.last_click_time = 0
                            self.last_click_param = None
                            return
                    else:
                        self.last_click_time = now
                        self.last_click_pos = (mx, my)
                        self.last_click_param = clicked_param
                else:
                    self.last_click_time = 0
                    self.last_click_param = None

                self.handle_panel_click(mx, my)
                return

            # --- Работа с миром ---
            if self.placement_mode:
                self.placement_mode = False
                self.placement_ghost_obj = None
                return

            if self.hover_resize and self.selected_indices:
                idx = self.selected_indices[0]
                if idx >= len(self.map_data["objects"]):
                    return
                obj = self.map_data["objects"][idx]
                self.resizing = True
                self.resize_index = idx
                self.resize_type = self.hover_resize_type
                self.resize_data = {}
                obj_type = obj.get("type")
                if obj_type in ("circle", "nocollide_circle") and self.hover_resize_type == "circle_radius":
                    self.resize_data["start_radius"] = obj.get("radius", 30)
                elif obj_type in ("rect", "nocollide_rect") and self.hover_resize_type == "rect_side":
                    corners = self.get_rect_corners(obj)
                    top_center = ((corners[0][0]+corners[1][0])/2, (corners[0][1]+corners[1][1])/2)
                    bottom_center = ((corners[3][0]+corners[2][0])/2, (corners[3][1]+corners[2][1])/2)
                    left_center = ((corners[0][0]+corners[3][0])/2, (corners[0][1]+corners[3][1])/2)
                    right_center = ((corners[1][0]+corners[2][0])/2, (corners[1][1]+corners[2][1])/2)
                    wx, wy = self.screen_to_world(mx, my)
                    dists = {
                        "top": math.hypot(wx - top_center[0], wy - top_center[1]),
                        "bottom": math.hypot(wx - bottom_center[0], wy - bottom_center[1]),
                        "left": math.hypot(wx - left_center[0], wy - left_center[1]),
                        "right": math.hypot(wx - right_center[0], wy - right_center[1])
                    }
                    side = min(dists, key=dists.get)
                    self.resize_data["side"] = side
                    self.resize_data["start_width"] = obj.get("width", 60)
                    self.resize_data["start_height"] = obj.get("height", 40)
                    self.resize_data["start_x"] = obj.get("x", 0)
                    self.resize_data["start_y"] = obj.get("y", 0)
                    self.resize_data["start_mx"], self.resize_data["start_my"] = mx, my
                elif obj_type == "triangle":
                    if self.hover_resize_type == "triangle_side":
                        vertices = self.get_triangle_vertices(obj)
                        if vertices:
                            mid_ab = ((vertices[0][0]+vertices[1][0])/2, (vertices[0][1]+vertices[1][1])/2)
                            mid_bc = ((vertices[1][0]+vertices[2][0])/2, (vertices[1][1]+vertices[2][1])/2)
                            mid_ca = ((vertices[2][0]+vertices[0][0])/2, (vertices[2][1]+vertices[0][1])/2)
                            wx, wy = self.screen_to_world(mx, my)
                            dists = {
                                "a": math.hypot(wx - mid_ab[0], wy - mid_ab[1]),
                                "b": math.hypot(wx - mid_bc[0], wy - mid_bc[1]),
                                "c": math.hypot(wx - mid_ca[0], wy - mid_ca[1])
                            }
                            side = min(dists, key=dists.get)
                            self.resize_data["side"] = side
                            self.resize_data["start_a"] = obj.get("a", 60.0)
                            self.resize_data["start_b"] = obj.get("b", 60.0)
                            self.resize_data["start_c"] = obj.get("c", 60.0)
                            self.resize_data["start_mx"], self.resize_data["start_my"] = mx, my
                    elif self.hover_resize_type == "triangle_vertex":
                        vertices = self.get_triangle_vertices(obj)
                        if vertices:
                            wx, wy = self.screen_to_world(mx, my)
                            best_idx = 0
                            best_dist = math.hypot(wx - vertices[0][0], wy - vertices[0][1])
                            for i in range(1, 3):
                                d = math.hypot(wx - vertices[i][0], wy - vertices[i][1])
                                if d < best_dist:
                                    best_dist = d
                                    best_idx = i
                            self.resize_data["vertex_idx"] = best_idx
                            self.resize_data["start_vertices"] = vertices
                            self.resize_data["current_vx"] = vertices[best_idx][0]
                            self.resize_data["current_vy"] = vertices[best_idx][1]
                self.hover_resize = False
                return

            # Обработка двойного клика
            now = pygame.time.get_ticks()
            if (now - self.last_click_time < 500 and
                abs(mx - self.last_click_pos[0]) < 10 and
                abs(my - self.last_click_pos[1]) < 10):
                world_pos = self.get_world_pos((mx, my))
                if world_pos is not None:
                    wx, wy = world_pos
                    if self.selected_indices:
                        idx = self.selected_indices[0]
                        if idx < len(self.map_data["objects"]):
                            obj = self.map_data["objects"][idx]
                            if obj.get("group_id") is not None and not obj.get("is_group"):
                                abs_x, abs_y, _ = self.get_abs_transform(idx)
                            else:
                                abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                            cx, cy = abs_x, abs_y
                            if math.hypot(wx - cx, wy - cy) < 15 / self.zoom:
                                self.rotating = True
                                self.rotate_index = idx
                                self.rotate_start_angle = obj.get("angle", 0)
                                self.last_click_time = 0
                                self.last_click_param = None
                                return
                    idx2, part_type, part_idx = self.get_triangle_part_at_pos(wx, wy)
                    if idx2 is not None and part_type == "vertex":
                        param_map = {0: "alpha", 1: "beta", 2: "gamma"}
                        param_key = param_map.get(part_idx)
                        if param_key is not None:
                            obj = self.map_data["objects"][idx2]
                            val = obj.get(param_key, 60.0)
                            self.input_active = True
                            self.input_text = str(val)
                            self.input_param = param_key
                            self.input_obj_index = idx2
                            self.last_click_time = 0
                            self.last_click_param = None
                            return
            self.last_click_time = now
            self.last_click_pos = (mx, my)
            self.last_click_param = None

            if not self.input_active and not self.rotating:
                self.dragging_camera = True
                self.camera_drag_start = (mx, my)

        elif event.button == 3:
            # ПКМ — если в режиме размещения, фиксируем позицию
            if self.placement_mode:
                world_pos = self.get_world_pos((mx, my))
                if world_pos is not None:
                    wx, wy = world_pos
                    parent_idx = self.placement_parent_idx
                    if parent_idx >= len(self.map_data["objects"]):
                        self.placement_mode = False
                        self.placement_ghost_obj = None
                        return
                    parent = self.map_data["objects"][parent_idx]
                    if parent.get("is_group"):
                        group_id = parent["id"]
                        self.object_counter += 1
                        new_obj = self._create_object_data(self.placement_type, wx, wy, parent.get("color", (255,0,0)), self.placement_dummy)
                        new_obj["group_id"] = group_id
                        main_idx = self.get_group_main(group_id)
                        if main_idx is not None:
                            main_obj = self.map_data["objects"][main_idx]
                            px, py, pa = main_obj.get("x", 0), main_obj.get("y", 0), main_obj.get("angle", 0)
                            dx = wx - px
                            dy = wy - py
                            angle_rad = math.radians(pa)
                            local_x = dx * math.cos(-angle_rad) - dy * math.sin(-angle_rad)
                            local_y = dx * math.sin(-angle_rad) + dy * math.cos(-angle_rad)
                            new_obj["local_x"] = rnd(local_x)
                            new_obj["local_y"] = rnd(local_y)
                            new_obj["local_angle"] = 0.0
                        else:
                            new_obj["local_x"] = 0.0
                            new_obj["local_y"] = 0.0
                            new_obj["local_angle"] = 0.0
                        new_obj["name"] = f"UNDGobj: {new_obj.get('name', 'Объект')}"
                        new_obj["is_main"] = False
                        self.map_data["objects"].append(new_obj)
                        new_idx = len(self.map_data["objects"]) - 1
                        parent["children"].append(new_idx)
                        self.selected_indices = [new_idx]
                        self.rgb_sliders = list(new_obj["color"][:3])
                    else:
                        self.group_counter += 1
                        group_id = self.group_counter
                        parent["is_group"] = True
                        parent["id"] = group_id
                        parent["children"] = []
                        parent["collapsed"] = False
                        parent["is_main"] = True
                        old_name = parent.get("name", "Объект")
                        if not old_name.startswith("UNDGmain:"):
                            parent["name"] = f"UNDGmain: {old_name}"
                        parent["local_x"] = 0.0
                        parent["local_y"] = 0.0
                        parent["local_angle"] = 0.0
                        self.object_counter += 1
                        new_obj = self._create_object_data(self.placement_type, wx, wy, parent.get("color", (255,0,0)), self.placement_dummy)
                        new_obj["group_id"] = group_id
                        px, py, pa = parent["x"], parent["y"], parent.get("angle", 0)
                        dx = wx - px
                        dy = wy - py
                        angle_rad = math.radians(pa)
                        local_x = dx * math.cos(-angle_rad) - dy * math.sin(-angle_rad)
                        local_y = dx * math.sin(-angle_rad) + dy * math.cos(-angle_rad)
                        new_obj["local_x"] = rnd(local_x)
                        new_obj["local_y"] = rnd(local_y)
                        new_obj["local_angle"] = 0.0
                        new_obj["name"] = f"UNDGobj: {new_obj.get('name', 'Объект')}"
                        new_obj["is_main"] = False
                        self.map_data["objects"].append(new_obj)
                        new_idx = len(self.map_data["objects"]) - 1
                        parent["children"].append(new_idx)
                        self.group_main[group_id] = parent_idx
                        self.selected_indices = [new_idx]
                        self.rgb_sliders = list(new_obj["color"][:3])
                self.placement_mode = False
                self.placement_ghost_obj = None
                return

            if self.right_panel_visible and self.right_panel_rect.collidepoint(mx, my):
                objects = self.map_data["objects"]
                display_items = []
                for i, obj in enumerate(objects):
                    if obj.get("is_group"):
                        display_items.append((i, 0, True, obj.get("collapsed", False)))
                        if not obj.get("collapsed", False):
                            children = obj.get("children", [])
                            for child_idx in children:
                                if child_idx < len(objects):
                                    display_items.append((child_idx, 1, False, False))
                    else:
                        if obj.get("group_id") is None:
                            display_items.append((i, 0, False, False))
                item_height = self.right_panel_item_height
                padding = self.right_panel_padding
                list_start_y = 40
                scroll = self.right_panel_scroll
                rel_y = my - list_start_y
                item_idx = rel_y // (item_height + padding) + scroll
                if 0 <= item_idx < len(display_items):
                    idx, indent, is_group, is_collapsed = display_items[item_idx]
                    if idx < len(objects):
                        self.right_panel_rename_index = idx
                        self.right_panel_rename_text = objects[idx].get("name", "")
                        self.right_panel_drag_start_y = my
                        self.right_panel_dragging = False
                        self.right_panel_drag_index = idx
                        self.right_panel_mouse_down_pos = (mx, my)
                return

            if self.panel_rect.collidepoint(mx, my):
                # Проверяем клик по слайдеру правой кнопкой
                for i, (rect, idx) in enumerate(self.slider_rects):
                    if rect.collidepoint(mx, my):
                        self.slider_dragging = i
                        self.slider_dragging_button = 3
                        return
                return

            world_pos = self.get_world_pos((mx, my))
            if world_pos is None:
                return
            wx, wy = world_pos

            # Shift + ПКМ для смены главного объекта в группе
            if pygame.key.get_mods() & KMOD_SHIFT:
                found = -1
                for i in range(len(self.map_data["objects"])):
                    obj = self.map_data["objects"][i]
                    if obj.get("group_id") is not None and not obj.get("is_group"):
                        abs_x, abs_y, _ = self.get_abs_transform(i)
                    else:
                        abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                    dist = math.hypot(wx - abs_x, wy - abs_y)
                    if dist < 30:
                        found = i
                        break
                if found >= 0:
                    obj = self.map_data["objects"][found]
                    if obj.get("group_id") is not None:
                        group_id = obj["group_id"]
                        if group_id is not None:
                            self.set_group_main(group_id, found)
                            self.selected_indices = [found]
                            col = obj.get("color", (255,0,0))
                            if isinstance(col, str):
                                col = pygame.Color(col)
                            if isinstance(col, tuple):
                                self.rgb_sliders = list(col[:3])
                            return
                self.dragging_selection = True
                self.selection_rect_start = (wx, wy)
                self.selection_rect_end = (wx, wy)
                return

            # Обычное выделение ПКМ
            found = -1
            for i in range(len(self.map_data["objects"])):
                obj = self.map_data["objects"][i]
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.get_abs_transform(i)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                dist = math.hypot(wx - abs_x, wy - abs_y)
                if dist < 30:
                    found = i
                    break

            if found >= 0:
                if self.map_data["objects"][found].get("is_group"):
                    self.select_object_with_children(found)
                else:
                    if pygame.key.get_mods() & KMOD_SHIFT:
                        if found not in self.selected_indices:
                            self.selected_indices.append(found)
                    else:
                        self.selected_indices = [found]
                    obj = self.map_data["objects"][found]
                    col = obj.get("color", (255,0,0))
                    if isinstance(col, str):
                        col = pygame.Color(col)
                    if isinstance(col, tuple):
                        self.rgb_sliders = list(col[:3])
                if len(self.selected_indices) >= 1:
                    self.dragging_object = True
                    self.drag_start_world = (wx, wy)
                    self.drag_initial_abs = {}
                    self.drag_group_indices = []
                    has_main = False
                    main_group_ids = set()
                    for idx in self.selected_indices:
                        if idx < len(self.map_data["objects"]):
                            obj = self.map_data["objects"][idx]
                            if obj.get("is_main", False):
                                has_main = True
                                main_group_ids.add(obj.get("id"))
                    if has_main:
                        for gid in main_group_ids:
                            for i, o in enumerate(self.map_data["objects"]):
                                if o.get("group_id") == gid or (o.get("is_group") and o.get("id") == gid):
                                    if i not in self.drag_group_indices:
                                        self.drag_group_indices.append(i)
                    else:
                        self.drag_group_indices = self.selected_indices[:]
                    for idx in self.drag_group_indices:
                        if idx < len(self.map_data["objects"]):
                            ax, ay, _ = self.get_abs_transform(idx)
                            self.drag_initial_abs[idx] = (ax, ay)
                    self.drag_offset = (0, 0)
            else:
                self.dragging_selection = True
                self.selection_rect_start = (wx, wy)
                self.selection_rect_end = (wx, wy)

    def handle_mouse_up(self, event):
        if event.button == 1:
            self.dragging_camera = False
            if self.slider_dragging is not None and self.slider_dragging_button == 1:
                self.slider_dragging = None
                self.slider_dragging_button = None
            if self.rotating:
                self.rotating = False
                self.rotate_index = -1
            if self.resizing:
                if self.resize_type == "triangle_vertex":
                    obj = self.map_data["objects"][self.resize_index]
                    vertex_idx = self.resize_data["vertex_idx"]
                    target_vx = self.resize_data["current_vx"]
                    target_vy = self.resize_data["current_vy"]
                    start_vertices = self.resize_data["start_vertices"]
                    other_indices = [i for i in range(3) if i != vertex_idx]
                    p0 = start_vertices[other_indices[0]]
                    p1 = start_vertices[other_indices[1]]
                    p_new = (target_vx, target_vy)
                    if vertex_idx == 0:
                        target_points = (p_new, p0, p1)
                    elif vertex_idx == 1:
                        target_points = (p0, p_new, p1)
                    else:
                        target_points = (p0, p1, p_new)
                    success = self.set_triangle_from_points(obj, target_points)
                    if not success:
                        obj["valid"] = False
                self.resizing = False
                self.resize_type = None
                self.resize_data = {}
        elif event.button == 3:
            if self.slider_dragging is not None and self.slider_dragging_button == 3:
                self.slider_dragging = None
                self.slider_dragging_button = None

            if self.right_panel_dragging:
                from_idx = self.right_panel_drag_index
                mx, my = pygame.mouse.get_pos()
                objects = self.map_data["objects"]
                if objects and 0 <= from_idx < len(objects):
                    display_items = []
                    for i, obj in enumerate(objects):
                        if obj.get("is_group"):
                            display_items.append((i, 0, True, obj.get("collapsed", False)))
                            if not obj.get("collapsed", False):
                                children = obj.get("children", [])
                                for child_idx in children:
                                    if child_idx < len(objects):
                                        display_items.append((child_idx, 1, False, False))
                        else:
                            if obj.get("group_id") is None:
                                display_items.append((i, 0, False, False))
                    item_height = self.right_panel_item_height
                    padding = self.right_panel_padding
                    list_start_y = 40
                    scroll = self.right_panel_scroll
                    rel_y = my - list_start_y
                    to_item_idx = rel_y // (item_height + padding) + scroll
                    if 0 <= to_item_idx < len(display_items):
                        to_idx, _, _, _ = display_items[to_item_idx]
                        if to_idx != from_idx and to_idx < len(objects):
                            obj = objects.pop(from_idx)
                            objects.insert(to_idx, obj)
                            self.selected_indices = [to_idx]
                self.right_panel_dragging = False
                self.right_panel_drag_index = -1
                self.right_panel_rename_index = -1
                self.right_panel_rename_text = ""
            else:
                if self.right_panel_rename_index >= 0:
                    pass

            if self.dragging_selection:
                self.dragging_selection = False
                if self.selection_rect_start and self.selection_rect_end:
                    x1, y1 = self.selection_rect_start
                    x2, y2 = self.selection_rect_end
                    left = min(x1, x2)
                    right = max(x1, x2)
                    top = min(y1, y2)
                    bottom = max(y1, y2)
                    new_selection = []
                    for i, obj in enumerate(self.map_data["objects"]):
                        if obj.get("group_id") is not None and not obj.get("is_group"):
                            abs_x, abs_y, _ = self.get_abs_transform(i)
                        else:
                            abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                        if left <= abs_x <= right and top <= abs_y <= bottom:
                            new_selection.append(i)
                    if new_selection:
                        if pygame.key.get_mods() & KMOD_SHIFT:
                            for idx in new_selection:
                                if idx not in self.selected_indices:
                                    self.selected_indices.append(idx)
                        else:
                            first = new_selection[0]
                            if self.map_data["objects"][first].get("is_group"):
                                self.select_object_with_children(first)
                            else:
                                self.selected_indices = new_selection
                        if self.selected_indices:
                            obj = self.map_data["objects"][self.selected_indices[0]]
                            col = obj.get("color", (255,0,0))
                            if isinstance(col, str):
                                col = pygame.Color(col)
                            if isinstance(col, tuple):
                                self.rgb_sliders = list(col[:3])
                    else:
                        if not (pygame.key.get_mods() & KMOD_SHIFT):
                            self.selected_indices = []
                    self.selection_rect_start = None
                    self.selection_rect_end = None
            if self.dragging_object:
                self.dragging_object = False
                self.drag_start_world = None
                self.drag_initial_abs = {}
                self.drag_group_indices = []

    def handle_mouse_motion(self, event):
        mx, my = event.pos

        if mx > self.screen_width - RIGHT_PANEL_TRIGGER_WIDTH:
            self.right_panel_visible = True
        elif mx < self.screen_width - RIGHT_PANEL_WIDTH - 10:
            self.right_panel_visible = False

        if self.right_panel_rename_index >= 0 and pygame.mouse.get_pressed()[2]:
            dx = mx - self.right_panel_mouse_down_pos[0]
            dy = my - self.right_panel_mouse_down_pos[1]
            if abs(dx) > 5 or abs(dy) > 5:
                self.right_panel_rename_index = -1
                self.right_panel_rename_text = ""
                self.right_panel_dragging = True

        if self.rotating and self.rotate_index >= 0:
            if self.rotate_index < len(self.map_data["objects"]):
                obj = self.map_data["objects"][self.rotate_index]
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.get_abs_transform(self.rotate_index)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                cx, cy = abs_x, abs_y
                world_pos = self.get_world_pos((mx, my))
                if world_pos is not None:
                    wx, wy = world_pos
                    dx = wx - cx
                    dy = wy - cy
                    if math.hypot(dx, dy) > 5:
                        new_angle = math.degrees(math.atan2(dy, dx))
                        if obj.get("group_id") is not None and not obj.get("is_group"):
                            group_id = obj["group_id"]
                            main_idx = self.get_group_main(group_id)
                            if main_idx is not None:
                                parent_obj = self.map_data["objects"][main_idx]
                                pa = parent_obj.get("angle", 0)
                                obj["local_angle"] = rnd(new_angle - pa)
                            else:
                                obj["angle"] = rnd(new_angle)
                        else:
                            obj["angle"] = rnd(new_angle)

        if self.dragging_camera:
            dx = mx - self.camera_drag_start[0]
            dy = my - self.camera_drag_start[1]
            self.camera_x -= dx / self.zoom
            self.camera_y -= dy / self.zoom
            self.camera_drag_start = (mx, my)

        # Перетаскивание объектов
        if self.dragging_object and self.drag_start_world is not None:
            world_pos = self.get_world_pos((mx, my))
            if world_pos is None:
                return
            wx, wy = world_pos
            dx = wx - self.drag_start_world[0]
            dy = wy - self.drag_start_world[1]
            for idx in list(self.drag_group_indices):
                if idx not in self.drag_initial_abs:
                    continue
                if idx >= len(self.map_data["objects"]):
                    continue
                init_ax, init_ay = self.drag_initial_abs[idx]
                new_ax = init_ax + dx
                new_ay = init_ay + dy
                self.set_abs_position(idx, new_ax, new_ay)

        if self.resizing and self.resize_index >= 0:
            if self.resize_index >= len(self.map_data["objects"]):
                return
            obj = self.map_data["objects"][self.resize_index]
            obj_type = obj.get("type")

            if obj_type in ("circle", "nocollide_circle") and self.resize_type == "circle_radius":
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.get_abs_transform(self.resize_index)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                sx, sy = self.world_to_screen(abs_x, abs_y)
                dist = math.hypot(mx - sx, my - sy)
                if dist > 5:
                    new_radius = max(1, dist / self.zoom)
                    obj["radius"] = rnd(new_radius)

            elif obj_type in ("rect", "nocollide_rect") and self.resize_type == "rect_side":
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.get_abs_transform(self.resize_index)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                sx, sy = self.world_to_screen(abs_x, abs_y)
                side = self.resize_data["side"]
                start_w = self.resize_data["start_width"]
                start_h = self.resize_data["start_height"]
                start_x = self.resize_data["start_x"]
                start_y = self.resize_data["start_y"]
                start_mx = self.resize_data["start_mx"]
                start_my = self.resize_data["start_my"]
                dx = (mx - start_mx) / self.zoom
                dy = (my - start_my) / self.zoom

                if side == "left":
                    new_w = max(1, start_w - dx)
                    new_x = start_x + dx/2
                    obj["width"] = rnd(new_w)
                    obj["x"] = rnd(new_x)
                elif side == "right":
                    new_w = max(1, start_w + dx)
                    new_x = start_x + dx/2
                    obj["width"] = rnd(new_w)
                    obj["x"] = rnd(new_x)
                elif side == "top":
                    new_h = max(1, start_h - dy)
                    new_y = start_y + dy/2
                    obj["height"] = rnd(new_h)
                    obj["y"] = rnd(new_y)
                elif side == "bottom":
                    new_h = max(1, start_h + dy)
                    new_y = start_y + dy/2
                    obj["height"] = rnd(new_h)
                    obj["y"] = rnd(new_y)

            elif obj_type == "triangle":
                if self.resize_type == "triangle_side":
                    if obj.get("group_id") is not None and not obj.get("is_group"):
                        abs_x, abs_y, _ = self.get_abs_transform(self.resize_index)
                    else:
                        abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                    sx, sy = self.world_to_screen(abs_x, abs_y)
                    side = self.resize_data["side"]
                    start_mx = self.resize_data["start_mx"]
                    start_my = self.resize_data["start_my"]
                    dx = (mx - start_mx) / self.zoom
                    dy = (my - start_my) / self.zoom
                    if side == "a":
                        new_a = max(1, self.resize_data["start_a"] + dx * 2)
                        obj["a"] = rnd(new_a)
                        self.update_triangle_from_angles(obj)
                    elif side == "b":
                        alpha = obj.get("alpha", 60)
                        beta = obj.get("beta", 60)
                        gamma = obj.get("gamma", 60)
                        old_b = self.resize_data["start_b"]
                        new_b = max(1, old_b + dy * 2)
                        if math.sin(math.radians(beta)) != 0:
                            a = new_b * math.sin(math.radians(alpha)) / math.sin(math.radians(beta))
                            c = new_b * math.sin(math.radians(gamma)) / math.sin(math.radians(beta))
                            if a > 0 and c > 0:
                                obj["a"] = rnd(a)
                                obj["b"] = rnd(new_b)
                                obj["c"] = rnd(c)
                                obj["valid"] = True
                            else:
                                obj["valid"] = False
                        else:
                            obj["valid"] = False
                    elif side == "c":
                        alpha = obj.get("alpha", 60)
                        beta = obj.get("beta", 60)
                        gamma = obj.get("gamma", 60)
                        old_c = self.resize_data["start_c"]
                        new_c = max(1, old_c - dx * 2)
                        if math.sin(math.radians(gamma)) != 0:
                            a = new_c * math.sin(math.radians(alpha)) / math.sin(math.radians(gamma))
                            b = new_c * math.sin(math.radians(beta)) / math.sin(math.radians(gamma))
                            if a > 0 and b > 0:
                                obj["a"] = rnd(a)
                                obj["b"] = rnd(b)
                                obj["c"] = rnd(new_c)
                                obj["valid"] = True
                            else:
                                obj["valid"] = False
                        else:
                            obj["valid"] = False
                elif self.resize_type == "triangle_vertex":
                    world_pos = self.get_world_pos((mx, my))
                    if world_pos is not None:
                        wx, wy = world_pos
                        self.resize_data["current_vx"] = wx
                        self.resize_data["current_vy"] = wy

        if self.dragging_selection:
            world_pos = self.get_world_pos((mx, my))
            if world_pos is not None:
                wx, wy = world_pos
                self.selection_rect_end = (wx, wy)

        if not self.dragging_object and not self.resizing and not self.rotating:
            world_pos = self.get_world_pos((mx, my))
            if world_pos is not None:
                wx, wy = world_pos
                self.hover_index = -1
                for i in range(len(self.map_data["objects"])-1, -1, -1):
                    obj = self.map_data["objects"][i]
                    if obj.get("group_id") is not None and not obj.get("is_group"):
                        abs_x, abs_y, _ = self.get_abs_transform(i)
                    else:
                        abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                    dist = math.hypot(wx - abs_x, wy - abs_y)
                    if dist < 30:
                        self.hover_index = i
                        break

        # Обновление слайдеров (левой или правой кнопкой)
        if self.slider_dragging is not None:
            # Проверяем, есть ли ещё зажатая кнопка мыши
            pressed = pygame.mouse.get_pressed()
            if (self.slider_dragging_button == 1 and not pressed[0]) or \
               (self.slider_dragging_button == 3 and not pressed[2]):
                self.slider_dragging = None
                self.slider_dragging_button = None
                return
            if self.selected_indices:
                slider_rect, idx = self.slider_rects[self.slider_dragging]
                rel_x = mx - (PANEL_WIDTH + slider_rect.x)
                val = max(0, min(255, int((rel_x / slider_rect.w) * 255)))
                self.rgb_sliders[self.slider_dragging] = val
                for i in self.selected_indices:
                    if i < len(self.map_data["objects"]):
                        obj = self.map_data["objects"][i]
                        obj["color"] = tuple(self.rgb_sliders)

        # Обновление ховера для ресайза
        if not self.resizing and self.selected_indices:
            idx = self.selected_indices[0]
            if idx >= len(self.map_data["objects"]):
                return
            obj = self.map_data["objects"][idx]
            obj_type = obj.get("type")
            self.hover_resize = False
            self.hover_resize_type = None
            if obj.get("group_id") is not None and not obj.get("is_group"):
                abs_x, abs_y, _ = self.get_abs_transform(idx)
            else:
                abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
            sx, sy = self.world_to_screen(abs_x, abs_y)

            if obj_type in ("circle", "nocollide_circle"):
                radius = obj.get("radius", 30) * self.zoom
                dist = math.hypot(mx - sx, my - sy)
                if abs(dist - radius) < 20:
                    self.hover_resize = True
                    self.hover_resize_type = "circle_radius"
            elif obj_type in ("rect", "nocollide_rect"):
                corners = self.get_rect_corners(obj)
                top_center = ((corners[0][0]+corners[1][0])/2, (corners[0][1]+corners[1][1])/2)
                bottom_center = ((corners[3][0]+corners[2][0])/2, (corners[3][1]+corners[2][1])/2)
                left_center = ((corners[0][0]+corners[3][0])/2, (corners[0][1]+corners[3][1])/2)
                right_center = ((corners[1][0]+corners[2][0])/2, (corners[1][1]+corners[2][1])/2)
                side_points = [("top", top_center), ("bottom", bottom_center), ("left", left_center), ("right", right_center)]
                for (label, (cx, cy)) in side_points:
                    scx, scy = self.world_to_screen(cx, cy)
                    if math.hypot(mx - scx, my - scy) < 15:
                        self.hover_resize = True
                        self.hover_resize_type = "rect_side"
                        break
            elif obj_type == "triangle":
                vertices = self.get_triangle_vertices(obj)
                if not vertices:
                    return
                mid_ab = ((vertices[0][0]+vertices[1][0])/2, (vertices[0][1]+vertices[1][1])/2)
                mid_bc = ((vertices[1][0]+vertices[2][0])/2, (vertices[1][1]+vertices[2][1])/2)
                mid_ca = ((vertices[2][0]+vertices[0][0])/2, (vertices[2][1]+vertices[0][1])/2)
                side_points = [("a", mid_ab), ("b", mid_bc), ("c", mid_ca)]
                for (label, (cx, cy)) in side_points:
                    scx, scy = self.world_to_screen(cx, cy)
                    if math.hypot(mx - scx, my - scy) < 15:
                        self.hover_resize = True
                        self.hover_resize_type = "triangle_side"
                        break
                if not self.hover_resize:
                    for i, (vx, vy) in enumerate(vertices):
                        scx, scy = self.world_to_screen(vx, vy)
                        if math.hypot(mx - scx, my - scy) < 15:
                            self.hover_resize = True
                            self.hover_resize_type = "triangle_vertex"
                            break

    def handle_mouse_wheel(self, event):
        mx, my = pygame.mouse.get_pos()
        if self.panel_rect.collidepoint(mx, my):
            self.panel_scroll -= event.y * 20
            return
        if self.right_panel_visible and self.right_panel_rect.collidepoint(mx, my):
            self.right_panel_scroll -= event.y
            return
        if mx > PANEL_WIDTH and mx < self.screen_width - RIGHT_PANEL_TRIGGER_WIDTH:
            wx, wy = self.screen_to_world(mx, my)
            zoom_factor = 1.1 if event.y > 0 else 0.9
            self.zoom *= zoom_factor
            self.zoom = max(0.1, min(10.0, self.zoom))
            self.camera_x = wx - (mx - PANEL_WIDTH) / self.zoom
            self.camera_y = wy - my / self.zoom

    def handle_panel_click(self, mx, my):
        for rect, typ in self.icon_rects:
            if rect.collidepoint(mx, my):
                self.new_object_type = typ
                return
        for rect, col in self.color_rects:
            if rect.collidepoint(mx, my):
                if self.selected_indices:
                    self.rgb_sliders = list(col[:3])
                    for i in self.selected_indices:
                        if i < len(self.map_data["objects"]):
                            self.map_data["objects"][i]["color"] = tuple(self.rgb_sliders)
                return
        # Слайдеры обрабатываются отдельно, но и здесь можно начать перетаскивание левой кнопкой
        for i, (rect, idx) in enumerate(self.slider_rects):
            if rect.collidepoint(mx, my):
                self.slider_dragging = i
                self.slider_dragging_button = 1
                return
        if self.checkbox_rect and self.checkbox_rect.collidepoint(mx, my):
            self.fine_tune = not self.fine_tune
            return
        for rect, action in self.button_rects:
            if rect.collidepoint(mx, my):
                if action == "help":
                    self.toggle_help()
                elif action == "resize":
                    self.start_resize()
                elif action == "run":
                    self.run_game()
                elif action == "saveas":
                    self.start_save_as()
                elif action == "overwrite":
                    self.save_overwrite()
                elif action == "exit":
                    self.running = False
                elif action == "create_child":
                    if self.selected_indices:
                        parent_idx = self.selected_indices[0]
                        if parent_idx < len(self.map_data["objects"]):
                            parent = self.map_data["objects"][parent_idx]
                            if parent.get("is_group") or parent.get("group_id") is None:
                                self.create_child_dialog = True
                                self.create_child_parent_idx = parent_idx
                                self.create_child_selected_type = "circle"
                                self.create_child_dialog_rect = pygame.Rect(self.screen_width//2 - 100, self.screen_height//2 - 100, 200, 200)
                                self.create_child_buttons = []
                                types = ["circle", "rect", "triangle", "nocollide_rect", "nocollide_circle", "dummy"]
                                labels = ["Круг", "Прям.", "Треуг.", "Прям. без", "Круг без", "Заглушка"]
                                y = self.create_child_dialog_rect.y + 30
                                for i, typ in enumerate(types):
                                    rect = pygame.Rect(self.create_child_dialog_rect.x + 20, y, 160, 30)
                                    self.create_child_buttons.append((rect, typ))
                                    y += 35
                return

    # ====== Действия ======
    def create_object(self):
        mx, my = pygame.mouse.get_pos()
        if mx < PANEL_WIDTH or mx > self.screen_width - RIGHT_PANEL_TRIGGER_WIDTH:
            return
        wx, wy = self.screen_to_world(mx, my)

        if self.new_object_type == "dummy":
            self.create_dummy_group(wx, wy)
            return

        self.object_counter += 1
        obj = {
            "type": self.new_object_type,
            "x": wx,
            "y": wy,
            "color": tuple(self.rgb_sliders),
            "angle": 0,
            "name": f"Объект {self.object_counter}",
            "children": [],
            "parent": None,
            "group_id": None,
            "is_group": False,
            "collapsed": False,
            "local_x": 0,
            "local_y": 0,
            "local_angle": 0,
            "dummy": False,
            "is_main": False
        }
        if self.new_object_type in ("circle", "nocollide_circle"):
            obj["radius"] = self.new_radius
        elif self.new_object_type in ("rect", "nocollide_rect"):
            obj["width"] = self.new_width
            obj["height"] = self.new_height
        elif self.new_object_type == "triangle":
            obj["a"] = self.new_a
            obj["b"] = self.new_b
            obj["c"] = self.new_c
            obj["alpha"] = self.new_alpha
            obj["beta"] = self.new_beta
            obj["gamma"] = self.new_gamma
            valid, angles = self.validate_triangle_angles(self.new_alpha, self.new_beta, self.new_gamma)
            if valid:
                a = self.new_a
                alpha, beta, gamma = angles
                sides = self.compute_triangle_sides(a, alpha, beta, gamma)
                if sides is not None:
                    b, c = sides
                    obj["a"] = rnd(a)
                    obj["b"] = rnd(b)
                    obj["c"] = rnd(c)
                    obj["alpha"] = rnd(alpha)
                    obj["beta"] = rnd(beta)
                    obj["gamma"] = rnd(gamma)
                    obj["valid"] = True
                else:
                    obj["valid"] = False
            else:
                obj["valid"] = False
        self.map_data["objects"].append(obj)
        self.selected_indices = [len(self.map_data["objects"]) - 1]
        self.rgb_sliders = list(obj["color"][:3])

    def rotate_selected(self, delta):
        if not self.selected_indices:
            return
        for idx in self.selected_indices:
            if idx >= len(self.map_data["objects"]):
                continue
            obj = self.map_data["objects"][idx]
            if obj.get("group_id") is not None and not obj.get("is_group"):
                obj["local_angle"] = rnd(obj.get("local_angle", 0) + delta)
            else:
                obj["angle"] = rnd((obj.get("angle", 0) + delta) % 360)

    def delete_selected(self):
        if not self.selected_indices:
            return
        to_delete = set()
        for idx in self.selected_indices:
            if idx >= len(self.map_data["objects"]):
                continue
            obj = self.map_data["objects"][idx]
            if obj.get("is_group"):
                members = self.get_group_members(obj.get("id"))
                to_delete.update(members)
            else:
                to_delete.add(idx)
        groups_to_fix = {}
        for idx in to_delete:
            if idx >= len(self.map_data["objects"]):
                continue
            obj = self.map_data["objects"][idx]
            if obj.get("is_group"):
                continue
            if obj.get("group_id") is not None:
                group_id = obj["group_id"]
                main_idx = self.get_group_main(group_id)
                if main_idx == idx:
                    groups_to_fix[group_id] = True
        for group_id in groups_to_fix:
            members = self.get_group_members(group_id)
            for i in members:
                if i not in to_delete and i < len(self.map_data["objects"]):
                    self.set_group_main(group_id, i)
                    break

        for idx in sorted(to_delete, reverse=True):
            if idx >= len(self.map_data["objects"]):
                continue
            obj = self.map_data["objects"][idx]
            if obj.get("group_id") is not None:
                group_id = obj["group_id"]
                for o in self.map_data["objects"]:
                    if o.get("is_group") and o.get("id") == group_id:
                        if idx in o.get("children", []):
                            o["children"].remove(idx)
                        break
            del self.map_data["objects"][idx]
        self.selected_indices = []

    def toggle_help(self):
        self.show_help = not self.show_help

    def start_resize(self):
        self.resize_input_active = True
        self.resize_width_text = str(self.map_data["width"])
        self.resize_height_text = str(self.map_data["height"])

    def run_game(self):
        temp_name = "_temp_editor"
        save_objects = [obj for obj in self.map_data["objects"] if not obj.get("dummy")]
        orig_objects = self.map_data["objects"]
        self.map_data["objects"] = save_objects
        self.loader.save_map(self.map_data, temp_name, user=True)
        self.map_data["objects"] = orig_objects
        try:
            subprocess.Popen([sys.executable, "main.py", "--map", temp_name])
        except Exception as e:
            print("Ошибка запуска игры:", e)

    def start_save_as(self):
        self.save_as_active = True
        self.save_as_text = ""

    def save_overwrite(self):
        if self.current_filename:
            save_objects = [obj for obj in self.map_data["objects"] if not obj.get("dummy")]
            orig_objects = self.map_data["objects"]
            self.map_data["objects"] = save_objects
            self.loader.save_map(self.map_data, self.current_filename, user=True)
            self.map_data["objects"] = orig_objects
            print(f"Карта сохранена как {self.current_filename}")
        else:
            self.start_save_as()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), FULLSCREEN | DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), RESIZABLE | DOUBLEBUF)
        self.panel_rect.height = self.screen_height
        self.right_panel_rect = pygame.Rect(self.screen_width - RIGHT_PANEL_WIDTH, 0, RIGHT_PANEL_WIDTH, self.screen_height)

    def apply_input(self):
        if self.input_active and self.input_obj_index >= 0:
            if self.input_obj_index >= len(self.map_data["objects"]):
                self.cancel_input()
                return
            obj = self.map_data["objects"][self.input_obj_index]
            try:
                val = float(self.input_text)
                if self.input_param in ["r", "g", "b"]:
                    idx = 0 if self.input_param=="r" else 1 if self.input_param=="g" else 2
                    self.rgb_sliders[idx] = max(0, min(255, int(val)))
                    for i in self.selected_indices:
                        if i < len(self.map_data["objects"]):
                            self.map_data["objects"][i]["color"] = tuple(self.rgb_sliders)
                elif self.input_param in ["local_x", "local_y", "local_angle"]:
                    if self.input_param == "local_x":
                        obj["local_x"] = rnd(val)
                    elif self.input_param == "local_y":
                        obj["local_y"] = rnd(val)
                    elif self.input_param == "local_angle":
                        obj["local_angle"] = rnd(val)
                elif self.input_param in ["radius", "width", "height", "angle"]:
                    for i in self.selected_indices:
                        if i >= len(self.map_data["objects"]):
                            continue
                        o = self.map_data["objects"][i]
                        if self.input_param == "radius":
                            o["radius"] = rnd(max(1, val))
                        elif self.input_param == "width":
                            o["width"] = rnd(max(1, val))
                        elif self.input_param == "height":
                            o["height"] = rnd(max(1, val))
                        elif self.input_param == "angle":
                            o["angle"] = rnd(val % 360)
                elif self.input_param in ["a", "b", "c", "alpha", "beta", "gamma"]:
                    for i in self.selected_indices:
                        if i >= len(self.map_data["objects"]):
                            continue
                        o = self.map_data["objects"][i]
                        if o.get("type") == "triangle":
                            if self.input_param == "a":
                                o["a"] = rnd(max(1, val))
                                self.update_triangle_from_angles(o)
                            elif self.input_param == "b":
                                o["b"] = rnd(max(1, val))
                                self.update_triangle_from_angles(o)
                            elif self.input_param == "c":
                                o["c"] = rnd(max(1, val))
                                self.update_triangle_from_angles(o)
                            elif self.input_param == "alpha":
                                if self.fine_tune:
                                    o["alpha"] = rnd(val)
                                    self.update_triangle_from_angles(o)
                                else:
                                    delta = val - o.get("alpha", 60)
                                    self.correct_angles(o, "alpha", delta)
                            elif self.input_param == "beta":
                                if self.fine_tune:
                                    o["beta"] = rnd(val)
                                    self.update_triangle_from_angles(o)
                                else:
                                    delta = val - o.get("beta", 60)
                                    self.correct_angles(o, "beta", delta)
                            elif self.input_param == "gamma":
                                if self.fine_tune:
                                    o["gamma"] = rnd(val)
                                    self.update_triangle_from_angles(o)
                                else:
                                    delta = val - o.get("gamma", 60)
                                    self.correct_angles(o, "gamma", delta)
            except:
                pass
        self.cancel_input()

    def cancel_input(self):
        self.input_active = False
        self.input_text = ""
        self.input_param = None
        self.input_obj_index = -1
        self.input_rect = None

    # ====== Отрисовка помощи и диалогов ======
    def draw_create_child_dialog(self):
        if not self.create_child_dialog:
            return
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        rect = pygame.Rect(self.screen_width//2 - 100, self.screen_height//2 - 100, 200, 200)
        pygame.draw.rect(self.screen, COLOR_PANEL, rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, rect, 2)
        title = self.font.render("Выберите тип", True, COLOR_WHITE)
        self.screen.blit(title, (rect.x + 40, rect.y + 10))
        y = rect.y + 40
        types = ["circle", "rect", "triangle", "nocollide_rect", "nocollide_circle", "dummy"]
        labels = ["Круг", "Прям.", "Треуг.", "Прям. без", "Круг без", "Заглушка"]
        self.create_child_buttons = []
        for i, typ in enumerate(types):
            btn = pygame.Rect(rect.x + 20, y, 160, 30)
            self.create_child_buttons.append((btn, typ))
            pygame.draw.rect(self.screen, COLOR_GRAY, btn)
            text_surf = self.font_small.render(labels[i], True, COLOR_WHITE)
            self.screen.blit(text_surf, (btn.x + 10, btn.y + 6))
            y += 35

    def draw_placement_ghost(self):
        if not self.placement_mode or self.placement_ghost_obj is None:
            return
        mx, my = pygame.mouse.get_pos()
        world_pos = self.get_world_pos((mx, my))
        if world_pos is None:
            return
        wx, wy = world_pos
        ghost = self.placement_ghost_obj
        ghost["x"] = wx
        ghost["y"] = wy
        # Рисуем с полупрозрачностью
        s = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        old_screen = self.screen
        self.screen = s
        self._draw_object_raw(ghost, -1)
        self.screen = old_screen
        s.set_alpha(128)
        self.screen.blit(s, (0, 0))

    def draw_help(self):
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        y = 100
        x = 100
        lines = [
            "Справка по клавишам:",
            "1,2,3,4,5,6 - выбор типа объекта (6 - заглушка)",
            "F3 - создать объект (для заглушки — сразу группа)",
            "ПКМ по объекту - выделить (Shift - добавить)",
            "Shift+ПКМ по объекту в группе - сделать его главным",
            "ПКМ+перетаскивание - выделение областью",
            "ПКМ на выделенном - перемещение",
            "ПКМ на маркере стороны - растягивание",
            "ПКМ на вершине треугольника - растягивание",
            "ЛКМ+перетаскивание - перемещение камеры",
            "Двойной клик по синему кругу - вращение",
            "Двойной клик по вершине треугольника - угол",
            "Num4 / Num6 - поворот на 5°",
            "Двойной клик по параметру - редактирование",
            "Правая панель: ЛКМ - выбор, ПКМ - переименовать, зажать ПКМ и двигать - перетащить",
            "В левой панели: кнопка 'Создать объект подгруппы' для создания группы или дочернего объекта",
            "Группы: UNDGmain - главный, UNDGobj - дочерние",
            "Заглушка (dummy) — зелёный ромб, только координаты и поворот. Не сохраняется в игру.",
            "F1 - справка, F2 - размер карты, F5 - запуск, F6 - сохранить как, F7 - перезаписать",
            "Delete - удалить выделенные объекты (и группы целиком), F11 - полноэкранный"
        ]
        for line in lines:
            surf = self.font_small.render(line, True, COLOR_WHITE)
            self.screen.blit(surf, (x, y))
            y += 25

    def draw_resize_dialog(self):
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        dialog_rect = pygame.Rect(self.screen_width//2 - 150, self.screen_height//2 - 60, 300, 120)
        pygame.draw.rect(self.screen, COLOR_PANEL, dialog_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, dialog_rect, 2)
        w_label = self.font.render("Ширина:", True, COLOR_WHITE)
        self.screen.blit(w_label, (dialog_rect.x+20, dialog_rect.y+20))
        h_label = self.font.render("Высота:", True, COLOR_WHITE)
        self.screen.blit(h_label, (dialog_rect.x+20, dialog_rect.y+55))
        w_rect = pygame.Rect(dialog_rect.x+120, dialog_rect.y+20, 100, 25)
        pygame.draw.rect(self.screen, COLOR_BLACK, w_rect)
        w_surf = self.font.render(self.resize_width_text, True, COLOR_WHITE)
        self.screen.blit(w_surf, (w_rect.x+5, w_rect.y+2))
        h_rect = pygame.Rect(dialog_rect.x+120, dialog_rect.y+55, 100, 25)
        pygame.draw.rect(self.screen, COLOR_BLACK, h_rect)
        h_surf = self.font.render(self.resize_height_text, True, COLOR_WHITE)
        self.screen.blit(h_surf, (h_rect.x+5, h_rect.y+2))
        ok_rect = pygame.Rect(dialog_rect.x+40, dialog_rect.y+90, 80, 30)
        pygame.draw.rect(self.screen, COLOR_GREEN, ok_rect)
        self.screen.blit(self.font.render("OK", True, COLOR_WHITE), (ok_rect.x+25, ok_rect.y+5))
        cancel_rect = pygame.Rect(dialog_rect.x+180, dialog_rect.y+90, 80, 30)
        pygame.draw.rect(self.screen, COLOR_RED, cancel_rect)
        self.screen.blit(self.font.render("Cancel", True, COLOR_WHITE), (cancel_rect.x+10, cancel_rect.y+5))

    def draw_save_as_dialog(self):
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        dialog_rect = pygame.Rect(self.screen_width//2 - 150, self.screen_height//2 - 50, 300, 100)
        pygame.draw.rect(self.screen, COLOR_PANEL, dialog_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, dialog_rect, 2)
        label = self.font.render("Имя карты:", True, COLOR_WHITE)
        self.screen.blit(label, (dialog_rect.x+20, dialog_rect.y+20))
        input_rect = pygame.Rect(dialog_rect.x+20, dialog_rect.y+50, 260, 30)
        pygame.draw.rect(self.screen, COLOR_BLACK, input_rect)
        text_surf = self.font.render(self.save_as_text, True, COLOR_WHITE)
        self.screen.blit(text_surf, (input_rect.x+5, input_rect.y+5))
        ok_rect = pygame.Rect(dialog_rect.x+40, dialog_rect.y+90, 80, 30)
        pygame.draw.rect(self.screen, COLOR_GREEN, ok_rect)
        self.screen.blit(self.font.render("OK", True, COLOR_WHITE), (ok_rect.x+25, ok_rect.y+5))
        cancel_rect = pygame.Rect(dialog_rect.x+180, dialog_rect.y+90, 80, 30)
        pygame.draw.rect(self.screen, COLOR_RED, cancel_rect)
        self.screen.blit(self.font.render("Cancel", True, COLOR_WHITE), (cancel_rect.x+10, cancel_rect.y+5))

    def run(self):
        while self.running:
            self.clock.tick(60)
            self.handle_events()

            self.screen.fill(COLOR_BG)
            self.draw_grid()

            render_order = []
            for i, obj in enumerate(self.map_data["objects"]):
                if obj.get("is_group"):
                    render_order.append(i)
                    children = obj.get("children", [])
                    for child_idx in children:
                        if child_idx < len(self.map_data["objects"]):
                            render_order.append(child_idx)
                else:
                    if obj.get("group_id") is None:
                        render_order.append(i)

            for idx in reversed(render_order):
                if idx < len(self.map_data["objects"]):
                    self.draw_object(self.map_data["objects"][idx], idx)

            if self.dragging_selection and self.selection_rect_start and self.selection_rect_end:
                x1, y1 = self.selection_rect_start
                x2, y2 = self.selection_rect_end
                sx1, sy1 = self.world_to_screen(x1, y1)
                sx2, sy2 = self.world_to_screen(x2, y2)
                rect = pygame.Rect(min(sx1, sx2), min(sy1, sy2), abs(sx2-sx1), abs(sy2-sy1))
                pygame.draw.rect(self.screen, COLOR_YELLOW, rect, 1)

            self.draw_panel()
            self.draw_right_panel()
            self.draw_cursor()
            self.draw_create_child_dialog()
            self.draw_placement_ghost()

            if self.show_help:
                self.draw_help()
            if self.resize_input_active:
                self.draw_resize_dialog()
            if self.save_as_active:
                self.draw_save_as_dialog()

            pygame.display.flip()

if __name__ == "__main__":
    error_log = "logs/editor_error.log"
    try:
        editor = Editor()
        editor.run()
    except Exception as e:
        with open(error_log, "w", encoding="utf-8") as f:
            f.write("Ошибка в редакторе карт:\n")
            f.write(traceback.format_exc())
        try:
            pygame.init()
            screen = pygame.display.set_mode((800, 200))
            pygame.display.set_caption("Ошибка редактора")
            font = pygame.font.Font(None, 24)
            lines = [
                "Произошла ошибка!",
                "Подробности записаны в файл: " + error_log,
                "Нажмите любую клавишу для выхода."
            ]
            while True:
                for event in pygame.event.get():
                    if event.type == QUIT or event.type == KEYDOWN:
                        pygame.quit()
                        sys.exit()
                screen.fill((40, 40, 40))
                y = 30
                for line in lines:
                    text = font.render(line, True, (255, 255, 255))
                    screen.blit(text, (20, y))
                    y += 30
                pygame.display.flip()
        except:
            print("Критическая ошибка в редакторе. Подробности в файле:", error_log)
            input("Нажмите Enter для выхода...")
        sys.exit(1)
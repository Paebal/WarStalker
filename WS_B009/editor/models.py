# editor/models.py
# Модель данных редактора — с усиленной защитой

import math
import pygame
from .utils import rnd, clamp
from .constants import *

class EditorModel:
    def __init__(self):
        self.map_data = {
            "name": "Новая карта",
            "width": 3000,
            "height": 3000,
            "background_color": "#3a3a3a",
            "objects": [],
            "spawn": [1500, 1500]
        }
        self.current_filename = None
        self.object_counter = 0
        self.group_counter = 0
        self.dummy_counter = 0

        self.selected_indices = []
        self.hover_index = -1

        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0

        self.rgb_sliders = [255, 0, 0]

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

        self.resizing = False
        self.resize_type = None
        self.resize_index = -1
        self.resize_data = {}
        self.hover_resize = False
        self.hover_resize_type = None

        self.rotating = False
        self.rotate_index = -1

        self.dragging_object = False
        self.drag_start_world = None
        self.drag_initial_abs = {}
        self.drag_group_indices = []

        self.dragging_selection = False
        self.selection_rect_start = None
        self.selection_rect_end = None

        self.placement_mode = False
        self.placement_parent_idx = -1
        self.placement_type = None
        self.placement_dummy = False
        self.placement_ghost_obj = None

        self.group_main = {}

        self.right_panel_scroll = 0
        self.panel_scroll = 0
        self.right_panel_visible = False
        self.right_panel_rename_index = -1
        self.right_panel_rename_text = ""
        self.input_active = False
        self.input_text = ""
        self.input_param = None
        self.input_obj_index = -1
        self.show_help = False
        self.resize_input_active = False
        self.resize_width_text = ""
        self.resize_height_text = ""
        self.save_as_active = False
        self.save_as_text = ""
        self.create_child_dialog = False
        self.create_child_parent_idx = -1
        self.create_child_dialog_rect = None
        self.create_child_buttons = []

        self.slider_dragging = None
        self.slider_dragging_button = None
        self.right_panel_dragging = False
        self.right_panel_drag_index = -1
        self.right_panel_mouse_down_pos = (0, 0)

    # ==================== Геометрия ====================
    def world_to_screen(self, wx, wy, camera_x, camera_y, zoom):
        sx = (wx - camera_x) * zoom + PANEL_WIDTH
        sy = (wy - camera_y) * zoom
        return int(sx), int(sy)

    def screen_to_world(self, sx, sy, camera_x, camera_y, zoom):
        wx = (sx - PANEL_WIDTH) / zoom + camera_x
        wy = sy / zoom + camera_y
        return wx, wy

    # ==================== Группы ====================
    def get_group_main(self, group_id):
        if group_id in self.group_main:
            return self.group_main[group_id]
        for i, obj in enumerate(self.map_data["objects"]):
            if obj.get("is_group") and obj.get("id") == group_id:
                children = obj.get("children", [])
                for child_idx in children:
                    child = self.map_data["objects"][child_idx]
                    if child.get("is_main", False):
                        self.group_main[group_id] = child_idx
                        return child_idx
                if children:
                    self.group_main[group_id] = children[0]
                    return children[0]
        return None

    def set_group_main(self, group_id, new_main_idx):
        old_main = self.get_group_main(group_id)
        if old_main is not None and old_main != new_main_idx:
            old_obj = self.map_data["objects"][old_main]
            old_obj["is_main"] = False
            old_name = old_obj.get("name", "Объект")
            if not old_name.startswith("UNDGobj:"):
                old_obj["name"] = f"UNDGobj: {old_name}"
        new_obj = self.map_data["objects"][new_main_idx]
        new_obj["is_main"] = True
        new_name = new_obj.get("name", "Объект")
        if not new_name.startswith("UNDGmain:"):
            new_obj["name"] = f"UNDGmain: {new_name}"
        self.group_main[group_id] = new_main_idx
        self.recalc_local_coords(group_id, new_main_idx)

    def recalc_local_coords(self, group_id, new_main_idx):
        main_obj = self.map_data["objects"][new_main_idx]
        px, py, pa = main_obj.get("x", 0), main_obj.get("y", 0), main_obj.get("angle", 0)
        for i, obj in enumerate(self.map_data["objects"]):
            if obj.get("group_id") == group_id and i != new_main_idx:
                abs_x, abs_y, abs_a = self.get_abs_transform(i, force_main=new_main_idx)
                dx = abs_x - px
                dy = abs_y - py
                angle_rad = math.radians(pa)
                local_x = dx * math.cos(-angle_rad) - dy * math.sin(-angle_rad)
                local_y = dx * math.sin(-angle_rad) + dy * math.cos(-angle_rad)
                local_angle = abs_a - pa
                obj["local_x"] = rnd(local_x)
                obj["local_y"] = rnd(local_y)
                obj["local_angle"] = rnd(local_angle)
                obj["x"] = abs_x
                obj["y"] = abs_y
                obj["angle"] = abs_a

    def get_abs_transform(self, obj_idx, force_main=None):
        obj = self.map_data["objects"][obj_idx]
        if obj.get("group_id") is None or obj.get("is_group"):
            return obj.get("x", 0), obj.get("y", 0), obj.get("angle", 0)
        group_id = obj["group_id"]
        main_idx = force_main if force_main is not None else self.get_group_main(group_id)
        if main_idx is None:
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
        obj = self.map_data["objects"][idx]
        if obj.get("is_group"):
            obj["x"] = abs_x
            obj["y"] = abs_y
            return
        group_id = obj.get("group_id")
        if group_id is not None:
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

    # ==================== Треугольники ====================
    def validate_triangle_angles(self, alpha, beta, gamma):
        alpha = clamp(alpha, 0.01, 179.9)
        beta = clamp(beta, 0.01, 179.9)
        gamma = clamp(gamma, 0.01, 179.9)
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
        alpha = clamp(alpha, 0.01, 179.9)
        beta = clamp(beta, 0.01, 179.9)
        gamma = clamp(gamma, 0.01, 179.9)
        total = alpha + beta + gamma
        if abs(total - 180.0) > 0.01:
            diff = 180.0 - total
            alpha += diff / 3
            beta += diff / 3
            gamma += diff / 3
            alpha = clamp(alpha, 0.01, 179.9)
            beta = clamp(beta, 0.01, 179.9)
            gamma = clamp(gamma, 0.01, 179.9)
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
            cos_alpha = clamp(cos_alpha, -1, 1)
            alpha = math.degrees(math.acos(cos_alpha))
            cos_beta = (a**2 + c**2 - b**2) / (2 * a * c)
            cos_beta = clamp(cos_beta, -1, 1)
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

    # ==================== Объекты и группы ====================
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

    def create_object(self, obj_type, x, y, color, radius=None, width=None, height=None,
                     a=None, b=None, c=None, alpha=None, beta=None, gamma=None):
        """
        Создаёт словарь объекта с заполнением всех полей.
        Возвращает готовый объект или None в случае ошибки.
        """
        try:
            self.object_counter += 1
            obj = {
                "type": obj_type,
                "x": x,
                "y": y,
                "color": color if isinstance(color, tuple) else (255, 0, 0),
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
            if obj_type in ("circle", "nocollide_circle"):
                obj["radius"] = radius if radius is not None else self.new_radius
            elif obj_type in ("rect", "nocollide_rect"):
                obj["width"] = width if width is not None else self.new_width
                obj["height"] = height if height is not None else self.new_height
            elif obj_type == "triangle":
                obj["a"] = a if a is not None else self.new_a
                obj["b"] = b if b is not None else self.new_b
                obj["c"] = c if c is not None else self.new_c
                obj["alpha"] = alpha if alpha is not None else self.new_alpha
                obj["beta"] = beta if beta is not None else self.new_beta
                obj["gamma"] = gamma if gamma is not None else self.new_gamma
                # Попробуем вычислить стороны
                valid, angles = self.validate_triangle_angles(obj["alpha"], obj["beta"], obj["gamma"])
                if valid:
                    a_val = obj["a"]
                    alpha_angle, beta_angle, gamma_angle = angles
                    sides = self.compute_triangle_sides(a_val, alpha_angle, beta_angle, gamma_angle)
                    if sides is not None:
                        b_val, c_val = sides
                        obj["a"] = rnd(a_val)
                        obj["b"] = rnd(b_val)
                        obj["c"] = rnd(c_val)
                        obj["alpha"] = rnd(alpha_angle)
                        obj["beta"] = rnd(beta_angle)
                        obj["gamma"] = rnd(gamma_angle)
                        obj["valid"] = True
                    else:
                        obj["valid"] = False
                else:
                    obj["valid"] = False
            return obj
        except Exception as e:
            print("Ошибка в create_object модели:", e)
            return None

    def _create_object_data(self, obj_type, x, y, color, dummy=False):
        """Вспомогательная функция для создания объекта при размещении."""
        self.object_counter += 1
        obj = {
            "type": obj_type,
            "x": x,
            "y": y,
            "color": color if isinstance(color, tuple) else (255, 0, 0),
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
                a_val = self.new_a
                alpha_angle, beta_angle, gamma_angle = angles
                sides = self.compute_triangle_sides(a_val, alpha_angle, beta_angle, gamma_angle)
                if sides is not None:
                    b_val, c_val = sides
                    obj["a"] = rnd(a_val)
                    obj["b"] = rnd(b_val)
                    obj["c"] = rnd(c_val)
                    obj["alpha"] = rnd(alpha_angle)
                    obj["beta"] = rnd(beta_angle)
                    obj["gamma"] = rnd(gamma_angle)
                    obj["valid"] = True
                else:
                    obj["valid"] = False
            else:
                obj["valid"] = False
        return obj

    def create_group_from_parent(self, parent_idx, child_type, dummy=False):
        parent = self.map_data["objects"][parent_idx]
        if parent.get("is_group"):
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

    def get_display_name(self, obj):
        if obj.get("dummy"):
            return obj.get("name", "UNDGmain: Заглушка")
        if obj.get("is_group"):
            return obj.get("name", "UNDGmain")
        if obj.get("group_id") is not None:
            return obj.get("name", "UNDGobj")
        return obj.get("name", "Объект")

    def delete_selected(self):
        if not self.selected_indices:
            return
        to_delete = set()
        for idx in self.selected_indices:
            obj = self.map_data["objects"][idx]
            if obj.get("is_group"):
                members = self.get_group_members(obj.get("id"))
                to_delete.update(members)
            else:
                to_delete.add(idx)
        groups_to_fix = {}
        for idx in to_delete:
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
                if i not in to_delete:
                    self.set_group_main(group_id, i)
                    break
        for idx in sorted(to_delete, reverse=True):
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
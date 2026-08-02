# editor/controller.py
# Контроллер — связывает модель и представление, обрабатывает события

import pygame
import sys
import math
import subprocess
import traceback
import os
from .constants import *
from .models import EditorModel
from .views import EditorView
from .utils import rnd

class EditorController:
    def __init__(self, screen, loader, map_file=None):
        """
        :param screen: экран pygame
        :param loader: экземпляр ConfigLoader
        :param map_file: имя файла для загрузки (полный путь или имя), если None — создаётся пустая карта
        """
        self.screen = screen
        self.loader = loader
        self.model = EditorModel()
        self.view = EditorView(screen, self.model)

        # Загрузка карты
        if map_file is None:
            print("Создана новая пустая карта")
        else:
            try:
                if os.path.exists(map_file):
                    base = os.path.splitext(os.path.basename(map_file))[0]
                    user = ('usermaps' in map_file)
                    self.model.map_data = self.loader.load_map(base, user=user)
                else:
                    self.model.map_data = self.loader.load_map(map_file, user=False)
                self.model.current_filename = os.path.basename(map_file)
                print(f"Загружена карта: {self.model.current_filename}, объектов: {len(self.model.map_data.get('objects', []))}")
            except Exception as e:
                print(f"Не удалось загрузить карту {map_file}: {e}. Создана пустая карта.")

        self.running = True
        self.clock = pygame.time.Clock()
        self.dragging_camera = False
        self.camera_drag_start = (0, 0)
        self.last_click_time = 0
        self.last_click_pos = (0, 0)
        self.last_click_param = None

        self.right_panel_dragging = False
        self.right_panel_drag_index = -1
        self.right_panel_mouse_down_pos = (0, 0)

    def run(self):
        while self.running:
            self.clock.tick(60)
            try:
                self.handle_events()
                self.view.draw()
                pygame.display.flip()
            except Exception as e:
                print("Ошибка в основном цикле:")
                traceback.print_exc()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                if not pygame.display.get_window_size() == (self.screen.get_width(), self.screen.get_height()):
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE | pygame.DOUBLEBUF)
            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.handle_mouse_up(event)
            elif event.type == pygame.MOUSEMOTION:
                self.handle_mouse_motion(event)
            elif event.type == pygame.MOUSEWHEEL:
                self.handle_mouse_wheel(event)
            elif event.type == pygame.TEXTINPUT:
                if self.model.input_active:
                    self.model.input_text += event.text
                elif self.model.right_panel_rename_index >= 0:
                    self.model.right_panel_rename_text += event.text

    def handle_keydown(self, event):
        key = event.key
        if key == pygame.K_ESCAPE:
            if self.model.placement_mode:
                self.model.placement_mode = False
                self.model.placement_ghost_obj = None
                return
            if self.model.input_active:
                self.cancel_input()
            elif self.model.show_help:
                self.model.show_help = False
            elif self.model.resize_input_active:
                self.model.resize_input_active = False
            elif self.model.save_as_active:
                self.model.save_as_active = False
            elif self.model.right_panel_rename_index >= 0:
                self.model.right_panel_rename_index = -1
                self.model.right_panel_rename_text = ""
            elif self.model.create_child_dialog:
                self.model.create_child_dialog = False
            return

        if self.model.right_panel_rename_index >= 0:
            if key == pygame.K_RETURN:
                obj = self.model.map_data["objects"][self.model.right_panel_rename_index]
                old_name = obj.get("name", "")
                prefix = ""
                if old_name.startswith("UNDGmain:"):
                    prefix = "UNDGmain: "
                elif old_name.startswith("UNDGobj:"):
                    prefix = "UNDGobj: "
                new_text = self.model.right_panel_rename_text.strip()
                obj["name"] = prefix + new_text if prefix else new_text
                self.model.right_panel_rename_index = -1
                self.model.right_panel_rename_text = ""
            elif key == pygame.K_ESCAPE:
                self.model.right_panel_rename_index = -1
                self.model.right_panel_rename_text = ""
            elif key == pygame.K_BACKSPACE:
                self.model.right_panel_rename_text = self.model.right_panel_rename_text[:-1]
            return

        if key == pygame.K_1:
            self.model.new_object_type = "circle"
        elif key == pygame.K_2:
            self.model.new_object_type = "rect"
        elif key == pygame.K_3:
            self.model.new_object_type = "triangle"
        elif key == pygame.K_4:
            self.model.new_object_type = "nocollide_rect"
        elif key == pygame.K_5:
            self.model.new_object_type = "nocollide_circle"
        elif key == pygame.K_6:
            self.model.new_object_type = "dummy"
        elif key == pygame.K_F3:
            self.create_object()
        elif key == pygame.K_KP4:
            self.rotate_selected(-5)
        elif key == pygame.K_KP6:
            self.rotate_selected(5)
        elif key == pygame.K_F1:
            self.model.show_help = not self.model.show_help
        elif key == pygame.K_F2:
            self.start_resize()
        elif key == pygame.K_F5:
            self.run_game()
        elif key == pygame.K_F6:
            self.start_save_as()
        elif key == pygame.K_F7:
            self.save_overwrite()
        elif key == pygame.K_DELETE:
            self.model.delete_selected()
        elif key == pygame.K_F11:
            self.toggle_fullscreen()

        if self.model.input_active:
            if key == pygame.K_RETURN:
                self.apply_input()
            elif key == pygame.K_ESCAPE:
                self.cancel_input()
            elif key == pygame.K_BACKSPACE:
                self.model.input_text = self.model.input_text[:-1]

    def create_object(self):
        try:
            mx, my = pygame.mouse.get_pos()
            if mx < PANEL_WIDTH or mx > self.screen.get_width() - RIGHT_PANEL_TRIGGER_WIDTH:
                return

            wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)

            if self.model.new_object_type == "dummy":
                self.model.create_dummy_group(wx, wy)
                return

            obj = self.model.create_object(
                self.model.new_object_type,
                wx, wy,
                tuple(self.model.rgb_sliders)
            )
            if obj is None:
                print("Ошибка: объект не создан (модель вернула None)")
                return

            self.model.map_data["objects"].append(obj)
            self.model.selected_indices = [len(self.model.map_data["objects"]) - 1]
            if "color" in obj:
                col = obj["color"]
                if isinstance(col, str):
                    col = pygame.Color(col)
                if isinstance(col, tuple):
                    self.model.rgb_sliders = list(col[:3])
                else:
                    self.model.rgb_sliders = [255, 0, 0]
        except Exception as e:
            print("=" * 50)
            print("КРИТИЧЕСКАЯ ОШИБКА ПРИ СОЗДАНИИ ОБЪЕКТА (F3):")
            traceback.print_exc()
            print("=" * 50)

    def handle_mouse_down(self, event):
        mx, my = event.pos
        if event.button == 1:
            # Диалоги
            if self.model.resize_input_active:
                dialog_rect = pygame.Rect(self.screen.get_width()//2 - 150, self.screen.get_height()//2 - 60, 300, 120)
                if dialog_rect.collidepoint(mx, my):
                    ok_rect = pygame.Rect(dialog_rect.x+40, dialog_rect.y+90, 80, 30)
                    cancel_rect = pygame.Rect(dialog_rect.x+180, dialog_rect.y+90, 80, 30)
                    if ok_rect.collidepoint(mx, my):
                        try:
                            w = int(self.model.resize_width_text)
                            h = int(self.model.resize_height_text)
                            if w > 10 and h > 10:
                                self.model.map_data["width"] = w
                                self.model.map_data["height"] = h
                                self.model.resize_input_active = False
                        except:
                            pass
                    elif cancel_rect.collidepoint(mx, my):
                        self.model.resize_input_active = False
                    return
                else:
                    return

            if self.model.save_as_active:
                dialog_rect = pygame.Rect(self.screen.get_width()//2 - 150, self.screen.get_height()//2 - 50, 300, 100)
                if dialog_rect.collidepoint(mx, my):
                    ok_rect = pygame.Rect(dialog_rect.x+40, dialog_rect.y+90, 80, 30)
                    cancel_rect = pygame.Rect(dialog_rect.x+180, dialog_rect.y+90, 80, 30)
                    if ok_rect.collidepoint(mx, my):
                        name = self.model.save_as_text.strip()
                        if name:
                            save_objects = [obj for obj in self.model.map_data["objects"] if not obj.get("dummy")]
                            orig_objects = self.model.map_data["objects"]
                            self.model.map_data["objects"] = save_objects
                            self.loader.save_map(self.model.map_data, name, user=True)
                            self.model.map_data["objects"] = orig_objects
                            self.model.current_filename = name
                            self.model.save_as_active = False
                            print(f"Карта сохранена как {name}")
                    elif cancel_rect.collidepoint(mx, my):
                        self.model.save_as_active = False
                    return
                else:
                    return

            if self.model.create_child_dialog:
                if self.model.create_child_dialog_rect and self.model.create_child_dialog_rect.collidepoint(mx, my):
                    for rect, typ in self.model.create_child_buttons:
                        if rect.collidepoint(mx, my):
                            if self.model.create_child_parent_idx >= 0:
                                self.model.placement_mode = True
                                self.model.placement_parent_idx = self.model.create_child_parent_idx
                                self.model.placement_type = typ
                                self.model.placement_dummy = (typ == "dummy")
                                parent = self.model.map_data["objects"][self.model.create_child_parent_idx]
                                color = parent.get("color", (255,0,0))
                                if self.model.placement_dummy:
                                    color = (0, 255, 0)
                                ghost = self.model._create_object_data(typ, 0, 0, color, self.model.placement_dummy)
                                ghost["x"] = 0
                                ghost["y"] = 0
                                self.model.placement_ghost_obj = ghost
                                self.model.create_child_dialog = False
                                return
                else:
                    self.model.create_child_dialog = False
                return

            # Правая панель
            if self.model.right_panel_visible and self.screen.get_width() - RIGHT_PANEL_WIDTH <= mx <= self.screen.get_width():
                objects = self.model.map_data["objects"]
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
                item_height = 28
                padding = 5
                list_start_y = 40
                scroll = self.model.right_panel_scroll
                rel_y = my - list_start_y
                item_idx = rel_y // (item_height + padding) + scroll
                if 0 <= item_idx < len(display_items):
                    idx, indent, is_group, is_collapsed = display_items[item_idx]
                    if idx >= len(objects):
                        return
                    if is_group:
                        rect = pygame.Rect(self.screen.get_width() - RIGHT_PANEL_WIDTH + 5 + indent * INDENT_WIDTH,
                                           list_start_y + (item_idx - scroll) * (item_height + padding), 20, item_height)
                        if rect.collidepoint(mx, my):
                            obj = objects[idx]
                            obj["collapsed"] = not obj.get("collapsed", False)
                            return
                    if objects[idx].get("is_group"):
                        self.model.select_object_with_children(idx)
                    else:
                        self.model.selected_indices = [idx]
                        obj = objects[idx]
                        col = obj.get("color", (255,0,0))
                        if isinstance(col, str):
                            col = pygame.Color(col)
                        if isinstance(col, tuple):
                            self.model.rgb_sliders = list(col[:3])
                return

            # Левая панель
            if mx < PANEL_WIDTH:
                self.handle_panel_click(mx, my)
                return

            # Если в режиме размещения, ЛКМ отменяет
            if self.model.placement_mode:
                self.model.placement_mode = False
                self.model.placement_ghost_obj = None
                return

            # Проверка на ресайз
            if self.model.hover_resize and self.model.selected_indices:
                idx = self.model.selected_indices[0]
                if idx >= len(self.model.map_data["objects"]):
                    return
                obj = self.model.map_data["objects"][idx]
                self.model.resizing = True
                self.model.resize_index = idx
                self.model.resize_type = self.model.hover_resize_type
                self.model.resize_data = {}
                obj_type = obj.get("type")
                if obj_type in ("circle", "nocollide_circle") and self.model.hover_resize_type == "circle_radius":
                    self.model.resize_data["start_radius"] = obj.get("radius", 30)
                elif obj_type in ("rect", "nocollide_rect") and self.model.hover_resize_type == "rect_side":
                    corners = self.model.get_rect_corners(obj)
                    top_center = ((corners[0][0]+corners[1][0])/2, (corners[0][1]+corners[1][1])/2)
                    bottom_center = ((corners[3][0]+corners[2][0])/2, (corners[3][1]+corners[2][1])/2)
                    left_center = ((corners[0][0]+corners[3][0])/2, (corners[0][1]+corners[3][1])/2)
                    right_center = ((corners[1][0]+corners[2][0])/2, (corners[1][1]+corners[2][1])/2)
                    wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    dists = {
                        "top": math.hypot(wx - top_center[0], wy - top_center[1]),
                        "bottom": math.hypot(wx - bottom_center[0], wy - bottom_center[1]),
                        "left": math.hypot(wx - left_center[0], wy - left_center[1]),
                        "right": math.hypot(wx - right_center[0], wy - right_center[1])
                    }
                    side = min(dists, key=dists.get)
                    self.model.resize_data["side"] = side
                    self.model.resize_data["start_width"] = obj.get("width", 60)
                    self.model.resize_data["start_height"] = obj.get("height", 40)
                    self.model.resize_data["start_x"] = obj.get("x", 0)
                    self.model.resize_data["start_y"] = obj.get("y", 0)
                    self.model.resize_data["start_mx"], self.model.resize_data["start_my"] = mx, my
                elif obj_type == "triangle":
                    if self.model.hover_resize_type == "triangle_side":
                        vertices = self.model.get_triangle_vertices(obj)
                        if vertices:
                            mid_ab = ((vertices[0][0]+vertices[1][0])/2, (vertices[0][1]+vertices[1][1])/2)
                            mid_bc = ((vertices[1][0]+vertices[2][0])/2, (vertices[1][1]+vertices[2][1])/2)
                            mid_ca = ((vertices[2][0]+vertices[0][0])/2, (vertices[2][1]+vertices[0][1])/2)
                            wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
                            dists = {
                                "a": math.hypot(wx - mid_ab[0], wy - mid_ab[1]),
                                "b": math.hypot(wx - mid_bc[0], wy - mid_bc[1]),
                                "c": math.hypot(wx - mid_ca[0], wy - mid_ca[1])
                            }
                            side = min(dists, key=dists.get)
                            self.model.resize_data["side"] = side
                            self.model.resize_data["start_a"] = obj.get("a", 60.0)
                            self.model.resize_data["start_b"] = obj.get("b", 60.0)
                            self.model.resize_data["start_c"] = obj.get("c", 60.0)
                            self.model.resize_data["start_mx"], self.model.resize_data["start_my"] = mx, my
                    elif self.model.hover_resize_type == "triangle_vertex":
                        vertices = self.model.get_triangle_vertices(obj)
                        if vertices:
                            wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
                            best_idx = 0
                            best_dist = math.hypot(wx - vertices[0][0], wy - vertices[0][1])
                            for i in range(1, 3):
                                d = math.hypot(wx - vertices[i][0], wy - vertices[i][1])
                                if d < best_dist:
                                    best_dist = d
                                    best_idx = i
                            self.model.resize_data["vertex_idx"] = best_idx
                            self.model.resize_data["start_vertices"] = vertices
                            self.model.resize_data["current_vx"] = vertices[best_idx][0]
                            self.model.resize_data["current_vy"] = vertices[best_idx][1]
                self.model.hover_resize = False
                return

            # Двойной клик
            now = pygame.time.get_ticks()
            if (now - self.last_click_time < 500 and
                abs(mx - self.last_click_pos[0]) < 10 and
                abs(my - self.last_click_pos[1]) < 10):
                wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
                if self.model.selected_indices:
                    idx = self.model.selected_indices[0]
                    if idx < len(self.model.map_data["objects"]):
                        obj = self.model.map_data["objects"][idx]
                        if obj.get("group_id") is not None and not obj.get("is_group"):
                            abs_x, abs_y, _ = self.model.get_abs_transform(idx)
                        else:
                            abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                        cx, cy = abs_x, abs_y
                        if math.hypot(wx - cx, wy - cy) < 15 / self.model.zoom:
                            self.model.rotating = True
                            self.model.rotate_index = idx
                            self.model.rotate_start_angle = obj.get("angle", 0)
                            self.last_click_time = 0
                            self.last_click_param = None
                            return
                idx2, part_type, part_idx = self.get_triangle_part_at_pos(wx, wy)
                if idx2 is not None and part_type == "vertex":
                    param_map = {0: "alpha", 1: "beta", 2: "gamma"}
                    param_key = param_map.get(part_idx)
                    if param_key is not None:
                        obj = self.model.map_data["objects"][idx2]
                        val = obj.get(param_key, 60.0)
                        self.model.input_active = True
                        self.model.input_text = str(val)
                        self.model.input_param = param_key
                        self.model.input_obj_index = idx2
                        self.last_click_time = 0
                        self.last_click_param = None
                        return
            self.last_click_time = now
            self.last_click_pos = (mx, my)
            self.last_click_param = None

            if not self.model.input_active and not self.model.rotating:
                self.dragging_camera = True
                self.camera_drag_start = (mx, my)

        elif event.button == 3:
            # ПКМ — если в режиме размещения, фиксируем объект
            if self.model.placement_mode:
                wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
                parent_idx = self.model.placement_parent_idx
                if parent_idx >= len(self.model.map_data["objects"]):
                    self.model.placement_mode = False
                    self.model.placement_ghost_obj = None
                    return
                parent = self.model.map_data["objects"][parent_idx]
                if parent.get("is_group"):
                    group_id = parent["id"]
                    self.model.object_counter += 1
                    new_obj = self.model._create_object_data(self.model.placement_type, wx, wy, parent.get("color", (255,0,0)), self.model.placement_dummy)
                    new_obj["group_id"] = group_id
                    main_idx = self.model.get_group_main(group_id)
                    if main_idx is not None:
                        main_obj = self.model.map_data["objects"][main_idx]
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
                    self.model.map_data["objects"].append(new_obj)
                    new_idx = len(self.model.map_data["objects"]) - 1
                    parent["children"].append(new_idx)
                    self.model.selected_indices = [new_idx]
                    self.model.rgb_sliders = list(new_obj["color"][:3])
                else:
                    self.model.group_counter += 1
                    group_id = self.model.group_counter
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
                    self.model.object_counter += 1
                    new_obj = self.model._create_object_data(self.model.placement_type, wx, wy, parent.get("color", (255,0,0)), self.model.placement_dummy)
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
                    self.model.map_data["objects"].append(new_obj)
                    new_idx = len(self.model.map_data["objects"]) - 1
                    parent["children"].append(new_idx)
                    self.model.group_main[group_id] = parent_idx
                    self.model.selected_indices = [new_idx]
                    self.model.rgb_sliders = list(new_obj["color"][:3])
                self.model.placement_mode = False
                self.model.placement_ghost_obj = None
                return

            # Правая панель — переименование
            if self.model.right_panel_visible and self.screen.get_width() - RIGHT_PANEL_WIDTH <= mx <= self.screen.get_width():
                objects = self.model.map_data["objects"]
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
                item_height = 28
                padding = 5
                list_start_y = 40
                scroll = self.model.right_panel_scroll
                rel_y = my - list_start_y
                item_idx = rel_y // (item_height + padding) + scroll
                if 0 <= item_idx < len(display_items):
                    idx, indent, is_group, is_collapsed = display_items[item_idx]
                    if idx < len(objects):
                        self.model.right_panel_rename_index = idx
                        self.model.right_panel_rename_text = objects[idx].get("name", "")
                        self.right_panel_drag_index = idx
                        self.right_panel_mouse_down_pos = (mx, my)
                return

            # Левая панель — слайдеры правой кнопкой
            if mx < PANEL_WIDTH:
                for i, (rect, idx) in enumerate(self.view.slider_rects):
                    if rect.collidepoint(mx, my):
                        self.model.slider_dragging = i
                        self.model.slider_dragging_button = 3
                        return
                return

            # Выделение на карте
            wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)

            # Shift+ПКМ — смена главного
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                found = -1
                for i in range(len(self.model.map_data["objects"])):
                    obj = self.model.map_data["objects"][i]
                    if obj.get("group_id") is not None and not obj.get("is_group"):
                        abs_x, abs_y, _ = self.model.get_abs_transform(i)
                    else:
                        abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                    dist = math.hypot(wx - abs_x, wy - abs_y)
                    if dist < 30:
                        found = i
                        break
                if found >= 0:
                    obj = self.model.map_data["objects"][found]
                    if obj.get("group_id") is not None:
                        group_id = obj["group_id"]
                        if group_id is not None:
                            self.model.set_group_main(group_id, found)
                            self.model.selected_indices = [found]
                            col = obj.get("color", (255,0,0))
                            if isinstance(col, str):
                                col = pygame.Color(col)
                            if isinstance(col, tuple):
                                self.model.rgb_sliders = list(col[:3])
                            return
                self.model.dragging_selection = True
                self.model.selection_rect_start = (wx, wy)
                self.model.selection_rect_end = (wx, wy)
                return

            # Обычное выделение
            found = -1
            for i in range(len(self.model.map_data["objects"])):
                obj = self.model.map_data["objects"][i]
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.model.get_abs_transform(i)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                dist = math.hypot(wx - abs_x, wy - abs_y)
                if dist < 30:
                    found = i
                    break

            if found >= 0:
                if self.model.map_data["objects"][found].get("is_group"):
                    self.model.select_object_with_children(found)
                else:
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        if found not in self.model.selected_indices:
                            self.model.selected_indices.append(found)
                    else:
                        self.model.selected_indices = [found]
                    obj = self.model.map_data["objects"][found]
                    col = obj.get("color", (255,0,0))
                    if isinstance(col, str):
                        col = pygame.Color(col)
                    if isinstance(col, tuple):
                        self.model.rgb_sliders = list(col[:3])
                if len(self.model.selected_indices) >= 1:
                    self.model.dragging_object = True
                    self.model.drag_start_world = (wx, wy)
                    self.model.drag_initial_abs = {}
                    self.model.drag_group_indices = []
                    has_main = False
                    main_group_ids = set()
                    for idx in self.model.selected_indices:
                        if idx < len(self.model.map_data["objects"]):
                            obj = self.model.map_data["objects"][idx]
                            if obj.get("is_main", False):
                                has_main = True
                                main_group_ids.add(obj.get("id"))
                    if has_main:
                        for gid in main_group_ids:
                            for i, o in enumerate(self.model.map_data["objects"]):
                                if o.get("group_id") == gid or (o.get("is_group") and o.get("id") == gid):
                                    if i not in self.model.drag_group_indices:
                                        self.model.drag_group_indices.append(i)
                    else:
                        self.model.drag_group_indices = self.model.selected_indices[:]
                    for idx in self.model.drag_group_indices:
                        if idx < len(self.model.map_data["objects"]):
                            ax, ay, _ = self.model.get_abs_transform(idx)
                            self.model.drag_initial_abs[idx] = (ax, ay)
            else:
                self.model.dragging_selection = True
                self.model.selection_rect_start = (wx, wy)
                self.model.selection_rect_end = (wx, wy)

    def handle_mouse_up(self, event):
        if event.button == 1:
            self.dragging_camera = False
            if self.model.slider_dragging is not None and self.model.slider_dragging_button == 1:
                self.model.slider_dragging = None
                self.model.slider_dragging_button = None
            if self.model.rotating:
                self.model.rotating = False
                self.model.rotate_index = -1
            if self.model.resizing:
                if self.model.resize_type == "triangle_vertex":
                    obj = self.model.map_data["objects"][self.model.resize_index]
                    vertex_idx = self.model.resize_data["vertex_idx"]
                    target_vx = self.model.resize_data["current_vx"]
                    target_vy = self.model.resize_data["current_vy"]
                    start_vertices = self.model.resize_data["start_vertices"]
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
                    success = self.model.set_triangle_from_points(obj, target_points)
                    if not success:
                        obj["valid"] = False
                self.model.resizing = False
                self.model.resize_type = None
                self.model.resize_data = {}
        elif event.button == 3:
            if self.model.slider_dragging is not None and self.model.slider_dragging_button == 3:
                self.model.slider_dragging = None
                self.model.slider_dragging_button = None

            if self.right_panel_dragging:
                from_idx = self.right_panel_drag_index
                mx, my = pygame.mouse.get_pos()
                objects = self.model.map_data["objects"]
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
                    item_height = 28
                    padding = 5
                    list_start_y = 40
                    scroll = self.model.right_panel_scroll
                    rel_y = my - list_start_y
                    to_item_idx = rel_y // (item_height + padding) + scroll
                    if 0 <= to_item_idx < len(display_items):
                        to_idx, _, _, _ = display_items[to_item_idx]
                        if to_idx != from_idx and to_idx < len(objects):
                            obj = objects.pop(from_idx)
                            objects.insert(to_idx, obj)
                            self.model.selected_indices = [to_idx]
                self.right_panel_dragging = False
                self.right_panel_drag_index = -1
                self.model.right_panel_rename_index = -1
                self.model.right_panel_rename_text = ""
            else:
                if self.model.right_panel_rename_index >= 0:
                    pass

            if self.model.dragging_selection:
                self.model.dragging_selection = False
                if self.model.selection_rect_start and self.model.selection_rect_end:
                    x1, y1 = self.model.selection_rect_start
                    x2, y2 = self.model.selection_rect_end
                    left = min(x1, x2)
                    right = max(x1, x2)
                    top = min(y1, y2)
                    bottom = max(y1, y2)
                    new_selection = []
                    for i, obj in enumerate(self.model.map_data["objects"]):
                        if obj.get("group_id") is not None and not obj.get("is_group"):
                            abs_x, abs_y, _ = self.model.get_abs_transform(i)
                        else:
                            abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                        if left <= abs_x <= right and top <= abs_y <= bottom:
                            new_selection.append(i)
                    if new_selection:
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            for idx in new_selection:
                                if idx not in self.model.selected_indices:
                                    self.model.selected_indices.append(idx)
                        else:
                            first = new_selection[0]
                            if self.model.map_data["objects"][first].get("is_group"):
                                self.model.select_object_with_children(first)
                            else:
                                self.model.selected_indices = new_selection
                        if self.model.selected_indices:
                            obj = self.model.map_data["objects"][self.model.selected_indices[0]]
                            col = obj.get("color", (255,0,0))
                            if isinstance(col, str):
                                col = pygame.Color(col)
                            if isinstance(col, tuple):
                                self.model.rgb_sliders = list(col[:3])
                    else:
                        if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                            self.model.selected_indices = []
                    self.model.selection_rect_start = None
                    self.model.selection_rect_end = None
            if self.model.dragging_object:
                self.model.dragging_object = False
                self.model.drag_start_world = None
                self.model.drag_initial_abs = {}
                self.model.drag_group_indices = []

    def handle_mouse_motion(self, event):
        mx, my = event.pos

        if mx > self.screen.get_width() - RIGHT_PANEL_TRIGGER_WIDTH:
            self.model.right_panel_visible = True
        elif mx < self.screen.get_width() - RIGHT_PANEL_WIDTH - 10:
            self.model.right_panel_visible = False

        if self.model.right_panel_rename_index >= 0 and pygame.mouse.get_pressed()[2]:
            dx = mx - self.right_panel_mouse_down_pos[0]
            dy = my - self.right_panel_mouse_down_pos[1]
            if abs(dx) > 5 or abs(dy) > 5:
                self.model.right_panel_rename_index = -1
                self.model.right_panel_rename_text = ""
                self.right_panel_dragging = True
                self.right_panel_drag_index = self.model.right_panel_rename_index

        if self.model.rotating and self.model.rotate_index >= 0:
            if self.model.rotate_index < len(self.model.map_data["objects"]):
                obj = self.model.map_data["objects"][self.model.rotate_index]
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.model.get_abs_transform(self.model.rotate_index)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                cx, cy = abs_x, abs_y
                wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
                dx = wx - cx
                dy = wy - cy
                if math.hypot(dx, dy) > 5:
                    new_angle = math.degrees(math.atan2(dy, dx))
                    if obj.get("group_id") is not None and not obj.get("is_group"):
                        group_id = obj["group_id"]
                        main_idx = self.model.get_group_main(group_id)
                        if main_idx is not None:
                            parent_obj = self.model.map_data["objects"][main_idx]
                            pa = parent_obj.get("angle", 0)
                            obj["local_angle"] = rnd(new_angle - pa)
                        else:
                            obj["angle"] = rnd(new_angle)
                    else:
                        obj["angle"] = rnd(new_angle)

        if self.dragging_camera:
            dx = mx - self.camera_drag_start[0]
            dy = my - self.camera_drag_start[1]
            self.model.camera_x -= dx / self.model.zoom
            self.model.camera_y -= dy / self.model.zoom
            self.camera_drag_start = (mx, my)

        if self.model.dragging_object and self.model.drag_start_world is not None:
            wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
            dx = wx - self.model.drag_start_world[0]
            dy = wy - self.model.drag_start_world[1]
            for idx in list(self.model.drag_group_indices):
                if idx not in self.model.drag_initial_abs:
                    continue
                if idx >= len(self.model.map_data["objects"]):
                    continue
                init_ax, init_ay = self.model.drag_initial_abs[idx]
                new_ax = init_ax + dx
                new_ay = init_ay + dy
                self.model.set_abs_position(idx, new_ax, new_ay)

        if self.model.resizing and self.model.resize_index >= 0:
            if self.model.resize_index >= len(self.model.map_data["objects"]):
                return
            obj = self.model.map_data["objects"][self.model.resize_index]
            obj_type = obj.get("type")
            if obj_type in ("circle", "nocollide_circle") and self.model.resize_type == "circle_radius":
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.model.get_abs_transform(self.model.resize_index)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                sx, sy = self.model.world_to_screen(abs_x, abs_y, self.model.camera_x, self.model.camera_y, self.model.zoom)
                dist = math.hypot(mx - sx, my - sy)
                if dist > 5:
                    new_radius = max(1, dist / self.model.zoom)
                    obj["radius"] = rnd(new_radius)
            elif obj_type in ("rect", "nocollide_rect") and self.model.resize_type == "rect_side":
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.model.get_abs_transform(self.model.resize_index)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                sx, sy = self.model.world_to_screen(abs_x, abs_y, self.model.camera_x, self.model.camera_y, self.model.zoom)
                side = self.model.resize_data["side"]
                start_w = self.model.resize_data["start_width"]
                start_h = self.model.resize_data["start_height"]
                start_x = self.model.resize_data["start_x"]
                start_y = self.model.resize_data["start_y"]
                start_mx = self.model.resize_data["start_mx"]
                start_my = self.model.resize_data["start_my"]
                dx = (mx - start_mx) / self.model.zoom
                dy = (my - start_my) / self.model.zoom
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
                if self.model.resize_type == "triangle_side":
                    if obj.get("group_id") is not None and not obj.get("is_group"):
                        abs_x, abs_y, _ = self.model.get_abs_transform(self.model.resize_index)
                    else:
                        abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                    sx, sy = self.model.world_to_screen(abs_x, abs_y, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    side = self.model.resize_data["side"]
                    start_mx = self.model.resize_data["start_mx"]
                    start_my = self.model.resize_data["start_my"]
                    dx = (mx - start_mx) / self.model.zoom
                    dy = (my - start_my) / self.model.zoom
                    if side == "a":
                        new_a = max(1, self.model.resize_data["start_a"] + dx * 2)
                        obj["a"] = rnd(new_a)
                        self.model.update_triangle_from_angles(obj)
                    elif side == "b":
                        alpha = obj.get("alpha", 60)
                        beta = obj.get("beta", 60)
                        gamma = obj.get("gamma", 60)
                        old_b = self.model.resize_data["start_b"]
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
                        old_c = self.model.resize_data["start_c"]
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
                elif self.model.resize_type == "triangle_vertex":
                    wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    self.model.resize_data["current_vx"] = wx
                    self.model.resize_data["current_vy"] = wy

        if self.model.dragging_selection:
            wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
            self.model.selection_rect_end = (wx, wy)

        if not self.model.dragging_object and not self.model.resizing and not self.model.rotating:
            wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
            self.model.hover_index = -1
            for i in range(len(self.model.map_data["objects"])-1, -1, -1):
                obj = self.model.map_data["objects"][i]
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.model.get_abs_transform(i)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                dist = math.hypot(wx - abs_x, wy - abs_y)
                if dist < 30:
                    self.model.hover_index = i
                    break

        if self.model.slider_dragging is not None:
            pressed = pygame.mouse.get_pressed()
            if (self.model.slider_dragging_button == 1 and not pressed[0]) or \
               (self.model.slider_dragging_button == 3 and not pressed[2]):
                self.model.slider_dragging = None
                self.model.slider_dragging_button = None
                return
            if self.model.selected_indices:
                slider_rect, idx = self.view.slider_rects[self.model.slider_dragging]
                rel_x = mx - (PANEL_WIDTH + slider_rect.x)
                val = max(0, min(255, int((rel_x / slider_rect.w) * 255)))
                self.model.rgb_sliders[self.model.slider_dragging] = val
                for i in self.model.selected_indices:
                    if i < len(self.model.map_data["objects"]):
                        obj = self.model.map_data["objects"][i]
                        obj["color"] = tuple(self.model.rgb_sliders)

        if not self.model.resizing and self.model.selected_indices:
            idx = self.model.selected_indices[0]
            if idx >= len(self.model.map_data["objects"]):
                return
            obj = self.model.map_data["objects"][idx]
            obj_type = obj.get("type")
            self.model.hover_resize = False
            self.model.hover_resize_type = None
            if obj.get("group_id") is not None and not obj.get("is_group"):
                abs_x, abs_y, _ = self.model.get_abs_transform(idx)
            else:
                abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
            sx, sy = self.model.world_to_screen(abs_x, abs_y, self.model.camera_x, self.model.camera_y, self.model.zoom)

            if obj_type in ("circle", "nocollide_circle"):
                radius = obj.get("radius", 30) * self.model.zoom
                dist = math.hypot(mx - sx, my - sy)
                if abs(dist - radius) < 20:
                    self.model.hover_resize = True
                    self.model.hover_resize_type = "circle_radius"
            elif obj_type in ("rect", "nocollide_rect"):
                corners = self.model.get_rect_corners(obj)
                top_center = ((corners[0][0]+corners[1][0])/2, (corners[0][1]+corners[1][1])/2)
                bottom_center = ((corners[3][0]+corners[2][0])/2, (corners[3][1]+corners[2][1])/2)
                left_center = ((corners[0][0]+corners[3][0])/2, (corners[0][1]+corners[3][1])/2)
                right_center = ((corners[1][0]+corners[2][0])/2, (corners[1][1]+corners[2][1])/2)
                side_points = [("top", top_center), ("bottom", bottom_center), ("left", left_center), ("right", right_center)]
                for (label, (cx, cy)) in side_points:
                    scx, scy = self.model.world_to_screen(cx, cy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    if math.hypot(mx - scx, my - scy) < 15:
                        self.model.hover_resize = True
                        self.model.hover_resize_type = "rect_side"
                        break
            elif obj_type == "triangle":
                vertices = self.model.get_triangle_vertices(obj)
                if not vertices:
                    return
                mid_ab = ((vertices[0][0]+vertices[1][0])/2, (vertices[0][1]+vertices[1][1])/2)
                mid_bc = ((vertices[1][0]+vertices[2][0])/2, (vertices[1][1]+vertices[2][1])/2)
                mid_ca = ((vertices[2][0]+vertices[0][0])/2, (vertices[2][1]+vertices[0][1])/2)
                side_points = [("a", mid_ab), ("b", mid_bc), ("c", mid_ca)]
                for (label, (cx, cy)) in side_points:
                    scx, scy = self.model.world_to_screen(cx, cy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    if math.hypot(mx - scx, my - scy) < 15:
                        self.model.hover_resize = True
                        self.model.hover_resize_type = "triangle_side"
                        break
                if not self.model.hover_resize:
                    for i, (vx, vy) in enumerate(vertices):
                        scx, scy = self.model.world_to_screen(vx, vy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                        if math.hypot(mx - scx, my - scy) < 15:
                            self.model.hover_resize = True
                            self.model.hover_resize_type = "triangle_vertex"
                            break

    def handle_mouse_wheel(self, event):
        mx, my = pygame.mouse.get_pos()
        if mx < PANEL_WIDTH:
            self.model.panel_scroll -= event.y * 20
            return
        if self.model.right_panel_visible and self.screen.get_width() - RIGHT_PANEL_WIDTH <= mx <= self.screen.get_width():
            self.model.right_panel_scroll -= event.y
            return
        if mx > PANEL_WIDTH and mx < self.screen.get_width() - RIGHT_PANEL_TRIGGER_WIDTH:
            wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
            zoom_factor = 1.1 if event.y > 0 else 0.9
            self.model.zoom *= zoom_factor
            self.model.zoom = max(0.1, min(10.0, self.model.zoom))
            self.model.camera_x = wx - (mx - PANEL_WIDTH) / self.model.zoom
            self.model.camera_y = wy - my / self.model.zoom

    def handle_panel_click(self, mx, my):
        for rect, typ in self.view.icon_rects:
            if rect.collidepoint(mx, my):
                self.model.new_object_type = typ
                return
        for rect, col in self.view.color_rects:
            if rect.collidepoint(mx, my):
                if self.model.selected_indices:
                    self.model.rgb_sliders = list(col[:3])
                    for i in self.model.selected_indices:
                        if i < len(self.model.map_data["objects"]):
                            self.model.map_data["objects"][i]["color"] = tuple(self.model.rgb_sliders)
                return
        for i, (rect, idx) in enumerate(self.view.slider_rects):
            if rect.collidepoint(mx, my):
                self.model.slider_dragging = i
                self.model.slider_dragging_button = 1
                return
        if self.view.checkbox_rect and self.view.checkbox_rect.collidepoint(mx, my):
            self.model.fine_tune = not self.model.fine_tune
            return
        for rect, action in self.view.button_rects:
            if rect.collidepoint(mx, my):
                if action == "help":
                    self.model.show_help = not self.model.show_help
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
                return
        if self.view.create_child_button_rect and self.view.create_child_button_rect.collidepoint(mx, my):
            if self.model.selected_indices:
                parent_idx = self.model.selected_indices[0]
                if parent_idx < len(self.model.map_data["objects"]):
                    parent = self.model.map_data["objects"][parent_idx]
                    if parent.get("is_group") or parent.get("group_id") is None:
                        self.model.create_child_dialog = True
                        self.model.create_child_parent_idx = parent_idx
                        self.model.create_child_selected_type = "circle"
                        self.model.create_child_dialog_rect = pygame.Rect(self.screen.get_width()//2 - 100, self.screen.get_height()//2 - 100, 200, 200)
                        self.model.create_child_buttons = []
                        types = ["circle", "rect", "triangle", "nocollide_rect", "nocollide_circle", "dummy"]
                        labels = ["Круг", "Прям.", "Треуг.", "Прям. без", "Круг без", "Заглушка"]
                        y = self.model.create_child_dialog_rect.y + 30
                        for i, typ in enumerate(types):
                            btn_rect = pygame.Rect(self.model.create_child_dialog_rect.x + 20, y, 160, 30)
                            self.model.create_child_buttons.append((btn_rect, typ))
                            y += 35

    def rotate_selected(self, delta):
        if not self.model.selected_indices:
            return
        for idx in self.model.selected_indices:
            if idx >= len(self.model.map_data["objects"]):
                continue
            obj = self.model.map_data["objects"][idx]
            if obj.get("group_id") is not None and not obj.get("is_group"):
                obj["local_angle"] = rnd(obj.get("local_angle", 0) + delta)
            else:
                obj["angle"] = rnd((obj.get("angle", 0) + delta) % 360)

    def get_triangle_part_at_pos(self, wx, wy, threshold=20):
        for idx in self.model.selected_indices:
            obj = self.model.map_data["objects"][idx]
            if obj.get("type") != "triangle":
                continue
            if not obj.get("valid", True):
                continue
            if obj.get("group_id") is not None:
                abs_x, abs_y, _ = self.model.get_abs_transform(idx)
                orig_x, orig_y = obj.get("x", 0), obj.get("y", 0)
                obj["x"], obj["y"] = abs_x, abs_y
                vertices = self.model.get_triangle_vertices(obj)
                obj["x"], obj["y"] = orig_x, orig_y
            else:
                vertices = self.model.get_triangle_vertices(obj)
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

    def start_resize(self):
        self.model.resize_input_active = True
        self.model.resize_width_text = str(self.model.map_data["width"])
        self.model.resize_height_text = str(self.model.map_data["height"])

    def run_game(self):
        temp_name = "_temp_editor"
        save_objects = [obj for obj in self.model.map_data["objects"] if not obj.get("dummy")]
        orig_objects = self.model.map_data["objects"]
        self.model.map_data["objects"] = save_objects
        self.loader.save_map(self.model.map_data, temp_name, user=True)
        self.model.map_data["objects"] = orig_objects
        try:
            subprocess.Popen([sys.executable, "main.py", "--map", temp_name])
        except Exception as e:
            print("Ошибка запуска игры:", e)

    def start_save_as(self):
        self.model.save_as_active = True
        self.model.save_as_text = ""

    def save_overwrite(self):
        if self.model.current_filename:
            save_objects = [obj for obj in self.model.map_data["objects"] if not obj.get("dummy")]
            orig_objects = self.model.map_data["objects"]
            self.model.map_data["objects"] = save_objects
            self.loader.save_map(self.model.map_data, self.model.current_filename, user=True)
            self.model.map_data["objects"] = orig_objects
            print(f"Карта сохранена как {self.model.current_filename}")
        else:
            self.start_save_as()

    def toggle_fullscreen(self):
        fullscreen = not pygame.display.get_surface().get_flags() & pygame.FULLSCREEN
        if fullscreen:
            self.screen = pygame.display.set_mode((self.screen.get_width(), self.screen.get_height()), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((self.screen.get_width(), self.screen.get_height()), pygame.RESIZABLE | pygame.DOUBLEBUF)

    def apply_input(self):
        if self.model.input_active and self.model.input_obj_index >= 0:
            if self.model.input_obj_index >= len(self.model.map_data["objects"]):
                self.cancel_input()
                return
            obj = self.model.map_data["objects"][self.model.input_obj_index]
            try:
                val = float(self.model.input_text)
                if self.model.input_param in ["r", "g", "b"]:
                    idx = 0 if self.model.input_param=="r" else 1 if self.model.input_param=="g" else 2
                    self.model.rgb_sliders[idx] = max(0, min(255, int(val)))
                    for i in self.model.selected_indices:
                        if i < len(self.model.map_data["objects"]):
                            self.model.map_data["objects"][i]["color"] = tuple(self.model.rgb_sliders)
                elif self.model.input_param in ["local_x", "local_y", "local_angle"]:
                    if self.model.input_param == "local_x":
                        obj["local_x"] = rnd(val)
                    elif self.model.input_param == "local_y":
                        obj["local_y"] = rnd(val)
                    elif self.model.input_param == "local_angle":
                        obj["local_angle"] = rnd(val)
                elif self.model.input_param in ["radius", "width", "height", "angle"]:
                    for i in self.model.selected_indices:
                        if i >= len(self.model.map_data["objects"]):
                            continue
                        o = self.model.map_data["objects"][i]
                        if self.model.input_param == "radius":
                            o["radius"] = rnd(max(1, val))
                        elif self.model.input_param == "width":
                            o["width"] = rnd(max(1, val))
                        elif self.model.input_param == "height":
                            o["height"] = rnd(max(1, val))
                        elif self.model.input_param == "angle":
                            o["angle"] = rnd(val % 360)
                elif self.model.input_param in ["a", "b", "c", "alpha", "beta", "gamma"]:
                    for i in self.model.selected_indices:
                        if i >= len(self.model.map_data["objects"]):
                            continue
                        o = self.model.map_data["objects"][i]
                        if o.get("type") == "triangle":
                            if self.model.input_param == "a":
                                o["a"] = rnd(max(1, val))
                                self.model.update_triangle_from_angles(o)
                            elif self.model.input_param == "b":
                                o["b"] = rnd(max(1, val))
                                self.model.update_triangle_from_angles(o)
                            elif self.model.input_param == "c":
                                o["c"] = rnd(max(1, val))
                                self.model.update_triangle_from_angles(o)
                            elif self.model.input_param == "alpha":
                                if self.model.fine_tune:
                                    o["alpha"] = rnd(val)
                                    self.model.update_triangle_from_angles(o)
                                else:
                                    delta = val - o.get("alpha", 60)
                                    self.model.correct_angles(o, "alpha", delta)
                            elif self.model.input_param == "beta":
                                if self.model.fine_tune:
                                    o["beta"] = rnd(val)
                                    self.model.update_triangle_from_angles(o)
                                else:
                                    delta = val - o.get("beta", 60)
                                    self.model.correct_angles(o, "beta", delta)
                            elif self.model.input_param == "gamma":
                                if self.model.fine_tune:
                                    o["gamma"] = rnd(val)
                                    self.model.update_triangle_from_angles(o)
                                else:
                                    delta = val - o.get("gamma", 60)
                                    self.model.correct_angles(o, "gamma", delta)
            except:
                pass
        self.cancel_input()

    def cancel_input(self):
        self.model.input_active = False
        self.model.input_text = ""
        self.model.input_param = None
        self.model.input_obj_index = -1
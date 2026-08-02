# editor/views.py
# Представление — отрисовка всех элементов редактора

import pygame
from .constants import *
from .utils import rnd

class EditorView:
    def __init__(self, screen, model):
        self.screen = screen
        self.model = model
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_bold = pygame.font.Font(None, 28)

        # Эти атрибуты будут заполнены в draw_panel
        self.icon_rects = []
        self.color_rects = []
        self.slider_rects = []
        self.checkbox_rect = None
        self.button_rects = []
        self.param_rects = []
        self.collapse_buttons = []
        self.create_child_button_rect = None

    def draw(self):
        self.screen.fill(COLOR_BG)
        self.draw_grid()
        self.draw_objects()
        self.draw_selection_rect()
        self.draw_panel()
        self.draw_right_panel()
        self.draw_cursor()
        self.draw_dialogs()
        self.draw_placement_ghost()

    def draw_grid(self):
        step = 50 * self.model.zoom
        left = self.model.camera_x
        top = self.model.camera_y
        right = left + (self.screen.get_width() - PANEL_WIDTH - (RIGHT_PANEL_WIDTH if self.model.right_panel_visible else 0)) / self.model.zoom
        bottom = top + self.screen.get_height() / self.model.zoom
        start_x = int(left // step) * step
        start_y = int(top // step) * step
        for x in range(int(start_x), int(right + step), int(step)):
            sx, sy = self.model.world_to_screen(x, 0, self.model.camera_x, self.model.camera_y, self.model.zoom)
            pygame.draw.line(self.screen, COLOR_GRID, (sx, 0), (sx, self.screen.get_height()), 1)
        for y in range(int(start_y), int(bottom + step), int(step)):
            sx, sy = self.model.world_to_screen(0, y, self.model.camera_x, self.model.camera_y, self.model.zoom)
            pygame.draw.line(self.screen, COLOR_GRID, (0, sy), (self.screen.get_width(), sy), 1)
        w, h = self.model.map_data["width"], self.model.map_data["height"]
        x1, y1 = self.model.world_to_screen(0, 0, self.model.camera_x, self.model.camera_y, self.model.zoom)
        x2, y2 = self.model.world_to_screen(w, h, self.model.camera_x, self.model.camera_y, self.model.zoom)
        pygame.draw.rect(self.screen, COLOR_WHITE, (x1, y1, x2-x1, y2-y1), 2)

    def draw_objects(self):
        render_order = []
        for i, obj in enumerate(self.model.map_data["objects"]):
            if obj.get("is_group"):
                render_order.append(i)
                children = obj.get("children", [])
                for child_idx in children:
                    if child_idx < len(self.model.map_data["objects"]):
                        render_order.append(child_idx)
            else:
                if obj.get("group_id") is None:
                    render_order.append(i)
        for idx in reversed(render_order):
            if idx < len(self.model.map_data["objects"]):
                self.draw_object(self.model.map_data["objects"][idx], idx)

    def draw_object(self, obj, idx):
        try:
            if obj.get("dummy"):
                if obj.get("group_id") is not None and not obj.get("is_group"):
                    abs_x, abs_y, _ = self.model.get_abs_transform(idx)
                else:
                    abs_x, abs_y = obj.get("x", 0), obj.get("y", 0)
                sx, sy = self.model.world_to_screen(abs_x, abs_y, self.model.camera_x, self.model.camera_y, self.model.zoom)
                size = 12 * self.model.zoom
                points = [(sx, sy-size), (sx+size, sy), (sx, sy+size), (sx-size, sy)]
                pygame.draw.polygon(self.screen, COLOR_DUMMY, points, 2)
                glow = pygame.Surface((int(size*2.5), int(size*2.5)), pygame.SRCALPHA)
                pygame.draw.polygon(glow, (0, 255, 0, 50), [(glow.get_width()/2, 0), (glow.get_width(), glow.get_height()/2), (glow.get_width()/2, glow.get_height()), (0, glow.get_height()/2)])
                self.screen.blit(glow, (sx - glow.get_width()/2, sy - glow.get_height()/2))
                if idx in self.model.selected_indices:
                    pygame.draw.circle(self.screen, COLOR_SELECT, (sx, sy), 8, 2)
                if idx == self.model.hover_index:
                    pygame.draw.circle(self.screen, COLOR_HOVER, (sx, sy), 6, 1)
                return

            if obj.get("group_id") is not None and not obj.get("is_group"):
                abs_x, abs_y, abs_angle = self.model.get_abs_transform(idx)
                orig_x, orig_y, orig_angle = obj.get("x", 0), obj.get("y", 0), obj.get("angle", 0)
                obj["x"], obj["y"], obj["angle"] = abs_x, abs_y, abs_angle
                self._draw_object_raw(obj, idx)
                obj["x"], obj["y"], obj["angle"] = orig_x, orig_y, orig_angle
            else:
                self._draw_object_raw(obj, idx)
        except Exception as e:
            print(f"Ошибка при отрисовке объекта {idx}: {e}")

    def _draw_object_raw(self, obj, idx):
        x = obj["x"]
        y = obj["y"]
        sx, sy = self.model.world_to_screen(x, y, self.model.camera_x, self.model.camera_y, self.model.zoom)
        color = obj.get("color", (255, 0, 0))
        if isinstance(color, str):
            color = pygame.Color(color)
        if not isinstance(color, tuple):
            color = tuple(color)

        selected = (idx in self.model.selected_indices)
        hover = (idx == self.model.hover_index)
        obj_type = obj.get("type", "circle")
        angle = obj.get("angle", 0)

        is_nocollide = obj_type in ("nocollide_rect", "nocollide_circle")

        if obj_type == "circle":
            radius = obj.get("radius", 30) * self.model.zoom
            if radius > 1:
                pygame.draw.circle(self.screen, color, (sx, sy), int(radius))
                if selected and (self.model.hover_resize or self.model.resizing):
                    pygame.draw.circle(self.screen, COLOR_RESIZE, (sx, sy), int(radius), 2)
                if is_nocollide and not obj.get("image"):
                    pygame.draw.circle(self.screen, COLOR_SELECT, (sx, sy), int(radius)+2, 2)
        elif obj_type == "rect":
            w = obj.get("width", 60) * self.model.zoom
            h = obj.get("height", 40) * self.model.zoom
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
                corners = self.model.get_rect_corners(obj)
                top_center = ((corners[0][0]+corners[1][0])/2, (corners[0][1]+corners[1][1])/2)
                bottom_center = ((corners[3][0]+corners[2][0])/2, (corners[3][1]+corners[2][1])/2)
                left_center = ((corners[0][0]+corners[3][0])/2, (corners[0][1]+corners[3][1])/2)
                right_center = ((corners[1][0]+corners[2][0])/2, (corners[1][1]+corners[2][1])/2)
                for (cx, cy) in [top_center, bottom_center, left_center, right_center]:
                    scx, scy = self.model.world_to_screen(cx, cy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    pygame.draw.circle(self.screen, COLOR_MARKER, (int(scx), int(scy)), 5, 1)
                for (cx, cy) in [top_center, bottom_center]:
                    scx, scy = self.model.world_to_screen(cx, cy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    label = self.font_small.render("a", True, COLOR_LABEL)
                    self.screen.blit(label, (scx - 5, scy - 10))
                for (cx, cy) in [left_center, right_center]:
                    scx, scy = self.model.world_to_screen(cx, cy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    label = self.font_small.render("b", True, COLOR_LABEL)
                    self.screen.blit(label, (scx - 5, scy - 10))
        elif obj_type == "triangle":
            if not obj.get("valid", True):
                return
            vertices = self.model.get_triangle_vertices(obj)
            if not vertices:
                return
            sv = [self.model.world_to_screen(vx, vy, self.model.camera_x, self.model.camera_y, self.model.zoom) for vx, vy in vertices]
            pygame.draw.polygon(self.screen, color, sv)
            if selected and self.model.resizing and self.model.resize_type == "triangle_vertex" and self.model.resize_index == idx:
                temp_vx = self.model.resize_data.get("current_vx", vertices[0][0])
                temp_vy = self.model.resize_data.get("current_vy", vertices[0][1])
                other_vertices = [v for i, v in enumerate(vertices) if i != self.model.resize_data["vertex_idx"]]
                temp_points = []
                for p in [other_vertices[0], other_vertices[1], (temp_vx, temp_vy)]:
                    sp = self.model.world_to_screen(p[0], p[1], self.model.camera_x, self.model.camera_y, self.model.zoom)
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
                    scx, scy = self.model.world_to_screen(cx, cy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    pygame.draw.circle(self.screen, COLOR_MARKER, (int(scx), int(scy)), 5, 1)
                    lab = self.font_small.render(label, True, COLOR_LABEL)
                    self.screen.blit(lab, (scx - 5, scy - 10))
                angle_labels = [("α", A), ("β", B), ("γ", C)]
                for (label, (vx, vy)) in angle_labels:
                    scx, scy = self.model.world_to_screen(vx, vy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    offset_x, offset_y = 20, -20
                    lab = self.font_small.render(label, True, COLOR_LABEL)
                    self.screen.blit(lab, (scx + offset_x, scy + offset_y))
        elif obj_type == "nocollide_rect":
            w = obj.get("width", 60) * self.model.zoom
            h = obj.get("height", 40) * self.model.zoom
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
                corners = self.model.get_rect_corners(obj)
                top_center = ((corners[0][0]+corners[1][0])/2, (corners[0][1]+corners[1][1])/2)
                bottom_center = ((corners[3][0]+corners[2][0])/2, (corners[3][1]+corners[2][1])/2)
                left_center = ((corners[0][0]+corners[3][0])/2, (corners[0][1]+corners[3][1])/2)
                right_center = ((corners[1][0]+corners[2][0])/2, (corners[1][1]+corners[2][1])/2)
                for (cx, cy) in [top_center, bottom_center, left_center, right_center]:
                    scx, scy = self.model.world_to_screen(cx, cy, self.model.camera_x, self.model.camera_y, self.model.zoom)
                    pygame.draw.circle(self.screen, COLOR_MARKER, (int(scx), int(scy)), 5, 1)
        elif obj_type == "nocollide_circle":
            radius = obj.get("radius", 30) * self.model.zoom
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

    def draw_selection_rect(self):
        if self.model.dragging_selection and self.model.selection_rect_start and self.model.selection_rect_end:
            x1, y1 = self.model.selection_rect_start
            x2, y2 = self.model.selection_rect_end
            sx1, sy1 = self.model.world_to_screen(x1, y1, self.model.camera_x, self.model.camera_y, self.model.zoom)
            sx2, sy2 = self.model.world_to_screen(x2, y2, self.model.camera_x, self.model.camera_y, self.model.zoom)
            rect = pygame.Rect(min(sx1, sx2), min(sy1, sy2), abs(sx2-sx1), abs(sy2-sy1))
            pygame.draw.rect(self.screen, COLOR_YELLOW, rect, 1)

    def draw_cursor(self):
        mx, my = pygame.mouse.get_pos()
        if mx < PANEL_WIDTH:
            return
        if mx > self.screen.get_width() - RIGHT_PANEL_WIDTH and self.model.right_panel_visible:
            return
        size = 12
        gap = 4
        pygame.draw.line(self.screen, COLOR_CURSOR, (mx - size, my), (mx - gap, my), 1)
        pygame.draw.line(self.screen, COLOR_CURSOR, (mx + gap, my), (mx + size, my), 1)
        pygame.draw.line(self.screen, COLOR_CURSOR, (mx, my - size), (mx, my - gap), 1)
        pygame.draw.line(self.screen, COLOR_CURSOR, (mx, my + gap), (mx, my + size), 1)
        pygame.draw.circle(self.screen, COLOR_CURSOR, (mx, my), 2)

    def draw_right_panel(self):
        if not self.model.right_panel_visible:
            trigger_rect = pygame.Rect(self.screen.get_width() - RIGHT_PANEL_TRIGGER_WIDTH, 0, RIGHT_PANEL_TRIGGER_WIDTH, self.screen.get_height())
            pygame.draw.rect(self.screen, COLOR_RIGHT_PANEL_TRIGGER, trigger_rect)
            return
        panel = pygame.Rect(self.screen.get_width() - RIGHT_PANEL_WIDTH, 0, RIGHT_PANEL_WIDTH, self.screen.get_height())
        pygame.draw.rect(self.screen, COLOR_RIGHT_PANEL_BG, panel)
        pygame.draw.line(self.screen, COLOR_RIGHT_PANEL_BORDER, (panel.x, 0), (panel.x, self.screen.get_height()), 2)
        title = self.font.render("Объекты", True, COLOR_WHITE)
        self.screen.blit(title, (panel.x + 10, 10))
        objects = self.model.map_data["objects"]
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
                        if child_idx < len(objects):
                            display_items.append((child_idx, 1, False, False))
            else:
                if obj.get("group_id") is None:
                    display_items.append((i, 0, False, False))
        item_height = 28
        padding = 5
        list_start_y = 40
        list_height = self.screen.get_height() - list_start_y - 10
        max_visible = list_height // (item_height + padding)
        total_items = len(display_items)
        max_scroll = max(0, total_items - max_visible)
        scroll = max(0, min(max_scroll, self.model.right_panel_scroll))
        start_idx = scroll
        end_idx = min(total_items, start_idx + max_visible + 1)
        y = list_start_y
        for item_idx in range(start_idx, end_idx):
            if item_idx >= len(display_items):
                break
            idx, indent, is_group, is_collapsed = display_items[item_idx]
            if idx >= len(objects):
                continue
            obj = objects[idx]
            display_name = self.model.get_display_name(obj)
            prefix = "  " * indent
            full_name = f"{prefix}{display_name}"
            is_selected = (idx in self.model.selected_indices)
            is_hover = (idx == self.model.right_panel_drag_index)
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
            if self.model.right_panel_rename_index == idx:
                input_rect = pygame.Rect(text_x, rect.y + 2, rect.width - (text_x - rect.x) - 10, item_height - 4)
                pygame.draw.rect(self.screen, COLOR_WHITE, input_rect, 1)
                rename_surf = self.font_small.render(self.model.right_panel_rename_text, True, COLOR_WHITE)
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
        panel = pygame.Rect(0, 0, PANEL_WIDTH, self.screen.get_height())
        pygame.draw.rect(self.screen, COLOR_PANEL, panel)
        pygame.draw.line(self.screen, COLOR_GRAY, (panel.right, 0), (panel.right, self.screen.get_height()), 2)

        # Очищаем списки перед заполнением
        self.icon_rects = []
        self.color_rects = []
        self.slider_rects = []
        self.button_rects = []
        self.param_rects = []
        self.collapse_buttons = []
        self.create_child_button_rect = None

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
        for label, typ, key in icon_types:
            rect = pygame.Rect(x_icon, y, ICON_SIZE, ICON_SIZE)
            self.icon_rects.append((rect, typ))
            if self.model.new_object_type == typ:
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
        if self.model.selected_indices:
            main_idx = self.model.selected_indices[0]
            if main_idx < len(self.model.map_data["objects"]):
                main_obj = self.model.map_data["objects"][main_idx]
                menu_items.append((main_obj, main_idx, True))
                if main_obj.get("is_group"):
                    children = main_obj.get("children", [])
                    for child_idx in children:
                        if child_idx < len(self.model.map_data["objects"]):
                            child_obj = self.model.map_data["objects"][child_idx]
                            menu_items.append((child_obj, child_idx, False))

        item_height = 28
        spacing = 5
        total_height = 0
        for obj, idx, sel in menu_items:
            total_height += self.get_menu_height(obj)
        max_scroll = max(0, total_height - (self.screen.get_height() - y - 50))
        scroll = max(0, min(max_scroll, self.model.panel_scroll))

        current_y = y - scroll
        for obj, idx, is_selected in menu_items:
            header_rect = pygame.Rect(10, current_y, panel.width-20, 24)
            pygame.draw.rect(self.screen, COLOR_GRAY if not is_selected else COLOR_SELECT, header_rect)
            name = self.model.get_display_name(obj)
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

        self.model.panel_scroll = scroll

        # Кнопка создания дочернего
        bottom_y = self.screen.get_height() - 190
        if self.model.selected_indices:
            first_idx = self.model.selected_indices[0]
            if first_idx < len(self.model.map_data["objects"]):
                first_obj = self.model.map_data["objects"][first_idx]
                if (first_obj.get("group_id") is None and not first_obj.get("is_group")) or first_obj.get("is_group"):
                    btn_y = bottom_y - 40
                    btn_rect = pygame.Rect(10, btn_y, panel.width-20, 28)
                    self.create_child_button_rect = btn_rect
                    pygame.draw.rect(self.screen, COLOR_GRAY, btn_rect)
                    if first_obj.get("is_group"):
                        label = "Создать дочерний объект"
                    else:
                        label = "Создать объект подгруппы"
                    self.draw_text(label, 15, btn_y+5, COLOR_WHITE)

        # Нижние кнопки
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

    def draw_text(self, text, x, y, color):
        surf = self.font_small.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def draw_object_properties(self, obj, idx, y, panel):
        x = 10
        # Локальные координаты
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
            # Цвета
            self.draw_text("Цвет:", x, y, COLOR_WHITE)
            y += 22
            bx = x
            self.color_rects = []
            base_colors = [
                (255, 0, 0), (0, 255, 0), (0, 0, 255),
                (255, 255, 0), (255, 0, 255), (0, 255, 255),
                (255, 255, 255), (128, 128, 128), (0, 0, 0)
            ]
            for col in base_colors:
                rect = pygame.Rect(bx, y, COLOR_BOX_SIZE, COLOR_BOX_SIZE)
                self.color_rects.append((rect, col))
                pygame.draw.rect(self.screen, col, rect)
                pygame.draw.rect(self.screen, COLOR_WHITE, rect, 1)
                bx += COLOR_BOX_SIZE + 4
            y += COLOR_BOX_SIZE + 8

            # RGB слайдеры
            self.draw_text("RGB:", x, y, COLOR_WHITE)
            y += 20
            self.slider_rects = []
            for i, label in enumerate(["R", "G", "B"]):
                val = self.model.rgb_sliders[i]
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
                param_key = "r" if i==0 else "g" if i==1 else "b"
                self.draw_parameter("", val, x+130, y, param_key, idx)
                y += 20
            y += 5

            # Параметры объекта
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
                if self.model.fine_tune:
                    pts = [(x+135, y+6), (x+140, y+14), (x+150, y+4)]
                    pygame.draw.lines(self.screen, COLOR_GREEN, False, pts, 2)
                y += 30
        self.draw_text("Поворот: Num4 (-5°)  Num6 (+5°)", x, y, COLOR_GRAY)
        y += 30

    def draw_parameter(self, label, value, x, y, param_key, obj_idx):
        text = f"{label}: {value}" if label else f"{value}"
        if (self.model.input_active and self.model.input_param == param_key and
            self.model.input_obj_index == obj_idx):
            rect = pygame.Rect(x, y-2, 50 if not label else 160, 22)
            self.input_rect = rect
            pygame.draw.rect(self.screen, COLOR_WHITE, rect, 1)
            input_surf = self.font_small.render(self.model.input_text, True, COLOR_WHITE)
            self.screen.blit(input_surf, (x+4, y))
        else:
            rect = pygame.Rect(x, y-2, 50 if not label else 160, 22)
            self.param_rects.append((rect, param_key, obj_idx))
            self.draw_text(text, x, y, COLOR_WHITE)

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

    def draw_dialogs(self):
        if self.model.show_help:
            self.draw_help()
        if self.model.resize_input_active:
            self.draw_resize_dialog()
        if self.model.save_as_active:
            self.draw_save_as_dialog()
        if self.model.create_child_dialog:
            self.draw_create_child_dialog()

    def draw_help(self):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
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
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        dialog_rect = pygame.Rect(self.screen.get_width()//2 - 150, self.screen.get_height()//2 - 60, 300, 120)
        pygame.draw.rect(self.screen, COLOR_PANEL, dialog_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, dialog_rect, 2)
        w_label = self.font.render("Ширина:", True, COLOR_WHITE)
        self.screen.blit(w_label, (dialog_rect.x+20, dialog_rect.y+20))
        h_label = self.font.render("Высота:", True, COLOR_WHITE)
        self.screen.blit(h_label, (dialog_rect.x+20, dialog_rect.y+55))
        w_rect = pygame.Rect(dialog_rect.x+120, dialog_rect.y+20, 100, 25)
        pygame.draw.rect(self.screen, COLOR_BLACK, w_rect)
        w_surf = self.font.render(self.model.resize_width_text, True, COLOR_WHITE)
        self.screen.blit(w_surf, (w_rect.x+5, w_rect.y+2))
        h_rect = pygame.Rect(dialog_rect.x+120, dialog_rect.y+55, 100, 25)
        pygame.draw.rect(self.screen, COLOR_BLACK, h_rect)
        h_surf = self.font.render(self.model.resize_height_text, True, COLOR_WHITE)
        self.screen.blit(h_surf, (h_rect.x+5, h_rect.y+2))
        ok_rect = pygame.Rect(dialog_rect.x+40, dialog_rect.y+90, 80, 30)
        pygame.draw.rect(self.screen, COLOR_GREEN, ok_rect)
        self.screen.blit(self.font.render("OK", True, COLOR_WHITE), (ok_rect.x+25, ok_rect.y+5))
        cancel_rect = pygame.Rect(dialog_rect.x+180, dialog_rect.y+90, 80, 30)
        pygame.draw.rect(self.screen, COLOR_RED, cancel_rect)
        self.screen.blit(self.font.render("Cancel", True, COLOR_WHITE), (cancel_rect.x+10, cancel_rect.y+5))

    def draw_save_as_dialog(self):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        dialog_rect = pygame.Rect(self.screen.get_width()//2 - 150, self.screen.get_height()//2 - 50, 300, 100)
        pygame.draw.rect(self.screen, COLOR_PANEL, dialog_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, dialog_rect, 2)
        label = self.font.render("Имя карты:", True, COLOR_WHITE)
        self.screen.blit(label, (dialog_rect.x+20, dialog_rect.y+20))
        input_rect = pygame.Rect(dialog_rect.x+20, dialog_rect.y+50, 260, 30)
        pygame.draw.rect(self.screen, COLOR_BLACK, input_rect)
        text_surf = self.font.render(self.model.save_as_text, True, COLOR_WHITE)
        self.screen.blit(text_surf, (input_rect.x+5, input_rect.y+5))
        ok_rect = pygame.Rect(dialog_rect.x+40, dialog_rect.y+90, 80, 30)
        pygame.draw.rect(self.screen, COLOR_GREEN, ok_rect)
        self.screen.blit(self.font.render("OK", True, COLOR_WHITE), (ok_rect.x+25, ok_rect.y+5))
        cancel_rect = pygame.Rect(dialog_rect.x+180, dialog_rect.y+90, 80, 30)
        pygame.draw.rect(self.screen, COLOR_RED, cancel_rect)
        self.screen.blit(self.font.render("Cancel", True, COLOR_WHITE), (cancel_rect.x+10, cancel_rect.y+5))

    def draw_create_child_dialog(self):
        if not self.model.create_child_dialog:
            return
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        rect = pygame.Rect(self.screen.get_width()//2 - 100, self.screen.get_height()//2 - 100, 200, 200)
        pygame.draw.rect(self.screen, COLOR_PANEL, rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, rect, 2)
        title = self.font.render("Выберите тип", True, COLOR_WHITE)
        self.screen.blit(title, (rect.x + 40, rect.y + 10))
        y = rect.y + 40
        types = ["circle", "rect", "triangle", "nocollide_rect", "nocollide_circle", "dummy"]
        labels = ["Круг", "Прям.", "Треуг.", "Прям. без", "Круг без", "Заглушка"]
        self.model.create_child_buttons = []
        for i, typ in enumerate(types):
            btn = pygame.Rect(rect.x + 20, y, 160, 30)
            self.model.create_child_buttons.append((btn, typ))
            pygame.draw.rect(self.screen, COLOR_GRAY, btn)
            text_surf = self.font_small.render(labels[i], True, COLOR_WHITE)
            self.screen.blit(text_surf, (btn.x + 10, btn.y + 6))
            y += 35

    def draw_placement_ghost(self):
        if not self.model.placement_mode or self.model.placement_ghost_obj is None:
            return
        mx, my = pygame.mouse.get_pos()
        wx, wy = self.model.screen_to_world(mx, my, self.model.camera_x, self.model.camera_y, self.model.zoom)
        ghost = self.model.placement_ghost_obj
        ghost["x"] = wx
        ghost["y"] = wy
        s = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        old_screen = self.screen
        self.screen = s
        self._draw_object_raw(ghost, -1)
        self.screen = old_screen
        s.set_alpha(128)
        self.screen.blit(s, (0, 0))
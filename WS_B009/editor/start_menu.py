# editor/start_menu.py
# Стартовое меню редактора карт

import pygame
import os
from .constants import *

class StartMenu:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        self.font_title = pygame.font.Font(None, 48)
        self.clock = pygame.time.Clock()
        self.running = True
        self.choice = None  # 'new', 'user', 'builtin'
        self.selected_file = None  # полный путь к файлу
        self.file_list = []  # список файлов для выбора
        self.scroll = 0
        self.menu_state = 'main'  # 'main', 'file_list'
        self.file_list_type = ''  # 'user' или 'builtin'

    def run(self):
        while self.running:
            self.clock.tick(60)
            self.handle_events()
            self.draw()
            pygame.display.flip()
        return self.choice, self.selected_file

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.choice = 'quit'
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    self.choice = 'quit'
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if self.menu_state == 'main':
                    self.handle_main_click(mx, my)
                elif self.menu_state == 'file_list':
                    self.handle_file_list_click(mx, my)
            elif event.type == pygame.MOUSEWHEEL:
                if self.menu_state == 'file_list':
                    self.scroll -= event.y * 20
                    max_scroll = max(0, len(self.file_list) * 35 - self.screen.get_height() + 150)
                    self.scroll = max(0, min(max_scroll, self.scroll))

    def handle_main_click(self, mx, my):
        buttons = [
            (self.screen.get_width()//2 - 100, 180, 200, 50, 'Создать новую карту', 'new'),
            (self.screen.get_width()//2 - 100, 250, 200, 50, 'Выбрать пользовательскую карту', 'user'),
            (self.screen.get_width()//2 - 100, 320, 200, 50, 'Выбрать встроенную карту', 'builtin')
        ]
        for x, y, w, h, label, action in buttons:
            if x <= mx <= x+w and y <= my <= y+h:
                if action == 'new':
                    self.choice = 'new'
                    self.running = False
                else:
                    self.menu_state = 'file_list'
                    self.file_list_type = action
                    if action == 'user':
                        self.file_list = self.get_all_maps()
                    else:  # builtin
                        self.file_list = self.get_builtin_maps()
                    self.scroll = 0

    def handle_file_list_click(self, mx, my):
        list_start_y = 150
        item_height = 30
        # Проверяем клик по файлам
        for i, fname in enumerate(self.file_list):
            y = list_start_y + i * item_height - self.scroll
            if 0 <= y < self.screen.get_height() - 100:
                rect = pygame.Rect(self.screen.get_width()//2 - 200, y, 400, item_height)
                if rect.collidepoint(mx, my):
                    self.selected_file = fname
                    self.choice = self.file_list_type
                    self.running = False
                    return
        # Кнопка "Назад"
        back_rect = pygame.Rect(self.screen.get_width()//2 - 50, self.screen.get_height() - 60, 100, 40)
        if back_rect.collidepoint(mx, my):
            self.menu_state = 'main'
            self.file_list = []
            self.scroll = 0

    def get_all_maps(self):
        """Возвращает список всех .yaml карт из data/maps и data/maps/usermaps (полные пути)"""
        maps = []
        for root in ['data/maps', 'data/maps/usermaps']:
            if os.path.exists(root):
                for f in os.listdir(root):
                    if f.endswith('.yaml') and f != 'temp_map.yaml':
                        full_path = os.path.join(root, f)
                        maps.append(full_path)
        return sorted(maps)

    def get_builtin_maps(self):
        """Возвращает список встроенных карт (только из data/maps, исключая usermaps)"""
        maps = []
        root = 'data/maps'
        if os.path.exists(root):
            for f in os.listdir(root):
                if f.endswith('.yaml') and f != 'temp_map.yaml':
                    full_path = os.path.join(root, f)
                    # Проверяем, что файл не дублируется в usermaps (но это не обязательно)
                    maps.append(full_path)
        return sorted(maps)

    def draw(self):
        self.screen.fill(COLOR_BG)

        if self.menu_state == 'main':
            self.draw_main_menu()
        else:
            self.draw_file_list()

    def draw_main_menu(self):
        # Заголовок
        title = self.font_title.render("Редактор карт WarStalker", True, COLOR_WHITE)
        title_rect = title.get_rect(center=(self.screen.get_width()//2, 80))
        self.screen.blit(title, title_rect)

        # Кнопки
        buttons = [
            (self.screen.get_width()//2 - 100, 180, 200, 50, 'Создать новую карту', 'new'),
            (self.screen.get_width()//2 - 100, 250, 200, 50, 'Выбрать пользовательскую карту', 'user'),
            (self.screen.get_width()//2 - 100, 320, 200, 50, 'Выбрать встроенную карту', 'builtin')
        ]
        for x, y, w, h, label, action in buttons:
            rect = pygame.Rect(x, y, w, h)
            pygame.draw.rect(self.screen, COLOR_GRAY, rect)
            pygame.draw.rect(self.screen, COLOR_WHITE, rect, 2)
            text = self.font.render(label, True, COLOR_WHITE)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

        # Подсказка
        hint = self.font_small.render("Нажмите Escape для выхода", True, COLOR_GRAY)
        hint_rect = hint.get_rect(center=(self.screen.get_width()//2, self.screen.get_height() - 30))
        self.screen.blit(hint, hint_rect)

    def draw_file_list(self):
        # Заголовок
        if self.file_list_type == 'user':
            title_text = "Пользовательские карты"
        else:
            title_text = "Встроенные карты"
        title = self.font.render(title_text, True, COLOR_WHITE)
        title_rect = title.get_rect(center=(self.screen.get_width()//2, 80))
        self.screen.blit(title, title_rect)

        # Список файлов
        list_start_y = 150
        item_height = 30
        for i, fname in enumerate(self.file_list):
            y = list_start_y + i * item_height - self.scroll
            if 0 <= y < self.screen.get_height() - 100:
                # Отображаем только имя файла без пути
                display_name = os.path.basename(fname)
                rect = pygame.Rect(self.screen.get_width()//2 - 200, y, 400, item_height)
                # Светлый фон при наведении
                mx, my = pygame.mouse.get_pos()
                if rect.collidepoint(mx, my):
                    pygame.draw.rect(self.screen, COLOR_GRAY, rect)
                else:
                    pygame.draw.rect(self.screen, COLOR_BLACK, rect)
                pygame.draw.rect(self.screen, COLOR_WHITE, rect, 1)
                text = self.font_small.render(display_name, True, COLOR_WHITE)
                text_rect = text.get_rect(center=rect.center)
                self.screen.blit(text, text_rect)

        # Кнопка "Назад"
        back_rect = pygame.Rect(self.screen.get_width()//2 - 50, self.screen.get_height() - 60, 100, 40)
        pygame.draw.rect(self.screen, COLOR_GRAY, back_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, back_rect, 2)
        back_text = self.font.render("Назад", True, COLOR_WHITE)
        back_text_rect = back_text.get_rect(center=back_rect.center)
        self.screen.blit(back_text, back_text_rect)

        # Подсказка по скроллу
        if len(self.file_list) > (self.screen.get_height() - 150) // 30:
            hint = self.font_small.render("Используйте колёсико мыши для прокрутки", True, COLOR_GRAY)
            hint_rect = hint.get_rect(center=(self.screen.get_width()//2, self.screen.get_height() - 20))
            self.screen.blit(hint, hint_rect)
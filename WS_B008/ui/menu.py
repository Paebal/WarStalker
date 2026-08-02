# ui/menu.py
import pygame
import os
import subprocess
import sys
from constants import COLOR_WHITE, COLOR_YELLOW, COLOR_BLACK
from game.config_loader import ConfigLoader

class Menu:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.font = pygame.font.Font(None, 36)
        self.options = []
        self.selected = 0
        self.running = True

    def draw(self):
        self.screen.fill(COLOR_BLACK)
        width = self.screen.get_width()
        title = self.font.render("War Stalker 1.0", True, COLOR_WHITE)
        self.screen.blit(title, (width//2 - title.get_width()//2, 100))
        ver_font = pygame.font.Font(None, 24)
        version = ver_font.render("v1.00.000", True, (128,128,128))
        self.screen.blit(version, (width//2 - version.get_width()//2, 150))
        y = 250
        for i, option in enumerate(self.options):
            color = COLOR_YELLOW if i == self.selected else COLOR_WHITE
            text = self.font.render(option, True, color)
            text_rect = text.get_rect(center=(width//2, y))
            self.screen.blit(text, text_rect)
            y += 60

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game.quit()
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected = (self.selected - 1) % len(self.options)
                elif event.key == pygame.K_DOWN:
                    self.selected = (self.selected + 1) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    self.activate_option(self.selected)
            elif event.type == pygame.MOUSEMOTION:
                mouse_x, mouse_y = event.pos
                y = 250
                for i in range(len(self.options)):
                    text = self.font.render(self.options[i], True, COLOR_WHITE)
                    text_rect = text.get_rect(center=(self.screen.get_width()//2, y))
                    if text_rect.collidepoint(mouse_x, mouse_y):
                        self.selected = i
                    y += 60
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_x, mouse_y = event.pos
                    y = 250
                    for i in range(len(self.options)):
                        text = self.font.render(self.options[i], True, COLOR_WHITE)
                        text_rect = text.get_rect(center=(self.screen.get_width()//2, y))
                        if text_rect.collidepoint(mouse_x, mouse_y):
                            self.activate_option(i)
                            break
                        y += 60

    def activate_option(self, index):
        pass

    def run(self):
        self.running = True
        while self.running:
            self.handle_events()
            self.draw()
            pygame.display.flip()
            if not self.game.running:
                self.running = False


class MainMenu(Menu):
    def __init__(self, game):
        super().__init__(game)
        self.options = ["Новая игра", "Выбрать карту", "Настройки", "Выход"]
        if os.path.exists("map_editor.py"):
            self.options.insert(2, "Редактор карт")

    def activate_option(self, index):
        if self.options[index] == "Новая игра":
            self.game.new_game()
            self.running = False
        elif self.options[index] == "Выбрать карту":
            map_menu = MapSelectMenu(self.game)
            map_menu.run()
        elif self.options[index] == "Редактор карт":
            # Исправленный запуск с обработкой ошибок и абсолютным путём
            try:
                editor_path = os.path.abspath("map_editor.py")
                if not os.path.exists(editor_path):
                    self.game.chat.add_message("Система", "Файл map_editor.py не найден", temporary=True)
                    return
                # Запускаем в отдельном процессе, но перехватываем ошибки
                subprocess.Popen([sys.executable, editor_path], cwd=os.path.dirname(editor_path))
                self.game.chat.add_message("Система", "Редактор карт запущен", temporary=True)
            except Exception as e:
                self.game.chat.add_message("Система", f"Ошибка запуска редактора: {e}", temporary=True)
        elif self.options[index] == "Настройки":
            settings_menu = SettingsMenu(self.game)
            settings_menu.run()
        elif self.options[index] == "Выход":
            self.game.quit()
            self.running = False


class MapSelectMenu(Menu):
    def __init__(self, game):
        super().__init__(game)
        self.loader = ConfigLoader()
        self.maps = self.loader.list_maps()
        self.options = [f"{name} ({typ})" for typ, name in self.maps]
        self.options.append("Назад")

    def activate_option(self, index):
        if index == len(self.options) - 1:
            self.running = False
        else:
            typ, name = self.maps[index]
            self.game.load_map(name)
            self.running = False


class SettingsMenu(Menu):
    def __init__(self, game):
        super().__init__(game)
        self.resolution_display = f"{game.screen_width}x{game.screen_height}"
        self.options = [
            "Изменить клавиши",
            f"Разрешение: {self.resolution_display} [→]",
            f"FPS: {'Вкл' if game.settings.get_show_fps() else 'Выкл'}",
            "Полноэкранный: " + ("ON" if game.settings.data["fullscreen"] else "OFF"),
            "Без рамки: " + ("ON" if game.settings.data["borderless"] else "OFF"),
            "Назад"
        ]
        if game.dev_mode:
            self.options.insert(2, f"Масштаб карты: {game.settings.get_map_scale():.1f} [→]")

    def activate_option(self, index):
        if self.options[index].startswith("Изменить клавиши"):
            self.game.chat.add_message("Система", "Изменение клавиш пока не реализовано", temporary=True)
        elif self.options[index].startswith("Разрешение"):
            res_menu = ResolutionMenu(self.game)
            res_menu.run()
            self.resolution_display = f"{self.game.screen_width}x{self.game.screen_height}"
            self.options[1] = f"Разрешение: {self.resolution_display} [→]"
        elif self.options[index].startswith("Масштаб карты"):
            if self.game.dev_mode:
                scales = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
                current = self.game.settings.get_map_scale()
                try:
                    idx = scales.index(current)
                    new_scale = scales[(idx + 1) % len(scales)]
                except ValueError:
                    new_scale = scales[0]
                self.game.set_map_scale(new_scale)
                self.options[2] = f"Масштаб карты: {self.game.settings.get_map_scale():.1f} [→]"
        elif self.options[index].startswith("FPS"):
            self.game.settings.toggle_fps()
            idx = 3 if self.game.dev_mode else 2
            self.options[idx] = f"FPS: {'Вкл' if self.game.settings.get_show_fps() else 'Выкл'}"
        elif self.options[index].startswith("Полноэкранный"):
            self.game.toggle_fullscreen()
            idx = 4 if self.game.dev_mode else 3
            self.options[idx] = "Полноэкранный: " + ("ON" if self.game.settings.data["fullscreen"] else "OFF")
        elif self.options[index].startswith("Без рамки"):
            self.game.toggle_borderless()
            idx = 5 if self.game.dev_mode else 4
            self.options[idx] = "Без рамки: " + ("ON" if self.game.settings.data["borderless"] else "OFF")
        elif self.options[index] == "Назад":
            self.running = False


class ResolutionMenu(Menu):
    def __init__(self, game):
        super().__init__(game)
        self.resolutions = [
            ("1280x720", 1280, 720),
            ("1600x900", 1600, 900),
            ("1920x1080", 1920, 1080),
            ("1920x1200", 1920, 1200)
        ]
        current_res = f"{game.screen_width}x{game.screen_height}"
        self.selected = 0
        for i, (res_name, w, h) in enumerate(self.resolutions):
            if res_name == current_res:
                self.selected = i
                break
        self.options = [f"{res[0]}" for res in self.resolutions]
        self.options.append("Назад")

    def activate_option(self, index):
        if index == len(self.options) - 1:
            self.running = False
        else:
            res_name, w, h = self.resolutions[index]
            self.game.set_resolution(w, h)
            self.running = False
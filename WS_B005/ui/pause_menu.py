# ui/pause_menu.py
import pygame
from constants import COLOR_WHITE, COLOR_YELLOW, COLOR_BLACK
from ui.menu import SettingsMenu

class PauseMenu:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.font = pygame.font.Font(None, 36)
        self.options = ["Продолжить", "Сохранить игру", "Настройки", "Выйти в главное меню"]
        self.selected = 0
        self.running = True
        self.back_to_menu = False
        self.continue_game = True

    def draw(self):
        width = self.screen.get_width()
        height = self.screen.get_height()
        overlay = pygame.Surface((width, height))
        overlay.set_alpha(180)
        overlay.fill(COLOR_BLACK)
        self.screen.blit(overlay, (0,0))
        title = self.font.render("ПАУЗА", True, (255,255,255))
        self.screen.blit(title, (width//2 - title.get_width()//2, 150))
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
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    self.continue_game = True
                elif event.key == pygame.K_UP:
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
        if index == 0:
            self.running = False
            self.continue_game = True
        elif index == 1:
            self.game.save_game("save_manual.json")
            self.game.chat.add_message("Система", "Игра сохранена", temporary=True)
            self.running = False
            self.continue_game = True
        elif index == 2:
            settings_menu = SettingsMenu(self.game)
            settings_menu.run()
        elif index == 3:
            self.game.save_game("auto_save.json")
            self.back_to_menu = True
            self.continue_game = False
            self.running = False

    def run(self):
        self.running = True
        self.back_to_menu = False
        self.continue_game = True
        while self.running:
            self.handle_events()
            self.draw()
            pygame.display.flip()
            if not self.game.running:
                self.running = False
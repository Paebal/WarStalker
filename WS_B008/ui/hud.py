# ui/hud.py
import pygame
from constants import COLOR_WHITE, COLOR_YELLOW, COLOR_GRAY, COLOR_GREEN

class HUD:
    def __init__(self, player, constants):
        self.player = player
        self.constants = constants
        self.font = pygame.font.Font(None, 30)
        self.version = constants.get("game", {}).get("version", "1.00.000")

    def draw(self, screen):
        width = screen.get_width()
        height = screen.get_height()

        # Здоровье
        health_text = f"HP: {self.player.health}/{self.player.max_health}"
        text_surface = self.font.render(health_text, True, COLOR_WHITE)
        screen.blit(text_surface, (10, height - 40))

        # Патроны
        ammo_text = self.player.inventory.get_ammo_display()
        ammo_surface = self.font.render(f"Патроны: {ammo_text}", True, COLOR_YELLOW)
        screen.blit(ammo_surface, (10, height - 70))

        # Стамина
        stamina_bar_width = 150
        stamina_bar_height = 12
        stamina_x = 10
        stamina_y = height - 100
        pygame.draw.rect(screen, (60, 60, 60), (stamina_x, stamina_y, stamina_bar_width, stamina_bar_height))
        fill = (self.player.stamina / self.player.max_stamina) * stamina_bar_width
        if fill > 0:
            pygame.draw.rect(screen, (255, 200, 50), (stamina_x, stamina_y, fill, stamina_bar_height))
        pygame.draw.rect(screen, (200, 200, 200), (stamina_x, stamina_y, stamina_bar_width, stamina_bar_height), 1)
        stamina_text = f"STA: {int(self.player.stamina)}"
        stamina_surface = self.font.render(stamina_text, True, COLOR_WHITE)
        screen.blit(stamina_surface, (stamina_x, stamina_y - 20))

        # Версия
        version_surface = self.font.render(f"v{self.version}", True, COLOR_GRAY)
        screen.blit(version_surface, (width - 150, height - 30))

        # Перезарядка
        weapon = self.player.inventory.active_weapon
        if weapon and weapon.is_reloading:
            progress = 1 - (weapon.reload_timer / weapon.reload_time)
            bar_width = 200
            bar_height = 16
            x = width // 2 - bar_width // 2
            y = height - 100
            pygame.draw.rect(screen, (60, 60, 60), (x, y, bar_width, bar_height))
            pygame.draw.rect(screen, COLOR_GREEN, (x, y, bar_width * progress, bar_height))
            pygame.draw.rect(screen, (200, 200, 200), (x, y, bar_width, bar_height), 2)
            reload_text = self.font.render("Перезарядка...", True, COLOR_WHITE)
            screen.blit(reload_text, (width // 2 - reload_text.get_width() // 2, y - 25))
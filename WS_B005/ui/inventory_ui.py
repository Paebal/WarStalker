# ui/inventory_ui.py
import pygame
from constants import COLOR_WHITE, COLOR_YELLOW, COLOR_GRAY, COLOR_BLACK

class InventoryUI:
    def __init__(self, player):
        self.player = player
        self.visible = False
        self.font = pygame.font.Font(None, 24)
        self.slots = 9

    def toggle(self):
        self.visible = not self.visible

    def draw(self, screen):
        if not self.visible:
            self.draw_quickbar(screen)
        else:
            self.draw_full(screen)

    def draw_quickbar(self, screen):
        width = screen.get_width()
        height = screen.get_height()
        slot_size = int(min(width, height) * 0.04)
        spacing = int(slot_size * 0.2)
        total_width = self.slots * (slot_size + spacing) - spacing
        start_x = (width - total_width) // 2
        start_y = height - slot_size - int(height * 0.03)
        for i in range(self.slots):
            x = start_x + i * (slot_size + spacing)
            y = start_y
            rect = pygame.Rect(x, y, slot_size, slot_size)
            pygame.draw.rect(screen, COLOR_GRAY, rect, 2)
            if i < len(self.player.inventory.weapons):
                weapon = self.player.inventory.weapons[i]
                if weapon:
                    text = self.font.render(weapon.name, True, COLOR_WHITE)
                    screen.blit(text, (x + 5, y + 5))
            if self.player.inventory.active_weapon and i < len(self.player.inventory.weapons):
                if self.player.inventory.weapons[i] == self.player.inventory.active_weapon:
                    pygame.draw.rect(screen, COLOR_YELLOW, rect, 3)

    def draw_full(self, screen):
        width = screen.get_width()
        height = screen.get_height()
        overlay = pygame.Surface((width, height))
        overlay.set_alpha(200)
        overlay.fill(COLOR_BLACK)
        screen.blit(overlay, (0,0))
        title = self.font.render("ИНВЕНТАРЬ", True, COLOR_WHITE)
        screen.blit(title, (width//2 - title.get_width()//2, 50))
        y = int(height * 0.15)
        for i, weapon in enumerate(self.player.inventory.weapons):
            if weapon:
                text = self.font.render(f"{i+1}. {weapon.name} (маг: {weapon.magazine}, запас: {weapon.total_ammo})", True, COLOR_WHITE)
                screen.blit(text, (int(width * 0.1), y))
                y += int(height * 0.05)
        close_text = self.font.render("Нажмите I для закрытия", True, COLOR_GRAY)
        screen.blit(close_text, (width//2 - close_text.get_width()//2, height - 50))
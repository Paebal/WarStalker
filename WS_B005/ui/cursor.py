# ui/cursor.py
import pygame
from constants import COLOR_WHITE

class Cursor:
    def __init__(self):
        self.mouse_pos = (0,0)
        self.weapon_equipped = False

    def update(self, mouse_pos, weapon_equipped):
        self.mouse_pos = mouse_pos
        self.weapon_equipped = weapon_equipped

    def draw(self, screen):
        x, y = self.mouse_pos
        if not self.weapon_equipped:
            pygame.draw.circle(screen, COLOR_WHITE, (x, y), 4)
        else:
            size = 10
            gap = 4
            pygame.draw.line(screen, COLOR_WHITE, (x - size, y), (x - gap, y), 2)
            pygame.draw.line(screen, COLOR_WHITE, (x + gap, y), (x + size, y), 2)
            pygame.draw.line(screen, COLOR_WHITE, (x, y - size), (x, y - gap), 2)
            pygame.draw.line(screen, COLOR_WHITE, (x, y + gap), (x, y + size), 2)
            pygame.draw.circle(screen, COLOR_WHITE, (x, y), 2)
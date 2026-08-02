# game/entity.py
import pygame
from constants import COLOR_GRAY, COLOR_RED

class Entity:
    def __init__(self, x, y, width, height, color=COLOR_GRAY):
        self.id = id(self)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.rect = pygame.Rect(x - width/2, y - height/2, width, height)
        self.health = 100
        self.max_health = 100
        self.alive = True
        self.components = {}

    def update(self, dt):
        self.rect.x = self.x - self.width/2
        self.rect.y = self.y - self.height/2

    def draw(self, screen, camera):
        screen_rect = pygame.Rect(
            self.rect.x - camera.x,
            self.rect.y - camera.y,
            self.width,
            self.height
        )
        pygame.draw.rect(screen, self.color, screen_rect)
        if self.health < self.max_health:
            health_width = self.width * (self.health / self.max_health)
            health_rect = pygame.Rect(
                screen_rect.x,
                screen_rect.y - 6,
                health_width,
                4
            )
            pygame.draw.rect(screen, COLOR_RED, health_rect)

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "health": self.health,
            "max_health": self.max_health,
            "alive": self.alive
        }

    def from_dict(self, data):
        self.x = data["x"]
        self.y = data["y"]
        self.health = data["health"]
        self.max_health = data["max_health"]
        self.alive = data["alive"]
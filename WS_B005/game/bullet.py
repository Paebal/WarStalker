# game/bullet.py
import math
import pygame
from constants import BULLET_RADIUS, COLOR_YELLOW, BULLET_SPEED

class Bullet:
    def __init__(self, x, y, target_x, target_y, damage, owner):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.damage = damage
        self.owner = owner
        self.speed = BULLET_SPEED
        dx = target_x - x
        dy = target_y - y
        length = math.hypot(dx, dy)
        if length != 0:
            self.vx = dx / length * self.speed
            self.vy = dy / length * self.speed
        else:
            self.vx = 0
            self.vy = 0
        self.active = True
        self.radius = BULLET_RADIUS
        self.life = 5.0

    def update(self, dt):
        if not self.active:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 0:
            self.active = False

    def draw(self, screen, camera):
        if not self.active:
            return
        screen_x = self.x - camera.x
        screen_y = self.y - camera.y
        pygame.draw.circle(screen, COLOR_YELLOW, (int(screen_x), int(screen_y)), self.radius)

    def check_hit(self, target):
        if not target.alive:
            return False
        dx = self.x - target.x
        dy = self.y - target.y
        dist = math.hypot(dx, dy)
        return dist < (target.width/2 + self.radius)
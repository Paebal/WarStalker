# game/player.py
import math
import pygame
from game.entity import Entity
from game.inventory import Inventory
from constants import COLOR_BLUE, COLOR_WHITE

class Player(Entity):
    def __init__(self, x, y, config_loader, world=None):
        constants = config_loader.load_constants()
        player_cfg = constants.get("player", {})
        self.max_health = constants.get("game", {}).get("max_health", 100)
        self.speed_forward = player_cfg.get("speed_forward", 150)
        self.speed_side = player_cfg.get("speed_side", 100)
        self.speed_back = player_cfg.get("speed_back", 100)
        self.speed_run = 350

        width = 20
        height = 20
        super().__init__(x, y, width, height, COLOR_BLUE)
        self.health = self.max_health
        self.inventory = Inventory(constants)
        self.direction = pygame.math.Vector2(1, 0)
        self.weapon_ready = True

        # Стамина
        self.max_stamina = 100.0
        self.stamina = self.max_stamina
        self.stamina_regen_standing = 0.5
        self.stamina_regen_walking = 0.1
        self.stamina_drain_running = 2.0
        self.stamina_threshold_run = 20.0
        self.stamina_threshold_walk = 5.0

        # Ссылка на мир для коллизий
        self.world = world

    def update(self, dt, keys_pressed, settings):
        if dt > 0.05:
            dt = 0.05

        forward_key = settings.get_key("move_forward")
        backward_key = settings.get_key("move_backward")
        left_key = settings.get_key("move_left")
        right_key = settings.get_key("move_right")

        dir_vec = self.direction
        left_vec = pygame.math.Vector2(-dir_vec.y, dir_vec.x)

        move_vec = pygame.math.Vector2(0, 0)

        if keys_pressed.get(pygame.key.key_code(forward_key), False):
            move_vec += dir_vec
        if keys_pressed.get(pygame.key.key_code(backward_key), False):
            move_vec -= dir_vec
        if keys_pressed.get(pygame.key.key_code(left_key), False):
            move_vec += left_vec
        if keys_pressed.get(pygame.key.key_code(right_key), False):
            move_vec -= left_vec

        is_moving = move_vec.length() > 0
        is_running = False
        is_walking = False

        if is_moving:
            move_vec.normalize_ip()
            forward_comp = move_vec.dot(dir_vec)
            shift_pressed = keys_pressed.get(pygame.K_LSHIFT, False) or keys_pressed.get(pygame.K_RSHIFT, False)
            if forward_comp > 0.7 and shift_pressed and self.stamina > self.stamina_threshold_run:
                is_running = True
            else:
                is_walking = True

        # Обновление стамины
        if self.stamina <= 0:
            is_running = False
            is_walking = False
            self.stamina += self.stamina_regen_standing * dt
            if self.stamina > self.stamina_threshold_walk:
                self.stamina = self.stamina_threshold_walk
            move_vec = pygame.math.Vector2(0, 0)
            is_moving = False
        elif is_running:
            self.stamina -= self.stamina_drain_running * dt
            if self.stamina < 0:
                self.stamina = 0
        elif is_walking:
            self.stamina += self.stamina_regen_walking * dt
            if self.stamina > self.max_stamina:
                self.stamina = self.max_stamina
        else:
            self.stamina += self.stamina_regen_standing * dt
            if self.stamina > self.max_stamina:
                self.stamina = self.max_stamina

        # Вычисление скорости и перемещения
        if is_moving and move_vec.length() > 0:
            if is_running:
                speed = self.speed_run
            elif is_walking:
                if move_vec.dot(dir_vec) < -0.7:
                    speed = self.speed_back
                else:
                    speed = self.speed_side
            else:
                speed = 0

            if speed > 0:
                new_x = self.x + move_vec.x * speed * dt
                new_y = self.y + move_vec.y * speed * dt

                # Проверка коллизий по X и Y раздельно
                if self.world:
                    # Проверка по X
                    test_rect = pygame.Rect(new_x - self.width/2, self.y - self.height/2, self.width, self.height)
                    if not self.world.is_colliding(test_rect, ignore_entities=[self]):
                        self.x = new_x
                    # Проверка по Y
                    test_rect = pygame.Rect(self.x - self.width/2, new_y - self.height/2, self.width, self.height)
                    if not self.world.is_colliding(test_rect, ignore_entities=[self]):
                        self.y = new_y
                else:
                    self.x = new_x
                    self.y = new_y

        super().update(dt)

    def set_direction(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        length = math.hypot(dx, dy)
        if length > 0:
            self.direction = pygame.math.Vector2(dx / length, dy / length)

    def shoot(self):
        weapon = self.inventory.active_weapon
        if weapon and weapon.can_shoot():
            weapon.shoot()
            return True
        return False

    def reload(self):
        weapon = self.inventory.active_weapon
        if weapon:
            return weapon.start_reload()
        return False

    def switch_weapon(self, index):
        return self.inventory.switch_weapon(index)

    def draw(self, screen, camera):
        super().draw(screen, camera)
        end_x = self.x + self.direction.x * 30
        end_y = self.y + self.direction.y * 30
        pygame.draw.line(screen, COLOR_WHITE,
                         (self.x - camera.x, self.y - camera.y),
                         (end_x - camera.x, end_y - camera.y), 2)

    def to_dict(self):
        data = super().to_dict()
        data["inventory"] = self.inventory.to_dict()
        data["direction_x"] = self.direction.x
        data["direction_y"] = self.direction.y
        data["stamina"] = self.stamina
        return data

    def from_dict(self, data):
        super().from_dict(data)
        self.inventory.from_dict(data["inventory"])
        self.direction = pygame.math.Vector2(data["direction_x"], data["direction_y"])
        self.stamina = data.get("stamina", self.max_stamina)
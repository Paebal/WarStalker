# game/game.py
import pygame
import sys
import json
import os
import ctypes
from settings import Settings
from event_bus import event_bus
from game.world import World, Camera
from game.player import Player
from game.bullet import Bullet
from game.entity_manager import EntityManager
from game.physics_manager import PhysicsManager
from game.ai_manager import AIManager
from game.network_manager import NetworkManager
from game.render_manager import RenderManager
from game.config_loader import ConfigLoader
from ui.hud import HUD
from ui.chat import Chat
from ui.inventory_ui import InventoryUI
from ui.menu import MainMenu, SettingsMenu
from ui.pause_menu import PauseMenu
from ui.cursor import Cursor

class Game:
    def __init__(self, settings):
        self.settings = settings
        self.running = True
        self.paused = False
        self.clock = pygame.time.Clock()
        self.screen = None
        self.is_fullscreen = settings.data["fullscreen"]
        self.is_borderless = settings.data["borderless"]

        self.screen_width = 1280
        self.screen_height = 720

        self.config_loader = ConfigLoader()
        self.constants = self.config_loader.load_constants()
        self.current_map_name = "cordon"
        self.map_data = self.config_loader.load_map(self.current_map_name)

        # Dev-режим: активируется только при наличии файла dev_mode.flag в корне
        self.dev_mode = os.path.exists("dev_mode.flag")
        if self.dev_mode:
            print("!!! DEV MODE ACTIVATED !!!")

        self.init_screen()

        self.entity_manager = EntityManager()
        self.physics_manager = PhysicsManager()
        self.ai_manager = AIManager()
        self.network_manager = NetworkManager()

        self.map_scale = self.settings.get_map_scale()
        self.world = World(self.map_data, scale=self.map_scale)
        self.camera = Camera(self.screen_width, self.screen_height)
        self.render_manager = RenderManager(self.screen)

        spawn_x, spawn_y = self.get_spawn()
        self.player = Player(spawn_x, spawn_y, self.config_loader, world=self.world)
        self.entity_manager.set_player(self.player)

        self.hud = HUD(self.player, self.constants)
        self.chat = Chat()
        self.inventory_ui = InventoryUI(self.player)
        self.cursor = Cursor()

        self.bullets = []
        self.keys_pressed = {}

        self.font = pygame.font.Font(None, 30)

        self.load_game("auto_save.json")
        event_bus.subscribe("shoot", self.on_shoot_event)
        event_bus.subscribe("reload", self.on_reload_event)

    def get_spawn(self):
        if self.map_data and "spawn" in self.map_data:
            sx, sy = self.map_data["spawn"]
            return int(sx * self.map_scale), int(sy * self.map_scale)
        return int(670 * self.map_scale), int(2469 * self.map_scale)

    def load_map(self, map_name):
        self.current_map_name = map_name
        self.map_data = self.config_loader.load_map(map_name)
        if "map_scale" in self.map_data:
            new_scale = self.map_data["map_scale"]
            if new_scale != self.map_scale:
                self.map_scale = new_scale
                self.settings.set_map_scale(new_scale)
        print(f"[GAME] Загрузка карты {map_name}, масштаб {self.map_scale}, объектов: {len(self.map_data.get('objects', []))}")
        self.world = World(self.map_data, scale=self.map_scale)
        self.camera = Camera(self.screen_width, self.screen_height)
        sx, sy = self.get_spawn()
        self.player.x = sx
        self.player.y = sy
        self.player.world = self.world  # обновляем ссылку на мир
        self.camera.update(self.player, self.world.width, self.world.height)
        self.chat.add_message("Система", f"Загружена карта: {map_name}", temporary=True)

    def center_window(self):
        try:
            user32 = ctypes.windll.user32
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            x = (screen_width - self.screen_width) // 2
            y = (screen_height - self.screen_height) // 2
            hwnd = pygame.display.get_wm_info()['window']
            user32.SetWindowPos(hwnd, 0, x, y, self.screen_width, self.screen_height, 0)
        except:
            os.environ['SDL_VIDEO_CENTERED'] = '1'

    def init_screen(self):
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height),
                                                  pygame.FULLSCREEN | (pygame.NOFRAME if self.is_borderless else 0))
        else:
            flags = pygame.NOFRAME if self.is_borderless else 0
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), flags)
        pygame.display.set_caption("War Stalker 1.0")
        if not self.is_fullscreen:
            self.center_window()
        if hasattr(self, 'camera'):
            self.camera.width = self.screen_width
            self.camera.height = self.screen_height
        if hasattr(self, 'render_manager'):
            self.render_manager.screen = self.screen

    def set_resolution(self, width, height):
        self.screen_width = width
        self.screen_height = height
        self.settings.data["resolution"] = f"{width}x{height}"
        self.settings.save()
        self.init_screen()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.settings.toggle_fullscreen()
        self.init_screen()

    def toggle_borderless(self):
        self.is_borderless = not self.is_borderless
        self.settings.toggle_borderless()
        self.init_screen()

    def set_map_scale(self, new_scale):
        if not self.dev_mode:
            return
        self.map_scale = new_scale
        self.settings.set_map_scale(new_scale)
        self.world.reload(new_scale)
        sx, sy = self.get_spawn()
        self.player.x = sx
        self.player.y = sy
        self.player.world = self.world
        self.camera.update(self.player, self.world.width, self.world.height)
        self.chat.add_message("Система", f"Масштаб карты изменён на {new_scale}", temporary=True)

    def new_game(self):
        if self.player:
            self.entity_manager.remove_entity(self.player)
        sx, sy = self.get_spawn()
        self.player = Player(sx, sy, self.config_loader, world=self.world)
        self.entity_manager.set_player(self.player)
        self.bullets = []
        self.chat = Chat()
        self.hud = HUD(self.player, self.constants)
        self.inventory_ui = InventoryUI(self.player)
        self.paused = False
        self.chat.add_message("Система", "Добро пожаловать в Зону!", temporary=False)

    def run(self, skip_menu=False):
        if not skip_menu:
            menu = MainMenu(self)
            menu.run()
            if not self.running:
                return

        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            if not self.paused:
                self.update(dt)
            self.render()
            pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.keys_pressed[event.key] = True
                if event.key == pygame.key.key_code(self.settings.get_key("pause")):
                    pause_menu = PauseMenu(self)
                    pause_menu.run()
                    if pause_menu.back_to_menu:
                        self.running = False
                        self.run()
                        return
                    elif not pause_menu.continue_game:
                        self.running = False
                        return
                elif event.key == pygame.key.key_code(self.settings.get_key("inventory")):
                    self.inventory_ui.toggle()
                elif event.key == pygame.key.key_code(self.settings.get_key("chat")):
                    self.chat.toggle_input()
                elif event.key == pygame.key.key_code(self.settings.get_key("reload")):
                    self.player.reload()
                    self.chat.add_message("Система", "Перезарядка начата", temporary=True)
                elif event.key == pygame.key.key_code(self.settings.get_key("weapon_1")):
                    self.player.switch_weapon(0)
                    weapon = self.player.inventory.active_weapon
                    if weapon:
                        self.chat.add_message("Система", f"Выбрано: {weapon.name}", temporary=True)
                    else:
                        self.chat.add_message("Система", "Оружие убрано", temporary=True)
                elif event.key == pygame.key.key_code(self.settings.get_key("weapon_2")):
                    self.player.switch_weapon(1)
                    weapon = self.player.inventory.active_weapon
                    if weapon:
                        self.chat.add_message("Система", f"Выбрано: {weapon.name}", temporary=True)
                elif event.key == pygame.key.key_code(self.settings.get_key("weapon_3")):
                    self.player.switch_weapon(2)
                    weapon = self.player.inventory.active_weapon
                    if weapon:
                        self.chat.add_message("Система", f"Выбрано: {weapon.name}", temporary=True)
                    else:
                        self.chat.add_message("Система", "Оружие убрано", temporary=True)
                elif event.key == pygame.key.key_code("f11"):
                    self.toggle_fullscreen()
                elif event.key == pygame.key.key_code("f12"):
                    self.toggle_borderless()
                elif event.key == pygame.K_F5:
                    self.save_game("save_quick.json")
                    self.chat.add_message("Система", "Игра сохранена", temporary=True)
                elif event.key == pygame.K_F9:
                    self.load_game("save_quick.json")
                    self.chat.add_message("Система", "Игра загружена", temporary=True)

            elif event.type == pygame.KEYUP:
                if event.key in self.keys_pressed:
                    del self.keys_pressed[event.key]

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not self.chat.is_input_active():
                    self.player_shoot()

            elif event.type == pygame.MOUSEMOTION:
                if not self.chat.is_input_active():
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    world_x = mouse_x + self.camera.x
                    world_y = mouse_y + self.camera.y
                    self.player.set_direction(world_x, world_y)

        if self.chat.is_input_active():
            try:
                if event:
                    self.chat.handle_events(event)
            except:
                pass

    def player_shoot(self):
        if not self.player.alive:
            return
        weapon = self.player.inventory.active_weapon
        if not weapon:
            self.chat.add_message("Система", "Нет оружия!", temporary=True)
            return
        mouse_x, mouse_y = pygame.mouse.get_pos()
        target_x = mouse_x + self.camera.x
        target_y = mouse_y + self.camera.y
        if weapon.max_magazine == 0 or "нож" in weapon.name.lower():
            hit = False
            for entity in self.entity_manager.get_entities():
                if entity != self.player and entity.alive:
                    dist = ((entity.x - target_x)**2 + (entity.y - target_y)**2)**0.5
                    if dist < 50:
                        damage = 30
                        entity.take_damage(damage)
                        self.chat.add_message("Бой", f"Нанесено {damage} урона ножом", temporary=True)
                        hit = True
                        break
            if not hit:
                self.chat.add_message("Бой", "Промах ножом", temporary=True)
        else:
            if weapon.can_shoot():
                weapon.shoot()
                damage = getattr(weapon, 'damage', 15)
                bullet = Bullet(self.player.x, self.player.y, target_x, target_y, damage, self.player)
                self.bullets.append(bullet)
                self.chat.add_message("Бой", f"Выстрел из {weapon.name}", temporary=True)
            else:
                self.chat.add_message("Система", "Нет патронов!", temporary=True)

    def update(self, dt):
        self.entity_manager.update_all(dt, self.keys_pressed, self.settings)
        for bullet in self.bullets[:]:
            bullet.update(dt)
            if not bullet.active:
                self.bullets.remove(bullet)
                continue
            for entity in self.entity_manager.get_entities():
                if entity != bullet.owner and entity.alive:
                    if bullet.check_hit(entity):
                        entity.take_damage(bullet.damage)
                        self.chat.add_message("Бой", f"Попадание! Урон {bullet.damage}", temporary=True)
                        bullet.active = False
                        break
        self.world.tile_map.process_queue()
        weapon = self.player.inventory.active_weapon
        if weapon:
            if weapon.update_reload(dt):
                self.chat.add_message("Система", "Перезарядка завершена", temporary=True)
        self.camera.update(self.player, self.world.width, self.world.height)
        self.physics_manager.update(dt)
        self.ai_manager.update(dt)
        self.chat.update(dt)

    def render(self):
        self.render_manager.render_world_only(self.world, self.camera)
        self.render_manager.render_entities_except_player(self.entity_manager, self.camera)
        for bullet in self.bullets:
            bullet.draw(self.screen, self.camera)
        self.hud.draw(self.screen)
        self.inventory_ui.draw(self.screen)
        self.chat.draw(self.screen)
        mouse_pos = pygame.mouse.get_pos()
        weapon = self.player.inventory.active_weapon
        weapon_equipped = weapon is not None and weapon.max_magazine > 0
        self.cursor.update(mouse_pos, weapon_equipped)
        self.cursor.draw(self.screen)
        self.render_manager.render_player(self.player, self.camera)

        if self.settings.get_show_fps():
            fps_text = f"FPS: {int(self.clock.get_fps())}"
            fps_surface = self.font.render(fps_text, True, (255,255,0))
            self.screen.blit(fps_surface, (self.screen_width - 100, 10))

        if self.paused:
            overlay = pygame.Surface((self.screen_width, self.screen_height))
            overlay.set_alpha(128)
            overlay.fill((0,0,0))
            self.screen.blit(overlay, (0,0))
            font = pygame.font.Font(None, 74)
            text = font.render("ПАУЗА", True, (255,255,255))
            self.screen.blit(text, (self.screen_width//2 - text.get_width()//2,
                                    self.screen_height//2 - text.get_height()//2))

    def save_game(self, filename="save.json"):
        data = {
            "player": self.player.to_dict(),
            "bullets": [],
            "world": {
                "width": self.world.width,
                "height": self.world.height
            },
            "map_scale": self.map_scale,
            "current_map": self.current_map_name
        }
        os.makedirs("saves", exist_ok=True)
        with open(os.path.join("saves", filename), "w") as f:
            json.dump(data, f, indent=4)

    def load_game(self, filename="save.json"):
        try:
            with open(os.path.join("saves", filename), "r") as f:
                data = json.load(f)
            if self.player:
                self.entity_manager.remove_entity(self.player)
            if "map_scale" in data:
                scale = data["map_scale"]
                if scale != self.map_scale:
                    self.set_map_scale(scale)
            if "current_map" in data and data["current_map"] != self.current_map_name:
                self.load_map(data["current_map"])
            self.player = Player(0, 0, self.config_loader, world=self.world)
            self.player.from_dict(data["player"])
            self.entity_manager.set_player(self.player)
            self.bullets = []
            self.chat.add_message("Система", "Загрузка выполнена", temporary=True)
        except FileNotFoundError:
            self.chat.add_message("Система", "Сохранение не найдено", temporary=True)

    def on_shoot_event(self, data):
        pass

    def on_reload_event(self, data):
        pass

    def quit(self):
        self.running = False
        pygame.quit()
        sys.exit()
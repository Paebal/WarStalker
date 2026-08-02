# game/render_manager.py
import pygame

class RenderManager:
    def __init__(self, screen):
        self.screen = screen

    def render_world_only(self, world, camera):
        world.draw(self.screen, camera)

    def render_entities_except_player(self, entity_manager, camera):
        player = entity_manager.get_player()
        for entity in entity_manager.get_entities():
            if entity != player and entity.alive:
                entity.draw(self.screen, camera)

    def render_player(self, player, camera):
        if player and player.alive:
            player.draw(self.screen, camera)

    def render(self, world, entity_manager, camera):
        world.draw(self.screen, camera)
        entity_manager.draw_all(self.screen, camera)
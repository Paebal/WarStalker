# game/entity_manager.py
import inspect

class EntityManager:
    def __init__(self):
        self.entities = []
        self.player = None

    def add_entity(self, entity):
        if entity not in self.entities:
            self.entities.append(entity)
        return entity

    def remove_entity(self, entity):
        if entity in self.entities:
            self.entities.remove(entity)

    def get_entities(self):
        return self.entities

    def get_player(self):
        return self.player

    def set_player(self, player):
        if self.player and self.player in self.entities:
            self.entities.remove(self.player)
        self.player = player
        if player and player not in self.entities:
            self.entities.append(player)

    def update_all(self, dt, keys_pressed, settings):
        for entity in self.entities[:]:
            if entity.alive:
                sig = inspect.signature(entity.update)
                params = list(sig.parameters.keys())
                if len(params) == 3:
                    entity.update(dt, keys_pressed, settings)
                else:
                    entity.update(dt)

    def draw_all(self, screen, camera):
        for entity in self.entities:
            if entity.alive:
                entity.draw(screen, camera)
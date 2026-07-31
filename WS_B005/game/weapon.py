# game/weapon.py
class Weapon:
    def __init__(self, name, weapon_type, damage_head, damage_body, magazine=0, total_ammo=0, reload_time=1.0):
        self.name = name
        self.type = weapon_type
        self.damage_head = damage_head
        self.damage_body = damage_body
        self.magazine = magazine
        self.total_ammo = total_ammo
        self.max_magazine = magazine
        self.reload_time = reload_time
        self.is_reloading = False
        self.reload_timer = 0.0

    def can_shoot(self):
        return self.magazine > 0 and not self.is_reloading

    def shoot(self):
        if self.can_shoot():
            self.magazine -= 1
            return True
        return False

    def start_reload(self):
        if self.is_reloading:
            return False
        if self.total_ammo <= 0:
            return False
        if self.magazine == self.max_magazine:
            return False
        self.is_reloading = True
        self.reload_timer = self.reload_time
        return True

    def update_reload(self, dt):
        if not self.is_reloading:
            return False
        self.reload_timer -= dt
        if self.reload_timer <= 0:
            self.is_reloading = False
            need = self.max_magazine - self.magazine
            if need > self.total_ammo:
                add = self.total_ammo
            else:
                add = need
            self.magazine += add
            self.total_ammo -= add
            return True
        return False

    def reload(self):
        return self.start_reload()

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "damage_head": self.damage_head,
            "damage_body": self.damage_body,
            "magazine": self.magazine,
            "total_ammo": self.total_ammo,
            "max_magazine": self.max_magazine,
            "reload_time": self.reload_time,
            "is_reloading": self.is_reloading,
            "reload_timer": self.reload_timer
        }

    @staticmethod
    def create_from_config(data):
        return Weapon(
            name=data["name"],
            weapon_type=data["type"],
            damage_head=data["damage_head"],
            damage_body=data["damage_body"],
            magazine=data.get("magazine", 0),
            total_ammo=data.get("total_ammo", 0),
            reload_time=data.get("reload_time", 1.0)
        )

class PistolPM(Weapon):
    def __init__(self):
        super().__init__("ПМ", 2, 30, 15, 8, 8, 4.0)
        self.max_magazine = 8

class Knife(Weapon):
    def __init__(self):
        super().__init__("Нож", 3, 50, 30, 1, 0, 0.5)
        self.max_magazine = 0

    def can_shoot(self):
        return True

    def shoot(self):
        return True

    def start_reload(self):
        return False

    def update_reload(self, dt):
        return False

    def reload(self):
        return False
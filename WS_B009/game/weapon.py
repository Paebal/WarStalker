# game/weapon.py
class Weapon:
    def __init__(self, name, weapon_type, damage_head, damage_body, magazine=0, total_ammo=0, reload_time=1.0,
                 max_magazine=None, accuracy=0.8, pellets=1, range=20, burst=3, max_durability=400):
        self.name = name
        self.type = weapon_type
        self.damage_head = damage_head
        self.damage_body = damage_body
        self.magazine = magazine
        self.total_ammo = total_ammo
        self.max_magazine = max_magazine if max_magazine is not None else magazine
        self.reload_time = reload_time
        self.is_reloading = False
        self.reload_timer = 0.0
        self.accuracy = accuracy
        self.pellets = pellets
        self.range = range
        self.burst = burst
        self.max_durability = max_durability
        self.durability = max_durability

    def can_shoot(self):
        return self.magazine > 0 and not self.is_reloading and self.durability > 0

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
            "reload_timer": self.reload_timer,
            "accuracy": self.accuracy,
            "pellets": self.pellets,
            "range": self.range,
            "burst": self.burst,
            "max_durability": self.max_durability,
            "durability": self.durability
        }

    @staticmethod
    def create_from_config(data):
        """Создаёт оружие из словаря YAML (weapons.yaml)"""
        return Weapon(
            name=data.get("name", "Unknown"),
            weapon_type=data.get("type", 2),
            damage_head=data.get("damage_head", data.get("damage", 15)),  # если damage_head нет, берём damage
            damage_body=data.get("damage_body", data.get("damage", 15)),
            magazine=data.get("magazine_capacity", 0),
            total_ammo=data.get("total_ammo", 0),
            reload_time=data.get("reload_time", 1.0),
            max_magazine=data.get("magazine_capacity", 0),
            accuracy=data.get("accuracy", 0.8),
            pellets=data.get("pellets", 1),
            range=data.get("range", 20),
            burst=data.get("burst", 3),
            max_durability=data.get("max_durability", 400)
        )

    @staticmethod
    def create_from_dict(data):
        """Восстанавливает оружие из словаря сохранения"""
        w = Weapon(
            name=data["name"],
            weapon_type=data["type"],
            damage_head=data["damage_head"],
            damage_body=data["damage_body"],
            magazine=data["magazine"],
            total_ammo=data["total_ammo"],
            reload_time=data["reload_time"],
            max_magazine=data["max_magazine"],
            accuracy=data.get("accuracy", 0.8),
            pellets=data.get("pellets", 1),
            range=data.get("range", 20),
            burst=data.get("burst", 3),
            max_durability=data.get("max_durability", 400)
        )
        w.is_reloading = data.get("is_reloading", False)
        w.reload_timer = data.get("reload_timer", 0.0)
        w.durability = data.get("durability", w.max_durability)
        return w


# Для обратной совместимости оставляем старые классы
class PistolPM(Weapon):
    def __init__(self):
        super().__init__("ПМ", 2, 30, 15, 8, 8, 4.0, max_magazine=8)

class Knife(Weapon):
    def __init__(self):
        super().__init__("Нож", 3, 50, 30, 1, 0, 0.5, max_magazine=0)
        self.max_durability = 1000
        self.durability = 1000

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
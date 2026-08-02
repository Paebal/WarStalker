# game/inventory.py
from game.weapon import Weapon, Knife, PistolPM

class Inventory:
    def __init__(self, config=None, weapons_data=None):
        self.weapons = [Knife(), PistolPM(), None]
        self.active_weapon_index = 1
        # Если переданы данные оружия из конфига, создаём оружие по ним
        if weapons_data:
            self.load_weapons_from_config(weapons_data)

    def load_weapons_from_config(self, weapons_data):
        """Загружает оружие из списка словарей (YAML) и заменяет стандартные."""
        new_weapons = []
        for i in range(3):
            if i < len(weapons_data):
                w_data = weapons_data[i]
                if w_data:
                    w = Weapon.create_from_config(w_data)
                    new_weapons.append(w)
                else:
                    new_weapons.append(None)
            else:
                new_weapons.append(None)
        # Сохраняем активное оружие, если было
        old_active = self.active_weapon
        self.weapons = new_weapons
        # Пытаемся сохранить индекс, если он валиден
        if self.active_weapon_index >= len(self.weapons):
            self.active_weapon_index = 0

    @property
    def active_weapon(self):
        if 0 <= self.active_weapon_index < len(self.weapons):
            return self.weapons[self.active_weapon_index]
        return None

    def switch_weapon(self, index):
        if 0 <= index < len(self.weapons):
            if self.active_weapon and self.active_weapon.is_reloading:
                self.active_weapon.is_reloading = False
            self.active_weapon_index = index
            return True
        return False

    def add_weapon(self, weapon):
        # Поиск свободного слота или замена
        for i in range(len(self.weapons)):
            if self.weapons[i] is None:
                self.weapons[i] = weapon
                return True
        return False

    def get_ammo_display(self):
        weapon = self.active_weapon
        if weapon:
            return f"{weapon.magazine}/{weapon.total_ammo}"
        return "0/0"

    def to_dict(self):
        return {
            "weapons": [w.to_dict() if w else None for w in self.weapons],
            "active_index": self.active_weapon_index
        }

    def from_dict(self, data):
        self.weapons = []
        for w_data in data["weapons"]:
            if w_data is None:
                self.weapons.append(None)
            else:
                # Используем универсальный метод создания
                w = Weapon.create_from_dict(w_data)
                self.weapons.append(w)
        self.active_weapon_index = data.get("active_index", 1)
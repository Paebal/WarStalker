# game/inventory.py
from game.weapon import Weapon, PistolPM, Knife

class Inventory:
    def __init__(self, config=None):
        self.weapons = [Knife(), PistolPM(), None]
        self.active_weapon_index = 1

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
        if weapon.type == 1:
            self.weapons[2] = weapon
        elif weapon.type == 2:
            self.weapons[1] = weapon
        elif weapon.type == 3:
            self.weapons[0] = weapon

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
                name = w_data.get("name", "Unknown")
                weapon_type = w_data.get("type", 2)
                damage_head = w_data.get("damage_head", 30)
                damage_body = w_data.get("damage_body", 15)
                magazine = w_data.get("magazine", 0)
                total_ammo = w_data.get("total_ammo", 0)
                reload_time = w_data.get("reload_time", 1.0)
                is_reloading = w_data.get("is_reloading", False)
                reload_timer = w_data.get("reload_timer", 0.0)
                w = Weapon(name, weapon_type, damage_head, damage_body, magazine, total_ammo, reload_time)
                w.is_reloading = is_reloading
                w.reload_timer = reload_timer
                self.weapons.append(w)
        self.active_weapon_index = data.get("active_index", 1)
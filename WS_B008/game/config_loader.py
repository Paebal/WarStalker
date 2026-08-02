# game/config_loader.py
import yaml
import os

class ConfigLoader:
    def __init__(self, config_dir="data/config", maps_dir="data/maps"):
        self.config_dir = config_dir
        self.maps_dir = maps_dir
        self.usermaps_dir = os.path.join(maps_dir, "usermaps")
        os.makedirs(self.usermaps_dir, exist_ok=True)
        self.cache = {}

    def load_yaml(self, filename, subdir=None):
        if subdir:
            path = os.path.join(self.config_dir, subdir, filename)
        else:
            path = os.path.join(self.config_dir, filename)
        if filename in self.cache:
            return self.cache[filename]
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self.cache[filename] = data
            return data

    def load_constants(self):
        return self.load_yaml("constants.yaml")

    def load_weapons(self):
        data = self.load_yaml("weapons.yaml")
        return data.get("weapons", [])

    def load_items(self):
        data = self.load_yaml("items.yaml")
        return data.get("items", [])

    def load_armors(self):
        data = self.load_yaml("armors.yaml")
        return data.get("armors", [])

    def load_artifacts(self):
        data = self.load_yaml("artifacts.yaml")
        return data.get("artifacts", [])

    def load_ammo(self):
        data = self.load_yaml("ammo.yaml")
        return data.get("ammo", [])

    def load_names(self):
        data = self.load_yaml("names.yaml")
        return data.get("first_names", [])

    def load_surnames(self):
        data = self.load_yaml("surnames.yaml")
        return data.get("last_names", [])

    def load_map(self, map_name):
        user_path = os.path.join(self.usermaps_dir, f"{map_name}.yaml")
        if os.path.exists(user_path):
            with open(user_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        main_path = os.path.join(self.maps_dir, f"{map_name}.yaml")
        if os.path.exists(main_path):
            with open(main_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        raise FileNotFoundError(f"Карта {map_name} не найдена")

    def list_maps(self):
        maps = []
        if os.path.exists(self.maps_dir):
            for f in os.listdir(self.maps_dir):
                if f.endswith(".yaml") and os.path.isfile(os.path.join(self.maps_dir, f)):
                    maps.append(("builtin", f.replace(".yaml", "")))
        if os.path.exists(self.usermaps_dir):
            for f in os.listdir(self.usermaps_dir):
                if f.endswith(".yaml") and os.path.isfile(os.path.join(self.usermaps_dir, f)):
                    maps.append(("user", f.replace(".yaml", "")))
        return maps

    def save_map(self, map_data, map_name, user=True):
        if user:
            path = os.path.join(self.usermaps_dir, f"{map_name}.yaml")
        else:
            path = os.path.join(self.maps_dir, f"{map_name}.yaml")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(map_data, f, allow_unicode=True, sort_keys=False)
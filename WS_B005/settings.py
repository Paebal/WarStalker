# settings.py
import json
import os

DEFAULT_SETTINGS = {
    "fullscreen": False,
    "borderless": False,
    "resolution": "1280x720",
    "volume": 0.5,
    "map_scale": 50.0,
    "show_fps": False,
    "keys": {
        "move_forward": "w",
        "move_backward": "s",
        "move_left": "a",
        "move_right": "d",
        "shoot": "mouse_left",
        "reload": "r",
        "weapon_1": "1",
        "weapon_2": "2",
        "weapon_3": "3",
        "inventory": "i",
        "chat": "t",
        "interact": "e",
        "pause": "escape"
    }
}

class Settings:
    def __init__(self):
        self.data = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        try:
            with open("settings.json", "r") as f:
                loaded = json.load(f)
                for key in loaded:
                    if key in self.data:
                        if isinstance(self.data[key], dict) and isinstance(loaded[key], dict):
                            self.data[key].update(loaded[key])
                        else:
                            self.data[key] = loaded[key]
        except FileNotFoundError:
            self.save()

    def save(self):
        with open("settings.json", "w") as f:
            json.dump(self.data, f, indent=4)

    def get_key(self, action):
        return self.data["keys"].get(action, "")

    def set_key(self, action, key):
        self.data["keys"][action] = key
        self.save()

    def toggle_fullscreen(self):
        self.data["fullscreen"] = not self.data["fullscreen"]
        self.save()

    def toggle_borderless(self):
        self.data["borderless"] = not self.data["borderless"]
        self.save()

    def get_map_scale(self):
        return self.data.get("map_scale", 50.0)

    def set_map_scale(self, value):
        self.data["map_scale"] = float(value)
        self.save()

    def toggle_fps(self):
        self.data["show_fps"] = not self.data["show_fps"]
        self.save()

    def get_show_fps(self):
        return self.data.get("show_fps", False)
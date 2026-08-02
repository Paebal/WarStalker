# game/network_manager.py
class NetworkManager:
    def __init__(self):
        self.is_server = False
        self.is_client = False

    def start_server(self):
        self.is_server = True

    def start_client(self, address):
        self.is_client = True

    def send_event(self, event_type, data):
        pass

    def receive_events(self):
        return []
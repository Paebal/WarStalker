# ui/chat.py
import pygame
from constants import COLOR_WHITE, COLOR_GREEN
import time

class Chat:
    def __init__(self):
        self.font = pygame.font.Font(None, 24)
        self.messages = []
        self.input_active = False
        self.input_text = ""
        self.max_messages = 20
        self.visible_lines = 10
        self.max_temporary = 2
        self.temporary_lifetime = 5.0

    def add_message(self, sender, text, temporary=False):
        current_time = time.time()
        expire_time = current_time + self.temporary_lifetime if temporary else None
        if temporary:
            temp_msgs = [m for m in self.messages if m[3] is True]
            while len(temp_msgs) >= self.max_temporary:
                oldest = min(temp_msgs, key=lambda m: m[0])
                self.messages.remove(oldest)
                temp_msgs.remove(oldest)
        self.messages.append((current_time, sender, text, temporary, expire_time))
        if len(self.messages) > self.max_messages + self.max_temporary:
            non_temp = [m for m in self.messages if m[3] is False]
            if non_temp:
                oldest = min(non_temp, key=lambda m: m[0])
                self.messages.remove(oldest)

    def toggle_input(self):
        self.input_active = not self.input_active
        if self.input_active:
            self.input_text = ""

    def is_input_active(self):
        return self.input_active

    def handle_events(self, event):
        if not self.input_active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.input_text.strip():
                    self.add_message("Игрок", self.input_text, temporary=False)
                self.input_active = False
                self.input_text = ""
            elif event.key == pygame.K_ESCAPE:
                self.input_active = False
                self.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode

    def update(self, dt):
        current_time = time.time()
        self.messages = [m for m in self.messages if not (m[3] and m[4] and current_time > m[4])]

    def draw(self, screen):
        width = screen.get_width()
        height = screen.get_height()
        start = max(0, len(self.messages) - self.visible_lines)
        y_offset = int(height * 0.02)
        for i in range(start, len(self.messages)):
            timestamp, sender, text, temporary, expire_time = self.messages[i]
            color = (200, 200, 200) if temporary else COLOR_WHITE
            msg = f"[{sender}] {text}"
            surface = self.font.render(msg, True, color)
            x = int(width * 0.02)
            screen.blit(surface, (x, y_offset))
            y_offset += int(height * 0.035)
        if self.input_active:
            input_surface = self.font.render("> " + self.input_text, True, COLOR_GREEN)
            x = (width - input_surface.get_width()) // 2
            y = int(height * 0.95)
            screen.blit(input_surface, (x, y))
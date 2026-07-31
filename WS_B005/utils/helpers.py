# utils/helpers.py
# Вспомогательные функции

import math

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)
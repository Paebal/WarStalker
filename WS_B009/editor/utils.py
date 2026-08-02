# editor/utils.py
import math

def rnd(v):
    return round(v, 2)

def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))
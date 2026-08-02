# editor/__init__.py
# Пакет редактора карт WarStalker

from .constants import *
from .utils import *
from .models import EditorModel
from .views import EditorView
from .controller import EditorController
from .start_menu import StartMenu
from .main import main

__all__ = [
    'EditorModel',
    'EditorView',
    'EditorController',
    'StartMenu',
    'main',
    'COLOR_BG', 'COLOR_GRID', 'COLOR_PANEL', 'COLOR_WHITE',
    'COLOR_RED', 'COLOR_GREEN', 'COLOR_BLUE', 'COLOR_YELLOW',
    'COLOR_BLACK', 'COLOR_GRAY', 'COLOR_LIGHT_GRAY', 'COLOR_ORANGE',
    'COLOR_SELECT', 'COLOR_CURSOR', 'COLOR_HOVER', 'COLOR_RESIZE',
    'COLOR_ANGLE', 'COLOR_LABEL', 'COLOR_MARKER', 'COLOR_TEMP',
    'COLOR_RIGHT_PANEL_BG', 'COLOR_RIGHT_PANEL_BORDER',
    'COLOR_RIGHT_PANEL_ITEM', 'COLOR_RIGHT_PANEL_ITEM_HOVER',
    'COLOR_RIGHT_PANEL_ITEM_SELECTED', 'COLOR_RIGHT_PANEL_TEXT',
    'COLOR_RIGHT_PANEL_TRIGGER', 'COLOR_GROUP_EXPAND', 'COLOR_DUMMY',
    'COLOR_PLACEMENT_GHOST',
    'PANEL_WIDTH', 'ICON_SIZE', 'COLOR_BOX_SIZE', 'SLIDER_WIDTH',
    'SLIDER_HEIGHT', 'RIGHT_PANEL_WIDTH', 'RIGHT_PANEL_TRIGGER_WIDTH',
    'INDENT_WIDTH',
    'rnd', 'clamp'
]
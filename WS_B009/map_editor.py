#!/usr/bin/env python3
# map_editor.py — точка запуска редактора карт WarStalker

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from editor.main import main

if __name__ == "__main__":
    main()
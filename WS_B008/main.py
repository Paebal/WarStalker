# main.py
import sys
import pygame
from settings import Settings
from game.game import Game

def main():
    pygame.init()
    settings = Settings()
    game = Game(settings)
    if len(sys.argv) > 2 and sys.argv[1] == "--map":
        map_name = sys.argv[2]
        game.load_map(map_name)
        game.run(skip_menu=True)
    else:
        game.run()

if __name__ == "__main__":
    main()
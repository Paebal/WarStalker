# editor/main.py
# Точка входа в редактор с меню

import pygame
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.config_loader import ConfigLoader
from .controller import EditorController
from .start_menu import StartMenu

def main():
    pygame.init()
    screen = pygame.display.set_mode((1400, 900), pygame.RESIZABLE | pygame.DOUBLEBUF)
    pygame.display.set_caption("Редактор карт WarStalker")

    # Создаём необходимые папки
    for dir_path in ["data/config", "data/maps", "data/maps/usermaps", "saves", "logs", "editor/logs"]:
        os.makedirs(dir_path, exist_ok=True)

    # Показываем стартовое меню
    menu = StartMenu(screen)
    choice, map_file = menu.run()

    if choice == 'quit':
        pygame.quit()
        sys.exit()

    # Загружаем конфиги
    loader = ConfigLoader()

    # Создаём контроллер с выбранной картой
    if choice == 'new':
        controller = EditorController(screen, loader, map_file=None)
    elif choice in ('user', 'builtin'):
        if map_file and os.path.exists(map_file):
            controller = EditorController(screen, loader, map_file=map_file)
        else:
            print("Файл не найден, создаём пустую карту")
            controller = EditorController(screen, loader, map_file=None)
    else:
        controller = EditorController(screen, loader, map_file=None)

    try:
        controller.run()
    except Exception as e:
        print("Критическая ошибка в редакторе:")
        traceback.print_exc()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    # Перенаправляем логи ошибок в editor/logs/
    error_log = "editor/logs/editor_error.log"
    try:
        main()
    except Exception as e:
        # Создаём папку, если её нет
        os.makedirs(os.path.dirname(error_log), exist_ok=True)
        with open(error_log, "w", encoding="utf-8") as f:
            f.write("Ошибка в редакторе карт:\n")
            f.write(traceback.format_exc())
        try:
            pygame.init()
            screen = pygame.display.set_mode((800, 200))
            pygame.display.set_caption("Ошибка редактора")
            font = pygame.font.Font(None, 24)
            lines = [
                "Произошла ошибка!",
                "Подробности записаны в файл: " + error_log,
                "Нажмите любую клавишу для выхода."
            ]
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                        pygame.quit()
                        sys.exit()
                screen.fill((40, 40, 40))
                y = 30
                for line in lines:
                    text = font.render(line, True, (255, 255, 255))
                    screen.blit(text, (20, y))
                    y += 30
                pygame.display.flip()
        except:
            print("Критическая ошибка в редакторе. Подробности в файле:", error_log)
            input("Нажмите Enter для выхода...")
        sys.exit(1)
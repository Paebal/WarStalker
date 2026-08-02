# split_tiles.py
# Разбивает большое изображение на тайлы 256x256

import os
from PIL import Image

def split_image(input_path, output_dir, tile_size=256):
    os.makedirs(output_dir, exist_ok=True)
    with Image.open(input_path) as img:
        width, height = img.size
        col = 0
        for x in range(0, width, tile_size):
            row = 0
            for y in range(0, height, tile_size):
                # Вырезаем тайл (не выходим за границы)
                box = (x, y, min(x + tile_size, width), min(y + tile_size, height))
                tile = img.crop(box)
                tile.save(os.path.join(output_dir, f"tile_{col}_{row}.png"))
                row += 1
            col += 1
    print(f"Тайлы сохранены в {output_dir}")

if __name__ == "__main__":
    split_image("assets/images/MAIN_MAP_V1.png", "assets/tiles", tile_size=256)
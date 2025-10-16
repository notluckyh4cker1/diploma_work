# Разбиение изображения на тайлы (части)

import numpy as np
from OpenGL.GL import *
from PyQt5.QtCore import QPointF
from collections import deque

class Tile:
    def __init__(self, x, y, width, height, texture_id, image_data=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.texture_id = texture_id
        self.image_data = image_data

class TileManager:
    def __init__(self):
        self.tiles = []
        self.tile_size = 1024
        self.min_tile_size = 2  # Минимальный размер тайла
        self.image_width = 0
        self.image_height = 0

    def split_into_tiles(self, image_data, img_width, img_height, progress_callback=None):
        self.tiles.clear()
        self.image_width = img_width
        self.image_height = img_height

        if len(image_data.shape) != 3 or image_data.shape[2] != 4:
            raise ValueError("Image data must be in RGBA format")

        total_tiles = ((img_height + self.tile_size - 1) // self.tile_size) * \
                      ((img_width + self.tile_size - 1) // self.tile_size)
        current_tile = 0

        for y in range(0, img_height, self.tile_size):
            for x in range(0, img_width, self.tile_size):
                tile_width = min(self.tile_size, img_width - x)
                tile_height = min(self.tile_size, img_height - y)

                tile_data = image_data[y:y + tile_height, x:x + tile_width].copy()

                texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, texture_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, tile_width, tile_height,
                             0, GL_RGBA, GL_UNSIGNED_BYTE, tile_data)

                self.tiles.append(Tile(x, y, tile_width, tile_height, texture_id, tile_data))

                current_tile += 1
                if progress_callback:
                    progress_callback(int((current_tile / total_tiles) * 100))

    def get_visible_tiles(self, viewport_width, viewport_height, pan, zoom, rotation_angle=0,
                          rotation_center=QPointF(0, 0)):
        visible_tiles = []

        # Рассчитываем расширенную область видимости с учетом поворота
        expanded_viewport = max(viewport_width, viewport_height) * 1.5

        for tile in self.tiles:
            # Центр тайла в мировых координатах
            tile_center_x = tile.x + tile.width / 2
            tile_center_y = tile.y + tile.height / 2

            # Преобразуем координаты с учетом поворота
            if rotation_angle != 0:
                # Смещаем в систему координат с центром в rotation_center
                dx = tile_center_x - rotation_center.x()
                dy = tile_center_y - rotation_center.y()

                # Поворачиваем
                import math
                angle_rad = math.radians(rotation_angle)
                cos_val = math.cos(angle_rad)
                sin_val = math.sin(angle_rad)
                rotated_dx = dx * cos_val - dy * sin_val
                rotated_dy = dx * sin_val + dy * cos_val

                # Возвращаем в мировые координаты
                tile_center_x = rotated_dx + rotation_center.x()
                tile_center_y = rotated_dy + rotation_center.y()

            # Проверяем, попадает ли тайл в расширенную область видимости
            tile_screen_x = tile_center_x * zoom + pan.x() - (tile.width * zoom) / 2
            tile_screen_y = tile_center_y * zoom + pan.y() - (tile.height * zoom) / 2
            tile_screen_width = tile.width * zoom
            tile_screen_height = tile.height * zoom

            if (tile_screen_x + tile_screen_width > -expanded_viewport and
                    tile_screen_y + tile_screen_height > -expanded_viewport and
                    tile_screen_x < viewport_width + expanded_viewport and
                    tile_screen_y < viewport_height + expanded_viewport):
                visible_tiles.append(tile)

        return visible_tiles

    def prepare_for_cut(self, line_pt1, line_pt2, progress_callback=None):
        """Подготовка к разрезу: дробим пересекающиеся тайлы"""
        new_tiles = []
        tiles_to_process = deque((tile, False) for tile in self.tiles)
        total = len(tiles_to_process)
        processed = 0

        while tiles_to_process:
            tile, checked = tiles_to_process.popleft()

            if not checked and self._tile_intersects_line(tile, line_pt1, line_pt2):
                if tile.width > self.min_tile_size and tile.height > self.min_tile_size:
                    half_w = tile.width // 2
                    half_h = tile.height // 2
                    sub_tiles = [
                        Tile(tile.x, tile.y, half_w, half_h, tile.texture_id, tile.image_data),
                        Tile(tile.x + half_w, tile.y, tile.width - half_w, half_h, tile.texture_id, tile.image_data),
                        Tile(tile.x, tile.y + half_h, half_w, tile.height - half_h, tile.texture_id, tile.image_data),
                        Tile(tile.x + half_w, tile.y + half_h, tile.width - half_w, tile.height - half_h,
                             tile.texture_id, tile.image_data)
                    ]
                    tiles_to_process.extendleft((t, False) for t in reversed(sub_tiles))
                    continue

            new_tiles.append(tile)
            processed += 1
            if progress_callback:
                progress_callback(int((processed / total) * 100))

        self.tiles = new_tiles

    def split_by_line(self, line_pt1, line_pt2):
        """Разделяет тайлы на две группы по линии разреза"""
        left_tiles = []
        right_tiles = []

        for tile in self.tiles:
            if self._is_tile_left_of_line(tile, line_pt1, line_pt2):
                left_tiles.append(tile)
            else:
                right_tiles.append(tile)

        return left_tiles, right_tiles

    def _is_tile_left_of_line(self, tile, line_pt1, line_pt2):
        """Определяет, находится ли тайл слева от линии разреза"""
        # Берем центр тайла для проверки
        center = QPointF(tile.x + tile.width / 2, tile.y + tile.height / 2)
        return ((line_pt2.x() - line_pt1.x()) * (center.y() - line_pt1.y()) -
                (line_pt2.y() - line_pt1.y()) * (center.x() - line_pt1.x())) > 0

    def _create_and_add_tile(self, image_data, x, y, width, height):
        tile_data = image_data[y:y + height, x:x + width]
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height,
                     0, GL_RGBA, GL_UNSIGNED_BYTE, tile_data)
        self.tiles.append(Tile(x, y, width, height, texture_id, tile_data.copy()))

    def _tile_intersects_line(self, tile, line_pt1, line_pt2):
        """Проверяет пересечение линии с тайлом"""
        tile_rect = [
            QPointF(tile.x, tile.y),
            QPointF(tile.x + tile.width, tile.y),
            QPointF(tile.x + tile.width, tile.y + tile.height),
            QPointF(tile.x, tile.y + tile.height)
        ]

        for i in range(4):
            if self._line_intersection(line_pt1, line_pt2,
                                       tile_rect[i], tile_rect[(i + 1) % 4]):
                return True
        return False

    def clear_textures(self):
        """Полная очистка текстур"""
        for tile in self.tiles:
            if tile.texture_id:
                glDeleteTextures([tile.texture_id])
                tile.texture_id = None
        self.tiles = []

    def _line_intersection(self, A, B, C, D):
        """Проверяет пересечение двух отрезков AB и CD"""

        def ccw(a, b, c):
            return (c.y() - a.y()) * (b.x() - a.x()) > (b.y() - a.y()) * (c.x() - a.x())

        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

    def get_combined_image(self):
        """Собирает изображение из всех тайлов"""
        if not self.tiles:
            return None

        width = max(tile.x + tile.width for tile in self.tiles)
        height = max(tile.y + tile.height for tile in self.tiles)
        combined = np.zeros((height, width, 4), dtype=np.uint8)

        for tile in self.tiles:
            if hasattr(tile, 'image_data') and tile.image_data is not None:
                combined[tile.y:tile.y + tile.height, tile.x:tile.x + tile.width] = tile.image_data

        return combined

    @staticmethod
    def from_image(pil_image):
        """Создает TileManager из изображения PIL"""
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        tile_manager = TileManager()
        img_array = np.array(pil_image)
        tile_manager.split_into_tiles(img_array, pil_image.width, pil_image.height)
        return tile_manager

    def is_empty(self):
        return len(self.tiles) == 0
# Класс данных растра

from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from PIL import Image, ImageFile
import numpy as np

# Увеличиваем лимит PIL для больших изображений
Image.MAX_IMAGE_PIXELS = None  # Снимаем ограничение
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Разрешаем загружать усеченные изображения


@dataclass
class SeismogramRaster:
    """Класс для хранения растрового изображения и его метаданных."""
    image_path: str
    pil_image: Optional[Image.Image] = None
    np_array: Optional[np.ndarray] = None  # Для OpenCV операций
    dpi: Tuple[int, int] = (300, 300)  # Разрешение сканирования (DPI)
    color_mode: str = "L"  # "L" (grayscale), "RGB", "1" (бинарное)
    metadata: dict = field(default_factory=dict)  # Доп. метаданные из файла

    # Добавляем параметры для обработки больших изображений
    tile_size: Tuple[int, int] = (2048, 2048)  # Размер тайлов
    use_tiling: bool = True  # Использовать тайлинг для больших изображений
    preview_scale: float = 0.1  # Масштаб превью для навигации

    def load(self, load_full_image: bool = False):
        """Загружает изображение с поддержкой больших файлов."""
        try:
            if self.use_tiling and not load_full_image:
                # Для больших изображений загружаем только метаданные
                with Image.open(self.image_path) as img:
                    self.pil_image = None  # Не храним полное изображение в памяти
                    self.metadata.update({
                        'size': img.size,
                        'mode': img.mode,
                        'format': img.format
                    })
                    print(f"Изображение {self.image_path}: {img.size[0]}x{img.size[1]}")
            else:
                # Загружаем полное изображение (для маленьких файлов)
                self.pil_image = Image.open(self.image_path)
                if self.pil_image.mode != self.color_mode:
                    self.pil_image = self.pil_image.convert(self.color_mode)

        except Exception as e:
            print(f"Ошибка загрузки изображения {self.image_path}: {e}")
            raise

    def get_tile(self, x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
        """
        Получает тайл (часть изображения) без загрузки всего файла в память.
        Оптимизированная версия для больших BMP файлов.
        """
        try:
            with Image.open(self.image_path) as img:
                # Получаем размеры изображения
                img_width, img_height = img.size

                # Проверяем координаты
                if x >= img_width or y >= img_height:
                    print(f"Координаты ({x},{y}) вне границ {img_width}x{img_height}")
                    return None

                # Корректируем координаты
                x = max(0, min(x, img_width - 1))
                y = max(0, min(y, img_height - 1))

                # Вычисляем реальный размер тайла
                actual_width = min(width, img_width - x)
                actual_height = min(height, img_height - y)

                if actual_width <= 0 or actual_height <= 0:
                    print(f"Нулевой размер тайла")
                    return None

                # Для BMP файлов используем оптимизированную загрузку
                if self.image_path.lower().endswith('.bmp'):
                    # BMP файлы могут быть большими, загружаем построчно
                    try:
                        # Обрезаем изображение
                        tile = img.crop((x, y, x + actual_width, y + actual_height))

                        # Оптимизация для grayscale BMP
                        if tile.mode == 'L' and actual_width * actual_height > 1000000:
                            # Конвертируем в массив numpy для ускорения
                            import numpy as np
                            tile_array = np.array(tile)
                            # Создаем новое изображение из массива
                            tile = Image.fromarray(tile_array)

                        return tile

                    except MemoryError as e:
                        # Пробуем загрузить уменьшенную версию
                        scale = 0.5
                        small_width = int(actual_width * scale)
                        small_height = int(actual_height * scale)
                        if small_width > 0 and small_height > 0:
                            tile = img.crop((x, y, x + actual_width, y + actual_height))
                            return tile.resize((small_width, small_height), Image.Resampling.LANCZOS)
                        return None
                else:
                    # Для других форматов обычная загрузка
                    return img.crop((x, y, x + actual_width, y + actual_height))

        except Exception as e:
            print(f"Ошибка получения тайла: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_preview(self, max_size: Tuple[int, int] = (1920, 1080)) -> Optional[Image.Image]:
        """
        Создает превью изображения для навигации.

        Args:
            max_size: Максимальный размер превью

        Returns:
            Image.Image: Уменьшенное превью
        """
        try:
            with Image.open(self.image_path) as img:
                # Вычисляем масштаб для уменьшения
                width, height = img.size
                scale_x = max_size[0] / width
                scale_y = max_size[1] / height
                scale = min(scale_x, scale_y, 1.0) * self.preview_scale

                # Уменьшаем изображение
                new_width = int(width * scale)
                new_height = int(height * scale)

                if scale < 1.0:
                    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    return img.copy()

        except Exception as e:
            print(f"Ошибка создания превью: {e}")
            return None

    def get_image_info(self) -> dict:
        """Возвращает информацию об изображении без загрузки в память."""
        try:
            with Image.open(self.image_path) as img:
                return {
                    'path': self.image_path,
                    'size': img.size,
                    'mode': img.mode,
                    'format': img.format,
                    'dpi': self.dpi,
                    'tile_size': self.tile_size,
                    'use_tiling': self.use_tiling
                }
        except Exception as e:
            print(f"Ошибка получения информации: {e}")
            return {}
# Менеджер для работы с растровыми изображениями с использованием OpenGL

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtOpenGL import QGLWidget, QGLFormat
from OpenGL.GL import *
from OpenGL.GLU import *
from typing import Tuple, Optional, List
import warnings

class RasterManager(QGLWidget):
    """Виджет OpenGL для отображения и обработки растровых изображений."""

    def __init__(self, parent=None):
        format = QGLFormat()
        format.setSampleBuffers(True)
        format.setSamples(4)  # 4x сглаживание
        super().__init__(format, parent)

        self.image_texture = None
        self.texture_width = 0
        self.texture_height = 0
        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.image_loaded = False

        # Настройки обработки изображения
        self.brightness = 1.0
        self.contrast = 1.0
        self.gamma = 1.0
        self.invert_colors = False
        self.threshold = 0
        self.threshold_enabled = False

    def initializeGL(self):
        """Инициализация OpenGL."""
        glClearColor(0.2, 0.2, 0.2, 1.0)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, width, height):
        """Обработка изменения размера виджета."""
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, width, 0, height)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        """Отрисовка сцены."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        if self.image_texture and self.image_loaded:
            # Применяем трансформации (масштабирование и панорамирование)
            glTranslatef(self.pan_x, self.pan_y, 0)
            glScalef(self.zoom_factor, self.zoom_factor, 1.0)

            # Рисуем текстуру
            glBindTexture(GL_TEXTURE_2D, self.image_texture)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1);
            glVertex2f(0, 0)
            glTexCoord2f(1, 1);
            glVertex2f(self.texture_width, 0)
            glTexCoord2f(1, 0);
            glVertex2f(self.texture_width, self.texture_height)
            glTexCoord2f(0, 0);
            glVertex2f(0, self.texture_height)
            glEnd()
            glBindTexture(GL_TEXTURE_2D, 0)

    def load_image(self, image_path: str):
        """Загружает изображение и создает текстуру."""
        try:
            # Загружаем изображение через PIL
            pil_image = Image.open(image_path)

            # Конвертируем в RGB/RGBA
            if pil_image.mode == 'L':  # Grayscale
                pil_image = pil_image.convert('RGB')
            elif pil_image.mode == 'P':  # Palette
                pil_image = pil_image.convert('RGB')
            elif pil_image.mode == '1':  # Binary
                pil_image = pil_image.convert('RGB')

            # Применяем обработку изображения
            pil_image = self._process_image(pil_image)

            # Конвертируем в данные для текстуры
            image_data = pil_image.tobytes("raw", "RGB", 0, -1)
            width, height = pil_image.size

            # Создаем текстуру OpenGL
            self.makeCurrent()

            if self.image_texture is None:
                self.image_texture = glGenTextures(1)

            glBindTexture(GL_TEXTURE_2D, self.image_texture)

            # Настройки текстуры
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            # Загружаем данные текстуры
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0,
                         GL_RGB, GL_UNSIGNED_BYTE, image_data)

            self.texture_width = width
            self.texture_height = height
            self.image_loaded = True

            # Сбрасываем трансформации
            self.zoom_factor = 1.0
            self.pan_x = 0.0
            self.pan_y = 0.0

            self.update()
            return True

        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return False

    def _process_image(self, pil_image: Image.Image) -> Image.Image:
        """Обрабатывает изображение с применением настроек."""
        image = pil_image.copy()

        # Яркость
        if self.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(self.brightness)

        # Контраст
        if self.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(self.contrast)

        # Гамма-коррекция
        if self.gamma != 1.0:
            # Гамма-коррекция вручную
            gamma_table = [int(255 * (i / 255) ** (1.0 / self.gamma))
                           for i in range(256)]
            if image.mode == 'RGB':
                # Применяем таблицу к каждому каналу
                r, g, b = image.split()
                r = r.point(gamma_table)
                g = g.point(gamma_table)
                b = b.point(gamma_table)
                image = Image.merge('RGB', (r, g, b))
            elif image.mode == 'L':
                image = image.point(gamma_table)

        # Инверсия цветов
        if self.invert_colors:
            if image.mode == 'RGB':
                r, g, b = image.split()
                r = Image.eval(r, lambda x: 255 - x)
                g = Image.eval(g, lambda x: 255 - x)
                b = Image.eval(b, lambda x: 255 - x)
                image = Image.merge('RGB', (r, g, b))
            elif image.mode == 'L':
                image = Image.eval(image, lambda x: 255 - x)

        # Пороговая обработка (бинаризация)
        if self.threshold_enabled and self.threshold > 0:
            if image.mode == 'RGB':
                image = image.convert('L')
            image = image.point(lambda x: 255 if x > self.threshold else 0)
            image = image.convert('RGB')

        return image

    def zoom_in(self, factor: float = 1.25):
        """Увеличивает масштаб."""
        self.zoom_factor *= factor
        self.update()

    def zoom_out(self, factor: float = 0.8):
        """Уменьшает масштаб."""
        self.zoom_factor *= factor
        self.update()

    def zoom_reset(self):
        """Сбрасывает масштаб."""
        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.update()

    def pan(self, dx: float, dy: float):
        """Панорамирует изображение."""
        self.pan_x += dx / self.zoom_factor
        self.pan_y += dy / self.zoom_factor
        self.update()

    def set_brightness(self, value: float):
        """Устанавливает яркость."""
        self.brightness = max(0.1, min(5.0, value))
        if self.image_loaded:
            self.reload_texture()

    def set_contrast(self, value: float):
        """Устанавливает контраст."""
        self.contrast = max(0.1, min(5.0, value))
        if self.image_loaded:
            self.reload_texture()

    def set_gamma(self, value: float):
        """Устанавливает гамму."""
        self.gamma = max(0.1, min(5.0, value))
        if self.image_loaded:
            self.reload_texture()

    def set_invert_colors(self, invert: bool):
        """Включает/выключает инверсию цветов."""
        self.invert_colors = invert
        if self.image_loaded:
            self.reload_texture()

    def set_threshold(self, threshold: int, enabled: bool = True):
        """Устанавливает порог бинаризации."""
        self.threshold = max(0, min(255, threshold))
        self.threshold_enabled = enabled
        if self.image_loaded:
            self.reload_texture()

    def reload_texture(self):
        """Перезагружает текстуру с текущими настройками обработки."""
        # Этот метод нужно вызывать, когда меняются настройки обработки
        # Для простоты перерисовываем текущую текстуру
        self.update()

    def wheelEvent(self, event):
        """Обработка колесика мыши для масштабирования."""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def mouseMoveEvent(self, event):
        """Обработка движения мыши для панорамирования."""
        if event.buttons() & Qt.LeftButton:
            dx = event.x() - self.last_mouse_x
            dy = event.y() - self.last_mouse_y
            self.pan(dx, -dy)  # Инвертируем dy для естественного поведения
        self.last_mouse_x = event.x()
        self.last_mouse_y = event.y()

    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши."""
        self.last_mouse_x = event.x()
        self.last_mouse_y = event.y()

    def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """Возвращает цвет пикселя в координатах изображения."""
        if not self.image_loaded:
            return (0, 0, 0)

        # Преобразуем координаты виджета в координаты текстуры
        tex_x = int((x - self.pan_x) / self.zoom_factor)
        tex_y = int((self.texture_height - (y - self.pan_y) / self.zoom_factor))

        # Читаем пиксель из текстуры (требует FBO для корректной работы)
        # Это упрощенная версия - в реальности нужно использовать FBO
        return (128, 128, 128)  # Заглушка
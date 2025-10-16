# Виджет OpenGL (масштабирование, перемещение)

import os
from PIL import Image, ImageDraw
from PyQt5.QtWidgets import QOpenGLWidget, QMessageBox
from PyQt5.QtCore import Qt, QPoint, QPointF, QSizeF, pyqtSignal, QRectF
from OpenGL.GL import *
from OpenGL.GLU import *
from image_loader import ImageLoader
from tile_manager import TileManager
import numpy as np

class RasterObject:
    def __init__(self, tile_manager, position=QPointF(0, 0), size=QSizeF(100, 100), file_path=""):
        self.tile_manager = tile_manager
        self.position = position
        self.size = size
        self.selected = False
        self.hovered = False
        self.is_active = False
        self.rotation_angle = 0
        self.rotation_center = QPointF(size.width() / 2, size.height() / 2)
        self.dpi = (600, 600)
        self.file_path = file_path  # Сохраняем путь к файлу
        self.scale_settings = ScaleSettings()  # Добавляем настройки шкалы

        self.cut_polygon = None
        self.cut_children = []  # Список вырезанных частей
        self.cut_parent = None  # Ссылка на родительский растр
        self.cut_group_id = None  # Идентификатор группы разрезанных частей

    def get_physical_size_mm(self): # Просто для вывода размеров изображения
        return QSizeF(
            self.size.width() * 25.4 / self.dpi[0],
            self.size.height() * 25.4 / self.dpi[1]
        )

    def contains_point(self, point):
        # Проверка попадания точки с учетом поворота
        local_x = point.x() - self.position.x()
        local_y = point.y() - self.position.y()

        dx = local_x - self.rotation_center.x()
        dy = local_y - self.rotation_center.y()

        angle_rad = -np.radians(self.rotation_angle)
        cos_val = np.cos(angle_rad)
        sin_val = np.sin(angle_rad)

        rotated_x = dx * cos_val - dy * sin_val + self.rotation_center.x()
        rotated_y = dx * sin_val + dy * cos_val + self.rotation_center.y()

        return (0 <= rotated_x <= self.size.width() and 0 <= rotated_y <= self.size.height())

    def is_on_border(self, point, threshold=5):
        """Проверяет, находится ли точка на границе растра"""
        x, y = point.x(), point.y()
        width, height = self.size.width(), self.size.height()

        return (abs(x) < threshold or
                abs(y) < threshold or
                abs(x - width) < threshold or
                abs(y - height) < threshold)

    def get_border_rect(self):
        """Возвращает координаты границы в виде QRectF"""
        return QRectF(self.position, self.size)

    def snap_to_border(self, point, corner_threshold=15, edge_threshold=10):
        """Примагничивает точку с приоритетом углов"""
        x, y = point.x(), point.y()
        width, height = self.size.width(), self.size.height()

        # Сначала проверяем углы (они имеют приоритет)
        corners = [
            (0, 0),  # Левый верхний
            (width, 0),  # Правый верхний
            (width, height),  # Правый нижний
            (0, height)  # Левый нижний
        ]

        # Находим ближайший угол
        nearest_corner = None
        min_corner_dist = float('inf')

        for corner_x, corner_y in corners:
            dist = (x - corner_x) ** 2 + (y - corner_y) ** 2  # Квадрат расстояния
            if dist < min_corner_dist:
                min_corner_dist = dist
                nearest_corner = QPointF(corner_x, corner_y)

        # Если близко к углу (в пределах corner_threshold)
        if min_corner_dist <= corner_threshold ** 2:
            return nearest_corner

        # Если не близко к углу, проверяем границы
        left_dist = abs(x)
        right_dist = abs(x - width)
        top_dist = abs(y)
        bottom_dist = abs(y - height)

        min_edge_dist = min(left_dist, right_dist, top_dist, bottom_dist)

        if min_edge_dist > edge_threshold:
            return point  # Не примагничиваем если далеко от границ

        # Примагничиваем к ближайшей границе
        if min_edge_dist == left_dist:
            return QPointF(0, y)
        elif min_edge_dist == right_dist:
            return QPointF(width, y)
        elif min_edge_dist == top_dist:
            return QPointF(x, 0)
        else:
            return QPointF(x, height)

    @staticmethod
    def _convert_to_image_coords(scene_point, raster_object):
        """Преобразует координаты сцены в координаты изображения с учетом поворота и положения"""
        # Переводим в локальные координаты объекта (относительно его позиции)
        local_x = scene_point.x() - raster_object.position.x()
        local_y = scene_point.y() - raster_object.position.y()

        # Учитываем поворот (обратное преобразование)
        angle_rad = np.radians(-raster_object.rotation_angle)  # Обратный поворот
        cos_val = np.cos(angle_rad)
        sin_val = np.sin(angle_rad)

        # Центр вращения в локальных координатах
        center_x = raster_object.rotation_center.x()
        center_y = raster_object.rotation_center.y()

        # Переносим в систему координат с центром в точке вращения
        dx = local_x - center_x
        dy = local_y - center_y

        # Применяем обратное вращение
        rotated_x = dx * cos_val - dy * sin_val
        rotated_y = dx * sin_val + dy * cos_val

        # Возвращаем в систему координат изображения
        return QPointF(rotated_x + center_x, rotated_y + center_y)

    @staticmethod
    def _raster_object_to_image(raster_object):
        """Конвертирует RasterObject в PIL Image"""
        if not raster_object or not raster_object.tile_manager:
            return None

        # Собираем все тайлы в одно изображение
        full_img = Image.new('RGBA',
                             (int(raster_object.size.width()),
                              int(raster_object.size.height())))

        for tile in raster_object.tile_manager.tiles:
            if hasattr(tile, 'image_data') and tile.image_data is not None:
                tile_img = Image.fromarray(tile.image_data)
                if tile_img.mode != 'RGBA':
                    tile_img = tile_img.convert('RGBA')
                full_img.paste(tile_img, (int(tile.x), int(tile.y)))

        return full_img

    @staticmethod
    def _trim_transparent(img):
        """Обрезает прозрачные края у изображения"""
        bbox = img.getbbox()
        if bbox:
            return img.crop(bbox)
        return img

    def _line_intersection(self, line1_start, line1_end, line2_start, line2_end):
        """Находит точку пересечения двух линий (более надежная версия)"""
        x1, y1 = line1_start.x(), line1_start.y()
        x2, y2 = line1_end.x(), line1_end.y()
        x3, y3 = line2_start.x(), line2_start.y()
        x4, y4 = line2_end.x(), line2_end.y()

        # Параметры уравнений линий
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:  # Линии параллельны
            return None

        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

        # Если пересечение в пределах обоих отрезков
        if 0 <= ua <= 1 and 0 <= ub <= 1:
            x = x1 + ua * (x2 - x1)
            y = y1 + ua * (y2 - y1)
            return QPointF(x, y)

        return None

class ScaleSettings:
    def __init__(self):
        self.time_visible = False
        self.amplitude_visible = False
        self.time_min = 0.0
        self.time_max = 60.0
        self.time_step = 10.0
        self.amplitude_min = 0.0
        self.amplitude_max = 5.0
        self.amplitude_step = 0.5
        self.color = (1.0, 0.0, 0.0, 1.0)
        self.line_width = 1.0

class VectorCurve:
    def __init__(self, raster_object, color=(0.0, 1.0, 0.0, 1.0), line_width=2.0):
        self.points = []  # Точки кривой в локальных координатах растра
        self.raster_object = raster_object  # Ссылка на растровый объект
        self.color = color
        self.line_width = line_width
        self.completed = False  # Завершена ли кривая

class CuttingPolygon:
    def __init__(self):
        self.points = []  # Точки полигона
        self.active = False
        self.closed = False
        self.max_points = 4  # Максимум 4 точки для прямоугольного выделения

    def add_point(self, point, raster_object):
        """Добавляет точку в локальных координатах растра"""
        if not self.closed and len(self.points) < self.max_points:
            # Проверяем, что точка на границе (уже в локальных координатах)
            border_width = 5  # Допуск для границы в пикселях
            x, y = point.x(), point.y()
            width, height = raster_object.size.width(), raster_object.size.height()

            on_border = (
                    abs(x) < border_width or
                    abs(y) < border_width or
                    abs(x - width) < border_width or
                    abs(y - height) < border_width
            )

            if on_border:
                self.points.append(point)
                if len(self.points) >= 4 and self._check_closure():
                    self.closed = True
                return True
        return False

    def reset(self):
        self.points = []
        self.active = False
        self.closed = False

    def _check_closure(self):
        """Проверяет, нужно ли замкнуть полигон"""
        if len(self.points) < 4:
            return False
        return len(self.points) == 4 and (
                (self.points[-1] - self.points[0]).manhattanLength() < 15
        )

    def get_lines(self):
        """Возвращает линии для отрисовки"""
        lines = []
        for i in range(1, len(self.points)):
            lines.append((self.points[i-1], self.points[i]))
        if self.closed:
            lines.append((self.points[-1], self.points[0]))
        return lines

class SelectionArea:
    def __init__(self):
        self.start_point = None
        self.end_point = None
        self.active = False

    def set_start(self, point):
        self.start_point = point
        self.active = True

    def set_end(self, point):
        self.end_point = point

    def reset(self):
        self.start_point = None
        self.end_point = None
        self.active = False

    def rect(self):
        if not self.start_point or not self.end_point:
            return None
        return QRectF(self.start_point, self.end_point).normalized()

    def contains(self, point):
        rect = self.rect()
        return rect.contains(point) if rect else False

class GLWidget(QOpenGLWidget):
    objectActivated = pyqtSignal(bool)
    curvesChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_loader = ImageLoader()
        self.tile_manager = TileManager()
        self.raster_objects = []
        self.active_object = None
        self.hovered_object = None

        # Режим: True — движение сцены, False — работа с растром (перемещение/вращение)
        self.mode_move = True

        self.zoom = 1.0
        self.pan = QPoint(0, 0)
        self.last_pos = QPoint(0, 0)
        self.dragging = False
        self.selection_mode = False

        self.setMouseTracking(True)

        self.vectorization_mode = False
        self.current_curve = None
        self.curves = []  # Все кривые
        self.current_color_index = 0
        self.current_color = (1.0, 0.0, 0.0, 1.0)  # Красный по умолчанию

        self.hovered_scale_line = None  # Какая линия шкалы под курсором
        self.dragging_scale_line = None  # Какую линию шкалы перемещаем
        self.scale_line_tooltip = ""  # Текст подсказки для линии

        self.cut_mode = False
        self.cutting_polygon = CuttingPolygon()
        self.selection_area = SelectionArea()
        self.border_hovered = False
        self.border_color = (0, 1, 0)  # Зеленый цвет подсветки
        self.cut_point_color = (0.4, 0.8, 1.0)  # Голубой цвет
        self.last_snapped_pos = QPointF(0, 0)

    def start_vectorization(self):
        try:
            if not self.active_object:
                return False

            self.vectorization_mode = True
            if not hasattr(self, 'curves'):
                self.curves = []
            self.current_curve = VectorCurve(self.active_object, self.current_color)
            self.setCursor(Qt.CrossCursor)
            self.update()
            return True
        except Exception as e:
            print(f"Ошибка! Не удалось начать векторизацию: {str(e)}")
            return False

    def finish_vectorization(self):
        """Завершение режима векторизации с очисткой"""
        try:
            # Завершаем текущую кривую, если она есть
            if hasattr(self, 'current_curve') and self.current_curve:
                if len(self.current_curve.points) >= 2:
                    self.finish_current_curve()
                self.current_curve = None

            self.vectorization_mode = False
            self.setCursor(Qt.ArrowCursor)
            self.update()
            return True

        except Exception as e:
            print(f"Ошибка завершения векторизации: {str(e)}")
            self.vectorization_mode = False
            return False

    def finish_current_curve(self):
        if not self.current_curve or len(self.current_curve.points) < 2:
            return False

        completed_curve = VectorCurve(
            self.current_curve.raster_object,
            self.current_curve.color,
            self.current_curve.line_width
        )
        completed_curve.points = self.current_curve.points.copy()
        completed_curve.completed = True

        if not hasattr(self, 'curves'):
            self.curves = []
        self.curves.append(completed_curve)
        self.current_curve = None

        # Уведомляем об изменении
        if hasattr(self.parent(), 'curves_changed'):
            self.parent().curves_changed(True)

        self._notify_curves_changed()
        self.update()
        return True

    def clear_last_curve(self):
        """Удаляет последнюю кривую без лишних проверок"""
        try:
            if not self.curves:  # Простая проверка на пустоту
                return True  # Успех, даже если нечего удалять

            self.curves.pop()
            self._notify_curves_changed()
            self.update()
            return True
        except Exception as e:
            print(f"Реальная ошибка при удалении: {e}")
            return False

    def clear_all_curves(self):
        """Очищает все кривые гарантированно"""
        try:
            self.curves = []
            self.current_curve = None
            self._notify_curves_changed()
            self.update()
            return True
        except Exception as e:
            print(f"Реальная ошибка при очистке: {e}")
            return False

    def _scene_to_raster_local(self, scene_point, raster_object):
        """Преобразует глобальные координаты сцены в локальные координаты растра с учетом поворота"""
        # Сначала вычитаем позицию растра
        local_x = scene_point.x() - raster_object.position.x()
        local_y = scene_point.y() - raster_object.position.y()

        # Затем учитываем поворот
        dx = local_x - raster_object.rotation_center.x()
        dy = local_y - raster_object.rotation_center.y()

        angle_rad = -np.radians(raster_object.rotation_angle)
        cos_val = np.cos(angle_rad)
        sin_val = np.sin(angle_rad)

        rotated_x = dx * cos_val - dy * sin_val + raster_object.rotation_center.x()
        rotated_y = dx * sin_val + dy * cos_val + raster_object.rotation_center.y()

        return QPointF(rotated_x, rotated_y)

    def set_mode_move(self, enabled: bool):
        self.mode_move = enabled
        self.vectorization_mode = False  # Выходим из режима векторизации
        self.setCursor(Qt.ArrowCursor)
        if enabled:
            if self.active_object:
                self.active_object.is_active = False
                self.active_object = None
                self.objectActivated.emit(False)
            self.selection_mode = False
            self.hovered_object = None
        else:
            self.selection_mode = True
            # self.center_camera_on_raster() - оставляем там, где пользователь изволит
        self.update()

    def set_selection_enabled(self, enabled: bool):
        self.selection_mode = enabled
        if not enabled:
            self.hovered_object = None
            if self.active_object:
                self.active_object.is_active = False
                self.active_object = None
                self.objectActivated.emit(False)
        self.update()

    def set_cut_mode(self, enabled):
        """Установка режима резки с защитой от ошибок"""
        try:
            # При выходе из режима или повторном входе сбрасываем полигон
            if self.cut_mode or not enabled:
                self.cutting_polygon.reset()

            self.cut_mode = enabled
            if enabled:
                self.selection_mode = True
                if hasattr(self, 'parent') and self.parent():
                    self.parent().show_cut_instruction("Дважды кликните по растру для выбора")
            else:
                if hasattr(self, 'active_object') and self.active_object:
                    self.active_object.is_active = False
                    self.active_object = None
                    if hasattr(self, 'objectActivated'):
                        self.objectActivated.emit(False)

            self.update()
        except Exception as e:
            print(f"Error in set_cut_mode: {str(e)}")

    def _finalize_cutting(self):
        if not self.active_object or len(self.cutting_polygon.points) != 5:
            return

        try:
            # 1. Получаем оригинальное изображение
            full_img = RasterObject._raster_object_to_image(self.active_object)
            if full_img.mode != 'RGBA':
                full_img = full_img.convert('RGBA')

            # 2. Создаем маску (белая - сохранить, черная - удалить)
            mask = Image.new('L', full_img.size, 255)  # Начинаем с полностью белой маски
            draw = ImageDraw.Draw(mask)

            # Преобразуем точки полигона в кортежи (x,y)
            polygon_points = [(p.x(), p.y()) for p in self.cutting_polygon.points]

            # Закрашиваем область вырезания черным (0)
            draw.polygon(polygon_points, fill=0)

            # 3. Применяем маску к оригинальному изображению
            # Создаем копию изображения с альфа-каналом
            result_img = full_img.copy()

            # Обновляем только альфа-канал (прозрачность)
            r, g, b, a = result_img.split()
            a = Image.fromarray(np.array(mask))
            result_img = Image.merge("RGBA", (r, g, b, a))

            # 4. Обрезаем прозрачные края
            result_img = RasterObject._trim_transparent(result_img)

            # 5. Обновляем основной объект
            self.active_object.tile_manager = TileManager.from_image(result_img)
            self.active_object.size = QSizeF(result_img.width, result_img.height)
            self.active_object.cut_polygon = None

            self.cutting_polygon.reset()
            self.update()

            QMessageBox.information(self, "Обрезка готова", "Вырезанная часть удалена. Исходный растр обновлен.")

        except Exception as e:
            print(f"Ошибка при вырезании: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось вырезать область:\n{str(e)}")

    def add_image(self, file_path, progress_callback=None):
        try:
            # Проверка существования файла
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Файл не найден: {file_path}")

            # Загрузка с автоматическим приведением к 600 DPI
            new_loader = ImageLoader()
            new_loader.load(file_path, target_dpi=600)

            # Создание тайлов с обработкой прогресса
            new_tile_manager = TileManager()
            new_tile_manager.split_into_tiles(
                new_loader.image_data,
                new_loader.width,
                new_loader.height,
                progress_callback
            )

            # Позиционирование нового изображения со смещением
            new_pos = QPointF(0, 0)
            if self.raster_objects:
                last_obj = self.raster_objects[-1]
                new_pos = QPointF(
                    last_obj.position.x() + 20 / self.zoom,
                    last_obj.position.y() + 20 / self.zoom
                )

            # Создание объекта растра с сохранением пути к файлу
            obj = RasterObject(
                new_tile_manager,
                new_pos,
                QSizeF(new_loader.width, new_loader.height),
                file_path  # Добавляем путь к файлу
            )
            obj.rotation_center = QPointF(new_loader.width / 2, new_loader.height / 2)
            obj.dpi = (600, 600)

            self.raster_objects.append(obj)

            # Центрирование камеры для первого изображения
            if len(self.raster_objects) == 1:
                self.center_camera_on_raster()

            self.update()
            return True

        except Exception as e:
            print(f"Ошибка при добавлении изображения: {str(e)}")
            return False

    def load_image(self, file_path, progress_callback=None):
        try:
            # Проверка существования файла
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Файл не найден: {file_path}")

            self.clear_rasters()

            # Загрузка изображения
            self.image_loader = ImageLoader()
            self.image_loader.load(file_path, target_dpi=600)

            # Создание тайлов
            self.tile_manager = TileManager()
            self.tile_manager.split_into_tiles(
                self.image_loader.image_data,
                self.image_loader.width,
                self.image_loader.height,
                progress_callback
            )

            # Создание основного объекта растра
            obj = RasterObject(
                self.tile_manager,
                QPointF(0, 0),
                QSizeF(self.image_loader.width, self.image_loader.height),
                file_path  # Добавляем путь к файлу
            )
            obj.rotation_center = QPointF(self.image_loader.width / 2, self.image_loader.height / 2)
            obj.dpi = (600, 600)

            self.raster_objects.append(obj)
            self.center_camera_on_raster()
            self.update()

            return True  # Указываем на успешную загрузку

        except Exception as e:
            print(f"Ошибка при загрузке изображения: {str(e)}")
            raise  # Пробрасываем исключение для обработки в MainWindow

    def clear_rasters(self):
        self.raster_objects = []
        self.active_object = None
        self.hovered_object = None
        self.update()

    def rotate(self, angle):
        if self.active_object and not self.mode_move:
            self.active_object.rotation_angle = (self.active_object.rotation_angle + angle) % 360
            self.update()

    def initializeGL(self):
        glClearColor(0.2, 0.2, 0.2, 1.0)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, w, h, 0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def paintGL(self):
        if not self.raster_objects:
            return
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.width(), self.height(), 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glTranslatef(self.pan.x(), self.pan.y(), 0)
        glScalef(self.zoom, self.zoom, 1.0)

        for obj in self.raster_objects:
            glPushMatrix()

            glTranslatef(obj.position.x(), obj.position.y(), 0)
            glTranslatef(obj.rotation_center.x(), obj.rotation_center.y(), 0)
            glRotatef(obj.rotation_angle, 0, 0, 1)
            glTranslatef(-obj.rotation_center.x(), -obj.rotation_center.y(), 0)

            if obj.tile_manager and not obj.tile_manager.is_empty():
                for tile in obj.tile_manager.tiles:
                    # Светлее, если наведён и в режиме работы с растром
                    if not self.mode_move:
                        if obj == self.active_object:
                            glColor4f(0.65, 0.65, 0.65, 1.0)  # Тёмнее — активный растр
                        elif obj == self.hovered_object:
                            glColor4f(1.0, 1.0, 1.0, 0.7)  # Полупрозрачный при наведении
                        else:
                            glColor4f(1.0, 1.0, 1.0, 1.0)
                    else:
                        glColor4f(1.0, 1.0, 1.0, 1.0)

                    if not tile.texture_id:
                        continue
                    glBindTexture(GL_TEXTURE_2D, tile.texture_id)
                    glBegin(GL_QUADS)
                    glTexCoord2f(0, 0)
                    glVertex2f(tile.x, tile.y)
                    glTexCoord2f(1, 0)
                    glVertex2f(tile.x + tile.width, tile.y)
                    glTexCoord2f(1, 1)
                    glVertex2f(tile.x + tile.width, tile.y + tile.height)
                    glTexCoord2f(0, 1)
                    glVertex2f(tile.x, tile.y + tile.height)
                    glEnd()

            glPopMatrix()
            # Отрисовка шкал поверх изображения
            self.draw_scales(obj)

        # Отрисовка кривых векторизации
        glDisable(GL_TEXTURE_2D)
        for curve in self.curves:
            self._draw_curve(curve)

        if self.current_curve and len(self.current_curve.points) > 0:
            self._draw_curve(self.current_curve)
        glEnable(GL_TEXTURE_2D)

        # Отрисовка полигона выделения
        if self.cutting_polygon.active and self.active_object:
            glPushMatrix()
            glTranslatef(self.active_object.position.x(), self.active_object.position.y(), 0)
            glTranslatef(self.active_object.rotation_center.x(), self.active_object.rotation_center.y(), 0)
            glRotatef(self.active_object.rotation_angle, 0, 0, 1)
            glTranslatef(-self.active_object.rotation_center.x(), -self.active_object.rotation_center.y(), 0)

            glDisable(GL_TEXTURE_2D)

            if len(self.cutting_polygon.points) > 1:
                glColor3f(0.2, 0.6, 1.0)
                glLineWidth(2.0)
                glBegin(GL_LINE_STRIP)
                for point in self.cutting_polygon.points:
                    glVertex2f(point.x(), point.y())
                glEnd()

            glPointSize(10.0)
            glBegin(GL_POINTS)
            for i, point in enumerate(self.cutting_polygon.points):
                if i == 0:
                    glColor3f(0, 1, 0)
                else:
                    glColor3f(0.2, 0.6, 1.0)
                glVertex2f(point.x(), point.y())
            glEnd()

            if not self.cutting_polygon.closed and len(self.cutting_polygon.points) > 0:
                glColor3f(1, 1, 0)
                glLineWidth(1.0)
                glBegin(GL_LINES)
                glVertex2f(self.cutting_polygon.points[-1].x(), self.cutting_polygon.points[-1].y())
                glVertex2f(self.last_snapped_pos.x(), self.last_snapped_pos.y())
                glEnd()

            glEnable(GL_TEXTURE_2D)
            glPopMatrix()

    def _draw_curve(self, curve):
        if not curve or not hasattr(curve, 'points') or not curve.raster_object:
            return

        try:
            # Проверяем корректность цвета
            color = getattr(curve, 'color', (1.0, 0.0, 0.0, 1.0))
            if not isinstance(color, (tuple, list)) or len(color) != 4:
                color = (1.0, 0.0, 0.0, 1.0)

            glColor4f(*color)
            glLineWidth(getattr(curve, 'line_width', 2.0))

            glPushMatrix()
            # Применяем преобразования растра
            glTranslatef(curve.raster_object.position.x(), curve.raster_object.position.y(), 0)
            glTranslatef(curve.raster_object.rotation_center.x(), curve.raster_object.rotation_center.y(), 0)
            glRotatef(curve.raster_object.rotation_angle, 0, 0, 1)
            glTranslatef(-curve.raster_object.rotation_center.x(), -curve.raster_object.rotation_center.y(), 0)

            # Рисуем линии
            if len(curve.points) > 1:
                glBegin(GL_LINE_STRIP)
                for point in curve.points:
                    if isinstance(point, QPointF):
                        glVertex2f(point.x(), point.y())
                glEnd()

            # Рисуем точки
            glPointSize(5.0)
            glBegin(GL_POINTS)
            for point in curve.points:
                if isinstance(point, QPointF):
                    glVertex2f(point.x(), point.y())
            glEnd()

            glPopMatrix()
        except Exception as e:
            print(f"Ошибка отрисовки кривой: {str(e)}")

    def draw_scales(self, obj):
        if not obj.scale_settings.time_visible and not obj.scale_settings.amplitude_visible:
            return

        glPushMatrix()
        glTranslatef(obj.position.x(), obj.position.y(), 0)
        glTranslatef(obj.rotation_center.x(), obj.rotation_center.y(), 0)
        glRotatef(obj.rotation_angle, 0, 0, 1)
        glTranslatef(-obj.rotation_center.x(), -obj.rotation_center.y(), 0)

        # Устанавливаем параметры линий
        glColor4f(*obj.scale_settings.color)
        glLineWidth(obj.scale_settings.line_width)

        # ВРЕМЕННАЯ ШКАЛА (горизонтальные линии)
        if obj.scale_settings.time_visible and obj.scale_settings.time_max > obj.scale_settings.time_min:
            time_range = obj.scale_settings.time_max - obj.scale_settings.time_min
            pixels_per_second = obj.size.height() / time_range

            # Рассчитываем видимый диапазон времени
            visible_time_min = max(obj.scale_settings.time_min, 0)
            visible_time_max = min(obj.scale_settings.time_max,
                                   obj.scale_settings.time_min + obj.size.height() / pixels_per_second)

            # Находим первый и последний шаг, попадающий в видимый диапазон
            first_step = int(np.ceil((visible_time_min - obj.scale_settings.time_min) / obj.scale_settings.time_step))
            last_step = int(np.floor((visible_time_max - obj.scale_settings.time_min) / obj.scale_settings.time_step))

            # Рисуем только видимые линии
            for i in range(first_step, last_step + 1):
                time = obj.scale_settings.time_min + i * obj.scale_settings.time_step
                y = (time - obj.scale_settings.time_min) * pixels_per_second
                if 0 <= y <= obj.size.height():
                    glBegin(GL_LINES)
                    glVertex2f(0, y)
                    glVertex2f(obj.size.width(), y)
                    glEnd()

        # ШКАЛА АМПЛИТУД (вертикальные линии)
        if obj.scale_settings.amplitude_visible and obj.scale_settings.amplitude_max > obj.scale_settings.amplitude_min:
            amp_range = obj.scale_settings.amplitude_max - obj.scale_settings.amplitude_min
            pixels_per_unit = obj.size.width() / amp_range

            # Рассчитываем видимый диапазон амплитуд
            visible_amp_min = max(obj.scale_settings.amplitude_min, 0)
            visible_amp_max = min(obj.scale_settings.amplitude_max,
                                  obj.scale_settings.amplitude_min + obj.size.width() / pixels_per_unit)

            # Находим первый и последний шаг, попадающий в видимый диапазон
            first_step = int(
                np.ceil((visible_amp_min - obj.scale_settings.amplitude_min) / obj.scale_settings.amplitude_step))
            last_step = int(
                np.floor((visible_amp_max - obj.scale_settings.amplitude_min) / obj.scale_settings.amplitude_step))

            # Рисуем только видимые линии
            for i in range(first_step, last_step + 1):
                amp = obj.scale_settings.amplitude_min + i * obj.scale_settings.amplitude_step
                x = (amp - obj.scale_settings.amplitude_min) * pixels_per_unit
                if 0 <= x <= obj.size.width():
                    glBegin(GL_LINES)
                    glVertex2f(x, 0)
                    glVertex2f(x, obj.size.height())
                    glEnd()

        glPopMatrix()

    def _notify_curves_changed(self):
        """Уведомляет об изменении состояния кривых"""
        has_curves = (hasattr(self, 'curves') and bool(self.curves)) or \
                     (hasattr(self, 'current_curve') and self.current_curve and len(self.current_curve.points) > 0)
        self.curvesChanged.emit(has_curves)

    def save_curves_to_file(self, file_path):
        """Сохраняет кривые с проверкой формата точек"""
        if not hasattr(self, 'curves') or not self.curves:
            return False

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Информация о растре
                if self.raster_objects:
                    obj = self.raster_objects[0]
                    f.write("[raster]\n")
                    f.write(f"file_path={os.path.basename(obj.file_path)}\n")
                    f.write(f"width={obj.size.width()}\n")
                    f.write(f"height={obj.size.height()}\n\n")

                # Сохраняем каждую кривую, удаляя дубликаты точек
                for i, curve in enumerate(self.curves):
                    if not curve.points:  # Пропускаем пустые кривые
                        continue

                    f.write(f"[curve_{i}]\n")
                    f.write(f"color={','.join(map(str, curve.color))}\n")
                    f.write(f"width={curve.line_width}\n")

                    # Удаляем дубликаты соседних точек
                    unique_points = []
                    prev_point = None
                    for point in curve.points:
                        if prev_point is None or (point.x() != prev_point.x() or point.y() != prev_point.y()):
                            unique_points.append(point)
                            prev_point = point

                    # Сохраняем только уникальные точки
                    points_str = []
                    for point in unique_points:
                        if hasattr(point, 'x') and hasattr(point, 'y'):
                            points_str.append(f"{point.x():.2f},{point.y():.2f}")
                        elif isinstance(point, (tuple, list)) and len(point) >= 2:
                            points_str.append(f"{point[0]:.2f},{point[1]:.2f}")

                    f.write(f"points={';'.join(points_str)}\n\n")

            return True
        except Exception as e:
            print(f"Ошибка сохранения: {str(e)}")
            return False

    def load_curves_from_file(self, file_path):
        """Загружает кривые из файла с проверкой соответствия файла растра"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Проверяем, есть ли активный растр
            if not self.active_object:
                raise ValueError("Нет активного растрового объекта")

            # Разбираем информацию о растре из файла
            raster_section = content.split('[raster]')[1].split('[curve]')[0]
            raster_info = {}
            for line in raster_section.split('\n'):
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    raster_info[key] = value

            # Проверяем соответствие файлов
            saved_filename = raster_info.get('file_path', '')
            current_filename = os.path.basename(self.active_object.file_path)

            if saved_filename != current_filename:
                raise ValueError(
                    f"Файл кривых не соответствует текущему растру.\n"
                    f"Сохранено для: {saved_filename}\n"
                    f"Текущий растр: {current_filename}"
                )

            # Очищаем текущие кривые
            self.curves = []

            # Загружаем кривые из файла
            curve_sections = [s for s in content.split('[curve_') if s.strip()]  # Все секции кривых
            for section in curve_sections[1:]:  # Пропускаем первый элемент (он может быть пустым)
                try:
                    # Разбираем параметры кривой
                    header_end = section.find(']')
                    curve_data = {}
                    lines = section[header_end + 1:].split('\n')

                    for line in lines:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            curve_data[key.strip()] = value.strip()

                    # Создаем новую кривую
                    color = tuple(map(float, curve_data.get('color', '1.0,0.0,0.0,1.0').split(',')))
                    width = float(curve_data.get('width', '2.0'))
                    curve = VectorCurve(self.active_object, color, width)

                    # Загружаем точки
                    points_str = curve_data.get('points', '')
                    if points_str:
                        for pair in points_str.split(';'):
                            if ',' in pair:
                                try:
                                    x, y = map(float, pair.split(','))
                                    # Добавляем точку в локальных координатах растра
                                    curve.points.append(QPointF(x, y))
                                except ValueError:
                                    continue

                    if len(curve.points) >= 2:  # Добавляем только кривые с достаточным количеством точек
                        curve.completed = True
                        self.curves.append(curve)

                except Exception as e:
                    print(f"Ошибка загрузки кривой: {str(e)}")
                    continue

            # Убедимся, что кривые есть перед обновлением
            if self.curves:
                self._notify_curves_changed()
                self.update()
                return True
            else:
                raise ValueError("Не удалось загрузить ни одной кривой")

        except Exception as e:
            print(f"Ошибка загрузки кривых: {str(e)}")
            raise

    def mouseDoubleClickEvent(self, event):
        if not self.mode_move and self.selection_mode and event.button() == Qt.LeftButton:
            scene_pos = self.map_to_scene(event.pos())
            for obj in reversed(self.raster_objects):
                if obj.contains_point(scene_pos):
                    if self.active_object:
                        self.active_object.is_active = False
                    self.active_object = obj
                    obj.is_active = True
                    self.objectActivated.emit(True)
                    self.update()
                    break
            else:
                # Если ни один объект не выбран, деактивируем текущий
                if self.active_object:
                    self.active_object.is_active = False
                    self.active_object = None
                    self.objectActivated.emit(False)
                    self.update()

        if self.vectorization_mode and event.button() == Qt.LeftButton:
            self.finish_current_curve()
        else:
            super().mouseDoubleClickEvent(event)

        if not self.cut_mode or event.button() != Qt.LeftButton:
            return super().mouseDoubleClickEvent(event)

        scene_pos = self.map_to_scene(event.pos())

        # Если нет активного объекта - пытаемся выбрать
        if not self.active_object:
            for obj in reversed(self.raster_objects):
                if obj.contains_point(scene_pos):
                    self.active_object = obj
                    break
            else:
                return  # Не нашли подходящий растр - ничего не делаем

        # Преобразуем координаты в локальные для активного растра
        local_pos = RasterObject._convert_to_image_coords(scene_pos, self.active_object)

        # Проверяем, что точка на границе (с небольшим допуском)
        if not self.active_object.is_on_border(local_pos, threshold=15):
            return  # Клик не на границе - игнорируем, но активный растр остается

        # Примагничиваем точку к границе
        snapped_pos = self.active_object.snap_to_border(local_pos)

        # Логика добавления точек
        if not self.cutting_polygon.active:
            # Начало нового полигона
            self.cutting_polygon.active = True
            self.cutting_polygon.points = [snapped_pos]
            self.parent().show_cut_instruction("Поставьте вторую точку на границе")
        else:
            # Проверка замыкания полигона
            if len(self.cutting_polygon.points) >= 1 and \
                    (snapped_pos - self.cutting_polygon.points[0]).manhattanLength() < 15:
                if len(self.cutting_polygon.points) >= 3:
                    self.cutting_polygon.points.append(self.cutting_polygon.points[0])
                    self.cutting_polygon.closed = True
                    self._finalize_cutting()
            else:
                # Добавление новой точки (не более 4)
                if len(self.cutting_polygon.points) < 4:
                    self.cutting_polygon.points.append(snapped_pos)
                    # Обновляем инструкции
                    if len(self.cutting_polygon.points) == 1:
                        self.parent().show_cut_instruction("Поставьте вторую точку на границе")
                    if len(self.cutting_polygon.points) == 2:
                        self.parent().show_cut_instruction("Поставьте третью точку на границе")
                    elif len(self.cutting_polygon.points) == 3:
                        self.parent().show_cut_instruction("Поставьте четвертую точку или замкните полигон")
                    elif len(self.cutting_polygon.points) == 4:
                        self.parent().show_cut_instruction("Кликните на первую точку для замыкания")

        self.update()

    def mousePressEvent(self, event):
        scene_pos = self.map_to_scene(event.pos())

        if event.button() == Qt.LeftButton:
            # Режим выделения области
            if self.cut_mode and self.active_object:
                if self.active_object.contains_point(scene_pos):
                    self.selection_area.set_start(scene_pos)

            # Обычное перемещение
            self.last_pos = event.pos()
            if self.mode_move:
                self.dragging = True
            else:
                # Выбор объекта для перемещения
                self.active_object = None
                for obj in reversed(self.raster_objects):
                    if obj.contains_point(scene_pos):
                        self.active_object = obj
                        self.dragging = True
                        break

        # Отмена выделения при нажатии правой кнопки
        elif event.button() == Qt.RightButton:
            if self.cutting_polygon.active:
                self.cutting_polygon.reset()
                self.update()
                if hasattr(self, 'parent') and self.parent():
                    self.parent().show_cut_instruction("Выделение отменено")

        if event.button() == Qt.LeftButton and self.vectorization_mode:
            try:
                scene_pos = self.map_to_scene(event.pos())
                local_pos = self._scene_to_raster_local(scene_pos, self.active_object)

                if not self.current_curve:
                    self.current_curve = VectorCurve(self.active_object, self.current_color)

                self.current_curve.points.append(local_pos)
                self.update()

                # Уведомляем об изменении кривых
                if hasattr(self.parent(), 'curves_changed'):
                    self.parent().curves_changed(bool(self.curves) or
                                                 (self.current_curve and len(self.current_curve.points) > 0))
            except Exception as e:
                print(f"Ошибка при добавлении точки: {str(e)}")

        if event.button() == Qt.LeftButton:
            self.last_pos = event.pos()
            scene_pos = self.map_to_scene(event.pos())

            if self.mode_move:
                self.dragging = True
            else:
                # Режим работы с растром: можно двигать активный объект
                self.dragging = bool(self.active_object and self.active_object.contains_point(scene_pos))

            # Обработка векторизации
            if self.vectorization_mode and self.active_object:
                try:
                    scene_pos = self.map_to_scene(event.pos())
                    local_pos = self._scene_to_raster_local(scene_pos, self.active_object)

                    if not self.current_curve:
                        self.current_curve = VectorCurve(self.active_object, self.current_color)

                    self.current_curve.points.append(local_pos)
                    self._notify_curves_changed()
                    self.update()
                except Exception as e:
                    print(f"Ошибка при добавлении точки векторизации: {str(e)}")
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.map_to_scene(event.pos())

        # 1. Обработка предпросмотра точек при резке
        if self.cut_mode and self.active_object and self.cutting_polygon.active:
            local_pos = RasterObject._convert_to_image_coords(scene_pos, self.active_object)
            self.last_snapped_pos = self.active_object.snap_to_border(local_pos)

        # 2. Обновляем выделение области
        if self.cut_mode and self.selection_area.active:
            self.selection_area.set_end(scene_pos)

        # 3. Обработка перемещения
        if self.dragging and event.buttons() & Qt.LeftButton:
            delta = event.pos() - self.last_pos
            if self.mode_move:
                self.pan += delta
            elif self.active_object:
                self.active_object.position += QPointF(delta.x() / self.zoom, delta.y() / self.zoom)
            self.last_pos = event.pos()

        # 4. Обновление курсора
        if self.cut_mode and self.active_object:
            local_pos = RasterObject._convert_to_image_coords(scene_pos, self.active_object)
            if self.active_object.is_on_border(local_pos):
                self.setCursor(Qt.CrossCursor)  # Крестообразный курсор у границ
            else:
                self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        self.update()

        if not self.mode_move and self.selection_mode:
            # Обновляем hovered объект только в режиме работы с растром и при включенном выделении
            new_hovered = None
            for obj in reversed(self.raster_objects):
                if obj.contains_point(scene_pos):
                    new_hovered = obj
                    break

            if new_hovered != self.hovered_object:
                self.hovered_object = new_hovered
                self.update()

        if self.dragging:
            delta = event.pos() - self.last_pos
            if self.mode_move:
                self.pan += delta
            else:
                if self.active_object and self.selection_mode:  # Добавили проверку selection_mode
                    self.active_object.position += QPointF(delta.x() / self.zoom, delta.y() / self.zoom)
            self.last_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def wheelEvent(self, event):
        mouse_pos = event.pos()
        scene_pos_before = QPointF(
            (mouse_pos.x() - self.pan.x()) / self.zoom,
            (mouse_pos.y() - self.pan.y()) / self.zoom
        )

        zoom_factor = 1.1
        if event.angleDelta().y() > 0:
            self.zoom *= zoom_factor
        else:
            self.zoom /= zoom_factor

        scene_pos_after = QPointF(
            (mouse_pos.x() - self.pan.x()) / self.zoom,
            (mouse_pos.y() - self.pan.y()) / self.zoom
        )

        delta = scene_pos_after - scene_pos_before
        self.pan += QPoint(int(delta.x() * self.zoom), int(delta.y() * self.zoom))
        self.update()

    def map_to_scene(self, widget_point):
        return QPointF(
            (widget_point.x() - self.pan.x()) / self.zoom,
            (widget_point.y() - self.pan.y()) / self.zoom
        )

    def center_camera_on_raster(self):
        if not self.raster_objects:
            return

        obj = self.raster_objects[-1]
        img_w = obj.size.width()
        img_h = obj.size.height()

        zoom_x = self.width() / img_w
        zoom_y = self.height() / img_h
        self.zoom = min(zoom_x, zoom_y) * 0.95

        # Центр изображения в координатах сцены
        img_center = QPointF(img_w / 2, img_h / 2)

        # Центр окна в экранных координатах
        widget_center = QPoint(self.width() // 2, self.height() // 2)

        # Переводим сцену так, чтобы центр изображения оказался в центре окна
        self.pan = widget_center - QPoint(
            int(img_center.x() * self.zoom),
            int(img_center.y() * self.zoom)
        )

        # print(f"[DEBUG] zoom={self.zoom:.4f}, pan={self.pan}")
        self.update()
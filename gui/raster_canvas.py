from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QWheelEvent, QMouseEvent
import numpy as np


class RasterCanvas(QGraphicsView):
    mouse_moved = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = None
        self.current_image = None

        # Режимы взаимодействия
        self.mode = 'pan'  # pan, add_point, delete_point, move_point, digitize

        # Данные оцифровки
        self.current_project = None
        self.current_trace = None
        self.current_interval = None

        # Масштабирование и панорамирование
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHint(QPainter.Antialiasing)

        # История действий
        self.history = []
        self.history_index = -1

        # Настройки отображения
        self.show_points = True
        self.show_lines = True
        self.point_size = 8
        self.line_color = QColor(255, 50, 50)
        self.line_width = 2
        self.point_color = QColor(255, 50, 50)

        # Zoom limits
        self.min_zoom = 0.1
        self.max_zoom = 150.0
        self.current_zoom = 1.0

        # Для перемещения точек
        self.dragging_point = False
        self.dragging_point_idx = -1

        # Настройка Drag Mode для панорамирования
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def load_image(self, image_array: np.ndarray):
        """Загрузить изображение из numpy array"""
        if image_array is None:
            print("Ошибка: image_array is None")
            return

        try:
            height, width = image_array.shape[:2]
            print(f"Загрузка изображения: {width}x{height}, dtype={image_array.dtype}")

            from PyQt5.QtGui import QImage

            if len(image_array.shape) == 2:
                bytes_per_line = width
                img_data = image_array.astype(np.uint8).copy()
                qimage = QImage(img_data.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            else:
                bytes_per_line = 3 * width
                img_data = image_array.astype(np.uint8).copy()
                qimage = QImage(img_data.data, width, height, bytes_per_line, QImage.Format_RGB888)

            pixmap = QPixmap.fromImage(qimage)

            if pixmap.isNull():
                print("Ошибка: не удалось создать QPixmap")
                return

            if self.pixmap_item:
                self.scene.removeItem(self.pixmap_item)

            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.pixmap_item)
            self.setSceneRect(QRectF(pixmap.rect()))

            self.current_image = image_array
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.current_zoom = 1.0

            print("Изображение успешно загружено")

        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            import traceback
            traceback.print_exc()

    def wheelEvent(self, event: QWheelEvent):
        """Масштабирование колесиком мыши"""
        if not self.pixmap_item:
            event.accept()
            return

        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            factor = zoom_in_factor
        else:
            factor = zoom_out_factor

        new_zoom = self.current_zoom * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.scale(factor, factor)
            self.current_zoom = new_zoom

        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """Обработка кликов мыши"""
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())

            # Проверяем клик внутри растра
            if self.pixmap_item:
                rect = self.pixmap_item.boundingRect()
                if not rect.contains(scene_pos):
                    super().mousePressEvent(event)
                    return

            # Обработка в зависимости от режима
            if self.mode == 'add_point':
                self.add_point(scene_pos.x(), scene_pos.y())
            elif self.mode == 'delete_point':
                self.delete_nearest_point(scene_pos.x(), scene_pos.y())
            elif self.mode == 'move_point':
                self.start_move_point(scene_pos.x(), scene_pos.y())
            elif self.mode == 'pan':
                super().mousePressEvent(event)
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Обработка движения мыши"""
        scene_pos = self.mapToScene(event.pos())
        if self.pixmap_item:
            rect = self.pixmap_item.boundingRect()
            if rect.contains(scene_pos):
                self.mouse_moved.emit(scene_pos.x(), scene_pos.y())

        if self.mode == 'move_point' and self.dragging_point and self.dragging_point_idx >= 0:
            scene_pos = self.mapToScene(event.pos())
            if self.pixmap_item:
                rect = self.pixmap_item.boundingRect()
                x = max(rect.left(), min(rect.right(), scene_pos.x()))
                y = max(rect.top(), min(rect.bottom(), scene_pos.y()))

                if self.current_interval and self.dragging_point_idx < len(self.current_interval.points):
                    point = self.current_interval.points[self.dragging_point_idx]
                    point.x = x
                    point.y = y
                    self.update_display()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Обработка отпускания кнопки"""
        if self.mode == 'move_point' and self.dragging_point:
            self.dragging_point = False
            self.dragging_point_idx = -1
            self.save_to_history()
        super().mouseReleaseEvent(event)

    def add_point(self, x: float, y: float):
        """Добавить точку оцифровки"""
        if not self.current_trace:
            print("Нет активной трассы")
            return

        if not self.current_interval:
            from models.trace import Interval
            import uuid
            self.current_interval = Interval(
                id=str(uuid.uuid4()),
                trace_id=self.current_trace.id,
                points=[]
            )
            self.current_trace.add_interval(self.current_interval)

        # Проверка границ
        if self.pixmap_item:
            rect = self.pixmap_item.boundingRect()
            x = max(rect.left(), min(rect.right(), x))
            y = max(rect.top(), min(rect.bottom(), y))

        self.save_to_history()
        self.current_interval.add_point(x, y)
        self.update_display()

    def delete_nearest_point(self, x: float, y: float, radius: float = 10.0):
        """Удалить ближайшую точку"""
        if not self.current_interval or not self.current_interval.points:
            return

        min_dist = float('inf')
        min_idx = -1

        for i, point in enumerate(self.current_interval.points):
            dist = ((point.x - x) ** 2 + (point.y - y) ** 2) ** 0.5
            if dist < min_dist and dist < radius:
                min_dist = dist
                min_idx = i

        if min_idx >= 0:
            self.save_to_history()
            self.current_interval.remove_point(min_idx)
            self.update_display()

    def start_move_point(self, x: float, y: float, radius: float = 10.0):
        """Начать перемещение точки"""
        if not self.current_interval or not self.current_interval.points:
            self.dragging_point = False
            return

        min_dist = float('inf')
        self.dragging_point_idx = -1

        for i, point in enumerate(self.current_interval.points):
            dist = ((point.x - x) ** 2 + (point.y - y) ** 2) ** 0.5
            if dist < min_dist and dist < radius:
                min_dist = dist
                self.dragging_point_idx = i

        if self.dragging_point_idx >= 0:
            self.save_to_history()
            self.dragging_point = True
        else:
            self.dragging_point = False

    def finish_current_interval(self) -> bool:
        """Завершить текущий интервал"""
        if self.current_interval and len(self.current_interval.points) > 0:
            self.save_to_history()

            from models.trace import Interval
            import uuid
            new_interval = Interval(
                id=str(uuid.uuid4()),
                trace_id=self.current_trace.id if self.current_trace else "unknown",
                points=[]
            )

            if self.current_trace:
                self.current_trace.add_interval(new_interval)

            self.current_interval = new_interval
            self.update_display()
            return True
        return False

    def save_to_history(self):
        """Сохранить текущее состояние"""
        if not self.current_interval:
            return

        points_copy = [(p.x, p.y, p.point_type) for p in self.current_interval.points]

        self.history = self.history[:self.history_index + 1]
        self.history.append(points_copy)
        self.history_index = len(self.history) - 1

    def undo(self):
        """Отменить последнее действие"""
        if self.history_index > 0 and self.current_interval:
            self.history_index -= 1
            self.restore_from_history()

    def redo(self):
        """Повторить действие"""
        if self.history_index < len(self.history) - 1 and self.current_interval:
            self.history_index += 1
            self.restore_from_history()

    def restore_from_history(self):
        """Восстановить из истории"""
        if not self.current_interval or self.history_index < 0:
            return

        points_data = self.history[self.history_index]
        from models.trace import Point2D, PointType

        self.current_interval.points = []
        for x, y, ptype in points_data:
            self.current_interval.points.append(Point2D(x, y, ptype))

        self.update_display()

    def update_display(self):
        """Обновить отображение"""
        if not self.pixmap_item:
            return

        # Очищаем все кроме изображения
        items_list = list(self.scene.items())
        for item in items_list:
            if item != self.pixmap_item:
                self.scene.removeItem(item)

        if hasattr(self, 'current_trace') and self.current_trace:
            if hasattr(self.current_trace, 'project') and self.current_trace.project:
                for trace in self.current_trace.project.traces:
                    if trace.is_visible:
                        for interval in trace.intervals:
                            if interval and interval.points:
                                if trace == self.current_trace:
                                    self.draw_interval(interval, color=QColor(255, 50, 50))
                                else:
                                    self.draw_interval(interval, color=QColor(255, 215, 0))
            else:
                if self.current_trace and self.current_trace.is_visible:
                    for interval in self.current_trace.intervals:
                        if interval and interval.points:
                            self.draw_interval(interval)
        else:
            if hasattr(self, 'current_project') and self.current_project:
                for trace in self.current_project.traces:
                    if trace.is_visible:
                        for interval in trace.intervals:
                            if interval and interval.points:
                                self.draw_interval(interval, color=QColor(255, 50, 50))
    def draw_interval(self, interval, color=None):
        """Нарисовать интервал"""
        if not interval or not interval.points:
            return

        points = interval.points
        num_points = len(points)

        if num_points == 0:
            return

        line_color = color if color else self.line_color
        point_color = color if color else self.point_color

        if self.show_lines and num_points > 1:
            pen = QPen(line_color, self.line_width)
            for i in range(num_points - 1):
                self.scene.addLine(
                    points[i].x, points[i].y,
                    points[i + 1].x, points[i + 1].y,
                    pen
                )

        if self.show_points:
            for point in points:
                ellipse = self.scene.addEllipse(
                    point.x - self.point_size / 2,
                    point.y - self.point_size / 2,
                    self.point_size, self.point_size,
                    QPen(point_color), point_color
                )

    def set_mode(self, mode: str):
        """Установить режим взаимодействия"""
        self.mode = mode

        if self.mode == 'pan':
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        elif self.mode == 'add_point':
            self.setCursor(Qt.CrossCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        elif self.mode == 'delete_point':
            self.setCursor(Qt.PointingHandCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        elif self.mode == 'move_point':
            self.setCursor(Qt.SizeAllCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.ScrollHandDrag)

    def set_current_trace(self, trace):
        """Установить текущую трассу"""
        self.current_trace = trace

        if trace and trace.intervals:
            self.current_interval = trace.intervals[-1]
        elif trace:
            from models.trace import Interval
            import uuid
            self.current_interval = Interval(
                id=str(uuid.uuid4()),
                trace_id=trace.id,
                points=[]
            )
            trace.add_interval(self.current_interval)
        else:
            self.current_interval = None

        self.update_display()

    def clear_current_interval(self):
        """Очистить текущий интервал"""
        self.current_interval = None
        self.update_display()

    def keyPressEvent(self, event):
        """Обработка клавиш"""
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            factor = 1.25
            new_zoom = self.current_zoom * factor
            if new_zoom <= self.max_zoom:
                self.scale(factor, factor)
                self.current_zoom = new_zoom
        elif event.key() == Qt.Key_Minus:
            factor = 0.8
            new_zoom = self.current_zoom * factor
            if new_zoom >= self.min_zoom:
                self.scale(factor, factor)
                self.current_zoom = new_zoom
        elif event.key() == Qt.Key_Home or event.key() == Qt.Key_F:
            self.resetTransform()
            if self.pixmap_item:
                self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.current_zoom = 1.0
        elif event.key() == Qt.Key_Space:
            if self.mode != 'pan':
                self.set_mode('pan')
            else:
                self.set_mode(self._prev_mode if hasattr(self, '_prev_mode') else 'add_point')
        else:
            super().keyPressEvent(event)
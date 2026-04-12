from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any
import numpy as np
import uuid


@dataclass
class Trace:
    """Класс для представления сейсмической трассы"""
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Уникальный ID
    points: List[Tuple[float, float]] = field(default_factory=list)  # [(x1, y1), (x2, y2), ...]
    color: Tuple[int, int, int] = (255, 0, 0)  # RGB цвет по умолчанию (красный)
    is_completed: bool = False  # Завершено ли выделение трассы
    is_editing: bool = False  # Режим редактирования
    bounding_box: Optional[Tuple[float, float, float, float]] = None  # (x1, y1, x2, y2)
    intervals: List[Any] = field(default_factory=list)  # Список интервалов трассы

    def __post_init__(self):
        """Инициализация после создания объекта"""
        if not hasattr(self, 'intervals') or self.intervals is None:
            self.intervals = []

    def add_point(self, x: float, y: float) -> None:
        """Добавить точку к трассе"""
        self.points.append((x, y))

    def clear_points(self) -> None:
        """Очистить все точки трассы"""
        self.points.clear()
        self.is_completed = False

    def get_point_count(self) -> int:
        """Получить количество точек в трассе"""
        return len(self.points)

    def to_polygon(self) -> List[Tuple[float, float]]:
        """Преобразовать точки в полигон (для отображения)"""
        if len(self.points) < 2:
            return []

        # Просто соединяем точки линией
        return self.points

    def __eq__(self, other):
        """Сравнение трасс по ID"""
        if not isinstance(other, Trace):
            return False
        return self.id == other.id

    def __hash__(self):
        """Хэш-функция для использования в словарях и множествах"""
        return hash(self.id)
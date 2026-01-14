# Класс сейсмических данных

from dataclasses import dataclass, field
from typing import List, Optional, Literal, Tuple
import numpy as np

type IntervalType = Literal["time_marker", "waveform", "noise"]

@dataclass
class DigitizationPoint:
    """Одна точка, поставленная пользователем на растре."""
    x_px: float          # Координата X на изображении (пиксель)
    y_px: float          # Координата Y на изображении (пиксель)
    t_val: Optional[float] = None  # Временная метка (сек), если вычислена
    a_val: Optional[float] = None  # Амплитудное значение, если вычислено

@dataclass
class DigitizationInterval:
    """Интервал для оцифровки (метка времени, сегмент волновой формы и т.д.)."""
    id: str
    type: IntervalType
    points: List[DigitizationPoint] = field(default_factory=list)  # Точки ручной разметки
    interpolated_points: Optional[np.ndarray] = None  # Регулярная оцифровка после интерполяции
    color: str = "#FF0000"  # Цвет отрисовки
    polynomial_order: int = 3  # Порядок интерполирующего полинома
    time_correction: float = 0.0
    amplitude_correction: float = 0.0
    metadata: dict = field(default_factory=dict)

    def add_point(self, x: float, y: float):
        self.points.append(DigitizationPoint(x_px=x, y_px=y))

@dataclass
class SeismicTrace:
    """Сейсмическая трасса (канал)."""
    id: str
    name: str
    raster_coords: Tuple[float, float, float, float]  # Область на растре (x0, y0, x1, y1)
    intervals: List[DigitizationInterval] = field(default_factory=list)
    sampling_rate: Optional[float] = None  # Частота дискретизации (Гц)
    units: str = "counts"
    metadata: dict = field(default_factory=dict)
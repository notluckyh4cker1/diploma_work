# Настройки рабочего экрана

from dataclasses import dataclass, field
from typing import Tuple, Optional
from enum import Enum


class RasterOrientation(Enum):
    """Ориентация растрового изображения."""
    HORIZONTAL = "horizontal"  # Время по горизонтали
    VERTICAL = "vertical"  # Время по вертикали


class TimeMarkType(Enum):
    """Тип временных меток."""
    REGULAR = "regular"  # Регулярные метки
    IRREGULAR = "irregular"  # Нерегулярные метки


@dataclass
class WorkspaceSettings:
    """Настройки рабочего пространства."""
    # Ориентация растра
    raster_orientation: RasterOrientation = RasterOrientation.HORIZONTAL

    # Временные параметры
    time_start: float = 0.0  # Время начала записи (сек)
    time_end: float = 100.0  # Время конца записи (сек)
    time_mark_type: TimeMarkType = TimeMarkType.REGULAR
    time_mark_interval: float = 1.0  # Интервал между метками (сек)

    # Поправки
    time_correction_start: float = 0.0  # Поправка начала времени
    time_correction_end: float = 0.0  # Поправка конца времени

    # Настройки отображения
    show_grid: bool = True
    grid_color: str = "#CCCCCC"
    grid_spacing: Tuple[float, float] = (50.0, 50.0)  # Интервал сетки в пикселях

    # Настройки оцифровки
    default_interpolation_order: int = 3
    auto_interpolate: bool = False  # Автоматическая интерполяция после завершения интервала

    # Настройки экспорта
    export_sampling_rate: float = 100.0  # Частота дискретизации для экспорта (Гц)
    export_amplitude_units: str = "counts"

    def __post_init__(self):
        # Проверка корректности параметров
        if self.time_end <= self.time_start:
            self.time_end = self.time_start + 100.0
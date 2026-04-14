from dataclasses import dataclass, field
from typing import List, Tuple, Optional, TYPE_CHECKING
from enum import Enum
import numpy as np

if TYPE_CHECKING:
    from models.project import Project


class PointType(Enum):
    MANUAL = "manual"
    INTERPOLATED = "interpolated"
    CORRECTED = "corrected"


class InterpolationType(Enum):
    LINEAR = "linear"
    CUBIC = "cubic"
    QUADRATIC = "quadratic"


@dataclass
class Point2D:
    x: float
    y: float
    point_type: PointType = PointType.MANUAL
    timestamp: Optional[float] = None
    amplitude: Optional[float] = None

    @property
    def x_px(self) -> float:
        return self.x

    @property
    def y_px(self) -> float:
        return self.y

    @property
    def t_val(self) -> Optional[float]:
        return self.timestamp

    @property
    def a_val(self) -> Optional[float]:
        return self.amplitude


@dataclass
class Interval:
    id: str
    trace_id: str
    points: List[Point2D] = field(default_factory=list)
    interpolation_type: InterpolationType = InterpolationType.CUBIC
    color: str = "#ff0000"
    is_noise: bool = False
    notes: str = ""

    def add_point(self, x: float, y: float):
        self.points.append(Point2D(x, y))

    def remove_point(self, index: int):
        if 0 <= index < len(self.points):
            self.points.pop(index)

    def get_xy_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        if not self.points:
            return np.array([]), np.array([])
        x = np.array([p.x for p in self.points])
        y = np.array([p.y for p in self.points])
        return x, y


@dataclass
class Trace:
    id: str
    name: str
    raster_coords: Tuple[Tuple[float, float], Tuple[float, float]] = ((0, 0), (0, 0))
    time_calibration: Optional[dict] = None
    amplitude_calibration: Optional[dict] = None
    intervals: List[Interval] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    is_visible: bool = True
    is_editing: bool = False

    def __post_init__(self):
        self._project = None

    @property
    def project(self):
        return self._project

    @project.setter
    def project(self, value):
        self._project = value

    def add_interval(self, interval: Interval):
        self.intervals.append(interval)

    def get_all_points(self) -> List[Point2D]:
        points = []
        for interval in self.intervals:
            points.extend(interval.points)
        return points

    def clear(self):
        """Очистить данные трассы (для предотвращения утечек)"""
        for interval in self.intervals:
            interval.points.clear()
        self.intervals.clear()
        self._project = None
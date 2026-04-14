import numpy as np
from scipy import interpolate
from typing import List, Tuple, Optional
from models.trace import Interval, InterpolationType, Point2D, PointType


class DigitizerEngine:
    """Движок для оцифровки и интерполяции"""

    @staticmethod
    def interpolate_interval(interval: Interval, num_points: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        Интерполяция точек интервала с заданным полиномом
        Возвращает (x_interp, y_interp)
        """
        if len(interval.points) < 2:
            return np.array([]), np.array([])

        x = np.array([p.x for p in interval.points])
        y = np.array([p.y for p in interval.points])

        # Сортируем по x
        sort_idx = np.argsort(x)
        x = x[sort_idx]
        y = y[sort_idx]

        # Создаем равномерную сетку по x
        x_interp = np.linspace(x[0], x[-1], num_points)

        # Выбираем метод интерполяции
        if interval.interpolation_type == InterpolationType.LINEAR:
            f = interpolate.interp1d(x, y, kind='linear', fill_value='extrapolate')
            y_interp = f(x_interp)

        elif interval.interpolation_type == InterpolationType.QUADRATIC:
            # Квадратичная интерполяция (полином 2-й степени)
            coeffs = np.polyfit(x, y, 2)
            y_interp = np.polyval(coeffs, x_interp)

        elif interval.interpolation_type == InterpolationType.CUBIC:
            # Кубический сплайн
            try:
                cs = interpolate.CubicSpline(x, y, bc_type='natural')
                y_interp = cs(x_interp)
            except:
                # Fallback на линейную
                f = interpolate.interp1d(x, y, kind='linear', fill_value='extrapolate')
                y_interp = f(x_interp)

        return x_interp, y_interp

    @staticmethod
    def regular_sampling(interval: Interval, time_step: float,
                         time_calibration: dict) -> List[Point2D]:
        """
        Регулярная оцифровка с фиксированным шагом по времени
        time_calibration: {'pixel_to_time': function, 'time_to_pixel': function}
        """
        if len(interval.points) < 2:
            return []

        x, y = DigitizerEngine.interpolate_interval(interval, num_points=1000)

        # Конвертируем x (пиксели) во время
        if time_calibration and 'pixel_to_time' in time_calibration:
            time_func = time_calibration['pixel_to_time']
            times = np.array([time_func(xi) for xi in x])

            # Создаем регулярную сетку по времени
            t_start = times[0]
            t_end = times[-1]
            t_regular = np.arange(t_start, t_end + time_step, time_step)

            # Интерполируем обратно в пиксели для точек
            x_regular = np.interp(t_regular, times, x)
            y_regular = np.interp(t_regular, times, y)

            # Создаем точки
            points = []
            for xi, yi, ti in zip(x_regular, y_regular, t_regular):
                point = Point2D(xi, yi, PointType.INTERPOLATED)
                point.timestamp = ti
                points.append(point)

            return points

        return []

    @staticmethod
    def remove_trend(points: List[Point2D], degree: int = 1) -> List[Point2D]:
        """
        Удаление тренда из точек
        degree: степень полинома для тренда (1 - линейный, 2 - квадратичный и т.д.)
        """
        if len(points) < degree + 1:
            return points

        x = np.array([p.x for p in points])
        y = np.array([p.y for p in points])

        # Находим тренд
        coeffs = np.polyfit(x, y, degree)
        trend = np.polyval(coeffs, x)

        # Вычитаем тренд
        y_corrected = y - trend

        # Создаем новые точки
        corrected_points = []
        for i, point in enumerate(points):
            new_point = Point2D(point.x, y_corrected[i], PointType.CORRECTED)
            new_point.timestamp = point.timestamp
            corrected_points.append(new_point)

        return corrected_points
# Интерполяция

import numpy as np
from scipy import interpolate
from typing import List, Tuple, Optional
from models.seismic_data import DigitizationPoint


def interpolate_points(points: List[DigitizationPoint],
                       polynomial_order: int = 3,
                       num_samples: int = 100,
                       use_spline: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """
    Интерполирует точки с использованием полинома или сплайна.

    Args:
        points: Список точек для интерполяции
        polynomial_order: Порядок полинома (если не используется сплайн)
        num_samples: Количество точек для регулярной оцифровки
        use_spline: Использовать сплайн вместо полинома

    Returns:
        x_interp, y_interp: Интерполированные координаты
    """
    if len(points) < 2:
        raise ValueError("Нужно как минимум 2 точки для интерполяции")

    # Извлекаем координаты
    x = np.array([p.x_px for p in points])
    y = np.array([p.y_px for p in points])

    # Сортируем по X
    sort_idx = np.argsort(x)
    x_sorted = x[sort_idx]
    y_sorted = y[sort_idx]

    if use_spline:
        # Кубический сплайн
        spline = interpolate.CubicSpline(x_sorted, y_sorted)
        x_interp = np.linspace(x_sorted.min(), x_sorted.max(), num_samples)
        y_interp = spline(x_interp)
    else:
        # Полиномиальная интерполяция
        coeffs = np.polyfit(x_sorted, y_sorted, polynomial_order)
        poly = np.poly1d(coeffs)
        x_interp = np.linspace(x_sorted.min(), x_sorted.max(), num_samples)
        y_interp = poly(x_interp)

    return x_interp, y_interp


def regular_digitization(points: List[DigitizationPoint],
                         time_start: float,
                         time_end: float,
                         sampling_rate: float = 100.0,
                         polynomial_order: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """
    Регулярная оцифровка с преобразованием в время и амплитуду.

    Args:
        points: Список точек
        time_start: Время начала интервала (сек)
        time_end: Время конца интервала (сек)
        sampling_rate: Частота дискретизации (Гц)
        polynomial_order: Порядок интерполяционного полинома

    Returns:
        time, amplitude: Временные метки и амплитуды
    """
    if len(points) < 2:
        raise ValueError("Нужно как минимум 2 точки для оцифровки")

    # Интерполируем точки
    x_interp, y_interp = interpolate_points(points, polynomial_order, use_spline=True)

    # Преобразуем координаты X во время
    # Предполагаем линейную зависимость между координатой X и временем
    x_min = x_interp.min()
    x_max = x_interp.max()

    # Линейное преобразование X -> время
    time = time_start + (x_interp - x_min) * (time_end - time_start) / (x_max - x_min)

    # Преобразуем координаты Y в амплитуду
    # Инвертируем Y, так как в изображениях ось Y направлена вниз
    amplitude = y_interp.max() + y_interp.min() - y_interp

    # Ресэмплируем на регулярную сетку, если нужно
    if sampling_rate > 0:
        regular_time = np.arange(time_start, time_end, 1.0 / sampling_rate)
        if len(regular_time) > 0:
            amplitude_regular = np.interp(regular_time, time, amplitude)
            return regular_time, amplitude_regular

    return time, amplitude


def fit_time_markers(points: List[DigitizationPoint],
                     expected_times: List[float]) -> Tuple[np.ndarray, float]:
    """
    Определяет преобразование координат пикселей во время на основе меток времени.

    Args:
        points: Метки времени на изображении
        expected_times: Ожидаемые времена для каждой метки

    Returns:
        coeffs: Коэффициенты полинома X -> время
        r_squared: Коэффициент детерминации
    """
    if len(points) != len(expected_times):
        raise ValueError("Количество точек должно совпадать с количеством ожидаемых времен")

    x = np.array([p.x_px for p in points])
    t = np.array(expected_times)

    # Линейная регрессия (можно расширить до полиномиальной)
    coeffs = np.polyfit(x, t, 1)

    # Вычисляем R²
    poly = np.poly1d(coeffs)
    y_pred = poly(x)
    ss_res = np.sum((t - y_pred) ** 2)
    ss_tot = np.sum((t - np.mean(t)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 1.0

    return coeffs, r_squared
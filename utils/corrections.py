# Коррекции

import numpy as np
from typing import Tuple, Optional
from scipy import signal, interpolate


def remove_trend(time: np.ndarray, amplitude: np.ndarray,
                 polynomial_order: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    """
    Удаляет полиномиальный тренд из сигнала.
    """
    if len(time) != len(amplitude):
        raise ValueError("Длины массивов времени и амплитуды должны совпадать")

    # Аппроксимируем тренд полиномом
    coeffs = np.polyfit(time, amplitude, polynomial_order)
    trend_poly = np.poly1d(coeffs)
    trend = trend_poly(time)

    # Удаляем тренд
    amplitude_detrended = amplitude - trend

    return amplitude_detrended, trend


def correct_time_irregularity(time_marks: np.ndarray,
                              expected_times: np.ndarray,
                              signal_time: np.ndarray,
                              signal_amplitude: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Корректирует неравномерность временного хода.

    Args:
        time_marks: Измеренные времена меток
        expected_times: Ожидаемые времена меток
        signal_time: Временная шкала сигнала
        signal_amplitude: Амплитуды сигнала

    Returns:
        corrected_time, corrected_amplitude: Корректированные данные
    """
    if len(time_marks) != len(expected_times):
        raise ValueError("Количество меток должно совпадать с количеством ожидаемых времен")

    # Интерполируем поправку времени
    time_correction = expected_times - time_marks

    # Интерполируем поправку на временную сетку сигнала
    correction_interp = np.interp(signal_time, time_marks, time_correction)

    # Применяем поправку
    corrected_time = signal_time + correction_interp

    # Ресэмплируем сигнал на равномерную временную сетку
    # (если исходная сетка была неравномерной)
    if len(corrected_time) > 1:
        dt = np.diff(corrected_time)
        if np.std(dt) / np.mean(dt) > 0.01:  # Если сетка неравномерная
            regular_time = np.linspace(corrected_time.min(), corrected_time.max(), len(corrected_time))
            amplitude_interp = np.interp(regular_time, corrected_time, signal_amplitude)
            return regular_time, amplitude_interp

    return corrected_time, signal_amplitude


def fix_trace_break(time: np.ndarray, amplitude: np.ndarray,
                    break_indices: Optional[np.ndarray] = None,
                    window_size: int = 10) -> np.ndarray:
    """
    Склеивает разрывы в закольцованной трассе.

    Args:
        time: Временные метки
        amplitude: Амплитуды сигнала
        break_indices: Индексы разрывов (если None, определяются автоматически)
        window_size: Размер окна для анализа скачков

    Returns:
        amplitude_fixed: Сигнал со склеенными разрывами
    """
    if break_indices is None:
        # Автоматическое определение разрывов
        diff = np.diff(amplitude)
        diff_abs = np.abs(diff)

        # Находим скачки, превышающие порог
        threshold = 3 * np.std(diff_abs)
        break_indices = np.where(diff_abs > threshold)[0]

    if len(break_indices) == 0:
        return amplitude.copy()

    amplitude_fixed = amplitude.copy()

    for idx in break_indices:
        if idx < window_size or idx > len(amplitude) - window_size - 1:
            continue

        # Вычисляем смещение до и после разрыва
        before_mean = np.mean(amplitude[idx - window_size:idx])
        after_mean = np.mean(amplitude[idx + 1:idx + window_size + 1])
        offset = after_mean - before_mean

        # Корректируем часть после разрыва
        amplitude_fixed[idx + 1:] -= offset

    return amplitude_fixed


def normalize_amplitude(amplitude: np.ndarray,
                        method: str = 'zscore') -> np.ndarray:
    """
    Нормализует амплитуду сигнала.

    Args:
        amplitude: Амплитуды сигнала
        method: Метод нормализации ('zscore', 'minmax', 'rms')

    Returns:
        normalized_amplitude: Нормализованные амплитуды
    """
    if method == 'zscore':
        # Z-score нормализация
        mean = np.mean(amplitude)
        std = np.std(amplitude)
        if std == 0:
            return amplitude - mean
        return (amplitude - mean) / std

    elif method == 'minmax':
        # Min-Max нормализация к [-1, 1]
        min_val = np.min(amplitude)
        max_val = np.max(amplitude)
        if max_val == min_val:
            return np.zeros_like(amplitude)
        return 2 * (amplitude - min_val) / (max_val - min_val) - 1

    elif method == 'rms':
        # Нормализация по RMS
        rms = np.sqrt(np.mean(amplitude ** 2))
        if rms == 0:
            return amplitude
        return amplitude / rms

    else:
        raise ValueError(f"Неизвестный метод нормализации: {method}")
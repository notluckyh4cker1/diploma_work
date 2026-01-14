# Движок для автоматической и полуавтоматической оцифровки

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from models.seismic_data import DigitizationPoint, DigitizationInterval
from utils.interpolation import interpolate_points, regular_digitization
from utils.corrections import remove_trend, correct_time_irregularity, fix_trace_break


class DigitizerEngine:
    """Движок для выполнения операций оцифровки."""

    def __init__(self, project=None):
        self.project = project
        self.auto_corrections_enabled = True

    def digitize_interval(self, interval: DigitizationInterval,
                          sampling_rate: float = None,
                          apply_corrections: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Выполняет полную оцифровку интервала.

        Args:
            interval: Интервал для оцифровки
            sampling_rate: Частота дискретизации
            apply_corrections: Применять автоматические коррекции

        Returns:
            Tuple: (время, амплитуда)
        """
        if len(interval.points) < 2:
            raise ValueError("Нужно минимум 2 точки для оцифровки")

        # Получаем настройки
        if self.project:
            time_start = self.project.settings.time_start
            time_end = self.project.settings.time_end
            if sampling_rate is None:
                sampling_rate = self.project.settings.export_sampling_rate
        else:
            time_start = 0.0
            time_end = 1.0
            if sampling_rate is None:
                sampling_rate = 100.0

        # Выполняем регулярную оцифровку
        time, amplitude = regular_digitization(
            interval.points,
            time_start=time_start,
            time_end=time_end,
            sampling_rate=sampling_rate,
            polynomial_order=interval.polynomial_order
        )

        # Применяем поправки интервала
        time += interval.time_correction
        amplitude += interval.amplitude_correction

        # Применяем автоматические коррекции
        if apply_corrections and self.auto_corrections_enabled:
            amplitude = self._apply_auto_corrections(time, amplitude)

        return time, amplitude

    def _apply_auto_corrections(self, time: np.ndarray,
                                amplitude: np.ndarray) -> np.ndarray:
        """
        Применяет автоматические коррекции к данным.

        Args:
            time: Временные метки
            amplitude: Амплитуды

        Returns:
            np.ndarray: Скорректированные амплитуды
        """
        if len(time) < 10:  # Слишком мало точек для коррекций
            return amplitude

        amplitude_corrected = amplitude.copy()

        try:
            # 1. Удаление линейного тренда
            amplitude_corrected, _ = remove_trend(time, amplitude_corrected,
                                                  polynomial_order=1)

            # 2. Коррекция разрывов (для закольцованных трасс)
            amplitude_corrected = fix_trace_break(time, amplitude_corrected)

        except Exception as e:
            print(f"Ошибка при автоматических коррекциях: {e}")

        return amplitude_corrected

    def auto_digitize_trace(self, trace_points: List[Tuple[float, float]],
                            num_samples: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        Автоматическая оцифровка трассы по ключевым точкам.

        Args:
            trace_points: Ключевые точки трассы [(x1, y1), (x2, y2), ...]
            num_samples: Количество точек для оцифровки

        Returns:
            Tuple: (координаты X, координаты Y оцифрованной трассы)
        """
        if len(trace_points) < 2:
            raise ValueError("Нужно минимум 2 точки для оцифровки")

        # Преобразуем точки в DigitizationPoint
        points = [DigitizationPoint(x_px=x, y_px=y) for x, y in trace_points]

        # Интерполируем
        x_interp, y_interp = interpolate_points(
            points,
            polynomial_order=3,
            num_samples=num_samples,
            use_spline=True
        )

        return x_interp, y_interp

    def refine_points(self, points: List[DigitizationPoint],
                      search_radius: float = 5.0) -> List[DigitizationPoint]:
        """
        Уточняет положение точек на основе локальных минимумов/максимумов.

        Args:
            points: Исходные точки
            search_radius: Радиус поиска для уточнения

        Returns:
            List[DigitizationPoint]: Уточненные точки
        """
        if not self.project or not self.project.raster:
            return points

        refined_points = []

        for point in points:
            # Ищем локальный минимум/максимум в окрестности точки
            refined_point = self._find_local_extremum(
                point.x_px, point.y_px, search_radius
            )

            if refined_point:
                refined_points.append(refined_point)
            else:
                refined_points.append(point)

        return refined_points

    def _find_local_extremum(self, x: float, y: float,
                             radius: float) -> Optional[DigitizationPoint]:
        """
        Находит локальный экстремум в окрестности точки.

        Args:
            x, y: Координаты точки
            radius: Радиус поиска

        Returns:
            DigitizationPoint: Точка локального экстремума или None
        """
        # Эта функция требует доступа к данным изображения
        # В текущей реализации возвращаем исходную точку
        # Для полноценной реализации нужен доступ к значениям пикселей
        return DigitizationPoint(x_px=x, y_px=y)

    def batch_digitize(self, intervals: List[DigitizationInterval],
                       progress_callback=None) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """
        Пакетная оцифровка нескольких интервалов.

        Args:
            intervals: Список интервалов
            progress_callback: Функция для отслеживания прогресса

        Returns:
            Dict: Результаты оцифровки {interval_id: (time, amplitude)}
        """
        results = {}
        total = len(intervals)

        for i, interval in enumerate(intervals):
            try:
                time, amplitude = self.digitize_interval(interval)
                results[interval.id] = (time, amplitude)
            except Exception as e:
                print(f"Ошибка при оцифровке интервала {interval.id}: {e}")
                results[interval.id] = (None, None)

            # Вызываем callback для отслеживания прогресса
            if progress_callback:
                progress_callback(i + 1, total, interval.id)

        return results

    def calculate_interval_quality(self, interval: DigitizationInterval,
                                   digitized_data: Tuple[np.ndarray, np.ndarray]) -> float:
        """
        Вычисляет качество оцифровки интервала.

        Args:
            interval: Интервал
            digitized_data: Оцифрованные данные (time, amplitude)

        Returns:
            float: Оценка качества (0-1)
        """
        time, amplitude = digitized_data

        if time is None or amplitude is None or len(time) < 2:
            return 0.0

        # Вычисляем несколько метрик качества

        # 1. Плавность данных (стандартное отклонение второй производной)
        if len(amplitude) > 4:
            second_derivative = np.diff(amplitude, 2)
            smoothness = 1.0 / (1.0 + np.std(second_derivative))
        else:
            smoothness = 0.5

        # 2. Равномерность распределения точек
        if len(interval.points) > 2:
            x_coords = [p.x_px for p in interval.points]
            x_diff = np.diff(x_coords)
            uniformity = 1.0 / (1.0 + np.std(x_diff) / np.mean(x_diff))
        else:
            uniformity = 0.5

        # 3. Количество точек (чем больше, тем лучше, до определенного предела)
        point_quality = min(len(interval.points) / 20.0, 1.0)

        # Итоговая оценка
        quality = 0.4 * smoothness + 0.3 * uniformity + 0.3 * point_quality

        return max(0.0, min(1.0, quality))

    def generate_time_marks(self, start_time: float, end_time: float,
                            interval_seconds: float = 1.0) -> List[Dict[str, float]]:
        """
        Генерирует временные метки для оцифровки.

        Args:
            start_time: Начальное время
            end_time: Конечное время
            interval_seconds: Интервал между метками

        Returns:
            List: Список временных меток
        """
        time_marks = []
        current_time = start_time

        while current_time <= end_time:
            time_marks.append({
                'time': current_time,
                'x_position': self._time_to_x_position(current_time, start_time, end_time)
            })
            current_time += interval_seconds

        return time_marks

    def _time_to_x_position(self, time: float, start_time: float,
                            end_time: float) -> float:
        """
        Преобразует время в координату X на изображении.

        Args:
            time: Время
            start_time: Начальное время
            end_time: Конечное время

        Returns:
            float: Координата X
        """
        # Линейное преобразование время -> координата X
        # Предполагаем, что изображение занимает всю ширину
        if self.project and self.project.raster and self.project.raster.pil_image:
            width, _ = self.project.raster.pil_image.size
        else:
            width = 1000.0

        if end_time == start_time:
            return 0.0

        return width * (time - start_time) / (end_time - start_time)

    def validate_interval(self, interval: DigitizationInterval) -> Tuple[bool, List[str]]:
        """
        Проверяет корректность интервала.

        Args:
            interval: Интервал для проверки

        Returns:
            Tuple: (корректность, список ошибок)
        """
        errors = []

        # Проверка количества точек
        if len(interval.points) < 2:
            errors.append("Интервал должен содержать минимум 2 точки")

        # Проверка порядка полинома
        if interval.polynomial_order < 1 or interval.polynomial_order > 10:
            errors.append("Порядок полинома должен быть от 1 до 10")

        # Проверка уникальности ID
        if not interval.id or len(interval.id) < 2:
            errors.append("ID интервала должен содержать минимум 2 символа")

        # Проверка типа интервала
        valid_types = ['time_marker', 'waveform', 'noise']
        if interval.type not in valid_types:
            errors.append(f"Некорректный тип интервала. Допустимые: {valid_types}")

        return len(errors) == 0, errors

    def export_digitization_report(self, intervals: List[DigitizationInterval],
                                   output_path: str) -> bool:
        """
        Экспортирует отчет об оцифровке.

        Args:
            intervals: Список интервалов
            output_path: Путь для сохранения отчета

        Returns:
            bool: Успешность экспорта
        """
        try:
            import json

            report = {
                'timestamp': np.datetime64('now').astype(str),
                'total_intervals': len(intervals),
                'intervals': []
            }

            for interval in intervals:
                interval_data = {
                    'id': interval.id,
                    'type': interval.type,
                    'point_count': len(interval.points),
                    'polynomial_order': interval.polynomial_order,
                    'color': interval.color,
                    'time_correction': interval.time_correction,
                    'amplitude_correction': interval.amplitude_correction
                }

                # Добавляем статистику оцифровки, если есть данные
                try:
                    time, amplitude = self.digitize_interval(interval)
                    if time is not None and amplitude is not None:
                        interval_data['digitized'] = {
                            'sample_count': len(time),
                            'time_range': [float(time[0]), float(time[-1])],
                            'amplitude_range': [float(np.min(amplitude)),
                                                float(np.max(amplitude))],
                            'quality_score': self.calculate_interval_quality(
                                interval, (time, amplitude)
                            )
                        }
                except:
                    pass

                report['intervals'].append(interval_data)

            # Сохраняем отчет
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Ошибка при экспорте отчета: {e}")
            return False
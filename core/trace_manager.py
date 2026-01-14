# Менеджер для работы с сейсмическими трассами

from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from models.seismic_data import SeismicTrace, DigitizationInterval, DigitizationPoint
from utils.interpolation import regular_digitization, interpolate_points


class TraceManager:
    """Управляет операциями с сейсмическими трассами."""

    def __init__(self, project=None):
        self.project = project

    def create_trace(self, name: str,
                     raster_coords: Tuple[float, float, float, float] = None,
                     sampling_rate: float = None) -> SeismicTrace:
        """
        Создает новую сейсмическую трассу.

        Args:
            name: Имя трассы
            raster_coords: Координаты области трассы на растре (x0, y0, x1, y1)
            sampling_rate: Частота дискретизации

        Returns:
            SeismicTrace: Созданная трасса
        """
        import uuid

        # Генерируем уникальный ID
        trace_id = f"TR_{uuid.uuid4().hex[:8]}"

        if raster_coords is None:
            # По умолчанию - вся область изображения
            if self.project and self.project.raster:
                # Получаем размеры из метаданных
                info = self.project.raster.get_image_info()
                if info:
                    width, height = info['size']
                    raster_coords = (0, 0, width, height)
                else:
                    raster_coords = (0, 0, 1000, 1000)
            else:
                raster_coords = (0, 0, 1000, 1000)

        # Создаем трассу
        trace = SeismicTrace(
            id=trace_id,
            name=name,
            raster_coords=raster_coords,
            sampling_rate=sampling_rate or (self.project.settings.export_sampling_rate
                                            if self.project else 100.0)
        )

        return trace

    def add_interval_to_trace(self, trace: SeismicTrace,
                              interval: DigitizationInterval) -> bool:
        """
        Добавляет интервал к трассе.

        Args:
            trace: Трасса
            interval: Интервал для добавления

        Returns:
            bool: Успешность операции
        """
        # Проверяем, что интервал находится в области трассы
        if not self._is_interval_in_trace_area(interval, trace):
            print("Интервал находится вне области трассы")
            return False

        # Добавляем интервал
        trace.intervals.append(interval)

        # Обновляем статистику проекта
        if self.project:
            self.project.total_intervals += 1
            self.project.total_points += len(interval.points)

        return True

    def _is_interval_in_trace_area(self, interval: DigitizationInterval,
                                   trace: SeismicTrace) -> bool:
        """
        Проверяет, находится ли интервал в области трассы.

        Args:
            interval: Интервал
            trace: Трасса

        Returns:
            bool: True если интервал в области трассы
        """
        if not interval.points:
            return True

        x0, y0, x1, y1 = trace.raster_coords
        trace_min_x, trace_max_x = min(x0, x1), max(x0, x1)
        trace_min_y, trace_max_y = min(y0, y1), max(y0, y1)

        for point in interval.points:
            if not (trace_min_x <= point.x_px <= trace_max_x and
                    trace_min_y <= point.y_px <= trace_max_y):
                return False

        return True

    def merge_intervals(self, trace: SeismicTrace,
                        interval_ids: List[str]) -> Optional[DigitizationInterval]:
        """
        Объединяет несколько интервалов в один.

        Args:
            trace: Трасса
            interval_ids: Список ID интервалов для объединения

        Returns:
            DigitizationInterval: Объединенный интервал или None
        """
        # Находим интервалы
        intervals = []
        remaining_intervals = []

        for interval in trace.intervals:
            if interval.id in interval_ids:
                intervals.append(interval)
            else:
                remaining_intervals.append(interval)

        if len(intervals) < 2:
            print("Для объединения нужно минимум 2 интервала")
            return None

        # Объединяем точки
        all_points = []
        for interval in intervals:
            all_points.extend(interval.points)

        # Сортируем точки по координате X
        all_points.sort(key=lambda p: p.x_px)

        # Создаем новый интервал
        import uuid
        from models.seismic_data import DigitizationInterval

        merged_interval = DigitizationInterval(
            id=str(uuid.uuid4())[:8],
            type=intervals[0].type,  # Берем тип первого интервала
            points=all_points,
            color=intervals[0].color,
            polynomial_order=intervals[0].polynomial_order
        )

        # Заменяем старые интервалы на объединенный
        trace.intervals = remaining_intervals
        trace.intervals.append(merged_interval)

        return merged_interval

    def split_interval(self, trace: SeismicTrace, interval_id: str,
                       split_index: int) -> Tuple[Optional[DigitizationInterval],
    Optional[DigitizationInterval]]:
        """
        Разделяет интервал на две части.

        Args:
            trace: Трасса
            interval_id: ID интервала для разделения
            split_index: Индекс точки для разделения

        Returns:
            Tuple: Два новых интервала или (None, None)
        """
        # Находим интервал
        interval = None
        interval_index = -1
        for i, interv in enumerate(trace.intervals):
            if interv.id == interval_id:
                interval = interv
                interval_index = i
                break

        if not interval:
            print(f"Интервал {interval_id} не найден")
            return None, None

        if split_index < 1 or split_index >= len(interval.points) - 1:
            print("Некорректный индекс для разделения")
            return None, None

        # Разделяем точки
        points1 = interval.points[:split_index + 1]
        points2 = interval.points[split_index:]

        # Создаем новые интервалы
        import uuid
        from models.seismic_data import DigitizationInterval

        interval1 = DigitizationInterval(
            id=str(uuid.uuid4())[:8],
            type=interval.type,
            points=points1,
            color=interval.color,
            polynomial_order=interval.polynomial_order,
            time_correction=interval.time_correction,
            amplitude_correction=interval.amplitude_correction
        )

        interval2 = DigitizationInterval(
            id=str(uuid.uuid4())[:8],
            type=interval.type,
            points=points2,
            color=interval.color,
            polynomial_order=interval.polynomial_order,
            time_correction=interval.time_correction,
            amplitude_correction=interval.amplitude_correction
        )

        # Заменяем старый интервал на новые
        trace.intervals.pop(interval_index)
        trace.intervals.append(interval1)
        trace.intervals.append(interval2)

        return interval1, interval2

    def calculate_trace_statistics(self, trace: SeismicTrace) -> Dict[str, Any]:
        """
        Вычисляет статистику для трассы.

        Args:
            trace: Трасса

        Returns:
            Dict: Статистика трассы
        """
        stats = {
            'name': trace.name,
            'id': trace.id,
            'interval_count': len(trace.intervals),
            'total_points': sum(len(interval.points) for interval in trace.intervals),
            'sampling_rate': trace.sampling_rate,
            'units': trace.units,
            'raster_area': trace.raster_coords
        }

        # Статистика по типам интервалов
        type_stats = {}
        for interval in trace.intervals:
            type_stats[interval.type] = type_stats.get(interval.type, 0) + 1

        stats['interval_types'] = type_stats

        # Временной диапазон (если есть временные данные)
        if self.project:
            all_times = []
            for interval in trace.intervals:
                time, _ = self.project.get_digitized_data(interval.id, trace.id)
                if time is not None:
                    all_times.extend(time)

            if all_times:
                stats['time_range'] = (min(all_times), max(all_times))
                stats['duration'] = max(all_times) - min(all_times)

        return stats

    def auto_detect_traces(self, num_traces: int = 3,
                           margin: float = 0.1) -> List[SeismicTrace]:
        """
        Автоматически определяет трассы на изображении.

        Args:
            num_traces: Количество трасс для определения
            margin: Отступ от краев (в долях от высоты/ширины)

        Returns:
            List[SeismicTrace]: Список обнаруженных трасс
        """
        if not self.project or not self.project.raster or not self.project.raster.pil_image:
            return []

        # Получаем размеры изображения
        width, height = self.project.raster.pil_image.size

        # Вычисляем отступы
        margin_x = int(width * margin)
        margin_y = int(height * margin)

        # Вычисляем ширину каждой трассы
        trace_width = (width - 2 * margin_x) / num_traces

        traces = []
        for i in range(num_traces):
            x0 = margin_x + i * trace_width
            x1 = margin_x + (i + 1) * trace_width

            trace = self.create_trace(
                name=f"Автотрасса_{i + 1}",
                raster_coords=(x0, margin_y, x1, height - margin_y),
                sampling_rate=self.project.settings.export_sampling_rate
            )
            traces.append(trace)

        return traces

    def export_trace_data(self, trace: SeismicTrace,
                          format: str = 'numpy') -> Dict[str, Any]:
        """
        Экспортирует данные трассы в указанном формате.

        Args:
            trace: Трасса для экспорта
            format: Формат данных ('numpy', 'dict', 'list')

        Returns:
            Dict: Данные трассы в указанном формате
        """
        data = {
            'trace_info': {
                'name': trace.name,
                'id': trace.id,
                'sampling_rate': trace.sampling_rate,
                'units': trace.units,
                'raster_coords': trace.raster_coords
            },
            'intervals': []
        }

        for interval in trace.intervals:
            interval_data = {
                'id': interval.id,
                'type': interval.type,
                'color': interval.color,
                'polynomial_order': interval.polynomial_order,
                'time_correction': interval.time_correction,
                'amplitude_correction': interval.amplitude_correction,
                'point_count': len(interval.points)
            }

            # Добавляем оцифрованные данные, если они есть
            if self.project:
                time, amplitude = self.project.get_digitized_data(interval.id, trace.id)
                if time is not None and amplitude is not None:
                    if format == 'numpy':
                        interval_data['time'] = time
                        interval_data['amplitude'] = amplitude
                    elif format == 'list':
                        interval_data['time'] = time.tolist()
                        interval_data['amplitude'] = amplitude.tolist()
                    elif format == 'dict':
                        interval_data['data'] = [
                            {'t': float(t), 'a': float(a)}
                            for t, a in zip(time, amplitude)
                        ]

            data['intervals'].append(interval_data)

        return data

    def find_intervals_by_type(self, trace: SeismicTrace,
                               interval_type: str) -> List[DigitizationInterval]:
        """
        Находит все интервалы указанного типа в трассе.

        Args:
            trace: Трасса
            interval_type: Тип интервала

        Returns:
            List[DigitizationInterval]: Список интервалов
        """
        return [interval for interval in trace.intervals
                if interval.type == interval_type]

    def get_trace_time_range(self, trace: SeismicTrace) -> Tuple[float, float]:
        """
        Возвращает временной диапазон трассы.

        Args:
            trace: Трасса

        Returns:
            Tuple: (начальное время, конечное время)
        """
        if not self.project:
            return 0.0, 1.0

        all_times = []
        for interval in trace.intervals:
            time, _ = self.project.get_digitized_data(interval.id, trace.id)
            if time is not None and len(time) > 0:
                all_times.extend([time[0], time[-1]])

        if not all_times:
            return self.project.settings.time_start, self.project.settings.time_end

        return min(all_times), max(all_times)
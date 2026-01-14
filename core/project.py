# Главное ядро проекта

import json
import pickle
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

from models.raster_data import SeismogramRaster
from models.seismic_data import SeismicTrace, DigitizationInterval
from models.workspace_params import WorkspaceSettings


@dataclass
class DigitizationProject:
    """Проект оцифровки (*.trace)."""

    project_path: Optional[Path] = None
    raster: Optional[SeismogramRaster] = None
    traces: List[SeismicTrace] = field(default_factory=list)
    loose_intervals: List[DigitizationInterval] = field(default_factory=list)
    settings: WorkspaceSettings = field(default_factory=WorkspaceSettings)

    # Метаданные проекта
    name: str = "Новый проект"
    description: str = ""
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_date: str = field(default_factory=lambda: datetime.now().isoformat())
    author: str = ""
    version: str = "1.0"

    # Статистика
    digitization_time: float = 0.0  # Время, затраченное на оцифровку (часы)
    total_points: int = 0
    total_intervals: int = 0

    def __post_init__(self):
        """Инициализация после создания."""
        if not self.name:
            self.name = f"Проект {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # --- Методы сериализации ---
    def save(self, filepath: Path):
        """Сохраняет проект в файл."""
        self.modified_date = datetime.now().isoformat()
        self.project_path = filepath

        # Подготавливаем данные для сохранения
        data = {
            'metadata': {
                'name': self.name,
                'description': self.description,
                'created_date': self.created_date,
                'modified_date': self.modified_date,
                'author': self.author,
                'version': self.version,
                'digitization_time': self.digitization_time,
                'total_points': self.total_points,
                'total_intervals': self.total_intervals
            },
            'raster_info': {
                'path': str(self.raster.image_path) if self.raster else None,
                'dpi': self.raster.dpi if self.raster else (300, 300),
                'color_mode': self.raster.color_mode if self.raster else 'L',
                'metadata': self.raster.metadata if self.raster else {}
            },
            'traces': self._serialize_traces(self.traces),
            'loose_intervals': self._serialize_intervals(self.loose_intervals),
            'settings': asdict(self.settings)
        }

        try:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            return True
        except Exception as e:
            print(f"Ошибка сохранения проекта: {e}")
            return False

    @classmethod
    def load(cls, filepath: Path) -> 'DigitizationProject':
        """Загружает проект из файла."""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)

            # Создаем проект
            project = cls(project_path=filepath)

            # Восстанавливаем метаданные
            metadata = data.get('metadata', {})
            project.name = metadata.get('name', 'Загруженный проект')
            project.description = metadata.get('description', '')
            project.created_date = metadata.get('created_date', datetime.now().isoformat())
            project.modified_date = metadata.get('modified_date', datetime.now().isoformat())
            project.author = metadata.get('author', '')
            project.version = metadata.get('version', '1.0')
            project.digitization_time = metadata.get('digitization_time', 0.0)
            project.total_points = metadata.get('total_points', 0)
            project.total_intervals = metadata.get('total_intervals', 0)

            # Восстанавливаем информацию о растре
            ri = data.get('raster_info', {})
            if ri.get('path'):
                project.raster = SeismogramRaster(
                    image_path=ri['path'],
                    dpi=ri.get('dpi', (300, 300)),
                    color_mode=ri.get('color_mode', 'L'),
                    metadata=ri.get('metadata', {})
                )

            # Восстанавливаем трассы и интервалы
            project.traces = cls._deserialize_traces(data.get('traces', []))
            project.loose_intervals = cls._deserialize_intervals(data.get('loose_intervals', []))

            # Восстанавливаем настройки
            settings_data = data.get('settings', {})
            project.settings = WorkspaceSettings(**settings_data)

            return project

        except Exception as e:
            print(f"Ошибка загрузки проекта: {e}")
            raise

    def _serialize_traces(self, traces: List[SeismicTrace]) -> List[Dict]:
        """Сериализует список трасс."""
        serialized = []
        for trace in traces:
            trace_dict = asdict(trace)
            trace_dict['intervals'] = self._serialize_intervals(trace.intervals)
            serialized.append(trace_dict)
        return serialized

    def _serialize_intervals(self, intervals: List[DigitizationInterval]) -> List[Dict]:
        """Сериализует список интервалов."""
        serialized = []
        for interval in intervals:
            interval_dict = asdict(interval)

            # Сериализуем точки
            points_data = []
            for point in interval.points:
                points_data.append({
                    'x_px': point.x_px,
                    'y_px': point.y_px,
                    't_val': point.t_val,
                    'a_val': point.a_val
                })
            interval_dict['points'] = points_data

            # Сериализуем интерполированные точки
            if interval.interpolated_points is not None:
                interval_dict['interpolated_points'] = interval.interpolated_points.tolist()

            serialized.append(interval_dict)
        return serialized

    @staticmethod
    def _deserialize_traces(data: List[Dict]) -> List[SeismicTrace]:
        """Десериализует список трасс."""
        traces = []
        for trace_data in data:
            # Восстанавливаем интервалы
            intervals_data = trace_data.pop('intervals', [])
            intervals = DigitizationProject._deserialize_intervals(intervals_data)

            # Создаем трассу
            trace = SeismicTrace(**trace_data)
            trace.intervals = intervals
            traces.append(trace)
        return traces

    @staticmethod
    def _deserialize_intervals(data: List[Dict]) -> List[DigitizationInterval]:
        """Десериализует список интервалов."""
        intervals = []
        for interval_data in data:
            # Восстанавливаем точки
            points_data = interval_data.pop('points', [])
            points = []
            for point_data in points_data:
                from models.seismic_data import DigitizationPoint
                points.append(DigitizationPoint(**point_data))

            # Восстанавливаем интерполированные точки
            interpolated_data = interval_data.pop('interpolated_points', None)
            interpolated_points = None
            if interpolated_data is not None:
                interpolated_points = np.array(interpolated_data)

            # Создаем интервал
            from models.seismic_data import DigitizationInterval
            interval = DigitizationInterval(**interval_data)
            interval.points = points
            interval.interpolated_points = interpolated_points
            intervals.append(interval)
        return intervals

    # --- Методы управления проектом ---
    def add_trace(self, trace: SeismicTrace) -> str:
        """Добавляет трассу в проект."""
        self.traces.append(trace)
        self.total_intervals += len(trace.intervals)
        self.total_points += sum(len(interval.points) for interval in trace.intervals)
        return trace.id

    def remove_trace(self, trace_id: str) -> bool:
        """Удаляет трассу из проекта."""
        for i, trace in enumerate(self.traces):
            if trace.id == trace_id:
                # Обновляем статистику
                self.total_intervals -= len(trace.intervals)
                self.total_points -= sum(len(interval.points) for interval in trace.intervals)

                self.traces.pop(i)
                return True
        return False

    def find_trace_by_id(self, trace_id: str) -> Optional[SeismicTrace]:
        """Находит трассу по ID."""
        for trace in self.traces:
            if trace.id == trace_id:
                return trace
        return None

    def find_interval_by_id(self, interval_id: str) -> Tuple[Optional[DigitizationInterval], Optional[str]]:
        """
        Находит интервал по ID.

        Returns:
            (interval, trace_id): Интервал и ID трассы (None если свободный интервал)
        """
        # Ищем в трассах
        for trace in self.traces:
            for interval in trace.intervals:
                if interval.id == interval_id:
                    return interval, trace.id

        # Ищем в свободных интервалах
        for interval in self.loose_intervals:
            if interval.id == interval_id:
                return interval, None

        return None, None

    # --- Методы обработки данных ---
    def interpolate_all_intervals(self) -> Dict[str, bool]:
        """Интерполирует все интервалы в проекте."""
        results = {}

        # Интервалы в трассах
        for trace in self.traces:
            for interval in trace.intervals:
                success = self._interpolate_interval(interval)
                results[f"{trace.id}/{interval.id}"] = success

        # Свободные интервалы
        for interval in self.loose_intervals:
            success = self._interpolate_interval(interval)
            results[interval.id] = success

        return results

    def _interpolate_interval(self, interval: DigitizationInterval) -> bool:
        """Интерполирует один интервал."""
        if len(interval.points) < 2:
            return False

        try:
            from utils.interpolation import interpolate_points

            x_interp, y_interp = interpolate_points(
                interval.points,
                polynomial_order=interval.polynomial_order,
                num_samples=100,
                use_spline=True
            )

            interval.interpolated_points = np.column_stack((x_interp, y_interp))
            return True

        except Exception as e:
            print(f"Ошибка интерполяции интервала {interval.id}: {e}")
            return False

    def get_digitized_data(self, interval_id: str, trace_id: str = None) -> Tuple[
        Optional[np.ndarray], Optional[np.ndarray]]:
        """Возвращает оцифрованные данные интервала."""
        interval, found_trace_id = self.find_interval_by_id(interval_id)

        if not interval:
            return None, None

        if trace_id is not None and found_trace_id != trace_id:
            return None, None

        try:
            from utils.interpolation import regular_digitization

            # Определяем временной интервал
            time_start = self.settings.time_start
            time_end = self.settings.time_end

            # Получаем регулярно оцифрованные данные
            time, amplitude = regular_digitization(
                interval.points,
                time_start=time_start,
                time_end=time_end,
                sampling_rate=self.settings.export_sampling_rate,
                polynomial_order=interval.polynomial_order
            )

            # Применяем поправки
            time += interval.time_correction
            amplitude += interval.amplitude_correction

            return time, amplitude

        except Exception as e:
            print(f"Ошибка получения данных интервала {interval_id}: {e}")
            return None, None

    def export_data(self, output_dir: Path, format: str = 'SAC',
                    selected_items: List = None) -> Dict[str, bool]:
        """
        Экспортирует данные проекта.

        Args:
            output_dir: Директория для сохранения
            format: Формат экспорта
            selected_items: Список выбранных элементов для экспорта

        Returns:
            Dict: Результаты экспорта
        """
        from utils.file_io import export_multiple_traces, generate_metadata_from_project

        traces_to_export = []

        # Подготавливаем данные для экспорта
        if selected_items:
            for item in selected_items:
                item_type = item[0]

                if item_type == 'trace':
                    trace_id = item[1]
                    trace = self.find_trace_by_id(trace_id)
                    if trace:
                        for interval in trace.intervals:
                            time, amplitude = self.get_digitized_data(interval.id, trace_id)
                            if time is not None and amplitude is not None:
                                metadata = generate_metadata_from_project({
                                    'station': trace.name,
                                    'channel': f'TR{trace.id}'
                                })
                                traces_to_export.append({
                                    'name': f"{trace.name}_{interval.id}",
                                    'time': time,
                                    'amplitude': amplitude,
                                    'metadata': metadata
                                })

                elif item_type == 'interval':
                    trace_id, interval_id = item[1], item[2]
                    time, amplitude = self.get_digitized_data(interval_id, trace_id)
                    if time is not None and amplitude is not None:
                        trace = self.find_trace_by_id(trace_id)
                        station = trace.name if trace else 'UNKNOWN'
                        metadata = generate_metadata_from_project({
                            'station': station,
                            'channel': f'INT{interval_id[:4]}'
                        })
                        traces_to_export.append({
                            'name': f"{station}_{interval_id}",
                            'time': time,
                            'amplitude': amplitude,
                            'metadata': metadata
                        })

                elif item_type == 'loose_interval':
                    interval_id = item[1]
                    time, amplitude = self.get_digitized_data(interval_id)
                    if time is not None and amplitude is not None:
                        metadata = generate_metadata_from_project({
                            'station': 'LOOSE',
                            'channel': f'INT{interval_id[:4]}'
                        })
                        traces_to_export.append({
                            'name': f"loose_{interval_id}",
                            'time': time,
                            'amplitude': amplitude,
                            'metadata': metadata
                        })

        # Экспортируем
        if traces_to_export:
            return export_multiple_traces(
                traces_to_export,
                str(output_dir),
                format,
                base_name=self.name.replace(' ', '_')
            )

        return {}

    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику проекта."""
        total_trace_intervals = sum(len(trace.intervals) for trace in self.traces)
        total_trace_points = sum(len(interval.points) for trace in self.traces
                                 for interval in trace.intervals)

        total_loose_points = sum(len(interval.points) for interval in self.loose_intervals)

        return {
            'name': self.name,
            'traces_count': len(self.traces),
            'loose_intervals_count': len(self.loose_intervals),
            'total_intervals': total_trace_intervals + len(self.loose_intervals),
            'total_points': total_trace_points + total_loose_points,
            'digitization_time_hours': self.digitization_time,
            'created_date': self.created_date,
            'modified_date': self.modified_date,
            'author': self.author,
            'raster_loaded': self.raster is not None
        }

    def validate(self) -> Tuple[bool, List[str]]:
        """Проверяет целостность проекта."""
        errors = []

        # Проверяем трассы
        trace_ids = set()
        for trace in self.traces:
            if trace.id in trace_ids:
                errors.append(f"Дублирующийся ID трассы: {trace.id}")
            trace_ids.add(trace.id)

            # Проверяем интервалы трассы
            interval_ids = set()
            for interval in trace.intervals:
                if interval.id in interval_ids:
                    errors.append(f"Дублирующийся ID интервала в трассе {trace.id}: {interval.id}")
                interval_ids.add(interval.id)

        # Проверяем свободные интервалы
        loose_interval_ids = set()
        for interval in self.loose_intervals:
            if interval.id in loose_interval_ids:
                errors.append(f"Дублирующийся ID свободного интервала: {interval.id}")
            loose_interval_ids.add(interval.id)

        # Проверяем настройки
        if self.settings.time_end <= self.settings.time_start:
            errors.append("Время конца должно быть больше времени начала")

        return len(errors) == 0, errors
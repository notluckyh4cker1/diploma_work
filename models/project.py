from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
import json
import zipfile
import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from models.trace import Trace

@dataclass
class Project:
    name: str
    filepath: Optional[Path] = None
    raster_path: Optional[Path] = None
    raster_data: Optional[np.ndarray] = None
    traces: List = field(default_factory=list)
    workspace_settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def add_trace(self, trace):
        trace.project = self
        self.traces.append(trace)
        self.modified_at = datetime.now()

    def remove_trace(self, trace_id: str):
        """Удалить трассу по ID"""
        for i, trace in enumerate(self.traces):
            if trace.id == trace_id:
                # Очищаем данные трассы перед удалением
                if hasattr(trace, 'clear'):
                    trace.clear()
                # Удаляем из списка
                self.traces.pop(i)
                self.modified_at = datetime.now()
                return

    def get_trace(self, trace_id: str) -> Optional:
        for trace in self.traces:
            if trace.id == trace_id:
                return trace
        return None

    def save(self, filepath: Optional[Path] = None):
        """Сохранить проект в .trace файл"""
        save_path = filepath or self.filepath
        if not save_path:
            raise ValueError("No filepath specified")

        with zipfile.ZipFile(save_path, 'w') as zf:
            traces_data = []
            for trace in self.traces:
                trace_data = {
                    'id': trace.id,
                    'name': trace.name,
                    'raster_coords': trace.raster_coords,
                    'time_calibration': trace.time_calibration,
                    'amplitude_calibration': trace.amplitude_calibration,
                    'metadata': trace.metadata,
                    'is_visible': trace.is_visible,
                    'intervals': []
                }

                for interval in trace.intervals:
                    interval_data = {
                        'id': interval.id,
                        'trace_id': interval.trace_id,
                        'points': [(p.x, p.y, p.point_type.value) for p in interval.points],
                        'interpolation_type': interval.interpolation_type.value,
                        'color': interval.color,
                        'is_noise': interval.is_noise,
                        'notes': interval.notes
                    }
                    trace_data['intervals'].append(interval_data)

                traces_data.append(trace_data)

            project_data = {
                'name': self.name,
                'raster_path': str(self.raster_path) if self.raster_path else None,
                'traces': traces_data,
                'workspace_settings': self.workspace_settings,
                'created_at': self.created_at.isoformat(),
                'modified_at': self.modified_at.isoformat()
            }
            zf.writestr('project.json', json.dumps(project_data, indent=2))

            if self.raster_data is not None:
                img = Image.fromarray(self.raster_data)
                img.save(zf.open('raster.png', 'w'), 'PNG')

        self.filepath = save_path

    @classmethod
    def load(cls, filepath: Path) -> 'Project':
        """Загрузить проект из .trace файла"""
        with zipfile.ZipFile(filepath, 'r') as zf:
            project_data = json.loads(zf.read('project.json'))

            raster_data = None
            if 'raster.png' in zf.namelist():
                with zf.open('raster.png') as img_file:
                    img = Image.open(img_file)
                    raster_data = np.array(img)

            project = cls(
                name=project_data['name'],
                filepath=filepath,
                raster_data=raster_data,
                workspace_settings=project_data.get('workspace_settings', {})
            )

            from models.trace import Trace, Interval, Point2D, PointType, InterpolationType

            for trace_data in project_data.get('traces', []):
                trace = Trace(
                    id=trace_data['id'],
                    name=trace_data['name'],
                    raster_coords=tuple(tuple(coord) for coord in trace_data['raster_coords']),
                    time_calibration=trace_data.get('time_calibration'),
                    amplitude_calibration=trace_data.get('amplitude_calibration'),
                    metadata=trace_data.get('metadata', {}),
                    is_visible=trace_data.get('is_visible', True)
                )
                trace.project = project

                for interval_data in trace_data.get('intervals', []):
                    interval = Interval(
                        id=interval_data['id'],
                        trace_id=interval_data['trace_id'],
                        points=[],
                        interpolation_type=InterpolationType(interval_data['interpolation_type']),
                        color=interval_data['color'],
                        is_noise=interval_data['is_noise'],
                        notes=interval_data['notes']
                    )

                    for x, y, ptype in interval_data['points']:
                        interval.points.append(Point2D(x, y, PointType(ptype)))

                    trace.intervals.append(interval)

                project.traces.append(trace)

            return project

    def clear(self):
        """Очистить проект от всех данных"""
        for trace in self.traces:
            trace.intervals.clear()
        self.traces.clear()
        self.raster_data = None
        import gc
        gc.collect()
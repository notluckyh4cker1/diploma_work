"""
Утилиты для импорта/экспорта данных в различные форматы.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import warnings

try:
    from obspy import Stream, Trace, UTCDateTime
    from obspy.io.sac import SACTrace

    HAS_OBSPY = True
except ImportError:
    HAS_OBSPY = False
    warnings.warn("ObsPy не установлен. Экспорт в SAC/MiniSEED недоступен.")


def export_to_sac(time: np.ndarray, amplitude: np.ndarray,
                  output_path: str, metadata: Dict[str, Any] = None,
                  little_endian: bool = True) -> bool:
    """
    Экспортирует данные в формат SAC.

    Args:
        time: Временные метки (секунды)
        amplitude: Амплитуды
        output_path: Путь для сохранения файла
        metadata: Метаданные для заголовка SAC
        little_endian: Использовать little-endian формат

    Returns:
        bool: Успешность экспорта
    """
    if not HAS_OBSPY:
        warnings.warn("ObsPy не установлен. Экспорт в SAC недоступен.")
        return False

    try:
        # Создаем трассу ObsPy
        sampling_rate = 1.0 / np.mean(np.diff(time)) if len(time) > 1 else 1.0
        starttime = UTCDateTime(metadata.get('starttime', '2000-01-01T00:00:00'))

        trace = Trace(data=amplitude, header={
            'sampling_rate': sampling_rate,
            'starttime': starttime,
            'npts': len(amplitude),
            'calib': metadata.get('calib', 1.0),
            'station': metadata.get('station', 'STA'),
            'network': metadata.get('network', 'XX'),
            'location': metadata.get('location', ''),
            'channel': metadata.get('channel', 'BHZ')
        })

        # Создаем SAC трассу
        sac_trace = SACTrace.from_obspy_trace(trace)

        # Заполняем дополнительные поля SAC заголовка
        if metadata:
            for key, value in metadata.items():
                if hasattr(sac_trace, key):
                    try:
                        setattr(sac_trace, key, value)
                    except:
                        pass

        # Сохраняем файл
        sac_trace.write(output_path, byteorder='little' if little_endian else 'big')
        return True

    except Exception as e:
        print(f"Ошибка экспорта в SAC: {e}")
        return False


def export_to_miniseed(time: np.ndarray, amplitude: np.ndarray,
                       output_path: str, metadata: Dict[str, Any] = None,
                       encoding: str = 'STEIM2', record_length: int = 512) -> bool:
    """
    Экспортирует данные в формат MiniSEED.

    Args:
        time: Временные метки (секунды)
        amplitude: Амплитуды
        output_path: Путь для сохранения файла
        metadata: Метаданные для заголовка
        encoding: Кодирование ('STEIM1', 'STEIM2', 'INT32', 'FLOAT32')
        record_length: Длина записи в байтах

    Returns:
        bool: Успешность экспорта
    """
    if not HAS_OBSPY:
        warnings.warn("ObsPy не установлен. Экспорт в MiniSEED недоступен.")
        return False

    try:
        # Создаем трассу ObsPy
        sampling_rate = 1.0 / np.mean(np.diff(time)) if len(time) > 1 else 1.0
        starttime = UTCDateTime(metadata.get('starttime', '2000-01-01T00:00:00'))

        trace = Trace(data=amplitude, header={
            'sampling_rate': sampling_rate,
            'starttime': starttime,
            'npts': len(amplitude),
            'station': metadata.get('station', 'STA'),
            'network': metadata.get('network', 'XX'),
            'location': metadata.get('location', ''),
            'channel': metadata.get('channel', 'BHZ')
        })

        # Создаем поток и сохраняем в MiniSEED
        stream = Stream([trace])
        stream.write(output_path, format='MSEED',
                     encoding=encoding, reclen=record_length)
        return True

    except Exception as e:
        print(f"Ошибка экспорта в MiniSEED: {e}")
        return False


def export_to_csv(time: np.ndarray, amplitude: np.ndarray,
                  output_path: str, delimiter: str = ',',
                  header: bool = True) -> bool:
    """
    Экспортирует данные в CSV файл.

    Args:
        time: Временные метки
        amplitude: Амплитуды
        output_path: Путь для сохранения файла
        delimiter: Разделитель
        header: Включать заголовок

    Returns:
        bool: Успешность экспорта
    """
    try:
        # Проверяем одинаковую длину массивов
        if len(time) != len(amplitude):
            print("Длины массивов времени и амплитуды не совпадают")
            return False

        # Сохраняем в CSV
        data = np.column_stack((time, amplitude))
        header_line = f"time{delimiter}amplitude\n" if header else ""

        np.savetxt(output_path, data, delimiter=delimiter,
                   header=header_line if header else '',
                   comments='')
        return True

    except Exception as e:
        print(f"Ошибка экспорта в CSV: {e}")
        return False


def export_to_numpy(time: np.ndarray, amplitude: np.ndarray,
                    output_path: str, metadata: Dict[str, Any] = None) -> bool:
    """
    Экспортирует данные в бинарный формат NumPy.

    Args:
        time: Временные метки
        amplitude: Амплитуды
        output_path: Путь для сохранения файла
        metadata: Метаданные

    Returns:
        bool: Успешность экспорта
    """
    try:
        # Сохраняем данные и метаданные
        data_dict = {
            'time': time,
            'amplitude': amplitude,
            'metadata': metadata or {}
        }

        np.save(output_path, data_dict, allow_pickle=True)
        return True

    except Exception as e:
        print(f"Ошибка экспорта в NumPy формат: {e}")
        return False


def export_to_matlab(time: np.ndarray, amplitude: np.ndarray,
                     output_path: str, variable_name: str = 'seismic_data') -> bool:
    """
    Экспортирует данные в формат MATLAB (.mat).

    Args:
        time: Временные метки
        amplitude: Амплитуды
        output_path: Путь для сохранения файла
        variable_name: Имя переменной в файле .mat

    Returns:
        bool: Успешность экспорта
    """
    try:
        import scipy.io as sio

        # Создаем структуру данных
        data = {
            'time': time,
            'amplitude': amplitude,
            'sampling_rate': 1.0 / np.mean(np.diff(time)) if len(time) > 1 else 1.0
        }

        # Сохраняем в .mat файл
        sio.savemat(output_path, {variable_name: data})
        return True

    except ImportError:
        warnings.warn("SciPy не установлен. Экспорт в MATLAB формат недоступен.")
        return False
    except Exception as e:
        print(f"Ошибка экспорта в MATLAB формат: {e}")
        return False


def export_multiple_traces(traces: List[Dict[str, Any]],
                           output_dir: str,
                           format: str = 'SAC',
                           base_name: str = 'trace') -> Dict[str, bool]:
    """
    Экспортирует несколько трасс одновременно.

    Args:
        traces: Список словарей с данными трасс
        output_dir: Директория для сохранения
        format: Формат экспорта ('SAC', 'MiniSEED', 'CSV', 'NPY', 'MAT')
        base_name: Базовое имя файлов

    Returns:
        Dict: Результаты экспорта для каждой трассы
    """
    results = {}
    output_path = Path(output_dir)

    for i, trace_data in enumerate(traces):
        time = trace_data.get('time')
        amplitude = trace_data.get('amplitude')
        metadata = trace_data.get('metadata', {})
        name = trace_data.get('name', f'{base_name}_{i:03d}')

        if time is None or amplitude is None:
            results[name] = False
            continue

        # Формируем имя файла
        if format == 'SAC':
            filename = output_path / f'{name}.sac'
            success = export_to_sac(time, amplitude, str(filename), metadata)
        elif format == 'MiniSEED':
            filename = output_path / f'{name}.mseed'
            success = export_to_miniseed(time, amplitude, str(filename), metadata)
        elif format == 'CSV':
            filename = output_path / f'{name}.csv'
            success = export_to_csv(time, amplitude, str(filename))
        elif format == 'NPY':
            filename = output_path / f'{name}.npy'
            success = export_to_numpy(time, amplitude, str(filename), metadata)
        elif format == 'MAT':
            filename = output_path / f'{name}.mat'
            success = export_to_matlab(time, amplitude, str(filename))
        else:
            print(f"Неизвестный формат: {format}")
            success = False

        results[name] = success

    return results


def generate_metadata_from_project(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Генерирует метаданные для экспорта из данных проекта.

    Args:
        project_data: Данные проекта

    Returns:
        Dict: Метаданные для экспорта
    """
    metadata = {
        'starttime': '2000-01-01T00:00:00',
        'station': project_data.get('station', 'STA'),
        'network': project_data.get('network', 'XX'),
        'location': project_data.get('location', ''),
        'channel': project_data.get('channel', 'BHZ'),
        'calib': project_data.get('calibration', 1.0),
        'units': project_data.get('units', 'counts'),
        'latitude': project_data.get('latitude', 0.0),
        'longitude': project_data.get('longitude', 0.0),
        'elevation': project_data.get('elevation', 0.0),
        'depth': project_data.get('depth', 0.0),
        'azimuth': project_data.get('azimuth', 0.0),
        'dip': project_data.get('dip', -90.0),
        'scale': project_data.get('scale', 1.0)
    }

    # Добавляем пользовательские поля
    if 'custom_metadata' in project_data:
        metadata.update(project_data['custom_metadata'])

    return metadata
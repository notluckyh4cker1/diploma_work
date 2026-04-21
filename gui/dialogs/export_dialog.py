from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QComboBox, QSpinBox,
                             QDoubleSpinBox, QGroupBox, QFormLayout, QCheckBox,
                             QTreeWidget, QTreeWidgetItem, QTabWidget, QWidget,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
import numpy as np
import os

# Добавляем импорт scipy с обработкой ошибки
try:
    from scipy import interpolate

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Предупреждение: scipy не установлен. Интерполяция будет недоступна.")


class ExportDialog(QDialog):
    """Диалог экспорта данных в различные форматы."""

    def __init__(self, parent=None, format_type='SAC'):
        super().__init__(parent)
        self.main_window = parent
        self.format_type = format_type
        self.selected_items = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Экспорт данных - {self.format_type}")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)

        # Вкладки
        self.tab_widget = QTabWidget()

        # Вкладка выбора данных
        self.selection_tab = QWidget()
        self.init_selection_tab()
        self.tab_widget.addTab(self.selection_tab, "Выбор данных")

        # Вкладка параметров экспорта
        self.settings_tab = QWidget()
        self.init_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Параметры")

        # Вкладка предпросмотра
        self.preview_tab = QWidget()
        self.init_preview_tab()
        self.tab_widget.addTab(self.preview_tab, "Предпросмотр")

        layout.addWidget(self.tab_widget)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.export_btn = QPushButton("Экспорт")
        self.export_btn.clicked.connect(self.do_export)
        btn_layout.addWidget(self.export_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def init_selection_tab(self):
        layout = QVBoxLayout(self.selection_tab)

        # Дерево элементов для выбора
        self.selection_tree = QTreeWidget()
        self.selection_tree.setHeaderLabels(["Элемент", "Тип", "Точек", "Интервалов"])
        self.selection_tree.setSelectionMode(QTreeWidget.MultiSelection)
        self.selection_tree.itemChanged.connect(self.on_item_changed)
        self.selection_tree.itemClicked.connect(self.on_item_clicked)

        layout.addWidget(QLabel("Выберите элементы для экспорта:"))
        layout.addWidget(self.selection_tree)

        # Кнопки выбора
        btn_layout = QHBoxLayout()

        self.select_all_btn = QPushButton("Выбрать все")
        self.select_all_btn.clicked.connect(self.select_all)
        btn_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Снять все")
        self.select_none_btn.clicked.connect(self.select_none)
        btn_layout.addWidget(self.select_none_btn)

        layout.addLayout(btn_layout)

        self.load_project_items()

    def init_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)

        # Общие настройки
        general_group = QGroupBox("Общие настройки")
        form_layout = QFormLayout()

        self.sampling_rate_spin = QDoubleSpinBox()
        self.sampling_rate_spin.setRange(1.0, 10000.0)
        self.sampling_rate_spin.setValue(100.0)
        self.sampling_rate_spin.setSuffix(" Гц")
        form_layout.addRow("Частота дискретизации:", self.sampling_rate_spin)

        self.time_start_spin = QDoubleSpinBox()
        self.time_start_spin.setRange(-1e6, 1e6)
        self.time_start_spin.setValue(0.0)
        self.time_start_spin.setSuffix(" с")
        form_layout.addRow("Начало времени:", self.time_start_spin)

        self.units_combo = QComboBox()
        self.units_combo.addItems(["counts", "m/s", "m/s²", "nm", "custom"])
        form_layout.addRow("Единицы измерения:", self.units_combo)

        self.custom_units_edit = QLineEdit()
        self.custom_units_edit.setPlaceholderText("Пользовательские единицы")
        self.custom_units_edit.setEnabled(False)
        form_layout.addRow("", self.custom_units_edit)

        self.units_combo.currentTextChanged.connect(
            lambda t: self.custom_units_edit.setEnabled(t == "custom")
        )

        self.raw_points_cb = QCheckBox("Экспортировать только сырые точки (без интерполяции)")
        form_layout.addRow("", self.raw_points_cb)

        general_group.setLayout(form_layout)
        layout.addWidget(general_group)

        # Настройки обработки
        processing_group = QGroupBox("Обработка данных")
        processing_layout = QVBoxLayout()

        self.remove_trend_cb = QCheckBox("Удалить тренд")
        processing_layout.addWidget(self.remove_trend_cb)

        trend_layout = QHBoxLayout()
        trend_layout.addWidget(QLabel("Порядок полинома:"))
        self.detrend_order_spin = QSpinBox()
        self.detrend_order_spin.setRange(1, 5)
        self.detrend_order_spin.setValue(1)
        trend_layout.addWidget(self.detrend_order_spin)
        processing_layout.addLayout(trend_layout)

        self.normalize_cb = QCheckBox("Нормализовать амплитуду")
        processing_layout.addWidget(self.normalize_cb)

        norm_layout = QHBoxLayout()
        norm_layout.addWidget(QLabel("Метод:"))
        self.normalize_combo = QComboBox()
        self.normalize_combo.addItems(["zscore", "minmax", "rms"])
        norm_layout.addWidget(self.normalize_combo)
        processing_layout.addLayout(norm_layout)

        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)

        # Настройки формата
        format_group = QGroupBox(f"Настройки {self.format_type}")
        format_layout = QVBoxLayout()

        if self.format_type == 'SAC':
            self.sac_little_endian_cb = QCheckBox("Little-endian формат")
            format_layout.addWidget(self.sac_little_endian_cb)

        elif self.format_type == 'MiniSEED':
            self.mseed_encoding_combo = QComboBox()
            self.mseed_encoding_combo.addItems(["STEIM1", "STEIM2", "INT32", "FLOAT32"])
            format_layout.addWidget(QLabel("Кодирование:"))
            format_layout.addWidget(self.mseed_encoding_combo)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        layout.addStretch()

    def init_preview_tab(self):
        """Вкладка предпросмотра данных"""
        layout = QVBoxLayout(self.preview_tab)

        self.preview_label = QLabel("Выберите элемент для предпросмотра")
        self.preview_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.preview_label)

        self.preview_text = QLabel()
        self.preview_text.setWordWrap(True)
        self.preview_text.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 10px;
                font-family: monospace;
                border: 1px solid #ccc;
            }
        """)
        layout.addWidget(self.preview_text)

    def load_project_items(self):
        """Загружает элементы проекта в дерево выбора."""
        self.selection_tree.clear()

        if not self.main_window or not self.main_window.current_project:
            return

        project = self.main_window.current_project

        # Добавляем трассы
        for trace in project.traces:
            # Подсчитываем только интервалы с точками
            intervals_with_points = [i for i in trace.intervals if i.points]
            total_points = sum(len(i.points) for i in trace.intervals if i.points)

            trace_item = QTreeWidgetItem(self.selection_tree)
            trace_item.setText(0, trace.name)
            trace_item.setText(1, "Трасса")
            trace_item.setText(2, str(total_points))
            trace_item.setText(3, str(len(intervals_with_points)))  # Только интервалы с точками
            trace_item.setData(0, Qt.UserRole, ("trace", trace.id, trace.name))
            trace_item.setCheckState(0, Qt.Unchecked)

            # Добавляем ТОЛЬКО интервалы с точками
            for interval in intervals_with_points:  # Используем отфильтрованный список
                if not interval.points:  # Дополнительная проверка
                    continue

                interval_item = QTreeWidgetItem(trace_item)
                interval_item.setText(0, f"Интервал {interval.id[:8]}")
                interval_item.setText(1, "Волновая форма")
                interval_item.setText(2, str(len(interval.points)))
                interval_item.setText(3, "1")
                interval_item.setData(0, Qt.UserRole, ("interval", trace.id, interval.id, trace.name))
                interval_item.setCheckState(0, Qt.Unchecked)

        self.selection_tree.expandAll()

    def on_item_changed(self, item, column):
        """Обработка изменения состояния элемента."""
        if column != 0:
            return

        # Обновляем состояние дочерних элементов
        if item.childCount() > 0:
            state = item.checkState(0)
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, state)

    def on_item_clicked(self, item, column):
        """Показывает предпросмотр выбранного элемента"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data[0]

        if item_type == "trace":
            trace_id = data[1]
            trace_name = data[2]
            self.show_trace_preview(trace_id, trace_name)
        elif item_type == "interval":
            trace_id = data[1]
            interval_id = data[2]
            trace_name = data[3]
            self.show_interval_preview(trace_id, interval_id, trace_name)

    def show_trace_preview(self, trace_id, trace_name):
        """Показать предпросмотр трассы"""
        project = self.main_window.current_project
        trace = project.get_trace(trace_id)

        if not trace:
            return

        # Подсчитываем только интервалы с точками
        intervals_with_points = [i for i in trace.intervals if i.points]
        total_points = sum(len(i.points) for i in trace.intervals if i.points)
        total_intervals = len(intervals_with_points)

        preview_text = f"""
        <b>Трасса: {trace_name}</b><br>
        <br>
        <b>Статистика:</b><br>
        • Интервалов: {total_intervals}<br>
        • Всего точек: {total_points}<br>
        <br>
        <b>Интервалы:</b><br>
        """

        # Показываем только интервалы с точками
        for i, interval in enumerate(intervals_with_points):
            points = interval.points
            if points:
                x_vals = [p.x for p in points]
                y_vals = [p.y for p in points]
                preview_text += f"  Интервал {i + 1}: {len(points)} точек, X: [{min(x_vals):.1f}, {max(x_vals):.1f}], Y: [{min(y_vals):.1f}, {max(y_vals):.1f}]<br>"

        if total_intervals == 0:
            preview_text += "  Нет интервалов с точками<br>"

        self.preview_label.setText(f"Предпросмотр: {trace_name}")
        self.preview_text.setText(preview_text)

    def show_interval_preview(self, trace_id, interval_id, trace_name):
        """Показать предпросмотр интервала"""
        project = self.main_window.current_project
        trace = project.get_trace(trace_id)

        if not trace:
            return

        interval = None
        for inv in trace.intervals:
            if inv.id == interval_id:
                interval = inv
                break

        if not interval or not interval.points:
            self.preview_text.setText("Нет данных для предпросмотра")
            return

        points = interval.points
        x_vals = [p.x for p in points]
        y_vals = [p.y for p in points]

        preview_text = f"""
        <b>Трасса:</b> {trace_name}<br>
        <b>Интервал:</b> {interval.id[:8]}<br>
        <br>
        <b>Статистика точек:</b><br>
        • Всего точек: {len(points)}<br>
        • X (пиксели): min={min(x_vals):.1f}, max={max(x_vals):.1f}<br>
        • Y (пиксели): min={min(y_vals):.1f}, max={max(y_vals):.1f}<br>
        <br>
        <b>Первые 5 точек:</b><br>
        """

        for i, point in enumerate(points[:5]):
            preview_text += f"  {i + 1}: ({point.x:.1f}, {point.y:.1f})<br>"

        if len(points) > 5:
            preview_text += f"  ... и еще {len(points) - 5} точек<br>"

        self.preview_label.setText(f"Предпросмотр: интервал {interval.id[:8]}")
        self.preview_text.setText(preview_text)

    def select_all(self):
        """Выбирает все элементы."""
        self.set_all_checkstates(Qt.Checked)

    def select_none(self):
        """Снимает выбор со всех элементов."""
        self.set_all_checkstates(Qt.Unchecked)

    def set_all_checkstates(self, state):
        """Устанавливает состояние для всех элементов."""
        root = self.selection_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setCheckState(0, state)

    def get_selected_items(self):
        """Возвращает список выбранных элементов с данными."""
        selected = []
        root = self.selection_tree.invisibleRootItem()

        def collect_items(item):
            if item.checkState(0) == Qt.Checked:
                data = item.data(0, Qt.UserRole)
                if data:
                    selected.append(data)

            for i in range(item.childCount()):
                collect_items(item.child(i))

        for i in range(root.childCount()):
            collect_items(root.child(i))

        return selected

    def get_export_settings(self):
        """Возвращает настройки экспорта."""
        settings = {
            'sampling_rate': self.sampling_rate_spin.value(),
            'time_start': self.time_start_spin.value(),
            'units': self.custom_units_edit.text() if self.units_combo.currentText() == 'custom'
            else self.units_combo.currentText(),
            'remove_trend': self.remove_trend_cb.isChecked(),
            'detrend_order': self.detrend_order_spin.value(),
            'normalize': self.normalize_cb.isChecked(),
            'normalize_method': self.normalize_combo.currentText(),
            'format': self.format_type,
            'raw_points_only': self.raw_points_cb.isChecked() if hasattr(self, 'raw_points_cb') else False
        }

        if self.format_type == 'SAC':
            settings['little_endian'] = self.sac_little_endian_cb.isChecked()
        elif self.format_type == 'MiniSEED':
            settings['encoding'] = self.mseed_encoding_combo.currentText()

        return settings

    def extract_points_data(self, selected_items, settings):
        """Извлекает данные точек из выбранных элементов"""
        project = self.main_window.current_project
        all_data = []

        raw_only = settings.get('raw_points_only', False)

        for item in selected_items:
            item_type = item[0]

            if item_type == "trace":
                trace_id = item[1]
                trace_name = item[2]
                trace = project.get_trace(trace_id)

                if trace:
                    for interval in trace.intervals:
                        if raw_only:
                            data = self.extract_interval_data_simple(interval, trace_name, settings)
                        else:
                            data = self.extract_interval_data(interval, trace_name, settings)
                        if data:
                            all_data.append(data)

            elif item_type == "interval":
                trace_id = item[1]
                interval_id = item[2]
                trace_name = item[3]
                trace = project.get_trace(trace_id)

                if trace:
                    for interval in trace.intervals:
                        if interval.id == interval_id:
                            if raw_only:
                                data = self.extract_interval_data_simple(interval, trace_name, settings)
                            else:
                                data = self.extract_interval_data(interval, trace_name, settings)
                            if data:
                                all_data.append(data)
                            break

        return all_data

    def extract_interval_data(self, interval, trace_name, settings):
        """Извлекает данные из одного интервала"""
        if not interval.points or len(interval.points) < 2:
            return None

        points = interval.points
        x_vals = np.array([p.x for p in points])
        y_vals = np.array([p.y for p in points])

        # Сортируем по x
        sort_idx = np.argsort(x_vals)
        x_sorted = x_vals[sort_idx]
        y_sorted = y_vals[sort_idx]

        # Вычисляем реальную длительность в пикселях
        duration_pixels = x_sorted[-1] - x_sorted[0]

        # Количество точек после интерполяции (не более чем исходных точек * 10)
        num_samples = min(len(points) * 10, 10000)

        # Создаем равномерную сетку по X (пиксели)
        x_interp = np.linspace(x_sorted[0], x_sorted[-1], num_samples)

        # Интерполяция
        try:
            if len(points) >= 4:
                # Кубическая интерполяция для гладкости
                f = interpolate.interp1d(x_sorted, y_sorted, kind='cubic',
                                         fill_value='extrapolate', bounds_error=False)
            else:
                # Линейная для малого количества точек
                f = interpolate.interp1d(x_sorted, y_sorted, kind='linear',
                                         fill_value='extrapolate', bounds_error=False)

            y_interp = f(x_interp)

            # Заменяем NaN на ближайшие значения
            nan_mask = np.isnan(y_interp)
            if np.any(nan_mask):
                # Заполняем NaN ближайшими значениями
                for i in range(len(y_interp)):
                    if nan_mask[i]:
                        # Ищем ближайшее не-NaN значение
                        for offset in range(1, len(y_interp)):
                            if i - offset >= 0 and not nan_mask[i - offset]:
                                y_interp[i] = y_interp[i - offset]
                                break
                            if i + offset < len(y_interp) and not nan_mask[i + offset]:
                                y_interp[i] = y_interp[i + offset]
                                break

        except Exception as e:
            print(f"Ошибка интерполяции: {e}")
            # Fallback на линейную
            f = interpolate.interp1d(x_sorted, y_sorted, kind='linear',
                                     fill_value=(y_sorted[0], y_sorted[-1]),
                                     bounds_error=False)
            y_interp = f(x_interp)

        # Создаем временную ось на основе реальной длительности в пикселях
        # Предполагаем, что 1 секунда = settings['sampling_rate'] пикселей
        duration_seconds = duration_pixels / settings['sampling_rate']
        time = np.linspace(settings['time_start'],
                           settings['time_start'] + duration_seconds,
                           len(y_interp))

        data = {
            'name': f"{trace_name}",
            'time': time,
            'amplitude': y_interp,
            'sampling_rate': settings['sampling_rate'],
            'units': settings['units'],
            'time_start': settings['time_start'],
            'duration_seconds': duration_seconds,
            'raw_points': list(zip(x_vals, y_vals))
        }

        # Обработка данных
        if settings['remove_trend']:
            data['amplitude'] = self.remove_trend(data['amplitude'], settings['detrend_order'])

        if settings['normalize']:
            data['amplitude'] = self.normalize_data(data['amplitude'], settings['normalize_method'])

        return data

    def extract_interval_data_simple(self, interval, trace_name, settings):
        """Простое извлечение данных без scipy (только сырые точки)"""
        points = interval.points
        x_vals = np.array([p.x for p in points])
        y_vals = np.array([p.y for p in points])

        data = {
            'name': f"{trace_name}_interval",
            'time': np.linspace(settings['time_start'],
                                settings['time_start'] + len(y_vals) / settings['sampling_rate'],
                                len(y_vals)),
            'amplitude': y_vals,
            'sampling_rate': settings['sampling_rate'],
            'units': settings['units'],
            'time_start': settings['time_start'],
            'raw_points': list(zip(x_vals, y_vals))
        }

        if settings['remove_trend']:
            data['amplitude'] = self.remove_trend(data['amplitude'], settings['detrend_order'])

        if settings['normalize']:
            data['amplitude'] = self.normalize_data(data['amplitude'], settings['normalize_method'])

        return data

    def remove_trend(self, data, order=1):
        """Удаление тренда из данных"""
        x = np.arange(len(data))
        coeffs = np.polyfit(x, data, order)
        trend = np.polyval(coeffs, x)
        return data - trend

    def normalize_data(self, data, method='zscore'):
        """Нормализация данных"""
        if len(data) == 0:
            return data

        if method == 'zscore':
            mean = np.mean(data)
            std = np.std(data)
            if std > 0:
                return (data - mean) / std
        elif method == 'minmax':
            min_val = np.min(data)
            max_val = np.max(data)
            if max_val > min_val:
                return (data - min_val) / (max_val - min_val)
        elif method == 'rms':
            rms = np.sqrt(np.mean(data ** 2))
            if rms > 0:
                return data / rms
        return data

    def export_to_csv(self, data, filepath):
        """Экспорт в CSV формат"""
        import csv

        # Проверяем наличие NaN и заменяем их
        amplitude = np.array(data['amplitude'])
        amplitude = np.nan_to_num(amplitude, nan=0.0, posinf=0.0, neginf=0.0)

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['# Seismogram Digitizer Export'])
            writer.writerow([f'# Format: CSV'])
            writer.writerow([f'# Trace: {data["name"]}'])
            writer.writerow([f'# Sampling rate: {data["sampling_rate"]} Hz'])
            writer.writerow([f'# Units: {data["units"]}'])
            writer.writerow([f'# Number of points: {len(data["time"])}'])
            writer.writerow([f'# Duration: {data.get("duration_seconds", 0):.3f} seconds'])
            writer.writerow(['#'])
            writer.writerow(['Time (s)', 'Amplitude'])

            for t, a in zip(data['time'], amplitude):
                writer.writerow([f"{t:.6f}", f"{a:.6f}"])

    def export_to_sac(self, data, filepath):
        """Экспорт в SAC формат (упрощенный)"""
        try:
            import struct

            with open(filepath, 'wb') as f:
                # Заголовок SAC (70 float + 40 int)
                header = [0.0] * 70 + [0] * 40
                header[0] = 1.0 / data['sampling_rate']  # DELTA (шаг по времени)
                header[5] = len(data['amplitude'])  # NPTS
                header[9] = data.get('time_start', 0.0)  # B
                header[10] = data.get('time_start', 0.0) + len(data['amplitude']) / data['sampling_rate']  # E

                # Пишем заголовок (big-endian для SAC)
                for val in header[:70]:
                    f.write(struct.pack('>f', float(val)))
                for val in header[70:]:
                    f.write(struct.pack('>i', int(val)))

                # Пишем данные
                for val in data['amplitude']:
                    f.write(struct.pack('>f', float(val)))

            return True
        except Exception as e:
            print(f"Ошибка экспорта в SAC: {e}")
            return False

    def export_to_numpy(self, data, filepath):
        """Экспорт в NPY/NPZ формат"""
        np.savez(filepath,
                 time=data['time'],
                 amplitude=data['amplitude'],
                 sampling_rate=data['sampling_rate'],
                 units=data['units'],
                 raw_points=data['raw_points'])

    def do_export(self):
        """Выполняет экспорт выбранных данных."""
        selected = self.get_selected_items()
        if not selected:
            QMessageBox.warning(self, "Предупреждение", "Не выбраны элементы для экспорта")
            return

        settings = self.get_export_settings()

        # Извлекаем данные
        all_data = self.extract_points_data(selected, settings)

        if not all_data:
            QMessageBox.warning(self, "Ошибка",
                                "Не удалось извлечь данные для экспорта.\nУбедитесь, что в интервалах есть минимум 2 точки.")
            return

        # Выбираем директорию для экспорта
        export_dir = QFileDialog.getExistingDirectory(self, "Выберите директорию для экспорта")
        if not export_dir:
            return

        success_count = 0

        for i, data in enumerate(all_data):
            # Формируем имя файла
            extension = self.format_type.lower()
            if self.format_type == 'MiniSEED':
                extension = 'mseed'

            filename = f"{data['name']}.{extension}"
            if len(all_data) > 1:
                filename = f"{data['name']}_{i + 1}.{extension}"

            filepath = os.path.join(export_dir, filename)

            # Экспортируем в зависимости от формата
            if self.format_type == 'CSV':
                self.export_to_csv(data, filepath)
                success_count += 1
            elif self.format_type == 'SAC':
                if self.export_to_sac(data, filepath):
                    success_count += 1
            elif self.format_type == 'NPY':
                self.export_to_numpy(data, filepath)
                success_count += 1
            elif self.format_type == 'MiniSEED':
                QMessageBox.information(self, "Информация",
                                        "Экспорт в MiniSEED требует установки obspy\n"
                                        "Функция будет доступна в следующей версии")

        QMessageBox.information(self, "Экспорт завершен",
                                f"Успешно экспортировано {success_count} из {len(all_data)} элементов\n"
                                f"в директорию: {export_dir}")

        self.accept()
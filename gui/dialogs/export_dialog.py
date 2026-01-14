from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QComboBox, QSpinBox,
                             QDoubleSpinBox, QGroupBox, QFormLayout, QCheckBox,
                             QListWidget, QListWidgetItem, QTreeWidget,
                             QTreeWidgetItem, QTabWidget, QWidget)
from PyQt5.QtCore import Qt


class ExportDialog(QDialog):
    """Диалог экспорта данных в различные форматы."""

    def __init__(self, parent=None, format_type='SAC'):
        super().__init__(parent)
        self.main_window = parent
        self.format_type = format_type
        self.selected_items = []  # Выбранные для экспорта элементы
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Экспорт данных - {self.format_type}")
        self.setModal(True)
        self.setMinimumWidth(600)

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
        self.selection_tree.setHeaderLabels(["Элемент", "Тип", "Точек"])
        self.selection_tree.setSelectionMode(QTreeWidget.MultiSelection)
        self.selection_tree.itemChanged.connect(self.on_item_changed)

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

        general_group.setLayout(form_layout)
        layout.addWidget(general_group)

        # Настройки обработки
        processing_group = QGroupBox("Обработка данных")
        processing_layout = QVBoxLayout()

        self.remove_trend_cb = QCheckBox("Удалить тренд")
        processing_layout.addWidget(self.remove_trend_cb)

        self.detrend_order_spin = QSpinBox()
        self.detrend_order_spin.setRange(1, 5)
        self.detrend_order_spin.setValue(1)
        processing_layout.addWidget(QLabel("Порядок полинома тренда:"))
        processing_layout.addWidget(self.detrend_order_spin)

        self.normalize_cb = QCheckBox("Нормализовать амплитуду")
        processing_layout.addWidget(self.normalize_cb)

        self.normalize_combo = QComboBox()
        self.normalize_combo.addItems(["zscore", "minmax", "rms"])
        processing_layout.addWidget(QLabel("Метод нормализации:"))
        processing_layout.addWidget(self.normalize_combo)

        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)

        # Настройки формата (зависит от выбранного формата)
        format_group = QGroupBox(f"Настройки {self.format_type}")
        format_layout = QVBoxLayout()

        if self.format_type == 'SAC':
            self.sac_little_endian_cb = QCheckBox("Little-endian формат")
            format_layout.addWidget(self.sac_little_endian_cb)

            self.sac_header_info = QLabel("SAC заголовок будет заполнен метаданными")
            format_layout.addWidget(self.sac_header_info)

        elif self.format_type == 'MiniSEED':
            self.mseed_encoding_combo = QComboBox()
            self.mseed_encoding_combo.addItems(["STEIM1", "STEIM2", "INT32", "FLOAT32"])
            format_layout.addWidget(QLabel("Кодирование:"))
            format_layout.addWidget(self.mseed_encoding_combo)

            self.mseed_record_length_spin = QSpinBox()
            self.mseed_record_length_spin.setRange(256, 4096)
            self.mseed_record_length_spin.setValue(512)
            self.mseed_record_length_spin.setSuffix(" байт")
            format_layout.addWidget(QLabel("Длина записи:"))
            format_layout.addWidget(self.mseed_record_length_spin)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        layout.addStretch()

    def load_project_items(self):
        """Загружает элементы проекта в дерево выбора."""
        self.selection_tree.clear()

        if not self.main_window or not self.main_window.project:
            return

        project = self.main_window.project

        # Добавляем трассы
        for trace in project.traces:
            trace_item = QTreeWidgetItem(self.selection_tree)
            trace_item.setText(0, trace.name)
            trace_item.setText(1, "Трасса")
            trace_item.setText(2, str(len(trace.intervals)))
            trace_item.setData(0, Qt.UserRole, ("trace", trace.id))
            trace_item.setCheckState(0, Qt.Unchecked)

            # Добавляем интервалы трассы
            for interval in trace.intervals:
                interval_item = QTreeWidgetItem(trace_item)
                interval_item.setText(0, f"Интервал {interval.id[:8]}")
                interval_item.setText(1, self.get_interval_type_name(interval.type))
                interval_item.setText(2, str(len(interval.points)))
                interval_item.setData(0, Qt.UserRole, ("interval", trace.id, interval.id))
                interval_item.setCheckState(0, Qt.Unchecked)

        # Добавляем свободные интервалы
        if project.loose_intervals:
            loose_item = QTreeWidgetItem(self.selection_tree)
            loose_item.setText(0, "Свободные интервалы")
            loose_item.setText(1, "Группа")
            loose_item.setCheckState(0, Qt.Unchecked)

            for interval in project.loose_intervals:
                interval_item = QTreeWidgetItem(loose_item)
                interval_item.setText(0, f"Интервал {interval.id[:8]}")
                interval_item.setText(1, self.get_interval_type_name(interval.type))
                interval_item.setText(2, str(len(interval.points)))
                interval_item.setData(0, Qt.UserRole, ("loose_interval", interval.id))
                interval_item.setCheckState(0, Qt.Unchecked)

        self.selection_tree.expandAll()

    def get_interval_type_name(self, interval_type):
        """Возвращает читаемое имя типа интервала."""
        type_names = {
            "time_marker": "Метка времени",
            "waveform": "Волновая форма",
            "noise": "Помеха"
        }
        return type_names.get(interval_type, "Неизвестно")

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
        """Возвращает список выбранных элементов."""
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
            'units': self.custom_units_edit.text() if self.units_combo.currentText() == 'custom'
            else self.units_combo.currentText(),
            'remove_trend': self.remove_trend_cb.isChecked(),
            'detrend_order': self.detrend_order_spin.value(),
            'normalize': self.normalize_cb.isChecked(),
            'normalize_method': self.normalize_combo.currentText(),
            'format': self.format_type
        }

        if self.format_type == 'SAC':
            settings['little_endian'] = self.sac_little_endian_cb.isChecked()
        elif self.format_type == 'MiniSEED':
            settings['encoding'] = self.mseed_encoding_combo.currentText()
            settings['record_length'] = self.mseed_record_length_spin.value()

        return settings

    def do_export(self):
        """Выполняет экспорт выбранных данных."""
        selected = self.get_selected_items()
        if not selected:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Предупреждение", "Не выбраны элементы для экспорта")
            return

        settings = self.get_export_settings()

        # TODO: Реализовать экспорт
        print(f"Экспорт {len(selected)} элементов в формат {self.format_type}")
        print("Настройки:", settings)

        # Показываем информацию о готовности
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Экспорт",
                                f"Экспорт {len(selected)} элементов в формат {self.format_type}\n"
                                "Функция экспорта будет реализована в следующей версии.")

        self.accept()
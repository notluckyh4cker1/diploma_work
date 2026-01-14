# Панель управления трассами

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                             QPushButton, QHBoxLayout, QGroupBox, QLabel,
                             QTreeWidget, QTreeWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt


class TracesPanel(QWidget):
    """Панель управления трассами и интервалами."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        self.add_trace_btn = QPushButton("+ Трасса")
        self.add_trace_btn.clicked.connect(self.add_trace)
        btn_layout.addWidget(self.add_trace_btn)

        self.remove_trace_btn = QPushButton("- Удалить")
        self.remove_trace_btn.clicked.connect(self.remove_selected)
        btn_layout.addWidget(self.remove_trace_btn)

        layout.addLayout(btn_layout)

        # Дерево трасс и интервалов
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Объект", "Тип", "Точек"])
        self.tree_widget.setColumnWidth(0, 150)
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree_widget)

        # Информация о выбранном элементе
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout()

        self.info_label = QLabel("Выберите элемент для просмотра информации")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Кнопки для интервалов
        interval_btn_layout = QHBoxLayout()

        self.edit_interval_btn = QPushButton("Редактировать")
        self.edit_interval_btn.clicked.connect(self.edit_selected)
        interval_btn_layout.addWidget(self.edit_interval_btn)

        self.export_interval_btn = QPushButton("Экспорт")
        self.export_interval_btn.clicked.connect(self.export_selected)
        interval_btn_layout.addWidget(self.export_interval_btn)

        layout.addLayout(interval_btn_layout)

        layout.addStretch()

    def update_trace_list(self):
        """Обновляет список трасс и интервалов."""
        self.tree_widget.clear()

        if not self.main_window.project:
            return

        project = self.main_window.project

        # Добавляем трассы
        for trace in project.traces:
            trace_item = QTreeWidgetItem(self.tree_widget)
            trace_item.setText(0, trace.name)
            trace_item.setText(1, "Трасса")
            trace_item.setText(2, str(len(trace.intervals)))
            trace_item.setData(0, Qt.UserRole, ("trace", trace.id))

            # Добавляем интервалы трассы
            for interval in trace.intervals:
                interval_item = QTreeWidgetItem(trace_item)
                interval_item.setText(0, f"Интервал {interval.id}")
                interval_item.setText(1, self.get_interval_type_name(interval.type))
                interval_item.setText(2, str(len(interval.points)))
                interval_item.setData(0, Qt.UserRole, ("interval", trace.id, interval.id))

        # Добавляем свободные интервалы
        if project.loose_intervals:
            loose_item = QTreeWidgetItem(self.tree_widget)
            loose_item.setText(0, "Свободные интервалы")
            loose_item.setText(1, "Группа")

            for interval in project.loose_intervals:
                interval_item = QTreeWidgetItem(loose_item)
                interval_item.setText(0, f"Интервал {interval.id}")
                interval_item.setText(1, self.get_interval_type_name(interval.type))
                interval_item.setText(2, str(len(interval.points)))
                interval_item.setData(0, Qt.UserRole, ("loose_interval", interval.id))

        self.tree_widget.expandAll()

    def get_interval_type_name(self, interval_type):
        """Возвращает читаемое имя типа интервала."""
        type_names = {
            "time_marker": "Метка времени",
            "waveform": "Волновая форма",
            "noise": "Помеха"
        }
        return type_names.get(interval_type, "Неизвестно")

    def add_trace(self):
        """Добавляет новую трассу."""
        from models.seismic_data import SeismicTrace
        import uuid

        if not self.main_window.project or not self.main_window.project.raster:
            return

        trace_id = str(uuid.uuid4())[:8]
        trace = SeismicTrace(
            id=trace_id,
            name=f"Трасса_{trace_id}",
            raster_coords=(0, 0, 100, 100)  # Заглушка
        )

        self.main_window.project.add_trace(trace)
        self.update_trace_list()

    def remove_selected(self):
        """Удаляет выбранный элемент."""
        current_item = self.tree_widget.currentItem()
        if not current_item:
            return

        data = current_item.data(0, Qt.UserRole)
        if not data:
            return

        project = self.main_window.project
        if not project:
            return

        item_type = data[0]

        if item_type == "trace":
            trace_id = data[1]
            # Находим и удаляем трассу
            for i, trace in enumerate(project.traces):
                if trace.id == trace_id:
                    project.traces.pop(i)
                    break

        elif item_type == "interval":
            trace_id, interval_id = data[1], data[2]
            # Находим трассу и удаляем интервал
            trace = project.find_trace_by_id(trace_id)
            if trace:
                for i, interval in enumerate(trace.intervals):
                    if interval.id == interval_id:
                        trace.intervals.pop(i)
                        break

        elif item_type == "loose_interval":
            interval_id = data[1]
            # Удаляем свободный интервал
            for i, interval in enumerate(project.loose_intervals):
                if interval.id == interval_id:
                    project.loose_intervals.pop(i)
                    break

        self.update_trace_list()

    def on_item_double_clicked(self, item, column):
        """Обработка двойного клика по элементу."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        # TODO: Реализовать выделение элемента на холсте
        self.show_item_info(item)

    def show_item_info(self, item):
        """Показывает информацию о выбранном элементе."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data[0]
        info_text = ""

        if item_type == "trace":
            trace_id = data[1]
            trace = self.main_window.project.find_trace_by_id(trace_id)
            if trace:
                info_text = f"Трасса: {trace.name}\nID: {trace.id}\n"
                info_text += f"Интервалов: {len(trace.intervals)}\n"
                info_text += f"Координаты: {trace.raster_coords}"

        elif item_type == "interval":
            trace_id, interval_id = data[1], data[2]
            trace = self.main_window.project.find_trace_by_id(trace_id)
            if trace:
                for interval in trace.intervals:
                    if interval.id == interval_id:
                        info_text = f"Интервал: {interval.id}\n"
                        info_text += f"Тип: {self.get_interval_type_name(interval.type)}\n"
                        info_text += f"Точек: {len(interval.points)}\n"
                        info_text += f"Цвет: {interval.color}"
                        break

        elif item_type == "loose_interval":
            interval_id = data[1]
            for interval in self.main_window.project.loose_intervals:
                if interval.id == interval_id:
                    info_text = f"Свободный интервал: {interval.id}\n"
                    info_text += f"Тип: {self.get_interval_type_name(interval.type)}\n"
                    info_text += f"Точек: {len(interval.points)}"
                    break

        self.info_label.setText(info_text)

    def edit_selected(self):
        """Редактирует выбранный элемент."""
        current_item = self.tree_widget.currentItem()
        if current_item:
            self.on_item_double_clicked(current_item, 0)

    def export_selected(self):
        """Экспортирует выбранный элемент."""
        current_item = self.tree_widget.currentItem()
        if not current_item:
            return

        # TODO: Реализовать экспорт выбранного интервала
        print("Экспорт будет реализован позже")
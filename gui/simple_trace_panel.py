# Упрощенная панель для управления трассами и интервалами.
# Будет вызываться через контекстное меню или горячие клавиши.


from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QPushButton, QLabel, QGroupBox,
                             QInputDialog, QMessageBox, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal


class SimpleTraceDialog(QDialog):
    """Диалог для просмотра и управления трассами и интервалами."""

    interval_selected = pyqtSignal(str, str)  # signal: (trace_id, interval_id)
    interval_deleted = pyqtSignal(str, str)  # signal: (trace_id, interval_id)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Управление трассами и интервалами")
        self.setModal(False)  # Не модальный, чтобы можно было работать с основным окном
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Трассы и интервалы проекта")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Дерево трасс и интервалов
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Имя", "Тип", "Точек", "ID"])
        self.tree_widget.setColumnWidth(0, 200)
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree_widget)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        self.add_trace_btn = QPushButton("+ Трасса")
        self.add_trace_btn.clicked.connect(self.add_trace)
        btn_layout.addWidget(self.add_trace_btn)

        self.add_interval_btn = QPushButton("+ Интервал")
        self.add_interval_btn.clicked.connect(self.add_interval)
        self.add_interval_btn.setEnabled(False)  # Включится при выборе трассы
        btn_layout.addWidget(self.add_interval_btn)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        self.interpolate_btn = QPushButton("Интерполировать")
        self.interpolate_btn.clicked.connect(self.interpolate_selected)
        btn_layout.addWidget(self.interpolate_btn)

        btn_layout.addStretch()

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        # Подключаем выбор элемента
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)

    def load_data(self):
        """Загружает данные проекта в дерево."""
        self.tree_widget.clear()

        if not self.project:
            return

        # Добавляем трассы
        for trace in self.project.traces:
            trace_item = QTreeWidgetItem(self.tree_widget)
            trace_item.setText(0, trace.name)
            trace_item.setText(1, "Трасса")
            trace_item.setText(2, str(len(trace.intervals)))
            trace_item.setText(3, trace.id)
            trace_item.setData(0, Qt.UserRole, ("trace", trace.id))

            # Добавляем интервалы трассы
            for interval in trace.intervals:
                interval_item = QTreeWidgetItem(trace_item)
                self.add_interval_to_tree(interval_item, interval, trace.id)

        # Добавляем свободные интервалы
        if self.project.loose_intervals:
            loose_item = QTreeWidgetItem(self.tree_widget)
            loose_item.setText(0, "Свободные интервалы")
            loose_item.setText(1, "Группа")
            loose_item.setData(0, Qt.UserRole, ("loose_group", ""))

            for interval in self.project.loose_intervals:
                interval_item = QTreeWidgetItem(loose_item)
                self.add_interval_to_tree(interval_item, interval, None)

        self.tree_widget.expandAll()

    def add_interval_to_tree(self, item, interval, trace_id):
        """Добавляет интервал в дерево."""
        type_names = {
            "time_marker": "Метка времени",
            "waveform": "Волновая форма",
            "noise": "Помеха"
        }

        item.setText(0, f"Интервал: {interval.id[:8]}")
        item.setText(1, type_names.get(interval.type, "Неизвестно"))
        item.setText(2, str(len(interval.points)))
        item.setText(3, interval.id)
        item.setData(0, Qt.UserRole, ("interval", trace_id, interval.id))

    def on_selection_changed(self):
        """Обработчик изменения выбранного элемента."""
        selected_items = self.tree_widget.selectedItems()
        has_selection = len(selected_items) > 0

        self.delete_btn.setEnabled(has_selection)

        # Включаем кнопку добавления интервала только если выбрана трасса
        if has_selection:
            item = selected_items[0]
            data = item.data(0, Qt.UserRole)
            if data and data[0] == "trace":
                self.add_interval_btn.setEnabled(True)
            else:
                self.add_interval_btn.setEnabled(False)
        else:
            self.add_interval_btn.setEnabled(False)

    def add_trace(self):
        """Добавляет новую трассу."""
        from core.trace_manager import TraceManager

        name, ok = QInputDialog.getText(self, "Создать трассу",
                                        "Введите имя трассы:")
        if ok and name:
            trace_manager = TraceManager(self.project)
            trace = trace_manager.create_trace(name)
            trace_id = self.project.add_trace(trace)

            # Добавляем в дерево
            trace_item = QTreeWidgetItem(self.tree_widget)
            trace_item.setText(0, trace.name)
            trace_item.setText(1, "Трасса")
            trace_item.setText(2, "0")
            trace_item.setText(3, trace.id)
            trace_item.setData(0, Qt.UserRole, ("trace", trace.id))

    def add_interval(self):
        """Добавляет интервал к выбранной трассе."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        data = item.data(0, Qt.UserRole)

        if data and data[0] == "trace":
            trace_id = data[1]
            trace = self.project.find_trace_by_id(trace_id)

            if trace:
                # Создаем тестовый интервал (в реальности будет из холста)
                from models.seismic_data import DigitizationInterval
                import uuid

                interval = DigitizationInterval(
                    id=str(uuid.uuid4())[:8],
                    type="waveform",
                    points=[],  # Пустой интервал
                    color="#FF0000"
                )

                trace.intervals.append(interval)

                # Добавляем в дерево
                interval_item = QTreeWidgetItem(item)
                self.add_interval_to_tree(interval_item, interval, trace_id)
                item.setText(2, str(len(trace.intervals)))  # Обновляем счетчик

                self.statusBar().showMessage(f"Добавлен интервал к трассе {trace.name}", 2000)

    def delete_selected(self):
        """Удаляет выбранный элемент."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        data = item.data(0, Qt.UserRole)

        if not data:
            return

        item_type = data[0]

        if item_type == "trace":
            trace_id = data[1]
            reply = QMessageBox.question(self, "Удаление трассы",
                                         f"Удалить трассу и все её интервалы?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.project.remove_trace(trace_id)
                self.tree_widget.takeTopLevelItem(
                    self.tree_widget.indexOfTopLevelItem(item)
                )

        elif item_type == "interval":
            trace_id, interval_id = data[1], data[2]

            if trace_id:  # Интервал в трассе
                trace = self.project.find_trace_by_id(trace_id)
                if trace:
                    for i, interval in enumerate(trace.intervals):
                        if interval.id == interval_id:
                            trace.intervals.pop(i)
                            item.parent().removeChild(item)
                            # Обновляем счетчик интервалов у трассы
                            parent = item.parent()
                            if parent:
                                parent.setText(2, str(len(trace.intervals)))
                            break
            else:  # Свободный интервал
                for i, interval in enumerate(self.project.loose_intervals):
                    if interval.id == interval_id:
                        self.project.loose_intervals.pop(i)
                        item.parent().removeChild(item)
                        break

    def interpolate_selected(self):
        """Интерполирует выбранные интервалы."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            data = item.data(0, Qt.UserRole)
            if data and data[0] == "interval":
                trace_id, interval_id = data[1], data[2]

                if trace_id:
                    trace = self.project.find_trace_by_id(trace_id)
                    if trace:
                        for interval in trace.intervals:
                            if interval.id == interval_id:
                                if self.project._interpolate_interval(interval):
                                    item.setText(1, f"{item.text(1)} [интерп.]")
                                break
                else:
                    for interval in self.project.loose_intervals:
                        if interval.id == interval_id:
                            if self.project._interpolate_interval(interval):
                                item.setText(1, f"{item.text(1)} [интерп.]")
                            break

        self.statusBar().showMessage("Интерполяция завершена", 2000)

    def on_item_double_clicked(self, item, column):
        """Обработка двойного клика по элементу."""
        data = item.data(0, Qt.UserRole)
        if data and data[0] == "interval":
            trace_id, interval_id = data[1], data[2]
            self.interval_selected.emit(trace_id, interval_id)

    def showEvent(self, event):
        """Обработчик показа диалога."""
        super().showEvent(event)
        self.load_data()  # Перезагружаем данные при каждом показе
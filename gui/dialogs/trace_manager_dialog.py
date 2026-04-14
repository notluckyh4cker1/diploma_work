from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView,
                             QMessageBox, QWidget, QLabel, QFrame, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
import uuid


class TraceManagerDialog(QDialog):
    """Диалог управления трассами"""

    start_trace_selection = pyqtSignal(object)  # Сигнал для начала выделения трассы

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Управление трассами")
        self.setMinimumSize(700, 500)

        self.setup_ui()
        self.load_traces()

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)

        # Верхняя панель с выбором трассы
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 5, 0, 5)

        top_layout.addWidget(QLabel("Работа с трассой:"))

        self.trace_selector = QComboBox()
        self.trace_selector.setMinimumWidth(200)
        self.trace_selector.currentIndexChanged.connect(self.on_trace_selected)
        top_layout.addWidget(self.trace_selector)

        top_layout.addStretch()
        layout.addWidget(top_panel)

        # Разделитель
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line1)

        # Информационная метка
        info_label = QLabel("Список сейсмических трасс в проекте:")
        info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)

        # Таблица трасс (без колонки видимости)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Название", "ID", "Интервалы", "Точки"])

        # Настройка таблицы
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)

        layout.addWidget(self.table)

        # Разделитель
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)

        # Панель кнопок управления
        panel1 = QWidget()
        panel1_layout = QHBoxLayout(panel1)
        panel1_layout.setContentsMargins(0, 5, 0, 5)

        self.add_trace_btn = QPushButton("Новая трасса")
        self.add_trace_btn.clicked.connect(self.add_trace)
        panel1_layout.addWidget(self.add_trace_btn)

        self.edit_trace_btn = QPushButton("Редактировать")
        self.edit_trace_btn.clicked.connect(self.edit_trace)
        panel1_layout.addWidget(self.edit_trace_btn)

        self.delete_trace_btn = QPushButton("Удалить")
        self.delete_trace_btn.clicked.connect(self.delete_trace)
        panel1_layout.addWidget(self.delete_trace_btn)

        panel1_layout.addStretch()

        layout.addWidget(panel1)

        # Нижняя панель (кнопки диалога)
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 5, 0, 5)

        bottom_layout.addStretch()

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)

        layout.addWidget(bottom_panel)

    def load_traces(self):
        """Загрузить список трасс в таблицу и в селектор"""
        self.table.setRowCount(0)
        self.trace_selector.clear()

        if not self.project or not self.project.traces:
            self.trace_selector.addItem("Нет трасс", None)
            return

        for trace in self.project.traces:
            self.trace_selector.addItem(trace.name, trace.id)

        for row, trace in enumerate(self.project.traces):
            self.table.insertRow(row)

            # Название трассы
            name_item = QTableWidgetItem(trace.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            # ID трассы (укороченный для отображения)
            short_id = trace.id[:8] + "..." if len(trace.id) > 8 else trace.id
            id_item = QTableWidgetItem(short_id)
            id_item.setToolTip(trace.id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, id_item)

            # Количество интервалов
            intervals_count = len(trace.intervals)
            intervals_item = QTableWidgetItem(str(intervals_count))
            intervals_item.setTextAlignment(Qt.AlignCenter)
            intervals_item.setFlags(intervals_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, intervals_item)

            # Количество точек
            total_points = sum(len(interval.points) for interval in trace.intervals)
            points_item = QTableWidgetItem(str(total_points))
            points_item.setTextAlignment(Qt.AlignCenter)
            points_item.setFlags(points_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, points_item)

            # Сохраняем ссылку на трассу
            self.table.item(row, 0).setData(Qt.UserRole, trace.id)

    def get_selected_trace(self):
        """Получить выбранную трассу"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            trace_id = self.table.item(current_row, 0).data(Qt.UserRole)
            return self.project.get_trace(trace_id)
        return None

    def on_trace_selected(self, index):
        """Выбор трассы из выпадающего списка"""
        trace_id = self.trace_selector.currentData()
        if trace_id:
            trace = self.project.get_trace(trace_id)
            if trace:
                # Выделяем строку в таблице
                for row in range(self.table.rowCount()):
                    if self.table.item(row, 0).data(Qt.UserRole) == trace_id:
                        self.table.selectRow(row)
                        break

    def on_table_selection_changed(self):
        """При выборе строки в таблице - обновляем выпадающий список"""
        trace = self.get_selected_trace()
        if trace:
            index = self.trace_selector.findData(trace.id)
            if index >= 0:
                self.trace_selector.blockSignals(True)
                self.trace_selector.setCurrentIndex(index)
                self.trace_selector.blockSignals(False)

    def add_trace(self):
        """Добавить новую трассу"""
        from PyQt5.QtWidgets import QInputDialog
        from models.trace import Trace

        name, ok = QInputDialog.getText(self, "Новая трасса", "Введите название трассы:")
        if ok and name:
            trace_id = str(uuid.uuid4())
            trace = Trace(
                id=trace_id,
                name=name,
                raster_coords=((0, 0), (0, 0)),
                is_visible=True,
                is_editing=False
            )
            self.project.add_trace(trace)
            self.load_traces()
            QMessageBox.information(self, "Успех", f"Трасса '{name}' добавлена")

    def edit_trace(self):
        """Редактировать название трассы"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для редактирования")
            return

        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Редактирование",
                                        "Введите новое название:",
                                        text=trace.name)
        if ok and name:
            trace.name = name
            self.load_traces()
            QMessageBox.information(self, "Успех", f"Трасса переименована в '{name}'")

    def delete_trace(self):
        """Удалить выбранную трассу"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для удаления")
            return

        total_points = sum(len(interval.points) for interval in trace.intervals)

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить трассу '{trace.name}'?\n"
            f"(Содержит {len(trace.intervals)} интервалов и {total_points} точек)",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            trace_id = trace.id

            for interval in trace.intervals:
                interval.points.clear()
            trace.intervals.clear()

            self.project.remove_trace(trace_id)

            parent = self.parent()
            if parent and hasattr(parent, 'canvas'):
                canvas = parent.canvas
                if canvas.current_trace and canvas.current_trace.id == trace_id:
                    canvas.current_trace = None
                    canvas.current_interval = None
                    canvas.update_display()

            self.load_traces()

            import gc
            gc.collect()

            QMessageBox.information(self, "Успех", f"Трасса '{trace.name}' удалена")

    def start_editing(self):
        """Начать редактирование выбранной трассы"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для оцифровки")
            return

        if not self.project.raster_data:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите растер")
            return

        self.start_trace_selection.emit(trace)
        self.accept()

    def refresh(self):
        """Обновить таблицу"""
        self.load_traces()
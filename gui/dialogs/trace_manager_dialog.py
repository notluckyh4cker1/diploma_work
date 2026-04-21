from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView,
                             QMessageBox, QWidget, QLabel, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
import uuid


class TraceManagerDialog(QDialog):
    """Диалог управления трассами"""

    trace_selected_for_editing = pyqtSignal(object)  # Сигнал для выбора трассы для оцифровки

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

        # Информационная метка
        info_label = QLabel("Список сейсмических трасс в проекте:")
        info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)

        # Таблица трасс
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

        layout.addWidget(self.table)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Панель кнопок управления
        panel = QWidget()
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(0, 5, 0, 5)

        self.add_trace_btn = QPushButton("Новая трасса")
        self.add_trace_btn.clicked.connect(self.add_trace)
        panel_layout.addWidget(self.add_trace_btn)

        self.edit_trace_btn = QPushButton("Редактировать")
        self.edit_trace_btn.clicked.connect(self.edit_trace)
        panel_layout.addWidget(self.edit_trace_btn)

        self.delete_trace_btn = QPushButton("Удалить")
        self.delete_trace_btn.clicked.connect(self.delete_trace)
        panel_layout.addWidget(self.delete_trace_btn)

        layout.addWidget(panel)

        # Нижняя панель
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 5, 0, 5)

        bottom_layout.addStretch()

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_traces)
        bottom_layout.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)

        layout.addWidget(bottom_panel)

    def load_traces(self):
        """Загрузить список трасс в таблицу"""
        self.table.setRowCount(0)

        if not self.project or not self.project.traces:
            return

        for row, trace in enumerate(self.project.traces):
            self.table.insertRow(row)

            # Название трассы
            name_item = QTableWidgetItem(trace.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            # ID трассы
            short_id = trace.id[:8] + "..." if len(trace.id) > 8 else trace.id
            id_item = QTableWidgetItem(short_id)
            id_item.setToolTip(trace.id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, id_item)

            # Количество интервалов
            intervals_with_points = [i for i in trace.intervals if i.points]
            intervals_count = len(intervals_with_points)
            intervals_item = QTableWidgetItem(str(intervals_count))
            intervals_item.setTextAlignment(Qt.AlignCenter)
            intervals_item.setFlags(intervals_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, intervals_item)

            # Количество точек
            total_points = sum(len(i.points) for i in trace.intervals if i.points)
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

        intervals_with_points = [i for i in trace.intervals if i.points]
        total_points = sum(len(i.points) for i in trace.intervals if i.points)

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить трассу '{trace.name}'?\n"
            f"(Содержит {len(intervals_with_points)} интервалов и {total_points} точек)",
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

    def select_for_editing(self):
        """Выбрать трассу для оцифровки"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для оцифровки")
            return

        if not self.project.raster_data:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите растер")
            return

        self.trace_selected_for_editing.emit(trace)
        self.accept()
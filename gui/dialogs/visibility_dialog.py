from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView,
                             QWidget, QLabel, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush


class VisibilityDialog(QDialog):
    """Диалог управления видимостью трасс"""

    visibility_changed = pyqtSignal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Отображение трасс")
        self.setMinimumSize(500, 400)

        self.setup_ui()
        self.load_traces()

        # Подключаем сигнал изменения чекбоксов
        self.table.itemChanged.connect(self.on_checkbox_changed)

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)

        info_label = QLabel("Управление видимостью трасс:")
        info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)

        # Таблица трасс
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Видимость", "Название трассы", "Информация"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Панель кнопок
        button_panel = QWidget()
        button_layout = QHBoxLayout(button_panel)
        button_layout.setContentsMargins(0, 5, 0, 5)

        self.show_all_btn = QPushButton("Показать все")
        self.show_all_btn.clicked.connect(self.show_all)
        button_layout.addWidget(self.show_all_btn)

        self.hide_all_btn = QPushButton("Скрыть все")
        self.hide_all_btn.clicked.connect(self.hide_all)
        button_layout.addWidget(self.hide_all_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addWidget(button_panel)

    def load_traces(self):
        """Загрузить список трасс в таблицу"""
        self.table.setRowCount(0)

        if not self.project or not self.project.traces:
            return

        # Блокируем сигналы во время загрузки
        self.table.blockSignals(True)

        for row, trace in enumerate(self.project.traces):
            self.table.insertRow(row)

            # Чекбокс видимости
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Checked if trace.is_visible else Qt.Unchecked)
            self.table.setItem(row, 0, checkbox_item)

            # Название трассы
            name_item = QTableWidgetItem(trace.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name_item)

            # Информация (количество точек)
            total_points = sum(len(interval.points) for interval in trace.intervals)
            info_text = f"Точек: {total_points}, Интервалов: {len(trace.intervals)}"
            info_item = QTableWidgetItem(info_text)
            info_item.setFlags(info_item.flags() & ~Qt.ItemIsEditable)
            info_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, info_item)

            # Сохраняем ID трассы
            self.table.item(row, 1).setData(Qt.UserRole, trace.id)

        self.table.blockSignals(False)

    def on_checkbox_changed(self, item):
        """Обработка изменения чекбокса"""
        if item.column() != 0:  # Только для колонки с чекбоксом
            return

        row = item.row()
        trace_id = self.table.item(row, 1).data(Qt.UserRole)
        trace = self.project.get_trace(trace_id)

        if trace:
            new_state = (item.checkState() == Qt.Checked)
            trace.is_visible = new_state
            self.visibility_changed.emit()

    def show_all(self):
        """Показать все трассы"""
        self.table.blockSignals(True)

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            item.setCheckState(Qt.Checked)
            trace_id = self.table.item(row, 1).data(Qt.UserRole)
            trace = self.project.get_trace(trace_id)
            if trace:
                trace.is_visible = True

        self.table.blockSignals(False)
        self.visibility_changed.emit()

    def hide_all(self):
        """Скрыть все трассы"""
        self.table.blockSignals(True)

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            item.setCheckState(Qt.Unchecked)
            trace_id = self.table.item(row, 1).data(Qt.UserRole)
            trace = self.project.get_trace(trace_id)
            if trace:
                trace.is_visible = False

        self.table.blockSignals(False)
        self.visibility_changed.emit()

    def closeEvent(self, event):
        """При закрытии окна"""
        self.visibility_changed.emit()
        event.accept()
# Панель управления

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QLabel,
                             QComboBox, QPushButton, QColorDialog, QSpinBox,
                             QHBoxLayout, QCheckBox)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor

class ControlsPanel(QWidget):
    """Панель управления параметрами оцифровки."""

    # Сигналы
    interval_type_changed = pyqtSignal(str)
    color_changed = pyqtSignal(str)
    polynomial_order_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_color = "#FF0000"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Группа "Тип интервала"
        type_group = QGroupBox("Тип интервала")
        type_layout = QVBoxLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Метка времени", "Волновая форма", "Помеха"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_layout.addWidget(QLabel("Тип:"))
        type_layout.addWidget(self.type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Группа "Настройки отображения"
        display_group = QGroupBox("Настройки отображения")
        display_layout = QVBoxLayout()

        # Цвет
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Цвет:"))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 30)
        self.color_btn.setStyleSheet(f"background-color: {self.current_color};")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        display_layout.addLayout(color_layout)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Группа "Интерполяция"
        interp_group = QGroupBox("Интерполяция")
        interp_layout = QVBoxLayout()

        interp_layout.addWidget(QLabel("Порядок полинома:"))
        self.poly_spin = QSpinBox()
        self.poly_spin.setRange(1, 10)
        self.poly_spin.setValue(3)
        self.poly_spin.valueChanged.connect(self.on_poly_order_changed)
        interp_layout.addWidget(self.poly_spin)

        interp_group.setLayout(interp_layout)
        layout.addWidget(interp_group)

        # Группа "Действия"
        action_group = QGroupBox("Действия")
        action_layout = QVBoxLayout()

        self.finish_btn = QPushButton("Завершить интервал (ПКМ)")
        self.finish_btn.clicked.connect(self.finish_interval)
        action_layout.addWidget(self.finish_btn)

        self.clear_btn = QPushButton("Очистить интервал (Del)")
        self.clear_btn.clicked.connect(self.clear_interval)
        action_layout.addWidget(self.clear_btn)

        self.interpolate_btn = QPushButton("Интерполировать")
        self.interpolate_btn.clicked.connect(self.interpolate_current)
        action_layout.addWidget(self.interpolate_btn)

        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        # Группа "Коррекции"
        correction_group = QGroupBox("Коррекции")
        correction_layout = QVBoxLayout()

        self.correct_trend_cb = QCheckBox("Автокоррекция тренда")
        correction_layout.addWidget(self.correct_trend_cb)

        correction_group.setLayout(correction_layout)
        layout.addWidget(correction_group)

        layout.addStretch()

    def on_type_changed(self, index):
        """Обработка изменения типа интервала."""
        type_map = {
            0: "time_marker",
            1: "waveform",
            2: "noise"
        }
        type_str = type_map.get(index, "waveform")
        self.main_window.current_interval_type = type_str
        self.interval_type_changed.emit(type_str)

    def choose_color(self):
        """Выбор цвета для интервала."""
        color = QColorDialog.getColor(QColor(self.current_color), self, "Выберите цвет")
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self.current_color};")
            self.color_changed.emit(self.current_color)

    def on_poly_order_changed(self, value):
        """Обработка изменения порядка полинома."""
        self.polynomial_order_changed.emit(value)

    def finish_interval(self):
        """Завершает текущий интервал."""
        if self.main_window.raster_canvas:
            self.main_window.raster_canvas.finish_current_interval()

    def clear_interval(self):
        """Очищает текущий интервал."""
        if self.main_window.raster_canvas:
            self.main_window.raster_canvas.clear_current_interval()

    def interpolate_current(self):
        """Интерполирует текущий интервал."""
        # TODO: Реализовать интерполяцию
        print("Интерполяция будет реализована позже")
# gui/controls_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                             QComboBox, QLabel, QGroupBox, QSpinBox,
                             QFrame)
from PyQt5.QtCore import pyqtSignal


class ControlsPanel(QWidget):
    mode_changed = pyqtSignal(str)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    interpolate_requested = pyqtSignal()
    remove_trend_requested = pyqtSignal()
    finish_interval_requested = pyqtSignal()
    manage_traces_requested = pyqtSignal()
    finish_trace_requested = pyqtSignal()
    show_visibility_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # ===== РЕЖИМ "ПАНОРАМИРОВАНИЕ" =====
        pan_group = QGroupBox("Навигация")
        pan_layout = QVBoxLayout()

        self.pan_mode_btn = QPushButton("Режим панорамирования")
        self.pan_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.pan_mode_btn.clicked.connect(lambda: self.mode_changed.emit('pan'))
        pan_layout.addWidget(self.pan_mode_btn)

        pan_group.setLayout(pan_layout)
        layout.addWidget(pan_group)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # ===== РЕЖИМ "ОЦИФРОВКА" =====
        digitize_group = QGroupBox("Оцифровка")
        digitize_layout = QVBoxLayout()

        self.digitize_mode_btn = QPushButton("Режим оцифровки")
        self.digitize_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.digitize_mode_btn.clicked.connect(lambda: self.mode_changed.emit('digitize'))
        digitize_layout.addWidget(self.digitize_mode_btn)

        digitize_layout.addWidget(QLabel("Инструменты оцифровки"))

        self.add_point_btn = QPushButton("Добавить точку")
        self.add_point_btn.clicked.connect(lambda: self.mode_changed.emit('add_point'))
        digitize_layout.addWidget(self.add_point_btn)

        self.delete_point_btn = QPushButton("Удалить точку")
        self.delete_point_btn.clicked.connect(lambda: self.mode_changed.emit('delete_point'))
        digitize_layout.addWidget(self.delete_point_btn)

        self.move_point_btn = QPushButton("Переместить точку")
        self.move_point_btn.clicked.connect(lambda: self.mode_changed.emit('move_point'))
        digitize_layout.addWidget(self.move_point_btn)

        self.finish_interval_btn = QPushButton("Завершить текущую линию")
        self.finish_interval_btn.clicked.connect(self.finish_interval_requested.emit)
        digitize_layout.addWidget(self.finish_interval_btn)

        digitize_group.setLayout(digitize_layout)
        layout.addWidget(digitize_group)

        # ===== Группа управления =====
        control_group = QGroupBox("Управление")
        control_layout = QVBoxLayout()

        self.undo_btn = QPushButton("Отменить (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.undo_requested.emit)
        control_layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("Вернуть (Ctrl+Y)")
        self.redo_btn.clicked.connect(self.redo_requested.emit)
        control_layout.addWidget(self.redo_btn)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # ===== Группа обработки =====
        process_group = QGroupBox("Обработка")
        process_layout = QVBoxLayout()

        self.interpolate_btn = QPushButton("Интерполяция")
        self.interpolate_btn.clicked.connect(self.interpolate_requested.emit)
        process_layout.addWidget(self.interpolate_btn)

        self.trend_btn = QPushButton("Удалить тренд")
        self.trend_btn.clicked.connect(self.remove_trend_requested.emit)
        process_layout.addWidget(self.trend_btn)

        process_group.setLayout(process_layout)
        layout.addWidget(process_group)

        # ===== Группа трасс =====
        traces_group = QGroupBox("Трассы")
        traces_layout = QVBoxLayout()

        self.show_visibility_btn = QPushButton("Отображение трасс")
        self.show_visibility_btn.clicked.connect(self.show_visibility_requested.emit)
        traces_layout.addWidget(self.show_visibility_btn)

        self.manage_traces_btn = QPushButton("Управление трассами")
        self.manage_traces_btn.clicked.connect(self.manage_traces_requested)
        traces_layout.addWidget(self.manage_traces_btn)

        self.finish_trace_btn = QPushButton("Завершить текущую трассу")
        self.finish_trace_btn.clicked.connect(self.finish_trace_requested)
        traces_layout.addWidget(self.finish_trace_btn)

        traces_group.setLayout(traces_layout)
        layout.addWidget(traces_group)

        # ===== Группа настроек интерполяции =====
        interp_group = QGroupBox("Параметры интерполяции")
        interp_layout = QVBoxLayout()

        interp_layout.addWidget(QLabel("Тип полинома:"))
        self.interp_type = QComboBox()
        self.interp_type.addItems(["Линейный", "Квадратичный", "Кубический"])
        interp_layout.addWidget(self.interp_type)

        interp_layout.addWidget(QLabel("Количество точек:"))
        self.num_points = QSpinBox()
        self.num_points.setRange(10, 10000)
        self.num_points.setValue(500)
        interp_layout.addWidget(self.num_points)

        interp_group.setLayout(interp_layout)
        layout.addWidget(interp_group)

        layout.addStretch()
        self.setLayout(layout)

    def set_digitize_tools_enabled(self, enabled: bool):
        """Включить/выключить инструменты оцифровки"""
        self.add_point_btn.setEnabled(enabled)
        self.delete_point_btn.setEnabled(enabled)
        self.move_point_btn.setEnabled(enabled)
        self.finish_interval_btn.setEnabled(enabled)
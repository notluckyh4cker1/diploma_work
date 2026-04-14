# gui/controls_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                             QComboBox, QLabel, QGroupBox, QSpinBox,
                             QFrame, QHBoxLayout)
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
    select_trace_requested = pyqtSignal(object)
    show_visibility_requested = pyqtSignal()  # Добавляем обратно

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # ===== РЕЖИМ "ПАНОРАМИРОВАНИЕ" =====
        pan_group = QGroupBox("Навигация")
        pan_layout = QVBoxLayout()

        self.pan_mode_btn = QPushButton("🔍 Режим панорамирования")
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

        self.digitize_mode_btn = QPushButton("✏️ Режим оцифровки")
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

        # ===== РАБОТА С ТРАССОЙ =====
        trace_work_group = QGroupBox("Работа с трассой")
        trace_work_layout = QVBoxLayout()

        # Выбор трассы
        trace_select_layout = QHBoxLayout()
        trace_select_layout.addWidget(QLabel("Трасса:"))
        self.trace_selector = QComboBox()
        self.trace_selector.setMinimumWidth(150)
        self.trace_selector.currentIndexChanged.connect(self.on_trace_selected)
        trace_select_layout.addWidget(self.trace_selector)
        trace_work_layout.addLayout(trace_select_layout)

        # Кнопки управления трассой

        self.manage_traces_btn = QPushButton("Управление трассами")
        self.manage_traces_btn.clicked.connect(self.manage_traces_requested.emit)
        trace_work_layout.addWidget(self.manage_traces_btn)

        self.visibility_btn = QPushButton("Видимость трасс")
        self.visibility_btn.clicked.connect(self.show_visibility_requested.emit)
        trace_work_layout.addWidget(self.visibility_btn)

        self.finish_trace_btn = QPushButton("Завершить текущую трассу")
        self.finish_trace_btn.clicked.connect(self.finish_trace_requested.emit)
        trace_work_layout.addWidget(self.finish_trace_btn)

        trace_work_group.setLayout(trace_work_layout)
        layout.addWidget(trace_work_group)

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

    def update_trace_selector(self, traces, current_trace_id=None):
        """Обновить выпадающий список трасс"""
        self.trace_selector.blockSignals(True)
        self.trace_selector.clear()

        self.trace_selector.addItem("Выберите трассу", None)

        for trace in traces:
            icon = "👁️" if trace.is_visible else "🚫"
            self.trace_selector.addItem(f"{icon} {trace.name}", trace.id)

        if current_trace_id:
            index = self.trace_selector.findData(current_trace_id)
            if index >= 0:
                self.trace_selector.setCurrentIndex(index)

        self.trace_selector.blockSignals(False)

    def on_trace_selected(self, index):
        """Выбор трассы из списка"""
        if index <= 0:
            return
        trace_id = self.trace_selector.itemData(index)
        if trace_id:
            self.select_trace_requested.emit(trace_id)

    def select_current_trace(self):
        """Выбрать текущую трассу из селектора"""
        index = self.trace_selector.currentIndex()
        if index <= 0:
            return
        trace_id = self.trace_selector.itemData(index)
        if trace_id:
            self.select_trace_requested.emit(trace_id)

    def set_selected_trace(self, trace_id):
        """Установить выбранную трассу в селекторе"""
        if trace_id:
            index = self.trace_selector.findData(trace_id)
            if index >= 0:
                self.trace_selector.setCurrentIndex(index)
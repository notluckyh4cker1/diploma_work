# Диалог настроек растра

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QDoubleSpinBox, QGroupBox,
                             QFormLayout, QCheckBox, QComboBox, QTabWidget,
                             QWidget, QSlider)
from PyQt5.QtCore import Qt, pyqtSignal


class RasterSettingsDialog(QDialog):
    """Диалог настройки параметров растра."""

    settings_changed = pyqtSignal(dict)  # Сигнал при изменении настроек

    def __init__(self, parent=None, initial_settings=None):
        super().__init__(parent)
        self.initial_settings = initial_settings or {}
        self.init_ui()
        self.load_initial_settings()

    def init_ui(self):
        self.setWindowTitle("Настройки растра")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Вкладки
        self.tab_widget = QTabWidget()

        # Вкладка "Основные"
        basic_tab = QWidget()
        self.init_basic_tab(basic_tab)
        self.tab_widget.addTab(basic_tab, "Основные")

        # Вкладка "Улучшение"
        enhancement_tab = QWidget()
        self.init_enhancement_tab(enhancement_tab)
        self.tab_widget.addTab(enhancement_tab, "Улучшение")

        # Вкладка "Интерполяция"
        interpolation_tab = QWidget()
        self.init_interpolation_tab(interpolation_tab)
        self.tab_widget.addTab(interpolation_tab, "Интерполяция")

        layout.addWidget(self.tab_widget)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.apply_btn = QPushButton("Применить")
        self.apply_btn.clicked.connect(self.apply_settings)
        btn_layout.addWidget(self.apply_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_and_apply)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def init_basic_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Ориентация
        orientation_group = QGroupBox("Ориентация растра")
        orientation_layout = QFormLayout()

        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Горизонтальная (время по X)",
                                         "Вертикальная (время по Y)"])
        orientation_layout.addRow("Ориентация:", self.orientation_combo)

        orientation_group.setLayout(orientation_layout)
        layout.addWidget(orientation_group)

        # Временные параметры
        time_group = QGroupBox("Временные параметры")
        time_layout = QFormLayout()

        self.time_start_spin = QDoubleSpinBox()
        self.time_start_spin.setRange(0, 10000)
        self.time_start_spin.setValue(0.0)
        self.time_start_spin.setSuffix(" с")
        time_layout.addRow("Начальное время:", self.time_start_spin)

        self.time_end_spin = QDoubleSpinBox()
        self.time_end_spin.setRange(0, 10000)
        self.time_end_spin.setValue(100.0)
        self.time_end_spin.setSuffix(" с")
        time_layout.addRow("Конечное время:", self.time_end_spin)

        self.sampling_rate_spin = QDoubleSpinBox()
        self.sampling_rate_spin.setRange(1, 10000)
        self.sampling_rate_spin.setValue(100.0)
        self.sampling_rate_spin.setSuffix(" Гц")
        time_layout.addRow("Частота дискретизации:", self.sampling_rate_spin)

        time_group.setLayout(time_layout)
        layout.addWidget(time_group)

        layout.addStretch()

    def init_enhancement_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Яркость
        brightness_group = QGroupBox("Яркость")
        brightness_layout = QVBoxLayout()

        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(10, 500)
        self.brightness_slider.setValue(100)
        self.brightness_slider.setTickPosition(QSlider.TicksBelow)
        self.brightness_slider.setTickInterval(50)

        self.brightness_label = QLabel("100%")
        self.brightness_slider.valueChanged.connect(
            lambda v: self.brightness_label.setText(f"{v}%")
        )

        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_label)
        brightness_group.setLayout(brightness_layout)
        layout.addWidget(brightness_group)

        # Контраст
        contrast_group = QGroupBox("Контрастность")
        contrast_layout = QVBoxLayout()

        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(10, 500)
        self.contrast_slider.setValue(100)
        self.contrast_slider.setTickPosition(QSlider.TicksBelow)
        self.contrast_slider.setTickInterval(50)

        self.contrast_label = QLabel("100%")
        self.contrast_slider.valueChanged.connect(
            lambda v: self.contrast_label.setText(f"{v}%")
        )

        contrast_layout.addWidget(self.contrast_slider)
        contrast_layout.addWidget(self.contrast_label)
        contrast_group.setLayout(contrast_layout)
        layout.addWidget(contrast_group)

        # Дополнительные настройки
        advanced_group = QGroupBox("Дополнительно")
        advanced_layout = QFormLayout()

        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.1, 5.0)
        self.gamma_spin.setValue(1.0)
        self.gamma_spin.setSingleStep(0.1)
        advanced_layout.addRow("Гамма-коррекция:", self.gamma_spin)

        self.invert_cb = QCheckBox("Инвертировать цвета")
        advanced_layout.addRow("", self.invert_cb)

        self.threshold_cb = QCheckBox("Пороговая обработка")
        self.threshold_cb.setChecked(False)
        advanced_layout.addRow("", self.threshold_cb)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 255)
        self.threshold_spin.setValue(128)
        self.threshold_spin.setEnabled(False)
        advanced_layout.addRow("Порог:", self.threshold_spin)

        self.threshold_cb.toggled.connect(self.threshold_spin.setEnabled)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()

    def init_interpolation_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Настройки интерполяции
        interp_group = QGroupBox("Настройки интерполяции")
        interp_layout = QFormLayout()

        self.poly_order_spin = QDoubleSpinBox()
        self.poly_order_spin.setRange(1, 10)
        self.poly_order_spin.setValue(3)
        self.poly_order_spin.setDecimals(0)
        interp_layout.addRow("Порядок полинома:", self.poly_order_spin)

        self.interp_method_combo = QComboBox()
        self.interp_method_combo.addItems(["Кубический сплайн", "Полиномиальная"])
        interp_layout.addRow("Метод интерполяции:", self.interp_method_combo)

        self.num_samples_spin = QDoubleSpinBox()
        self.num_samples_spin.setRange(10, 10000)
        self.num_samples_spin.setValue(100)
        self.num_samples_spin.setDecimals(0)
        interp_layout.addRow("Количество точек:", self.num_samples_spin)

        self.auto_interpolate_cb = QCheckBox("Автоматическая интерполяция")
        self.auto_interpolate_cb.setChecked(True)
        interp_layout.addRow("", self.auto_interpolate_cb)

        interp_group.setLayout(interp_layout)
        layout.addWidget(interp_group)

        # Настройки отображения
        display_group = QGroupBox("Настройки отображения")
        display_layout = QFormLayout()

        self.show_grid_cb = QCheckBox("Показывать сетку")
        self.show_grid_cb.setChecked(True)
        display_layout.addRow("", self.show_grid_cb)

        self.show_points_cb = QCheckBox("Показывать точки оцифровки")
        self.show_points_cb.setChecked(True)
        display_layout.addRow("", self.show_points_cb)

        self.show_interpolated_cb = QCheckBox("Показывать интерполированные кривые")
        self.show_interpolated_cb.setChecked(True)
        display_layout.addRow("", self.show_interpolated_cb)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        layout.addStretch()

    def load_initial_settings(self):
        """Загружает начальные настройки."""
        if self.initial_settings:
            # Загружаем настройки из словаря
            pass  # Можно реализовать при необходимости

    def get_settings(self):
        """Возвращает текущие настройки."""
        settings = {
            'orientation': self.orientation_combo.currentIndex(),
            'time_start': self.time_start_spin.value(),
            'time_end': self.time_end_spin.value(),
            'sampling_rate': self.sampling_rate_spin.value(),
            'brightness': self.brightness_slider.value() / 100.0,
            'contrast': self.contrast_slider.value() / 100.0,
            'gamma': self.gamma_spin.value(),
            'invert_colors': self.invert_cb.isChecked(),
            'threshold_enabled': self.threshold_cb.isChecked(),
            'threshold': self.threshold_spin.value(),
            'poly_order': int(self.poly_order_spin.value()),
            'interp_method': self.interp_method_combo.currentIndex(),
            'num_samples': int(self.num_samples_spin.value()),
            'auto_interpolate': self.auto_interpolate_cb.isChecked(),
            'show_grid': self.show_grid_cb.isChecked(),
            'show_points': self.show_points_cb.isChecked(),
            'show_interpolated': self.show_interpolated_cb.isChecked()
        }
        return settings

    def apply_settings(self):
        """Применяет настройки."""
        settings = self.get_settings()
        self.settings_changed.emit(settings)

    def accept_and_apply(self):
        """Применяет настройки и закрывает диалог."""
        self.apply_settings()
        self.accept()
from PyQt5.QtWidgets import *

class ImportRasterDialog(QDialog):
    """Диалог импорта растрового изображения."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filepath = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Импорт растрового изображения")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Выбор файла
        file_group = QGroupBox("Файл")
        file_layout = QHBoxLayout()

        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        file_layout.addWidget(self.file_edit)

        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Настройки
        settings_group = QGroupBox("Настройки")
        form_layout = QFormLayout()

        # Единое разрешение (DPI)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(1, 2400)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" dpi")
        form_layout.addRow("Разрешение сканирования:", self.dpi_spin)

        # Цветовой режим
        self.color_combo = QComboBox()
        self.color_combo.addItems(["Градации серого", "RGB", "Авто"])
        form_layout.addRow("Цветовой режим:", self.color_combo)

        settings_group.setLayout(form_layout)
        layout.addWidget(settings_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.ok_btn = QPushButton("Импорт")
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def browse_file(self):
        """Открывает диалог выбора файла."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл изображения", "",
            "Images (*.bmp *.tiff *.tif *.png *.jpg *.jpeg);;All files (*.*)"
        )
        if filepath:
            self.filepath = filepath
            self.file_edit.setText(filepath)

    def get_parameters(self):
        """Возвращает параметры импорта."""
        color_mode_map = {
            "Градации серого": "L",
            "RGB": "RGB",
            "Авто": "auto"  # Будет определен автоматически
        }

        return {
            'filepath': self.filepath,
            'dpi': (self.dpi_spin.value(), self.dpi_spin.value()),  # Одинаковое по X и Y
            'color_mode': color_mode_map.get(self.color_combo.currentText(), "auto")
        }
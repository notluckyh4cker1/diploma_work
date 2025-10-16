# Главное окно приложения

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QColor, QIcon
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QFileDialog, QProgressDialog,
                             QMessageBox, QApplication, QLabel, QFrame, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QCheckBox, QFormLayout, QGroupBox, QActionGroup, QAction)
from PyQt5.QtXml import QDomDocument
from gl_widget import GLWidget

class ScaleSettingsDialog(QDialog):
    def __init__(self, scale_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка шкалы")
        self.scale_settings = scale_settings

        layout = QVBoxLayout()

        # Временная шкала
        time_group = QGroupBox("Временная шкала (горизонтальные линии)")
        time_layout = QFormLayout()

        self.time_visible = QCheckBox()
        self.time_visible.setChecked(scale_settings.time_visible)
        time_layout.addRow("Показывать временную шкалу:", self.time_visible)

        self.time_min = QDoubleSpinBox()
        self.time_min.setRange(-1e6, 1e6)
        self.time_min.setValue(scale_settings.time_min)
        time_layout.addRow("Минимальное время (с):", self.time_min)

        self.time_max = QDoubleSpinBox()
        self.time_max.setRange(-1e6, 1e6)
        self.time_max.setValue(scale_settings.time_max)
        time_layout.addRow("Максимальное время (с):", self.time_max)

        self.time_step = QDoubleSpinBox()
        self.time_step.setRange(0.001, 1e6)
        self.time_step.setValue(scale_settings.time_step)
        time_layout.addRow("Шаг времени (с):", self.time_step)

        time_group.setLayout(time_layout)
        layout.addWidget(time_group)

        # Шкала амплитуд
        amp_group = QGroupBox("Шкала амплитуд (вертикальные линии)")
        amp_layout = QFormLayout()

        self.amp_visible = QCheckBox()
        self.amp_visible.setChecked(scale_settings.amplitude_visible)
        amp_layout.addRow("Показывать шкалу амплитуд:", self.amp_visible)

        self.amp_min = QDoubleSpinBox()
        self.amp_min.setRange(-1e6, 1e6)
        self.amp_min.setValue(scale_settings.amplitude_min)
        amp_layout.addRow("Минимальная амплитуда:", self.amp_min)

        self.amp_max = QDoubleSpinBox()
        self.amp_max.setRange(-1e6, 1e6)
        self.amp_max.setValue(scale_settings.amplitude_max)
        amp_layout.addRow("Максимальная амплитуда:", self.amp_max)

        self.amp_step = QDoubleSpinBox()
        self.amp_step.setRange(0.001, 1e6)
        self.amp_step.setValue(scale_settings.amplitude_step)
        amp_layout.addRow("Шаг амплитуды:", self.amp_step)

        amp_group.setLayout(amp_layout)
        layout.addWidget(amp_group)

        # Кнопки
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.validate_and_accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        # Подключаем сигналы валидации
        self.time_min.valueChanged.connect(self.validate_values)
        self.time_max.valueChanged.connect(self.validate_values)
        self.amp_min.valueChanged.connect(self.validate_values)
        self.amp_max.valueChanged.connect(self.validate_values)

        # Первоначальная валидация
        self.validate_values()

    def validate_values(self):
        """Проверка корректности введенных значений"""
        time_valid = self.time_max.value() > self.time_min.value()
        amp_valid = self.amp_max.value() > self.amp_min.value()

        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(time_valid and amp_valid)

        if not time_valid:
            self.time_max.setStyleSheet("background-color: #ffdddd;")
        else:
            self.time_max.setStyleSheet("")

        if not amp_valid:
            self.amp_max.setStyleSheet("background-color: #ffdddd;")
        else:
            self.amp_max.setStyleSheet("")

    def validate_and_accept(self):
        """Проверка значений перед принятием"""
        if self.time_max.value() <= self.time_min.value():
            QMessageBox.warning(self, "Ошибка", "Максимальное время должно быть больше минимального")
            return

        if self.amp_max.value() <= self.amp_min.value():
            QMessageBox.warning(self, "Ошибка", "Максимальная амплитуда должна быть больше минимальной")
            return

        self.accept()

    def accept(self):
        """Сохраняем настройки перед закрытием"""
        self.scale_settings.time_visible = self.time_visible.isChecked()
        self.scale_settings.time_min = self.time_min.value()
        self.scale_settings.time_max = self.time_max.value()
        self.scale_settings.time_step = self.time_step.value()

        self.scale_settings.amplitude_visible = self.amp_visible.isChecked()
        self.scale_settings.amplitude_min = self.amp_min.value()
        self.scale_settings.amplitude_max = self.amp_max.value()
        self.scale_settings.amplitude_step = self.amp_step.value()

        super().accept()


class ProjectManager:
    @staticmethod
    def save_project(gl_widget, file_path):
        """Сохраняет проект в XML файл (исправленная версия)"""
        doc = QDomDocument()

        # Создаем правильный XML-заголовок
        header = doc.createProcessingInstruction(
            "xml",
            'version="1.0" encoding="UTF-8"'
        )
        doc.appendChild(header)

        # Корневой элемент
        root = doc.createElement("seismogram_project")
        doc.appendChild(root)

        # 1. Сохраняем информацию о программе
        info = doc.createElement("info")
        info.appendChild(doc.createTextNode("Проект аналоговых сейсмограмм"))
        root.appendChild(info)

        # 2. Сохраняем растры
        rasters = doc.createElement("rasters")
        root.appendChild(rasters)

        for obj in gl_widget.raster_objects:
            raster = doc.createElement("raster")

            # Основные атрибуты
            raster.setAttribute("file_path", obj.file_path)
            raster.setAttribute("x", str(obj.position.x()))
            raster.setAttribute("y", str(obj.position.y()))
            raster.setAttribute("width", str(obj.size.width()))
            raster.setAttribute("height", str(obj.size.height()))
            raster.setAttribute("rotation", str(obj.rotation_angle))

            # Настройки шкалы
            scale = doc.createElement("scale_settings")
            scale.setAttribute("time_visible", str(int(obj.scale_settings.time_visible)))
            scale.setAttribute("amplitude_visible", str(int(obj.scale_settings.amplitude_visible)))
            scale.setAttribute("time_min", str(obj.scale_settings.time_min))
            scale.setAttribute("time_max", str(obj.scale_settings.time_max))
            scale.setAttribute("time_step", str(obj.scale_settings.time_step))
            scale.setAttribute("amplitude_min", str(obj.scale_settings.amplitude_min))
            scale.setAttribute("amplitude_max", str(obj.scale_settings.amplitude_max))
            scale.setAttribute("amplitude_step", str(obj.scale_settings.amplitude_step))
            raster.appendChild(scale)

            rasters.appendChild(raster)

        # 3. Сохраняем кривые (исправленный порядок координат)
        if hasattr(gl_widget, 'curves') and gl_widget.curves:
            curves = doc.createElement("curves")
            root.appendChild(curves)

            for curve in gl_widget.curves:
                curve_elem = doc.createElement("curve")
                curve_elem.setAttribute("raster_index", str(gl_widget.raster_objects.index(curve.raster_object)))
                curve_elem.setAttribute("color_r", str(curve.color[0]))
                curve_elem.setAttribute("color_g", str(curve.color[1]))
                curve_elem.setAttribute("color_b", str(curve.color[2]))
                curve_elem.setAttribute("color_a", str(curve.color[3]))
                curve_elem.setAttribute("line_width", str(curve.line_width))

                points = doc.createElement("points")
                for point in curve.points:
                    point_elem = doc.createElement("point")
                    point_elem.setAttribute("x", str(point.x()))
                    point_elem.setAttribute("y", str(point.y()))
                    points.appendChild(point_elem)

                curve_elem.appendChild(points)
                curves.appendChild(curve_elem)

        # 4. Сохраняем настройки вида
        view = doc.createElement("view")
        view.setAttribute("zoom", str(gl_widget.zoom))
        view.setAttribute("pan_x", str(gl_widget.pan.x()))
        view.setAttribute("pan_y", str(gl_widget.pan.y()))
        root.appendChild(view)

        # Записываем в файл как чистый XML
        with open(file_path, 'w', encoding='utf-8') as f:
            # Используем toByteArray для корректного сохранения
            xml_data = doc.toByteArray(4)  # 4 - это отступ
            f.write(xml_data.data().decode('utf-8'))

class MainWindow(QMainWindow):
    objectCutProgress = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Аналоговые сейсмограммы")

        self.gl_widget = GLWidget(self)
        self.setCentralWidget(self.gl_widget)

        # Создаём панели
        self.mode_panel = self._create_mode_panel()
        self.selection_panel = self._create_selection_panel()
        self.tool_panel = self._create_tool_panel()

        # Скрываем панели по умолчанию
        self.mode_panel.setVisible(False)
        self.selection_panel.setVisible(False)
        self.tool_panel.setVisible(False)

        self.add_action = None  # Добавляем инициализацию атрибута

        # Позиционируем панели поверх gl_widget, не используя layout для них
        self._position_panels()

        self._create_menu()
        self._connect_signals()

        self.gl_widget.objectActivated.connect(self._on_object_activated)

        # Меню шкалы (изначально полностью неактивно)
        self.scale_menu = self.menuBar().addMenu("Шкала")
        self.scale_settings_action = self.scale_menu.addAction("Настроить шкалу")
        self.scale_settings_action.triggered.connect(self._show_scale_settings)
        self.scale_toggle_action = self.scale_menu.addAction("Показать шкалу")
        self.scale_toggle_action.setEnabled(False)  # Изначально недоступна
        self.scale_toggle_action.triggered.connect(self._toggle_scale)
        self.scale_menu.setEnabled(False)

        # Меню векторизации (изначально неактивно)
        self._create_vectorization_menu()
        self.vectorization_menu.setEnabled(False)

        self.gl_widget.curvesChanged.connect(self._update_save_button_state)
        self.curves_actions_created = False  # Флаг, созданы ли уже действия

        self.cut_instruction_label = QLabel("", self)
        self.cut_instruction_label.setStyleSheet("""
                QLabel {
                    background: rgba(50, 50, 50, 220);
                    color: white;
                    padding: 10px 15px;
                    border-radius: 5px;
                    font: 12pt "Arial";
                    border: 2px solid #4CAF50;
                }
            """)
        self.cut_instruction_label.setAlignment(Qt.AlignCenter)
        self.cut_instruction_label.hide()
        self.cutting_object = None  # Объект, который сейчас режем

    def _update_save_button_state(self, has_curves):
        """Обновляет состояние кнопки сохранения"""
        if hasattr(self, 'save_curves_action'):
            # Проверяем, что есть хотя бы одна кривая с минимум 2 точками
            valid_curves = has_curves and any(
                len(c.points) >= 2
                for c in (self.gl_widget.curves if hasattr(self.gl_widget, 'curves') else [])
            )
            self.save_curves_action.setEnabled(valid_curves)

    def _save_project(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить проект как XML",
            "",
            "XML Files (*.xml);;All Files (*)"
        )

        if not file_path:
            return

        # Добавляем расширение .xml если его нет
        if not file_path.lower().endswith('.xml'):
            file_path += '.xml'

        try:
            ProjectManager.save_project(self.gl_widget, file_path)
            self.show_toast(f"Проект сохранен в {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения",
                                 f"Не удалось сохранить проект:\n{str(e)}")

    def _position_panels(self):
        x = 20
        y = 20
        spacing = 10

        for panel in [self.mode_panel, self.selection_panel, self.tool_panel]:
            panel.adjustSize()
            panel.move(x, y)
            y += panel.height() + spacing

    def _create_menu(self):
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu("Файл")  # Сохраняем ссылку на меню

        open_action = self.file_menu.addAction("Открыть изображение")
        open_action.triggered.connect(self._open_image)

        self.add_action = self.file_menu.addAction("Добавить изображение")
        self.add_action.setVisible(False)
        self.add_action.triggered.connect(self._add_image)

        self.file_menu.addSeparator()

        self.save_project_action = self.file_menu.addAction("Сохранить проект...")
        self.save_project_action.setVisible(False)
        self.save_project_action.triggered.connect(self._save_project)

    def _create_mode_panel(self):
        panel = QWidget(self)
        panel.setStyleSheet(self._panel_style())
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Режим работы")
        title.setStyleSheet("color: gray; font-weight: normal; background: transparent; border: none;")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #bbb;")
        layout.addWidget(line)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)

        self.move_mode_btn = QPushButton("Режим движения")
        self.move_mode_btn.setCheckable(True)
        buttons_layout.addWidget(self.move_mode_btn)

        self.raster_mode_btn = QPushButton("Работа с растром")
        self.raster_mode_btn.setCheckable(True)
        buttons_layout.addWidget(self.raster_mode_btn)

        layout.addLayout(buttons_layout)

        return panel

    def _create_selection_panel(self):
        panel = QWidget(self)
        panel.setStyleSheet(self._panel_style())
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Выделение растра")
        title.setStyleSheet("color: gray; font-weight: normal; background: transparent; border: none;")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #bbb;")
        layout.addWidget(line)

        self.select_raster_btn = QPushButton("Выделить растр")
        self.select_raster_btn.setCheckable(True)
        layout.addWidget(self.select_raster_btn)

        # Добавьте эту кнопку для режима нарезки
        self.cut_raster_btn = QPushButton("Обрезать растр")
        self.cut_raster_btn.setCheckable(True)
        layout.addWidget(self.cut_raster_btn)

        return panel

    def _create_tool_panel(self):
        panel = QWidget(self)
        panel.setStyleSheet(self._panel_style())
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Инструменты")
        title.setStyleSheet("color: gray; font-weight: normal; background: transparent; border: none;")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #bbb;")
        layout.addWidget(line)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)

        self.rotate_left_btn = QPushButton("↺ 90°")
        buttons_layout.addWidget(self.rotate_left_btn)

        self.rotate_right_btn = QPushButton("↻ 90°")
        buttons_layout.addWidget(self.rotate_right_btn)

        self.rotate_custom_btn = QPushButton("Ввести угол")
        buttons_layout.addWidget(self.rotate_custom_btn)

        layout.addLayout(buttons_layout)

        return panel

    def _create_vectorization_menu(self):
        """Создание меню векторизации"""
        self.vectorization_menu = self.menuBar().addMenu("Векторизация")

        self.start_vector_action = self.vectorization_menu.addAction("Начать векторизацию")
        self.start_vector_action.triggered.connect(self._start_vectorization)
        self.start_vector_action.setEnabled(False)  # Изначально недоступно

        self.finish_vector_action = self.vectorization_menu.addAction("Завершить векторизацию")
        self.finish_vector_action.setEnabled(False)
        self.finish_vector_action.triggered.connect(self._finish_vectorization)

        self.finish_curve_action = self.vectorization_menu.addAction("Завершить текущую кривую")
        self.finish_curve_action.setEnabled(False)
        self.finish_curve_action.triggered.connect(self._finish_current_curve)

        self.color_menu = self.vectorization_menu.addMenu("Цвет кривой")
        self.color_menu.setEnabled(False)

        # Создаем группу действий для эксклюзивного выбора
        self.color_action_group = QActionGroup(self)
        self.color_action_group.setExclusive(True)  # Только один выбранный цвет

        colors = [
            ("Красный", (1.0, 0.0, 0.0, 1.0)),
            ("Зеленый", (0.0, 1.0, 0.0, 1.0)),
            ("Синий", (0.0, 0.0, 1.0, 1.0)),
            ("Пурпурный", (1.0, 0.0, 1.0, 1.0)),
            ("Желтый", (1.0, 1.0, 0.0, 1.0)),
            ("Голубой", (0.0, 1.0, 1.0, 1.0)),
            ("Черный", (0.0, 0.0, 0.0, 1.0))
        ]

        for name, color in colors:
            action = QAction(name, self)
            action.setCheckable(True)

            # Создаем цветную иконку
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)))
            action.setIcon(QIcon(pixmap))

            action.setData(color)
            self.color_action_group.addAction(action)
            self.color_menu.addAction(action)

            # Подключаем сигнал
            action.triggered.connect(lambda checked, c=color: self._set_curve_color(c))

        # Устанавливаем красный цвет по умолчанию (с галочкой)
        if self.color_action_group.actions():
            self.color_action_group.actions()[0].setChecked(True)
            self._current_color = colors[0][1]

        self.clear_last_curve_action = self.vectorization_menu.addAction("Очистить предыдущую кривую")
        self.clear_last_curve_action.setEnabled(False)
        self.clear_last_curve_action.triggered.connect(self._clear_last_curve)

        self.clear_curves_action = self.vectorization_menu.addAction("Очистить все кривые")
        self.clear_curves_action.setEnabled(False)
        self.clear_curves_action.triggered.connect(self._clear_all_curves)

    def _create_curves_actions(self):
        """Создает действия для работы с кривыми при первом использовании"""
        if not self.curves_actions_created:
            self.save_curves_action = QAction("Сохранить кривые...", self)
            self.save_curves_action.triggered.connect(self._save_curves)
            self.save_curves_action.setEnabled(False)

            self.load_curves_action = QAction("Загрузить кривые...", self)
            self.load_curves_action.triggered.connect(self._load_curves)
            self.load_curves_action.setEnabled(False)

            self.curves_actions_created = True

    def _update_curves_actions_visibility(self, visible):
        """Управляет видимостью действий для кривых"""
        self._create_curves_actions()  # Убедимся, что действия созданы

        # Удаляем старые действия если они есть
        if self.save_curves_action in self.file_menu.actions():
            self.file_menu.removeAction(self.save_curves_action)
        if self.load_curves_action in self.file_menu.actions():
            self.file_menu.removeAction(self.load_curves_action)

        if visible:
            # Добавляем разделитель и действия
            self.file_menu.addSeparator()
            self.file_menu.addAction(self.save_curves_action)
            self.file_menu.addAction(self.load_curves_action)

    def _start_vectorization(self):
        if not hasattr(self.gl_widget, 'active_object') or not self.gl_widget.active_object:
            QMessageBox.warning(self, "Ошибка",
                                "Нет активного растрового объекта.\n"
                                "Выберите растр двойным кликом перед началом векторизации.")
            return

        try:
            if not self.gl_widget.start_vectorization():
                raise Exception("Ошибка! Не удалось начать векторизацию!")

            # Включаем все кнопки кроме "Начать векторизацию"
            self.start_vector_action.setEnabled(False)
            self.finish_vector_action.setEnabled(True)
            self.finish_curve_action.setEnabled(True)
            self.color_menu.setEnabled(True)
            self.clear_last_curve_action.setEnabled(True)  # Всегда доступна при векторизации
            self.clear_curves_action.setEnabled(True)  # Всегда доступна при векторизации

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка начала векторизации:\n{str(e)}")
            self.gl_widget.vectorization_mode = False
            self.gl_widget.setCursor(Qt.ArrowCursor)

    def _finish_vectorization(self):
        """Завершение режима векторизации и сброс состояния кнопок"""
        try:
            # Завершаем векторизацию в виджете
            if not self.gl_widget.finish_vectorization():
                QMessageBox.warning(self, "Предупреждение", "Не удалось корректно завершить векторизацию")

            # Сбрасываем состояние UI
            self.start_vector_action.setEnabled(True)  # Можно начать снова
            self.finish_vector_action.setEnabled(False)
            self.finish_curve_action.setEnabled(False)
            self.clear_last_curve_action.setEnabled(False)
            self.clear_curves_action.setEnabled(False)
            # Цвет остается доступным всегда

        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Критическая ошибка при завершении векторизации:\n{str(e)}")

    def _finish_current_curve(self):
        """Завершение текущей кривой"""
        if not hasattr(self.gl_widget, 'finish_current_curve'):
            QMessageBox.warning(self, "Ошибка", "Функция завершения кривой недоступна")
            return

        success = self.gl_widget.finish_current_curve()

        if not success:
            QMessageBox.warning(self, "Ошибка",
                                "Не удалось завершить кривую.\n"
                                "Убедитесь, что кривая содержит хотя бы 2 точки")

    def _set_curve_color(self, color):
        """Установка цвета кривой"""
        try:
            # Проверяем корректность цвета
            if not color or len(color) != 4:
                color = (1.0, 0.0, 0.0, 1.0)  # Красный по умолчанию при ошибке

            self._current_color = color

            # Обновляем цвет в виджете OpenGL
            if hasattr(self.gl_widget, 'current_color'):
                self.gl_widget.current_color = color

            # Обновляем текущую кривую
            if hasattr(self.gl_widget, 'current_curve') and self.gl_widget.current_curve:
                self.gl_widget.current_curve.color = color

            self.gl_widget.update()

        except Exception as e:
            print(f"Ошибка установки цвета: {str(e)}")
            # Восстанавливаем красный цвет
            self._set_curve_color((1.0, 0.0, 0.0, 1.0))

    def _clear_last_curve(self):
        """Обработчик с гарантированным обновлением"""
        try:
            before_count = len(self.gl_widget.curves)
            success = self.gl_widget.clear_last_curve()

            if not success and len(self.gl_widget.curves) == before_count:
                QMessageBox.warning(self, "Ошибка", "Кривая не удалилась")
            else:
                # Принудительное обновление, даже если не было изменений
                self.gl_widget.update()

        except Exception as e:
            print(f"Ошибка: {e}")

    def _clear_all_curves(self):
        """Обработчик с гарантированным обновлением"""
        try:
            success = self.gl_widget.clear_all_curves()

            if not success and self.gl_widget.curves:
                QMessageBox.warning(self, "Ошибка", "Кривые не очистились")
            else:
                # Всегда обновляем виджет
                self.gl_widget.update()

        except Exception as e:
            print(f"Ошибка: {e}")

    def _save_curves(self):
        if not hasattr(self.gl_widget, 'curves') or not self.gl_widget.curves:
            QMessageBox.warning(self, "Ошибка", "Нет кривых для сохранения")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить кривые", "", "Text Files (*.txt)"
        )

        if file_path:
            if not file_path.endswith('.txt'):
                file_path += '.txt'

            if self.gl_widget.save_curves_to_file(file_path):
                self.show_toast("Кривые успешно сохранены")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить кривые")

    def _load_curves(self):
        if not hasattr(self.gl_widget, 'active_object') or not self.gl_widget.active_object:
            QMessageBox.warning(self, "Ошибка", "Сначала активируйте растр")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить кривые", "", "Text Files (*.txt)"
        )

        if file_path:
            try:
                if self.gl_widget.load_curves_from_file(file_path):
                    self.show_toast("Кривые успешно загружены")
                    # Обновляем состояние кнопки сохранения
                    self.save_curves_action.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def _enable_raster_cutting(self, enabled):
        """Включает/выключает режим нарезки растра"""
        self.cut_raster_btn.setChecked(enabled)
        self.gl_widget.set_cut_mode(enabled)
        if enabled:
            self.select_raster_btn.setChecked(False)
            self.gl_widget.set_selection_enabled(False)
            self.show_cut_instruction(
                "Дважды кликните по растру для выбора и расположения на границе растра первой точки полигона."
            )
        else:
            self.hide_cut_instruction()
            self.gl_widget.set_selection_enabled(False)
        self.gl_widget.update()

    def show_cut_instruction(self, text):
        """Показывает инструкцию по нарезке"""
        self.cut_instruction_label.setText(text)
        self.cut_instruction_label.adjustSize()
        x = (self.width() - self.cut_instruction_label.width()) // 2
        y = 20
        self.cut_instruction_label.move(x, y)
        self.cut_instruction_label.show()

    def hide_cut_instruction(self):
        """Скрывает инструкцию по нарезке"""
        self.cut_instruction_label.hide()

    def _handle_cut_progress(self, value):
        """Обработчик прогресса операции нарезки"""
        if not hasattr(self, '_cut_progress_dialog'):
            self._cut_progress_dialog = QProgressDialog(
                "Выполняется обрезка...",
                "Отмена",
                0, 100,
                self
            )
            self._cut_progress_dialog.setStyleSheet("""
                QProgressDialog {
                    background: rgba(50, 50, 50, 200);
                    color: white;
                }
                QProgressBar {
                    border: 1px solid #444;
                    border-radius: 3px;
                    text-align: center;
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #555, stop:1 #333
                    );
                }
                QProgressBar::chunk {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6a9, stop:1 #4a7
                    );
                }
                QLabel {
                    color: white;
                }
            """)
            self._cut_progress_dialog.setWindowTitle("Обрезка")
            self._cut_progress_dialog.setWindowModality(True)
            self._cut_progress_dialog.show()

        self._cut_progress_dialog.setValue(value)

        if value >= 100:
            QTimer.singleShot(500, self._close_cut_progress)

    def _close_cut_progress(self):
        """Закрывает диалог прогресса нарезки"""
        if hasattr(self, '_cut_progress_dialog'):
            self._cut_progress_dialog.close()
            del self._cut_progress_dialog

    def _panel_style(self):
        return """
            QWidget {
                background: rgba(240, 240, 240, 0.9);
                border: 1px solid #aaa;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                padding: 5px 10px;
                min-width: 120px;
                border: 1px solid #888;
                border-radius: 3px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f6f7fa, stop:1 #dadbde);
            }
            QPushButton:checked {
                background: #b0d0ff;
            }
        """

    def _connect_signals(self):
        self.move_mode_btn.clicked.connect(self._activate_move_mode)
        self.raster_mode_btn.clicked.connect(self._activate_raster_mode)
        self.select_raster_btn.clicked.connect(self._enable_raster_selection)

        self.rotate_left_btn.clicked.connect(lambda: self.gl_widget.rotate(-90))
        self.rotate_right_btn.clicked.connect(lambda: self.gl_widget.rotate(90))
        self.rotate_custom_btn.clicked.connect(self._show_angle_dialog)

        self.cut_raster_btn.clicked.connect(self._enable_raster_cutting)

    def _show_scale_settings(self):
        if not hasattr(self.gl_widget, 'active_object') or not self.gl_widget.active_object:
            QMessageBox.warning(self, "Ошибка",
                                "Нет активного растрового объекта.\n"
                                "Дважды кликните по растру, чтобы активировать его.")
            return

        dialog = ScaleSettingsDialog(self.gl_widget.active_object.scale_settings, self)
        if dialog.exec_() == QDialog.Accepted:
            # Только после успешной настройки делаем кнопку доступной
            self.scale_toggle_action.setEnabled(True)
            self.gl_widget.update()

    def _toggle_scale(self):
        if not self.gl_widget.active_object:
            return

        scale = self.gl_widget.active_object.scale_settings
        if scale.time_visible or scale.amplitude_visible:
            scale.time_visible = False
            scale.amplitude_visible = False
            self.scale_toggle_action.setText("Показать шкалу")
        else:
            scale.time_visible = True
            scale.amplitude_visible = True
            self.scale_toggle_action.setText("Убрать шкалу")

        self.gl_widget.update()

    def _show_angle_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Точный поворот")
        dialog.setFixedSize(300, 150)

        layout = QVBoxLayout(dialog)

        # Создаем контейнер для ввода угла
        angle_layout = QHBoxLayout()
        angle_label = QLabel("Угол (°):")
        angle_layout.addWidget(angle_label)

        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-360.0, 360.0)
        self.angle_spin.setDecimals(2)  # Две цифры после запятой
        self.angle_spin.setValue(0.0)
        self.angle_spin.setSingleStep(0.01)  # Шаг изменения 0.01
        angle_layout.addWidget(self.angle_spin)

        # Кнопки для быстрого изменения сотых долей
        btn_layout = QVBoxLayout()
        up_btn = QPushButton("▲")
        up_btn.setFixedWidth(1)
        up_btn.clicked.connect(lambda: self.angle_spin.setValue(
            round(self.angle_spin.value() + 0.01, 2)))
        down_btn = QPushButton("▼")
        down_btn.setFixedWidth(1)
        down_btn.clicked.connect(lambda: self.angle_spin.setValue(
            round(self.angle_spin.value() - 0.01, 2)))
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        angle_layout.addLayout(btn_layout)

        layout.addLayout(angle_layout)

        # Кнопки подтверждения/отмены
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._apply_rotation(dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec_()

    def _apply_rotation(self, dialog):
        angle = self.angle_spin.value()
        self.gl_widget.rotate(angle)
        dialog.accept()

    def _activate_move_mode(self):
        self.raster_mode_btn.setChecked(False)
        self.move_mode_btn.setChecked(True)
        self.move_mode_btn.setEnabled(False)
        self.raster_mode_btn.setEnabled(True)

        self.gl_widget.set_mode_move(True)
        self.gl_widget.set_selection_enabled(False)  # Отключаем выделение
        self.select_raster_btn.setChecked(False)  # Сбрасываем состояние кнопки

        self.gl_widget.setCursor(Qt.ArrowCursor)
        self.selection_panel.setVisible(False)

    def _activate_raster_mode(self):
        self.move_mode_btn.setChecked(False)
        self.raster_mode_btn.setChecked(True)
        self.raster_mode_btn.setEnabled(False)
        self.move_mode_btn.setEnabled(True)

        self.selection_panel.setVisible(True)
        self.tool_panel.setVisible(False)

        self.gl_widget.set_mode_move(False)
        self.gl_widget.set_selection_enabled(False)
        # self.gl_widget.center_camera_on_raster() - оставляем там, где пользователь изволит

    def _enable_raster_selection(self):
        self.gl_widget.set_selection_enabled(self.select_raster_btn.isChecked())

    def _on_object_activated(self, active):
        self.tool_panel.setVisible(active)
        self.scale_menu.setEnabled(active)  # Меню шкалы доступно только при активном растре
        self.vectorization_menu.setEnabled(active)  # Меню векторизации доступно только при активном растре
        self.color_menu.setEnabled(active)  # Активируем меню цветов
        self._update_curves_actions_visibility(active) # Обновляем видимость действий для кривых
        if active:
            has_curves = hasattr(self.gl_widget, 'curves') and bool(self.gl_widget.curves)
            self.save_curves_action.setEnabled(has_curves)
            self.load_curves_action.setEnabled(True)
            # При активации объекта всегда выключаем кнопку показа шкалы
            self.scale_toggle_action.setEnabled(False)
            self.scale_toggle_action.setText("Показать шкалу")
            self.start_vector_action.setEnabled(True)
        else:
            # Если объект деактивирован, выключаем режим векторизации
            if self.gl_widget.vectorization_mode:
                self._finish_vectorization()
        if active and hasattr(self.gl_widget, 'curves'):
            self._update_save_button_state(bool(self.gl_widget.curves))

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        try:
            if hasattr(self.gl_widget, 'cleanup'):
                self.gl_widget.cleanup()
        except Exception as e:
            print(f"Ошибка при очистке ресурсов: {str(e)}")
        super().closeEvent(event)

    def _add_image(self):
        """Добавление нового изображения к текущей сцене"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Добавить изображение",
            "",
            "Images (*.bmp *.tif *.tiff *.png *.jpg *.jpeg)"
        )

        if not file_path:
            return

        try:
            # Закрываем предыдущие уведомления перед операцией
            if hasattr(self, '_current_toast'):
                try:
                    self._current_toast.hide()
                except RuntimeError:
                    pass  # Игнорируем ошибки удаленного объекта

            # Добавляем изображение
            success = self.gl_widget.add_image(file_path, self._progress_callback)

            if success:
                # Формируем сообщение после успешного добавления
                try:
                    last_obj = self.gl_widget.raster_objects[-1]
                    self.show_toast(
                        f"Добавлено изображение: {file_path.split('/')[-1]}\n"
                        f"Размер: {last_obj.size.width():.0f}×{last_obj.size.height():.0f} px\n"
                        f"Физический размер: "
                        f"{last_obj.get_physical_size_mm().width():.1f}×"
                        f"{last_obj.get_physical_size_mm().height():.1f} мм"
                    )
                except (IndexError, AttributeError, RuntimeError) as e:
                    print(f"Ошибка при показе уведомления: {str(e)}")
            self.save_project_action.setVisible(True)

        except Exception as e:
            # Сначала скрываем прогресс-диалог, если он есть
            if hasattr(self, '_progress_dialog'):
                try:
                    self._progress_dialog.hide()
                except RuntimeError:
                    pass

            QMessageBox.critical( self, "Ошибка", f"Не удалось добавить изображение:\n{str(e)}")

    def _open_image(self):
        """Загрузка нового изображения (очищает предыдущее)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть изображение",
            "",
            "Images (*.bmp *.tif *.tiff *.png *.jpg *.jpeg)"
        )

        if not file_path:
            return

        try:
            # Закрываем предыдущие уведомления
            if hasattr(self, '_current_toast'):
                try:
                    self._current_toast.hide()
                except RuntimeError:
                    pass

            # Загружаем изображение
            self.gl_widget.load_image(file_path, self._progress_callback)

            # Формируем информационное сообщение
            try:
                img_info = (
                    f"Загружено изображение: {file_path.split('/')[-1]}\n"
                    f"Размер: {self.gl_widget.image_loader.width}×{self.gl_widget.image_loader.height} px\n"
                    f"Физический размер: "
                    f"{self.gl_widget.raster_objects[0].get_physical_size_mm().width():.1f}×"
                    f"{self.gl_widget.raster_objects[0].get_physical_size_mm().height():.1f} мм"
                )
                self.show_toast(img_info, timeout=5000)  # Увеличиваем время показа
            except (IndexError, AttributeError, RuntimeError) as e:
                print(f"Ошибка при формировании информации: {str(e)}")

            # Активируем интерфейс
            self._update_curves_actions_visibility(True)
            self.add_action.setVisible(True)
            self.save_project_action.setVisible(True)
            self.scale_menu.setEnabled(False)  # Меню шкалы неактивно
            self.vectorization_menu.setEnabled(False)  # Меню векторизации неактивно
            self.mode_panel.setVisible(True)
            self._activate_move_mode()

        except Exception as e:
            # Скрываем прогресс-диалог при ошибке
            if hasattr(self, '_progress_dialog'):
                try:
                    self._progress_dialog.hide()
                except RuntimeError:
                    pass

            QMessageBox.critical( self, "Ошибка", f"Не удалось загрузить изображение:\n{str(e)}")

    def _progress_callback(self, percent):
        """Обработчик прогресса операций загрузки"""
        # Инициализация диалога только при начале операции (percent == 0)
        if percent == 0:
            if hasattr(self, '_progress_dialog'):
                self._progress_dialog.deleteLater()

            self._progress_dialog = QProgressDialog("Обработка изображения...", "Отмена", 0, 100, self)
            self._progress_dialog.setWindowTitle("Прогресс")
            self._progress_dialog.setWindowModality(True)
            self._progress_dialog.setAutoClose(True)  # Автоматически закрывать при завершении
            self._progress_dialog.show()

        # Обновляем прогресс только если диалог существует
        if hasattr(self, '_progress_dialog'):
            self._progress_dialog.setValue(percent)
            QApplication.processEvents()

            if self._progress_dialog.wasCanceled():
                self._progress_dialog.deleteLater()
                del self._progress_dialog
                raise Exception("Операция отменена пользователем")

    def show_toast(self, message, timeout=7000):
        """Всплывающее уведомление с автоисчезновением"""
        # Удаляем предыдущее уведомление безопасным способом
        if hasattr(self, '_current_toast'):
            try:
                if self._current_toast:
                    self._current_toast.deleteLater()
            except RuntimeError:
                pass  # Объект уже был удален

        # Создаем новое уведомление
        self._current_toast = QLabel(message, self)
        self._current_toast.setObjectName("ToastNotification")
        self._current_toast.setStyleSheet("""
            QLabel#ToastNotification {
                background: rgba(50, 50, 50, 220);
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                font: 12px;
                border: 1px solid #444;
            }
        """)
        self._current_toast.setAlignment(Qt.AlignCenter)
        self._current_toast.adjustSize()

        # Позиционируем
        x = (self.width() - self._current_toast.width()) // 2
        y = self.height() - self._current_toast.height() - 30
        self._current_toast.move(x, y)
        self._current_toast.show()

        # Автоудаление с проверкой
        def safe_delete():
            if hasattr(self, '_current_toast'):
                try:
                    self._current_toast.deleteLater()
                    del self._current_toast
                except RuntimeError:
                    pass

        QTimer.singleShot(timeout, safe_delete) # Удаление через timeout миллисекунд
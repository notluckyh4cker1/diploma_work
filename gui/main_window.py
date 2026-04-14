from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QToolBar, QAction, QStatusBar, QFileDialog,
                             QInputDialog, QMessageBox, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from pathlib import Path

# Исправленные импорты
from models.project import Project
from models.trace import Trace, Interval, PointType
from models.workspace_params import WorkspaceSettings
from models.seismic_data import SeismicTrace, DigitizationInterval
from core.digitizer_engine import DigitizerEngine
from gui.raster_canvas import RasterCanvas
from gui.controls_panel import ControlsPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seismograms Digitizer v1.0")
        self.setGeometry(100, 100, 1200, 800)

        self.current_project = None
        self.workspace_settings = WorkspaceSettings()

        self.setup_ui()
        self.setup_menu()
        self.setup_statusbar()

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)

        # Холст для отображения растра
        self.canvas = RasterCanvas()
        layout.addWidget(self.canvas, stretch=3)

        # Панель управления
        self.controls_panel = ControlsPanel()
        self.controls_panel.mode_changed.connect(self.on_mode_changed)
        self.controls_panel.undo_requested.connect(self.canvas.undo)
        self.controls_panel.redo_requested.connect(self.canvas.redo)
        self.controls_panel.interpolate_requested.connect(self.interpolate_current_interval)
        self.controls_panel.remove_trend_requested.connect(self.remove_trend_current_interval)
        self.controls_panel.finish_interval_requested.connect(self.finish_current_interval)
        self.controls_panel.manage_traces_requested.connect(self.show_trace_manager)
        self.controls_panel.finish_trace_requested.connect(self.finish_current_trace)

        self.controls_panel.trace_selected.connect(self.on_trace_selected_from_selector)

        layout.addWidget(self.controls_panel, stretch=1)

        self.canvas.mouse_moved.connect(self.update_coordinates) # сигнал движения мыши после создания канваса

    def setup_menu(self):
        """Настройка меню"""
        menubar = self.menuBar()

        # Меню File
        file_menu = menubar.addMenu("Файл")

        new_action = QAction("Новый проект", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("Открыть проект...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        save_action = QAction("Сохранить проект", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Сохранить как...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        import_raster_action = QAction("Импортировать растер...", self)
        import_raster_action.triggered.connect(self.import_raster)
        file_menu.addAction(import_raster_action)

        export_sac_action = QAction("Экспорт в SAC...", self)
        export_sac_action.triggered.connect(self.export_sac)
        file_menu.addAction(export_sac_action)

        # Меню Edit
        edit_menu = menubar.addMenu("Правка")

        undo_action = QAction("Отменить", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.canvas.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Повторить", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.canvas.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        settings_action = QAction("Настройки проекта...", self)
        settings_action.triggered.connect(self.project_settings)
        edit_menu.addAction(settings_action)

        # Меню View
        view_menu = menubar.addMenu("Вид")

        zoom_in_action = QAction("Приблизить", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(lambda: self.canvas.scale(1.2, 1.2))
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Отдалить", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(lambda: self.canvas.scale(0.8, 0.8))
        view_menu.addAction(zoom_out_action)

        fit_view_action = QAction("Подогнать под размер", self)
        fit_view_action.setShortcut(QKeySequence("Ctrl+F"))
        fit_view_action.triggered.connect(self.fit_view)
        view_menu.addAction(fit_view_action)

    def setup_statusbar(self):
        """Настройка строки состояния"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Добавляем информационные метки
        self.zoom_label = QLabel("Масштаб: 100%")
        self.mode_label = QLabel("Режим: Добавление точек")
        self.coord_label = QLabel("Координаты: -")

        self.statusbar.addWidget(self.zoom_label)
        self.statusbar.addWidget(self.mode_label)
        self.statusbar.addWidget(self.coord_label)

        self.statusbar.showMessage("Готов к работе")

    def new_project(self):
        """Создать новый проект"""
        name, ok = QInputDialog.getText(self, "Новый проект", "Название проекта:")
        if ok and name:
            self.current_project = Project(name=name)
            self.current_project.traces = []
            self.canvas.current_trace = None
            self.canvas.current_interval = None
            self.canvas.update_display()
            self.update_trace_selector()
            self.statusbar.showMessage(f"Создан проект: {name}")

    def open_project(self):
        """Открыть существующий проект"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", "", "Trace Project (*.trace)"
        )
        if filepath:
            self.current_project = Project.load(Path(filepath))
            if self.current_project.raster_data is not None:
                self.canvas.load_image(self.current_project.raster_data)

            # Делаем все трассы видимыми
            for trace in self.current_project.traces:
                trace.is_visible = True
                trace.is_editing = False

            # Очищаем текущую трассу на канвасе
            self.canvas.current_trace = None
            self.canvas.current_interval = None

            # ОБНОВЛЯЕМ СЕЛЕКТОР
            self.update_trace_selector()

            # Устанавливаем "Все трассы" как активный пункт
            self.controls_panel.trace_selector.setCurrentIndex(0)

            # Обновляем отображение
            self.canvas.update_display()

            self.statusbar.showMessage(f"Загружен проект: {self.current_project.name}")

    def save_project(self):
        """Сохранить проект"""
        if self.current_project:
            if not self.current_project.filepath:
                self.save_project_as()
            else:
                self.current_project.save()
                self.statusbar.showMessage(f"Проект сохранен: {self.current_project.name}")

    def save_project_as(self):
        """Сохранить проект как..."""
        if self.current_project:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Сохранить проект", f"{self.current_project.name}.trace", "Trace Project (*.trace)"
            )
            if filepath:
                self.current_project.filepath = Path(filepath)
                self.current_project.save()
                self.statusbar.showMessage(f"Проект сохранен: {filepath}")

    def import_raster(self):
        """Импортировать растер"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Импортировать растер",
            "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
        )

        if filepath and self.current_project:
            from PIL import Image
            import numpy as np

            # Открываем изображение
            img = Image.open(filepath)
            print(f"Загружен файл: {filepath}")
            print(f"Режим: {img.mode}, Размер: {img.size}")

            # Конвертируем в RGB или Grayscale
            if img.mode == 'L':
                raster_data = np.array(img, dtype=np.uint8)
            else:
                # Конвертируем в RGB
                img = img.convert('RGB')
                raster_data = np.array(img, dtype=np.uint8)

            print(f"Shape массива: {raster_data.shape}, dtype: {raster_data.dtype}")

            self.current_project.raster_data = raster_data
            self.current_project.raster_path = Path(filepath)

            # Загружаем изображение в canvas
            self.canvas.load_image(raster_data)
            self.statusbar.showMessage(f"Загружен растер: {filepath}")

    def export_sac(self):
        """Экспорт в SAC формат"""
        if not self.current_project or not self.current_project.traces:
            QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в SAC", "", "SAC Files (*.sac)"
        )

        if filepath:
            # TODO: Реализовать экспорт в SAC через obspy или вручную
            self.statusbar.showMessage(f"Экспорт в SAC: {filepath}")
            QMessageBox.information(self, "Информация", "Экспорт в SAC будет реализован в следующей версии")

    def fit_view(self):
        """Подогнать изображение под размер окна"""
        if self.canvas.pixmap_item:
            self.canvas.fitInView(self.canvas.pixmap_item, Qt.KeepAspectRatio)

    def project_settings(self):
        """Настройки проекта"""
        from gui.dialogs.raster_settings_dialog import RasterSettingsDialog
        dialog = RasterSettingsDialog(self.workspace_settings, self)
        if dialog.exec_():
            # Обновляем настройки
            self.workspace_settings = dialog.get_settings()
            self.statusbar.showMessage("Настройки проекта обновлены")

    def interpolate_current_interval(self):
        """Интерполяция текущего интервала"""
        if self.canvas.current_interval and len(self.canvas.current_interval.points) >= 2:
            from core.digitizer_engine import DigitizerEngine
            x_interp, y_interp = DigitizerEngine.interpolate_interval(
                self.canvas.current_interval,
                num_points=500
            )
            self.statusbar.showMessage(f"Интерполяция выполнена: {len(x_interp)} точек")
            # TODO: Отобразить интерполированную кривую
        else:
            QMessageBox.warning(self, "Ошибка", "Недостаточно точек для интерполяции (нужно минимум 2)")

    def remove_trend_current_interval(self):
        """Удалить тренд текущего интервала"""
        if self.canvas.current_interval and len(self.canvas.current_interval.points) >= 2:
            from core.digitizer_engine import DigitizerEngine
            corrected_points = DigitizerEngine.remove_trend(
                self.canvas.current_interval.points,
                degree=1
            )
            self.canvas.current_interval.points = corrected_points
            self.canvas.update_display()
            self.statusbar.showMessage("Тренд удален")
        else:
            QMessageBox.warning(self, "Ошибка", "Недостаточно точек для удаления тренда")

    def update_coordinates(self, x, y):
        """Обновление отображения координат"""
        self.coord_label.setText(f"Координаты: ({x:.1f}, {y:.1f})")

    def on_mode_changed(self, mode: str):
        """Обработка смены режима"""
        if mode == 'digitize':
            # Включаем режим оцифровки, но инструменты пока не активны
            self.canvas.set_mode('digitize')
            self.controls_panel.set_digitize_tools_enabled(True)
        elif mode == 'pan':
            self.canvas.set_mode('pan')
            self.controls_panel.set_digitize_tools_enabled(False)
        else:
            # add_point, delete_point, move_point
            self.canvas.set_mode(mode)
            # Остаемся в режиме оцифровки
            self.controls_panel.set_digitize_tools_enabled(True)

    def finish_current_interval(self):
        """Завершить текущий интервал оцифровки"""
        if self.canvas.finish_current_interval():
            self.statusbar.showMessage("Текущий интервал завершен. Можно начинать новую линию.")
        else:
            self.statusbar.showMessage("Нет активного интервала для завершения")

    def show_trace_manager(self):
        """Показать диалог управления трассами"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте или откройте проект")
            return

        if self.current_project.raster_data is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите растер")
            return

        from gui.dialogs.trace_manager_dialog import TraceManagerDialog
        dialog = TraceManagerDialog(self.current_project, self)
        dialog.start_trace_selection.connect(self.start_trace_selection)
        dialog.trace_visibility_changed.connect(self.on_visibility_changed)  # Добавить эту строку
        dialog.exec_()

    def on_visibility_changed(self):
        """Обработка изменения видимости трасс"""
        if self.current_project:
            self.update_trace_selector()
            self.canvas.update_display()

    def hide_trace(self, trace):
        """Спрятать трассу (если trace=None, то скрыть все)"""
        if trace is None:
            # Скрываем все трассы
            for t in self.current_project.traces:
                t.is_visible = False
        else:
            # Проверяем, существует ли еще трасса в проекте
            if trace in self.current_project.traces:
                trace.is_visible = False

        # Обновляем отображение
        self.canvas.update_display()

        # Принудительно запускаем сборщик мусора
        import gc
        gc.collect()

        self.statusbar.showMessage("Трассы скрыты")

    def show_all_traces(self):
        """Показать все трассы"""
        for trace in self.current_project.traces:
            trace.is_visible = True

        self.canvas.update_display()
        self.update_trace_selector()
        self.statusbar.showMessage("Все трассы показаны")

    def start_trace_selection(self, trace):
        """Показать трассу на изображении"""
        # Снимаем флаг редактирования со всех трасс
        for t in self.current_project.traces:
            t.is_editing = False

        trace.is_editing = True
        trace.is_visible = True
        trace.project = self.current_project

        self.canvas.set_current_trace(trace)
        self.update_trace_selector()

        index = self.controls_panel.trace_selector.findData(trace.id)
        if index >= 0:
            self.controls_panel.trace_selector.setCurrentIndex(index)

        self.canvas.update_display()

    def finish_current_trace(self):
        """Завершить текущую трассу"""
        if not self.current_project:
            self.statusbar.showMessage("Нет активного проекта")
            return

        current_trace = self.canvas.current_trace
        if not current_trace:
            self.statusbar.showMessage("Нет активной трассы для завершения")
            return

        # Проверяем, есть ли точки в текущей трассе
        total_points = sum(len(interval.points) for interval in current_trace.intervals)

        if total_points == 0:
            reply = QMessageBox.question(
                self,
                "Завершение трассы",
                f"Трасса '{current_trace.name}' не содержит точек.\nЗавершить её?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        else:
            reply = QMessageBox.question(
                self,
                "Завершение трассы",
                f"Завершить трассу '{current_trace.name}'?\n(Содержит {total_points} точек)",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Снимаем флаг редактирования с текущей трассы
        current_trace.is_editing = False

        # Очищаем текущую трассу на канвасе
        self.canvas.current_trace = None
        self.canvas.current_interval = None
        self.canvas.update_display()

        # Сбрасываем селектор трасс
        self.controls_panel.trace_selector.setCurrentIndex(-1)

        self.statusbar.showMessage(f"Трасса '{current_trace.name}' завершена")

    def update_trace_selector(self):
        """Обновить выпадающий список трасс"""
        if self.current_project:
            current_id = self.canvas.current_trace.id if self.canvas.current_trace else None
            self.controls_panel.update_trace_selector(self.current_project.traces, current_id)
        else:
            self.controls_panel.update_trace_selector([], None)

    def on_trace_selected_from_selector(self, trace_id):
        """Обработка выбора трассы из выпадающего списка"""
        if not self.current_project:
            return

        if trace_id is None:
            # Выбраны "Все трассы" - показываем все
            for trace in self.current_project.traces:
                trace.is_visible = True
            self.canvas.current_trace = None
            self.canvas.current_interval = None
            self.canvas.update_display()  # <-- ЭТО ВАЖНО
            self.update_trace_selector()  # <-- ОБНОВЛЯЕМ СЕЛЕКТОР
            self.statusbar.showMessage("Режим: отображение всех трасс")
        else:
            # Выбрана конкретная трасса
            for trace in self.current_project.traces:
                if trace.id == trace_id:
                    # Скрываем все трассы, показываем только выбранную
                    for t in self.current_project.traces:
                        t.is_visible = (t.id == trace_id)
                    self.canvas.set_current_trace(trace)
                    self.canvas.update_display()  # <-- ЭТО ВАЖНО
                    self.update_trace_selector()  # <-- ОБНОВЛЯЕМ СЕЛЕКТОР
                    self.statusbar.showMessage(f"Выбрана трасса: {trace.name}")
                    break

    def update_current_trace_display(self):
        """Обновить отображение текущей трассы"""
        if not self.current_project:
            return

        # Проверяем, какая трасса выбрана в селекторе
        selected_id = self.controls_panel.get_selected_trace_id()

        if selected_id is None:
            # Режим "Все трассы"
            for trace in self.current_project.traces:
                trace.is_visible = True
            self.canvas.current_trace = None
            self.canvas.current_interval = None
        else:
            # Конкретная трасса
            for trace in self.current_project.traces:
                if trace.id == selected_id:
                    trace.is_visible = True
                    self.canvas.current_trace = trace
                    if trace.intervals:
                        self.canvas.current_interval = trace.intervals[-1]
                else:
                    trace.is_visible = False

        self.canvas.update_display()
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QToolBar, QAction, QStatusBar, QFileDialog,
                             QInputDialog, QMessageBox, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from pathlib import Path

from models.project import Project
from models.workspace_params import WorkspaceSettings
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
        self.controls_panel.select_trace_requested.connect(self.on_select_trace)
        self.controls_panel.finish_trace_requested.connect(self.finish_current_trace)
        self.controls_panel.show_visibility_requested.connect(self.show_visibility_dialog)

        layout.addWidget(self.controls_panel, stretch=1)

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

        import_raster_action = QAction("Импортировать растр...", self)
        import_raster_action.triggered.connect(self.import_raster)
        file_menu.addAction(import_raster_action)

        file_menu.addSeparator()

        # Подменю экспорта
        export_menu = file_menu.addMenu("Экспорт")

        export_csv_action = QAction("CSV формат...", self)
        export_csv_action.triggered.connect(self.export_all_data)
        export_menu.addAction(export_csv_action)

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

        self.statusbar.showMessage("Готов к работе")

    def new_project(self):
        """Создать новый проект"""
        name, ok = QInputDialog.getText(self, "Новый проект", "Название проекта:")
        if ok and name:
            self.current_project = Project(name=name)
            self.canvas.current_project = self.current_project
            self.canvas.current_trace = None
            self.canvas.current_interval = None
            self.canvas.update_display()
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

            self.canvas.current_project = self.current_project

            for trace in self.current_project.traces:
                trace.is_visible = True
                trace.is_editing = False

            self.canvas.current_trace = None
            self.canvas.current_interval = None
            self.canvas.update_display()

            # Обновляем селектор трасс
            self.controls_panel.update_trace_selector(self.current_project.traces, None)

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

            img = Image.open(filepath)

            if img.mode == 'L':
                raster_data = np.array(img, dtype=np.uint8)
            else:
                img = img.convert('RGB')
                raster_data = np.array(img, dtype=np.uint8)

            self.current_project.raster_data = raster_data
            self.current_project.raster_path = Path(filepath)
            self.canvas.load_image(raster_data)
            self.statusbar.showMessage(f"Загружен растер: {filepath}")

    def fit_view(self):
        """Подогнать изображение под размер окна"""
        if self.canvas.pixmap_item:
            self.canvas.fitInView(self.canvas.pixmap_item, Qt.KeepAspectRatio)

    def project_settings(self):
        """Настройки проекта"""
        from gui.dialogs.raster_settings_dialog import RasterSettingsDialog
        dialog = RasterSettingsDialog(self.workspace_settings, self)
        if dialog.exec_():
            self.workspace_settings = dialog.get_settings()
            self.statusbar.showMessage("Настройки проекта обновлены")

    def interpolate_current_interval(self):
        """Интерполяция текущего интервала"""
        if self.canvas.current_interval and len(self.canvas.current_interval.points) >= 2:
            x_interp, y_interp = DigitizerEngine.interpolate_interval(
                self.canvas.current_interval,
                num_points=500
            )
            self.statusbar.showMessage(f"Интерполяция выполнена: {len(x_interp)} точек")
        else:
            QMessageBox.warning(self, "Ошибка", "Недостаточно точек для интерполяции (нужно минимум 2)")

    def remove_trend_current_interval(self):
        """Удалить тренд текущего интервала"""
        if self.canvas.current_interval and len(self.canvas.current_interval.points) >= 2:
            corrected_points = DigitizerEngine.remove_trend(
                self.canvas.current_interval.points,
                degree=1
            )
            self.canvas.current_interval.points = corrected_points
            self.canvas.update_display()
            self.statusbar.showMessage("Тренд удален")
        else:
            QMessageBox.warning(self, "Ошибка", "Недостаточно точек для удаления тренда")

    def on_select_trace(self, trace_id):
        """Выбрать трассу для работы (без включения режима оцифровки)"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте или откройте проект")
            return

        if trace_id is None:
            # Сбрасываем текущую трассу
            self.canvas.current_trace = None
            self.canvas.current_interval = None
            # Показываем все трассы
            for t in self.current_project.traces:
                t.is_visible = True
            self.canvas.update_display()
            self.controls_panel.set_selected_trace(None)
            self.statusbar.showMessage("Режим просмотра всех трасс")
            return

        trace = self.current_project.get_trace(trace_id)
        if not trace:
            return

        # Скрываем все трассы, показываем только выбранную
        for t in self.current_project.traces:
            t.is_visible = (t.id == trace_id)

        # Устанавливаем текущую трассу
        self.canvas.set_current_trace(trace)
        self.canvas.update_display()

        # Обновляем селектор
        self.controls_panel.set_selected_trace(trace_id)

    def on_mode_changed(self, mode: str):
        """Обработка смены режима"""
        if mode == 'digitize':
            self.canvas.set_mode('add_point')  # По умолчанию режим добавления точек
            self.controls_panel.set_digitize_tools_enabled(True)
        elif mode == 'pan':
            self.canvas.set_mode('pan')
            self.controls_panel.set_digitize_tools_enabled(False)
        elif mode == 'add_point':
            self.canvas.set_mode('add_point')
        elif mode == 'delete_point':
            self.canvas.set_mode('delete_point')
        elif mode == 'move_point':
            self.canvas.set_mode('move_point')

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
        dialog.trace_selected_for_editing.connect(self.on_trace_selected_for_editing)

        old_traces_count = len(self.current_project.traces)
        dialog.exec_()

        new_traces_count = len(self.current_project.traces)
        if new_traces_count != old_traces_count:
            self.controls_panel.update_trace_selector(self.current_project.traces, None)

    def on_trace_selected_for_editing(self, trace):
        """Обработка выбора трассы для оцифровки из менеджера"""
        # Скрываем все трассы, показываем только выбранную
        for t in self.current_project.traces:
            t.is_visible = (t.id == trace.id)

        # Устанавливаем текущую трассу
        self.canvas.set_current_trace(trace)
        self.canvas.update_display()

        # Обновляем селектор
        self.controls_panel.set_selected_trace(trace.id)

        self.statusbar.showMessage(f"Выбрана трасса для оцифровки: {trace.name}")

    def show_visibility_dialog(self):
        """Показать диалог управления видимостью трасс"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте или откройте проект")
            return

        if not self.current_project.traces:
            QMessageBox.warning(self, "Ошибка", "Нет созданных трасс")
            return

        from gui.dialogs.visibility_dialog import VisibilityDialog
        dialog = VisibilityDialog(self.current_project, self)
        dialog.visibility_changed.connect(self.on_visibility_changed)
        dialog.exec_()

    def on_visibility_changed(self):
        """Обработка изменения видимости трасс"""
        if self.current_project:
            self.canvas.update_display()
            self.statusbar.showMessage("Отображение трасс обновлено")

    def finish_current_trace(self):
        """Завершить текущую трассу"""
        if not self.current_project:
            self.statusbar.showMessage("Нет активного проекта")
            return

        current_trace = self.canvas.current_trace
        if not current_trace:
            self.statusbar.showMessage("Нет активной трассы для завершения")
            return

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

        current_trace.is_editing = False
        self.canvas.current_trace = None
        self.canvas.current_interval = None
        self.canvas.update_display()

        self.controls_panel.update_trace_selector(self.current_project.traces, None)
        self.controls_panel.set_selected_trace(None)

        self.statusbar.showMessage(f"Трасса '{current_trace.name}' завершена")

    def export_all_data(self):
        """Экспорт всех данных в CSV"""
        if not self.current_project:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте или откройте проект")
            return

        if not self.current_project.traces:
            QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта")
            return

        export_dir = QFileDialog.getExistingDirectory(self, "Выберите директорию для экспорта")
        if not export_dir:
            return

        import os
        import numpy as np
        from scipy import interpolate
        import csv

        success_count = 0
        total_points = 0

        for trace in self.current_project.traces:
            for i, interval in enumerate(trace.intervals):
                if not interval.points:
                    continue

                points = interval.points
                x_vals = np.array([p.x for p in points])
                y_vals = np.array([p.y for p in points])

                sort_idx = np.argsort(x_vals)
                x_sorted = x_vals[sort_idx]
                y_sorted = y_vals[sort_idx]

                if len(points) >= 2:
                    num_samples = max(10, min(len(points) * 10, 10000))
                    x_interp = np.linspace(x_sorted[0], x_sorted[-1], num_samples)
                    f = interpolate.interp1d(x_sorted, y_sorted, kind='cubic', fill_value='extrapolate')
                    y_interp = f(x_interp)

                    time = np.linspace(0, len(y_interp) / 100.0, len(y_interp))

                    filename = f"{trace.name}_interval_{i + 1}.csv"
                    filepath = os.path.join(export_dir, filename)

                    with open(filepath, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(['Time (s)', 'Amplitude (pixels)', 'X_pixel', 'Y_pixel'])
                        for j, (t, a, x, y) in enumerate(zip(time, y_interp, x_interp, y_interp)):
                            writer.writerow([f"{t:.6f}", f"{a:.6f}", f"{x:.2f}", f"{y:.2f}"])

                    success_count += 1
                    total_points += len(points)

        QMessageBox.information(
            self,
            "Экспорт завершен",
            f"Экспортировано {success_count} интервалов\n"
            f"Всего точек: {total_points}\n"
            f"Директория: {export_dir}"
        )
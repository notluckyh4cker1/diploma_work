import sys
import os
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QSplitter, QFileDialog, QMessageBox,
                             QToolBar, QAction, QDockWidget, QLabel, QStatusBar)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
from PyQt5.QtGui import QIcon, QPainter

from gui.raster_canvas import RasterCanvas
from gui.controls_panel import ControlsPanel
from gui.traces_panel import TracesPanel
from core.project import DigitizationProject
from models import RasterOrientation
from models.raster_data import SeismogramRaster
from gui.dialogs.import_dialog import ImportRasterDialog
from gui.dialogs.export_dialog import ExportDialog

class MainWindow(QMainWindow):
    # Сигналы для обновления интерфейса
    project_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.project = DigitizationProject()  # Текущий проект
        self.current_interval_type = "waveform"  # Тип создаваемого интервала по умолчанию

        # ИНИЦИАЛИЗИРУЕМ raster_canvas ПЕРЕД init_ui
        self.raster_canvas = RasterCanvas(self)

        self.raster_menu = None
        self.traces_menu = None
        self.finish_interval_action = None
        self.clear_interval_action = None
        self.time_marker_action = None
        self.waveform_action = None
        self.noise_action = None

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("Seismogram Digitizer [Новый проект]")
        self.showMaximized()  # ПОЛНОЭКРАННЫЙ РЕЖИМ

        # --- Центральный виджет ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- ТОЛЬКО ХОЛСТ НА ВСЕМ ЭКРАНЕ ---
        main_layout.addWidget(self.raster_canvas)

        # --- Создание меню ---
        self.create_menu_bar()

        # --- Статусбар ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")

        # Подключаем сигналы
        self.project_updated.connect(self.on_project_updated)

    def create_menu_bar(self):
        menubar = self.menuBar()

        # Меню "Файл"
        file_menu = menubar.addMenu('&Файл')

        new_action = self.create_action('&Новый проект', self.new_project,
                                        'Ctrl+N', 'new.png')
        file_menu.addAction(new_action)

        open_action = self.create_action('&Открыть проект...', self.open_project,
                                         'Ctrl+O', 'open.png')
        file_menu.addAction(open_action)

        import_raster_action = self.create_action('&Импорт растра...',
                                                  self.import_raster,
                                                  'Ctrl+I', 'import.png')
        file_menu.addAction(import_raster_action)

        file_menu.addSeparator()

        save_action = self.create_action('&Сохранить проект', self.save_project,
                                         'Ctrl+S', 'save.png')
        file_menu.addAction(save_action)

        save_as_action = self.create_action('Сохранить проект &как...',
                                            self.save_project_as,
                                            'Ctrl+Shift+S', 'save_as.png')
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_menu = file_menu.addMenu('&Экспорт данных')
        export_sac_action = self.create_action('В формат &SAC...',
                                               self.export_to_sac,
                                               '', 'export.png')
        export_menu.addAction(export_sac_action)

        export_miniseed_action = self.create_action('В формат &MiniSEED...',
                                                    self.export_to_miniseed,
                                                    '', 'export.png')
        export_menu.addAction(export_miniseed_action)

        export_csv_action = self.create_action('В формат &CSV...',
                                               self.export_to_csv,
                                               '', 'export.png')
        export_menu.addAction(export_csv_action)

        file_menu.addSeparator()
        exit_action = self.create_action('&Выход', self.close,
                                         'Ctrl+Q', 'exit.png')
        file_menu.addAction(exit_action)

        # Меню "Растр" - ТОЛЬКО ПОСЛЕ ЗАГРУЗКИ ИЗОБРАЖЕНИЯ
        self.raster_menu = menubar.addMenu('&Растр')
        self.raster_menu.setEnabled(False)  # Изначально отключено

        # Создаем действия для меню "Растр" (будут активированы после загрузки)
        self.raster_settings_action = self.create_action('&Настройки растра...',
                                                         self.show_raster_settings,
                                                         '', 'settings.png')
        self.raster_menu.addAction(self.raster_settings_action)

        self.raster_menu.addSeparator()

        self.zoom_in_action = self.create_action('&Увеличить', self.zoom_in,
                                                 'Ctrl++', 'zoom_in.png')
        self.raster_menu.addAction(self.zoom_in_action)

        self.zoom_out_action = self.create_action('&Уменьшить', self.zoom_out,
                                                  'Ctrl+-', 'zoom_out.png')
        self.raster_menu.addAction(self.zoom_out_action)

        self.zoom_original_action = self.create_action('Исходный &размер',
                                                       self.zoom_original,
                                                       'Ctrl+0', 'zoom_original.png')
        self.raster_menu.addAction(self.zoom_original_action)

        self.raster_menu.addSeparator()

        self.brightness_action = self.create_action('&Яркость...',
                                                    self.adjust_brightness,
                                                    '', 'brightness.png')
        self.raster_menu.addAction(self.brightness_action)

        self.contrast_action = self.create_action('&Контрастность...',
                                                  self.adjust_contrast,
                                                  '', 'contrast.png')
        self.raster_menu.addAction(self.contrast_action)

        self.gamma_action = self.create_action('&Гамма-коррекция...',
                                               self.adjust_gamma,
                                               '', 'gamma.png')
        self.raster_menu.addAction(self.gamma_action)

        self.raster_menu.addSeparator()

        self.invert_action = self.create_action('&Инвертировать цвета',
                                                self.invert_colors,
                                                'Ctrl+Shift+I', 'invert.png')
        self.invert_action.setCheckable(True)
        self.raster_menu.addAction(self.invert_action)

        # Меню "Трассы"
        self.traces_menu = menubar.addMenu('&Трассы')
        self.traces_menu.setEnabled(False)  # Изначально отключено

        create_trace_action = self.create_action('Создать &трассу',
                                                 self.create_trace,
                                                 'Ctrl+T', 'trace.png')
        self.traces_menu.addAction(create_trace_action)

        auto_detect_action = self.create_action('&Автоопределение трасс',
                                                self.auto_detect_traces,
                                                '', 'auto_detect.png')
        self.traces_menu.addAction(auto_detect_action)

        manage_traces_action = self.create_action('Управление трассами...',
                                                  self.show_trace_manager,
                                                  'Ctrl+M', 'manage.png')
        self.traces_menu.addAction(manage_traces_action)

        self.traces_menu.addSeparator()

        self.interpolate_action = self.create_action('&Интерполировать все',
                                                     self.interpolate_all,
                                                     'Ctrl+P', 'interpolate.png')
        self.traces_menu.addAction(self.interpolate_action)

        self.correct_trend_action = self.create_action('Устранить &тренд',
                                                       self.correct_trend,
                                                       'Ctrl+R', 'correction.png')
        self.traces_menu.addAction(self.correct_trend_action)

        # Меню "Инструменты"
        tools_menu = menubar.addMenu('&Инструменты')

        interval_menu = tools_menu.addMenu('&Тип интервала')

        self.time_marker_action = self.create_action('&Метка времени',
                                                     lambda: self.set_interval_type('time_marker'),
                                                     '', 'time_marker.png')
        self.time_marker_action.setCheckable(True)
        interval_menu.addAction(self.time_marker_action)

        self.waveform_action = self.create_action('&Волновая форма',
                                                  lambda: self.set_interval_type('waveform'),
                                                  '', 'waveform.png')
        self.waveform_action.setCheckable(True)
        self.waveform_action.setChecked(True)  # По умолчанию
        interval_menu.addAction(self.waveform_action)

        self.noise_action = self.create_action('&Помеха',
                                               lambda: self.set_interval_type('noise'),
                                               '', 'noise.png')
        self.noise_action.setCheckable(True)
        interval_menu.addAction(self.noise_action)

        # Группа для радио-кнопок
        from PyQt5.QtWidgets import QActionGroup
        self.interval_type_group = QActionGroup(self)
        self.interval_type_group.addAction(self.time_marker_action)
        self.interval_type_group.addAction(self.waveform_action)
        self.interval_type_group.addAction(self.noise_action)

        tools_menu.addSeparator()

        # Дополнительные инструменты оцифровки
        self.finish_interval_action = self.create_action('&Завершить интервал',
                                                         self.finish_current_interval,
                                                         'Ctrl+Enter', 'finish.png')
        tools_menu.addAction(self.finish_interval_action)

        self.clear_interval_action = self.create_action('&Очистить интервал',
                                                        self.clear_current_interval,
                                                        'Del', 'clear.png')
        tools_menu.addAction(self.clear_interval_action)

    def create_action(self, text, slot, shortcut=None, icon_name=None):
        from PyQt5.QtWidgets import QAction
        from PyQt5.QtGui import QIcon

        action = QAction(text, self)
        action.triggered.connect(slot)

        if shortcut:
            action.setShortcut(shortcut)

        if icon_name:
            # Пытаемся загрузить иконку из ресурсов или файла
            try:
                # Здесь можно добавить загрузку реальных иконок
                pass
            except:
                pass

        return action

    def enable_raster_menu(self, enabled=True):
        """Включает/выключает меню 'Растр' и 'Трассы'."""
        # Включаем меню "Растр"
        self.raster_menu.setEnabled(enabled)

        # Включаем меню "Трассы"
        self.traces_menu.setEnabled(enabled)

        # Также включаем действия в меню "Инструменты"
        self.finish_interval_action.setEnabled(enabled)
        self.clear_interval_action.setEnabled(enabled)

        # Включаем тип интервалов
        self.time_marker_action.setEnabled(enabled)
        self.waveform_action.setEnabled(enabled)
        self.noise_action.setEnabled(enabled)

    # --- Слоты для меню ---
    def new_project(self):
        if self.maybe_save():
            self.project = DigitizationProject()
            self.raster_canvas.clear_scene()
            self.setWindowTitle("Seismogram Digitizer")
            self.update_project_info()
            self.status_bar.showMessage("Создан новый проект", 3000)

    def open_project(self):
        if not self.maybe_save():
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", "", "Trace Files (*.trace);;All files (*.*)"
        )
        if filepath:
            try:
                self.project = DigitizationProject.load(Path(filepath))
                # Загружаем изображение в растр
                if self.project.raster:
                    self.project.raster.load()
                    self.raster_canvas.set_raster(self.project.raster)

                self.setWindowTitle(f"Seismogram Digitizer [{os.path.basename(filepath)}]")
                self.update_project_info()
                self.status_bar.showMessage(f"Проект загружен: {filepath}", 3000)

            except Exception as e:
                QMessageBox.critical(self, "Ошибка",
                                     f"Не удалось загрузить проект:\n{str(e)}")

    def import_raster(self):
        try:
            dialog = ImportRasterDialog(self)
            if dialog.exec_():
                params = dialog.get_parameters()
                filepath = params.get('filepath')

                if filepath and os.path.exists(filepath):
                    try:
                        # Показываем сообщение о загрузке
                        self.status_bar.showMessage(f"Загрузка {os.path.basename(filepath)}...")
                        QApplication.processEvents()  # Обновляем GUI

                        # Создаем растр с поддержкой тайлов
                        self.project.raster = SeismogramRaster(
                            image_path=filepath,
                            dpi=params['dpi'],
                            color_mode=params['color_mode'],
                            use_tiling=True,  # Включаем тайлинг
                            tile_size=(1024, 1024)  # Размер тайлов
                        )

                        # Загружаем только метаданные
                        self.project.raster.load(load_full_image=False)

                        # Получаем информацию об изображении
                        info = self.project.raster.get_image_info()

                        # Пробуем загрузить изображение в холст
                        success = self.raster_canvas.set_raster(self.project.raster)
                        if success:
                            # Включаем меню "Растр"
                            self.enable_raster_menu(True)

                            # Показываем информацию
                            size_str = f"{info['size'][0]}x{info['size'][1]}"
                            self.status_bar.showMessage(
                                f"Растр загружен: {os.path.basename(filepath)} ({size_str})",
                                5000
                            )
                            self.update_project_info()
                        else:
                            QMessageBox.warning(self, "Предупреждение",
                                                "Не удалось отобразить изображение")

                    except Exception as e:
                        QMessageBox.critical(self, "Ошибка",
                                             f"Не удалось загрузить растр:\n{str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Ошибка при импорте:\n{str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Ошибка при импорте:\n{str(e)}\n"
                                 f"Убедитесь, что OpenGL работает на вашей системе.")

    def save_project(self):
        if not self.project.project_path:
            self.save_project_as()
        else:
            success = self.project.save(self.project.project_path)
            if success:
                self.status_bar.showMessage("Проект сохранен", 3000)
                self.update_project_info()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить проект")

    def save_project_as(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Сохранить проект как", "", "Trace Files (*.trace);;All files (*.*)"
        )
        if filepath:
            if not filepath.endswith('.trace'):
                filepath += '.trace'
            success = self.project.save(Path(filepath))
            if success:
                self.setWindowTitle(f"Seismogram Digitizer [{os.path.basename(filepath)}]")
                self.status_bar.showMessage("Проект сохранен", 3000)
                self.update_project_info()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить проект")

    def show_raster_settings(self):
        """Показывает диалог настроек растра."""
        from gui.dialogs.raster_settings_dialog import RasterSettingsDialog

        dialog = RasterSettingsDialog(self)
        dialog.settings_changed.connect(self.apply_raster_settings)
        dialog.exec_()

    def apply_raster_settings(self, settings):
        """Применяет настройки растра."""
        # Применяем настройки к проекту
        if self.project:
            # Ориентация
            if settings['orientation'] == 0:
                self.project.settings.raster_orientation = RasterOrientation.HORIZONTAL
            else:
                self.project.settings.raster_orientation = RasterOrientation.VERTICAL

            # Временные параметры
            self.project.settings.time_start = settings['time_start']
            self.project.settings.time_end = settings['time_end']
            self.project.settings.export_sampling_rate = settings['sampling_rate']

            # Настройки интерполяции
            self.project.settings.default_interpolation_order = settings['poly_order']
            self.project.settings.auto_interpolate = settings['auto_interpolate']
            self.project.settings.show_grid = settings['show_grid']

            # Применяем настройки улучшения к холсту
            if hasattr(self.raster_canvas, 'gl_widget'):
                self.raster_canvas.gl_widget.brightness = settings['brightness']
                self.raster_canvas.gl_widget.contrast = settings['contrast']
                self.raster_canvas.gl_widget.gamma = settings['gamma']
                self.raster_canvas.gl_widget.invert_colors = settings['invert_colors']

                if settings['threshold_enabled']:
                    self.raster_canvas.gl_widget.set_threshold(
                        int(settings['threshold']), True
                    )

                # Перерисовываем
                self.raster_canvas.gl_widget.update()

        self.status_bar.showMessage("Настройки растра применены", 3000)

    def adjust_brightness(self):
        """Настройка яркости."""
        from PyQt5.QtWidgets import QInputDialog
        value, ok = QInputDialog.getDouble(self, "Яркость",
                                           "Яркость (%):", 100, 10, 500, 1)
        if ok and hasattr(self.raster_canvas, 'gl_widget'):
            self.raster_canvas.gl_widget.brightness = value / 100.0
            self.raster_canvas.gl_widget.update()

    def adjust_contrast(self):
        """Настройка контрастности."""
        from PyQt5.QtWidgets import QInputDialog
        value, ok = QInputDialog.getDouble(self, "Контрастность",
                                           "Контрастность (%):", 100, 10, 500, 1)
        if ok and hasattr(self.raster_canvas, 'gl_widget'):
            self.raster_canvas.gl_widget.contrast = value / 100.0
            self.raster_canvas.gl_widget.update()

    def adjust_gamma(self):
        """Настройка гаммы."""
        from PyQt5.QtWidgets import QInputDialog
        value, ok = QInputDialog.getDouble(self, "Гамма-коррекция",
                                           "Значение гаммы:", 1.0, 0.1, 5.0, 1)
        if ok and hasattr(self.raster_canvas, 'gl_widget'):
            self.raster_canvas.gl_widget.gamma = value
            self.raster_canvas.gl_widget.update()

    def invert_colors(self):
        """Инвертирует цвета."""
        if hasattr(self.raster_canvas, 'gl_widget'):
            self.raster_canvas.gl_widget.invert_colors = self.invert_action.isChecked()
            self.raster_canvas.gl_widget.update()

    def finish_current_interval(self):
        """Завершает текущий интервал."""
        if self.raster_canvas:
            interval_type = self.current_interval_type
            interval = self.raster_canvas.finish_current_interval(interval_type)
            if interval and self.project:
                self.project.loose_intervals.append(interval)
                self.project_updated.emit()

    def clear_current_interval(self):
        """Очищает текущий интервал."""
        if self.raster_canvas:
            self.raster_canvas.clear_current_interval()

    def export_data(self):
        """Общий диалог экспорта."""
        if not self.project or (not self.project.traces and not self.project.loose_intervals):
            QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта")
            return

        dialog = ExportDialog(self, format_type='SAC')
        dialog.exec_()

    def export_to_sac(self):
        from gui.dialogs.export_dialog import ExportDialog
        dialog = ExportDialog(self, format_type='SAC')
        dialog.exec_()

    def export_to_miniseed(self):
        from gui.dialogs.export_dialog import ExportDialog
        dialog = ExportDialog(self, format_type='MiniSEED')
        dialog.exec_()

    def export_to_csv(self):
        from gui.dialogs.export_dialog import ExportDialog
        dialog = ExportDialog(self, format_type='CSV')
        dialog.exec_()

    def undo(self):
        self.status_bar.showMessage("Отмена - будет реализовано", 2000)

    def redo(self):
        self.status_bar.showMessage("Повтор - будет реализовано", 2000)

    def delete_selected(self):
        self.status_bar.showMessage("Удаление - будет реализовано", 2000)

    def create_trace(self):
        """Создает новую трассу через диалог управления."""
        try:
            # Показываем диалог управления трассами
            from gui.simple_trace_panel import SimpleTraceDialog
            dialog = SimpleTraceDialog(self.project, self)

            # Прямо вызываем добавление трассы через диалог
            dialog.add_trace()

            # Показываем диалог после создания (опционально)
            dialog.show()

        except Exception as e:
            print(f"Ошибка при создании трассы: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Ошибка",
                                f"Не удалось создать трассу:\n{str(e)}")

    def auto_detect_traces(self):
        from core.trace_manager import TraceManager
        from PyQt5.QtWidgets import QInputDialog

        num_traces, ok = QInputDialog.getInt(self, "Автоопределение трасс",
                                             "Количество трасс:", 3, 1, 10, 1)
        if ok:
            trace_manager = TraceManager(self.project)
            traces = trace_manager.auto_detect_traces(num_traces)
            for trace in traces:
                self.project.add_trace(trace)
            self.traces_panel.update_trace_list()
            self.status_bar.showMessage(f"Создано {len(traces)} трасс", 3000)
            self.project_updated.emit()

    def interpolate_all(self):
        if not self.project:
            return

        success_count = 0
        total_count = 0

        # Интервалы в трассах
        for trace in self.project.traces:
            for interval in trace.intervals:
                total_count += 1
                if self.project._interpolate_interval(interval):
                    success_count += 1

        # Свободные интервалы
        for interval in self.project.loose_intervals:
            total_count += 1
            if self.project._interpolate_interval(interval):
                success_count += 1

        self.status_bar.showMessage(
            f"Интерполировано {success_count} из {total_count} интервалов",
            3000)
        self.project_updated.emit()

    def correct_trend(self):
        if not self.project.traces:
            QMessageBox.warning(self, "Предупреждение", "Нет трасс для обработки")
            return

        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Коррекция тренда",
                                     "Удалить линейный тренд из всех интервалов?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.status_bar.showMessage("Коррекция тренда - будет реализовано", 3000)

    def zoom_in(self):
        if hasattr(self.raster_canvas, 'zoom_in'):
            self.raster_canvas.zoom_in()
            self.update_zoom_label()

    def zoom_out(self):
        if hasattr(self.raster_canvas, 'zoom_out'):
            self.raster_canvas.zoom_out()
            self.update_zoom_label()

    def zoom_original(self):
        if hasattr(self.raster_canvas, 'zoom_original'):
            self.raster_canvas.zoom_original()
            self.update_zoom_label()

    def fit_to_view(self):
        if hasattr(self.raster_canvas, 'fit_to_view'):
            self.raster_canvas.fit_to_view()
            self.update_zoom_label()

    def update_zoom_label(self):
        """Обновляет отображение масштаба."""
        if hasattr(self.raster_canvas, 'zoom_factor'):
            zoom_percent = int(self.raster_canvas.zoom_factor * 100)
            self.status_bar.showMessage(f"Масштаб: {zoom_percent}%", 2000)

    def show_about(self):
        QMessageBox.about(self, "О программе",
                          "Seismogram Digitizer v0.1\n\n"
                          "Программа для ручной оцифровки аналоговых сейсмограмм.\n"
                          "НИР: Оцифровка аналоговых сейсмограмм сильных землетрясений\n\n"
                          "Используемые технологии:\n"
                          "- PyQt5 для интерфейса\n"
                          "- OpenGL для отображения\n"
                          "- NumPy/SciPy для вычислений\n"
                          "- ObsPy для работы с сейсмическими форматами")

    def show_help(self):
        QMessageBox.information(self, "Справка",
                                "Краткая справка:\n\n"
                                "1. Импортируйте сейсмограмму через меню 'Файл' → 'Импорт растра'\n"
                                "2. Создайте трассы через 'Инструменты' → 'Создать трассу'\n"
                                "3. Щелкайте левой кнопкой мыши для оцифровки точек\n"
                                "4. Правая кнопка завершает интервал\n"
                                "5. Управляйте трассами и интервалами в левой панели\n"
                                "6. Экспортируйте данные через меню 'Файл' → 'Экспорт'")

    def maybe_save(self) -> bool:
        # TODO: Проверить, были ли изменения в проекте
        return True

    def load_settings(self):
        settings = QSettings("SeismologyLab", "SeismogramDigitizer")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        settings = QSettings("SeismologyLab", "SeismogramDigitizer")
        settings.setValue("geometry", self.saveGeometry())

        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш."""
        # Горячие клавиши для управления
        if event.key() == Qt.Key_T and event.modifiers() & Qt.ControlModifier:
            # Ctrl+T - создать трассу
            self.create_trace()
        elif event.key() == Qt.Key_M and event.modifiers() & Qt.ControlModifier:
            # Ctrl+M - управление трассами
            self.show_trace_manager()
        elif event.key() == Qt.Key_I and event.modifiers() & Qt.ControlModifier:
            # Ctrl+I - интерполировать все
            self.interpolate_all()
        elif event.key() == Qt.Key_Delete:
            # Delete - очистить текущий интервал
            if hasattr(self.raster_canvas, 'clear_current_interval'):
                self.raster_canvas.clear_current_interval()
        elif event.key() == Qt.Key_Escape:
            # Esc - сброс
            if hasattr(self.raster_canvas, 'clear_current_interval'):
                self.raster_canvas.clear_current_interval()
        else:
            super().keyPressEvent(event)

    def show_trace_manager(self):
        """Показывает диалог управления трассами."""
        from gui.simple_trace_panel import SimpleTraceDialog
        dialog = SimpleTraceDialog(self.project, self)
        dialog.show()

    def update_project_info(self):
        """Обновляет информацию о проекте."""
        if self.project:
            stats = self.project.get_statistics()
            info_text = f"Проект: {stats['name']} | "
            info_text += f"Трасс: {stats['traces_count']} | "
            info_text += f"Интервалов: {stats['total_intervals']}"
        else:
            self.project_info_label.setText("Проект: Новый")

    def on_project_updated(self):
        """Обработчик обновления проекта."""
        self.update_project_info()
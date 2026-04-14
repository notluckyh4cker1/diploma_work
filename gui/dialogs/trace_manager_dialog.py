from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView,
                             QMessageBox, QWidget, QLabel, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
import uuid


class TraceManagerDialog(QDialog):
    """Диалог управления трассами"""

    start_trace_selection = pyqtSignal(object)  # Сигнал для начала выделения трассы
    trace_visibility_changed = pyqtSignal()  # Сигнал об изменении видимости

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Управление трассами")
        self.setMinimumSize(700, 500)

        self.setup_ui()
        self.load_traces()

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)

        # Информационная метка
        info_label = QLabel("Список сейсмических трасс в проекте:")
        info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)

        # Таблица трасс
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Название", "ID", "Интервалы", "Точки", "Видимость"])

        # Настройка таблицы
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Первая панель кнопок (управление трассами)
        panel1 = QWidget()
        panel1_layout = QHBoxLayout(panel1)
        panel1_layout.setContentsMargins(0, 5, 0, 5)

        self.add_trace_btn = QPushButton("➕ Новая трасса")
        self.add_trace_btn.clicked.connect(self.add_trace)
        panel1_layout.addWidget(self.add_trace_btn)

        self.edit_trace_btn = QPushButton("✏️ Редактировать")
        self.edit_trace_btn.clicked.connect(self.edit_trace)
        panel1_layout.addWidget(self.edit_trace_btn)

        self.delete_trace_btn = QPushButton("🗑️ Удалить")
        self.delete_trace_btn.clicked.connect(self.delete_trace)
        panel1_layout.addWidget(self.delete_trace_btn)

        panel1_layout.addStretch()

        self.start_edit_btn = QPushButton("🎯 Начать оцифровку")
        self.start_edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_edit_btn.clicked.connect(self.start_editing)
        panel1_layout.addWidget(self.start_edit_btn)

        layout.addWidget(panel1)

        # Вторая панель кнопок (управление видимостью)
        panel2 = QWidget()
        panel2_layout = QHBoxLayout(panel2)
        panel2_layout.setContentsMargins(0, 5, 0, 5)

        # Кнопки для работы с видимостью (все статические)
        self.hide_selected_btn = QPushButton("👁️ Скрыть выбранную")
        self.hide_selected_btn.clicked.connect(self.hide_selected_trace)
        panel2_layout.addWidget(self.hide_selected_btn)

        self.show_selected_btn = QPushButton("👁️ Показать выбранную")
        self.show_selected_btn.clicked.connect(self.show_selected_trace)
        panel2_layout.addWidget(self.show_selected_btn)

        panel2_layout.addStretch()

        self.hide_all_btn = QPushButton("🚫 Скрыть все")
        self.hide_all_btn.clicked.connect(self.hide_all_traces)
        panel2_layout.addWidget(self.hide_all_btn)

        self.show_all_btn = QPushButton("✅ Показать все")
        self.show_all_btn.clicked.connect(self.show_all_traces)
        panel2_layout.addWidget(self.show_all_btn)

        layout.addWidget(panel2)

        # Третья панель (кнопки диалога)
        panel3 = QWidget()
        panel3_layout = QHBoxLayout(panel3)
        panel3_layout.setContentsMargins(0, 5, 0, 5)

        panel3_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self.load_traces)
        panel3_layout.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        panel3_layout.addWidget(self.close_btn)

        layout.addWidget(panel3)

    def load_traces(self):
        """Загрузить список трасс в таблицу"""
        self.table.setRowCount(0)

        if not self.project or not self.project.traces:
            return

        for row, trace in enumerate(self.project.traces):
            self.table.insertRow(row)

            # Название трассы
            name_item = QTableWidgetItem(trace.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            # ID трассы (укороченный для отображения)
            short_id = trace.id[:8] + "..." if len(trace.id) > 8 else trace.id
            id_item = QTableWidgetItem(short_id)
            id_item.setToolTip(trace.id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, id_item)

            # Количество интервалов
            intervals_count = len(trace.intervals)
            intervals_item = QTableWidgetItem(str(intervals_count))
            intervals_item.setTextAlignment(Qt.AlignCenter)
            intervals_item.setFlags(intervals_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, intervals_item)

            # Количество точек
            total_points = sum(len(interval.points) for interval in trace.intervals)
            points_item = QTableWidgetItem(str(total_points))
            points_item.setTextAlignment(Qt.AlignCenter)
            points_item.setFlags(points_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, points_item)

            # Видимость
            visible_text = "✓ Видима" if trace.is_visible else "✗ Скрыта"
            visible_item = QTableWidgetItem(visible_text)
            visible_item.setTextAlignment(Qt.AlignCenter)
            visible_item.setFlags(visible_item.flags() & ~Qt.ItemIsEditable)

            # Цвет для видимости
            if trace.is_visible:
                visible_item.setBackground(QBrush(QColor(200, 255, 200)))
            else:
                visible_item.setBackground(QBrush(QColor(255, 200, 200)))

            self.table.setItem(row, 4, visible_item)

            # Сохраняем ссылку на трассу
            self.table.item(row, 0).setData(Qt.UserRole, trace.id)

    def get_selected_trace(self):
        """Получить выбранную трассу"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            trace_id = self.table.item(current_row, 0).data(Qt.UserRole)
            return self.project.get_trace(trace_id)
        return None

    def add_trace(self):
        """Добавить новую трассу"""
        from PyQt5.QtWidgets import QInputDialog
        from models.trace import Trace

        name, ok = QInputDialog.getText(self, "Новая трасса", "Введите название трассы:")
        if ok and name:
            trace_id = str(uuid.uuid4())
            trace = Trace(
                id=trace_id,
                name=name,
                raster_coords=((0, 0), (0, 0)),
                is_visible=True,
                is_editing=False
            )
            self.project.add_trace(trace)
            self.load_traces()
            self.trace_visibility_changed.emit()
            QMessageBox.information(self, "Успех", f"Трасса '{name}' добавлена")

    def edit_trace(self):
        """Редактировать название трассы"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для редактирования")
            return

        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Редактирование",
                                        "Введите новое название:",
                                        text=trace.name)
        if ok and name:
            trace.name = name
            self.load_traces()
            QMessageBox.information(self, "Успех", f"Трасса переименована в '{name}'")

    def delete_trace(self):
        """Удалить выбранную трассу"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для удаления")
            return

        total_points = sum(len(interval.points) for interval in trace.intervals)

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить трассу '{trace.name}'?\n"
            f"(Содержит {len(trace.intervals)} интервалов и {total_points} точек)",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Сохраняем ID перед удалением
            trace_id = trace.id

            # Очищаем данные трассы
            for interval in trace.intervals:
                interval.points.clear()
            trace.intervals.clear()

            # Удаляем из проекта
            self.project.remove_trace(trace_id)

            # Проверяем родительский canvas
            parent = self.parent()
            if parent and hasattr(parent, 'canvas'):
                canvas = parent.canvas
                if canvas.current_trace and canvas.current_trace.id == trace_id:
                    canvas.current_trace = None
                    canvas.current_interval = None
                    canvas.update_display()

                # Обновляем селектор в controls_panel
                if hasattr(parent, 'update_trace_selector'):
                    parent.update_trace_selector()

            self.load_traces()
            self.trace_visibility_changed.emit()

            # Принудительная сборка мусора
            import gc
            gc.collect()

            QMessageBox.information(self, "Успех", f"Трасса '{trace.name}' удалена")

    def hide_selected_trace(self):
        """Скрыть выбранную трассу"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для скрытия")
            return

        trace.is_visible = False
        self.load_traces()
        self.trace_visibility_changed.emit()

        # Обновляем отображение
        parent = self.parent()
        if parent and hasattr(parent, 'canvas'):
            parent.canvas.update_display()
            if hasattr(parent, 'update_trace_selector'):
                parent.update_trace_selector()

    def show_selected_trace(self):
        """Показать выбранную трассу"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для показа")
            return

        trace.is_visible = True
        self.load_traces()
        self.trace_visibility_changed.emit()

        # Обновляем отображение
        parent = self.parent()
        if parent and hasattr(parent, 'canvas'):
            parent.canvas.update_display()
            if hasattr(parent, 'update_trace_selector'):
                parent.update_trace_selector()

    def hide_all_traces(self):
        """Скрыть все трассы"""
        for trace in self.project.traces:
            trace.is_visible = False
        self.load_traces()
        self.trace_visibility_changed.emit()

        # Обновляем отображение
        parent = self.parent()
        if parent and hasattr(parent, 'canvas'):
            parent.canvas.update_display()
            if hasattr(parent, 'update_trace_selector'):
                parent.update_trace_selector()

    def show_all_traces(self):
        """Показать все трассы"""
        for trace in self.project.traces:
            trace.is_visible = True
        self.load_traces()
        self.trace_visibility_changed.emit()

        # Обновляем отображение
        parent = self.parent()
        if parent and hasattr(parent, 'canvas'):
            parent.canvas.update_display()
            if hasattr(parent, 'update_trace_selector'):
                parent.update_trace_selector()

    def start_editing(self):
        """Начать редактирование выбранной трассы"""
        trace = self.get_selected_trace()
        if not trace:
            QMessageBox.warning(self, "Ошибка", "Выберите трассу для оцифровки")
            return

        if not self.project.raster_data:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите растер")
            return

        self.start_trace_selection.emit(trace)
        self.accept()

    def refresh(self):
        """Обновить таблицу"""
        self.load_traces()
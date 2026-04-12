from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel,
                             QLineEdit, QHeaderView, QMessageBox, QInputDialog,
                             QDialogButtonBox, QMenu)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
from models.trace import Trace


class TraceManagerDialog(QDialog):
    """Диалоговое окно управления трассами"""

    # Сигналы
    trace_selected = pyqtSignal(object)  # Выбрана трасса для просмотра
    trace_created = pyqtSignal(object)  # Создана новая трасса
    start_trace_selection = pyqtSignal(object)  # Начать выделение трассы

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.current_trace = None
        self.setWindowTitle("Управление трассами")
        self.resize(600, 400)

        self.init_ui()
        self.update_table()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title_label = QLabel("Список трасс")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Таблица трасс
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Название", "Состояние", "Интервалов", "Область"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        # Подключаем двойной клик
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        # Кнопка создания
        self.create_btn = QPushButton("Создать трассу")
        self.create_btn.clicked.connect(self.create_trace_dialog)
        self.create_btn.setToolTip("Создать новую трассу")
        btn_layout.addWidget(self.create_btn)

        # Кнопка выделения
        self.select_btn = QPushButton("Выделить трассу")
        self.select_btn.clicked.connect(self.select_trace_for_digitization)
        self.select_btn.setEnabled(False)
        self.select_btn.setToolTip("Выделить выбранную трассу на изображении")
        btn_layout.addWidget(self.select_btn)

        # Кнопка удаления
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_selected_trace)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)

        # Кнопки диалога
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def update_table(self):
        """Обновляет таблицу трасс"""
        self.table.setRowCount(len(self.project.traces))

        for row, trace in enumerate(self.project.traces):
            # Название
            name_item = QTableWidgetItem(trace.name)
            name_item.setData(Qt.UserRole, trace)
            self.table.setItem(row, 0, name_item)

            # Состояние
            if getattr(trace, 'is_editing', False):
                status = "Редактируется"
                color = QColor(255, 200, 200)  # Светло-красный
            elif getattr(trace, 'intervals', []):
                status = "Оцифрована"
                color = QColor(200, 255, 200)  # Светло-зеленый
            else:
                status = "Новая"
                color = QColor(240, 240, 240)  # Серый

            status_item = QTableWidgetItem(status)
            status_item.setBackground(QBrush(color))
            self.table.setItem(row, 1, status_item)

            # Количество интервалов
            intervals = getattr(trace, 'intervals', [])
            count_item = QTableWidgetItem(str(len(intervals)))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, count_item)

            # Область
            if hasattr(trace, 'bounding_box') and trace.bounding_box:
                x1, y1, x2, y2 = trace.bounding_box
                area_item = QTableWidgetItem(f"{int(x2 - x1)}x{int(y2 - y1)}")
            else:
                area_item = QTableWidgetItem("Не выделена")
            area_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, area_item)

        # Выделяем первую строку, если есть трассы
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.update_buttons_state()

    def on_cell_double_clicked(self, row, column):
        """Обработка двойного клика по ячейке"""
        self.select_trace_for_digitization()

    def update_buttons_state(self):
        """Обновляет состояние кнопок"""
        selected_items = self.table.selectedItems()
        has_selection = len(selected_items) > 0

        self.select_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def get_selected_trace(self):
        """Возвращает выбранную трассу"""
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None

    def create_trace_dialog(self):
        """Создает новую трассу"""
        if not self.project.raster:
            QMessageBox.warning(self, "Ошибка",
                                "Сначала загрузите сейсмограмму")
            return

        # Простой диалог ввода названия
        name, ok = QInputDialog.getText(
            self, "Создание трассы",
            "Введите название трассы:",
            QLineEdit.Normal,
            f"Трасса {len(self.project.traces) + 1}"
        )

        if ok and name.strip():
            # Создаем трассу
            new_trace = Trace(name=name.strip())
            new_trace.is_editing = True

            # Добавляем в проект
            if hasattr(self.project, 'add_trace'):
                self.project.add_trace(new_trace)
            else:
                if not hasattr(self.project, 'traces'):
                    self.project.traces = []
                self.project.traces.append(new_trace)

            # Обновляем таблицу
            self.update_table()

            # Сигнализируем о начале выделения
            self.start_trace_selection.emit(new_trace)

            # Закрываем диалог
            self.accept()

    def select_trace_for_digitization(self):
        """Выбирает трассу для выделения на изображении"""
        trace = self.get_selected_trace()
        if trace:
            trace.is_editing = True
            self.start_trace_selection.emit(trace)
            self.accept()

    def delete_selected_trace(self):
        """Удаляет выбранную трассу"""
        trace = self.get_selected_trace()
        if not trace:
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить трассу '{trace.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if hasattr(self.project, 'remove_trace'):
                self.project.remove_trace(trace)
            else:
                if trace in self.project.traces:
                    self.project.traces.remove(trace)

            self.update_table()

    def show_context_menu(self, position):
        """Показывает контекстное меню"""
        trace = self.get_selected_trace()
        if not trace:
            return

        menu = QMenu()

        # Переименовать
        rename_action = menu.addAction("Переименовать")
        rename_action.triggered.connect(lambda: self.rename_trace(trace))

        # Выделить
        select_action = menu.addAction("Выделить на изображении")
        select_action.triggered.connect(lambda: self.select_trace_for_digitization())

        # Удалить
        delete_action = menu.addAction("Удалить")
        delete_action.triggered.connect(lambda: self.delete_selected_trace())

        menu.exec_(self.table.viewport().mapToGlobal(position))

    def rename_trace(self, trace):
        """Переименовывает трассу"""
        new_name, ok = QInputDialog.getText(
            self, "Переименование",
            "Новое название:",
            QLineEdit.Normal,
            trace.name
        )

        if ok and new_name.strip():
            trace.name = new_name.strip()
            self.update_table()
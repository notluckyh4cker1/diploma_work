# Главный файл для запуска приложения оцифровки сейсмограмм

import sys

from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    """Основная функция запуска приложения."""
    try:
        # Создаем приложение
        app = QApplication(sys.argv)
        app.setApplicationName("Seismogram Digitizer")
        app.setOrganizationName("Seismology Lab")

        # Устанавливаем стиль Fusion для более современного вида
        app.setStyle('Fusion')

        # Простой стиль для приложения
        app.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QMenuBar {
                background-color: #e0e0e0;
                border-bottom: 1px solid #cccccc;
            }
            QMenuBar::item:selected {
                background-color: #d0d0d0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                padding: 5px 15px;
                border: 1px solid #aaaaaa;
                border-radius: 3px;
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                  stop: 0 #f6f7fa, stop: 1 #dadbde);
            }
            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                  stop: 0 #e7e8eb, stop: 1 #cbcccf);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                  stop: 0 #dadbde, stop: 1 #bcbdc0);
            }
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QGraphicsView {
                border: 1px solid #aaaaaa;
                background-color: #f8f8f8;
            }
            QStatusBar {
                background-color: #e0e0e0;
                border-top: 1px solid #cccccc;
            }
        """)

        # Создаем главное окно
        window = MainWindow()
        window.show()

        # Запускаем цикл событий
        return app.exec_()

    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
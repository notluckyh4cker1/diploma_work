# Запуск приложения

import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()

    screen_rect = app.primaryScreen().availableGeometry()  # доступная область экрана (без панели задач)
    margin_w, margin_h = 40, 60  # запас для меню и панели задач

    window.resize(screen_rect.width() - margin_w, screen_rect.height() - margin_h)
    window.move(screen_rect.left() + margin_w // 2, screen_rect.top() + margin_h // 2)

    window.show()
    sys.exit(app.exec_())
"""
Точка входа в приложение Реометр R-100.
Запуск: python main.py
"""

import sys
import os

# Высокое разрешение DPI на Windows
if sys.platform == "win32":
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

# Включаем масштабирование до создания QApplication
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from app.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Реометр R-100")
    app.setOrganizationName("NIIEMI")

    # На Windows используем Segoe UI как системный шрифт
    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI", 11))
    else:
        app.setFont(QFont("", 14))

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

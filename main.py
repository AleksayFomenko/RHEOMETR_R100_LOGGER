"""
Точка входа в приложение Реометр R-100.
Запуск: python main.py
"""

import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication
from app.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Реометр R-100")
    app.setOrganizationName("NIIEMI")
    app.setFont(QFont("", 14))

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

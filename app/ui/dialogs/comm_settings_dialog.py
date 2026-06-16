"""
Диалог настроек связи Modbus RTU.

Для добавления нового параметра:
  1. Добавьте поле в CommConfig (settings.py)
  2. Создайте виджет в _build_ui()
  3. Заполните в _populate(), считайте в get_config()
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import CommConfig

_BAUDRATES = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
_PARITIES  = [("Нет (N)",   "N"),
              ("Чётность (E)", "E"),
              ("Нечётность (O)", "O")]


class CommSettingsDialog(QDialog):
    def __init__(self, config: CommConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки связи Modbus RTU")
        self.setMinimumWidth(380)
        self._build_ui()
        self._populate(config)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Последовательный порт ─────────────────────────────────────────
        port_group = QGroupBox("Последовательный порт")
        port_form  = QFormLayout(port_group)

        port_row = QHBoxLayout()
        self._port = QComboBox()
        self._port.setEditable(True)
        self._port.setMinimumWidth(120)
        port_row.addWidget(self._port)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self._refresh_ports)
        port_row.addWidget(refresh_btn)

        self._baudrate  = QComboBox()
        self._baudrate.addItems(_BAUDRATES)

        self._data_bits = QComboBox()
        self._data_bits.addItems(["7", "8"])

        self._parity = QComboBox()
        for label, _ in _PARITIES:
            self._parity.addItem(label)

        self._stop_bits = QComboBox()
        self._stop_bits.addItems(["1", "2"])

        port_form.addRow("Порт:",        port_row)
        port_form.addRow("Скорость:",    self._baudrate)
        port_form.addRow("Биты данных:", self._data_bits)
        port_form.addRow("Чётность:",    self._parity)
        port_form.addRow("Стоп-биты:",   self._stop_bits)

        layout.addWidget(port_group)

        # ── Modbus ────────────────────────────────────────────────────────
        mb_group = QGroupBox("Modbus")
        mb_form  = QFormLayout(mb_group)

        self._slave_addr = QSpinBox()
        self._slave_addr.setRange(1, 247)

        self._register = QSpinBox()
        self._register.setRange(0, 65535)

        self._decimals = QSpinBox()
        self._decimals.setRange(0, 6)
        self._decimals.setToolTip("Кол-во знаков после запятой в значении регистра")

        self._timeout = QDoubleSpinBox()
        self._timeout.setRange(0.1, 5.0)
        self._timeout.setSingleStep(0.1)
        self._timeout.setSuffix(" с")

        self._interval = QSpinBox()
        self._interval.setRange(50, 10000)
        self._interval.setSingleStep(50)
        self._interval.setSuffix(" мс")

        mb_form.addRow("Адрес устройства:", self._slave_addr)
        mb_form.addRow("Адрес регистра:",   self._register)
        mb_form.addRow("Знаков после зап.:", self._decimals)
        mb_form.addRow("Тайм-аут:",         self._timeout)
        mb_form.addRow("Интервал опроса:",  self._interval)

        # ── Добавляйте новые параметры Modbus здесь ───────────────────────
        # self._func_code = QSpinBox(); ...
        # ─────────────────────────────────────────────────────────────────

        layout.addWidget(mb_group)

        # ── Симуляция ─────────────────────────────────────────────────────
        sim_group = QGroupBox("Режим симуляции (без устройства)")
        sim_group.setCheckable(True)
        sim_layout = QVBoxLayout(sim_group)

        self._sim_sigmoid = QRadioButton("Синтетика (сигмоид)")
        self._sim_csv     = QRadioButton("Воспроизвести CSV")
        self._sim_sigmoid.setChecked(True)
        sim_layout.addWidget(self._sim_sigmoid)
        sim_layout.addWidget(self._sim_csv)

        csv_row = QHBoxLayout()
        self._csv_path = QLineEdit()
        self._csv_path.setPlaceholderText("Путь к CSV файлу…")
        self._csv_path.setReadOnly(True)
        browse_btn = QPushButton("Обзор…")
        browse_btn.clicked.connect(self._browse_csv)
        csv_row.addWidget(self._csv_path)
        csv_row.addWidget(browse_btn)
        sim_layout.addLayout(csv_row)

        self._sim_csv.toggled.connect(self._csv_path.setEnabled)
        self._sim_csv.toggled.connect(browse_btn.setEnabled)
        self._csv_path.setEnabled(False)
        browse_btn.setEnabled(False)

        self._sim_group = sim_group
        layout.addWidget(sim_group)

        # ── Кнопки ───────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_ports()

    def _refresh_ports(self) -> None:
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            ports = []
        current = self._port.currentText()
        self._port.clear()
        self._port.addItems(ports)
        if current:
            idx = self._port.findText(current)
            if idx >= 0:
                self._port.setCurrentIndex(idx)
            else:
                self._port.setCurrentText(current)

    def _browse_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать CSV для эмулятора", "",
            "CSV файлы (*.csv);;Все файлы (*)",
        )
        if path:
            self._csv_path.setText(path)

    def _populate(self, cfg: CommConfig) -> None:
        self._port.setCurrentText(cfg.port)
        idx = self._baudrate.findText(str(cfg.baudrate))
        self._baudrate.setCurrentIndex(idx if idx >= 0 else 3)

        self._data_bits.setCurrentText(str(cfg.data_bits))

        parity_codes = [code for _, code in _PARITIES]
        p_idx = parity_codes.index(cfg.parity) if cfg.parity in parity_codes else 0
        self._parity.setCurrentIndex(p_idx)

        self._stop_bits.setCurrentText(str(cfg.stop_bits))
        self._slave_addr.setValue(cfg.slave_address)
        self._register.setValue(cfg.register_address)
        self._decimals.setValue(cfg.register_decimals)
        self._timeout.setValue(cfg.timeout)
        self._interval.setValue(cfg.read_interval_ms)

        self._sim_group.setChecked(cfg.simulation_mode)
        if cfg.csv_path:
            self._sim_csv.setChecked(True)
            self._csv_path.setText(cfg.csv_path)
        else:
            self._sim_sigmoid.setChecked(True)

    def get_config(self) -> CommConfig:
        parity_code = _PARITIES[self._parity.currentIndex()][1]
        return CommConfig(
            port              = self._port.currentText().strip(),
            baudrate          = int(self._baudrate.currentText()),
            data_bits         = int(self._data_bits.currentText()),
            parity            = parity_code,
            stop_bits         = int(self._stop_bits.currentText()),
            slave_address     = self._slave_addr.value(),
            register_address  = self._register.value(),
            register_decimals = self._decimals.value(),
            timeout           = self._timeout.value(),
            read_interval_ms  = self._interval.value(),
            simulation_mode   = self._sim_group.isChecked(),
            csv_path          = self._csv_path.text() if self._sim_csv.isChecked() else "",
        )

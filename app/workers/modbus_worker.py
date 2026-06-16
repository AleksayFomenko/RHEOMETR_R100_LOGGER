"""
Поток опроса Modbus RTU.

Сигналы:
  data_point(float)            — новое сырое значение с датчика
  connection_status(bool, str) — (подключено, сообщение)
  error_occurred(str)          — текст ошибки (не фатальная)

Режим симуляции (CommConfig.simulation_mode = True):
  Генерирует синтетическую кривую вулканизации (сигмоид + шум).
  Реальный modbus не нужен — удобно для разработки UI.
"""

from __future__ import annotations
import math
import os
import random
import time

from PyQt5.QtCore import QThread, pyqtSignal

from app.core.settings import CommConfig


class ModbusWorker(QThread):
    data_point        = pyqtSignal(float)       # сырое значение
    connection_status = pyqtSignal(bool, str)   # (подключено, сообщение)
    error_occurred    = pyqtSignal(str)

    def __init__(self, config: CommConfig, parent=None) -> None:
        super().__init__(parent)
        self._cfg = config
        self._running = False
        self._instrument = None

    # ── Интерфейс ─────────────────────────────────────────────────────────────

    def stop(self) -> None:
        self._running = False

    # ── Поток ─────────────────────────────────────────────────────────────────

    def run(self) -> None:
        self._running = True

        if self._cfg.simulation_mode:
            if self._cfg.csv_path:
                self._replay_csv()
            else:
                self._run_sigmoid()
        else:
            if not self._connect():
                return
            self._run_modbus()

        if self._instrument is not None:
            try:
                self._instrument.serial.close()
            except Exception:
                pass
        self._instrument = None

    # ── Режимы работы ────────────────────────────────────────────────────────

    def _run_sigmoid(self) -> None:
        """Синтетическая кривая вулканизации."""
        self.connection_status.emit(True, "Симуляция: синтетика")
        start = time.monotonic()
        while self._running:
            elapsed = time.monotonic() - start
            self.data_point.emit(self._simulate(elapsed))
            self.msleep(self._cfg.read_interval_ms)

    def _run_modbus(self) -> None:
        """Реальный опрос Modbus RTU."""
        while self._running:
            try:
                self.data_point.emit(self._read_register())
            except Exception as exc:
                self.error_occurred.emit(str(exc))
            self.msleep(self._cfg.read_interval_ms)

    def _replay_csv(self) -> None:
        """
        Воспроизводит CSV с оригинальными интервалами между точками.
        Интервал = разница времён соседних строк в файле.
        """
        from app.core.export import import_csv
        try:
            times, raw, _ = import_csv(self._cfg.csv_path)
        except Exception as exc:
            self.connection_status.emit(False, f"Ошибка загрузки CSV: {exc}")
            return

        if not times:
            self.connection_status.emit(False, "CSV эмулятор: файл пустой")
            return

        name = os.path.basename(self._cfg.csv_path)
        self.connection_status.emit(True, f"Эмулятор CSV: {name}")

        self.data_point.emit(raw[0])

        for i in range(1, len(times)):
            if not self._running:
                break
            interval_ms = max(1, int((times[i] - times[i - 1]) * 1000))
            self.msleep(interval_ms)
            if self._running:
                self.data_point.emit(raw[i])

        if self._running:
            self.connection_status.emit(False, f"Эмулятор CSV: данные закончились ({name})")

    # ── Подключение к устройству ──────────────────────────────────────────────

    def _connect(self) -> bool:
        try:
            import minimalmodbus
            import serial

            cfg = self._cfg
            instr = minimalmodbus.Instrument(cfg.port, cfg.slave_address)
            instr.serial.baudrate = cfg.baudrate
            instr.serial.bytesize = cfg.data_bits
            instr.serial.parity   = cfg.parity
            instr.serial.stopbits = cfg.stop_bits
            instr.serial.timeout  = cfg.timeout
            self._instrument = instr
            self.connection_status.emit(True, f"Подключено: {cfg.port}")
            return True
        except Exception as exc:
            self.connection_status.emit(False, f"Ошибка подключения: {exc}")
            return False

    def _read_register(self) -> float:
        cfg = self._cfg
        return self._instrument.read_register(
            cfg.register_address,
            numberOfDecimals=cfg.register_decimals,
        )

    # ── Симуляция ─────────────────────────────────────────────────────────────

    @staticmethod
    def _simulate(elapsed_s: float) -> float:
        """
        Синтетическая кривая реометра: сигмоид + шум.
        ML=2.0, MH=18.0, центр кривой ~ 3 мин (180 с).
        Измените параметры под свой прибор.
        """
        ml, mh = 2.0, 18.0
        k,  t0 = 0.045, 190.0
        value = ml + (mh - ml) / (1.0 + math.exp(-k * (elapsed_s - t0)))
        return max(0.0, value + random.gauss(0.0, 0.25))

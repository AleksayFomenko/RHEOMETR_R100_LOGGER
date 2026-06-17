"""
Хранение и загрузка настроек через QSettings.

Для добавления новой группы настроек:
1. Создайте dataclass с полями по умолчанию
2. Добавьте методы load_*/save_* в SettingsManager
"""

from dataclasses import dataclass, field
from PyQt5.QtCore import QSettings

_ORG = "NIIEMI"
_APP = "Rheometr_R100"


@dataclass
class CommConfig:
    """Настройки Modbus RTU соединения."""
    port: str = "COM1"
    baudrate: int = 9600
    data_bits: int = 8
    parity: str = "N"           # N=None, E=Even, O=Odd
    stop_bits: int = 1
    slave_address: int = 1
    register_address: int = 0
    register_decimals: int = 2  # кол-во знаков после запятой в регистре
    timeout: float = 0.5        # секунды
    read_interval_ms: int = 100 # интервал опроса, мс
    simulation_mode: bool = True
    csv_path: str = ""          # путь к CSV для эмулятора (пусто = синтетика)


@dataclass
class TestConfig:
    """Настройки испытания (метаданные)."""
    operator: str = ""
    material_type: str = ""
    sample_id: str = ""
    test_duration_min: int = 0   # 0 = без ограничения
    temperature: float = 160.0
    notes: str = ""


# ── Дополнительные группы настроек добавляются сюда ──────────────────────────
# @dataclass
# class FilterConfig:
#     filter_type: str = "rolling_max"
#     window_size: int = 20
# ─────────────────────────────────────────────────────────────────────────────


class SettingsManager:
    def __init__(self) -> None:
        self._qs = QSettings(_ORG, _APP)

    # ── Comm ─────────────────────────────────────────────────────────────────

    def load_comm(self) -> CommConfig:
        cfg = CommConfig()
        s = self._qs
        s.beginGroup("comm")
        cfg.port             = s.value("port",             cfg.port,             str)
        cfg.baudrate         = s.value("baudrate",         cfg.baudrate,         int)
        cfg.data_bits        = s.value("data_bits",        cfg.data_bits,        int)
        cfg.parity           = s.value("parity",           cfg.parity,           str)
        cfg.stop_bits        = s.value("stop_bits",        cfg.stop_bits,        int)
        cfg.slave_address    = s.value("slave_address",    cfg.slave_address,    int)
        cfg.register_address = s.value("register_address", cfg.register_address, int)
        cfg.register_decimals= s.value("register_decimals",cfg.register_decimals,int)
        cfg.timeout          = s.value("timeout",          cfg.timeout,          float)
        cfg.read_interval_ms = s.value("read_interval_ms", cfg.read_interval_ms, int)
        cfg.simulation_mode  = s.value("simulation_mode",  cfg.simulation_mode,  bool)
        cfg.csv_path         = s.value("csv_path",         cfg.csv_path,         str)
        s.endGroup()
        return cfg

    def save_comm(self, cfg: CommConfig) -> None:
        s = self._qs
        s.beginGroup("comm")
        s.setValue("port",              cfg.port)
        s.setValue("baudrate",          cfg.baudrate)
        s.setValue("data_bits",         cfg.data_bits)
        s.setValue("parity",            cfg.parity)
        s.setValue("stop_bits",         cfg.stop_bits)
        s.setValue("slave_address",     cfg.slave_address)
        s.setValue("register_address",  cfg.register_address)
        s.setValue("register_decimals", cfg.register_decimals)
        s.setValue("timeout",           cfg.timeout)
        s.setValue("read_interval_ms",  cfg.read_interval_ms)
        s.setValue("simulation_mode",   cfg.simulation_mode)
        s.setValue("csv_path",          cfg.csv_path)
        s.endGroup()

    # ── Test ─────────────────────────────────────────────────────────────────

    def load_test(self) -> TestConfig:
        cfg = TestConfig()
        s = self._qs
        s.beginGroup("test")
        cfg.operator        = s.value("operator",        cfg.operator,        str)
        cfg.material_type   = s.value("material_type",   cfg.material_type,   str)
        cfg.sample_id       = s.value("sample_id",       cfg.sample_id,       str)
        cfg.test_duration_min = s.value("test_duration_min", cfg.test_duration_min, int)
        cfg.temperature     = s.value("temperature",     cfg.temperature,     float)
        cfg.notes           = s.value("notes",           cfg.notes,           str)
        s.endGroup()
        return cfg

    def save_test(self, cfg: TestConfig) -> None:
        s = self._qs
        s.beginGroup("test")
        s.setValue("operator",        cfg.operator)
        s.setValue("material_type",   cfg.material_type)
        s.setValue("sample_id",       cfg.sample_id)
        s.setValue("test_duration_min", cfg.test_duration_min)
        s.setValue("temperature",     cfg.temperature)
        s.setValue("notes",           cfg.notes)
        s.endGroup()

"""
Фильтры сигнала реального времени.

Для добавления нового фильтра:
  1. Унаследуйте BaseFilter
  2. Декорируйте @register_filter("имя")
  3. Используйте create_filter("имя", **kwargs) в main_window.py

Используемая стратегия (по умолчанию — rolling_max):
  Скользящий максимум → огибающая пика момента при вулканизации.
  Опционально можно добавить Savitzky-Golay поверх как финальный шаг.
"""

from __future__ import annotations
from collections import deque
from typing import Callable, Dict, Type

import numpy as np

_REGISTRY: Dict[str, Type["BaseFilter"]] = {}


def register_filter(name: str) -> Callable:
    def decorator(cls: Type["BaseFilter"]) -> Type["BaseFilter"]:
        _REGISTRY[name] = cls
        return cls
    return decorator


def create_filter(name: str, **kwargs) -> "BaseFilter":
    """Фабрика фильтров по имени из реестра."""
    cls = _REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Неизвестный фильтр: '{name}'. Доступные: {list(_REGISTRY)}")
    return cls(**kwargs)


# ── Базовый класс ─────────────────────────────────────────────────────────────

class BaseFilter:
    def process(self, value: float) -> float:
        raise NotImplementedError

    def reset(self) -> None:
        """Полный сброс, включая долгосрочную калибровку."""
        pass

    def soft_reset(self) -> None:
        """Сброс краткосрочного состояния (буферы), калибровка сохраняется.
        Используется при обрезке по пику — нулевой уровень NullCenter остаётся."""
        self.reset()  # по умолчанию: то же что полный сброс


# ── Без фильтра ───────────────────────────────────────────────────────────────

@register_filter("none")
class NoFilter(BaseFilter):
    def process(self, value: float) -> float:
        return value


# ── Скользящий максимум ───────────────────────────────────────────────────────

@register_filter("rolling_max")
class RollingMaxFilter(BaseFilter):
    """
    Возвращает 95-й перцентиль окна последних `window` отсчётов.
    Устойчив к одиночным выбросам: один аномальный отсчёт из 30 ≈ 3% → игнорируется.
    """
    def __init__(self, window: int = 20) -> None:
        self._window = window
        self._buf: deque[float] = deque(maxlen=window)

    def process(self, value: float) -> float:
        self._buf.append(value)
        return float(np.percentile(self._buf, 95))

    def reset(self) -> None:
        self._buf.clear()


# ── Скользящее среднее ────────────────────────────────────────────────────────

@register_filter("moving_average")
class MovingAverageFilter(BaseFilter):
    def __init__(self, window: int = 10) -> None:
        self._buf: deque[float] = deque(maxlen=window)

    def process(self, value: float) -> float:
        self._buf.append(value)
        return sum(self._buf) / len(self._buf)

    def reset(self) -> None:
        self._buf.clear()


# ── Экспоненциальное сглаживание ──────────────────────────────────────────────

@register_filter("exponential")
class ExponentialFilter(BaseFilter):
    def __init__(self, alpha: float = 0.3) -> None:
        self._alpha = alpha
        self._last: float | None = None

    def process(self, value: float) -> float:
        if self._last is None:
            self._last = value
        else:
            self._last = self._alpha * value + (1 - self._alpha) * self._last
        return self._last

    def reset(self) -> None:
        self._last = None


# ── Цепочка фильтров ─────────────────────────────────────────────────────────

class ChainFilter(BaseFilter):
    """Применяет фильтры последовательно: выход одного → вход следующего."""

    def __init__(self, *filters: BaseFilter) -> None:
        self._filters = list(filters)

    def process(self, value: float) -> float:
        for f in self._filters:
            value = f.process(value)
        return value

    def reset(self) -> None:
        for f in self._filters:
            f.reset()

    def soft_reset(self) -> None:
        for f in self._filters:
            f.soft_reset()


# ── Онлайн-выпрямитель (EMA-центр + отражение) ───────────────────────────────

@register_filter("online_rectifier")
class OnlineRectifierFilter(BaseFilter):
    """
    Каузальный выпрямитель для потокового сигнала:
      1. Центр отслеживается рекурсивным EMA: center = (1-a)*center + a*value
      2. Первый отсчёт инициализирует центр (center = value)
      3. Выход: abs(value - center) — нижняя ветвь зеркально поднимается вверх
      4. reset()/soft_reset() сбрасывают центр, чтобы следующий отсчёт
         переинициализировал его (нужно при обнаружении нового пика)
    """
    def __init__(self, alpha: float = 0.02) -> None:
        self._alpha  = alpha
        self._center: float | None = None

    def process(self, value: float) -> float:
        if self._center is None:
            self._center = value
            return abs(value)
        self._center = (1.0 - self._alpha) * self._center + self._alpha * value
        return abs(value - self._center)

    def reset(self) -> None:
        self._center = None

    def soft_reset(self) -> None:
        self._center = None


# ── Центрирование и выпрямление сигнала ──────────────────────────────────────

@register_filter("null_center")
class NullCenterFilter(BaseFilter):
    """
    Воспроизводит логику null_center.py в реальном времени:
      1. Калибровка: среднее первых `calibration_n` отсчётов → нулевой уровень
      2. Сдвиг:      shifted   = value - zero_level
      3. Модуль:     rectified = abs(shifted)

    Во время калибровки нулевой уровень — текущее скользящее среднее буфера,
    поэтому вывод стабилен с первой же точки.
    """

    def __init__(self, calibration_n: int = 50) -> None:
        self._cal_n = calibration_n
        self._cal_buf: list[float] = []
        self._zero: float | None = None

    def process(self, value: float) -> float:
        if self._zero is None:
            self._cal_buf.append(value)
            zero = sum(self._cal_buf) / len(self._cal_buf)
            if len(self._cal_buf) >= self._cal_n:
                self._zero = zero   # фиксируем ноль
        else:
            zero = self._zero
        return abs(value - zero)

    def reset(self) -> None:
        self._cal_buf.clear()
        self._zero = None

    def soft_reset(self) -> None:
        pass  # нулевой уровень (_zero) сохраняется — только он нам и нужен

    @property
    def calibrated(self) -> bool:
        """True когда нулевой уровень уже зафиксирован."""
        return self._zero is not None


# ── Фильтр Савицкого-Голея (реальное время) ──────────────────────────────────

@register_filter("savitzky_golay")
class SavitzkyGolayFilter(BaseFilter):
    """
    Сглаживание Савицкого-Голея в реальном времени.
    Хранит буфер последних `window_length` точек, возвращает последнее
    сглаженное значение. До заполнения буфера отдаёт входное значение.
    """
    def __init__(self, window_length: int = 10, polyorder: int = 3) -> None:
        from scipy.signal import savgol_filter as _sg
        self._sg            = _sg
        self._window_length = window_length
        self._polyorder     = polyorder
        self._buf: deque[float] = deque(maxlen=window_length)

    def process(self, value: float) -> float:
        self._buf.append(value)
        if len(self._buf) < self._window_length:
            return value
        smoothed = self._sg(list(self._buf), self._window_length,
                            self._polyorder, mode="nearest")
        return float(smoothed[-1])

    def reset(self) -> None:
        self._buf.clear()


# ── Медианный фильтр ─────────────────────────────────────────────────────────

@register_filter("median")
class MedianFilter(BaseFilter):
    """Медиана последних `window` отсчётов. Срезает импульсные выбросы."""
    def __init__(self, window: int = 15) -> None:
        self._buf: deque[float] = deque(maxlen=window)

    def process(self, value: float) -> float:
        self._buf.append(value)
        return float(np.median(self._buf))

    def reset(self) -> None:
        self._buf.clear()


# ── Добавляйте новые фильтры здесь ───────────────────────────────────────────

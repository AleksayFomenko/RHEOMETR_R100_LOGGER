"""
Модель данных испытания.

RheometerParams — вычисляемые параметры. Добавление нового параметра:
  1. Добавить поле в RheometerParams (Optional[float] = None)
  2. Вычислить его в DataModel._compute_tc_params() или _recompute_params()
  3. Добавить строку в params_panel.py :: PARAM_DEFS
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import math
import time

import numpy as np

from PyQt5.QtCore import QObject, pyqtSignal

# Таймаут подтверждения начального пика нагрузки (фаза 0, до обрезки).
PEAK_CONFIRM_TIMEOUT = 10   # секунды

# Точек после пика пропускать (артефакт спада нагрузочного маркера).
POST_PEAK_SKIP = 2

# Фаза 1: нет нового минимума ML_CONFIRM_TIMEOUT секунд → ML зафиксирован.
ML_CONFIRM_TIMEOUT = 30.0    # секунды

# Фаза 1: нет нового максимума MH_CONFIRM_TIMEOUT секунд → MH зафиксирован.
MH_CONFIRM_TIMEOUT = 30      # секунды


@dataclass
class RheometerParams:
    """Вычисляемые параметры реометра. None = ещё не определено."""
    ml: Optional[float] = None
    mh: Optional[float] = None
    ts1: Optional[float] = None
    ts2: Optional[float] = None
    tc10: Optional[float] = None
    tc50: Optional[float] = None
    tc90: Optional[float] = None
    cure_rate: Optional[float] = None

    # ── Добавляйте новые параметры здесь ─────────────────────────────────────
    # delta_torque: Optional[float] = None
    # ─────────────────────────────────────────────────────────────────────────


class DataModel(QObject):
    """
    Хранит сырые и отфильтрованные данные, вычисляет параметры.

    Фаза 0 (pre-trim): детекция начального пика нагрузки.
      После PEAK_CONFIRM_TIMEOUT секунд без нового максимума → peak_confirmed.
      MainWindow обрезает данные → переход в фазу 1.

    Фаза 1 (post-trim): ML → TS2 → MH последовательно.
      1. ML-трекер: фиксирует минимум, ML_CONFIRM_TIMEOUT без нового мин → ML зафиксирован.
      2. TS2-трекер: после ML — ждёт первого пересечения ML+2 → _ts2_crossed=True.
      3. MH-трекер: только после _ts2_crossed — отслеживает максимум;
         MH_CONFIRM_TIMEOUT без нового макс → MH зафиксирован → tc-параметры.

    Порядок гарантирован: ts2 ≤ tc10 ≤ tc50 ≤ tc90, все после ML.
    """
    params_updated = pyqtSignal(object)  # RheometerParams
    peak_confirmed = pyqtSignal()        # → MainWindow обрезает график (фаза 0)
    mh_confirmed   = pyqtSignal()        # → MH зафиксирован, расчёт tc-параметров

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.times: List[float] = []
        self.raw_values: List[float] = []
        self.filtered_values: List[float] = []
        self.params = RheometerParams()
        self._start_time: Optional[float] = None

        self.peak_index: int = 0
        self._detect_peaks: bool = True  # False после trim и при импорте CSV
        self._reset_peak_state()

        # Фаза 1: ML → TS2 → MH
        self._curve_started:      bool           = False
        self._ml_confirmed:       bool           = False
        self._ml_candidate_value: float           = math.inf
        self._ml_last_update_t:   float           = 0.0
        self._ts2_crossed:        bool           = False  # кривая пересекла ML+2
        self._mh_confirmed:       bool           = False
        self._mh_confirmed_value: Optional[float] = None
        self._mh_candidate_value: float           = -math.inf
        self._mh_last_update_t:   float           = 0.0

    # ── Запись данных ─────────────────────────────────────────────────────────

    def add_point(self, raw: float, filtered: float) -> float:
        """Добавляет точку, возвращает прошедшее время в секундах."""
        now = time.monotonic()
        if self._start_time is None:
            self._start_time = now
        elapsed = now - self._start_time

        self.times.append(elapsed)
        self.raw_values.append(raw)
        self.filtered_values.append(filtered)

        if self._detect_peaks:
            self._detect_peak(len(self.raw_values) - 1, raw, now)

        self._recompute_params()
        return self.times[-1]

    def trim_before_peak(self, skip: int = 0) -> None:
        """
        Удаляет всё до пика включительно, а также `skip` точек сразу после пика.
        Первая оставшаяся точка получает t=0. Переключает модель в фазу 1.
        """
        idx   = self.peak_index
        start = idx + 1 + skip

        if start < len(self.times):
            t_start = self.times[start]
            self.times           = [t - t_start for t in self.times[start:]]
            self.raw_values      = self.raw_values[start:]
            self.filtered_values = self.filtered_values[start:]
            if self._start_time is not None:
                self._start_time += t_start
        else:
            self.times           = []
            self.raw_values      = []
            self.filtered_values = []
            self._start_time     = None

        # Переходим в фазу 1
        self._detect_peaks = False
        self.peak_index    = 0
        self._reset_peak_state()

        self._curve_started      = True
        self._ml_confirmed       = False
        self._ml_candidate_value = math.inf
        self._ml_last_update_t   = 0.0
        self._ts2_crossed        = False
        self._mh_confirmed       = False
        self._mh_confirmed_value = None
        self._mh_candidate_value = -math.inf
        self._mh_last_update_t   = 0.0

        self._recompute_params()

    def load_from_arrays(
        self,
        times: List[float],
        raw_values: List[float],
        filtered_values: List[float],
    ) -> None:
        """
        Загружает данные из CSV. Воспроизводит логику ML → TS2 → MH.
        """
        self.times           = list(times)
        self.raw_values      = list(raw_values)
        self.filtered_values = list(filtered_values)
        self._start_time     = None
        self._detect_peaks   = False

        self._curve_started      = True
        self._ml_confirmed       = False
        self._ml_candidate_value = math.inf
        self._ml_last_update_t   = 0.0
        self._ts2_crossed        = False
        self._mh_confirmed       = False
        self._mh_confirmed_value = None
        self._mh_candidate_value = -math.inf
        self._mh_last_update_t   = 0.0

        for t, v in zip(self.times, self.filtered_values):
            # ML-трекер
            if v < self._ml_candidate_value:
                self._ml_candidate_value = v
                self._ml_last_update_t   = t

            # ML подтверждение
            if (not self._ml_confirmed
                    and self._ml_candidate_value < math.inf
                    and t - self._ml_last_update_t >= ML_CONFIRM_TIMEOUT):
                self._ml_confirmed = True

            # TS2-трекер: первое пересечение ML+2 после фиксации ML
            if self._ml_confirmed and not self._ts2_crossed:
                if v >= self._ml_candidate_value + 2.0:
                    self._ts2_crossed = True

            # MH-трекер: только после TS2
            if self._ts2_crossed and v > self._mh_candidate_value:
                self._mh_candidate_value = v
                self._mh_last_update_t   = t

        if (self._mh_last_update_t > 0 and self.times and
                self.times[-1] - self._mh_last_update_t >= MH_CONFIRM_TIMEOUT):
            self._mh_confirmed       = True
            self._mh_confirmed_value = self._mh_candidate_value

        self._recompute_params()

    def reset(self) -> None:
        self.times.clear()
        self.raw_values.clear()
        self.filtered_values.clear()
        self.params      = RheometerParams()
        self._start_time = None
        self.peak_index  = 0
        self._detect_peaks       = True
        self._curve_started      = False
        self._ml_confirmed       = False
        self._ml_candidate_value = math.inf
        self._ml_last_update_t   = 0.0
        self._ts2_crossed        = False
        self._mh_confirmed       = False
        self._mh_confirmed_value = None
        self._mh_candidate_value = -math.inf
        self._mh_last_update_t   = 0.0
        self._reset_peak_state()
        self.params_updated.emit(self.params)

    def finalize(self) -> None:
        """
        Принудительно фиксирует MH при остановке теста.
        Требует хотя бы пройденного TS2; иначе не делает ничего.
        """
        if not self._curve_started or self._mh_confirmed or not self.filtered_values:
            return
        if not self._ts2_crossed:
            return  # TS2 не пройден — MH не имеет смысла
        if self._mh_candidate_value > -math.inf:
            candidate = self._mh_candidate_value
        else:
            # TS2 пройден, но MH ещё не накопился — берём максимум после ML+2
            ts2_thr = self._ml_candidate_value + 2.0
            above   = [v for v in self.filtered_values if v >= ts2_thr]
            candidate = max(above) if above else None
        if candidate is None:
            return
        self._mh_confirmed       = True
        self._mh_confirmed_value = candidate
        self._recompute_params()

    def is_empty(self) -> bool:
        return len(self.times) == 0

    # ── Детекция начального пика (фаза 0) ────────────────────────────────────

    def _reset_peak_state(self) -> None:
        self._candidate_value: float = -math.inf
        self._candidate_time:  float = 0.0
        self._has_candidate:   bool  = False

    def _detect_peak(self, idx: int, value: float, now: float) -> None:
        if value > self._candidate_value:
            self._candidate_value = value
            self.peak_index       = idx
            self._candidate_time  = now
            self._has_candidate   = True
        elif self._has_candidate and (now - self._candidate_time) >= PEAK_CONFIRM_TIMEOUT:
            self._has_candidate  = False
            self._candidate_time = now
            self.peak_confirmed.emit()

    # ── Вычисление параметров ─────────────────────────────────────────────────

    def _recompute_params(self) -> None:
        vals  = self.filtered_values
        times = self.times
        if not vals:
            return

        p    = RheometerParams()
        p.ml = round(float(np.percentile(vals, 5)), 3)

        just_confirmed = False

        if not self._curve_started:
            p.mh = round(max(vals), 3)
            self._compute_tc_params(p, vals, times)
        else:
            current_t   = times[-1]
            current_val = vals[-1]

            # Если зафиксированный MH превышен на 10%+ — сбрасываем и ловим снова
            if (self._mh_confirmed
                    and self._mh_confirmed_value is not None
                    and current_val > self._mh_confirmed_value * 1.10):
                self._mh_confirmed       = False
                self._mh_confirmed_value = None
                self._mh_candidate_value = current_val
                self._mh_last_update_t   = current_t

            # ML-трекер
            if current_val < self._ml_candidate_value:
                self._ml_candidate_value = current_val
                self._ml_last_update_t   = current_t

            just_ml_confirmed = False
            if (not self._ml_confirmed
                    and self._ml_candidate_value < math.inf
                    and current_t - self._ml_last_update_t >= ML_CONFIRM_TIMEOUT):
                self._ml_confirmed  = True
                just_ml_confirmed   = True

            # TS2-трекер: после ML — первое пересечение ML+2 открывает MH
            if self._ml_confirmed and not self._ts2_crossed:
                ts2_thr = self._ml_candidate_value + 2.0
                if just_ml_confirmed:
                    # Ищем в истории с момента точки ML
                    for ht, hv in zip(self.times, self.filtered_values):
                        if ht >= self._ml_last_update_t and hv >= ts2_thr:
                            self._ts2_crossed = True
                            break
                elif current_val >= self._ml_candidate_value + 2.0:
                    self._ts2_crossed = True

            # MH-трекер: только после пересечения TS2
            if self._ts2_crossed and not self._mh_confirmed:
                if just_ml_confirmed:
                    # Бэкфилл: максимум начиная с момента первого пересечения ML+2
                    ts2_thr   = self._ml_candidate_value + 2.0
                    past_ts2  = False
                    for ht, hv in zip(self.times, self.filtered_values):
                        if ht < self._ml_last_update_t:
                            continue
                        if not past_ts2:
                            if hv >= ts2_thr:
                                past_ts2 = True
                            else:
                                continue
                        if hv > self._mh_candidate_value:
                            self._mh_candidate_value = hv
                            self._mh_last_update_t   = ht
                else:
                    if current_val > self._mh_candidate_value:
                        self._mh_candidate_value = current_val
                        self._mh_last_update_t   = current_t

                if self._mh_candidate_value > -math.inf:
                    p.mh = round(self._mh_candidate_value, 3)

                    if (self._mh_last_update_t > 0 and
                            current_t - self._mh_last_update_t >= MH_CONFIRM_TIMEOUT):
                        self._mh_confirmed       = True
                        self._mh_confirmed_value = self._mh_candidate_value
                        just_confirmed           = True

            if self._mh_confirmed:
                p.mh = round(self._mh_confirmed_value, 3)
                self._compute_tc_params(p, vals, times)

        self.params = p
        self.params_updated.emit(self.params)
        if just_confirmed:
            self.mh_confirmed.emit()

    def _compute_tc_params(
        self,
        p: RheometerParams,
        vals: List[float],
        times: List[float],
    ) -> None:
        """Вычисляет ts2, tc10, tc50, tc90, cure_rate. Требует p.ml и p.mh."""
        if p.mh is None or p.ml is None:
            return
        cure_range = p.mh - p.ml

        ml_idx = min(range(len(vals)), key=lambda i: vals[i])

        def first_crossing(start: int, threshold: float) -> Optional[int]:
            return next((i for i in range(start, len(vals)) if vals[i] >= threshold), None)

        ts1_idx = first_crossing(ml_idx, p.ml + 1.0)
        p.ts1   = round(times[ts1_idx] / 60, 2) if ts1_idx is not None else None

        ts2_idx = first_crossing(ml_idx, p.ml + 2.0)
        p.ts2   = round(times[ts2_idx] / 60, 2) if ts2_idx is not None else None

        # TC10/TC50/TC90 ищутся после TS2 → гарантируем ts2 ≤ tc10 ≤ tc50 ≤ tc90
        if cure_range > 0 and ts2_idx is not None:
            tc10_idx = first_crossing(ts2_idx, p.ml + 0.10 * cure_range)
            tc50_idx = first_crossing(ts2_idx, p.ml + 0.50 * cure_range)
            tc90_idx = first_crossing(ts2_idx, p.ml + 0.90 * cure_range)
            p.tc10 = round(times[tc10_idx] / 60, 2) if tc10_idx is not None else None
            p.tc50 = round(times[tc50_idx] / 60, 2) if tc50_idx is not None else None
            p.tc90 = round(times[tc90_idx] / 60, 2) if tc90_idx is not None else None
            if p.ts2 is not None and p.tc90 is not None:
                dt_sec = (p.tc90 - p.ts2) * 60  # мин → сек
                p.cure_rate = round(cure_range / dt_sec, 4) if dt_sec > 0 else None

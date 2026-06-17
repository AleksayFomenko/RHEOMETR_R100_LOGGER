"""
Виджет графика реального времени на базе pyqtgraph.

Для добавления нового ряда данных:
  1. Создайте PlotDataItem в _build_curves() с нужным pen и именем
  2. Добавьте список данных (self._<name>: list[float] = [])
  3. Вызывайте .setData() в add_point() и load_data()
  4. Очищайте в clear_data()
"""

from __future__ import annotations
from typing import List

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QSizePolicy

_TICK_FONT   = QFont("Arial", 16)   # шрифт делений осей
_LABEL_SIZE  = "16pt"               # шрифт подписей осей (Время / Момент)
_TITLE_SIZE  = "20pt"               # шрифт заголовка графика

# Тема: белый фон, чёрные оси
pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")

_DEBUG_ALL_CURVES = False  # True → сырой + выпрямл. + фильтр.; False → только фильтр.


class GraphWidget(pg.PlotWidget):
    """Основной виджет графика."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #self.setMaximumWidth(650)
        self._setup_axes()
        self._build_curves()

        # Буферы данных
        self._times:     List[float] = []
        self._raw:       List[float] = []
        self._rectified: List[float] = []
        self._filtered:  List[float] = []

        self._fixed_duration_min: float = 0.0  # 0 = авторазмер

    # ── Настройка внешнего вида ───────────────────────────────────────────────

    def _setup_axes(self) -> None:
        self.setTitle("Реометрическая кривая", color="k", size=_TITLE_SIZE)
        self.setLabel("left",   "Момент", units="дН·м")
        self.setLabel("bottom", "Время",  units="мин")
        self.showGrid(x=True, y=True, alpha=0.25)
        label_font = QFont("Arial", int(_LABEL_SIZE.replace("pt", "")))
        for axis in ("left", "bottom"):
            ax = self.getAxis(axis)
            ax.setTickFont(_TICK_FONT)
            ax.label.setFont(label_font)
        self.setLimits(xMin=0)
        pi = self.getPlotItem()
        if _DEBUG_ALL_CURVES:
            pi.addLegend(offset=(10, 10))
        # Кнопка "A" возвращает к нашему диапазону, а не делает autoRange по сигналу
        try:
            pi.autoBtn.clicked.disconnect(pi.autoBtnClicked)
        except Exception:
            pass
        pi.autoBtn.clicked.connect(self._on_auto_btn)

    def _build_curves(self) -> None:
        # ── Добавляйте новые кривые здесь ────────────────────────────────────
        if _DEBUG_ALL_CURVES:
            self._curve_raw = self.plot(
                pen=pg.mkPen(color=(200, 200, 200), width=1),
                name="Сырой сигнал",
            )
            self._curve_rectified = self.plot(
                pen=pg.mkPen(color=(220, 130, 0), width=1),
                name="Выпрямл. (EMA)",
            )
        else:
            self._curve_raw       = self.plot()
            self._curve_rectified = self.plot()
        self._curve_filtered = self.plot(
            pen=pg.mkPen(color=(30, 100, 210), width=6),
            name="Фильтр. сигнал",
        )
        # ─────────────────────────────────────────────────────────────────────

    # ── API ───────────────────────────────────────────────────────────────────

    def add_point(self, time_s: float, raw: float, rectified: float, filtered: float) -> None:
        """Добавляет одну точку и перерисовывает кривые. time_s — секунды."""
        self._times.append(time_s / 60.0)
        self._raw.append(raw)
        self._rectified.append(rectified)
        self._filtered.append(filtered)
        if _DEBUG_ALL_CURVES:
            self._curve_raw.setData(self._times, self._raw)
            self._curve_rectified.setData(self._times, self._rectified)
        self._curve_filtered.setData(self._times, self._filtered)

    def load_data(
        self,
        times: List[float],
        raw: List[float],
        rectified: List[float],
        filtered: List[float],
    ) -> None:
        """Загружает массив данных целиком. times — секунды, на граф идут минуты."""
        self._times     = [t / 60.0 for t in times]
        self._raw       = list(raw)
        self._rectified = list(rectified)
        self._filtered  = list(filtered)
        if _DEBUG_ALL_CURVES:
            self._curve_raw.setData(self._times, self._raw)
            self._curve_rectified.setData(self._times, self._rectified)
        self._curve_filtered.setData(self._times, self._filtered)
        self._apply_x_range()

    def clear_data(self) -> None:
        self._times.clear()
        self._raw.clear()
        self._rectified.clear()
        self._filtered.clear()
        self._curve_raw.setData([], [])
        self._curve_rectified.setData([], [])
        self._curve_filtered.setData([], [])

    def set_duration(self, minutes: float) -> None:
        """Задаёт фиксированный диапазон оси X. 0 = авторазмер."""
        self._fixed_duration_min = minutes
        self._apply_x_range()

    def _apply_x_range(self) -> None:
        if self._fixed_duration_min > 0:
            self.setXRange(0, self._fixed_duration_min, padding=0)
            self.enableAutoRange(axis=pg.ViewBox.YAxis)
        else:
            self.enableAutoRange()

    def _on_auto_btn(self) -> None:
        """Кнопка A: возврат к исходному масштабу (фиксированный или авто)."""
        self._apply_x_range()

    def set_x_label_minutes(self, use_minutes: bool) -> None:
        """Переключает подпись оси X между секундами и минутами."""
        units = "мин" if use_minutes else "с"
        self.setLabel("bottom", "Время", units=units)

    def grab_for_report(self, width: int = 650):
        """Рендерит график в фиксированный размер независимо от размера окна."""
        from PyQt5.QtGui import QPixmap
        from pyqtgraph.exporters import ImageExporter
        exporter = ImageExporter(self.plotItem)
        exporter.parameters()["width"] = width
        qimage = exporter.export(toBytes=True)
        return QPixmap.fromImage(qimage)

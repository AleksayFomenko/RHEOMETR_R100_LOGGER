"""
Панель вычисляемых параметров (правая колонка).

Для добавления нового параметра:
  1. Добавьте поле в RheometerParams (data_model.py)
  2. Вычислите его в DataModel._recompute_params()
  3. Добавьте кортеж в PARAM_DEFS ниже:
       ("имя_поля", "Метка", "ед.", "{:.3f}")
"""

from __future__ import annotations
from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.data_model import RheometerParams


# (поле в RheometerParams, Метка, единица, формат строки)
PARAM_DEFS: List[Tuple[str, str, str, str]] = [
    ("ml",         "ML  мин. момент",    "дН·м", "{:.3f}"),
    ("mh",         "MH  макс. момент",   "дН·м", "{:.3f}"),
    ("ts1",        "TS1",                "мин",  "{:.2f}"),
    ("ts2",        "TS2",                "мин",  "{:.2f}"),
    ("tc10",       "TC10",               "мин",  "{:.2f}"),
    ("tc50",       "TC50",               "мин",  "{:.2f}"),
    ("tc90",       "TC90",               "мин",  "{:.2f}"),
    ("cure_rate",  "Скорость вулк.",     "дН·м/сек", "{:.4f}"),
    # ── Добавляйте новые строки здесь ─────────────────────────────────────
    # ("delta_torque", "ΔM  (MH−ML)",    "дН·м", "{:.3f}"),
]

_NONE_TEXT   = "—"
_NONE_STYLE  = "color: #00FF00;"
_VALUE_STYLE = "font-weight: bold;"


class ParamsPanel(QWidget):
    """Панель параметров с прокруткой, вставляется в правую часть главного окна."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(260)
        #self.setMaximumWidth(260)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._value_labels: dict[str, QLabel] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Параметры")
        title.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setBold(True)
        f.setPointSize(10)
        title.setFont(f)
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setSpacing(2)
        layout.setContentsMargins(6, 4, 6, 4)

        for attr, label_text, unit, fmt in PARAM_DEFS:
            block = self._make_param_block(attr, label_text, unit)
            layout.addWidget(block)

        layout.addStretch()

    def _make_param_block(self, attr: str, label_text: str, unit: str) -> QWidget:
        block = QFrame()
        block.setFrameShape(QFrame.StyledPanel)
        block.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 4px; }")
        inner = QVBoxLayout(block)
        inner.setContentsMargins(6, 4, 6, 4)
        inner.setSpacing(0)

        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 16pt;")
        inner.addWidget(lbl)

        val = QLabel(_NONE_TEXT)
        val.setAlignment(Qt.AlignRight)
        val.setStyleSheet(_NONE_STYLE)
        f = QFont()
        f.setPointSize(13)
        val.setFont(f)
        inner.addWidget(val)

        if unit:
            unit_lbl = QLabel(unit)
            unit_lbl.setAlignment(Qt.AlignRight)
            unit_lbl.setStyleSheet("font-size: 16pt;")
            inner.addWidget(unit_lbl)

        self._value_labels[attr] = val
        return block

    # ── Обновление данных ─────────────────────────────────────────────────────

    def update_params(self, params: RheometerParams) -> None:
        """Слот: вызывается DataModel.params_updated."""
        for attr, _, unit, fmt in PARAM_DEFS:
            lbl = self._value_labels.get(attr)
            if lbl is None:
                continue
            value = getattr(params, attr, None)
            if value is None:
                lbl.setText(_NONE_TEXT)
                lbl.setStyleSheet(_NONE_STYLE)
            else:
                lbl.setText(fmt.format(value))
                lbl.setStyleSheet(_VALUE_STYLE)

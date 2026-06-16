"""
Диалог настроек испытания.

Для добавления нового поля:
  1. Добавьте поле в TestConfig (settings.py)
  2. Создайте виджет здесь и добавьте в _build_form()
  3. Добавьте считывание в get_config() и заполнение в _populate()
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from app.core.settings import TestConfig

_MATERIAL_TYPES = [
    "",
    "Каучук НК",
    "Каучук СКС",
    "Каучук СКЭПТ",
    "Каучук СКД",
    "Каучук БК",
    "Каучук ХК",
    "Резиновая смесь",
    # ── Добавляйте новые типы материалов здесь ────────────────────────────
]


class TestSettingsDialog(QDialog):
    def __init__(self, config: TestConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки испытания")
        self.setMinimumWidth(360)
        self._build_ui()
        self._populate(config)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Идентификация образца ─────────────────────────────────────────
        id_group = QGroupBox("Идентификация образца")
        id_form  = QFormLayout(id_group)

        self._operator   = QLineEdit()
        self._sample_id  = QLineEdit()
        self._material   = QComboBox()
        self._material.addItems(_MATERIAL_TYPES)
        self._material.setEditable(True)

        id_form.addRow("Оператор:",    self._operator)
        id_form.addRow("ID образца:",  self._sample_id)
        id_form.addRow("Тип материала:", self._material)

        layout.addWidget(id_group)

        # ── Условия испытания ─────────────────────────────────────────────
        cond_group = QGroupBox("Условия испытания")
        cond_form  = QFormLayout(cond_group)

        self._temperature = QDoubleSpinBox()
        self._temperature.setRange(0.0, 300.0)
        self._temperature.setSingleStep(0.5)
        self._temperature.setSuffix(" °C")

        self._duration = QSpinBox()
        self._duration.setRange(0, 180)        # 0 = без ограничения, до 180 мин
        self._duration.setSingleStep(1)
        self._duration.setSuffix(" мин")
        self._duration.setSpecialValueText("Без ограничения")

        cond_form.addRow("Температура:",       self._temperature)
        cond_form.addRow("Длит. испытания:",   self._duration)

        # ── Добавляйте новые условия испытания здесь ──────────────────────
        # self._pressure = QDoubleSpinBox(); ...
        # cond_form.addRow("Давление:", self._pressure)
        # ─────────────────────────────────────────────────────────────────

        layout.addWidget(cond_group)

        # ── Примечания ────────────────────────────────────────────────────
        notes_group = QGroupBox("Примечания")
        notes_layout = QVBoxLayout(notes_group)
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(80)
        notes_layout.addWidget(self._notes)
        layout.addWidget(notes_group)

        # ── Кнопки ───────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, cfg: TestConfig) -> None:
        self._operator.setText(cfg.operator)
        self._sample_id.setText(cfg.sample_id)
        idx = self._material.findText(cfg.material_type)
        if idx >= 0:
            self._material.setCurrentIndex(idx)
        else:
            self._material.setCurrentText(cfg.material_type)
        self._temperature.setValue(cfg.temperature)
        self._duration.setValue(cfg.test_duration_min)
        self._notes.setPlainText(cfg.notes)

    def get_config(self) -> TestConfig:
        """Считывает значения из формы и возвращает TestConfig."""
        return TestConfig(
            operator        = self._operator.text().strip(),
            sample_id       = self._sample_id.text().strip(),
            material_type   = self._material.currentText().strip(),
            temperature     = self._temperature.value(),
            test_duration_min = self._duration.value(),
            notes           = self._notes.toPlainText().strip(),
        )

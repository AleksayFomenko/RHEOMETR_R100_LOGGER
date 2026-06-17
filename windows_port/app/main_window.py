"""
Главное окно приложения.

Компоновка:
  ┌─────────────────────────────────────────────────────┐
  │  [Пуск] [Сброс] | [Имп.CSV] [Имп.отч.] [Эксп.CSV]  │  ← QToolBar
  │  [Отчёт] | [Настройки испытания] [Настройки связи]  │
  ├──────────────────────────────────┬──────────────────┤
  │                                  │  Параметры        │
  │        GraphWidget               │  ML  —            │
  │     (кривая вулканизации)        │  MH  —            │
  │                                  │  TS2 —            │
  │                                  │  ...              │
  ├──────────────────────────────────┴──────────────────┤
  │  ● Статус                              ● Связь       │  ← QStatusBar
  └─────────────────────────────────────────────────────┘
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QWidget,
)

from app.core.data_model import DataModel, POST_PEAK_SKIP
from app.core.export import export_csv, export_pdf, import_csv
from app.core.settings import CommConfig, SettingsManager, TestConfig
from app.ui.dialogs.comm_settings_dialog import CommSettingsDialog
from app.ui.dialogs.test_settings_dialog import TestSettingsDialog
from app.ui.graph_widget import GraphWidget
from app.ui.params_panel import ParamsPanel
from app.workers.filter import BaseFilter, ChainFilter, MedianFilter, OnlineRectifierFilter, RollingMaxFilter, SavitzkyGolayFilter
from app.workers.modbus_worker import ModbusWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        # ── Состояние ─────────────────────────────────────────────────────
        self._settings   = SettingsManager()
        self._comm_cfg   = self._settings.load_comm()
        self._test_cfg   = self._settings.load_test()
        self._data_model = DataModel(self)
        self._rectifier = OnlineRectifierFilter(alpha=0.1)     # сырой → выпрямитель (кривая 2)
        self._filter: BaseFilter = ChainFilter(
            OnlineRectifierFilter(alpha=0.1),                   # EMA-центр + |отражение|
            RollingMaxFilter(window=30),                         # огибающая по максимумам
            MedianFilter(window=200),                             # срезает импульсные выбросы
            SavitzkyGolayFilter(window_length=150, polyorder=3),  # сглаживание СГ
        )
        self._worker: Optional[ModbusWorker] = None
        self._time_display_offset: float = 0.0
        self._peak_just_confirmed: bool = False  # защита от двойного add_point в момент обрезки
        self._skip_after_peak: int = 0           # сколько точек после пика ещё не рисовать

        # ── UI ────────────────────────────────────────────────────────────
        self._build_ui()
        self._connect_signals()
        self.setWindowTitle("Реометр R-100")
        self.resize(1280, 720)

    # ─────────────────────────────────────────────────────────────────────────
    # Построение интерфейса
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

    def _build_toolbar(self) -> None:
        tb = self.addToolBar("Управление")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # ── Управление испытанием ─────────────────────────────────────────
        self._act_start = QAction("▶  Пуск", self)
        self._act_start.setCheckable(True)
        self._act_start.setShortcut("F5")
        self._act_start.setToolTip("Начать/остановить опрос (F5)")
        tb.addAction(self._act_start)

        self._act_reset = QAction("✕  Сброс", self)
        self._act_reset.setShortcut("F6")
        self._act_reset.setToolTip("Очистить данные (F6)")
        tb.addAction(self._act_reset)

        tb.addSeparator()

        # ── Импорт ────────────────────────────────────────────────────────
        self._act_import_csv = QAction("↓ CSV", self)
        self._act_import_csv.setToolTip("Импорт данных из CSV-файла")
        tb.addAction(self._act_import_csv)

        tb.addSeparator()

        # ── Экспорт ───────────────────────────────────────────────────────
        self._act_export_csv = QAction("↑ CSV", self)
        self._act_export_pdf = QAction("↑ PDF", self)
        self._act_export_csv.setToolTip("Сохранить данные в CSV")
        self._act_export_pdf.setToolTip("Сохранить PDF-отчёт")
        tb.addAction(self._act_export_csv)
        tb.addAction(self._act_export_pdf)

        tb.addSeparator()

        # ── Настройки ─────────────────────────────────────────────────────
        self._act_test_settings = QAction("⚙  Испытание", self)
        self._act_comm_settings = QAction("⚙  Связь",     self)
        self._act_test_settings.setToolTip("Настройки испытания: оператор, материал, длительность")
        self._act_comm_settings.setToolTip("Настройки Modbus RTU: порт, адрес, регистр")
        tb.addAction(self._act_test_settings)
        tb.addAction(self._act_comm_settings)

        # ── Добавляйте новые кнопки тулбара здесь ────────────────────────

    def _build_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── График (основная область) ─────────────────────────────────────
        self._graph = GraphWidget()
        layout.addWidget(self._graph, stretch=4)

        # ── Панель параметров (правая колонка) ────────────────────────────
        self._params_panel = ParamsPanel()
        layout.addWidget(self._params_panel, stretch=0)

    def _build_statusbar(self) -> None:
        self._status_label = QLabel("Готов")
        self.statusBar().addWidget(self._status_label)

        self._conn_dot = QLabel("●")
        self._conn_dot.setStyleSheet("color: #aaa;")
        self._conn_dot.setToolTip("Состояние соединения")
        self.statusBar().addPermanentWidget(self._conn_dot)

    # ─────────────────────────────────────────────────────────────────────────
    # Сигналы
    # ─────────────────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._act_start.toggled.connect(self._on_start_toggled)
        self._act_reset.triggered.connect(self._on_reset)

        self._act_import_csv.triggered.connect(self._on_import_csv)
        self._act_export_csv.triggered.connect(self._on_export_csv)
        self._act_export_pdf.triggered.connect(self._on_export_pdf)

        self._act_test_settings.triggered.connect(self._on_test_settings)
        self._act_comm_settings.triggered.connect(self._on_comm_settings)

        # DataModel → ParamsPanel: вычисленные параметры
        self._data_model.params_updated.connect(self._params_panel.update_params)
        # DataModel → MainWindow: начальный пик зафиксирован (фаза 0)
        self._data_model.peak_confirmed.connect(self._on_peak_confirmed)
        # DataModel → MainWindow: MH зафиксирован (фаза 1)
        self._data_model.mh_confirmed.connect(self._on_mh_confirmed)

    # ─────────────────────────────────────────────────────────────────────────
    # Управление испытанием
    # ─────────────────────────────────────────────────────────────────────────

    def _on_start_toggled(self, checked: bool) -> None:
        if checked:
            self._start_acquisition()
        else:
            self._stop_acquisition()

    def _start_acquisition(self) -> None:
        self._act_start.setText("■  Стоп")
        self._data_model.reset()
        self._graph.clear_data()
        self._filter.reset()
        self._rectifier.reset()
        self._time_display_offset = 0.0
        self._peak_just_confirmed = False
        self._skip_after_peak = 0

        self._graph.set_duration(self._test_cfg.test_duration_min)

        self._worker = ModbusWorker(self._comm_cfg, self)
        self._worker.data_point.connect(self._on_raw_data)
        self._worker.connection_status.connect(self._on_conn_status)
        self._worker.error_occurred.connect(self._on_modbus_error)
        self._worker.start()
        self._status_label.setText("Идёт испытание…")

    def _stop_acquisition(self) -> None:
        self._act_start.setText("▶  Пуск")
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
            self._worker.deleteLater()
            self._worker = None
        self._conn_dot.setStyleSheet("color: #aaa;")
        self._data_model.finalize()
        self._status_label.setText("Остановлено")

    def _on_reset(self) -> None:
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Сброс", "Сначала остановите испытание.")
            return
        self._data_model.reset()
        self._graph.clear_data()
        self._graph.set_duration(0)
        self._filter.reset()
        self._rectifier.reset()
        self._time_display_offset = 0.0
        self._peak_just_confirmed = False
        self._skip_after_peak = 0
        self._status_label.setText("Готов")

    # ─────────────────────────────────────────────────────────────────────────
    # Получение данных от воркера
    # ─────────────────────────────────────────────────────────────────────────

    def _on_raw_data(self, raw: float) -> None:
        # Точки сразу после пика пропускаем полностью: нет фильтрации, нет DataModel, нет CSV
        if self._skip_after_peak > 0:
            self._skip_after_peak -= 1
            return

        rectified = self._rectifier.process(raw)
        filtered  = self._filter.process(raw)
        elapsed   = self._data_model.add_point(raw, filtered)

        # _on_peak_confirmed вызывается синхронно внутри add_point и уже обновил
        # граф через load_data — добавлять точку снова не нужно
        if self._peak_just_confirmed:
            self._peak_just_confirmed = False
            return

        display_t = elapsed - self._time_display_offset
        self._graph.add_point(display_t, raw, rectified, filtered)

        limit = self._test_cfg.test_duration_min * 60
        if limit > 0 and elapsed >= limit:
            self._act_start.setChecked(False)
            self._status_label.setText("Испытание завершено")

    def _on_peak_confirmed(self) -> None:
        self._peak_just_confirmed = True
        dm = self._data_model

        # Мягкий сброс: буферы RollingMax/Exp очищаются, нулевой уровень NullCenter сохраняется
        self._filter.soft_reset()
        self._rectifier.soft_reset()

        # Сколько пост-пиковых точек уже в буфере (без пика)
        post_peak = len(dm.raw_values) - 1 - dm.peak_index
        self._skip_after_peak = max(0, POST_PEAK_SKIP - post_peak)

        # Удаляем всё до пика включительно + первые POST_PEAK_SKIP точек после него
        dm.trim_before_peak(skip=POST_PEAK_SKIP)

        # Фильтр видит только те сырые значения, которые есть на графике — с 284
        rectified_values = [self._rectifier.process(v) for v in dm.raw_values]
        for i in range(len(dm.raw_values)):
            dm.filtered_values[i] = self._filter.process(dm.raw_values[i])

        self._time_display_offset = 0.0
        self._graph.load_data(dm.times, dm.raw_values, rectified_values, dm.filtered_values)
        self._status_label.setText("Калибровка завершена — отсчёт вулканизации")

    def _on_mh_confirmed(self) -> None:
        self._status_label.setText("MH зафиксирован — расчёт параметров завершён")

    def _on_conn_status(self, connected: bool, message: str) -> None:
        color = "#2d9e2d" if connected else "#cc2222"
        self._conn_dot.setStyleSheet(f"color: {color};")
        self._status_label.setText(message)

    def _on_modbus_error(self, message: str) -> None:
        self._status_label.setText(f"Ошибка: {message}")

    # ─────────────────────────────────────────────────────────────────────────
    # Импорт
    # ─────────────────────────────────────────────────────────────────────────

    def _on_import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть CSV", "",
            "CSV файлы (*.csv);;Все файлы (*)",
        )
        if not path:
            return
        try:
            times, raw, _ = import_csv(path)
            if not times:
                QMessageBox.warning(self, "Импорт", "Файл не содержит данных.")
                return
            self._filter.reset()
            self._rectifier.reset()
            filt = [self._filter.process(v) for v in raw]
            rect = [self._rectifier.process(v) for v in raw]
            self._data_model.load_from_arrays(times, raw, filt)
            self._graph.set_duration(0)
            self._graph.load_data(times, raw, rect, filt)
            self._status_label.setText(f"Загружено {len(times)} точек: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка импорта", str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    # Экспорт
    # ─────────────────────────────────────────────────────────────────────────

    def _on_export_csv(self) -> None:
        if self._data_model.is_empty():
            QMessageBox.information(self, "Экспорт", "Нет данных для сохранения.")
            return
        default = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить CSV", default, "CSV файлы (*.csv)",
        )
        if not path:
            return
        try:
            export_csv(
                path,
                self._data_model.times,
                self._data_model.raw_values,
                self._data_model.filtered_values,
                self._test_cfg,
            )
            self._status_label.setText(f"Сохранено: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))

    def _on_export_pdf(self) -> None:
        if self._data_model.is_empty():
            QMessageBox.information(self, "PDF-отчёт", "Нет данных.")
            return
        default = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить PDF-отчёт", default, "PDF файлы (*.pdf)",
        )
        if not path:
            return
        try:
            export_pdf(path, self._graph.grab_for_report(), self._data_model.params, self._test_cfg)
            self._status_label.setText(f"PDF сохранён: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка экспорта PDF", str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    # Диалоги настроек
    # ─────────────────────────────────────────────────────────────────────────

    def _on_test_settings(self) -> None:
        dlg = TestSettingsDialog(self._test_cfg, self)
        if dlg.exec_():
            self._test_cfg = dlg.get_config()
            self._settings.save_test(self._test_cfg)

    def _on_comm_settings(self) -> None:
        dlg = CommSettingsDialog(self._comm_cfg, self)
        if dlg.exec_():
            self._comm_cfg = dlg.get_config()
            self._settings.save_comm(self._comm_cfg)

    # ─────────────────────────────────────────────────────────────────────────
    # Утилиты
    # ─────────────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._stop_acquisition()
        event.accept()

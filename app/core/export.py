"""
Импорт и экспорт данных.

Поддерживаемые форматы CSV:
  - Наш экспорт:   "Время (с)"; "Сырой"; "Фильтр."
  - Исходный формат прибора:  Minutes, Value   (импорт read-only)

Для добавления нового формата — добавьте ветку в import_csv().
"""

from __future__ import annotations
import csv
import os
import tempfile
from datetime import datetime
from typing import List, Optional, Tuple

from .data_model import POST_PEAK_SKIP, RheometerParams
from .settings import TestConfig


# ── Экспорт CSV ───────────────────────────────────────────────────────────────

def export_csv(
    filepath: str,
    times: List[float],
    raw_values: List[float],
    filtered_values: List[float],
    test_config: Optional[TestConfig] = None,
) -> None:
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if test_config:
            w.writerow(["# Оператор",   test_config.operator])
            w.writerow(["# Материал",   test_config.material_type])
            w.writerow(["# Образец",    test_config.sample_id])
            w.writerow(["# Темп-ра",    f"{test_config.temperature} °C"])
            w.writerow(["# Дата",       datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Время (с)", "Сырой", "Фильтр."])
        for t, r, fv in zip(times, raw_values, filtered_values):
            w.writerow([f"{t:.3f}", f"{r:.4f}", f"{fv:.4f}"])


# ── Импорт CSV ────────────────────────────────────────────────────────────────

def import_csv(
    filepath: str,
) -> Tuple[List[float], List[float], List[float]]:
    """
    Возвращает (times_s, raw, filtered).
    Поддерживает оба формата: наш экспорт и исходный Minutes/Value.
    """
    with open(filepath, "r", encoding="utf-8-sig") as f:
        sample = f.read(512)
        f.seek(0)
        is_native = "Minutes" in sample and "Value" in sample
        reader = csv.reader(f, delimiter="," if is_native else ";")

        times, raw, filt = [], [], []
        header_skipped = False

        for row in reader:
            if not row:
                continue
            first = row[0].strip()
            if first.startswith("#"):
                continue
            if not header_skipped:
                header_skipped = True
                continue
            try:
                if is_native:
                    # Minutes, Value → конвертируем минуты → секунды
                    t = float(first.replace(",", ".")) * 60.0
                    v = float(row[1].replace(",", "."))
                    times.append(t)
                    raw.append(v)
                    filt.append(v)
                else:
                    times.append(float(first.replace(",", ".")))
                    raw.append(float(row[1].replace(",", ".")))
                    filt.append(float(row[2].replace(",", ".")))
            except (ValueError, IndexError):
                continue

    # Нативный формат прибора: начальный маркер — глобальный максимум; обрезаем до него
    if is_native and raw:
        peak_idx = max(range(len(raw)), key=lambda i: raw[i])
        start = peak_idx + 1 + POST_PEAK_SKIP
        if start < len(times):
            t0 = times[start]
            times = [t - t0 for t in times[start:]]
            raw   = raw[start:]
            filt  = filt[start:]
        else:
            times, raw, filt = [], [], []

    return times, raw, filt


# ── Экспорт PDF-отчёта ───────────────────────────────────────────────────────

def export_pdf(
    filepath: str,
    graph_pixmap,           # QPixmap — захваченное изображение графика
    params: RheometerParams,
    test_config: Optional[TestConfig] = None,
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    def fmt(v: Optional[float], unit: str = "") -> str:
        if v is None:
            return "—"
        return f"{v:.3f}{(' ' + unit) if unit else ''}"

    now = datetime.now()
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M:%S")
    op   = test_config.operator      if test_config else "—"
    mat  = test_config.material_type if test_config else "—"
    sid  = test_config.sample_id     if test_config else "—"
    temp = f"{test_config.temperature} °C" if test_config else "—"

    pdfmetrics.registerFont(TTFont("Arial", "Arial.ttf"))

    styles = getSampleStyleSheet()
    styles["Title"].fontName  = "Arial"
    styles["Title"].fontSize  = 16
    styles["Title"].spaceAfter = 5


    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    elements = []

    # Заголовок
    elements.append(Paragraph("ООО «НИИЭМИ»", styles["Title"]))
    elements.append(Paragraph("Простокол испытаний ГОСТ Р 54547-2011", styles["Title"]))

    # Информационная таблица
    info_data = [
        ["Дата испытания", "Время испытания", "Материал / Образец", "Оператор"],
        [date_str, time_str, f"{mat} / {sid}", op],
    ]
    info_table = Table(info_data)
    info_table.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("GRID",          (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME",      (0, 0), (-1, -1), "Arial"),
        ("FONTSIZE",      (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # График — временный файл должен существовать до конца doc.build()
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png")
    os.close(tmp_fd)
    graph_pixmap.save(tmp_path, "PNG")
    elements.append(Image(tmp_path, width=16 * cm, height=12 * cm))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Технические характеристики испытания", styles["Title"]))

    # Таблица результатов
    param_rows = [
        ["Температура испытания", temp],
        ["ML — минимальный момент, дН·м",   fmt(params.ml)],
        ["MH — максимальный момент, дН·м",  fmt(params.mh)],
        ["TS1, мин",                        fmt(params.ts1)],
        ["TS2, мин",                        fmt(params.ts2)],
        ["TC10, мин",                       fmt(params.tc10)],
        ["TC50, мин",                       fmt(params.tc50)],
        ["TC90, мин",                       fmt(params.tc90)],
        ["Скорость вулканизации, дН·м/сек", fmt(params.cure_rate)],
    ]
    params_table = Table(param_rows, colWidths=[350, 100])
    params_table.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("GRID",          (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME",      (0, 0), (-1, -1), "Arial"),
        ("FONTSIZE",      (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(params_table)

    try:
        doc.build(elements)
    finally:
        os.remove(tmp_path)


# ── Экспорт отчёта (текст) ────────────────────────────────────────────────────

def export_report(
    filepath: str,
    params: RheometerParams,
    test_config: Optional[TestConfig] = None,
) -> None:
    def fmt(v: Optional[float], unit: str = "") -> str:
        if v is None:
            return "—"
        return f"{v:.3f}{(' ' + unit) if unit else ''}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=" * 56 + "\n")
        f.write("       РЕОМЕТР R-100 — ПРОТОКОЛ ИСПЫТАНИЯ\n")
        f.write("=" * 56 + "\n\n")
        f.write(f"Дата:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if test_config:
            f.write(f"Оператор:    {test_config.operator}\n")
            f.write(f"Материал:    {test_config.material_type}\n")
            f.write(f"Образец:     {test_config.sample_id}\n")
            f.write(f"Темп-ра:     {test_config.temperature} °C\n")
            if test_config.notes:
                f.write(f"Примечания:  {test_config.notes}\n")
        f.write("\n" + "-" * 40 + "\n")
        f.write("РЕЗУЛЬТАТЫ\n")
        f.write("-" * 40 + "\n")
        f.write(f"ML  (мин. момент):       {fmt(params.ml,        'дН·м')}\n")
        f.write(f"MH  (макс. момент):      {fmt(params.mh,        'дН·м')}\n")
        f.write(f"TS1:                     {fmt(params.ts1,       'мин')}\n")
        f.write(f"TS2:                     {fmt(params.ts2,       'мин')}\n")
        f.write(f"TC10:                    {fmt(params.tc10,      'мин')}\n")
        f.write(f"TC50:                    {fmt(params.tc50,      'мин')}\n")
        f.write(f"TC90:                    {fmt(params.tc90,      'мин')}\n")
        f.write(f"Скорость вулканизации:   {fmt(params.cure_rate, 'дН·м/сек')}\n")
        # ── Добавляйте строки новых параметров здесь ──────────────────────────
        f.write("\n" + "=" * 56 + "\n")

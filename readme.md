Структура:

main.py                          ← точка входа: python main.py
app/
├── main_window.py               ← главное окно, тулбар, компоновка
├── core/
│   ├── settings.py              ← CommConfig, TestConfig, SettingsManager
│   ├── data_model.py            ← DataModel, RheometerParams (вычисления)
│   └── export.py                ← import/export CSV и текстового отчёта
├── workers/
│   ├── filter.py                ← фильтры: rolling_max, moving_avg, exp
│   └── modbus_worker.py         ← QThread опроса Modbus RTU
└── ui/
    ├── graph_widget.py          ← pyqtgraph виджет реального времени
    ├── params_panel.py          ← правая панель параметров (ML, MH, TS2…)
    └── dialogs/
        ├── test_settings_dialog.py  ← оператор, материал, длит., темп-ра
        └── comm_settings_dialog.py  ← порт, baudrate, адрес, регистр


#запуск
.venv/bin/python main.py

#сборка
.venv\Scripts\pyinstaller rheometr.spec

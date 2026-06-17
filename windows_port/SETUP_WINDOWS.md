# Реометр R-100 — Установка на Windows

## Запуск из исходников

1. Установите **Python 3.10+** с [python.org](https://www.python.org/downloads/) (при установке поставьте галочку «Add Python to PATH»)
2. В папке `windows_port` откройте командную строку и выполните:
   ```
   pip install -r requirements_windows.txt
   python main.py
   ```

## Сборка в .exe (PyInstaller)

Запустите `build.bat` двойным кликом. Результат — папка `dist\Rheometr_R100\`.

## COM-порты

- Реальные приборы: на Windows порты называются `COM1`, `COM2` и т.д.
- Кнопка **«Обновить»** в настройках связи автоматически обнаруживает все доступные порты.
- Если прибор не отображается — установите драйвер USB-to-Serial (CP210x, CH340 и пр.).

## PDF-отчёты — шрифт Arial

PDF-отчёты используют шрифт **Arial**. На чистой Windows Arial уже есть (`C:\Windows\Fonts\arial.ttf`).
Если шрифт не найден, программа выдаст ошибку — скопируйте `Arial.ttf` в папку с `Rheometr_R100.exe`.

## Требования

| Компонент | Версия |
|-----------|--------|
| Python | 3.10+ |
| PyQt5 | 5.15.x |
| pyserial | 3.5+ |
| minimalmodbus | 2.1.x |
| numpy | 2.x |
| scipy | 1.x |
| reportlab | 4.x |
| pyqtgraph | 0.14.x |

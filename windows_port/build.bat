@echo off
chcp 65001 > nul
echo ============================================================
echo  Сборка Реометр R-100 для Windows
echo ============================================================

:: Проверяем наличие Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден. Установите Python 3.10+ из python.org
    pause
    exit /b 1
)

:: Устанавливаем зависимости
echo.
echo [1/3] Установка зависимостей...
python -m pip install --upgrade pip
python -m pip install -r requirements_windows.txt
if errorlevel 1 (
    echo ОШИБКА при установке зависимостей
    pause
    exit /b 1
)

:: Устанавливаем PyInstaller
python -m pip install pyinstaller
if errorlevel 1 (
    echo ОШИБКА при установке PyInstaller
    pause
    exit /b 1
)

:: Проверяем наличие Arial.ttf
echo.
echo [2/3] Проверка шрифта Arial...
if not exist "%WINDIR%\Fonts\arial.ttf" (
    if not exist "%WINDIR%\Fonts\Arial.ttf" (
        echo ПРЕДУПРЕЖДЕНИЕ: Arial.ttf не найден в %WINDIR%\Fonts\
        echo Скопируйте Arial.ttf в эту папку перед генерацией PDF-отчётов.
    )
)

:: Запускаем сборку
echo.
echo [3/3] Сборка исполняемого файла...
pyinstaller rheometr.spec --clean --noconfirm
if errorlevel 1 (
    echo ОШИБКА при сборке
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Готово! Папка с программой: dist\Rheometr_R100\
echo  Запустите: dist\Rheometr_R100\Rheometr_R100.exe
echo ============================================================
pause

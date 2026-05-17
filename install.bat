@echo off
echo ======================================
echo    Video Transcriber - Установка
echo ======================================
echo.

echo Проверяем Python...
python --version
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Установите Python 3.10+ с https://python.org
    pause
    exit /b 1
)

echo.
echo Проверяем FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ВНИМАНИЕ: FFmpeg не найден!
    echo Для полной функциональности установите FFmpeg:
    echo - Скачайте с https://ffmpeg.org/download.html
    echo - Или через winget: winget install ffmpeg
    echo - Или через chocolatey: choco install ffmpeg
    echo.
)

echo Обновляем pip...
python -m pip install --upgrade pip

echo.
echo Устанавливаем зависимости...
python -m pip install -r requirements.txt

echo.
echo Проверяем установку...
python transcriber.py --help >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Что-то пошло не так при установке
    pause
    exit /b 1
)

echo.
echo ======================================
echo    Установка завершена успешно! ✅
echo ======================================
echo.
echo Использование:
echo   Turbo-быстрая транскрипция:
echo     python transcriber.py -i "video.mp4"
echo.
echo   Медленная, но очень точная (если есть pisets):
echo     python transcriber_pisets.py -i "video.mp4"
echo.
echo   YouTube видео:
echo     python transcriber.py -i "https://youtube.com/watch?v=..."
echo.
echo Результаты сохраняются в папке transcripts/
echo ======================================
pause
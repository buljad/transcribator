#!/bin/bash

echo "======================================"
echo "    Video Transcriber - Установка"
echo "======================================"
echo

# Проверка Python
echo "Проверяем Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ ОШИБКА: Python3 не найден!"
    echo "Установите Python 3.10+ через ваш пакетный менеджер"
    exit 1
fi

python3 --version

# Проверка FFmpeg
echo
echo "Проверяем FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ВНИМАНИЕ: FFmpeg не найден!"
    echo "Для полной функциональности установите FFmpeg:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  CentOS/RHEL: sudo yum install ffmpeg"
    echo
fi

# Обновление pip
echo "Обновляем pip..."
python3 -m pip install --upgrade pip

# Установка зависимостей
echo
echo "Устанавливаем зависимости..."
python3 -m pip install -r requirements.txt

# Проверка
echo
echo "Проверяем установку..."
if python3 transcriber.py --help > /dev/null 2>&1; then
    echo
    echo "======================================"
    echo "    Установка завершена успешно! ✅"
    echo "======================================"
    echo
    echo "Использование:"
    echo "  Turbo-быстрая транскрипция:"
    echo "    python3 transcriber.py -i 'video.mp4'"
    echo
    echo "  Медленная, но очень точная (если есть pisets):"
    echo "    python3 transcriber_pisets.py -i 'video.mp4'"
    echo
    echo "  YouTube видео:"
    echo "    python3 transcriber.py -i 'https://youtube.com/watch?v=...'"
    echo
    echo "Результаты сохраняются в папке transcripts/"
    echo "======================================"
else
    echo "❌ ОШИБКА: Что-то пошло не так при установке"
    exit 1
fi
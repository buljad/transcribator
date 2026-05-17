#!/usr/bin/env python3
import argparse
import os
import tempfile
import subprocess
import sys
from pathlib import Path
import yt_dlp
import time
from tqdm import tqdm
import threading
import queue
import re

# Папка для сохранения всех транскрипций
TRANSCRIPTS_DIR = "transcripts"

def ensure_transcripts_dir():
    """Создает папку для транскрипций если её нет"""
    Path(TRANSCRIPTS_DIR).mkdir(exist_ok=True)
    return TRANSCRIPTS_DIR

def get_output_filename(input_path, is_url=False):
    """Генерирует имя выходного файла на основе входного"""
    if is_url:
        # Для URL используем безопасное имя
        import re
        safe_name = re.sub(r'[^\w\-_\.]', '_', input_path)
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        return f"{safe_name}.srt"
    else:
        # Для локальных файлов используем исходное имя
        input_file = Path(input_path)
        return f"{input_file.stem}.srt"

def get_audio_duration(file_path):
    """Получает длительность аудио файла"""
    try:
        import librosa
        duration = librosa.get_duration(path=file_path)
        return duration
    except:
        try:
            # Альтернативный способ через ffprobe
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 
                   'format=duration', '-of', 'csv=p=0', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
    return None

def monitor_pisets_output(process, progress_queue, duration):
    """Мониторит вывод pisets и отправляет прогресс"""
    try:
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                print(f"   {line}")  # Показываем вывод pisets
                
                # Пытаемся извлечь информацию о прогрессе из вывода
                if "Processing" in line or "Обработка" in line:
                    progress_queue.put("processing")
                elif "Downloading" in line or "Скачивание" in line:
                    progress_queue.put("downloading")
                elif "Loading" in line or "Загрузка" in line:
                    progress_queue.put("loading")
                    
    except Exception as e:
        print(f"Ошибка мониторинга: {e}")

def transcribe_with_pisets(input_path, output_path, language='ru'):
    """Транскрибирует файл используя pisets с прогресс-баром"""
    try:
        # Путь к скрипту pisets
        pisets_script = Path(__file__).parent / "pisets" / "speech_to_srt.py"
        
        if not pisets_script.exists():
            print(f"❌ Ошибка: файл {pisets_script} не найден!")
            print("Убедитесь, что папка 'pisets' находится в той же директории, что и этот скрипт")
            print("Или используйте основной скрипт transcriber.py (turbo-версия)")
            return False
        
        # Получаем длительность аудио для оценки времени
        duration = get_audio_duration(input_path)
        if duration:
            print(f"📊 Длительность аудио: {duration:.1f} секунд ({duration/60:.1f} минут)")
            estimated_time = duration * 3.0  # Pisets примерно в 3 раза медленнее реального времени на CPU
            print(f"⏱️  Примерное время обработки: {estimated_time/60:.1f} минут")
        else:
            print("📊 Не удалось определить длительность файла")
            estimated_time = None
        
        cmd = [
            sys.executable, str(pisets_script),
            "-i", input_path,
            "-o", output_path,
            "--lang", language
        ]
        
        print(f"\n🚀 Запускаем pisets транскрипцию...")
        print(f"Команда: {' '.join(cmd)}")
        print("=" * 50)
        
        # Создаем процесс с перехватом вывода
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True
        )
        
        # Очередь для передачи информации о прогрессе
        progress_queue = queue.Queue()
        
        # Запускаем мониторинг в отдельном потоке
        monitor_thread = threading.Thread(
            target=monitor_pisets_output, 
            args=(process, progress_queue, duration)
        )
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Основной прогресс-бар
        start_time = time.time()
        
        if estimated_time:
            # Прогресс-бар с примерным временем
            with tqdm(total=100, desc="🎯 Pisets", 
                     bar_format='{l_bar}{bar}| {percentage:3.0f}% [{elapsed}<{remaining}]') as pbar:
                
                while process.poll() is None:
                    elapsed = time.time() - start_time
                    if estimated_time > 0:
                        progress = min(95, (elapsed / estimated_time) * 100)
                        pbar.n = progress
                        pbar.refresh()
                    
                    # Проверяем сообщения из очереди
                    try:
                        message = progress_queue.get_nowait()
                        if message == "downloading":
                            pbar.set_description("📥 Скачивание моделей")
                        elif message == "loading":
                            pbar.set_description("🔄 Загрузка моделей")
                        elif message == "processing":
                            pbar.set_description("🎯 Обработка аудио")
                    except queue.Empty:
                        pass
                    
                    time.sleep(1)
                
                # Завершаем прогресс-бар
                pbar.n = 100
                pbar.set_description("✅ Завершено")
                pbar.refresh()
        else:
            # Простой спиннер без точного времени
            spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            spinner_idx = 0
            
            print("\n🎯 Выполняется транскрипция...")
            while process.poll() is None:
                elapsed = time.time() - start_time
                spinner = spinner_chars[spinner_idx % len(spinner_chars)]
                print(f"\r{spinner} Время выполнения: {elapsed:.0f}s", end="", flush=True)
                spinner_idx += 1
                time.sleep(0.1)
            
            print("\r✅ Завершено!                    ")
        
        # Ждем завершения мониторинга
        monitor_thread.join(timeout=1)
        
        # Получаем результат
        return_code = process.wait()
        elapsed_total = time.time() - start_time
        
        print("=" * 50)
        print(f"⏱️  Общее время выполнения: {elapsed_total/60:.1f} минут")
        
        if return_code == 0:
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✅ Транскрипция успешно сохранена: {output_path}")
                print(f"📄 Размер файла: {file_size} байт")
                return True
            else:
                print(f"❌ Файл результата не создан: {output_path}")
                return False
        else:
            print(f"❌ Процесс завершился с ошибкой (код: {return_code})")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка выполнения: {e}")
        return False

def download_video(url, output_dir):
    """Скачивает видео/аудио по ссылке с прогресс-баром"""
    try:
        def progress_hook(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and d['total_bytes']:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    print(f"\r⬇️  Скачано: {percent:.1f}%", end="", flush=True)
        
        ydl_opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'format': 'bestaudio/best',
            'restrictfilenames': True,
            'progress_hooks': [progress_hook],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о видео
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'downloaded_video')
            
            print(f"📺 Найдено видео: {title}")
            
            # Скачиваем с прогресс-баром
            ydl.download([url])
            print("\n✅ Скачивание завершено!")
            
            # Находим скачанный файл
            downloaded_files = list(Path(output_dir).glob(f"*{title}*"))
            if not downloaded_files:
                downloaded_files = list(Path(output_dir).iterdir())
            
            if downloaded_files:
                return str(downloaded_files[-1]), title
                    
        return None, None
    except Exception as e:
        print(f"\n❌ Ошибка скачивания: {e}")
        return None, None

def main():
    parser = argparse.ArgumentParser(description='🐌 Точная транскрипция видео/аудио (pisets - медленно, но очень качественно)')
    parser.add_argument('-i', '--input', required=True, 
                       help='Путь к файлу или URL (YouTube, и др.)')
    parser.add_argument('-lang', '--language', default='ru',
                       help='Язык транскрипции (ru/en)')
    
    args = parser.parse_args()
    
    # Создаем папку для транскрипций
    transcripts_dir = ensure_transcripts_dir()
    print(f"📁 Папка для транскрипций: {transcripts_dir}")
    print(f"🐌 Используем pisets (медленно, но очень точно)")
    
    # Проверяем, URL это или файл
    is_url = args.input.startswith(('http://', 'https://')) or 'youtube.com' in args.input or 'youtu.be' in args.input
    
    if is_url:
        print(f"🌐 Обнаружен URL: {args.input}")
        
        # Создаем временную папку для скачивания
        with tempfile.TemporaryDirectory() as temp_dir:
            downloaded_file, video_title = download_video(args.input, temp_dir)
            
            if downloaded_file:
                print(f"📁 Скачанный файл: {downloaded_file}")
                
                # Генерируем имя выходного файла на основе названия видео
                if video_title:
                    # Очищаем название от недопустимых символов
                    import re
                    safe_title = re.sub(r'[^\w\-_\.]', '_', video_title)
                    output_filename = f"{safe_title}.srt"
                else:
                    output_filename = get_output_filename(args.input, is_url=True)
                
                output_path = os.path.join(transcripts_dir, output_filename)
                transcribe_with_pisets(downloaded_file, output_path, args.language)
            else:
                print("❌ Не удалось скачать файл")
    else:
        print(f"📁 Транскрибирую локальный файл: {args.input}")
        
        if not os.path.exists(args.input):
            print(f"❌ Файл не найден: {args.input}")
            return
        
        # Генерируем имя выходного файла
        output_filename = get_output_filename(args.input, is_url=False)
        output_path = os.path.join(transcripts_dir, output_filename)
        
        transcribe_with_pisets(args.input, output_path, args.language)

if __name__ == "__main__":
    main()
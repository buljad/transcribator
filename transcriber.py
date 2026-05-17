#!/usr/bin/env python3
import argparse
import os
import tempfile
import sys
from pathlib import Path
import yt_dlp
import time
from tqdm import tqdm
from faster_whisper import WhisperModel

TRANSCRIPTS_DIR = "transcripts"

def ensure_transcripts_dir():
    Path(TRANSCRIPTS_DIR).mkdir(exist_ok=True)
    return TRANSCRIPTS_DIR

def get_output_filename(input_path, is_url=False):
    if is_url:
        import re
        safe_name = re.sub(r'[^\w\-_\.]', '_', input_path)[:50]
        return f"{safe_name}.srt"
    return f"{Path(input_path).stem}.srt"

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def transcribe_fast(input_path, output_path, language='ru', model_size='large-v3'):
    """Транскрибирует с помощью faster-whisper (стабильнее, чем transformers)"""
    
    # Маппинг названий моделей
    model_map = {
        'small': 'small',
        'medium': 'medium', 
        'large': 'large-v2',
        'large-v3': 'large-v3',
        'turbo': 'turbo',  # Новейшая турбо модель!
    }
    
    actual_model = model_map.get(model_size, 'large-v3')
    
    print(f"🤖 Загружаем модель Whisper '{actual_model}'")
    print("   (При первом запуске будет скачана из интернета)")
    
    start_load = time.time()
    
    # int8 квантизация - быстрее и меньше памяти
    model = WhisperModel(
        actual_model, 
        device="cpu", 
        compute_type="int8",
        cpu_threads=os.cpu_count(),  # Используем все ядра
    )
    
    load_time = time.time() - start_load
    print(f"✅ Модель загружена за {load_time:.1f}s")
    
    print(f"🎯 Начинаю транскрипцию на языке: {language}")
    print("=" * 50)
    
    start_time = time.time()
    
    # Транскрипция с VAD (фильтр тишины) - предотвращает зависания!
    segments, info = model.transcribe(
        input_path,
        language=language,
        beam_size=5,
        vad_filter=True,  # ⭐ Ключевое: пропускает тишину и шум
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.5,
        ),
        condition_on_previous_text=False,  # Меньше галлюцинаций
    )
    
    print(f"📊 Длительность: {info.duration:.1f}s, определенный язык: {info.language}")
    print(f"📝 Начинаю обработку сегментов...\n")
    
    # Записываем SRT с прогресс-баром
    segment_count = 0
    with open(output_path, 'w', encoding='utf-8') as srt_file:
        with tqdm(total=info.duration, desc="🚀 Транскрипция", unit='s',
                  bar_format='{l_bar}{bar}| {n:.0f}/{total:.0f}s [{elapsed}<{remaining}]') as pbar:
            
            for i, segment in enumerate(segments, start=1):
                # Пишем сегмент в SRT
                srt_file.write(f"{i}\n")
                srt_file.write(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n")
                srt_file.write(f"{segment.text.strip()}\n\n")
                srt_file.flush()  # Сразу пишем на диск
                
                # Обновляем прогресс на основе РЕАЛЬНОЙ позиции в аудио
                pbar.n = min(segment.end, info.duration)
                pbar.refresh()
                segment_count = i
            
            pbar.n = info.duration
            pbar.refresh()
    
    elapsed = time.time() - start_time
    xrt = elapsed / info.duration if info.duration > 0 else 0
    
    print("\n" + "=" * 50)
    print(f"⏱️  Время выполнения: {elapsed/60:.1f} минут")
    print(f"⚡ Скорость: xRT = {xrt:.2f}")
    print(f"📝 Создано сегментов: {segment_count}")
    print(f"✅ Сохранено: {output_path}")
    print(f"📄 Размер файла: {os.path.getsize(output_path)} байт")
    
    return True

def download_video(url, output_dir):
    def progress_hook(d):
        if d['status'] == 'downloading' and 'total_bytes' in d and d['total_bytes']:
            percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
            print(f"\r⬇️  Скачано: {percent:.1f}%", end="", flush=True)
    
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'bestaudio/best',
        'restrictfilenames': True,
        'progress_hooks': [progress_hook],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'downloaded_video')
        print(f"📺 Найдено видео: {title}")
        ydl.download([url])
        print("\n✅ Скачивание завершено!")
        
        downloaded_files = list(Path(output_dir).iterdir())
        if downloaded_files:
            return str(max(downloaded_files, key=os.path.getctime)), title
    return None, None

def main():
    parser = argparse.ArgumentParser(description='🚀 Быстрая транскрипция (faster-whisper)')
    parser.add_argument('-i', '--input', required=True, help='Путь к файлу или URL')
    parser.add_argument('-lang', '--language', default='ru', help='Язык (ru/en)')
    parser.add_argument('-m', '--model', default='large-v3',
                       choices=['small', 'medium', 'large', 'large-v3', 'turbo'],
                       help='Размер модели')
    
    args = parser.parse_args()
    
    transcripts_dir = ensure_transcripts_dir()
    print(f"📁 Папка для транскрипций: {transcripts_dir}")
    print(f"🚀 Используем faster-whisper")
    
    is_url = args.input.startswith(('http://', 'https://')) or 'youtu' in args.input
    
    if is_url:
        print(f"🌐 Обнаружен URL: {args.input}")
        with tempfile.TemporaryDirectory() as temp_dir:
            downloaded_file, video_title = download_video(args.input, temp_dir)
            if downloaded_file:
                import re
                safe_title = re.sub(r'[^\w\-_\.]', '_', video_title) if video_title else "video"
                output_path = os.path.join(transcripts_dir, f"{safe_title}.srt")
                transcribe_fast(downloaded_file, output_path, args.language, args.model)
    else:
        if not os.path.exists(args.input):
            print(f"❌ Файл не найден: {args.input}")
            return
        output_path = os.path.join(transcripts_dir, get_output_filename(args.input))
        transcribe_fast(args.input, output_path, args.language, args.model)

if __name__ == "__main__":
    main()
from setuptools import setup, find_packages

setup(
    name="video-transcriber",
    version="2.0.0",
    description="Turbo-быстрая транскрипция видео и аудио с помощью Distil-Whisper",
    packages=find_packages(),
    install_requires=[
        'torch>=2.0.0',
        'transformers>=4.36.0',
        'accelerate',
        'librosa>=0.10.0',
        'soundfile',
        'tqdm',
        'yt-dlp',
        'python-docx',
        'ffmpeg-python',
    ],
    entry_points={
        'console_scripts': [
            'transcriber=transcriber:main',
            'transcriber-pisets=transcriber_pisets:main',
        ],
    },
    python_requires='>=3.10',
    author="Ваше имя",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/video-transcriber",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
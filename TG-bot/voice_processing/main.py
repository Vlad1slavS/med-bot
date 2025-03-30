import soundfile as sf
import io
from pydub import AudioSegment
import wave
import json
from vosk import Model, KaldiRecognizer


def convert_ogg_to_wav(input_bytes: bytes, output_path: str):
    """Конвертирует OGG (bytes) в WAV с улучшенным качеством"""
    try:
        # Открываем аудио из памяти
        audio = AudioSegment.from_file(io.BytesIO(input_bytes), format="ogg")

        # Улучшаем качество:
        audio = audio.set_frame_rate(44100)  # Частота дискретизации 44.1 kHz (CD-качество)
        audio = audio.set_channels(2)  # стерео - моно 1
        audio = audio.set_sample_width(2)  # 16 бит
        audio = audio.low_pass_filter(3000)  # Уменьшаем высокие частоты (опционально)

        # Сохраняем в WAV с высоким качеством
        audio.export(output_path, format="wav", parameters=["-ar", "44100", "-ac", "1"])
        print(f"Конвертация успешна: {output_path}")
    except Exception as e:
        print(f"Ошибка конвертации: {e}")
    

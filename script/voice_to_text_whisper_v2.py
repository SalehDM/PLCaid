import os
import pyaudio
import wave
import time
import argparse
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import sys
import numpy as np

# --- Configurar la codificación de la salida de la consola al inicio ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass
except Exception as e:
    print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}")


# --- Configuracion ---
load_dotenv()
API_KEY = os.getenv("API_KEY")

try:
    if not API_KEY:
        raise ValueError("La variable de entorno OPENAI_API_KEY no esta configurada.")
    client = OpenAI(api_key=API_KEY)
except Exception as e:
    print(f"ERROR: Error al inicializar el cliente de OpenAI. Asegurese de que la variable de entorno OPENAI_API_KEY este configurada correctamente. Detalles: {e}")
    sys.exit(1)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "recorded_audio.wav"
TRANSCRIPTION_FILENAME = "order.txt"
SILENCE_THRESHOLD = 10 # <-- MUY REDUCIDO: Prácticamente cualquier sonido debería superar esto.

def get_input_device_index(audio_instance):
    info = audio_instance.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')
    
    print("\nINFO: Dispositivos de entrada de audio disponibles:")
    default_input_device_index = -1
    for i in range(0, num_devices):
        device_info = audio_instance.get_device_info_by_host_api_device_index(0, i)
        if device_info.get('maxInputChannels') > 0:
            print(f"  Dispositivo {i}: {device_info.get('name')}")
            if audio_instance.get_default_input_device_info()['index'] == i:
                print("    (Dispositivo de entrada predeterminado)")
                default_input_device_index = i
    
    if default_input_device_index == -1:
        print("ERROR: No se encontro ningun dispositivo de entrada predeterminado. Por favor, revisa la configuracion de audio de tu sistema.")
        sys.exit(1)
    
    print(f"INFO: Usando dispositivo de entrada predeterminado (indice: {default_input_device_index}).")
    return default_input_device_index

def calculate_rms(frames):
    if not frames:
        return 0
    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
    if audio_data.size == 0:
        return 0
    rms = np.sqrt(np.mean(audio_data**2))
    return rms

def transcribe_voice_input_whisper_direct_pyaudio(output_dir: str = "input_text", language: str = "es"):
    audio = pyaudio.PyAudio()
    
    input_device_index = get_input_device_index(audio)

    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK,
                        input_device_index=input_device_index)

    # Cebar el microfono antes de la grabacion real
    print("INFO: Cebando el microfono...")
    for _ in range(0, int(RATE / CHUNK * 0.5)): # Leer 0.5 segundos de audio para cebar
        stream.read(CHUNK)
    
    # --- NUEVO: Conteo regresivo para el usuario ---
    print("INFO: La grabacion comenzara en:")
    for i in range(3, 0, -1):
        print(f"INFO: ... {i} ...")
        sys.stdout.flush() # Forzar que el mensaje se muestre inmediatamente
        time.sleep(1)
    print("INFO: ¡HABLA AHORA!")
    sys.stdout.flush() # Forzar que el mensaje se muestre inmediatamente
    # Fin del conteo regresivo

    frames = []
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("INFO: Grabacion finalizada.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    rms_value = calculate_rms(frames)
    print(f"INFO: RMS del audio grabado: {rms_value}")

    if rms_value < SILENCE_THRESHOLD:
        transcribed_text = "No se detecto voz clara. Por favor, intente de nuevo."
        print("WARNING: Se detecto silencio o audio muy bajo. Saltando la llamada a la API de Whisper.")
    else:
        output_audio_path = os.path.join(output_dir, WAVE_OUTPUT_FILENAME)
        os.makedirs(output_dir, exist_ok=True)

        wf = wave.open(output_audio_path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"INFO: Audio guardado en: {output_audio_path}")

        print("INFO: Transcribiendo audio con OpenAI Whisper...")
        try:
            with open(output_audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                    language=language
                )
            transcribed_text = transcript.strip()
            print(f"INFO: Transcripcion: '{transcribed_text}'")

        except Exception as e:
            print(f"ERROR: Error al transcribir con OpenAI Whisper: {e}")
            transcribed_text = f"ERROR durante la transcripcion: {e}"

    output_text_path = os.path.join(output_dir, TRANSCRIPTION_FILENAME)
    with open(output_text_path, "w", encoding="utf-8") as f:
        f.write(transcribed_text)
    print(f"INFO: Transcripcion guardada en: {output_text_path}")
    return transcribed_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Graba audio y lo transcribe usando OpenAI Whisper.")
    parser.add_argument("--output_dir", type=str, default="input_text",
                        help="Directorio donde se guardara el archivo de audio y la transcripcion.")
    parser.add_argument("--duration", type=int, default=RECORD_SECONDS,
                        help=f"Duracion de la grabacion en segundos (por defecto: {RECORD_SECONDS}).")
    parser.add_argument("--lang", type=str, default="es",
                        help="Idioma de la transcripcion (ej. 'es' para espanol, 'en' para ingles).")
    
    args = parser.parse_args()

    RECORD_SECONDS = args.duration

    transcribed_text = transcribe_voice_input_whisper_direct_pyaudio(output_dir=args.output_dir, language=args.lang)
    
    if transcribed_text:
        print("\n--- Proceso de voz a texto finalizado exitosamente ---")
    else:
        print("\n--- Proceso de voz a texto finalizado con errores ---")

import os
import datetime
import argparse
from openai import OpenAI
import pyaudio
import wave
import io
# numpy ya no es necesario si no se usa directamente para manipulación de arrays de audio
# import numpy as np
import tempfile # Para crear archivos temporales

# Carga las variables de entorno desde el archivo .env
# Asegúrate de que tu archivo .env esté en la raíz del proyecto
# y contenga OPENAI_API_KEY="tu_clave_api_aqui"
from dotenv import load_dotenv
load_dotenv()

# Define el directorio por defecto para guardar las transcripciones
script_dir = os.path.dirname(os.path.abspath(__file__))
default_output_dir = os.path.join(script_dir, "..", "input_text")


def transcribe_voice_input_whisper_direct_pyaudio(output_dir=default_output_dir, language="es"):
    """
    Captura audio del micrófono directamente con PyAudio, lo transcribe a texto
    usando OpenAI Whisper API, guarda la transcripción en un único archivo .txt
    y elimina el archivo WAV temporal.

    Args:
        output_dir (str): Directorio donde se guardará el archivo de texto transcrito.
                        
        language (str): Idioma para la transcripción (ej. 'es' para español, 'en' para inglés).
                        Nota: Whisper usa códigos de idioma ISO-639-1 (ej. 'es', 'en').
    """
    # Asegura que el directorio de salida exista
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Directorio creado: {output_dir}")

    # Inicializa el cliente de OpenAI (la clave API se toma de OPENAI_API_KEY en el entorno)
    try:
        client = OpenAI()
    except Exception as e:
        print(f"❌ Error al inicializar el cliente de OpenAI. Asegúrate de que la variable de entorno OPENAI_API_KEY esté configurada correctamente. Detalles: {e}")
        return

    # Parámetros de grabación
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1 # Whisper prefiere audio mono
    RATE = 16000 # Frecuencia de muestreo (16 kHz es un buen balance para voz y Whisper)
    RECORD_SECONDS = 10 # Grabar por 10 segundos

    p = pyaudio.PyAudio()

    print("\n--- Prototipo de Entrada por Voz (Whisper API - PyAudio Directo) ---")
    print("Iniciando grabación... Di tu orden de voz.")

    # Abre el stream de audio para la grabación
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []

    # Lee datos del stream de audio durante el tiempo especificado
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        try:
            data = stream.read(CHUNK)
            frames.append(data)
        except IOError as e:
            # Manejo de error si el stream de audio se interrumpe
            print(f"⚠️ Advertencia: Error durante la lectura del stream de audio: {e}")
            break # Sale del bucle de grabación si hay un error

    print("Grabación finalizada. Procesando audio...")

    # Detiene y cierra el stream de audio
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Define la ruta del archivo WAV temporal que se enviará a Whisper
    temp_wav_path = None
    # Define la ruta del archivo de texto de salida único (siempre el mismo nombre)
    output_txt_filename = os.path.join(output_dir, "order.txt")

    try:
        # Crea un archivo WAV temporal en disco para asegurar la compatibilidad con Whisper API
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_wav_path = temp_file.name
            wf = wave.open(temp_wav_path, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames)) # Escribe todos los frames capturados
            wf.close()
        # print(f"🎶 Audio capturado temporalmente en: {temp_wav_path}") # Línea de depuración opcional

        # Abre el archivo WAV temporal en modo binario de lectura para pasárselo a Whisper
        with open(temp_wav_path, "rb") as audio_file_for_whisper:
            # Realiza la transcripción usando la API de OpenAI Whisper
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file_for_whisper, # Pasa el objeto archivo
                language=language            # Especifica el idioma para mejorar la precisión
            )
            text = transcription.text
            print(f"✅ Texto transcrito por Whisper: \"{text}\"")

        # Guarda la transcripción en el archivo .txt fijo (sobrescribe el contenido anterior)
        with open(output_txt_filename, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"💾 Transcripción guardada en: {output_txt_filename}")

    except Exception as e:
        print(f"❌ Ocurrió un error al transcribir con Whisper API: {e}")
    finally:
        # Asegúrate de eliminar el archivo WAV temporal si existe
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            # print(f"🗑️ Archivo WAV temporal eliminado: {temp_wav_path}") # Línea de depuración opcional


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prototipo de entrada de voz a texto usando OpenAI Whisper API para PLCaid.")
    parser.add_argument("--output_dir", type=str, default=default_output_dir,
        help="Directorio donde se guardarán las transcripciones de texto.")
    parser.add_argument("--lang", type=str, default="es",
                        help="Idioma para la transcripción (código ISO-639-1, ej. 'es', 'en').")

    args = parser.parse_args()

    transcribe_voice_input_whisper_direct_pyaudio(output_dir=args.output_dir, language=args.lang)
    print("\n--- Prototipo de Entrada por Voz (Whisper API) Finalizado ---")
import streamlit as st
import speech_recognition as sr
import sounddevice as sd
import wavio # Importar wavio para guardar archivos WAV
import subprocess
import os
import sys
import threading
import queue
import time

# --- Configurar la codificación de la salida de la consola al inicio ---
# Esto es crucial para asegurar que Streamlit y los subprocesos manejen UTF-8 correctamente.
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    # reconfigure no está disponible en todas las versions de Python o entornos
    pass
except Exception as e:
    st.error(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}")

# Rutas de archivos (ajustadas para la estructura del proyecto)
AUDIO_FILE = "input_audio/input.wav"
INPUT_TEXT_DIR = "input_text"
ORDER_FILE = os.path.join(INPUT_TEXT_DIR, "order.txt")
MAIN_SCRIPT = "main.py" # main.py está en la raíz del proyecto

# Asegurarse de que el directorio de audio exista
os.makedirs(os.path.dirname(AUDIO_FILE), exist_ok=True)
os.makedirs(INPUT_TEXT_DIR, exist_ok=True)

# Inicializar historial de órdenes en la sesión de Streamlit
if 'order_history' not in st.session_state:
    st.session_state.order_history = []

st.set_page_config(layout="wide", page_title="PLCaid - Asistente de Automatización")

st.title("🗣️ PLCaid - Asistente de Automatización por Voz")

# Contenedor para la salida de la consola en Streamlit
console_output_placeholder = st.empty()

# Cola para la comunicación entre el hilo de subproceso y el hilo principal de Streamlit
output_queue = queue.Queue()

def record_audio(filename, duration=5, samplerate=44100, channels=1):
    """
    Graba audio desde el micrófono predeterminado y lo guarda en un archivo WAV.
    """
    st.info(f"🎙️ Grabando audio... habla ahora ({duration} segundos).")
    try:
        # Grabar audio
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
        sd.wait() # Esperar a que la grabación termine
        
        # Guardar el archivo WAV usando wavio
        wavio.write(filename, recording, samplerate, sampwidth=2)
        st.success(f"✅ Grabación finalizada. Audio guardado en: {filename}")
        return True
    except Exception as e:
        st.error(f"❌ Error al grabar audio: {e}. Asegúrate de que un micrófono esté conectado y configurado.")
        return False

def transcribe_audio(audio_file):
    """
    Transcribe el audio de un archivo a texto usando Google Speech Recognition.
    """
    st.info("🗣️ Transcribiendo voz...")
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="es-ES")
            st.write(f"🗣️ Transcripción de voz: **{text}**")
            return text
    except sr.UnknownValueError:
        st.warning("⚠️ No se pudo entender el audio. Por favor, inténtalo de nuevo.")
        return None
    except sr.RequestError as e:
        st.error(f"❌ Error en el servicio de reconocimiento de voz; {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error al transcribir audio: {e}")
        return None

def run_main_script_in_thread(order_text, q):
    """
    Ejecuta el script main.py como un subproceso en un hilo separado
    y redirige su salida a una cola.
    """
    try:
        # Configurar el entorno para el subproceso, asegurando UTF-8
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1' # Para Python 3.7+

        # Usar Popen para capturar la salida en tiempo real
        process = subprocess.Popen(
            ["python", MAIN_SCRIPT, order_text],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False, # Leer como bytes
            env=env,
            encoding=None # No decodificar automáticamente aquí
        )

        # Leer stdout y stderr en hilos separados para evitar deadlocks
        def read_stream(stream, stream_name):
            for line_bytes in stream:
                try:
                    line_decoded = line_bytes.decode('utf-8', errors='replace').strip()
                    if line_decoded:
                        q.put(f"[{stream_name}] {line_decoded}")
                except Exception as decode_e:
                    q.put(f"[{stream_name} DECODE ERROR] {decode_e} - Raw: {line_bytes}")

        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, "STDOUT"))
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, "STDERR"))

        stdout_thread.start()
        stderr_thread.start()

        stdout_thread.join()
        stderr_thread.join()

        process.wait() # Esperar a que el proceso termine
        
        if process.returncode == 0:
            q.put("✅ main.py ejecutado correctamente.")
        else:
            q.put(f"❌ main.py finalizó con errores. Código de salida: {process.returncode}")

    except FileNotFoundError:
        q.put(f"❌ Error: El script '{MAIN_SCRIPT}' no se encontró. Asegúrate de que esté en la raíz del proyecto.")
    except Exception as e:
        q.put(f"❌ Error inesperado al ejecutar main.py: {e}")


# Función para actualizar la salida de la consola en Streamlit
def update_console_output():
    output_lines = []
    while not output_queue.empty():
        output_lines.append(output_queue.get())
    
    if output_lines:
        with console_output_placeholder.container():
            st.subheader("Salida en consola:")
            for line in output_lines:
                st.code(line, language="text")
        # st.experimental_rerun() # Descomentar si la actualización no es lo suficientemente rápida
                               # Puede causar parpadeo si se llama con demasiada frecuencia

# Botón para iniciar la grabación y el procesamiento
if st.button("🎤 Iniciar Asistente"):
    if record_audio(AUDIO_FILE):
        transcribed_text = transcribe_audio(AUDIO_FILE)
        if transcribed_text:
            # Guardar la transcripción en el archivo de orden
            with open(ORDER_FILE, "w", encoding="utf-8") as f:
                f.write(transcribed_text)
            st.info(f"INFO: Transcripción guardada en: {ORDER_FILE}")

            # Añadir al historial de órdenes
            st.session_state.order_history.append(f"[{time.strftime('%H:%M:%S')}] {transcribed_text}")

            st.info(f"🛠️ Ejecutando main.py con la orden: {transcribed_text}")
            
            # Ejecutar main.py en un hilo separado
            thread = threading.Thread(target=run_main_script_in_thread, args=(transcribed_text, output_queue))
            thread.start()
            
            # Mostrar un mensaje de carga mientras el subproceso se ejecuta
            with st.spinner('Procesando orden...'):
                while thread.is_alive() or not output_queue.empty():
                    update_console_output()
                    time.sleep(0.1) # Pequeña pausa para evitar el uso excesivo de la CPU

            update_console_output() # Una última actualización para asegurar que se muestre todo

# Mostrar historial de órdenes
st.subheader("🕓 Historial de órdenes")
if st.session_state.order_history:
    for order in reversed(st.session_state.order_history): # Mostrar las más recientes primero
        st.write(order)
else:
    st.info("No hay órdenes en el historial aún.")

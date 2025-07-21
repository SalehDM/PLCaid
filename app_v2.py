import streamlit as st
import subprocess
import os
from datetime import datetime
import time
import sounddevice as sd # Importar sounddevice
from scipy.io.wavfile import write # Importar write para guardar WAV
import speech_recognition as sr # Importar speech_recognition

# --- Configuración de rutas ---
# voice_to_text_whisper.py ya no se usará para la grabación de voz directa aquí
# ORDER_FILE_PATH se usará para guardar la transcripción de la voz
ORDER_FILE_PATH = os.path.join(os.path.dirname(__file__), 'input_text', 'order.txt')
HISTORIAL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'historial.txt')
RECORDED_AUDIO_PATH = os.path.join(os.path.dirname(__file__), 'input_text', 'recorded_audio.wav') # Ruta para guardar el audio grabado

# Inyectar CSS para estilos personalizados
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Montserrat', sans-serif;
        background-color: #f9fbfc;
    }
    .title {
        font-size: 3rem;
        font-weight: 700;
        color: #003366;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
        font-size: 1.1rem;
        transition: background-color 0.3s ease;
        border: none;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .stTextArea>div>textarea {
        font-size: 1.1rem;
        font-family: 'Courier New', Courier, monospace;
        border-radius: 8px;
        border: 1.5px solid #007BFF;
        background-color: #ffffff;
        padding: 10px;
    }
    .history-item {
        background-color: ;
        border-left: 5px solid #007BFF;
        padding: 12px 18px;
        margin-bottom: 10px;
        border-radius: 6px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .info-box {
        background-color: #d9edf7;
        color: #31708f;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Configuración general de la interfaz
st.markdown('<h1 class="title">🤖 Interfaz de Control para PLCaid</h1>', unsafe_allow_html=True)

# Sidebar con opciones extra y ayuda
st.sidebar.header("⚙️ Opciones")
duracion_grabacion = st.sidebar.slider("Duración grabación (segundos)", 1, 10, 5, help="Selecciona la duración en segundos para la grabación de voz.")

st.sidebar.markdown("""
---
### ℹ️ Ayuda
- Usa el modo Texto para escribir instrucciones manualmente.
- Usa el modo Voz para grabar y transcribir comandos.
- El historial se guarda automáticamente en un archivo.
- Puedes limpiar el historial usando el botón correspondiente.
""")

# Inicializar historial en sesión
if "historial" not in st.session_state:
    st.session_state.historial = []

# Cargar historial desde archivo al inicio (solo si está vacío)
if not st.session_state.historial:
    try:
        if os.path.exists(HISTORIAL_FILE_PATH):
            with open(HISTORIAL_FILE_PATH, "r", encoding="utf-8") as f:
                lineas = f.readlines()
                st.session_state.historial = [linea.strip() for linea in lineas if linea.strip()]
    except FileNotFoundError:
        pass

# Función para guardar línea en historial.txt
def guardar_historial(linea):
    os.makedirs(os.path.dirname(HISTORIAL_FILE_PATH), exist_ok=True)
    with open(HISTORIAL_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(linea + "\n")

# Función para grabar audio (integrada de la versión anterior)
def grabar_audio(duracion=5, samplerate=44100):
    st.info(f"🎙️ Grabando audio... habla ahora ({duracion} segundos).")
    # Asegurarse de que el directorio de salida exista para el audio
    os.makedirs(os.path.dirname(RECORDED_AUDIO_PATH), exist_ok=True)
    
    # sd.rec es no bloqueante, sd.wait() espera a que termine la grabación
    audio = sd.rec(int(duracion * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    
    write(RECORDED_AUDIO_PATH, samplerate, audio) # Guardar el audio en la ruta definida
    return RECORDED_AUDIO_PATH

# Función para transcribir audio con Google Speech Recognition (integrada de la versión anterior)
def transcribir_audio(ruta_audio):
    r = sr.Recognizer()
    try:
        with sr.AudioFile(ruta_audio) as source:
            audio = r.record(source)
        texto = r.recognize_google(audio, language="es-ES")
        return texto
    except sr.UnknownValueError:
        return "⚠️ No se entendió el audio."
    except sr.RequestError as e:
        return f"❌ Error al conectar con el servicio de reconocimiento: {e}"
    except Exception as e:
        return f"❌ Ocurrió un error inesperado durante la transcripción: {e}"


# Función para ejecutar main.py
def ejecutar_main(instruccion):
    st.info(f"🛠️ Ejecutando main.py con la orden: **{instruccion}**")
    try:
        main_script_path = os.path.join(os.path.dirname(__file__), 'main.py')
        resultado = subprocess.run(
            ["python", main_script_path, instruccion],
            capture_output=True, text=True, check=True
        )
        salida = resultado.stdout
        st.success("✅ main.py ejecutado correctamente.")
        st.code(salida, language="bash")
    except subprocess.CalledProcessError as e:
        st.error("❌ Error al ejecutar main.py")
        st.code(e.stderr)
    except FileNotFoundError:
        st.error(f"❌ Error: No se encontró 'main.py' en la ruta esperada: {main_script_path}")


# Layout: columnas para entrada y botones
col1, col2 = st.columns([3, 1])

with col1:
    modo = st.radio("Selecciona el modo de entrada:", ["📝 Texto", "🎙️ Voz"])

with col2:
    if st.button("🧹 Limpiar historial"):
        st.session_state.historial.clear()
        # También borrar archivo historial.txt
        if os.path.exists(HISTORIAL_FILE_PATH):
            with open(HISTORIAL_FILE_PATH, "w", encoding="utf-8") as f:
                f.write("")
        st.success("✅ Historial borrado.")

if modo == "📝 Texto":
    instruccion = st.text_area("Escribe tus instrucciones aquí:", height=150, key="entrada_texto")
    if st.button("▶️ Enviar texto"):
        if instruccion.strip():
            linea = f"[{datetime.now().strftime('%H:%M:%S')}] {instruccion.strip()}"
            st.session_state.historial.append(linea)
            guardar_historial(linea)
            ejecutar_main(instruccion.strip())
        else:
            st.warning("⚠️ Escribe alguna instrucción.")

elif modo == "🎙️ Voz":
    if st.button("🎧 Grabar voz"):
        # Asegurarse de que el directorio para la transcripción exista
        os.makedirs(os.path.dirname(ORDER_FILE_PATH), exist_ok=True)

        audio_path = grabar_audio(duracion=duracion_grabacion)
        transcripcion = transcribir_audio(audio_path)
        
        st.text_area("🗣️ Transcripción de voz:", transcripcion, height=100)
        
        # Guardar la transcripción en order.txt
        with open(ORDER_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(transcripcion)
        st.info(f"INFO: Transcripción guardada en: {ORDER_FILE_PATH}")

        if "⚠️" not in transcripcion and "❌" not in transcripcion:
            linea = f"[{datetime.now().strftime('%H:%M:%S')}] {transcripcion}"
            st.session_state.historial.append(linea)
            guardar_historial(linea)
            ejecutar_main(transcripcion)
        else:
            st.warning("⚠️ La transcripción contiene errores o no se entendió la voz. No se enviará a main.py.")


st.markdown("---")
st.subheader("🕓 Historial de órdenes")

if st.session_state.historial:
    for item in st.session_state.historial[::-1]:
        st.markdown(f'<div class="history-item">{item}</div>', unsafe_allow_html=True)
else:
    st.info("No hay órdenes registradas aún.")

import streamlit as st
import sys
import os
import subprocess
import speech_recognition as sr
from mss import mss

# --- Funciones Auxiliares ---

# Función para grabar audio y convertir a texto
def transcribir_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Hablando... (esperando voz)")
        # Ajustar para ruido ambiental para mejor reconocimiento
        r.adjust_for_ambient_noise(source) 
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10) # Añadir timeouts
            texto = r.recognize_google(audio, language="es-ES")
            return texto
        except sr.UnknownValueError:
            st.error("No se entendió el audio. Por favor, intenta de nuevo.")
        except sr.RequestError as e:
            st.error(f"Error en el servicio de reconocimiento de voz: {e}. Revisa tu conexión a internet.")
        except Exception as e:
            st.error(f"Ocurrió un error inesperado durante la transcripción: {e}")
    return ""

# Obtener monitores disponibles
def obtener_monitores():
    with mss() as sct:
        # mss.monitors[0] es una tupla que representa la pantalla combinada de todos los monitores.
        # Los monitores individuales comienzan desde el índice 1.
        monitors_list = sct.monitors[1:] 
        return monitors_list

# --- Inicialización del Estado de Sesión de Streamlit ---
# Se utiliza st.session_state para mantener el estado de la aplicación a través de las reruns.
if 'current_order' not in st.session_state:
    st.session_state.current_order = "" # Almacena la orden actual (texto o transcrita)
if 'input_mode' not in st.session_state:
    st.session_state.input_mode = "Texto" # Almacena el modo de entrada seleccionado ("Texto" o "Voz")
if 'selected_monitor_idx' not in st.session_state: # Inicializar el índice del monitor seleccionado
    st.session_state.selected_monitor_idx = 0

# --- Interfaz de Usuario Streamlit ---
col1, col2 = st.columns([1, 5])

with col1:
    # Asegúrate de que la ruta a tu icono sea correcta.
    # Si interface.py está en la raíz del proyecto, y icons/plc.png está en icons/, entonces './icons/plc.png' es correcto.
    st.image("./icons/plc.png", width=200) # Mostrar el logo del proyecto

with col2:
    st.title("Programador para PLC")

# Selector de entrada (Texto o Voz)
# El valor inicial del radio button se basa en el estado de sesión.
modo = st.radio(
    "Selecciona modo de entrada:", 
    ["Texto", "Voz"], 
    index=0 if st.session_state.input_mode == "Texto" else 1,
    key="input_mode_radio" # Clave única para el widget
)

# Actualizar el modo de entrada en el estado de sesión
st.session_state.input_mode = modo

# Lógica para la entrada de orden (Texto o Voz)
if st.session_state.input_mode == "Texto":
    # El st.text_area se enlaza directamente a st.session_state.current_order
    # Cualquier cambio en el text_area actualizará automáticamente el estado.
    st.session_state.current_order = st.text_area(
        "📄 Escribe tu orden en lenguaje natural:", 
        value=st.session_state.current_order, 
        height=150,
        key="text_input_area" # Clave única para el widget
    )
elif st.session_state.input_mode == "Voz":
    # Botón para iniciar la grabación de voz
    if st.button("🎤 Grabar orden por voz", key="record_voice_button"):
        with st.spinner("Escuchando... por favor, habla."):
            transcribed_text = transcribir_audio()
            if transcribed_text:
                st.session_state.current_order = transcribed_text
                st.success(f"Transcripción completada.")
            else:
                st.warning("No se pudo transcribir la voz.")
    
    # Mostrar el texto transcrito en un área de texto editable
    # El valor se toma de st.session_state.current_order, permitiendo al usuario editarlo.
    st.session_state.current_order = st.text_area(
        "📝 Texto transcrito (puedes editarlo):", 
        value=st.session_state.current_order, 
        height=150,
        key="transcribed_text_area" # Clave única para el widget
    )

# Selección de monitor
monitores = obtener_monitores()
monitor_options = [f"Monitor {i+1}: {m['width']}x{m['height']}" for i, m in enumerate(monitores)]

if not monitor_options:
    monitor_options = ["Monitor por defecto (primario)"]
    selected_monitor_index = 0
else:
    selected_monitor_index = st.selectbox(
        "🖥️ Selecciona el monitor a usar:", 
        range(len(monitores)), 
        index=st.session_state.selected_monitor_idx, # Usar el índice del estado de sesión
        format_func=lambda x: monitor_options[x],
        key="monitor_selectbox" # Clave única para el widget
    )
    # Actualizar el índice del monitor en el estado de sesión
    st.session_state.selected_monitor_idx = selected_monitor_index

# --- Botón de Ejecución del Flujo ---
if st.button("🚀 Ejecutar flujo", key="execute_flow_button"):
    # La orden a ejecutar siempre se toma de st.session_state.current_order
    orden_a_ejecutar = st.session_state.current_order.strip()

    if not orden_a_ejecutar:
        st.warning("Por favor, escribe o graba una orden antes de ejecutar.")
    else:
        # Obtener el directorio raíz del proyecto para guardar order.txt
        # Asumiendo que interface.py está en la raíz del proyecto (PLCaid/)
        project_root_for_files = os.path.dirname(os.path.abspath(__file__))
        
        input_path = os.path.join(project_root_for_files, "input_text", "order.txt")
        os.makedirs(os.path.dirname(input_path), exist_ok=True)
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(orden_a_ejecutar)
        
        # Preparar las variables de entorno para el subproceso
        env = os.environ.copy()
        # El ID real del monitor para mss es selected_monitor_index + 1
        env["MONITOR_ID"] = str(selected_monitor_index + 1) 
        
        try:
            st.info(f"Lanzando main.py para el monitor ID: {selected_monitor_index + 1} con la orden: '{orden_a_ejecutar}'...")
            
            # Construir la ruta absoluta a main.py
            # Asumiendo que main.py está en la misma raíz que interface.py
            main_script_path = os.path.join(project_root_for_files, "main.py")

            # Ejecutar main.py como un subproceso
            # El cwd (current working directory) del subproceso se establece a la raíz del proyecto.
            # Esto asegura que main.py pueda encontrar sus propios archivos relativos (input_text, parsed_steps, script).
            result = subprocess.run(
                [sys.executable, main_script_path], 
                env=env, 
                check=True, 
                capture_output=False, # Permite que la salida de main.py se imprima directamente en la consola
                text=True,
                cwd=project_root_for_files # <-- CWD ajustado a la raíz del proyecto
            )

            st.success("✅ Flujo lanzado con éxito. Revisa la consola para la salida de main.py.")
            
        except subprocess.CalledProcessError as e:
            st.error(f"❌ Error al ejecutar main.py (Código de salida: {e.returncode}): {e}")
            if e.stdout: st.code(e.stdout)
            if e.stderr: st.code(e.stderr)
        except FileNotFoundError:
            st.error(f"❌ Error: No se encontró el archivo '{main_script_path}'. Asegúrate de que el archivo 'main.py' exista en la raíz del proyecto.")
        except Exception as e:
            st.error(f"❌ Ocurrió un error inesperado: {e}")


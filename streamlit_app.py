import streamlit as st
import os
import uuid
from PIL import Image
import time
import pyautogui

# Importar los módulos que hemos creado
from qdrant_handler import QdrantHandler
from image_processor import ImageProcessor
from utils.screen_utils import take_screenshot, find_image_on_screen, get_monitor_info

# --- Inicializar handlers (pueden ser singleton o instanciados una vez) ---
qdrant_handler = QdrantHandler()
image_processor = ImageProcessor()

CLIPPINGS_DIR = "clippings"
os.makedirs(CLIPPINGS_DIR, exist_ok=True) # Asegurarse de que la carpeta exista

st.set_page_config(layout="wide", page_title="Automatización de UI con IA y RAG")

st.title("🤖 Automatización de UI y Control PLC con IA Generativa")
st.markdown("Esta aplicación te permite automatizar interacciones con la interfaz de Windows (clics) y controlar un PLC S7-1200, todo impulsado por IA generativa (Open AI), RAG y Qdrant.")

# --- Pestañas para organizar la interfaz ---
tab_ingesta, tab_acciones, tab_plc, tab_config = st.tabs(["📝 Ingesta de Recortes", "🚀 Ejecutar Acciones UI", "🏭 Control PLC", "⚙️ Configuración"])

# --- Tab 1: Ingesta de Recortes ---
with tab_ingesta:
    st.header("Gestionar Recortes de UI")
    st.write("Sube imágenes de recortes de elementos de la UI de Windows (iconos, pestañas, botones, campos de texto, etc.) para que la IA los describa y almacene en Qdrant.")

    uploaded_file = st.file_uploader("Sube un archivo de imagen (PNG, JPG) de tu recorte", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        # Guardar temporalmente el archivo subido
        temp_clipping_path = os.path.join("temp_uploaded_clipping.png") # O un nombre más único
        with open(temp_clipping_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.image(uploaded_file, caption="Recorte subido", use_column_width=True)
        st.success("Archivo subido con éxito. Procesando...")

        # Llama a la función de procesamiento
        try:
            # Aquí llamamos a la lógica de main.py
            # Necesitamos adaptar process_and_store_clipping para que no use print directamente
            # o capturar la salida. Por ahora, la copiamos aquí para la demo en Streamlit.

            description, keywords, element_type = image_processor.describe_image_with_ai(temp_clipping_path)
            
            if description:
                st.subheader("Descripción generada por Open AI:")
                st.write(f"**Descripción:** {description}")
                st.write(f"**Palabras clave:** {', '.join(keywords)}")
                st.write(f"**Tipo de Elemento:** {element_type}")

                embedding = image_processor.generate_embedding_from_text(description)
                if len(embedding) == qdrant_handler.VECTOR_DIMENSION:
                    point_id = str(uuid.uuid4())
                    final_clipping_path = os.path.join(CLIPPINGS_DIR, f"{point_id}.png")
                    
                    # Copiar el archivo subido a la carpeta de clippings con el nuevo ID
                    Image.open(temp_clipping_path).save(final_clipping_path)

                    payload = {
                        "image_id": point_id,
                        "image_path": os.path.abspath(final_clipping_path), # Ruta absoluta
                        "description": description,
                        "keywords": keywords,
                        "type": element_type,
                        "original_file_name": uploaded_file.name
                    }
                    
                    if qdrant_handler.upsert_point(point_id, embedding, payload):
                        st.success(f"Recorte procesado y almacenado en Qdrant con ID: `{point_id}`")
                        st.write(f"Guardado en: `{final_clipping_path}`")
                    else:
                        st.error("Error al guardar el recorte en Qdrant.")
                else:
                    st.error(f"Error: El embedding generado tiene una dimensión incorrecta ({len(embedding)}). Esperado: {qdrant_handler.VECTOR_DIMENSION}.")
            else:
                st.error("Open AI no pudo generar una descripción para la imagen.")
            
            # Limpiar el archivo temporal
            os.remove(temp_clipping_path)

        except Exception as e:
            st.error(f"Ocurrió un error durante el procesamiento: {e}")
            if os.path.exists(temp_clipping_path):
                os.remove(temp_clipping_path)

# --- Tab 2: Ejecutar Acciones UI ---
with tab_acciones:
    st.header("Ejecutar Acciones en la UI")
    st.write("Introduce una instrucción de texto o voz para que la aplicación localice y clique un elemento en tu pantalla.")

    st.subheader("Configuración de Captura de Pantalla")
    monitors_info = get_monitor_info()
    monitor_options = ["Todos los monitores"] + [f"Monitor {m['id']} ({m['width']}x{m['height']})" for m in monitors_info if m['id'] is not None]
    selected_monitor_option = st.selectbox("Selecciona un monitor para la captura:", monitor_options)
    
    monitor_to_capture_id = None
    if selected_monitor_option != "Todos los monitores":
        monitor_to_capture_id = int(selected_monitor_option.split('(')[0].replace('Monitor ', '').strip())
    
    confidence_level = st.slider("Nivel de confianza para la detección de imagen (PyAutoGUI):", 0.0, 1.0, 0.8, 0.05)

    instruction_text = st.text_input("Instrucción de texto (ej. 'Abrir papelera de reciclaje', 'Clicar en el botón Aceptar'):")

    if st.button("Ejecutar Acción"):
        if instruction_text:
            st.info(f"Buscando elementos relacionados con: '{instruction_text}'...")
            
            try:
                query_embedding = image_processor.generate_embedding_from_text(instruction_text)
                
                if len(query_embedding) != qdrant_handler.VECTOR_DIMENSION:
                    st.error("Error al generar embedding para la instrucción. Dimensión incorrecta.")
                else:
                    search_results = qdrant_handler.search_points(query_embedding, limit=3)

                    if search_results:
                        st.subheader("Resultados de la búsqueda RAG:")
                        best_match = search_results[0]
                        
                        st.write(f"**Mejor coincidencia (Score: {best_match.score:.4f}):**")
                        st.write(f"  **Descripción:** {best_match.payload.get('description', 'N/A')}")
                        st.write(f"  **Tipo:** {best_match.payload.get('type', 'N/A')}")
                        st.write(f"  **Ruta de Imagen:** `{best_match.payload.get('image_path', 'N/A')}`")

                        clipping_file_path = best_match.payload.get("image_path")
                        if clipping_file_path and os.path.exists(clipping_file_path):
                            st.image(clipping_file_path, caption="Recorte Sugerido", width=100)

                            st.write("Tomando captura de pantalla y buscando el elemento...")
                            current_screenshot_image = None
                            try:
                                current_screenshot_image = take_screenshot(monitor_number=monitor_to_capture_id)
                                current_screenshot_image_path = "temp_current_screenshot.png"
                                current_screenshot_image.save(current_screenshot_image_path)
                                # st.image(current_screenshot_image, caption="Captura de Pantalla Actual", use_column_width=True)
                            except ValueError as ve:
                                st.error(f"Error de monitor: {ve}")
                                current_screenshot_image = None
                            except Exception as e:
                                st.error(f"Error al tomar captura de pantalla: {e}")
                                current_screenshot_image = None
                            
                            if current_screenshot_image:
                                location = find_image_on_screen(clipping_file_path, current_screenshot_image, confidence=confidence_level)
                                
                                if location:
                                    center_x = location.left + location.width / 2
                                    center_y = location.top + location.height / 2
                                    st.success(f"Elemento localizado en pantalla en: ({location.left}, {location.top}, {location.width}, {location.height}). Clicando...")
                                    pyautogui.click(center_x, center_y)
                                    st.success("¡Clic ejecutado con éxito!")
                                else:
                                    st.warning("No se pudo localizar el elemento en la pantalla actual con la confianza dada.")
                            else:
                                st.error("No se pudo obtener una captura de pantalla para buscar el elemento.")
                            
                            if os.path.exists(current_screenshot_image_path):
                                os.remove(current_screenshot_image_path) # Limpiar archivo temporal

                        else:
                            st.error(f"Error: La imagen del recorte ({clipping_file_path}) no se encontró en el sistema de archivos.")
                    else:
                        st.info("No se encontraron coincidencias suficientes en Qdrant para tu instrucción.")
            except Exception as e:
                st.error(f"Ocurrió un error al procesar la instrucción: {e}")
        else:
            st.warning("Por favor, introduce una instrucción de texto.")

# --- Tab 3: Control PLC ---
with tab_plc:
    st.header("Control y Simulación de PLC (Siemens S7-1200)")
    st.info("Esta sección se desarrollará en futuras iteraciones. Aquí podrás programar y simular el PLC S7-1200.")
    st.markdown("""
    Funcionalidades planeadas:
    - Conexión al PLC S7-1200 (usando `python-snap7`).
    - Lectura y escritura de bloques de datos (DBs), entradas, salidas.
    - Interfaz para enviar comandos de programación o simulación.
    - Posiblemente, generación de código PLC simple usando IA (avanzado).
    """)

# --- Tab 4: Configuración ---
with tab_config:
    st.header("Configuración de la Aplicación")
    st.write("Aquí puedes ver y gestionar las configuraciones de la aplicación.")
    
    st.subheader("Variables de Entorno Cargadas")
    st.code(f"QDRANT_HOST: {os.getenv('QDRANT_HOST')}")
    st.code(f"QDRANT_API_KEY: {'*' * len(os.getenv('QDRANT_API_KEY')) if os.getenv('QDRANT_API_KEY') else 'No configurado'}")
    st.code(f"OPENAI_API_KEY: {'*' * len(os.getenv('OPENAI_API_KEY')) if os.getenv('OPENAI_API_KEY') else 'No configurado'}")

    st.subheader("Información de Monitores Detectados")
    monitors_data = get_monitor_info()
    if monitors_data:
        for mon in monitors_data:
            st.json(mon)
    else:
        st.info("No se pudo obtener la información de los monitores.")

    st.subheader("Directorio de Recortes")
    st.write(f"Los recortes se guardan en: `{os.path.abspath(CLIPPINGS_DIR)}`")
    st.write(f"Número de recortes guardados: {len(os.listdir(CLIPPINGS_DIR)) if os.path.exists(CLIPPINGS_DIR) else 0}")
import os
import uuid
from PIL import Image
import pyautogui # Para hacer clic en las coordenadas encontradas
import time # Para pausas entre acciones

from qdrant_handler import QdrantHandler
from image_processor import ImageProcessor
from utils.screen_utils import take_screenshot, find_image_on_screen, get_monitor_info

CLIPPINGS_DIR = "clippings"
os.makedirs(CLIPPINGS_DIR, exist_ok=True) # Asegurarse de que la carpeta exista

qdrant_handler = QdrantHandler()
image_processor = ImageProcessor()

def process_and_store_clipping(clipping_image_path: str):
    """
    Procesa un recorte de imagen: obtiene descripción y embedding,
    y lo almacena en Qdrant, moviendo el archivo a la carpeta 'clippings'.
    Args:
        clipping_image_path (str): Ruta al archivo de imagen del recorte original.
    Returns:
        str: El ID único del recorte en Qdrant (o None si falla).
    """
    print(f"\n--- Procesando y almacenando recorte: {clipping_image_path} ---")
    
    if not os.path.exists(clipping_image_path):
        print(f"Error: El archivo de recorte '{clipping_image_path}' no existe.")
        return None

    try:
        # 1. Obtener descripción, palabras clave y tipo de elemento con Gemini
        description, keywords, element_type = image_processor.describe_image_with_ai(clipping_image_path)
        if not description:
            print("No se pudo generar una descripción con Gemini. Abortando.")
            return None

        # 2. Generar embedding de la descripción
        embedding = image_processor.generate_embedding_from_text(description)
        if len(embedding) != qdrant_handler.VECTOR_DIMENSION:
            print(f"Error: El embedding generado tiene dimensión {len(embedding)}, se esperaba {qdrant_handler.VECTOR_DIMENSION}. Abortando.")
            return None

        # 3. Generar un ID único para Qdrant y para el nombre del archivo
        point_id = str(uuid.uuid4())
        
        # 4. Definir la ruta final del recorte
        final_clipping_path = os.path.join(CLIPPINGS_DIR, f"{point_id}.png")

        # 5. Preparar payload para Qdrant
        payload = {
            "image_id": point_id, # Usar el ID como identificador de imagen
            "image_path": os.path.abspath(final_clipping_path), # Ruta absoluta para referencia
            "description": description,
            "keywords": keywords,
            "type": element_type,
            "original_file_name": os.path.basename(clipping_image_path)
        }

        # 6. Almacenar en Qdrant
        success = qdrant_handler.upsert_point(point_id, embedding, payload)
        if not success:
            print(f"Falló el almacenamiento en Qdrant para '{clipping_image_path}'. Abortando.")
            return None

        # 7. Mover/Copiar el archivo de recorte a la carpeta 'clippings' con el ID como nombre
        Image.open(clipping_image_path).save(final_clipping_path)
        print(f"Recorte guardado en: {final_clipping_path}")

        print(f"Proceso de almacenamiento de recorte completado con éxito. ID: {point_id}")
        return point_id

    except Exception as e:
        print(f"Error general al procesar y almacenar el recorte '{clipping_image_path}': {e}")
        return None

def execute_action_from_text(instruction: str, monitor_to_capture: int = None, confidence: float = 0.9):
    """
    Toma una instrucción de texto, busca el recorte más relevante en Qdrant,
    lo localiza en pantalla y ejecuta un clic.
    Args:
        instruction (str): La instrucción de texto del usuario (ej. "abrir papelera").
        monitor_to_capture (int, optional): El ID del monitor a capturar (None para todos).
        confidence (float): Nivel de confianza para pyautogui.locate.
    Returns:
        bool: True si la acción se ejecutó, False en caso contrario.
    """
    print(f"\n--- Ejecutando acción para la instrucción: '{instruction}' ---")
    try:
        # 1. Generar embedding de la instrucción
        query_embedding = image_processor.generate_embedding_from_text(instruction)
        if len(query_embedding) != qdrant_handler.VECTOR_DIMENSION:
            print("Error: El embedding de la instrucción no tiene la dimensión esperada. Abortando búsqueda.")
            return False

        # 2. Buscar recortes relevantes en Qdrant
        search_results = qdrant_handler.search_points(query_embedding, limit=1) # Buscar el más relevante
        
        if not search_results:
            print(f"No se encontraron recortes relevantes en Qdrant para la instrucción: '{instruction}'.")
            return False

        best_match = search_results[0]
        match_id = best_match.id
        match_payload = best_match.payload
        match_score = best_match.score

        print("Mejor coincidencia encontrada en Qdrant:")
        print(f"  ID: {match_id}, Score: {match_score}")
        print(f"  Descripción: {match_payload.get('description', 'N/A')}")
        print(f"  Ruta de imagen: {match_payload.get('image_path', 'N/A')}")
        
        clipping_file_path = match_payload.get("image_path")
        if not clipping_file_path or not os.path.exists(clipping_file_path):
            print(f"Error: La ruta de imagen del recorte no es válida o no existe: {clipping_file_path}")
            return False

        # 3. Tomar captura de pantalla actual (del monitor/es deseado/s)
        current_screenshot_image = take_screenshot(monitor_to_capture)
        
        # 4. Localizar el recorte en la captura de pantalla
        location = find_image_on_screen(clipping_file_path, current_screenshot_image, confidence=confidence)

        if location:
            # Calcular el centro del recorte encontrado
            center_x = location.left + location.width / 2
            center_y = location.top + location.height / 2
            
            print(f"Recorte localizado en pantalla en: {location}. Clicando en ({center_x}, {center_y})...")
            pyautogui.click(center_x, center_y)
            print("Clic ejecutado.")
            return True
        else:
            print("No se pudo localizar el recorte en la pantalla actual.")
            return False

    except Exception as e:
        print(f"Error general al ejecutar la acción para '{instruction}': {e}")
        return False

if __name__ == "__main__":
    print("--- Iniciando el sistema de automatización de UI ---")

    # --- Parte 1: Ingesta Manual de Recortes (simulada) ---
    print("\n### Fase de Ingesta de Recortes ###")
    print("Para probar la ingesta, asegúrate de tener una imagen de recorte en la raíz del proyecto.")
    print("Por ejemplo, recorta el icono de la Papelera de Reciclaje y guárdalo como 'papelera_reciclaje.png'")
    
    test_clipping_path = "papelera_reciclaje.png" # <--- CAMBIA ESTO A TU ARCHIVO DE RECORTE DE PRUEBA
    
    if os.path.exists(test_clipping_path):
        qdrant_id_ingested = process_and_store_clipping(test_clipping_path)
        if qdrant_id_ingested:
            print(f"Recorte '{test_clipping_path}' procesado y almacenado con ID: {qdrant_id_ingested}")
        else:
            print(f"Falló el procesamiento de '{test_clipping_path}'.")
    else:
        print(f"El archivo de recorte de prueba '{test_clipping_path}' no se encontró.")
        print("Por favor, crea uno para probar la funcionalidad de ingesta.")

    # Dar un pequeño respiro al sistema antes de la siguiente fase
    time.sleep(2)

    # --- Parte 2: Ejecución de Acciones basada en Texto ---
    print("\n### Fase de Ejecución de Acciones ###")
    print("Ahora intentaremos ejecutar una acción basada en una instrucción de texto.")
    print("Asegúrate de que el elemento que intentas clicar esté visible en la pantalla.")

    # Ejemplo 1: Intentar abrir la papelera de reciclaje
    instruction_1 = "Abrir la papelera de reciclaje"
    print(f"\nIntento 1: Ejecutar la instrucción: '{instruction_1}'")
    success_1 = execute_action_from_text(instruction_1, monitor_to_capture=None, confidence=0.8) # None para todos los monitores
    if success_1:
        print(f"Acción para '{instruction_1}' ejecutada con éxito.")
    else:
        print(f"Falló la acción para '{instruction_1}'. Revisa logs y visibilidad del elemento.")
    
    time.sleep(3) # Pausa para ver el resultado

    # Ejemplo 2: Una instrucción que NO debería encontrar nada si solo tenemos el icono de la papelera
    instruction_2 = "Cerrar ventana de Chrome"
    print(f"\nIntento 2: Ejecutar la instrucción: '{instruction_2}' (no debería encontrar coincidencia si solo tienes un recorte de papelera)")
    success_2 = execute_action_from_text(instruction_2, monitor_to_capture=None, confidence=0.8)
    if success_2:
        print(f"Acción para '{instruction_2}' ejecutada con éxito (inesperado si solo tienes un recorte de papelera).")
    else:
        print(f"Falló la acción para '{instruction_2}' (esperado si no hay recorte de 'cerrar ventana de Chrome').")

    print("\n--- Sistema de automatización de UI finalizado para esta ejecución ---")
    print("Para instrucciones más complejas que requieran múltiples pasos, necesitaríamos implementar LangChain y un planificador con Gemini.")
    print("Para la parte de PLC, se integraría una librería como python-snap7.")
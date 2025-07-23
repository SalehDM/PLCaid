import os
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from datetime import datetime
import uuid
import sys
from dotenv import load_dotenv # Importar load_dotenv

# --- Configurar la codificación de la salida de la consola al inicio ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass
except Exception as e:
    print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}", flush=True)

# --- Cargar variables de entorno al inicio ---
load_dotenv()

# --- Configuración ---
# Ahora obtenemos la URL y la API Key de Qdrant desde el archivo .env
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION_NAME_UI_ELEMENTS = "ui_elements"
COLLECTION_NAME_TASK_FLOWS = "task_flows"
EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# Verificar que las variables de Qdrant están configuradas
if not QDRANT_URL:
    print("ERROR: La variable de entorno QDRANT_URL no está configurada en .env", flush=True)
    sys.exit(1)
# Aunque la API Key podría ser opcional en algunos setups auto-gestionados,
# si se está migrando de local con la intención de usar API Key, es mejor hacerla obligatoria.
if not QDRANT_API_KEY:
    print("ERROR: La variable de entorno QDRANT_API_KEY no está configurada en .env. Es crucial para la autenticación de Qdrant.", flush=True)
    sys.exit(1)

# Inicializar el modelo de embeddings
try:
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device='cpu')
    EMBEDDING_DIM = embedding_model.get_sentence_embedding_dimension()
    print(f"INFO: Modelo de embeddings '{EMBEDDING_MODEL_NAME}' cargado en CPU. Dimensión: {EMBEDDING_DIM}", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"ERROR: Error al cargar el modelo de embeddings: {e}", flush=True)
    print("Asegúrate de tener 'sentence-transformers' instalado y de que el modelo se pueda descargar.", flush=True)
    sys.stdout.flush()
    exit(1)

# Inicializar el cliente de Qdrant
try:
    # Conexión a Qdrant usando la URL y la API Key de las variables de entorno
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)
    # Se añade un pequeño test para verificar la conexión inicial
    # Esto lanzará una excepción si la conexión falla (ej. Qdrant no está accesible o API Key es incorrecta)
    client.get_collections()
    print(f"INFO: Cliente Qdrant conectado a {QDRANT_URL} (con API Key)", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"ERROR: Error al conectar con Qdrant en {QDRANT_URL}: {e}", flush=True)
    print("Asegúrate de que el servidor Qdrant esté corriendo y accesible, y que la QDRANT_API_KEY sea correcta.", flush=True)
    sys.stdout.flush()
    exit(1)

def create_collections():
    """
    Crea las colecciones en Qdrant si no existen.
    """
    optimizers_config_dict = {
        "deleted_threshold": 0.2,
        "vacuum_min_vector_number": 100,
        "default_segment_number": 0,
        "flush_interval_sec": 5,
        "memmap_threshold": 20000,
    }

    if not client.collection_exists(collection_name=COLLECTION_NAME_UI_ELEMENTS):
        client.create_collection(
            collection_name=COLLECTION_NAME_UI_ELEMENTS,
            vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
            optimizers_config=optimizers_config_dict
        )
        print(f"INFO: Colección '{COLLECTION_NAME_UI_ELEMENTS}' creada.", flush=True)
        sys.stdout.flush()
    else:
        print(f"INFO: Colección '{COLLECTION_NAME_UI_ELEMENTS}' ya existe.", flush=True)
        sys.stdout.flush()

    if not client.collection_exists(collection_name=COLLECTION_NAME_TASK_FLOWS):
        client.create_collection(
            collection_name=COLLECTION_NAME_TASK_FLOWS,
            vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
            optimizers_config=optimizers_config_dict
        )
        print(f"INFO: Colección '{COLLECTION_NAME_TASK_FLOWS}' creada.", flush=True)
        sys.stdout.flush()
    else:
        print(f"INFO: Colección '{COLLECTION_NAME_TASK_FLOWS}' ya existe.", flush=True)
        sys.stdout.flush()

def get_embedding(text: str):
    """
    Genera el embedding para un texto dado.
    """
    return embedding_model.encode(text).tolist()

def add_ui_element(description: str, element_type: str, image_path: str = None, ocr_text: str = None, metadata: dict = None):
    """
    Añade una descripción de elemento de UI a la colección de Qdrant.
    """
    vector = get_embedding(description)
    payload = {
        "description": description,
        "type": element_type,
        "timestamp": datetime.now().isoformat()
    }
    if image_path:
        payload["image_path"] = image_path
    if ocr_text:
        payload["ocr_text"] = ocr_text
    if metadata:
        payload.update(metadata)

    point_id = str(uuid.uuid4().hex)

    client.upsert(
        collection_name=COLLECTION_NAME_UI_ELEMENTS,
        points=[
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
        ]
    )
    print(f"INFO: Elemento UI '{description}' añadido/actualizado en Qdrant con ID: {point_id}.", flush=True)
    sys.stdout.flush()

def search_ui_element(query_text: str, limit: int = 1, score_threshold: float = 0.7):
    """
    Busca elementos de UI similares a la consulta.
    Retorna los payloads de los elementos encontrados.
    """
    query_vector = get_embedding(query_text)
    search_result = client.search(
        collection_name=COLLECTION_NAME_UI_ELEMENTS,
        query_vector=query_vector,
        limit=limit,
        score_threshold=score_threshold
    )
    return [hit.payload for hit in search_result]

def add_task_flow(task_description: str, steps: list, metadata: dict = None):
    """
    Añade un flujo de tarea a la colección de Qdrant.
    Los pasos se almacenan como parte del payload.
    """
    vector = get_embedding(task_description)
    payload = {
        "task_description": task_description,
        "steps": steps,
        "timestamp": datetime.now().isoformat()
    }
    if metadata:
        payload.update(metadata)

    point_id = str(uuid.uuid4().hex)

    client.upsert(
        collection_name=COLLECTION_NAME_TASK_FLOWS,
        points=[
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
        ]
    )
    print(f"INFO: Flujo de tarea '{task_description}' añadido/actualizado en Qdrant con ID: {point_id}.", flush=True)
    sys.stdout.flush()

def search_task_flow(query_text: str, limit: int = 1, score_threshold: float = 0.6):
    """
    Busca flujos de tarea similares a la consulta.
    Retorna los payloads de los flujos encontrados.
    """
    query_vector = get_embedding(query_text)
    search_result = client.search(
        collection_name=COLLECTION_NAME_TASK_FLOWS,
        query_vector=query_vector,
        limit=limit,
        score_threshold=score_threshold
    )
    return [hit.payload for hit in search_result]

if __name__ == "__main__":
    print("--- Inicializando Knowledge Manager ---", flush=True)
    sys.stdout.flush()
    create_collections()

    print("\n--- Añadiendo elementos de UI de ejemplo ---", flush=True)
    sys.stdout.flush()
    add_ui_element("icono de inicio de Windows", "icono", metadata={"os": "Windows XP"})
    add_ui_element("botón de aceptar", "botón")
    add_ui_element("pestaña de configuración", "pestaña")
    add_ui_element("campo de texto para URL", "campo_entrada")
    add_ui_element("icono de MicroWin", "icono", metadata={"app": "MicroWin", "color": "azul", "forma": "engranaje"})

    print("\n--- Buscando elementos de UI ---", flush=True)
    sys.stdout.flush()
    results_ui = search_ui_element("botón para confirmar")
    if results_ui:
        print(f"Encontrado (UI): {results_ui[0]['description']} (Tipo: {results_ui[0]['type']})", flush=True)
    else:
        print("No se encontró un elemento UI similar.", flush=True)
    sys.stdout.flush()

    results_ui_2 = search_ui_element("icono para iniciar el sistema")
    if results_ui_2:
        print(f"Encontrado (UI): {results_ui_2[0]['description']} (Tipo: {results_ui_2[0]['type']})", flush=True)
    else:
        print("No se encontró un elemento UI similar.", flush=True)
    sys.stdout.flush()

    results_ui_3 = search_ui_element("icono del programa PLC")
    if results_ui_3:
        print(f"Encontrado (UI): {results_ui_3[0]['description']} (Tipo: {results_ui_3[0]['type']})", flush=True)
    else:
        print("No se encontró un elemento UI similar.", flush=True)
    sys.stdout.flush()

    print("\n--- Añadiendo flujos de tarea de ejemplo ---", flush=True)
    sys.stdout.flush()
    add_task_flow(
        "abrir el navegador web",
        [
            {"step": 1, "action": "busca el icono de 'Inicio'"},
            {"step": 2, "action": "haz clic en el icono de 'Inicio'"},
            {"step": 3, "action": "espera a que se abra el menú de 'Inicio'"},
            {"step": 4, "action": "busca el icono de 'Todos los programas'"},
            {"step": 5, "action": "haz clic en el icono de 'Todos los programas'"},
            {"step": 6, "action": "espera a que se abra el menú desplegable 'Todos los programas'"},
            {"step": 7, "action": "haz scroll en el menú desplegable 'Todos los programas'"},
            {"step": 8, "action": "busca el icono del navegador web"},
            {"step": 9, "action": "haz clic en el icono del navegador web"},
            {"step": 10, "action": "espera a que se abra el navegador web"}
        ]
    )
    add_task_flow(
        "crear una nueva carpeta",
        [
            {"step": 1, "action": "busca el icono de 'Mi PC'"},
            {"step": 2, "action": "haz clic en el icono de 'Mi PC'"},
            {"step": 3, "action": "espera a que se abra la ventana de 'Mi PC'"},
            {"step": 4, "action": "haz clic derecho en un espacio vacío"},
            {"step": 5, "action": "selecciona 'Nuevo'"},
            {"step": 6, "action": "selecciona 'Carpeta'"},
            {"step": 7, "action": "escribe el nombre de la nueva carpeta"}
        ]
    )
    sys.stdout.flush()

    print("\n--- Buscando flujos de tarea ---", flush=True)
    sys.stdout.flush()
    results_task = search_task_flow("abrir el navegador de internet")
    if results_task:
        print(f"Encontrado (Tarea): {results_task[0]['task_description']}", flush=True)
        print(f"Pasos: {results_task[0]['steps']}", flush=True)
    else:
        print("No se encontró un flujo de tarea similar.", flush=True)
    sys.stdout.flush()

    results_task_2 = search_task_flow("hacer una carpeta")
    if results_task_2:
        print(f"Encontrado (Tarea): {results_task_2[0]['task_description']}", flush=True)
        print(f"Pasos: {results_task_2[0]['steps']}", flush=True)
    else:
        print("No se encontró un flujo de tarea similar.", flush=True)
    sys.stdout.flush()

    print("\n--- Knowledge Manager listo ---", flush=True)
    sys.stdout.flush()
    
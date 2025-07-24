import os
from qdrant_client import QdrantClient
# Importar modelos específicos de http.models para compatibilidad con versiones recientes
from qdrant_client.http import models # <-- CAMBIO AQUI: Importar 'models' de qdrant_client.http
from sentence_transformers import SentenceTransformer
from datetime import datetime
import uuid
import sys
from dotenv import load_dotenv
import json
import traceback

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
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION_NAME_UI_ELEMENTS = "ui_elements"
COLLECTION_NAME_TASK_FLOWS = "task_flows"
EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# Verificar que las variables de Qdrant están configuradas
if not QDRANT_URL:
    print("ERROR: La variable de entorno QDRANT_URL no está configurada en .env", flush=True)
    sys.exit(1)
if not QDRANT_API_KEY:
    print("ERROR: La variable de entorno QDRANT_API_KEY no está configurada en .env. Es crucial para la autenticación de Qdrant.", flush=True)
    sys.stdout.flush()
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
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)
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

    # Opcional: Si quieres borrar la colección siempre para empezar de cero en desarrollo, descomenta la siguiente línea.
    # ¡Úsalo con precaución, borrará todos tus datos de la colección UI_ELEMENTS!
    # client.delete_collection(collection_name=COLLECTION_NAME_UI_ELEMENTS, timeout=30)
    # print(f"INFO: Colección '{COLLECTION_NAME_UI_ELEMENTS}' eliminada para recrearla.", flush=True)


    if not client.collection_exists(collection_name=COLLECTION_NAME_UI_ELEMENTS):
        print(f"INFO: Colección '{COLLECTION_NAME_UI_ELEMENTS}' no existe. Creándola...", flush=True)
        client.create_collection(
            collection_name=COLLECTION_NAME_UI_ELEMENTS,
            vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
            optimizers_config=optimizers_config_dict
        )
        print(f"INFO: Colección '{COLLECTION_NAME_UI_ELEMENTS}' creada.", flush=True)
        # Importante: Añadir índices de payload para campos clave si los vas a usar en filtros
        client.create_payload_index(
            collection_name=COLLECTION_NAME_UI_ELEMENTS,
            field_name="type", # Ejemplo: indexar por tipo de elemento
            field_schema=models.FieldType.KEYWORD # <-- CAMBIO AQUI: models.FieldType
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME_UI_ELEMENTS,
            field_name="description", # Ejemplo: indexar por descripción para búsquedas exactas (no embeddings)
            field_schema=models.FieldType.TEXT, # <-- CAMBIO AQUI: models.FieldType
            optimizer_params={"on_disk": True} # Opcional: almacenar en disco para datasets grandes
        )
        print(f"INFO: Índices de payload para '{COLLECTION_NAME_UI_ELEMENTS}' creados/verificados.", flush=True)
        sys.stdout.flush()
    else:
        print(f"INFO: Colección '{COLLECTION_NAME_UI_ELEMENTS}' ya existe.", flush=True)
        sys.stdout.flush()
        # Puedes verificar si los índices ya existen aquí y crearlos si no, aunque create_payload_index
        # suele ser idempotente (no falla si ya existe).
        try:
            client.create_payload_index(collection_name=COLLECTION_NAME_UI_ELEMENTS, field_name="type", field_schema=models.FieldType.KEYWORD) # <-- CAMBIO AQUI: models.FieldType
            client.create_payload_index(collection_name=COLLECTION_NAME_UI_ELEMENTS, field_name="description", field_schema=models.FieldType.TEXT, optimizer_params={"on_disk": True}) # <-- CAMBIO AQUI: models.FieldType
            print(f"INFO: Índices de payload para '{COLLECTION_NAME_UI_ELEMENTS}' verificados/creados (si faltaban).", flush=True)
        except Exception as e:
            print(f"WARNING: No se pudieron crear/verificar todos los índices de payload para '{COLLECTION_NAME_UI_ELEMENTS}': {e}", flush=True)


    if not client.collection_exists(collection_name=COLLECTION_NAME_TASK_FLOWS):
        print(f"INFO: Colección '{COLLECTION_NAME_TASK_FLOWS}' no existe. Creándola...", flush=True)
        client.create_collection(
            collection_name=COLLECTION_NAME_TASK_FLOWS,
            vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
            optimizers_config=optimizers_config_dict
        )
        print(f"INFO: Colección '{COLLECTION_NAME_TASK_FLOWS}' creada.", flush=True)
        # Puedes añadir índices también para esta colección si vas a filtrar por algún campo
        sys.stdout.flush()
    else:
        print(f"INFO: Colección '{COLLECTION_NAME_TASK_FLOWS}' ya existe.", flush=True)
        sys.stdout.flush()

def get_embedding(text: str):
    """
    Genera el embedding para un texto dado.
    """
    try:
        return embedding_model.encode(text).tolist()
    except Exception as e:
        print(f"ERROR: Fallo al obtener embedding para el texto '{text}': {e}", flush=True)
        traceback.print_exc() # Añadido para más detalles
        sys.stdout.flush()
        return []

def add_ui_element(description: str, element_type: str, image_path: str = None, ocr_text: str = None, metadata: dict = None) -> str | None:
    """
    Añade una descripción de elemento de UI a la colección de Qdrant.
    Ahora devuelve el ID del punto creado.
    """
    vector = get_embedding(description)
    if not vector: # Asegurarse de que el embedding se generó correctamente
        print(f"ERROR: No se pudo generar el vector de embedding para '{description}'. No se añadirá el elemento.", flush=True)
        return None

    payload = {
        "description": description,
        "type": element_type,
        "timestamp": datetime.now().isoformat()
    }
    # Solo añade image_path si es proporcionado, podría ser una ruta temporal inicialmente
    if image_path:
        payload["image_path"] = image_path
    if ocr_text:
        payload["ocr_text"] = ocr_text
    if metadata:
        payload.update(metadata)

    point_id = str(uuid.uuid4().hex) # Generamos el ID aquí

    # --- PRINTS DE DEPURACIÓN AÑADIDOS ---
    print(f"DEBUG QDRANT (add_ui_element): Intentando añadir punto con ID: {point_id}")
    print(f"DEBUG QDRANT (add_ui_element): Payload a enviar: {payload}")
    # ------------------------------------

    try:
        operation_info = client.upsert(
            collection_name=COLLECTION_NAME_UI_ELEMENTS,
            points=[
                models.PointStruct( # <-- models.PointStruct está bien
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ],
            wait=True # Esperar a que la operación se complete
        )
        if operation_info.status == models.UpdateStatus.COMPLETED: # <-- models.UpdateStatus está bien
            print(f"INFO: Elemento UI '{description}' añadido/actualizado en Qdrant con ID: {point_id}.", flush=True)
            sys.stdout.flush()

            # --- VERIFICACIÓN INMEDIATA DESPUÉS DE LA INSERCIÓN ---
            try:
                retrieved_point = client.retrieve(
                    collection_name=COLLECTION_NAME_UI_ELEMENTS,
                    ids=[point_id],
                    with_payload=True
                )
                if retrieved_point:
                    # CAMBIO AQUI: retrieve devuelve una lista, necesitamos el primer elemento
                    if isinstance(retrieved_point, list) and len(retrieved_point) > 0:
                        print(f"DEBUG QDRANT (add_ui_element): ¡Elemento {point_id} RECUPERADO exitosamente justo después de insertarlo! Payload: {retrieved_point[0].payload}")
                    else:
                        print(f"WARNING QDRANT (add_ui_element): ¡No se pudo recuperar el elemento {point_id} justo después de insertarlo o la respuesta no es una lista válida!")
                else:
                    print(f"WARNING QDRANT (add_ui_element): ¡No se pudo recuperar el elemento {point_id} justo después de insertarlo!")
            except Exception as retrieve_e:
                print(f"ERROR QDRANT (add_ui_element): Fallo al intentar recuperar por ID {point_id} inmediatamente: {retrieve_e}")
            # ----------------------------------------------------

            return point_id
        else:
            print(f"WARNING: No se pudo añadir/actualizar el elemento UI '{description}'. Estado: {operation_info.status}", flush=True)
            sys.stdout.flush()
            return None
    except Exception as e:
        print(f"ERROR: Fallo al añadir elemento UI '{description}' en Qdrant: {e}", flush=True)
        traceback.print_exc() # Añadido para más detalles
        sys.stdout.flush()
        return None

def search_ui_element(query_text: str, limit: int = 3, score_threshold: float = 0.3, filters: dict = None):
    """
    Busca elementos de UI similares a la consulta, con filtros opcionales.
    Retorna los payloads de los elementos encontrados.
    """
    try:
        query_vector = get_embedding(query_text)
        if not query_vector:
            print("ERROR: No se pudo generar embedding para la consulta de busqueda.", flush=True)
            sys.stdout.flush()
            return []

        # Construir el filtro si se proporciona
        query_filter = None
        if filters:
            must_clauses = []
            for key, value in filters.items():
                # CAMBIO AQUI: Usar FieldCondition y MatchValue de qdrant_client.http.models
                must_clauses.append(models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value)
                ))
            query_filter = models.Filter(must=must_clauses) # <-- CAMBIO AQUI: models.Filter
            print(f"DEBUG QDRANT (search_ui_element): Aplicando filtro: {filters}", flush=True)


        # CAMBIO AQUI: Usar client.query_points en lugar de client.search (deprecated)
        # La estructura de argumentos es ligeramente diferente
        search_result = client.query_points(
            collection_name=COLLECTION_NAME_UI_ELEMENTS,
            vector=query_vector, # vector en lugar de query_vector
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter, # Añadido el filtro
            with_payload=True,
            with_vectors=False
        )
        return [hit.payload for hit in search_result]
    except Exception as e:
        print(f"ERROR: Fallo al buscar elementos UI en Qdrant: {e}", flush=True)
        traceback.print_exc() # Añadido para más detalles
        sys.stdout.flush()
        return []

def update_ui_element_payload(point_id: str, new_payload_data: dict) -> bool:
    """
    Actualiza campos específicos del payload de un punto de UI existente en Qdrant.
    Devuelve True si la actualización fue exitosa, False en caso contrario.
    """
    if not point_id:
        print("ERROR: update_ui_element_payload requiere un point_id válido.", flush=True)
        return False

    # --- PRINTS DE DEPURACIÓN AÑADIDOS ---
    print(f"DEBUG QDRANT (update_ui_element_payload): Intentando actualizar payload para ID: {point_id}")
    print(f"DEBUG QDRANT (update_ui_element_payload): Nuevos datos de payload: {new_payload_data}")
    # ------------------------------------

    try:
        operation_info = client.set_payload(
            collection_name=COLLECTION_NAME_UI_ELEMENTS,
            points=[point_id],
            payload=new_payload_data,
            wait=True
        )
        if operation_info.status == models.UpdateStatus.COMPLETED: # <-- models.UpdateStatus está bien
            print(f"INFO: Payload actualizado para el elemento UI con ID '{point_id}'.", flush=True)
            sys.stdout.flush()
            return True
        print(f"WARNING: No se pudo actualizar el payload para el elemento UI con ID '{point_id}'. Estado: {operation_info.status}", flush=True)
        sys.stdout.flush()
        return False
    except Exception as e:
        print(f"ERROR: Fallo al actualizar payload para el elemento UI con ID '{point_id}': {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        return False


def add_task_flow(task_description: str, steps: list, metadata: dict = None):
    """
    Añade un flujo de tarea a la colección de Qdrant.
    Los pasos se almacenan como parte del payload.
    """
    vector = get_embedding(task_description)
    if not vector:
        print(f"ERROR: No se pudo generar el vector de embedding para la tarea '{task_description}'. No se añadirá el flujo.", flush=True)
        return None

    payload = {
        "task_description": task_description,
        "steps": steps,
        "timestamp": datetime.now().isoformat()
    }
    if metadata:
        payload.update(metadata)

    point_id = str(uuid.uuid4().hex)

    try:
        operation_info = client.upsert( # Usamos el cliente global
            collection_name=COLLECTION_NAME_TASK_FLOWS,
            points=[
                models.PointStruct( # <-- models.PointStruct está bien
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ],
            wait=True
        )
        if operation_info.status == models.UpdateStatus.COMPLETED: # <-- models.UpdateStatus está bien
            print(f"INFO: Flujo de tarea '{task_description}' añadido/actualizado en Qdrant con ID: {point_id}.", flush=True)
            sys.stdout.flush()
            return point_id # Devuelve el ID también para flujos
        else:
            print(f"WARNING: No se pudo añadir/actualizar el flujo de tarea '{task_description}'. Estado: {operation_info.status}", flush=True)
            sys.stdout.flush()
            return None
    except Exception as e:
        print(f"ERROR: Fallo al añadir flujo de tarea '{task_description}' en Qdrant: {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        return None


def search_task_flow(query_text: str, limit: int = 1, score_threshold: float = 0.6):
    """
    Busca flujos de tarea similares a la consulta.
    Retorna los payloads de los flujos encontrados.
    """
    try:
        query_vector = get_embedding(query_text)
        if not query_vector:
            print("ERROR: No se pudo generar embedding para la consulta de busqueda.", flush=True)
            sys.stdout.flush()
            return []

        # CAMBIO AQUI: Usar client.query_points en lugar de client.search (deprecated)
        search_result = client.query_points( # Usamos el cliente global
            collection_name=COLLECTION_NAME_TASK_FLOWS,
            query_embedding=query_vector, # query_embedding en lugar de query_vector
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True, # Asegurarse de que el payload es devuelto
            with_vectors=False # No necesitamos los vectores en la busqueda
        )
        return [hit.payload for hit in search_result]
    except Exception as e:
        print(f"ERROR: Fallo al buscar flujos de tarea en Qdrant: {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        return []

# El bloque __main__ ya está correctamente adaptado a funciones globales
if __name__ == "__main__":
    print("--- Inicializando Knowledge Manager ---", flush=True)
    sys.stdout.flush()
    create_collections()

    print("\n--- Añadiendo elementos de UI de ejemplo ---", flush=True)
    sys.stdout.flush()
    
    # <--- Ejemplo de cómo se llamaría ahora y se capturaría el ID --->
    point_id_ejemplo_1 = add_ui_element("icono de inicio de Windows", "icono", metadata={"os": "Windows XP"})
    if point_id_ejemplo_1:
        print(f"ID del icono de inicio de Windows: {point_id_ejemplo_1}", flush=True)
        # Ejemplo de actualización (simulando que la imagen se copia y ahora tienes la ruta permanente)
        simulated_permanent_path = f"/path/to/qdrant_ui_cache/{point_id_ejemplo_1}.png"
        update_ui_element_payload(point_id_ejemplo_1, {"image_path": simulated_permanent_path})

    point_id_ejemplo_2 = add_ui_element("botón de aceptar", "botón")
    if point_id_ejemplo_2:
        print(f"ID del botón de aceptar: {point_id_ejemplo_2}", flush=True)

    point_id_ejemplo_3 = add_ui_element("pestaña de configuración", "pestaña")
    if point_id_ejemplo_3:
        print(f"ID de la pestaña de configuración: {point_id_ejemplo_3}", flush=True)

    add_ui_element("campo de texto para URL", "campo_entrada")
    add_ui_element("icono de MicroWin", "icono", metadata={"app": "MicroWin", "color": "azul", "forma": "engranaje"})


    print("\n--- Buscando elementos de UI ---", flush=True)
    sys.stdout.flush()
    results_ui = search_ui_element("botón para confirmar")
    if results_ui:
        print(f"Encontrado (UI): {results_ui[0]['description']} (Tipo: {results_ui[0]['type']})", flush=True)
        if 'image_path' in results_ui[0]:
            print(f"Ruta de imagen: {results_ui[0]['image_path']}", flush=True)
    else:
        print("No se encontró un elemento UI similar.", flush=True)
    sys.stdout.flush()

    results_ui_2 = search_ui_element("icono para iniciar el sistema")
    if results_ui_2:
        print(f"Encontrado (UI): {results_ui_2[0]['description']} (Tipo: {results_ui_2[0]['type']})", flush=True)
        if 'image_path' in results_ui_2[0]:
            print(f"Ruta de imagen: {results_ui_2[0]['image_path']}", flush=True)
    else:
        print("No se encontró un elemento UI similar.", flush=True)
    sys.stdout.flush()

    results_ui_3 = search_ui_element("icono del programa PLC")
    if results_ui_3:
        print(f"Encontrado (UI): {results_ui_3[0]['description']} (Tipo: {results_ui_3[0]['type']})", flush=True)
        if 'image_path' in results_ui_3[0]:
            print(f"Ruta de imagen: {results_ui_3[0]['image_path']}", flush=True)
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
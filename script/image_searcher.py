import os
from qdrant_client import QdrantClient, models
import google.generativeai as genai


# --- 1. Configuración inicial ---
# Reemplaza con tus propias credenciales y configuraciones
QDRANT_URL = os.getenv("QDRANT_URL") 
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configura la API de Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Configura el cliente de Qdrant
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

VECTOR_SIZE = 768

# --- 2. Generar embedding para la consulta de búsqueda ---
def generate_query_embedding(query_text):
    try:
        response_embedding = genai.embed_content(
            model="models/embedding-001",
            content=query_text,
            task_type="RETRIEVAL_QUERY"
        )
        return response_embedding['embedding']
    except Exception as e:
        print(f"Error al generar el embedding para la consulta: {e}")
        return None

# --- 3. Realizar la búsqueda en Qdrant ---
def search_images_in_qdrant(query_embedding, limit=5):
    if not query_embedding:
        return []

    search_result = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=limit,
        with_payload=True # Seguimos necesitando el payload para obtener la ruta
    )
    return search_result

# --- 4. Mostrar resultados (solo ruta) ---
def display_search_results(results):
    if not results:
        print("\nNo se encontraron resultados para tu consulta.")
        return None

    for hit in results:
        image_full_path = hit.payload.get('image_path', 'N/A')
        if image_full_path != 'N/A':
            print(image_full_path)
            return image_full_path
    return None


# --- 5. Proceso principal de búsqueda ---
def main_qdrant(descripcion_elemento):
    query_embedding = generate_query_embedding(descripcion_elemento)
    search_results = search_images_in_qdrant(query_embedding, limit=3)
    ruta_encontrada = display_search_results(search_results)
    return ruta_encontrada


if __name__ == "__main__":
    descripcion_elemento = "TIA Portal V15"
    captura = main_qdrant(descripcion_elemento)
    print(captura)



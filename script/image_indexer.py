import os
from PIL import Image
from qdrant_client import QdrantClient, models
import google.generativeai as genai
import time # Para manejar límites de tasa si es necesario
from dotenv import load_dotenv

load_dotenv()

# --- 1. Configuración inicial ---
QDRANT_URL = os.getenv("QDRANT_URL") 
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configura la API de Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash') # Modelo optimizado para imágenes

# Configura el cliente de Qdrant
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

VECTOR_SIZE = 768

# --- 2. Cargar imágenes ---
def load_images_from_folder(folder_path):
    image_paths = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_paths.append(os.path.join(folder_path, filename))
    print(f"Encontradas {len(image_paths)} imágenes en '{folder_path}'")
    return image_paths

# --- 3. Generar descripción y embeddings con Gemini ---
def generate_description_and_embedding(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        
        # Generar descripción
        prompt_description = "Describe esta imagen de forma concisa y detallada, resaltando los objetos principales y el contexto."
        response_description = gemini_model.generate_content([prompt_description, img])
        description = response_description.text.strip()

        # Generar embedding del texto de la descripción
        response_embedding = genai.embed_content(
            model="models/embedding-001", # Modelo de embedding para texto
            content=description,
            task_type="RETRIEVAL_DOCUMENT" # Tipo de tarea para embeddings de documentos
        )
        embedding = response_embedding['embedding']
        
        return description, embedding

    except Exception as e:
        print(f"Error al procesar la imagen {image_path}: {e}")
        return None, None

# --- 4. Conectar y gestionar Qdrant ---
def setup_qdrant_collection():
    if not qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )
        print(f"Colección '{COLLECTION_NAME}' creada.")
    else:
        print(f"Colección '{COLLECTION_NAME}' ya existe.")

def upsert_image_data_to_qdrant(image_path, description, embedding):
    point_id = abs(hash(image_path)) # Usar un hash de la ruta como ID único

    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        wait=True,
        points=[
            models.PointStruct(
                id=point_id,
                vector=embedding,
                payload={"image_path": image_path, "description": description},
            )
        ]
    )
    print(f"Datos de la imagen '{os.path.basename(image_path)}' guardados en Qdrant.")

# --- 5. Proceso principal ---
def main(image_folder_path):
    # 1. Configurar la colección de Qdrant
    setup_qdrant_collection()

    # 2. Cargar las rutas de las imágenes
    image_paths = load_images_from_folder(image_folder_path)

    # 3. Procesar cada imagen
    for image_path in image_paths:
        description, embedding = generate_description_and_embedding(image_path)
        
        if description and embedding:
            upsert_image_data_to_qdrant(image_path, description, embedding)
        
        # Pequeña pausa para evitar exceder los límites de tasa de las APIs
        time.sleep(1) 

    print("\n¡Proceso completado! Las imágenes y sus descripciones con embeddings se han guardado en Qdrant.")
    print(f"Total de puntos en la colección '{COLLECTION_NAME}': {qdrant_client.count(collection_name=COLLECTION_NAME, exact=True).count}")


if __name__ == "__main__":
    # Define la carpeta donde están tus imágenes
    images_directory = "../capture" 
    os.makedirs(images_directory, exist_ok=True) # Crea la carpeta si no existe

    main(images_directory)
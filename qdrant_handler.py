import os
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "windows_ui_elements"
# VECTOR_DIMENSION = 384 # Ya no es una variable global aquí, será un atributo de instancia

class QdrantHandler:
    def __init__(self):
        if not QDRANT_HOST or not QDRANT_API_KEY:
            raise ValueError("QDRANT_HOST y QDRANT_API_KEY deben estar configurados en el archivo .env")
        
        self.VECTOR_DIMENSION = 384 # <-- ¡Añade esta línea! Hazlo un atributo de la instancia
        self.COLLECTION_NAME = COLLECTION_NAME # También es buena práctica si la usas en otros métodos de la clase
                                             # O si COLLECTION_NAME no fuera global en este módulo.

        self.client = QdrantClient(
            host=QDRANT_HOST,
            api_key=QDRANT_API_KEY,
        )
        self._ensure_collection_exists()
        print(f"QdrantHandler inicializado para la colección: {self.COLLECTION_NAME}")

    def _ensure_collection_exists(self):
        try:
            # Usa self.COLLECTION_NAME y self.VECTOR_DIMENSION aquí
            self.client.get_collection(collection_name=self.COLLECTION_NAME)
        except Exception:
            print(f"Colección '{self.COLLECTION_NAME}' no existe. Creándola...")
            self.client.recreate_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(size=self.VECTOR_DIMENSION, distance=models.Distance.COSINE),
            )
            print(f"Colección '{self.COLLECTION_NAME}' creada con éxito.")

    def upsert_point(self, point_id: str, vector: list, payload: dict):
        try:
            self.client.upsert(
                collection_name=self.COLLECTION_NAME, # Usa self.COLLECTION_NAME
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
                wait=True
            )
            print(f"Punto ID '{point_id}' insertado/actualizado en Qdrant.")
            return True
        except Exception as e:
            print(f"Error al insertar punto '{point_id}' en Qdrant: {e}")
            return False

    def search_points(self, query_vector: list, limit: int = 5):
        try:
            search_result = self.client.search(
                collection_name=self.COLLECTION_NAME, # Usa self.COLLECTION_NAME
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            print(f"Búsqueda en Qdrant completada. Resultados encontrados: {len(search_result)}")
            return search_result
        except Exception as e:
            print(f"Error al buscar en Qdrant: {e}")
            return []

# Ejemplo de uso (solo para pruebas directas de este módulo)
if __name__ == "__main__":
    print("--- Probando QdrantHandler ---")
    try:
        qdrant_handler = QdrantHandler()
        # Para probar la inserción, necesitarías un vector y un payload.
        # Esto es solo un ejemplo simulado:
        # test_id = "test_point_123"
        # test_vector = [0.1] * VECTOR_DIMENSION # Vector de prueba
        # test_payload = {"name": "Test Item", "category": "Button"}
        # qdrant_handler.upsert_point(test_id, test_vector, test_payload)

        # Para probar la búsqueda, necesitarías un vector de consulta.
        # query_vec = [0.2] * VECTOR_DIMENSION # Vector de consulta de prueba
        # results = qdrant_handler.search_points(query_vec)
        # for hit in results:
        #     print(f"ID: {hit.id}, Score: {hit.score}, Payload: {hit.payload}")

    except ValueError as ve:
        print(f"Error de configuración: {ve}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
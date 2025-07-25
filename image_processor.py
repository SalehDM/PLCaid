import os
from PIL import Image
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from openai import OpenAI # Importa el cliente de OpenAI
import base64 # Para codificar la imagen en base64

# Cargar variables de entorno
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Usamos la API Key de OpenAI

class ImageProcessor:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY debe estar configurado en el archivo .env")
        
        # Inicializa el cliente de OpenAI
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Modelo GPT-4o es el más capaz para visión. GPT-4-turbo-preview también es una opción.
        self.vision_model = "gpt-4o" 
        # Si prefieres una opción más económica para el desarrollo y tienes acceso, podrías probar "gpt-4-turbo" (o "gpt-4-turbo-2024-04-09")
        # o incluso "gpt-3.5-turbo" si solo necesitas descripciones de texto y no usas la imagen directamente en la prompt con el modelo.
        # PERO para describir IMÁGENES, NECESITAS un modelo con capacidad de visión, como gpt-4o o gpt-4-turbo con la API de visión.

        # Cargar el modelo de Sentence Transformer para embeddings de 384 dimensiones
        # Mantenemos este modelo para embeddings para consistencia con Qdrant
        try:
            self.sentence_transformer_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Modelo 'all-MiniLM-L6-v2' cargado para embeddings.")
        except Exception as e:
            print(f"Error al cargar el modelo 'all-MiniLM-L6-v2': {e}")
            print("Asegúrate de tener conexión a internet o de haber descargado el modelo previamente.")
            self.sentence_transformer_model = None

    def _encode_image_to_base64(self, image_path: str):
        """
        Codifica una imagen en formato base64.
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def describe_image_with_ai(self, image_path: str): # Renombrada para ser más genérica
        """
        Genera una descripción detallada, palabras clave y clasificación de tipo de elemento
        para una imagen usando OpenAI GPT-4o (o similar con visión).
        Args:
            image_path (str): Ruta al archivo de imagen.
        Returns:
            tuple: (description: str, keywords: list, element_type: str)
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"La imagen no se encontró en: {image_path}")
                
            # Codificar la imagen para la API de OpenAI
            base64_image = self._encode_image_to_base64(image_path)
            
            prompt_content = (
                "Eres un experto en interfaces de usuario. Describe la siguiente imagen con gran detalle, "
                "identificando si es un icono, una pestaña, un campo de texto, un desplegable, un botón, un enlace, una barra de desplazamiento, un menú, una ventana, una sección de fondo, etc. "
                "Incluye su propósito, texto visible, colores, forma, y cualquier otro detalle relevante para identificarlo y clasificarlo. "
                "Genera también una lista de palabras clave relevantes para la búsqueda y clasificación, separadas por comas. "
                "Finalmente, clasifica el tipo de elemento de UI utilizando una de estas categorías: 'icono', 'pestaña', 'campo_texto', 'boton', 'desplegable', 'enlace', 'barra_desplazamiento', 'menu', 'ventana', 'fondo', 'otro'."
                "\n\nFormato de salida esperado:\n"
                "Descripción: [Descripción detallada aquí]\n"
                "Palabras clave: [palabra1, palabra2, ...]\n"
                "Tipo de elemento: [Tipo de elemento de UI]"
            )
            
            # Llamada a la API de OpenAI
            response = self.openai_client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_content},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                        ],
                    }
                ],
                max_tokens=500, # Ajusta según la longitud esperada de la descripción
            )
            
            text_response = response.choices[0].message.content.strip()
            print(f"Respuesta cruda de OpenAI:\n{text_response}\n---")
            
            description = ""
            keywords = []
            element_type = "otro"

            # Parsear la respuesta
            lines = text_response.split('\n')
            for line in lines:
                if line.startswith("Descripción:"):
                    description = line.replace("Descripción:", "").strip()
                elif line.startswith("Palabras clave:"):
                    keywords = [k.strip() for k in line.replace("Palabras clave:", "").strip().split(',') if k.strip()]
                elif line.startswith("Tipo de elemento:"):
                    element_type = line.replace("Tipo de elemento:", "").strip().lower()
            
            print(f"Descripción extraída: {description}")
            print(f"Palabras clave extraídas: {keywords}")
            print(f"Tipo de elemento extraído: {element_type}")
            
            return description, keywords, element_type
        except FileNotFoundError as fnfe:
            print(f"Error: {fnfe}")
            return "", [], "otro"
        except Exception as e:
            print(f"Error al describir la imagen con OpenAI: {e}")
            # Puedes añadir aquí manejo de errores específico para OpenAI, como RateLimitError
            return "", [], "otro"

    def generate_embedding_from_text(self, text: str):
        """
        Genera un embedding de texto de 384 dimensiones utilizando 'all-MiniLM-L6-v2'.
        Args:
            text (str): El texto para generar el embedding.
        Returns:
            list: El vector de embedding como una lista de floats.
        Raises:
            RuntimeError: Si el modelo de Sentence Transformer no se cargó correctamente.
        """
        if self.sentence_transformer_model is None:
            raise RuntimeError("El modelo de Sentence Transformer no se cargó correctamente. No se pueden generar embeddings.")
        
        try:
            embedding = self.sentence_transformer_model.encode(text).tolist()
            if len(embedding) != 384:
                raise ValueError(f"El embedding generado no tiene la dimensión esperada (384), sino {len(embedding)}")
            return embedding
        except Exception as e:
            print(f"Error al generar embedding de texto: {e}")
            return [0.0] * 384 

# Ejemplo de uso (para pruebas directas de este módulo)
if __name__ == "__main__":
    print("--- Probando ImageProcessor (image_processor.py) con OpenAI ---")
    processor = ImageProcessor()

    test_clipping_path = "papelera_reciclaje.png" # <--- ASEGÚRATE DE TENER ESTE ARCHIVO (recorte UI real)

    if os.path.exists(test_clipping_path):
        print(f"\nProcesando imagen: {test_clipping_path}")
        description, keywords, element_type = processor.describe_image_with_ai(test_clipping_path)
        print("\nResultado de la IA (OpenAI):")
        print(f"  Descripción: {description}")
        print(f"  Palabras clave: {keywords}")
        print(f"  Tipo de elemento: {element_type}")

        if description:
            try:
                embedding = processor.generate_embedding_from_text(description)
                print(f"  Embedding generado (primeros 5 valores): {embedding[:5]}...")
                print(f"  Longitud del embedding: {len(embedding)}")
            except RuntimeError as re:
                print(f"Error al generar embedding: {re}")
        else:
            print("No se generó descripción, no se puede crear embedding.")
    else:
        print(f"\n¡ATENCIÓN! El archivo '{test_clipping_path}' no se encontró.")
        print("Crea un recorte de una parte de tu UI y guárdalo con ese nombre para probar este módulo.")
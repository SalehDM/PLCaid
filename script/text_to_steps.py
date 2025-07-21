import os
import sys
import json
import argparse
from dotenv import load_dotenv
from openai import OpenAI
from openai import OpenAIError # Import specific OpenAI error for better catching

# --- Configurar la codificación de la salida de la consola al inicio ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    # reconfigure no está disponible en todas las versions de Python o entornos
    pass
except Exception as e:
    print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}", flush=True)

# ==== CARGAR API KEY ====
load_dotenv()
OPENAI_API_KEY = os.getenv("API_KEY") # Usar la variable de entorno para OpenAI

if not OPENAI_API_KEY:
    print("ERROR: La variable de entorno API_KEY (para OpenAI) no esta configurada. Por favor, configurala en tu archivo .env", flush=True)
    sys.exit(1)

client = None # Initialize client to None
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Opcional: Puedes añadir una pequeña prueba de conexión aquí si quieres,
    # pero ten cuidado con los límites de tasa y el tiempo de respuesta.
    # Por ejemplo: client.models.list()
except OpenAIError as e:
    print(f"ERROR: Error al inicializar el cliente de OpenAI o al conectar con la API: {e}", flush=True)
    sys.stdout.flush() # Asegurar que el error se imprima antes de salir
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Error inesperado al inicializar el cliente de OpenAI: {e}", flush=True)
    sys.stdout.flush() # Asegurar que el error se imprima antes de salir
    sys.exit(1)

def generate_steps_from_instruction(instruction):
    """
    Genera una lista de pasos de automatización a partir de una instrucción dada,
    utilizando un modelo de lenguaje.
    """
    # Construye el prompt para el modelo de lenguaje
    # Se ha añadido una guía explícita sobre cómo manejar instrucciones de prueba o declaraciones.
    prompt = f"""
    Eres un asistente de automatización de interfaz de usuario. Tu tarea es generar una lista de pasos detallados para automatizar una tarea dada una instrucción.
    Cada paso debe ser una acción clara y concisa que se pueda ejecutar en una interfaz de usuario.
    La respuesta DEBE ser un objeto JSON con una única clave "steps", cuyo valor es un array de objetos de paso, siguiendo este esquema:
    {{
      "steps": [
        {{ "step": INTEGER, "action": "STRING" }},
        {{ "step": INTEGER, "action": "STRING" }},
        ...
      ]
    }}

    **Reglas importantes:**
    1. Si la instrucción es una simple declaración, una prueba, un saludo, o no implica una serie de acciones de automatización complejas,
       genera UN ÚNICO paso que refleje la intención de la instrucción o un paso simple de reconocimiento.
    2. No intentes inferir acciones de interfaz de usuario para instrucciones que no las implican directamente.
    3. Para acciones de "búsqueda", usa "busca el icono de 'X'", "busca el botón de 'Y'", "busca la pestaña de 'Z'", "busca el campo de entrada de 'W'".
    4. Para acciones de "clic", usa "haz clic en el icono de 'X'", "haz clic en el botón de 'Y'", etc.
    5. Para escribir, usa "escribe 'texto a escribir'".
    6. Para presionar una tecla, usa "presiona 'tecla'".
    7. Para esperar, usa "espera X segundos" o "espera a que se abra la ventana 'Nombre de la ventana'".

    **Ejemplos:**
    - Instrucción: "abre la aplicación MicroWin"
      Respuesta JSON esperada:
      {{
        "steps": [
          {{ "step": 1, "action": "busca el icono de 'Inicio'" }},
          {{ "step": 2, "action": "haz clic en el icono de 'Inicio'" }},
          {{ "step": 3, "action": "espera a que se abra el menú de 'Inicio'" }},
          {{ "step": 4, "action": "busca el icono de 'MicroWin'" }},
          {{ "step": 5, "action": "haz clic en el icono de 'MicroWin'" }},
          {{ "step": 6, "action": "espera a que se abra la aplicación MicroWin" }}
        ]
      }}

    - Instrucción: "probando la nueva configuración del audio"
      Respuesta JSON esperada:
      {{
        "steps": [
          {{ "step": 1, "action": "reconoce que la instrucción es una prueba de audio" }}
        ]
      }}

    - Instrucción: "Hola"
      Respuesta JSON esperada:
      {{
        "steps": [
          {{ "step": 1, "action": "saluda al usuario" }}
        ]
      }}

    - Instrucción: "Cierra la ventana actual"
      Respuesta JSON esperada:
      {{
        "steps": [
          {{ "step": 1, "action": "presiona 'alt+f4'" }}
        ]
      }}

    Instrucción: "{instruction}"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # O el modelo de OpenAI que prefieras
            messages=[
                {"role": "system", "content": "Genera pasos de automatizacion en formato JSON. La respuesta debe ser un objeto JSON con una clave 'steps' que contiene una lista de objetos de paso."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}, # Solicitar respuesta en formato JSON de nivel superior
            temperature=0.2,
            max_tokens=500
        )
        
        json_response_str = response.choices[0].message.content
        
        print(f"DEBUG: Raw JSON response from model: {json_response_str}", flush=True)
        sys.stdout.flush() # Ensure this debug print is flushed

        parsed_json = json.loads(json_response_str)

        # Validar y extraer la lista de pasos de la clave "steps"
        if isinstance(parsed_json, dict) and "steps" in parsed_json and \
           isinstance(parsed_json["steps"], list) and \
           all(isinstance(item, dict) for item in parsed_json["steps"]):
            return parsed_json["steps"]
        else:
            print(f"ERROR: El modelo no devolvio un objeto JSON con la clave 'steps' conteniendo una lista de objetos. Tipo recibido: {type(parsed_json)}", flush=True)
            sys.stdout.flush()
            return []

    except json.JSONDecodeError as e:
        print(f"ERROR: Error al parsear la respuesta JSON del modelo: {e}", flush=True)
        print(f"DEBUG: JSON string que causo el error: {json_response_str}", flush=True)
        sys.stdout.flush()
        return []
    except Exception as e:
        print(f"ERROR: Error al generar pasos con el modelo de lenguaje: {e}", flush=True)
        print(f"Detalles de la respuesta (si existe): {getattr(e, 'response', 'No response attribute')}", flush=True)
        sys.stdout.flush()
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera pasos de automatizacion a partir de una instruccion de texto.")
    parser.add_argument("--input", required=True, help="Ruta al archivo de texto con la instruccion.")
    parser.add_argument("--output", required=True, help="Ruta al archivo JSON donde se guardaran los pasos generados.")
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output

    if not os.path.exists(input_path):
        print(f"ERROR: El archivo de entrada no existe: {input_path}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        instruction = f.read().strip()

    print("[INFO] Generando pasos...", flush=True)
    sys.stdout.flush()
    steps = generate_steps_from_instruction(instruction)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(steps, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Pasos guardados en {output_path}", flush=True)
    sys.stdout.flush()

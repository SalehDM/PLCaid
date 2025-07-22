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
  # Se ha añadido una guía explícita sobre cómo manejar instrucciones de prueba o declaraciones,
  # y se han refinado las acciones y ejemplos para mayor claridad y consistencia.
  prompt = f"""
  Eres un asistente experto en **automatización de interfaces gráficas (GUI)**, especializado en entornos de **sistemas PLC** y aplicaciones relacionadas.
  Tu objetivo es transformar una instrucción de usuario en una secuencia de pasos atómicos y ejecutables para la automatización.
  Cada paso debe describir una acción clara sobre un elemento de la interfaz de usuario o una operación de sistema, enfocada en la interacción directa con la GUI.

  La respuesta **DEBE** ser un objeto JSON con una única clave "steps", cuyo valor es un array de objetos de paso. El formato estricto es:
  {{{{
    "steps": [
      {{{{ "step": INTEGER, "action": "STRING" }}}},
      {{{{ "step": INTEGER, "action": "STRING" }}}},
      // ...
    ]
  }}}}

  ---
  **Reglas y Formato de Acciones:**

  1.  **Prioriza la interacción con elementos de la GUI.** Piensa en términos de "buscar", "hacer clic", "escribir", "seleccionar".
  2.  **Precisión en la Identificación de Elementos:** Al referirte a un elemento, sé lo más descriptivo posible. Usa "[tipo de elemento] de '[texto/nombre visible]'".
      * **Tipos de Elementos comunes:** `icono`, `botón`, `campo de texto`, `pestaña`, `ventana`, `menú desplegable`, `enlace`, `casilla de verificación`, `elemento de lista`, `área de texto`, `campo de número`, `control deslizante`.
  3.  **Lista de Acciones Atómicas y Ejecutables:** Utiliza **SOLO** las siguientes estructuras de acción. Si una instrucción no encaja, intenta simplificarla o recurre a la acción "instrucción no clara".

      * **Búsqueda:** `busca el [tipo de elemento] de '[texto/nombre del elemento]'`
          * Ej: "busca el icono de 'Inicio'", "busca el botón de 'Aceptar'", "busca el campo de texto de 'Nombre de usuario'"
      * **Clic:** `haz clic en el [tipo de elemento] de '[texto/nombre del elemento]'`
          * Ej: "haz clic en el botón de 'Cancelar'", "haz clic en el icono de 'Mi PC'"
      * **Doble Clic:** `haz doble clic en el [tipo de elemento] de '[texto/nombre del elemento]'`
          * Ej: "haz doble clic en el icono de 'Documentos'"
      * **Escribir:** `escribe '[texto a introducir]' en el [tipo de elemento] de '[texto/nombre del elemento]'`
          * Ej: "escribe 'mi_proyecto_final' en el campo de texto de 'Nombre del proyecto'", "escribe 'contraseña123' en el campo de texto de 'Contraseña'"
      * **Seleccionar (en listas/menús):** `selecciona '[opción deseada]' en el [tipo de elemento] de '[nombre del menú/lista]'`
          * Ej: "selecciona 'Configuración Avanzada' en el menú desplegable de 'Opciones'"
      * **Presionar Tecla/Combinación:** `presiona '[tecla]'` o `presiona '[tecla1]+[tecla2]'`
          * Ej: "presiona 'Enter'", "presiona 'Alt+F4'", "presiona 'Ctrl+S'"
      * **Esperar:** `espera a que se abra la [ventana/diálogo] '[Nombre de la ventana]'` o `espera X segundos`
          * Ej: "espera a que se abra la ventana 'Configuración'", "espera 5 segundos"
      * **Scroll:** `haz scroll [arriba/abajo/izquierda/derecha] en el [tipo de elemento] de '[texto/nombre del elemento]'`
          * Ej: "haz scroll abajo en el área de texto de 'Log'"
      * **Cierre genérico:** `cierra la ventana actual` (para casos como Alt+F4 si el modelo no lo infiere bien)

  4.  **Manejo de Instrucciones no Automatizables/Claras:**
      Si la instrucción es una simple declaración, una prueba, un saludo, una pregunta, o no implica una serie de acciones de automatización concretas sobre una GUI, genera **UN ÚNICO paso** utilizando una de las siguientes acciones genéricas:
      * `reconoce que la instrucción es una prueba de [tipo de prueba]` (ej. "prueba de audio", "prueba de configuración")
      * `saluda al usuario`
      * `la instrucción no implica una acción de automatización de GUI específica` (para instrucciones vagas o irrelevantes)
      * `solicita más detalles sobre la tarea a automatizar` (si la instrucción es ambigua pero podría ser automatizable con más info)

  ---
  **Ejemplos para el Modelo:**

  -   **Instrucción:** "abre la aplicación MicroWin"
      **Respuesta JSON esperada:**
      {{{{
        "steps": [
          {{{{ "step": 1, "action": "busca el icono de 'Inicio'" }}}},
          {{{{ "step": 2, "action": "haz clic en el icono de 'Inicio'" }}}},
          {{{{ "step": 3, "action": "espera a que se abra el menú de 'Inicio'" }}}},
          {{{{ "step": 4, "action": "busca el icono de 'MicroWin'" }}}},
          {{{{ "step": 5, "action": "haz clic en el icono de 'MicroWin'" }}}},
          {{{{ "step": 6, "action": "espera a que se abra la aplicación MicroWin" }}}}
        ]
      }}}}

  -   **Instrucción:** "Quiero crear un nuevo programa en STEP 7."
      **Respuesta JSON esperada:**
      {{{{
        "steps": [
          {{{{ "step": 1, "action": "busca el icono de 'Inicio'" }}}},
          {{{{ "step": 2, "action": "haz clic en el icono de 'Inicio'" }}}},
          {{{{ "step": 3, "action": "espera a que se abra el menú de 'Inicio'" }}}},
          {{{{ "step": 4, "action": "busca el icono de 'SIMATIC Manager'" }}}},
          {{{{ "step": 5, "action": "haz clic en el icono de 'SIMATIC Manager'" }}}},
          {{{{ "step": 6, "action": "espera a que se abra la ventana de 'SIMATIC Manager'" }}}},
          {{{{ "step": 7, "action": "haz clic en el menú de 'Archivo'" }}}},
          {{{{ "step": 8, "action": "selecciona 'Nuevo' en el menú" }}}},
          {{{{ "step": 9, "action": "espera a que se abra el cuadro de diálogo 'Nuevo Proyecto'" }}}},
          {{{{ "step": 10, "action": "escribe 'MiNuevoProyectoPLC' en el campo de texto de 'Nombre del Proyecto'" }}}},
          {{{{ "step": 11, "action": "haz clic en el botón de 'Crear'" }}}}
        ]
      }}}}

  -   **Instrucción:** "probando la nueva configuración del audio"
      **Respuesta JSON esperada:**
      {{{{
        "steps": [
          {{{{ "step": 1, "action": "reconoce que la instrucción es una prueba de audio" }}}}
        ]
      }}}}

  -   **Instrucción:** "Hola"
      **Respuesta JSON esperada:**
      {{{{
        "steps": [
          {{{{ "step": 1, "action": "saluda al usuario" }}}}
        ]
      }}}}

  -   **Instrucción:** "Cierra la ventana actual"
      **Respuesta JSON esperada:**
      {{{{
        "steps": [
          {{{{ "step": 1, "action": "presiona 'Alt+F4'" }}}}
        ]
      }}}}

  -   **Instrucción:** "Qué hora es?"
      **Respuesta JSON esperada:**
      {{{{
        "steps": [
          {{{{ "step": 1, "action": "la instrucción no implica una acción de automatización de GUI específica" }}}}
        ]
      }}}}

  ---
  **Instrucción del Usuario:** "{instruction}"
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

import subprocess
import os
import sys
import json
import time
import shutil # Necesario para shutil.copy




#import qdrant_client # Asegúrate de que esto se resuelva correctamente

# print(f"DEBUG_MAIN: Python executable used by main.py: {sys.executable}")
# print(f"DEBUG_MAIN: sys.path for main.py: {sys.path}")
# if 'qdrant_client' in sys.modules:
#     print(f"DEBUG_MAIN: qdrant_client.__file__ loaded by main.py: {qdrant_client.__file__}")
#     print(f"DEBUG_MAIN: qdrant_client version loaded by main.py: {qdrant_client.__version__}")
# else:
#     print("DEBUG_MAIN: qdrant_client not yet loaded by main.py directly.")

# # Asegúrate de que el directorio del proyecto esté en sys.path para importar knowledge_manager.py
# project_root = os.path.dirname(os.path.abspath(__file__))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)
# print(f"DEBUG_MAIN: Project root added to sys.path: {project_root}")







# --- Configurar la codificación de la salida de la consola al inicio ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    # reconfigure no está disponible en todas las versions de Python o entornos
    pass
except Exception as e:
    print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}", flush=True)
sys.stdout.flush() # Forzar el flush inicial

print("INFO: main.py iniciado.", flush=True)
sys.stdout.flush()

# Importar módulos esenciales
try:
    import knowledge_manager as km
    print("INFO: 'knowledge_manager.py' importado correctamente.", flush=True)
except ImportError:
    print("ERROR: No se pudo importar 'knowledge_manager.py'. Asegúrate de que esté en la misma carpeta o en la ruta de Python. Saliendo.", flush=True)
    sys.exit(1)

# Importar módulos de herramientas (google_search y generic_reminders) - pueden ser opcionales
try:
    import google_search
    print("INFO: 'google_search' importado correctamente.", flush=True)
except ImportError:
    print("WARNING: No se pudo importar 'google_search'. Las búsquedas en Google no funcionarán.", flush=True)
    google_search = None # Establecer a None para manejarlo más tarde

try:
    import generic_reminders
    print("INFO: 'generic_reminders' importado correctamente.", flush=True)
except ImportError:
    print("WARNING: No se pudo importar 'generic_reminders'. La gestión de recordatorios no funcionará.", flush=True)
    generic_reminders = None # Establecer a None para manejarlo más tarde


# --- Configuración de rutas ---
project_root = os.path.dirname(__file__) # La raíz del proyecto es la carpeta donde está main.py

TEXT_TO_STEPS_SCRIPT = os.path.join(project_root, 'script', 'text_to_steps.py')
PARSED_STEPS_FILE = os.path.join(project_root, 'parsed_steps', 'steps.json')
INPUT_ORDER_FILE = os.path.join(project_root, 'input_text', 'order.txt')
SCREENSHOT_SCRIPT = os.path.join(project_root, 'script', 'screenshot.py')
ANALIZAR_ICONOS_SCRIPT = os.path.join(project_root, 'recorte', 'analizar_iconos.py')
EXECUTE_ACTIONS_SCRIPT = os.path.join(project_root, 'script', 'execute_actions.py')

# Umbral de similitud para la búsqueda en Qdrant
QDRANT_UI_SEARCH_THRESHOLD = 0.7 # Ajusta este valor según la precisión deseada. Considerar 0.6 si es demasiado estricto.


def execute_command(command_list):
    """
    Ejecuta un comando de sistema y captura su salida.
    """
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'

    print(f"DEBUG: Ejecutando subproceso: {' '.join(command_list)}", flush=True)
    sys.stdout.flush()

    try:
        process = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        stdout_bytes, stderr_bytes = process.communicate()
        
        stdout_decoded = stdout_bytes.decode('utf-8', errors='replace')
        stderr_decoded = stderr_bytes.decode('utf-8', errors='replace')

        if process.returncode != 0:
            print(f"❌ Error al ejecutar comando: {' '.join(command_list)}", flush=True)
            print(f"Salida del subcomando (STDOUT): \n{stdout_decoded}", flush=True)
            if stderr_decoded:
                print(f"Errores del subcomando (STDERR): \n{stderr_decoded}", flush=True)
            sys.stdout.flush()
            raise subprocess.CalledProcessError(process.returncode, command_list, output=stdout_bytes, stderr=stderr_bytes)

        print(f"✅ Comando ejecutado: {' '.join(command_list)}", flush=True)
        print(f"Salida del subcomando: \n{stdout_decoded}", flush=True)
        if stderr_decoded:
            print(f"Errores del subcomando (STDERR): \n{stderr_decoded}", flush=True)
        sys.stdout.flush()
        return stdout_decoded
    except subprocess.CalledProcessError as e:
        error_output_decoded = e.stderr.decode('utf-8', errors='replace') if e.stderr else "No hay salida de error disponible."
        print(f"❌ Error al ejecutar comando: {' '.join(command_list)}", flush=True)
        print(f"Error del subcomando: \n{error_output_decoded}", flush=True)
        sys.stdout.flush()
        raise
    except FileNotFoundError:
        print(f"❌ Error: El comando o script no se encontró: {command_list[0]}", flush=True)
        sys.stdout.flush()
        raise
    except Exception as e:
        print(f"❌ Error inesperado en execute_command: {e}", flush=True)
        sys.stdout.flush()
        raise

# Función auxiliar para encapsular el flujo de análisis completo y clic
def _perform_full_analysis_and_click(element_description_query, add_to_knowledge=False, element_type=None, point_id=None):
    """
    Realiza la captura de pantalla, análisis de elementos UI con GPT-4o y el clic.
    Retorna True si la secuencia de análisis y clic fue exitosa, False en caso contrario.
    """
    print("📸 Tomando captura de pantalla...", flush=True)
    sys.stdout.flush()
    try:
        execute_command(["python", SCREENSHOT_SCRIPT])
    except Exception as e:
        print(f"❌ Fallo en la captura de pantalla: {e}. No se puede continuar con el análisis.", flush=True)
        sys.stdout.flush()
        return False # Indica que falló

    print(f"🔎 Analizando elementos UI para: '{element_description_query}'", flush=True)
    sys.stdout.flush()
    try:
        # Pasa el indicador add_to_knowledge y el element_type a analizar_iconos.py
        # para que pueda decidir si añadir o actualizar el elemento en Qdrant.
        command = ["python", ANALIZAR_ICONOS_SCRIPT, element_description_query]
        if add_to_knowledge:
            command.extend(["--add_to_knowledge", "true"])
        if element_type: # Solo si conocemos el tipo, para ayudar al script
            command.extend(["--element_type", element_type])
        if point_id: # Si estamos actualizando un elemento existente
            command.extend(["--point_id", str(point_id)]) # Convertir a string para el argparse

        execute_command(command)
    except Exception as e:
        print(f"❌ Fallo en el análisis de elementos UI: {e}. No se puede continuar con la acción de clic.", flush=True)
        sys.stdout.flush()
        return False # Indica que falló

    print("🎯 Ejecutando acción de clic en el elemento encontrado...", flush=True)
    sys.stdout.flush()
    try:
        execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"])
        return True # Indica éxito
    except Exception as e:
        print(f"❌ Fallo en la ejecución de la acción de clic: {e}", flush=True)
        sys.stdout.flush()
        return False # Indica que falló


def process_instruction(instruction: str):
    """
    Procesa la instrucción del usuario, la convierte en pasos
    y los ejecuta.
    """
    print(f"\n--- Procesando instrucción: '{instruction}' ---", flush=True)
    sys.stdout.flush()

    # 1. Guardar la instrucción en input_text/order.txt para text_to_steps.py
    os.makedirs(os.path.dirname(INPUT_ORDER_FILE), exist_ok=True)
    with open(INPUT_ORDER_FILE, "w", encoding="utf-8") as f:
        f.write(instruction)
    print(f"💾 Instrucción guardada en: {INPUT_ORDER_FILE}", flush=True)
    sys.stdout.flush()

    # 2. Convertir la instrucción en pasos usando text_to_steps.py
    print("\n[1] Generando pasos a partir de la instrucción...", flush=True)
    sys.stdout.flush()
    try:
        execute_command(["python", TEXT_TO_STEPS_SCRIPT, "--input", INPUT_ORDER_FILE, "--output", PARSED_STEPS_FILE])
    except Exception as e:
        print(f"❌ Fallo al generar pasos: {e}", flush=True)
        sys.stdout.flush()
        return

    # 3. Leer los pasos generados
    if not os.path.exists(PARSED_STEPS_FILE):
        print(f"❌ Error: No se generó el archivo de pasos: {PARSED_STEPS_FILE}", flush=True)
        sys.stdout.flush()
        return

    with open(PARSED_STEPS_FILE, "r", encoding="utf-8") as f:
        steps = json.load(f)
    print(f"📋 Pasos generados: {json.dumps(steps, indent=2, ensure_ascii=False)}", flush=True)
    sys.stdout.flush()

    # 4. Ejecutar cada paso
    print("\n--- Ejecutando pasos ---", flush=True)
    sys.stdout.flush()
    for step_data in steps:
        step_num = step_data.get("step")
        action = step_data.get("action", "").lower() # Convertir a minúsculas para facilitar el matching

        print(f"\n[Paso {step_num}] Acción: '{action}'", flush=True)
        sys.stdout.flush()

        # Identificar el tipo de elemento para una búsqueda/cacheo más preciso
        element_type = None
        if "icono de" in action:
            element_type = "icono"
        elif "botón de" in action:
            element_type = "boton" # Usar 'boton' para consistencia en Qdrant
        elif "pestaña de" in action:
            element_type = "pestaña"
        elif "campo de entrada de" in action:
            element_type = "campo_entrada"

        if action.startswith("busca el icono de") or \
            action.startswith("busca el botón de") or \
            action.startswith("busca la pestaña de") or \
            action.startswith("busca el campo de entrada de"):

            element_description_query = action.replace("busca el icono de", "").replace("busca el botón de", "").replace("busca la pestaña de", "").replace("busca el campo de entrada de", "").strip()
            if element_description_query.startswith("'") and element_description_query.endswith("'"):
                element_description_query = element_description_query[1:-1]

            print(f"INFO: Buscando elemento UI: '{element_description_query}' en Qdrant...", flush=True)
            sys.stdout.flush()

            # Incluir 'type' en el filtro de búsqueda para mayor precisión
            filters = {"type": element_type} if element_type else None
            found_elements = km.search_ui_element(element_description_query, limit=1, score_threshold=QDRANT_UI_SEARCH_THRESHOLD, filters=filters)

            cached_image_path = None
            cached_point_id = None 

            if found_elements and found_elements[0].get('image_path'):
                cached_element = found_elements[0]
                # Se asume que image_path en Qdrant es relativa a project_root
                cached_image_path = os.path.join(project_root, cached_element['image_path'])
                cached_point_id = cached_element.get('id')

                # Verificar si la imagen en caché realmente existe en el disco
                if os.path.exists(cached_image_path):
                    print(f"INFO: Elemento '{cached_element['description']}' encontrado en Qdrant (cache hit). Tipo: {cached_element['type']}", flush=True)
                    print(f"INFO: Usando imagen de referencia de caché: {cached_image_path}", flush=True)
                    sys.stdout.flush()
                    
                    try:
                        capture_dir = os.path.join(project_root, 'capture')
                        os.makedirs(capture_dir, exist_ok=True)
                        shutil.copy(cached_image_path, os.path.join(capture_dir, 'image.png'))
                        print("INFO: Imagen de caché copiada a 'capture/image.png'.", flush=True)
                        sys.stdout.flush()
                        
                        print("INFO: Ejecutando acción de clic en el elemento encontrado (desde caché)...", flush=True)
                        sys.stdout.flush()
                        execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"])
                        
                        # Si todo fue bien, no necesitamos el análisis completo. Pasamos al siguiente paso.
                        continue 
                    except Exception as e:
                        print(f"ERROR: Fallo al usar imagen de caché o ejecutar acción: {e}. Procediendo con análisis completo...", flush=True)
                        sys.stdout.flush()
                else:
                    print(f"WARNING: La imagen en caché en '{cached_image_path}' no existe en disco. Forzando análisis completo.", flush=True)
                    sys.stdout.flush()
            
            # CACHE MISS (o caché incompleto / imagen no encontrada en disco), proceder con el análisis completo
            print(f"INFO: Elemento '{element_description_query}' NO encontrado en Qdrant (cache miss) o sin ruta de imagen válida/existente. Recurriendo a análisis completo con GPT-4o.", flush=True)
            sys.stdout.flush()
            # Pasar add_to_knowledge=True para que analizar_iconos.py gestione el guardado/actualización.
            # También pasamos el element_type y el point_id si ya existía para que se actualice.
            _perform_full_analysis_and_click(element_description_query, add_to_knowledge=True, element_type=element_type, point_id=cached_point_id)

        elif action.startswith("haz clic en el icono de") or \
            action.startswith("haz clic en el botón de") or \
            action.startswith("haz clic en la pestaña de") or \
            action.startswith("haz clic en el campo de entrada de"):
            print("🎯 Intentando ejecutar acción de clic en el elemento previamente encontrado o implícito...", flush=True)
            sys.stdout.flush()
            try:
                execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"])
            except Exception as e:
                print(f"❌ Fallo en la ejecución de la acción de clic: {e}", flush=True)
                sys.stdout.flush()
                continue

        elif action.startswith("haz doble clic en el icono de") or \
            action.startswith("haz doble clic en el botón de"):
            print("⚠️ Acción de doble clic no implementada directamente en execute_actions.py aún. Se realizará un clic simple.", flush=True)
            sys.stdout.flush()
            try:
                execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"]) # Por ahora, solo un clic
            except Exception as e:
                print(f"❌ Fallo en la ejecución de la acción (doble clic): {e}", flush=True)
                sys.stdout.flush()
                continue

        elif action.startswith("haz clic derecho en"):
            print("⚠️ Acción de clic derecho no implementada directamente en execute_actions.py aún. Se realizará un clic simple.", flush=True)
            sys.stdout.flush()
            try:
                execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"]) # Por ahora, solo un clic
            except Exception as e:
                print(f"❌ Fallo en la ejecución de la acción (clic derecho): {e}", flush=True)
                sys.stdout.flush()
                continue

        elif action.startswith("escribe"):
            text_to_write = action.replace("escribe", "").strip().strip("'\"")
            print(f"⌨️ Escribiendo texto: '{text_to_write}'", flush=True)
            sys.stdout.flush()
            try:
                execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "write", text_to_write])
            except Exception as e:
                print(f"❌ Fallo al escribir texto: {e}", flush=True)
                sys.stdout.flush()
                continue

        elif action.startswith("presiona"):
            key_to_press = action.replace("presiona", "").strip().strip("'\"").lower()
            print(f"⬇️ Presionando tecla: '{key_to_press}'", flush=True)
            sys.stdout.flush()
            try:
                execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "press", key_to_press])
            except Exception as e:
                print(f"❌ Fallo al presionar tecla: {e}", flush=True)
                sys.stdout.flush()
                continue

        elif action.startswith("espera"):
            if "segundos" in action:
                try:
                    delay_str = action.split("espera")[1].split("segundos")[0].strip()
                    delay = float(delay_str)
                    print(f"⏳ Esperando {delay} segundos...", flush=True)
                    sys.stdout.flush()
                    time.sleep(delay)
                except ValueError:
                    print("⚠️ No se pudo parsear el tiempo de espera. Esperando 1 segundo por defecto.", flush=True)
                    sys.stdout.flush()
                    time.sleep(1)
            elif "a que se abra la ventana" in action:
                print("⏳ Esperando a que se abra la ventana... (simulado con 2 segundos)", flush=True)
                sys.stdout.flush()
                time.sleep(2) # Placeholder, en el futuro podría haber una detección de ventana
            else:
                print("⏳ Espera no especificada. Esperando 1 segundo por defecto.", flush=True)
                sys.stdout.flush()
                time.sleep(1)

        elif action.startswith("haz scroll en"):
            print("⚠️ Acción de scroll no implementada aún.", flush=True)
            sys.stdout.flush()
            time.sleep(1) # Pequeña pausa para simular

        elif action.startswith("selecciona"):
            print(f"⚠️ Acción de selección '{action}' no implementada aún.", flush=True)
            sys.stdout.flush()
            time.sleep(1) # Pequeña pausa para simular

        elif action.startswith("busca en google"):
            query = action.replace("busca en google", "").strip().strip("'\"")
            print(f"🌐 Realizando búsqueda en Google para: '{query}'", flush=True)
            sys.stdout.flush()
            if google_search:
                try:
                    search_results = google_search(queries=[query])
                    for result_set in search_results:
                        if result_set.results:
                            for res in result_set.results:
                                print(f"    Título: {res.source_title}", flush=True)
                                print(f"    Snippet: {res.snippet}", flush=True)
                                print(f"    URL: {res.url}", flush=True)
                                print("-" * 20, flush=True)
                        else:
                            print(f"    No se encontraron resultados para: {result_set.query}", flush=True)
                except Exception as e:
                    print(f"ERROR: Error al realizar búsqueda en Google: {e}", flush=True)
            else:
                print("ERROR: 'google_search' no está disponible. No se puede realizar la búsqueda.", flush=True)
            sys.stdout.flush()
            time.sleep(1)

        elif action.startswith("recuérdame"):
            reminder_text = action.replace("recuérdame", "").strip().strip("'\"")
            print(f"⏰ Creando recordatorio: '{reminder_text}'", flush=True)
            sys.stdout.flush()
            if generic_reminders:
                try:
                    generic_reminders.create_reminder(text=reminder_text)
                    print(f"INFO: Recordatorio creado: '{reminder_text}'", flush=True)
                except Exception as e:
                    print(f"ERROR: Error al crear recordatorio: {e}", flush=True)
            else:
                print("ERROR: 'generic_reminders' no está disponible. No se puede crear el recordatorio.", flush=True)
            sys.stdout.flush()
            time.sleep(1)

        elif action.startswith("muestra mis recordatorios"):
            print("📅 Mostrando recordatorios...", flush=True)
            sys.stdout.flush()
            if generic_reminders:
                try:
                    reminders = generic_reminders.show_matching_reminders()
                    if reminders:
                        print("INFO: Tus recordatorios:", flush=True)
                        for r in reminders:
                            print(f"    - {r}", flush=True)
                    else:
                        print("INFO: No tienes recordatorios.", flush=True)
                except Exception as e:
                    print(f"ERROR: Error al mostrar recordatorios: {e}", flush=True)
            else:
                print("ERROR: 'generic_reminders' no está disponible. No se pueden mostrar los recordatorios.", flush=True)
            sys.stdout.flush()
            time.sleep(1)

        elif action.startswith("reconoce que la instrucción es una prueba de audio") or \
            action.startswith("saluda al usuario"):
            print(f"✅ Acción de reconocimiento o saludo: '{action}'", flush=True)
            sys.stdout.flush()
            time.sleep(1)

        else:
            print(f"🤷‍♂️ Acción no reconocida o no implementada: '{action}'", flush=True)
            sys.stdout.flush()
            time.sleep(1)

    print("\n--- Ejecución de pasos finalizada ---", flush=True)
    sys.stdout.flush()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_instruction = " ".join(sys.argv[1:])
        process_instruction(user_instruction)
    else:
        print("Uso: python main.py \"[tu instrucción aquí]\"", flush=True)
        print("Ej: python main.py \"abre la aplicación MicroWin\"", flush=True)
    print("INFO: main.py finalizado.", flush=True)
    sys.stdout.flush()
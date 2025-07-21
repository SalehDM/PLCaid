import subprocess
import os
import sys
import json
import time

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

# Importar el módulo knowledge_manager
# Asumiendo que knowledge_manager.py está en la raíz del proyecto
try:
    import knowledge_manager as km
    print("INFO: 'knowledge_manager.py' importado correctamente.", flush=True)
except ImportError:
    print("ERROR: No se pudo importar 'knowledge_manager.py'. Asegúrate de que esté en la misma carpeta o en la ruta de Python.", flush=True)
    sys.exit(1)

# Importar módulos de herramientas (google_search y generic_reminders)
try:
    import google_search
    print("INFO: 'google_search' importado correctamente.", flush=True)
except ImportError:
    print("WARNING: No se pudo importar 'google_search'. Las búsquedas en Google no funcionarán.", flush=True)
    google_search = None # Establecer a None para manejarlo más tarde

try:
    # Asumiendo que generic_reminders.py está en la raíz del proyecto
    import generic_reminders
    print("INFO: 'generic_reminders' importado correctamente.", flush=True)
except ImportError:
    print("WARNING: No se pudo importar 'generic_reminders'. La gestión de recordatorios no funcionará.", flush=True)
    generic_reminders = None # Establecer a None para manejarlo más tarde


# --- Configuración de rutas ---
# Ruta al script text_to_steps.py (CORREGIDA: ahora en la subcarpeta 'script')
TEXT_TO_STEPS_SCRIPT = os.path.join(os.path.dirname(__file__), 'script', 'text_to_steps.py')
# Ruta al archivo de salida de los pasos parseados por text_to_steps.py
PARSED_STEPS_FILE = os.path.join(os.path.dirname(__file__), 'parsed_steps', 'steps.json')
# Ruta al archivo donde se guarda la orden de texto para text_to_steps.py
INPUT_ORDER_FILE = os.path.join(os.path.dirname(__file__), 'input_text', 'order.txt')
# Ruta al script de captura de pantalla (CORREGIDA: ahora en la subcarpeta 'script')
SCREENSHOT_SCRIPT = os.path.join(os.path.dirname(__file__), 'script', 'screenshot.py')
# Ruta al script de análisis de iconos (asumiendo que está en la subcarpeta 'recorte')
ANALIZAR_ICONOS_SCRIPT = os.path.join(os.path.dirname(__file__), 'recorte', 'analizar_iconos.py')
# Ruta al script de ejecución de acciones (CORREGIDA: ahora en la subcarpeta 'script')
EXECUTE_ACTIONS_SCRIPT = os.path.join(os.path.dirname(__file__), 'script', 'execute_actions.py')

# Umbral de similitud para la búsqueda en Qdrant
QDRANT_UI_SEARCH_THRESHOLD = 0.8 # Ajusta este valor según la precisión deseada


def execute_command(command_list):
    """
    Ejecuta un comando de sistema y captura su salida.
    """
    # Copiar el entorno actual y añadir PYTHONIOENCODING
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'

    print(f"DEBUG: Ejecutando subproceso: {' '.join(command_list)}", flush=True) # <--- NUEVO: Imprimir el comando
    sys.stdout.flush()

    try:
        # Ejecutar el subproceso sin decodificar automáticamente (text=False)
        # TEMPORALMENTE: Capturar stderr para depuración, en lugar de DEVNULL
        process = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, # <--- CAMBIO CLAVE: Capturar stderr
            env=env
        )
        
        # Leer la salida y el error
        stdout_bytes, stderr_bytes = process.communicate()
        
        # Decodificar la salida y el error explícitamente
        stdout_decoded = stdout_bytes.decode('utf-8', errors='replace')
        stderr_decoded = stderr_bytes.decode('utf-8', errors='replace')

        # Comprobar el código de retorno
        if process.returncode != 0:
            print(f"❌ Error al ejecutar comando: {' '.join(command_list)}", flush=True)
            print(f"Salida del subcomando (STDOUT): \n{stdout_decoded}", flush=True)
            if stderr_decoded:
                print(f"Errores del subcomando (STDERR): \n{stderr_decoded}", flush=True) # Mostrar stderr
            sys.stdout.flush()
            # Levantar la excepción con la salida de error para que se propague
            raise subprocess.CalledProcessError(process.returncode, command_list, output=stdout_bytes, stderr=stderr_bytes)


        print(f"✅ Comando ejecutado: {' '.join(command_list)}", flush=True)
        print(f"Salida del subcomando: \n{stdout_decoded}", flush=True)
        if stderr_decoded:
            print(f"Errores del subcomando (STDERR): \n{stderr_decoded}", flush=True) # Mostrar stderr
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

        if action.startswith("busca el icono de") or \
            action.startswith("busca el botón de") or \
            action.startswith("busca la pestaña de") or \
            action.startswith("busca el campo de entrada de"):

            element_description_query = action.replace("busca el icono de", "").replace("busca el botón de", "").replace("busca la pestaña de", "").replace("busca el campo de entrada de", "").strip()
            # Eliminar comillas simples del principio y final si existen
            if element_description_query.startswith("'") and element_description_query.endswith("'"):
                element_description_query = element_description_query[1:-1]

            print(f"INFO: Buscando elemento UI: '{element_description_query}' en Qdrant...", flush=True)
            sys.stdout.flush()

            # Intentar buscar en Qdrant primero (CACHE HIT)
            found_elements = km.search_ui_element(element_description_query, limit=1, score_threshold=QDRANT_UI_SEARCH_THRESHOLD)

            if found_elements:
                # CACHE HIT: Elemento encontrado en Qdrant
                cached_element = found_elements[0]
                print(f"INFO: Elemento '{cached_element['description']}' encontrado en Qdrant (cache hit). Tipo: {cached_element['type']}", flush=True)
                sys.stdout.flush()
                
                if 'image_path' in cached_element and cached_element['image_path']:
                    # La ruta almacenada en Qdrant es relativa a la raíz del proyecto.
                    # Necesitamos convertirla a una ruta absoluta para pyautogui.locateOnScreen
                    # Asumiendo que image_path en Qdrant es relativo a la raíz del proyecto (PLCaid/)
                    abs_image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), cached_element['image_path'])
                    print(f"INFO: Usando imagen de referencia de caché: {abs_image_path}", flush=True)
                    sys.stdout.flush()
                    
                    # Copiar la imagen de referencia a la carpeta 'capture' para que execute_actions.py la use
                    try:
                        capture_dir = os.path.join(os.path.dirname(__file__), 'capture')
                        os.makedirs(capture_dir, exist_ok=True)
                        import shutil
                        shutil.copy(abs_image_path, os.path.join(capture_dir, 'image.png'))
                        print("INFO: Imagen de caché copiada a 'capture/image.png'.", flush=True)
                        sys.stdout.flush()
                        # Ahora ejecutar execute_actions.py para hacer clic
                        print("INFO: Ejecutando acción de clic en el elemento encontrado (desde caché)...", flush=True)
                        sys.stdout.flush()
                        execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"])
                    except Exception as e:
                        print(f"ERROR: Fallo al usar imagen de caché o ejecutar acción: {e}", flush=True)
                        sys.stdout.flush()
                        # Si falla, podríamos considerar un fallback al análisis completo
                        print("INFO: Intentando fallback a análisis completo con GPT-4o...", flush=True)
                        sys.stdout.flush()
                        # Fallback a la lógica de GPT-4o si el caché falla
                        print("📸 Tomando captura de pantalla (fallback)...", flush=True)
                        sys.stdout.flush()
                        execute_command(["python", SCREENSHOT_SCRIPT])
                        print(f"🔎 Analizando iconos para: '{element_description_query}' (fallback)", flush=True)
                        sys.stdout.flush()
                        execute_command(["python", ANALIZAR_ICONOS_SCRIPT, element_description_query])
                        print("🎯 Ejecutando acción de clic en el elemento encontrado (fallback)...", flush=True)
                        sys.stdout.flush()
                        execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"])
                else:
                    print("INFO: No hay ruta de imagen en caché. Realizando análisis completo con GPT-4o.", flush=True)
                    sys.stdout.flush()
                    # CACHE MISS (o caché incompleto), proceder con el análisis completo
                    print("📸 Tomando captura de pantalla...", flush=True)
                    sys.stdout.flush()
                    try:
                        execute_command(["python", SCREENSHOT_SCRIPT])
                    except Exception as e:
                        print(f"❌ Fallo en la captura de pantalla: {e}", flush=True)
                        sys.stdout.flush()
                        continue

                    print(f"🔎 Analizando iconos para: '{element_description_query}'", flush=True)
                    sys.stdout.flush()
                    try:
                        execute_command(["python", ANALIZAR_ICONOS_SCRIPT, element_description_query])
                    except Exception as e:
                        print(f"❌ Fallo en el análisis de iconos: {e}", flush=True)
                        sys.stdout.flush()
                        continue

                    # Después de analizar_iconos.py, execute_actions.py debería encontrar la imagen en 'capture/image.png'
                    # y hacer clic en ella.
                    print("🎯 Ejecutando acción de clic en el elemento encontrado...", flush=True)
                    sys.stdout.flush()
                    try:
                        execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"])
                    except Exception as e:
                        print(f"❌ Fallo en la ejecución de la acción: {e}", flush=True)
                        sys.stdout.flush()
                        continue
            else:
                # CACHE MISS: Elemento no encontrado en Qdrant, recurrir a GPT-4o
                print(f"INFO: Elemento '{element_description_query}' NO encontrado en Qdrant (cache miss). Recurriendo a GPT-4o.", flush=True)
                sys.stdout.flush()
                print("📸 Tomando captura de pantalla...", flush=True)
                sys.stdout.flush()
                try:
                    execute_command(["python", SCREENSHOT_SCRIPT])
                except Exception as e:
                    print(f"❌ Fallo en la captura de pantalla: {e}", flush=True)
                    sys.stdout.flush()
                    continue

                print(f"🔎 Analizando iconos para: '{element_description_query}'", flush=True)
                sys.stdout.flush()
                try:
                    execute_command(["python", ANALIZAR_ICONOS_SCRIPT, element_description_query])
                except Exception as e:
                    print(f"❌ Fallo en el análisis de iconos: {e}", flush=True)
                    sys.stdout.flush()
                    continue

                # Después de analizar_iconos.py, execute_actions.py debería encontrar la imagen en 'capture/image.png'
                # y hacer clic en ella.
                print("🎯 Ejecutando acción de clic en el elemento encontrado...", flush=True)
                sys.stdout.flush()
                try:
                    execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"])
                except Exception as e:
                    print(f"❌ Fallo en la ejecución de la acción: {e}", flush=True)
                    sys.stdout.flush()
                    continue

        elif action.startswith("haz clic en el icono de") or \
            action.startswith("haz clic en el botón de") or \
            action.startswith("haz clic en la pestaña de") or \
            action.startswith("haz clic en el campo de entrada de"):
            # Si el LLM ya especificó un clic, asumimos que el elemento ya fue "buscado" o es obvio.
            print("🎯 Intentando ejecutar acción de clic en el elemento previamente encontrado o implícito...", flush=True)
            sys.stdout.flush()
            try:
                execute_command(["python", EXECUTE_ACTIONS_SCRIPT, "click"])
            except Exception as e:
                print(f"❌ Fallo en la ejecución de la acción: {e}", flush=True)
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
                    search_results = google_search.search(queries=[query])
                    for result_set in search_results:
                        if result_set.results:
                            for res in result_set.results:
                                print(f"   Título: {res.source_title}", flush=True)
                                print(f"   Snippet: {res.snippet}", flush=True)
                                print(f"   URL: {res.url}", flush=True)
                                print("-" * 20, flush=True)
                        else:
                            print(f"   No se encontraron resultados para: {result_set.query}", flush=True)
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
                    # Asumiendo que create_reminder toma 'text' como argumento
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
                    # Asumiendo que show_matching_reminders no toma argumentos o toma opcionales
                    reminders = generic_reminders.show_matching_reminders()
                    if reminders:
                        print("INFO: Tus recordatorios:", flush=True)
                        for r in reminders:
                            print(f"   - {r}", flush=True) # Asumiendo que los recordatorios son strings o tienen una representación amigable
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
            time.sleep(1) # Pequeña pausa para simular

        else:
            print(f"🤷‍♂️ Acción no reconocida o no implementada: '{action}'", flush=True)
            sys.stdout.flush()
            time.sleep(1) # Pausa por si acaso

    print("\n--- Ejecución de pasos finalizada ---", flush=True)
    sys.stdout.flush()


if __name__ == "__main__":
    # main.py ahora espera la instrucción como un argumento de línea de comandos
    if len(sys.argv) > 1:
        user_instruction = " ".join(sys.argv[1:])
        process_instruction(user_instruction)
    else:
        print("Uso: python main.py \"[tu instrucción aquí]\"", flush=True)
        print("Ej: python main.py \"abre la aplicación MicroWin\"", flush=True)
        print("No se proporcionó ninguna instrucción. Saliendo.", flush=True)
    print("INFO: main.py finalizado.", flush=True)
    sys.stdout.flush()

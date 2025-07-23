import os
import sys
import cv2
import base64
import json
import shutil
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from openai import OpenAIError
import pytesseract
from pytesseract import Output
import traceback
import argparse
from datetime import datetime # Importar datetime para el timestamp

# --- CRITICAL: Top-level try-except to catch ANY error and print traceback ---
try:
    # --- Configurar la codificación de la salida de la consola al inicio ---
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Not all Python versions/environments support reconfigure
    except Exception as e:
        print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}", flush=True)

    print("DEBUG: analizar_iconos.py iniciado.", flush=True)

    # Determinar la raíz del proyecto para añadirla al sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
        print(f"DEBUG: Añadido '{project_root}' a sys.path para importaciones.", flush=True)
        sys.stdout.flush()

    # Importar el módulo knowledge_manager
    try:
        import knowledge_manager as km
        print("INFO: 'knowledge_manager.py' importado correctamente.", flush=True)
        sys.stdout.flush()
    except ImportError:
        print("ERROR: No se pudo importar 'knowledge_manager.py'. Asegurate de que este en la raiz del proyecto y que la ruta sea correcta.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    # ==== CARGAR API KEY ====
    load_dotenv()
    API_KEY = os.getenv("API_KEY")

    if not API_KEY:
        print("ERROR: La variable de entorno API_KEY (para OpenAI) no esta configurada. Por favor, configurala en tu archivo .env", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    client = None
    try:
        client = OpenAI(api_key=API_KEY)
        print("INFO: Cliente OpenAI inicializado correctamente.", flush=True)
    except OpenAIError as e:
        print(f"ERROR: Error al inicializar el cliente de OpenAI o al conectar con la API: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error inesperado al inicializar el cliente de OpenAI: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    # ==== CONFIGURAR TESSERACT OCR ====
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    try:
        if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
            print(f"ERROR: Tesseract OCR no encontrado en la ruta configurada: '{pytesseract.pytesseract.tesseract_cmd}'.", flush=True)
            print("Asegurate de que Tesseract OCR este instalado y que la ruta en analizar_iconos.py sea la correcta.", flush=True)
            print("Descarga Tesseract OCR desde: https://tesseract-ocr.github.io/tessdoc/Downloads.html", flush=True)
            sys.stdout.flush()
            sys.exit(1)
        print(f"INFO: Tesseract OCR configurado en: {pytesseract.pytesseract.tesseract_cmd}", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"ERROR: Fallo al verificar la configuracion de Tesseract OCR: {e}", flush=True)
        print("Asegurate de que 'pytesseract' este instalado y Tesseract OCR este en tu PATH o configurado manualmente.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    # ==== CONFIGURACION DE CARPETAS PERMANENTES Y TEMPORALES ====
    QDRANT_UI_CACHE_DIR = os.path.join(project_root, "qdrant_ui_cache")
    os.makedirs(QDRANT_UI_CACHE_DIR, exist_ok=True) # Asegurarse de que exista

    # ==== LIMPIAR DATOS ANTERIORES ====
    def limpiar_directorios_y_archivos():
        # Excluir QDRANT_UI_CACHE_DIR de la limpieza
        carpetas_a_limpiar = ["cuadrantes", "icono_final", "iconos_recortados", "elementos_ui", "capture"]
        archivo = "iconos_descripciones.json"

        for carpeta in carpetas_a_limpiar:
            full_path = os.path.join(project_root, carpeta)
            if os.path.exists(full_path) and full_path != QDRANT_UI_CACHE_DIR: # Asegurar que no se borre la cache permanente
                try:
                    shutil.rmtree(full_path)
                    print(f"INFO: Carpeta eliminada: {full_path}", flush=True)
                    sys.stdout.flush()
                except OSError as e:
                    print(f"WARNING: No se pudo eliminar la carpeta '{full_path}': {e}", flush=True)
                    sys.stdout.flush()
            os.makedirs(full_path, exist_ok=True) # Volvemos a crear las carpetas temporales

        full_archivo_path = os.path.join(project_root, archivo)
        if os.path.exists(full_archivo_path):
            try:
                os.remove(full_archivo_path)
                print(f"INFO: Archivo eliminado: {full_archivo_path}", flush=True)
                sys.stdout.flush()
            except OSError as e:
                print(f"WARNING: No se pudo eliminar el archivo '{full_archivo_path}': {e}", flush=True)
                sys.stdout.flush()
        print("INFO: Directorios y archivos temporales limpiados/creados.", flush=True)
        sys.stdout.flush()

    # ==== 1. DIVIDIR EN CUADRANTES ====
    def dividir_en_cuadrantes(imagen_path, output_dir_name="cuadrantes", filas=3, columnas=4):
        output_dir = os.path.join(project_root, output_dir_name)
        os.makedirs(output_dir, exist_ok=True)

        print(f"DEBUG: Intentando cargar imagen con cv2.imread: {imagen_path}", flush=True)
        imagen = cv2.imread(imagen_path)
        
        if imagen is None:
            print(f"ERROR CRITICO: cv2.imread no pudo cargar la imagen: {imagen_path}. Esto puede indicar un archivo corrupto, permisos, o un formato no soportado (ej. no es un PNG/JPG valido).", flush=True)
            sys.stdout.flush()
            raise FileNotFoundError(f"No se pudo cargar la imagen: {imagen_path} (cv2.imread devolvio None).")

        alto, ancho = imagen.shape[:2]
        h_cuadro = alto // filas
        w_cuadro = ancho // columnas
        cuadrantes = []

        print(f"INFO: Dividiendo imagen de {ancho}x{alto}px en {filas}x{columnas} cuadrantes...", flush=True)
        for i in range(filas):
            for j in range(columnas):
                y1 = i * h_cuadro
                y2 = (i + 1) * h_cuadro
                x1 = j * w_cuadro
                x2 = (j + 1) * w_cuadro
                recorte = imagen[y1:y2, x1:x2]
                nombre = f"cuadrante_{i * columnas + j + 1:02d}.png"
                path = os.path.join(output_dir, nombre)
                try:
                    cv2.imwrite(path, recorte)
                    cuadrantes.append((nombre, path))
                except Exception as e:
                    print(f"ERROR: No se pudo guardar el cuadrante '{nombre}': {e}", flush=True)
                    sys.stdout.flush()
                    continue # Continua con el siguiente cuadrante aunque este falle
        
        if not cuadrantes:
            print("ERROR: No se genero ningun cuadrante. Puede haber un problema con la imagen de entrada o los permisos de escritura.", flush=True)
            sys.stdout.flush()
            return [] # Devuelve lista vacía si no se pudo guardar nada

        print(f"INFO: Imagen dividida en {len(cuadrantes)} cuadrantes en '{output_dir}'.", flush=True)
        sys.stdout.flush()
        return cuadrantes

    # ==== 2. IDENTIFICAR CUADRANTE RELEVANTE ====
    def identificar_cuadrante(descripcion, cuadrantes):
        # Modificación del prompt para GPT-4o: ahora le pedimos que evalúe todos los cuadrantes
        # y devuelva el que contenga el elemento o "0" si no lo ve.
        # Esto debería evitar que se limite al cuadrante 1 si no está allí.
        mensaje = [
            {"type": "text", "text": f"Dada la descripción '{descripcion}', ¿en cuál de estos cuadrantes está el elemento? Responde SOLO con el número del cuadrante (del 1 al {len(cuadrantes)}) que contenga el elemento. Si el elemento no es visible o no estás seguro, responde con '0'. Analiza todos los cuadrantes antes de decidir."}
        ]

        for idx, (_, path) in enumerate(cuadrantes): # Usar enumerate para obtener el índice y el número de cuadrante
            try:
                with open(path, "rb") as img_file:
                    imagen_b64 = base64.b64encode(img_file.read()).decode("utf-8")
                mensaje.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{imagen_b64}",
                        "detail": "high"
                    }
                })
                # Añadir un texto que identifique cada cuadrante por su número
                mensaje.append({"type": "text", "text": f"Cuadrante {idx + 1}:"})
            except FileNotFoundError:
                print(f"WARNING: Archivo de cuadrante no encontrado para GPT: {path}. Saltando este cuadrante.", flush=True)
                sys.stdout.flush()
                continue
            except Exception as e:
                print(f"WARNING: Error al codificar cuadrante {path} a base64 para GPT: {e}. Saltando este cuadrante.", flush=True)
                sys.stdout.flush()
                continue

        try:
            if not mensaje or len(mensaje) <= 1: # Si solo hay el texto pero no imagenes
                print("WARNING: No hay elementos visuales validos para enviar a GPT para la seleccion de cuadrante.", flush=True)
                sys.stdout.flush()
                return None

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un experto en diseño de interfaces de usuario. Tu tarea es identificar el cuadrante más relevante de la pantalla. Responde solo con el número del cuadrante (1 a N) o '0' si no estás seguro o no lo ves. No incluyas ningún otro texto."},
                    {"role": "user", "content": mensaje}
                ],
                max_tokens=50,
                temperature=0.2,
            )

            texto_respuesta = response.choices[0].message.content
            print(f"\nINFO: GPT respondio (cuadrante): '{texto_respuesta}'\n", flush=True)
            sys.stdout.flush()

            cuadrante_num_str = "".join(filter(str.isdigit, texto_respuesta))
            if cuadrante_num_str:
                cuadrante_num = int(cuadrante_num_str)
                if 1 <= cuadrante_num <= len(cuadrantes):
                    print(f"INFO: Cuadrante '{cuadrante_num}' seleccionado por GPT: {cuadrantes[cuadrante_num - 1][1]}", flush=True)
                    sys.stdout.flush()
                    return cuadrantes[cuadrante_num - 1][1]
                elif cuadrante_num == 0:
                    print("INFO: GPT indico que no esta seguro o no vio el elemento (respuesta '0').", flush=True)
                    sys.stdout.flush()
            else:
                print(f"WARNING: GPT no devolvio un numero valido para el cuadrante: '{texto_respuesta}'.", flush=True)
                sys.stdout.flush()
            return None
        except OpenAIError as e:
            print(f"ERROR: Error de OpenAI al identificar cuadrante: {e}", flush=True)
            sys.stdout.flush()
            return None
        except Exception as e:
            print(f"ERROR: Error inesperado al identificar cuadrante con GPT-4o: {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc() # Imprime el traceback para este error inesperado
            return None

    # ==== 3. DETECTOR DE ICONOS ====
    class IconDetector:
        def __init__(self, min_size=16, max_size=150, padding=6):
            self.min_size = min_size
            self.max_size = max_size
            self.padding = padding

        def preprocess_image(self, image):
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (3, 3), 0)
                edges = cv2.Canny(blurred, 50, 150)
                edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
                edges = cv2.dilate(edges, None, iterations=1)
                return edges
            except Exception as e:
                print(f"ERROR: Fallo en el preprocesamiento de la imagen para deteccion de iconos: {e}", flush=True)
                sys.stdout.flush()
                raise

        def detect_icons(self, image_path):
            image = cv2.imread(image_path)
            if image is None:
                print(f"ERROR: No se pudo cargar la imagen para detectar iconos: {image_path}. Asegurate de que la ruta es correcta y el archivo no esta corrompido.", flush=True)
                sys.stdout.flush()
                raise FileNotFoundError(f"No se pudo cargar la imagen: {image_path}")

            try:
                preprocessed = self.preprocess_image(image)
                contours, _ = cv2.findContours(preprocessed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                icons = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if self.min_size <= w <= self.max_size and self.min_size <= h <= self.max_size:
                        area = cv2.contourArea(contour)
                        if area > 0.3 * (w * h):
                            icons.append((x, y, w, h, area))
                print(f"INFO: Se detectaron {len(icons)} posibles iconos en el cuadrante (antes de solapamientos).", flush=True)
                sys.stdout.flush()
                return image, self.remove_overlaps(icons)
            except Exception as e:
                print(f"ERROR: Fallo en la deteccion de contornos o procesamiento de iconos: {e}", flush=True)
                sys.stdout.flush()
                traceback.print_exc()
                raise

        def remove_overlaps(self, icons):
            icons = sorted(icons, key=lambda x: x[4], reverse=True) # Ordenar por área descendente
            final = []
            for icon in icons:
                x_i, y_i, w_i, h_i, _ = icon
                
                # Expandir el bounding box del icono para la comprobación de solapamiento
                x1_i = max(0, x_i - self.padding)
                y1_i = max(0, y_i - self.padding)
                x2_i = x_i + w_i + self.padding
                y2_i = y_i + h_i + self.padding
                
                overlap = False
                for fx, fy, fw, fh, _ in final:
                    # Expandir el bounding box del icono ya final
                    x1_f = max(0, fx - self.padding)
                    y1_f = max(0, fy - self.padding)
                    x2_f = fx + fw + self.padding
                    y2_f = fy + fh + self.padding

                    # Comprobación de solapamiento (rectángulos no se solapan si...)
                    if not (x2_i < x1_f or x1_i > x2_f or y2_i < y1_f or y1_i > y2_f):
                        overlap = True
                        break
                if not overlap:
                    final.append(icon)
            print(f"INFO: {len(final)} iconos únicos después de eliminar solapamientos.", flush=True)
            sys.stdout.flush()
            return final

        def crop_icons(self, image, icons, output_dir_name="iconos_recortados"):
            output_dir = os.path.join(project_root, output_dir_name)
            os.makedirs(output_dir, exist_ok=True)
            cropped = []
            for i, (x, y, w, h, _) in enumerate(icons):
                # Aplicar padding y asegurar que no se salga de los límites de la imagen
                x1 = max(0, x - self.padding)
                y1 = max(0, y - self.padding)
                x2 = min(image.shape[1], x + w + self.padding)
                y2 = min(image.shape[0], y + h + self.padding)
                
                recorte = image[y1:y2, x1:x2]
                filename = os.path.join(output_dir, f"icono_{i+1:03d}.png")
                try:
                    cv2.imwrite(filename, recorte)
                    cropped.append(filename)
                except Exception as e:
                    print(f"ERROR: No se pudo guardar el icono recortado '{filename}': {e}", flush=True)
                    sys.stdout.flush()
                    continue
            print(f"INFO: Se recortaron {len(cropped)} iconos en '{output_dir}'.", flush=True)
            sys.stdout.flush()
            return cropped

    # ==== 4. ANALISIS CON GPT-4o ====
    def analizar_icono_con_gpt(icon_path):
        try:
            with open(icon_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un experto en diseno de interfaces de usuario. Describe este icono de forma concisa y clara, e indica su funcion tipica en una interfaz. Por ejemplo: 'Icono de engranaje, representa la configuracion.' o 'Boton con texto 'Aceptar', confirma una accion.' Responde solo con la descripción en formato JSON: {'description': 'tu_descripcion_aqui'}"},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Que representa este elemento visual? Que funcion tiene en una interfaz? Responde solo en formato JSON con la clave 'description'."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}", "detail": "high"}}
                        ]
                    }
                ],
                max_tokens=200, # Aumentar max_tokens para descripciones más completas
                temperature=0.2,
                response_format={"type": "json_object"} # Forzar la respuesta en formato JSON
            )
            
            # Intentar decodificar la respuesta JSON
            try:
                response_json = json.loads(response.choices[0].message.content.strip())
                description = response_json.get("description", "").strip()
                if not description:
                    print(f"WARNING: GPT devolvio JSON vacio o sin 'description' para '{os.path.basename(icon_path)}'. Contenido: {response_json}", flush=True)
                    description = "Descripcion no disponible."
            except json.JSONDecodeError as e:
                print(f"ERROR: No se pudo decodificar la respuesta JSON de GPT-4o para el elemento detallado: {e}", flush=True)
                print(f"DEBUG: Contenido crudo de la respuesta detallada: {response.choices[0].message.content.strip()}", flush=True)
                description = "Error al analizar el icono. Posiblemente relacionado con el formato de respuesta de GPT."
            except Exception as e:
                print(f"ERROR: Error inesperado al procesar la respuesta JSON de GPT para '{os.path.basename(icon_path)}': {e}", flush=True)
                description = "Error interno al procesar descripcion de GPT."

            print(f"INFO: GPT describio '{os.path.basename(icon_path)}': {description}", flush=True)
            sys.stdout.flush()
            return description
        except FileNotFoundError:
            print(f"ERROR: El archivo de icono no se encontro para el analisis GPT: {icon_path}", flush=True)
            sys.stdout.flush()
            return "ERROR: Archivo no encontrado para analisis GPT."
        except OpenAIError as e:
            print(f"ERROR: Error de OpenAI al analizar icono: {e}", flush=True)
            sys.stdout.flush()
            return f"ERROR de OpenAI al analizar: {e}"
        except Exception as e:
            print(f"ERROR: Error inesperado al analizar con GPT-4o: {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc()
            return f"ERROR al analizar: {e}"

    # ==== 5. OBTENER TEXTO DE IMAGEN (OCR) ====
    def obtener_texto_de_imagen(image_path):
        try:
            text_psm6 = pytesseract.image_to_string(image_path, lang='spa', config='--psm 6').strip()
            
            if not text_psm6 or len(text_psm6) < 3:
                text = pytesseract.image_to_string(image_path, lang='spa', config='--psm 3').strip()
                if not text:
                    text = pytesseract.image_to_string(image_path, lang='spa', config='--psm 11').strip()
            else:
                text = text_psm6

            data = pytesseract.image_to_data(image_path, lang='spa', output_type=Output.DICT)
            
            print(f"INFO: OCR detecto texto: '{text}' en '{os.path.basename(image_path)}'", flush=True)
            return text, data
        except pytesseract.TesseractNotFoundError:
            print("ERROR: Tesseract OCR no encontrado o no configurado. Asegurate de instalarlo y/o especificar la ruta.", flush=True)
            sys.stdout.flush()
            return "", {}
        except Exception as e:
            print(f"ERROR: Fallo al obtener texto de la imagen con OCR '{os.path.basename(image_path)}': {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc()
            return "", {}

    # ==== 6. CREAR EMBEDDINGS Y GESTIONAR CONOCIMIENTO ====
    def buscar_icono_en_conocimiento(texto_busqueda):
        print(f"INFO: Buscando '{texto_busqueda}' en la base de conocimiento (Qdrant)...", flush=True)
        sys.stdout.flush()
        try:
            resultados = km.buscar_elementos(texto_busqueda)
            if resultados:
                print(f"INFO: Encontrados {len(resultados)} resultados para '{texto_busqueda}'.", flush=True)
                sys.stdout.flush()
                return resultados[0]
            else:
                print(f"INFO: No se encontraron resultados en la base de conocimiento para '{texto_busqueda}'.", flush=True)
                sys.stdout.flush()
                return None
        except Exception as e:
            print(f"ERROR: Fallo al buscar icono en la base de conocimiento: {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc()
            return None
            
    # Función para seleccionar el elemento más relevante entre los detectados
    def seleccionar_elemento_mas_relevante(descripcion_a_buscar, elementos_detectados):
        if not elementos_detectados:
            print("INFO: No se detectaron elementos procesables en el cuadrante.", flush=True)
            sys.stdout.flush()
            return None

        mensaje_gpt = [
            {"type": "text", "text": f"Dada la siguiente lista de elementos visuales extraídos de una captura de pantalla, identifica cuál de ellos es el que mejor representa: '{descripcion_a_buscar}'. Responde solo con el ID numérico del elemento (1 a {len(elementos_detectados)}). Si no estás seguro o no lo ves claramente, responde con '0'. Prioriza la apariencia visual sobre el texto si hay ambigüedad."}
        ]

        elementos_info = [] # Para almacenar info legible para el prompt y mapear la respuesta de GPT
        for idx, elemento in enumerate(elementos_detectados):
            elemento_id = idx + 1
            elemento_path = elemento.get('path_imagen')
            # Asegurarse de que descripcion_texto y descripcion_gpt son strings, no None
            elemento_desc = elemento.get('descripcion_texto')
            if elemento_desc is None:
                elemento_desc = ""
            
            elemento_gpt_desc = elemento.get('descripcion_gpt')
            if elemento_gpt_desc is None:
                elemento_gpt_desc = ""

            final_desc_for_prompt = elemento_gpt_desc if elemento_gpt_desc else elemento_desc
            elemento_tipo = elemento.get('type', 'desconocido')

            if elemento_path and os.path.exists(elemento_path):
                try:
                    with open(elemento_path, "rb") as img_file:
                        imagen_b64 = base64.b64encode(img_file.read()).decode("utf-8")
                    
                    mensaje_gpt.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{imagen_b64}", "detail": "high"}
                    })
                    mensaje_gpt.append({
                        "type": "text",
                        "text": f"Elemento ID {elemento_id} (Tipo: {elemento_tipo}): {final_desc_for_prompt if final_desc_for_prompt else 'Sin descripcion textual/OCR'}"
                    })
                    elementos_info.append({"id": elemento_id, "path": elemento_path, "description": final_desc_for_prompt, "type": elemento_tipo})
                except Exception as e:
                    print(f"WARNING: Error al procesar elemento {elemento_path} para GPT: {e}. Saltando.", flush=True)
                    sys.stdout.flush()
                    continue
            else:
                print(f"WARNING: La imagen del elemento no existe o no se proporciono ruta: {elemento_path}. Saltando.", flush=True)
                sys.stdout.flush()
                continue
        
        if not elementos_info:
            print("INFO: No hay elementos visuales válidos para enviar a GPT para la selección final.", flush=True)
            sys.stdout.flush()
            return None

        try:
            print(f"INFO: Enviando lote de {len(elementos_info)} elementos a GPT para seleccion primaria.", flush=True)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un experto en reconocimiento de elementos de interfaz de usuario. Tu tarea es identificar el elemento más relevante. Responde solo con el ID numérico del elemento (1 a N) o '0' si no estás seguro."},
                    {"role": "user", "content": mensaje_gpt}
                ],
                max_tokens=100,
                temperature=0.2,
            )
            
            texto_respuesta = response.choices[0].message.content.strip()
            print(f"INFO: GPT selecciono en etapa primaria: '{texto_respuesta}'", flush=True)
            sys.stdout.flush()
            
            seleccion_id_str = "".join(filter(str.isdigit, texto_respuesta))
            if seleccion_id_str:
                seleccion_id = int(seleccion_id_str)
                for el in elementos_info:
                    if el['id'] == seleccion_id:
                        print(f"INFO: Elemento final seleccionado: {el['path']}", flush=True)
                        sys.stdout.flush()
                        return el # Retorna el diccionario completo del elemento seleccionado
            print(f"INFO: GPT no selecciono un elemento valido o respondio '0' ('{texto_respuesta}').", flush=True)
            sys.stdout.flush()
            return None

        except OpenAIError as e:
            print(f"ERROR: Error de OpenAI al seleccionar elemento relevante: {e}", flush=True)
            sys.stdout.flush()
            return None
        except Exception as e:
            print(f"ERROR: Error inesperado al seleccionar elemento relevante con GPT-4o: {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc()
            return None

    # ==== FUNCIÓN PRINCIPAL DE ANÁLISIS ====
    def analizar_pantalla_para_elemento(imagen_path, descripcion_buscada):
        print(f"INFO: Verificando la imagen de pantalla en: {imagen_path}", flush=True)
        sys.stdout.flush()

        if not os.path.exists(imagen_path):
            print(f"ERROR: La imagen de pantalla no se encontró en '{imagen_path}'. Asegúrate de que screenshot.py se ejecuto correctamente.", flush=True)
            sys.stdout.flush()
            return None

        print(f"INFO: Captura de pantalla encontrada en '{imagen_path}'. Procediendo...", flush=True)
        sys.stdout.flush()

        # Limpiar directorios temporales
        limpiar_directorios_y_archivos()

        # Paso 1: Dividir en cuadrantes
        print("\nINFO: Paso 1/5: Dividiendo imagen en cuadrantes...", flush=True)
        cuadrantes = dividir_en_cuadrantes(imagen_path)
        if not cuadrantes:
            print("ERROR: Fallo al dividir la imagen en cuadrantes. Saliendo.", flush=True)
            sys.stdout.flush()
            return None

        # Paso 2: Identificar cuadrante relevante con GPT-4o
        print(f"\nINFO: Paso 2/5: Identificando el cuadrante mas relevante para '{descripcion_buscada}'...", flush=True)
        cuadrante_relevante_path = identificar_cuadrante(descripcion_buscada, cuadrantes)
        if cuadrante_relevante_path is None:
            print("ERROR: No se pudo identificar el cuadrante relevante por GPT. Saliendo.", flush=True)
            sys.stdout.flush()
            return None

        # Paso 3: Analizar elementos visuales (iconos, texto, pestañas) en el cuadrante
        print(f"\nINFO: Paso 3/5: Analizando elementos visuales (iconos, texto, pestañas) en el cuadrante: {cuadrante_relevante_path}", flush=True)
        
        imagen_cuadrante, iconos_bboxes = IconDetector().detect_icons(cuadrante_relevante_path)
        iconos_recortados_paths = IconDetector().crop_icons(imagen_cuadrante, iconos_bboxes)

        elementos_detectados_para_gpt = []

        # Procesar iconos
        for icono_path in iconos_recortados_paths:
            descripcion_gpt = analizar_icono_con_gpt(icono_path)
            elementos_detectados_para_gpt.append({
                "type": "icono",
                "path_imagen": icono_path,
                "descripcion_gpt": descripcion_gpt # Descripción generada por GPT
            })
        
        # Procesar texto OCR (se asume que se guardan en elementos_ui si los hay)
        texto_ocr_raw, _ = obtener_texto_de_imagen(cuadrante_relevante_path)
        
        # Si quieres recortes individuales para cada palabra/línea de OCR,
        # deberías implementar una función aquí que itere sobre `ocr_data['left']`, etc.,
        # recorte esas regiones de `imagen_cuadrante` y las guarde.
        # Por ahora, simplemente añadimos una entrada general de texto si hay texto detectado.
        if texto_ocr_raw:
            # Puedes crear una imagen "simbólica" o un recorte de todo el texto si lo deseas,
            # o simplemente usar la descripción textual. Para este ejemplo, lo manejaremos como una descripción.
            elementos_detectados_para_gpt.append({
                "type": "texto_ocr",
                "path_imagen": cuadrante_relevante_path, # Se refiere al cuadrante completo con el texto
                "descripcion_texto": f"Texto OCR detectado: {texto_ocr_raw}"
            })
        
        if not elementos_detectados_para_gpt:
            print("INFO: No se detectaron iconos, texto o pestañas procesables en el cuadrante.", flush=True)
            sys.stdout.flush()
            return None

# Paso 4: Seleccionar el elemento más relevante entre los detectados
        print(f"\nINFO: Paso 4/5: Seleccionando el elemento mas relevante de {len(elementos_detectados_para_gpt)} detectados...", flush=True)
        elemento_final_seleccionado = seleccionar_elemento_mas_relevante(descripcion_buscada, elementos_detectados_para_gpt)

        if elemento_final_seleccionado is None:
            print("ERROR: No se pudo seleccionar ningun elemento en la etapa primaria. No se pudo identificar el elemento.", flush=True)
            sys.stdout.flush()
            return None

        # Acceder a 'descripcion_texto' o 'descripcion_gpt' de forma segura
        # Añadimos un mensaje más específico si la descripción es None
        desc_para_log = elemento_final_seleccionado.get('descripcion_texto') or elemento_final_seleccionado.get('descripcion_gpt')
        if desc_para_log is None:
            desc_para_log = "Sin descripción inicial"
        print(f"INFO: Elemento seleccionado: {os.path.basename(elemento_final_seleccionado['path'])} (Tipo: {elemento_final_seleccionado['type']}, Descripcion: {desc_para_log})", flush=True)
        sys.stdout.flush()

        # Paso 4.1: Analizar con GPT-4o el elemento seleccionado para una descripción detallada (si es un icono)
        # Re-evaluamos final_description para asegurarnos que sea la más completa
        final_description = elemento_final_seleccionado.get('descripcion_gpt')
        
        # Corregido: Usamos 'path' en lugar de 'path_imagen'
        if not final_description and elemento_final_seleccionado['type'] == 'icono':
            print("\nINFO: Paso 4.1/5: Analizando con GPT-4o el elemento seleccionado para una descripcion detallada...", flush=True)
            final_description = analizar_icono_con_gpt(elemento_final_seleccionado['path']) # <--- ¡CAMBIO AQUÍ!

        # Si aún no hay una descripción final (ej. si el tipo no es icono y no había descripcion_texto)
        if not final_description:
            # Intentar usar la descripcion_texto si existe y no se usó ya como final_description
            final_description = elemento_final_seleccionado.get('descripcion_texto')
            if not final_description:
                print("WARNING: No se pudo obtener una descripción final para el elemento seleccionado. Usando descripción de respaldo.", flush=True)
                final_description = f"Elemento tipo {elemento_final_seleccionado['type']} sin descripción detallada."
            else:
                print(f"INFO: Usando descripcion_texto como descripcion final: {final_description}", flush=True)

        # Paso 4.2: Almacenar el elemento en la base de conocimiento (Qdrant)
        print("\nINFO: Paso 4.2/5: Almacenando el elemento en la base de conocimiento (Qdrant)...", flush=True)
        
        # La función 'km.add_ui_element' espera la descripción y el tipo como primeros argumentos,
        # y ya calcula el embedding internamente.
        # También puede recibir 'image_path' y 'ocr_text' como argumentos opcionales.
        point_id = km.add_ui_element(
            description=final_description,
            element_type=elemento_final_seleccionado['type'],
            # La 'image_path' inicial puede ser None, ya que la actualizamos después de copiar la imagen permanente.
            # No pasamos el 'embedding' directamente aquí, porque 'add_ui_element' lo genera.
            # También podemos pasar el texto OCR si lo tenemos y es relevante para la entrada inicial
            ocr_text=elemento_final_seleccionado.get('descripcion_texto') # Usamos el texto OCR si existe
        )

        if point_id:
            # Una vez tenemos el point_id de Qdrant, construimos la ruta permanente para la imagen
            extension = os.path.splitext(elemento_final_seleccionado['path'])[1] 
            permanent_filename = f"{point_id}{extension}"
            permanent_filepath = os.path.join(QDRANT_UI_CACHE_DIR, permanent_filename)

            try:
                # Copiamos la imagen temporal a la carpeta permanente de caché de Qdrant
                shutil.copy(elemento_final_seleccionado['path'], permanent_filepath) 
                print(f"INFO: Icono '{os.path.basename(elemento_final_seleccionado['path'])}' copiado a la cache permanente: {permanent_filepath}", flush=True)
                
                # Y AHORA SÍ, ACTUALIZAMOS el payload en Qdrant con la ruta permanente correcta
                km.update_ui_element_payload(point_id, {"image_path": permanent_filepath})
                print(f"INFO: Elemento UI '{final_description}' añadido/actualizado en Qdrant con ID: {point_id} y ruta permanente.", flush=True)

            except Exception as e:
                print(f"ERROR: No se pudo copiar o actualizar la ruta del icono en Qdrant para el elemento ID {point_id}: {e}", flush=True)
                sys.stdout.flush()
                return None
        else:
            print("ERROR: No se pudo obtener un ID de Qdrant para almacenar el elemento. Saliendo.", flush=True)
            sys.stdout.flush()
            return None

        print(f"INFO: Elemento '{final_description}' almacenado en Qdrant.", flush=True)
        sys.stdout.flush()

        # Paso 5: Preparar imagen final para clic automatizado (copiar a 'capture' para execute_actions.py)
        print("\nINFO: Paso 5/5: Preparando imagen final para clic automatizado...", flush=True)
        final_capture_dir = os.path.join(project_root, "capture")
        os.makedirs(final_capture_dir, exist_ok=True)
        final_capture_path = os.path.join(final_capture_dir, "image.png") # Nombre fijo para el clic

        try:
            shutil.copy(permanent_filepath, final_capture_path)
            print(f"INFO: Imagen final copiada a '{final_capture_path}'.", flush=True)
            sys.stdout.flush()
        except Exception as e:
            print(f"ERROR: No se pudo copiar la imagen permanente a la carpeta de captura: {e}", flush=True)
            sys.stdout.flush()
            return None

        # Actualizar archivo JSON de descripciones (si lo usas para depuración o referencia)
        iconos_descripciones_path = os.path.join(project_root, "iconos_descripciones.json")
        try:
            with open(iconos_descripciones_path, 'w', encoding='utf-8') as f:
                json.dump({"description": final_description, "image_path": final_capture_path, "qdrant_id": point_id}, f, ensure_ascii=False, indent=4)
            print(f"INFO: Descripcion guardada en '{iconos_descripciones_path}'.", flush=True)
            sys.stdout.flush()
        except Exception as e:
            print(f"WARNING: No se pudo guardar la descripción en el archivo JSON: {e}", flush=True)
            sys.stdout.flush()

        print(f"\nPROCESO COMPLETADO. Elemento relevante guardado en '{final_capture_path}' y descripcion en '{iconos_descripciones_path}'", flush=True)
        sys.stdout.flush()
        
        return final_capture_path 
        
    # ==== PUNTO DE ENTRADA DEL SCRIPT (MAIN) ====
    if __name__ == "__main__":
        parser = argparse.ArgumentParser(description="Analiza una captura de pantalla para identificar un elemento UI.")
        parser.add_argument("descripcion", type=str, help="La descripcion del elemento UI a buscar (ej. 'papelera de reciclaje').")
        args = parser.parse_args()

        screenshot_path = os.path.join(project_root, "screenshots", "pantalla.png")
        
        elemento_encontrado_path = analizar_pantalla_para_elemento(screenshot_path, args.descripcion)

        if elemento_encontrado_path:
            sys.exit(0)
        else:
            sys.exit(1)

except Exception as e:
    print(f"\nERROR CRITICO INESPERADO EN analizar_iconos.py: {e}", flush=True)
    sys.stdout.flush()
    traceback.print_exc()
    sys.exit(1)
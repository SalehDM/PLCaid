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
    # ¡CRÍTICO! Asegúrate de que esta ruta sea la CORRECTA en tu sistema.
    # Por ejemplo: r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    # O para una instalación de 32 bits: r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    try:
        # Se verifica si la ruta configurada realmente existe y es un ejecutable.
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

    # ==== LIMPIAR DATOS ANTERIORES ====
    def limpiar_directorios_y_archivos():
        carpetas = ["cuadrantes", "icono_final", "iconos_recortados", "elementos_ui", "capture"] # Añadimos 'screenshots' para limpiar también la captura inicial
        archivo = "iconos_descripciones.json"

        for carpeta in carpetas:
            full_path = os.path.join(project_root, carpeta)
            if os.path.exists(full_path):
                try:
                    shutil.rmtree(full_path)
                    print(f"INFO: Carpeta eliminada: {full_path}", flush=True)
                    sys.stdout.flush()
                except OSError as e:
                    print(f"WARNING: No se pudo eliminar la carpeta '{full_path}': {e}", flush=True)
                    sys.stdout.flush()
            os.makedirs(full_path, exist_ok=True) # Volvemos a crear las carpetas

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
        mensaje = [
            {"type": "text", "text": f"En cual de estos cuadrantes (del 1 al {len(cuadrantes)}) esta el elemento que representa: '{descripcion}'? Elige solo uno y responde SOLO con el numero. Si no estas seguro o no lo ves, responde con '0'."}
        ]

        for _, path in cuadrantes:
            try:
                with open(path, "rb") as img_file:
                    imagen_b64 = base64.b64encode(img_file.read()).decode("utf-8")
                mensaje.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{imagen_b64}",
                        "detail": "low"
                    }
                })
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
                    {"role": "system", "content": "Eres un experto en diseno de interfaces de usuario. Responde solo con el numero del cuadrante (1 a N) o '0' si no esta seguro o no lo ves."},
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
                        # Filtro para evitar contornos muy pequeños que no sean "rellenos"
                        if area > 0.3 * (w * h): # Asegura que el área del contorno ocupe al menos un 30% del bounding box
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
                    {"role": "system", "content": "Eres un experto en diseno de interfaces de usuario. Describe este icono de forma concisa y clara, e indica su funcion tipica en una interfaz. Por ejemplo: 'Icono de engranaje, representa la configuracion.' o 'Boton con texto 'Aceptar', confirma una accion.'"},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Que representa este elemento visual? Que funcion tiene en una interfaz?"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                        ]
                    }
                ],
                max_tokens=100,
                temperature=0.2,
            )
            description = response.choices[0].message.content.strip()
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
            # Intentar obtener texto con el modo PSM (Page Segmentation Mode)
            # PSM 6: Assume a single uniform block of text. (Bueno para iconos con texto)
            # PSM 3: Fully automatic page segmentation, but no OSD (Orientation and Script Detection). (Por defecto)
            # PSM 11: Sparse text. Find as much text as possible in no particular order. (Más general, puede ser útil)
            
            # Primero intento con PSM 6 para texto en un bloque
            text_psm6 = pytesseract.image_to_string(image_path, lang='spa', config='--psm 6').strip()
            
            # Si no hay texto o es muy corto, intento con PSM 3 (por defecto) o PSM 11
            if not text_psm6 or len(text_psm6) < 3: # Umbral para considerar "texto encontrado"
                text = pytesseract.image_to_string(image_path, lang='spa', config='--psm 3').strip()
                if not text:
                    text = pytesseract.image_to_string(image_path, lang='spa', config='--psm 11').strip()
            else:
                text = text_psm6

            # Obtener datos detallados de OCR (para coordenadas, etc.)
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
    # Se asume que km (knowledge_manager) ya ha sido importado y configurado
    # con el cliente Qdrant y el modelo de embeddings.

    def buscar_icono_en_conocimiento(texto_busqueda):
        print(f"INFO: Buscando '{texto_busqueda}' en la base de conocimiento (Qdrant)...", flush=True)
        sys.stdout.flush()
        try:
            resultados = km.buscar_elementos(texto_busqueda)
            if resultados:
                print(f"INFO: Encontrados {len(resultados)} resultados para '{texto_busqueda}'.", flush=True)
                sys.stdout.flush()
                # Considera cómo manejar múltiples resultados. Por ahora, tomamos el primero.
                return resultados[0] # Devuelve el primer resultado, que debería ser el más relevante.
            else:
                print(f"INFO: No se encontraron resultados en la base de conocimiento para '{texto_busqueda}'.", flush=True)
                sys.stdout.flush()
                return None
        except Exception as e:
            print(f"ERROR: Fallo al buscar icono en la base de conocimiento: {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc()
            return None

    def agregar_icono_a_conocimiento(icono_id, descripcion, path_imagen):
        try:
            with open(path_imagen, "rb") as image_file:
                image_bytes = image_file.read()
            km.agregar_elemento(icono_id, descripcion, image_bytes) # Asumiendo que km.agregar_elemento guarda el ID, desc y bytes
            print(f"INFO: Icono '{icono_id}' con descripcion '{descripcion}' añadido al conocimiento.", flush=True)
            sys.stdout.flush()
            return True
        except Exception as e:
            print(f"ERROR: Fallo al agregar icono '{icono_id}' al conocimiento: {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc()
            return False

    # ==== 7. SELECCIONAR ELEMENTO MAS RELEVANTE CON GPT-4o ====
    def seleccionar_elemento_mas_relevante(elementos, descripcion):
        def preguntar_a_gpt(elementos_lote, descripcion, etapa="primaria"):
            mensaje = [
                {
                    "type": "text",
                    "text": (
                        f"Etapa {etapa}: De los siguientes recortes visuales de una interfaz, cual representa mejor la descripcion: '{descripcion}'?\n"
                        "Elige solo uno y responde SOLO con el numero (por ejemplo: '2'). Si no estas seguro o no lo ves, responde con '0'."
                    )
                }
            ]

            for i, (path, *_) in enumerate(elementos_lote, 1):
                try:
                    with open(path, "rb") as img_file:
                        image_b64 = base64.b64encode(img_file.read()).decode("utf-8")
                    mensaje.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "low"
                        }
                    })
                except FileNotFoundError:
                    print(f"WARNING: Archivo de elemento no encontrado para GPT: {path}. Saltando este elemento.", flush=True)
                    sys.stdout.flush()
                    continue
                except Exception as e:
                    print(f"WARNING: Error al codificar elemento {path} a base64 para GPT: {e}. Saltando este elemento.", flush=True)
                    sys.stdout.flush()
                    continue

            try:
                if not mensaje or len(mensaje) <= 1: # Si solo hay el texto pero no imagenes
                    print("WARNING: No hay elementos visuales validos para enviar a GPT para la seleccion.", flush=True)
                    sys.stdout.flush()
                    return None

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Eres un experto en interfaces graficas de usuario. Responde solo con el numero del elemento mas relevante (1 a N) o '0' si no esta seguro o no lo ves."},
                        {"role": "user", "content": mensaje}
                    ],
                    max_tokens=10,
                    temperature=0.2,
                )

                respuesta = response.choices[0].message.content.strip()
                print(f"INFO: GPT selecciono en etapa {etapa}: '{respuesta}'", flush=True)
                sys.stdout.flush()

                elemento_num_str = "".join(filter(str.isdigit, respuesta))
                if elemento_num_str:
                    elemento_num = int(elemento_num_str)
                    if 1 <= elemento_num <= len(elementos_lote):
                        return elementos_lote[elemento_num - 1]
                    elif elemento_num == 0:
                        print("INFO: GPT indico que no esta seguro o no vio el elemento (respuesta '0').", flush=True)
                        sys.stdout.flush()
                else:
                    print(f"WARNING: GPT no devolvio un numero valido para la seleccion de elemento: '{respuesta}'.", flush=True)
                    sys.stdout.flush()
                return None
            except OpenAIError as e:
                print(f"ERROR: Error de OpenAI al seleccionar elemento en etapa {etapa}: {e}", flush=True)
                sys.stdout.flush()
                return None
            except Exception as e:
                print(f"ERROR: Error inesperado al seleccionar elemento con GPT-4o en etapa {etapa}: {e}", flush=True)
                sys.stdout.flush()
                traceback.print_exc()
                return None

        ganadores = []
        print(f"INFO: Iniciando seleccion del elemento mas relevante entre {len(elementos)} elementos.", flush=True)
        sys.stdout.flush()
        # Procesar en lotes de 5 (límite de imágenes por petición a GPT-4o)
        for i in range(0, len(elementos), 5):
            lote = elementos[i:i + 5]
            print(f"INFO: Enviando lote {i//5 + 1} de {len(lote)} elementos a GPT para seleccion primaria.", flush=True)
            ganador = preguntar_a_gpt(lote, descripcion, etapa="primaria")
            if ganador:
                ganadores.append(ganador)

        if not ganadores:
            print("ERROR: No se pudo seleccionar ningun elemento en la etapa primaria. No se pudo identificar el elemento.", flush=True)
            sys.stdout.flush()
            return None

        if len(ganadores) == 1:
            print(f"INFO: Elemento final seleccionado: {ganadores[0][0]}", flush=True)
            sys.stdout.flush()
            return ganadores[0]

        # Segunda ronda si hay múltiples "ganadores"
        print(f"INFO: Realizando ronda final de seleccion entre {len(ganadores)} ganadores primarios.", flush=True)
        sys.stdout.flush()
        finalista = preguntar_a_gpt(ganadores, descripcion, etapa="final")
        if finalista:
            print(f"INFO: Elemento final seleccionado: {finalista[0]}", flush=True)
            sys.stdout.flush()
            return finalista

        print("ERROR: No se pudo seleccionar un elemento final despues de las dos etapas. No se pudo identificar el elemento.", flush=True)
        sys.stdout.flush()
        return None

    # ==== CLASE PARA DETECCION DE ELEMENTOS DE UI (texto y pestañas) ====
    class UIElementDetector:
        def __init__(self, padding=6):
            self.padding = padding

        def detectar_textos(self, image, output_dir_name="elementos_ui", tipo="texto"):
            output_dir = os.path.join(project_root, output_dir_name)
            os.makedirs(output_dir, exist_ok=True)
            
            # Asegurarse de que la imagen esté en BGR para cvtColor si es monocromática
            if len(image.shape) == 2:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:
                image_rgb = image

            elementos = []
            try:
                # Obtener datos de OCR (text, conf, bbox)
                data = pytesseract.image_to_data(image_rgb, output_type=Output.DICT, lang="spa")
                
                # Iterar sobre los resultados del OCR
                for i in range(len(data["text"])):
                    text = data["text"][i].strip()
                    conf = int(data["conf"][i])
                    
                    # Filtrar por confianza y si hay texto
                    if text and conf > 40: # Solo si hay texto y confianza aquí establecida
                        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                        
                        # Aplicar padding y asegurar límites de imagen
                        x1 = max(0, x - self.padding)
                        y1 = max(0, y - self.padding)
                        x2 = min(image.shape[1], x + w + self.padding)
                        y2 = min(image.shape[0], y + h + self.padding)

                        recorte = image[y1:y2, x1:x2]
                        filename = os.path.join(output_dir, f"texto_{i+1:03d}.png") # Renombrado a 'texto'
                        try:
                            cv2.imwrite(filename, recorte)
                            elementos.append((filename, tipo, text))
                        except Exception as e:
                            print(f"WARNING: No se pudo guardar el recorte de texto '{filename}': {e}", flush=True)
                            sys.stdout.flush()
                            continue
                print(f"INFO: Se detectaron {len(elementos)} elementos de texto en '{output_dir}'.", flush=True)
                sys.stdout.flush()
                return elementos
            except pytesseract.TesseractNotFoundError:
                print("ERROR: Tesseract no se encontro durante deteccion de texto. Asegurate de que este instalado y en tu PATH o configurado.", flush=True)
                sys.stdout.flush()
                return []
            except Exception as e:
                print(f"ERROR: Fallo en la deteccion de texto OCR: {e}", flush=True)
                sys.stdout.flush()
                traceback.print_exc()
                return []

        def detectar_pestanas(self, image, output_dir_name="elementos_ui"):
            output_dir = os.path.join(project_root, output_dir_name)
            os.makedirs(output_dir, exist_ok=True)
            elementos = []
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                # Aplicar un umbral para binarizar la imagen y resaltar posibles pestañas/contornos
                _, binaria = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

                # Encontrar contornos
                contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for i, c in enumerate(contornos):
                    x, y, w, h = cv2.boundingRect(c)
                    # Filtros heurísticos para identificar posibles pestañas (ajustar si es necesario)
                    if w > 50 and h > 10 and h < 60: # Ancho razonable, altura no muy grande
                        recorte = image[y:y+h, x:x+w]
                        filename = os.path.join(output_dir, f"pestana_{i+1:03d}.png")
                        try:
                            cv2.imwrite(filename, recorte)
                            elementos.append((filename, "pestana", None)) # No hay texto OCR directo aquí
                        except Exception as e:
                            print(f"WARNING: No se pudo guardar el recorte de pestaña '{filename}': {e}", flush=True)
                            sys.stdout.flush()
                            continue
                print(f"INFO: Se detectaron {len(elementos)} posibles pestañas en '{output_dir}'.", flush=True)
                sys.stdout.flush()
                return elementos
            except Exception as e:
                print(f"ERROR: Fallo en la deteccion de pestañas: {e}", flush=True)
                sys.stdout.flush()
                traceback.print_exc()
                return []

    # ==== FUNCIÓN PRINCIPAL ====
    def main(descripcion):
        # Primero limpia y crea las carpetas necesarias
        limpiar_directorios_y_archivos()

        # Define las rutas de archivos
        # Se asume que 'pantalla.png' debe ser generado por un proceso EXTERNO
        # y colocado en 'project_root/screenshots/' antes de ejecutar este script.
        IMAGE_PATH = os.path.join(project_root, "screenshots", "pantalla.png")
        FINAL_CAPTURE_DIR = os.path.join(project_root, "capture")
        JSON_OUTPUT = os.path.join(project_root, "iconos_descripciones.json")

        # --- Verificación CRÍTICA de la imagen de entrada ---
        print(f"\nINFO: Verificando la imagen de pantalla en: {IMAGE_PATH}", flush=True)
        sys.stdout.flush()
        if not os.path.exists(IMAGE_PATH):
            print(f"ERROR: El archivo de captura de pantalla '{IMAGE_PATH}' NO SE ENCONTRO.", flush=True)
            print("Asegurate de que se haya tomado una captura de pantalla completa y se haya guardado con ese nombre y ruta.", flush=True)
            sys.stdout.flush()
            sys.exit(1) # Salida crítica si la imagen no existe
        else:
            print(f"INFO: Captura de pantalla encontrada en '{IMAGE_PATH}'. Procediendo...", flush=True)

        print("\nINFO: Paso 1/5: Dividiendo imagen en cuadrantes...", flush=True)
        sys.stdout.flush()
        try:
            cuadrantes = dividir_en_cuadrantes(IMAGE_PATH)
            if not cuadrantes:
                print("ERROR: No se generaron cuadrantes. Abortando analisis. Esto puede ser un problema con la imagen de entrada o OpenCV.", flush=True)
                sys.stdout.flush()
                sys.exit(1)
        except FileNotFoundError as e: # Captura si cv2.imread devolvio None y la función lo re-lanzó
            print(f"ERROR: {e}. Asegurate de que la captura de pantalla sea un archivo de imagen valido y no este corrupto.", flush=True)
            sys.stdout.flush()
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Error inesperado al dividir en cuadrantes: {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc()
            sys.exit(1)

        print(f"\nINFO: Paso 2/5: Identificando el cuadrante mas relevante para '{descripcion}'...", flush=True)
        sys.stdout.flush()
        cuadrante_path = identificar_cuadrante(descripcion, cuadrantes)

        if not cuadrante_path:
            print("ERROR: No se pudo identificar el cuadrante relevante por GPT. Saliendo.", flush=True)
            sys.stdout.flush()
            sys.exit(1)

        print(f"\nINFO: Paso 3/5: Analizando elementos visuales (iconos, texto, pestañas) en el cuadrante: {cuadrante_path}\n", flush=True)
        sys.stdout.flush()
        detector = IconDetector(min_size=40, max_size=300, padding=20)
        ui_detector = UIElementDetector(padding=6)

        try:
            image_cuadrante = cv2.imread(cuadrante_path)
            if image_cuadrante is None:
                print(f"ERROR: No se pudo cargar la imagen del cuadrante para analisis: {cuadrante_path}. Asegurate de que la ruta es correcta y el archivo no esta corrompido.", flush=True)
                sys.stdout.flush()
                sys.exit(1)

            iconos = []
            try:
                _, iconos_raw = detector.detect_icons(cuadrante_path)
                paths_iconos_cropped = detector.crop_icons(image_cuadrante, iconos_raw, output_dir_name="iconos_recortados")
                iconos = [(path, "icono", None) for path in paths_iconos_cropped] # path, tipo, ocr_text (None para iconos puros)
                if not iconos:
                    print("INFO: No se detectaron iconos procesables en el cuadrante.", flush=True)
            except Exception as e:
                print(f"WARNING: Fallo en la deteccion y recorte de iconos: {e}. Continuando sin iconos.", flush=True)
                sys.stdout.flush()
                traceback.print_exc()
                iconos = []

            elementos_texto = []
            try:
                elementos_texto = ui_detector.detectar_textos(image_cuadrante, output_dir_name="elementos_ui")
                if not elementos_texto:
                    print("INFO: No se detectaron elementos de texto procesables en el cuadrante.", flush=True)
            except Exception as e:
                print(f"WARNING: Fallo en la deteccion de texto OCR: {e}. Continuando sin elementos de texto.", flush=True)
                sys.stdout.flush()
                traceback.print_exc()
                elementos_texto = []

            elementos_pestanas = []
            try:
                elementos_pestanas = ui_detector.detectar_pestanas(image_cuadrante, output_dir_name="elementos_ui")
                if not elementos_pestanas:
                    print("INFO: No se detectaron pestañas procesables en el cuadrante.", flush=True)
            except Exception as e:
                print(f"WARNING: Fallo en la deteccion de pestañas: {e}. Continuando sin pestañas.", flush=True)
                sys.stdout.flush()
                traceback.print_exc()
                elementos_pestanas = []

            elementos_combinados = iconos + elementos_texto + elementos_pestanas
            
            if not elementos_combinados:
                print("ERROR: No se detecto ningun elemento visual (icono, texto, pestaña) en el cuadrante para analizar. Saliendo.", flush=True)
                sys.stdout.flush()
                sys.exit(1)

            print(f"\nINFO: Paso 4/5: Seleccionando el elemento mas relevante de {len(elementos_combinados)} detectados...", flush=True)
            sys.stdout.flush()
            elemento_elegido_tuple = seleccionar_elemento_mas_relevante(elementos_combinados, descripcion)

            if elemento_elegido_tuple:
                elemento_elegido_path = elemento_elegido_tuple[0]
                elemento_tipo = elemento_elegido_tuple[1]
                # ocr_text_found podría ser None si es un icono o pestaña sin texto directo
                ocr_text_found = elemento_elegido_tuple[2] if len(elemento_elegido_tuple) > 2 else None
                
                filename = os.path.basename(elemento_elegido_path)
                print(f"\nINFO: Elemento seleccionado: {filename} (Tipo: {elemento_tipo}, OCR: {ocr_text_found})", flush=True)
                sys.stdout.flush()

                print(f"INFO: Paso 4.1/5: Analizando con GPT-4o el elemento seleccionado para una descripcion detallada...", flush=True)
                descripcion_final = analizar_icono_con_gpt(elemento_elegido_path)
                
                print(f"INFO: Paso 4.2/5: Almacenando el elemento en la base de conocimiento (Qdrant)...", flush=True)
                try:
                    rel_image_path_for_qdrant = os.path.relpath(elemento_elegido_path, project_root)
                    km.add_ui_element( # Asumiendo que esta es la función correcta en knowledge_manager.py
                        description=descripcion_final,
                        element_type=elemento_tipo,
                        image_path=rel_image_path_for_qdrant,
                        ocr_text=ocr_text_found
                    )
                    print(f"INFO: Elemento '{descripcion_final}' almacenado en Qdrant.", flush=True)
                    sys.stdout.flush()
                except Exception as e:
                    print(f"ERROR: Error al almacenar elemento en Qdrant: {e}", flush=True)
                    sys.stdout.flush()
                    traceback.print_exc()
                    # No sys.exit(1) aquí, ya que el archivo final todavía podría generarse.

                print(f"\nINFO: Paso 5/5: Preparando imagen final para clic automatizado...", flush=True)
                sys.stdout.flush()
                os.makedirs(FINAL_CAPTURE_DIR, exist_ok=True)
                ruta_final_imagen_para_clic = os.path.join(FINAL_CAPTURE_DIR, "image.png")
                try:
                    shutil.copy(elemento_elegido_path, ruta_final_imagen_para_clic)
                    print(f"INFO: Imagen final copiada a '{ruta_final_imagen_para_clic}'.", flush=True)
                except Exception as e:
                    print(f"ERROR: No se pudo copiar la imagen final a '{ruta_final_imagen_para_clic}': {e}", flush=True)
                    sys.stdout.flush()
                    sys.exit(1) # Error crítico si no se puede preparar la imagen para el clic

                print(f"INFO: Actualizando archivo JSON de descripciones...", flush=True)
                if os.path.exists(JSON_OUTPUT):
                    try:
                        with open(JSON_OUTPUT, "r", encoding="utf-8") as f:
                            data_existente = json.load(f)
                    except json.JSONDecodeError:
                        print(f"WARNING: El archivo JSON '{JSON_OUTPUT}' esta corrupto o vacio. Creando uno nuevo.", flush=True)
                        sys.stdout.flush()
                        data_existente = {}
                    except Exception as e:
                        print(f"WARNING: Error al leer JSON existente '{JSON_OUTPUT}': {e}. Se creara uno nuevo.", flush=True)
                        sys.stdout.flush()
                        data_existente = {}
                else:
                    data_existente = {}

                data_existente[filename] = descripcion_final
                try:
                    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
                        json.dump(data_existente, f, indent=4, ensure_ascii=False)
                    print(f"INFO: Descripcion guardada en '{JSON_OUTPUT}'.", flush=True)
                except Exception as e:
                    print(f"ERROR: No se pudo guardar el archivo JSON '{JSON_OUTPUT}': {e}", flush=True)
                    sys.stdout.flush()

                print(f"\nPROCESO COMPLETADO. Elemento relevante guardado en '{ruta_final_imagen_para_clic}' y descripcion en '{JSON_OUTPUT}'\n", flush=True)
                sys.stdout.flush()
            else:
                print("ERROR: No se pudo identificar el elemento mas relevante. Saliendo.", flush=True)
                sys.stdout.flush()
                sys.exit(1) # Salida si GPT no pudo seleccionar un elemento
        except Exception as e:
            print(f"ERROR: Error general en analizar_iconos.py durante el procesamiento del cuadrante o seleccion de elementos: {e}", flush=True)
            sys.stdout.flush()
            traceback.print_exc()
            sys.exit(1)

    if __name__ == "__main__":
        parser = argparse.ArgumentParser(description="Analiza una captura de pantalla para identificar iconos y elementos de UI.")
        parser.add_argument("descripcion", type=str,
                            help="Descripcion del icono o elemento de UI a buscar.")
        args = parser.parse_args()
        main(args.descripcion)

except Exception as e:
    print(f"CRITICAL ERROR in analizar_iconos.py (top-level): {e}", flush=True)
    traceback.print_exc(file=sys.stdout) # Asegura que el traceback se imprima en stdout
    sys.stdout.flush()
    sys.exit(1)

# Esta línea mantendrá la ventana de CMD abierta si el script se ejecuta directamente (no desde un IDE)
# print("\nPresiona Enter para salir...", flush=True)
# input()
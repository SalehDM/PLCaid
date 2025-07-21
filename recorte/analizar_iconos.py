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
        pass
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
    except OpenAIError as e:
        print(f"ERROR: Error al inicializar el cliente de OpenAI o al conectar con la API: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error inesperado al inicializar el cliente de OpenAI: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    # ==== CONFIGURAR TESSERACT OCR ====
    try:
        tesseract_path = pytesseract.pytesseract.tesseract_cmd
        if not tesseract_path or not os.path.exists(tesseract_path):
            print("ERROR: Tesseract OCR no encontrado o no configurado. Asegurate de instalarlo y/o especificar la ruta en analizar_iconos.py.", flush=True)
            print("Descarga Tesseract OCR desde: https://tesseract-ocr.github.io/tessdoc/Downloads.html", flush=True)
            sys.stdout.flush()
            sys.exit(1)
        print(f"INFO: Tesseract OCR configurado en: {tesseract_path}", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"ERROR: Fallo al verificar la configuracion de Tesseract OCR: {e}", flush=True)
        print("Asegurate de que 'pytesseract' este instalado y Tesseract OCR este en tu PATH o configurado manualmente.", flush=True)
        sys.stdout.flush()
        sys.exit(1)

    # ==== LIMPIAR DATOS ANTERIORES ====
    def limpiar_directorios_y_archivos():
        carpetas = ["cuadrantes", "icono_final", "iconos_recortados", "elementos_ui", "capture"]
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
            os.makedirs(full_path, exist_ok=True)

        full_archivo_path = os.path.join(project_root, archivo)
        if os.path.exists(full_archivo_path):
            try:
                os.remove(full_archivo_path)
                print(f"INFO: Archivo eliminado: {full_archivo_path}", flush=True)
                sys.stdout.flush()
            except OSError as e:
                print(f"WARNING: No se pudo eliminar el archivo '{full_archivo_path}': {e}", flush=True)
                sys.stdout.flush()

    # ==== 1. DIVIDIR EN CUADRANTES ====
    def dividir_en_cuadrantes(imagen_path, output_dir_name="cuadrantes", filas=3, columnas=4):
        output_dir = os.path.join(project_root, output_dir_name)
        os.makedirs(output_dir, exist_ok=True)

        imagen = cv2.imread(imagen_path)
        if imagen is None:
            print(f"ERROR: No se pudo cargar la imagen para dividir en cuadrantes: {imagen_path}. Asegurate de que la ruta es correcta y el archivo no esta corrompido.", flush=True)
            sys.stdout.flush()
            raise FileNotFoundError(f"No se pudo cargar la imagen: {imagen_path}")

        alto, ancho = imagen.shape[:2]
        h_cuadro = alto // filas
        w_cuadro = ancho // columnas
        cuadrantes = []

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
                except Exception as e:
                    print(f"ERROR: No se pudo guardar el cuadrante '{nombre}': {e}", flush=True)
                    sys.stdout.flush()
                    continue
                cuadrantes.append((nombre, path))
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
                print(f"WARNING: Archivo de cuadrante no encontrado: {path}. Saltando este cuadrante.", flush=True)
                sys.stdout.flush()
                continue
            except Exception as e:
                print(f"WARNING: Error al codificar cuadrante {path} a base64: {e}. Saltando este cuadrante.", flush=True)
                sys.stdout.flush()
                continue

        try:
            if not mensaje:
                print("WARNING: No hay elementos validos para enviar a GPT para la seleccion.", flush=True)
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
            print(f"\nINFO: GPT respondio (cuadrante): {texto_respuesta}\n", flush=True)
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
                print(f"ERROR: Fallo en el preprocesamiento de la imagen: {e}", flush=True)
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
                print(f"INFO: Se detectaron {len(icons)} posibles iconos en el cuadrante.", flush=True)
                sys.stdout.flush()
                return image, self.remove_overlaps(icons)
            except Exception as e:
                print(f"ERROR: Fallo en la deteccion de contornos o procesamiento de iconos: {e}", flush=True)
                sys.stdout.flush()
                raise

        def remove_overlaps(self, icons):
            icons = sorted(icons, key=lambda x: x[4], reverse=True)
            final = []
            for icon in icons:
                x1 = max(0, icon[0] - self.padding)
                y1 = max(0, icon[1] - self.padding)
                w1 = icon[2] + 2 * self.padding
                h1 = icon[3] + 2 * self.padding
                
                overlap = False
                for fx, fy, fw, fh, _ in final:
                    if not (x1 + w1 < fx or x1 > fx + fw or y1 + h1 < fy or y1 > fy + fh):
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
            return f"ERROR al analizar: {e}"

    # ==== 5. SELECCIONAR ELEMENTO MAS RELEVANTE ====
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
                    print(f"WARNING: Archivo de elemento no encontrado: {path}. Saltando este elemento.", flush=True)
                    sys.stdout.flush()
                    continue
                except Exception as e:
                    print(f"WARNING: Error al codificar elemento {path} a base64: {e}. Saltando este elemento.", flush=True)
                    sys.stdout.flush()
                    continue

            try:
                if not mensaje:
                    print("WARNING: No hay elementos validos para enviar a GPT para la seleccion.", flush=True)
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
                print(f"INFO: GPT selecciono en etapa {etapa}: {respuesta}", flush=True)
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
                return None

        ganadores = []
        print(f"INFO: Seleccionando el elemento mas relevante entre {len(elementos)} elementos.", flush=True)
        sys.stdout.flush()
        for i in range(0, len(elementos), 5):
            lote = elementos[i:i + 5]
            ganador = preguntar_a_gpt(lote, descripcion, etapa="primaria")
            if ganador:
                ganadores.append(ganador)

        if not ganadores:
            print("ERROR: No se pudo seleccionar ningun elemento en la etapa primaria.", flush=True)
            sys.stdout.flush()
            return None

        if len(ganadores) == 1:
            print(f"INFO: Elemento final seleccionado: {ganadores[0][0]}", flush=True)
            sys.stdout.flush()
            return ganadores[0]

        print(f"INFO: Realizando ronda final de seleccion entre {len(ganadores)} ganadores primarios.", flush=True)
        sys.stdout.flush()
        finalista = preguntar_a_gpt(ganadores, descripcion, etapa="final")
        if finalista:
            print(f"INFO: Elemento final seleccionado: {finalista[0]}", flush=True)
            sys.stdout.flush()
            return finalista

        print("ERROR: No se pudo seleccionar un elemento final.", flush=True)
        sys.stdout.flush()
        return None

    # ==== CLASE PARA DETECCION DE ELEMENTOS ====
    class UIElementDetector:
        def __init__(self, padding=6):
            self.padding = padding

        def detectar_textos(self, image, output_dir_name="elementos_ui", tipo="texto"):
            output_dir = os.path.join(project_root, output_dir_name)
            os.makedirs(output_dir, exist_ok=True)
            if len(image.shape) == 2:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:
                image_rgb = image

            elementos = []
            try:
                data = pytesseract.image_to_data(image_rgb, output_type=Output.DICT, lang="spa")
                for i in range(len(data["text"])):
                    text = data["text"][i].strip()
                    conf = int(data["conf"][i])
                    if text and conf > 60:
                        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                        x1 = max(0, x - self.padding)
                        y1 = max(0, y - self.padding)
                        x2 = min(image.shape[1], x + w + self.padding)
                        y2 = min(image.shape[0], y + h + self.padding)

                        recorte = image[y1:y2, x1:x2]
                        filename = os.path.join(output_dir, f"tipo_{i+1:03d}.png")
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
                print("ERROR: Tesseract no se encontro. Asegurate de que este instalado y en tu PATH.", flush=True)
                sys.stdout.flush()
                return []
            except Exception as e:
                print(f"ERROR: Fallo en la deteccion de texto OCR: {e}", flush=True)
                sys.stdout.flush()
                return []

        def detectar_pestanas(self, image, output_dir_name="elementos_ui"):
            output_dir = os.path.join(project_root, output_dir_name)
            os.makedirs(output_dir, exist_ok=True)
            elementos = []
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _, binaria = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

                contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for i, c in enumerate(contornos):
                    x, y, w, h = cv2.boundingRect(c)
                    if w > 50 and h < 60:
                        recorte = image[y:y+h, x:x+w]
                        filename = os.path.join(output_dir, f"pestana_{i+1:03d}.png")
                        try:
                            cv2.imwrite(filename, recorte)
                            elementos.append((filename, "pestana", None))
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
                return []

    # ==== FUNCION PRINCIPAL ====
    def main(descripcion):
        limpiar_directorios_y_archivos()

        IMAGE_PATH = os.path.join(project_root, "screenshots", "pantalla.png")
        FINAL_CAPTURE_DIR = os.path.join(project_root, "capture")
        JSON_OUTPUT = os.path.join(project_root, "iconos_descripciones.json")

        print("\nINFO: Dividiendo imagen en cuadrantes...", flush=True)
        sys.stdout.flush()
        try:
            cuadrantes = dividir_en_cuadrantes(IMAGE_PATH)
        except FileNotFoundError as e:
            print(f"ERROR: {e}. Asegurate de que la captura de pantalla exista antes de analizar iconos.", flush=True)
            sys.stdout.flush()
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Error inesperado al dividir en cuadrantes: {e}", flush=True)
            sys.stdout.flush()
            sys.exit(1)

        print(f"INFO: Descripcion recibida para busqueda: '{descripcion}'", flush=True)
        sys.stdout.flush()
        cuadrante_path = identificar_cuadrante(descripcion, cuadrantes)

        if not cuadrante_path:
            print("ERROR: No se pudo identificar el cuadrante relevante. Saliendo.", flush=True)
            sys.stdout.flush()
            sys.exit(1)

        print(f"INFO: Analizando cuadrante: {cuadrante_path}\n", flush=True)
        sys.stdout.flush()
        detector = IconDetector(min_size=16, max_size=150, padding=6)
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
                iconos = [(path, "icono", None) for path in paths_iconos_cropped]
            except Exception as e:
                print(f"WARNING: Fallo en la deteccion de iconos: {e}. Continuando sin iconos.", flush=True)
                sys.stdout.flush()
                iconos = []

            elementos_texto = []
            try:
                elementos_texto = ui_detector.detectar_textos(image_cuadrante, output_dir_name="elementos_ui")
            except Exception as e:
                print(f"WARNING: Fallo en la deteccion de texto OCR: {e}. Continuando sin elementos de texto.", flush=True)
                sys.stdout.flush()
                elementos_texto = []

            elementos_pestanas = []
            try:
                elementos_pestanas = ui_detector.detectar_pestanas(image_cuadrante, output_dir_name="elementos_ui")
            except Exception as e:
                print(f"WARNING: Fallo en la deteccion de pestañas: {e}. Continuando sin pestañas.", flush=True)
                sys.stdout.flush()
                elementos_pestanas = []

            elementos_combinados = iconos + elementos_texto + elementos_pestanas

            if not elementos_combinados:
                print("ERROR: No se detecto ningun elemento visual en el cuadrante para analizar. Saliendo.", flush=True)
                sys.stdout.flush()
                sys.exit(1)

            elemento_elegido_tuple = seleccionar_elemento_mas_relevante(elementos_combinados, descripcion)

            if elemento_elegido_tuple:
                elemento_elegido_path = elemento_elegido_tuple[0]
                elemento_tipo = elemento_elegido_tuple[1]
                ocr_text_found = elemento_elegido_tuple[2] if len(elemento_elegido_tuple) > 2 else None
                
                filename = os.path.basename(elemento_elegido_path)
                print(f"\nINFO: Analizando elemento seleccionado: {filename} (Tipo: {elemento_tipo}, OCR: {ocr_text_found})", flush=True)
                sys.stdout.flush()
                descripcion_final = analizar_icono_con_gpt(elemento_elegido_path)
                
                try:
                    rel_image_path_for_qdrant = os.path.relpath(elemento_elegido_path, project_root)
                    km.add_ui_element(
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
                    import traceback
                    traceback.print_exc()

                os.makedirs(FINAL_CAPTURE_DIR, exist_ok=True)
                ruta_final_imagen_para_clic = os.path.join(FINAL_CAPTURE_DIR, "image.png")
                try:
                    shutil.copy(elemento_elegido_path, ruta_final_imagen_para_clic)
                except Exception as e:
                    print(f"ERROR: No se pudo copiar la imagen final a '{ruta_final_imagen_para_clic}': {e}", flush=True)
                    sys.stdout.flush()
                    sys.exit(1)

                if os.path.exists(JSON_OUTPUT):
                    try:
                        with open(JSON_OUTPUT, "r", encoding="utf-8") as f:
                            data_existente = json.load(f)
                    except json.JSONDecodeError:
                        print(f"WARNING: El archivo JSON '{JSON_OUTPUT}' esta corrupto o vacio. Creando uno nuevo.", flush=True)
                        sys.stdout.flush()
                        data_existente = {}
                else:
                    data_existente = {}

                data_existente[filename] = descripcion_final
                try:
                    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
                        json.dump(data_existente, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"ERROR: No se pudo guardar el archivo JSON '{JSON_OUTPUT}': {e}", flush=True)
                    sys.stdout.flush()

                print(f"\nINFO: Elemento relevante guardado en '{ruta_final_imagen_para_clic}' y descripcion en '{JSON_OUTPUT}'\n", flush=True)
                sys.stdout.flush()
            else:
                print("ERROR: No se pudo identificar el elemento mas relevante. Saliendo.", flush=True)
                sys.stdout.flush()
                sys.exit(1)
        except Exception as e:
            print(f"ERROR: Error general en analizar_iconos.py: {e}", flush=True)
            sys.stdout.flush()
            import traceback
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
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    sys.exit(1)

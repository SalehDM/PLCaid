import os
import cv2
import base64
import json
import shutil
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
import pytesseract
from pytesseract import Output


# ==== CARGAR API KEY ====
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("❌ No se encontró la API_KEY en el archivo .env")
client = OpenAI(api_key=API_KEY)

# ==== LIMPIAR DATOS ANTERIORES ====
def limpiar_directorios_y_archivos():
    carpetas = ["icono_final", "iconos_recortados"]
    archivo = "iconos_descripciones.json"

    for carpeta in carpetas:
        if os.path.exists(carpeta):
            shutil.rmtree(carpeta)
            print(f"🧹 Carpeta eliminada: {carpeta}")

    if os.path.exists(archivo):
        os.remove(archivo)
        print(f"🧹 Archivo eliminado: {archivo}")

# ==== 1. DIVIDIR EN CUADRANTES ====
def dividir_en_cuadrantes(imagen_path, output_dir="cuadrantes", filas=3, columnas=4):
    os.makedirs(output_dir, exist_ok=True)
    imagen = cv2.imread(imagen_path)
    if imagen is None:
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
            cv2.imwrite(path, recorte)
            cuadrantes.append((nombre, path))
    return cuadrantes

# ==== 2. IDENTIFICAR CUADRANTE RELEVANTE ====
def identificar_cuadrante(descripcion, cuadrantes):
    mensaje = [
        {"type": "text", "text": f"¿En cuál de estos cuadrantes (del 1 al {len(cuadrantes)}) está el elemento que representa: '{descripcion}'? Elige solo uno."}
    ]

    for _, path in cuadrantes:
        with open(path, "rb") as img_file:
            imagen_b64 = base64.b64encode(img_file.read()).decode("utf-8")
        mensaje.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{imagen_b64}",
                "detail": "low"
            }
        })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un experto en diseño de interfaces de usuario."},
            {"role": "user", "content": mensaje}
        ],
        max_tokens=50,
        temperature=0.2,
    )

    texto_respuesta = response.choices[0].message.content
    print(f"\n📌 GPT respondió: {texto_respuesta}\n")
    for i in range(1, len(cuadrantes)+1):
        if str(i) in texto_respuesta:
            return cuadrantes[i-1][1]
    return None

# ==== 3. DETECTOR DE ÍCONOS ====
class IconDetector:
    def __init__(self, min_size=20, max_size=200, padding=5):
        self.min_size = min_size
        self.max_size = max_size
        self.padding = padding

    def preprocess_image(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(blurred, 50, 150)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        edges = cv2.dilate(edges, None, iterations=1)
        return edges

    def detect_icons(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"No se pudo cargar la imagen: {image_path}")
        preprocessed = self.preprocess_image(image)
        contours, _ = cv2.findContours(preprocessed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        icons = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if self.min_size <= w <= self.max_size and self.min_size <= h <= self.max_size:
                area = cv2.contourArea(contour)
                if area > 0.3 * (w * h):
                    icons.append((x, y, w, h, area))
        return image, self.remove_overlaps(icons)

    def remove_overlaps(self, icons):
        icons = sorted(icons, key=lambda x: x[4], reverse=True)
        final = []
        for icon in icons:
            x1, y1, w1, h1, _ = icon
            overlap = False
            for fx, fy, fw, fh, _ in final:
                if (x1 < fx + fw and x1 + w1 > fx and y1 < fy + fh and y1 + h1 > fy):
                    overlap = True
                    break
            if not overlap:
                final.append(icon)
        return final

    def crop_icons(self, image, icons, output_dir="iconos_recortados"):
        os.makedirs(output_dir, exist_ok=True)
        cropped = []
        for i, (x, y, w, h, _) in enumerate(icons):
            x1 = max(0, x - self.padding)
            y1 = max(0, y - self.padding)
            x2 = min(image.shape[1], x + w + self.padding)
            y2 = min(image.shape[0], y + h + self.padding)
            recorte = image[y1:y2, x1:x2]
            filename = os.path.join(output_dir, f"icono_{i+1:03d}.png")
            cv2.imwrite(filename, recorte)
            cropped.append(filename)
        return cropped

# ==== 4. ANÁLISIS CON GPT-4o ====
def analizar_icono_con_gpt(icon_path):
    try:
        with open(icon_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode("utf-8")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en diseño de interfaces de usuario."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "¿Qué representa este ícono? ¿Qué función tiene en una interfaz?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ]
                }
            ],
            max_tokens=100,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Error al analizar: {e}"

# ==== 5. SELECCIONAR ELEMENTO MÁS RELEVANTE ====
def seleccionar_elemento_mas_relevante(elementos, descripcion):
    def preguntar_a_gpt(elementos_lote, descripcion, etapa="primaria"):
        mensaje = [
            {
                "type": "text",
                "text": (
                    f"Etapa {etapa}: De los siguientes recortes visuales de una interfaz, ¿cuál representa mejor la descripción: '{descripcion}'?\n"
                    "Elige solo uno y responde SOLO con el número (por ejemplo: '2')."
                )
            }
        ]

        for i, (path, _) in enumerate(elementos_lote, 1):
            with open(path, "rb") as img_file:
                image_b64 = base64.b64encode(img_file.read()).decode("utf-8")
            mensaje.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}",
                    "detail": "low"
                }
            })

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en interfaces gráficas de usuario."},
                {"role": "user", "content": mensaje}
            ],
            max_tokens=10,
            temperature=0.2,
        )

        respuesta = response.choices[0].message.content.strip()
        print(f"📌 GPT seleccionó en etapa {etapa}: {respuesta}")
        for i in range(1, len(elementos_lote) + 1):
            if str(i) in respuesta:
                return elementos_lote[i - 1]  # Devuelve (path, tipo)
        return None

    # Paso 1: dividir en lotes de 5
    ganadores = []
    for i in range(0, len(elementos), 5):
        lote = elementos[i:i + 5]
        ganador = preguntar_a_gpt(lote, descripcion, etapa="primaria")
        if ganador:
            ganadores.append(ganador)

    if not ganadores:
        print("❌ No se pudo seleccionar ningún elemento en la etapa primaria.")
        return None

    if len(ganadores) == 1:
        return ganadores[0][0]  # Ruta del archivo

    # Paso 2: ronda final entre los ganadores
    finalista = preguntar_a_gpt(ganadores, descripcion, etapa="final")
    if finalista:
        return finalista[0]

    print("❌ No se pudo seleccionar un elemento final.")
    return None



# ==== CLASE PARA DETECCIÓN DE ELEMENTOS ====
class UIElementDetector:
    def __init__(self, padding=6):
        self.padding = padding

    def detectar_textos(self, image, output_dir="elementos_ui", tipo="texto"):
        os.makedirs(output_dir, exist_ok=True)
        data = pytesseract.image_to_data(image, output_type=Output.DICT, lang="eng")

        elementos = []
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
                filename = os.path.join(output_dir, f"{tipo}_{i+1:03d}.png")
                cv2.imwrite(filename, recorte)
                elementos.append((filename, text))
        return elementos

    def detectar_pestanas(self, image, output_dir="elementos_ui"):
        os.makedirs(output_dir, exist_ok=True)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binaria = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

        contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        elementos = []

        for i, c in enumerate(contornos):
            x, y, w, h = cv2.boundingRect(c)
            if w > 50 and h < 60:  # Heurística de pestaña horizontal
                recorte = image[y:y+h, x:x+w]
                filename = os.path.join(output_dir, f"pestana_{i+1:03d}.png")
                cv2.imwrite(filename, recorte)
                elementos.append((filename, "posible pestaña"))
        return elementos

# ==== FUNCIÓN PRINCIPAL ====
def main(descripcion):
    limpiar_directorios_y_archivos()

    IMAGE_PATH = "screenshots/pantalla.png"
    OUTPUT_DIR = "iconos_recortados"
    FINAL_ICON_DIR = "capture"
    JSON_OUTPUT = "iconos_descripciones.json"

    print("\n📷 Dividiendo imagen en cuadrantes...")
    cuadrantes = dividir_en_cuadrantes(IMAGE_PATH)

    print(f"📥 Descripción recibida: '{descripcion}'")
    cuadrante_path = identificar_cuadrante(descripcion, cuadrantes)

    if not cuadrante_path:
        print("❌ No se pudo identificar el cuadrante relevante.")
        return

    print(f"🔎 Analizando cuadrante: {cuadrante_path}\n")
    detector = IconDetector(min_size=16, max_size=150, padding=6)
    ui_detector = UIElementDetector(padding=6)

    try:
        image, iconos = detector.detect_icons(cuadrante_path)
        paths_iconos = detector.crop_icons(image, iconos, output_dir="iconos_recortados")

        elementos_texto = ui_detector.detectar_textos(image)
        elementos_pestanas = ui_detector.detectar_pestanas(image)

        elementos_combinados = [(path, "icono") for path in paths_iconos]
        elementos_combinados += [(path, "texto") for path, _ in elementos_texto]
        elementos_combinados += [(path, "pestana") for path, _ in elementos_pestanas]

        if not elementos_combinados:
            print("❌ No se detectó ningún elemento visual en el cuadrante.")
            return

        elemento_elegido = seleccionar_elemento_mas_relevante(elementos_combinados, descripcion)

        if elemento_elegido:
            filename = os.path.basename(elemento_elegido)
            print(f"\n🖼️ Analizando elemento seleccionado: {filename}")
            descripcion_final = analizar_icono_con_gpt(elemento_elegido)

            os.makedirs(FINAL_ICON_DIR, exist_ok=True)
            ruta_final = os.path.join(FINAL_ICON_DIR, "image.png")
            cv2.imwrite(ruta_final, cv2.imread(elemento_elegido))

            # Guardar en JSON
            if os.path.exists(JSON_OUTPUT):
                with open(JSON_OUTPUT, "r", encoding="utf-8") as f:
                    data_existente = json.load(f)
            else:
                data_existente = {}

            data_existente[filename] = descripcion_final
            with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
                json.dump(data_existente, f, indent=4, ensure_ascii=False)

            print(f"\n✅ Elemento relevante guardado en '{ruta_final}' y descripción en '{JSON_OUTPUT}'\n")
        else:
            print("❌ No se pudo identificar el elemento más relevante.")
    except Exception as e:
        print(f"❌ Error general: {e}")


# Permite que el script también funcione desde consola si se desea
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        descripcion_arg = " ".join(sys.argv[1:]).strip()
        main(descripcion_arg)
    else:
        descripcion_input = input("🔤 ¿Qué estás buscando? Describe el ícono o función: ").strip()
        main(descripcion_input)

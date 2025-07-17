import os
import cv2
import base64
from dotenv import load_dotenv
from openai import OpenAI

# === Cargar API_KEY desde .env ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("❌ No se encontró la API_KEY en el archivo .env")
client = OpenAI(api_key=API_KEY)

# === Dividir en cuadrantes ===
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

# === Preguntar a GPT-4o por pestañas abiertas ===
def detectar_pestanas(cuadrantes):
    mensaje = [
        {
            "type": "text",
            "text": (
                "¿Puedes decirme en qué cuadrantes hay pestañas abiertas como las de un navegador o aplicación?"
                " Describe cada pestaña visible brevemente y menciona si tiene un ícono de cierre (como una 'X')."
                " Responde claramente con el número del cuadrante, nombre o texto de la pestaña si es visible,"
                " y si tiene un ícono de cierre."
            )
        }
    ]

    for _, path in cuadrantes:
        with open(path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode("utf-8")
        mensaje.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"}
        })

    print("🧠 Consultando a GPT-4o sobre pestañas...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un experto en interfaces gráficas de usuario."},
            {"role": "user", "content": mensaje}
        ],
        max_tokens=500,
        temperature=0.3
    )

    respuesta = response.choices[0].message.content.strip()
    print("\n📋 GPT-4o detectó:\n")
    print(respuesta)

# === Ejecutar flujo principal ===
def main():
    imagen_path = "v2/captura.png"
    cuadrantes = dividir_en_cuadrantes(imagen_path)
    detectar_pestanas(cuadrantes)

if __name__ == "__main__":
    main()

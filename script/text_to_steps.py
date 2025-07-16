from openai import OpenAI
from dotenv import load_dotenv
import os, sys, json, argparse

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_text_to_steps(text: str) -> list:
    """
    Llama a la API de OpenAI para convertir un texto en pasos estructurados.
    """
    prompt = f"""
Eres un asistente que ayuda a un robot a ejecutar tareas en **Windows XP** exclusivamente.

El robot solo puede:
- Buscar elementos visuales (como iconos, botones, menús, submenús o campos de entrada).
- Hacer scroll con la rueda del ratón en menús desplegables o contextuales grandes que lo requieran; como, por ejemplo, el menú 'Todos los programas'.
- Hacer clic o doble clic con el botón izquierdo o derecho del ratón sobre los elementos visuales.
- Añadir texto en campos de entrada, haciendo clic previamente en la primera línea disponible.
- Usar atajos de teclado como 'Enter', 'Tab', 'Esc', 'Ctrl+C', 'Ctrl+V', etc.

Por lo tanto, para completar una tarea, debe buscar los elementos en la interfaz visual (por ejemplo: el botón de inicio, los accesos directos, los menús del sistema) y realizar las acciones permitidas pertinentes para conseguir el objetivo solicitado.
Incluye pausas entre pasos si es necesario, como por ejemplo, "espera 2 segundos" o "espera a que se abra la ventana".
Devuelve una **lista de pasos en formato JSON**, con los campos `"step"` y `"action"`.

Ejemplos:

Ir a la página 'www.youtube.es':
[
  {{ "step": 1, "action": "busca el icono de 'Inicio'" }},
  {{ "step": 2, "action": "haz clic en el icono de 'Inicio'" }},
  {{ "step": 3, "action": "espera a que se abra el menú de 'Inicio'" }},
  {{ "step": 4, "action": "busca el icono de 'Todos los programas'" }},
  {{ "step": 5, "action": "haz clic en el icono de 'Todos los programas'" }},
  {{ "step": 6, "action": "espera a que se abra el menú desplegable 'Todos los programas'" }},
  {{ "step": 7, "action": "haz scroll en el menú desplegable 'Todos los programas'" }},
  {{ "step": 8, "action": "busca el icono del navegador web" }},
  {{ "step": 9, "action": "haz clic en el icono del navegador web" }},
  {{ "step": 10, "action": "espera a que se abra el navegador web" }},
  {{ "step": 11, "action": "busca el campo de entrada de la URL" }},
  {{ "step": 12, "action": "haz clic en el campo de entrada de la URL" }},
  {{ "step": 13, "action": "escribe 'www.youtube.es'" }},
  {{ "step": 14, "action": "presiona 'Enter' para cargar la página" }}
]

Crear una carpeta nueva llamada 'Documentos':
[
  {{ "step": 1, "action": "busca el icono de 'Inicio'" }},
  {{ "step": 2, "action": "haz clic en el icono de 'Inicio'" }},
  {{ "step": 3, "action": "espera a que se abra el menú de 'Inicio'" }},
  {{ "step": 4, "action": "busca el icono de 'Mi PC'" }},
  {{ "step": 5, "action": "haz clic en el icono de 'Mi PC'" }},
  {{ "step": 6, "action": "espera a que se abra la ventana de 'Mi PC'" }},
  {{ "step": 7, "action": "busca el icono de 'Disco local (C:)'" }},
  {{ "step": 8, "action": "haz doble clic en el icono de 'Disco local (C:)'" }},
  {{ "step": 9, "action": "espera a que se abra la ventana del disco local" }},
  {{ "step": 10, "action": "haz clic derecho en un espacio vacío dentro de la ventana" }},
  {{ "step": 11, "action": "selecciona 'Nuevo' en el menú contextual" }},
  {{ "step": 12, "action": "selecciona 'Carpeta' en el submenú" }},
  {{ "step": 13, "action": "escribe 'Documentos' como nombre de la nueva carpeta" }},
  {{ "step": 14, "action": "presiona 'Enter' para crear la carpeta" }}
]

Abrir la aplicación MicroWin:

[
  {{ "step": 1, "action": "busca el icono de 'Inicio'" }},
  {{ "step": 2, "action": "haz clic en el icono de 'Inicio'" }},
  {{ "step": 3, "action": "espera a que se abra el menú de 'Inicio'" }},
  {{ "step": 4, "action": "busca el icono de 'Todos los programas'" }},
  {{ "step": 5, "action": "haz clic en el icono de 'Todos los programas'" }},
  {{ "step": 6, "action": "espera a que se abra el menú desplegable 'Todos los programas'" }},
  {{ "step": 7, "action": "haz scroll en el menú desplegable 'Todos los programas'" }},
  {{ "step": 8, "action": "busca el icono de 'MicroWin'" }},
  {{ "step": 9, "action": "haz clic en el icono de 'MicroWin'" }},
  {{ "step": 10, "action": "espera a que se abra la aplicación MicroWin" }}
]


Texto de entrada:
\"\"\"
{text}
\"\"\"

No expliques los pasos ni incluyas texto fuera del JSON.
Devuelve exclusivamente la lista JSON.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente que estructura instrucciones visuales paso a paso."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content

    cleaned_content = content.strip().strip("`")
    if cleaned_content.startswith("json"):
        cleaned_content = cleaned_content[4:].strip()

    try:
        return json.loads(cleaned_content)
    except json.JSONDecodeError:
        print("[✗] No se pudo interpretar la respuesta de OpenAI como JSON.")
        print("Respuesta recibida:\n", content)
        sys.exit(1)

# Cargar pasos desde steps.json
print("\n[1] Cargando pasos desde steps.json...")

txt_path = os.path.join("input_text", "order.txt")
steps_path = os.path.join("parsed_steps", "steps.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=txt_path, help="Ruta al archivo de entrada")
    parser.add_argument("--output", default=steps_path, help="Ruta al archivo de salida para los pasos JSON")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[✗] El archivo '{args.input}' no existe.")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        order = f.read()

    steps = parse_text_to_steps(order)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(steps, f, indent=2, ensure_ascii=False)

    print(f"[✓] Guardado en {args.output}")
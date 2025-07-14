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
Ignora el contenido lógico o técnico de la tarea descrita. Tu única responsabilidad es convertir el siguiente texto en una secuencia de pasos físicos específicos con ratón y teclado, como si fueras un asistente robótico que mueve el ratón y escribe en el teclado paso a paso.

Eres un asistente que ayuda al usuario a automatizar tareas dentro de Windows XP únicamente a partir de movimientos del ratón y del teclado. Cada paso debe ser una **acción física concreta**, como:

- mover el cursor a una posición o elemento (ejemplo: "mueve el ratón al acceso directo del navegador en el escritorio")
- hacer clic, doble clic, clic derecho
- introducir texto con el teclado
- pulsar combinaciones de teclas (Ctrl+C, Enter, etc.)
- seleccionar menús o botones
- arrastrar o soltar
- cerrar o minimizar ventanas

Extrae estos pasos en formato JSON, con los campos `"step"` y `"action"`, como en este ejemplo:

[
  {{ "step": 1, "action": "mueve el cursor al acceso directo del navegador en el escritorio" }},
  {{ "step": 2, "action": "haz doble clic en el acceso directo" }},
  {{ "step": 3, "action": "espera a que se abra la ventana principal del programa" }},
  {{ "step": 4, "action": "mueve el ratón al icono de 'Nueva pestaña'" }},
  {{ "step": 5, "action": "haz clic en el icono de 'Nueva pestaña'" }},
  ...
]

Texto de entrada:
\"\"\"
{text}
\"\"\"

No expliques qué hace cada paso, solo describe la acción física como si la ejecutara un robot sin contexto

Devuelve únicamente la lista JSON.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente que estructura instrucciones paso a paso."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content

    # Eliminar delimitadores de bloque tipo ```json ... ```
    cleaned_content = content.strip().strip("`")

    # A veces viene como ```json\n...\n``` así que lo filtramos más seguro:
    if cleaned_content.startswith("json"):
        cleaned_content = cleaned_content[4:].strip()

    try:
        return json.loads(cleaned_content)
    except json.JSONDecodeError:
        print("[✗] No se pudo interpretar la respuesta de OpenAI como JSON.")
        print("Respuesta recibida:\n", content)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Ruta al archivo.txt")
    parser.add_argument("--output", default="parsed_steps/steps.json")
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
import os
from dotenv import load_dotenv
from openai import OpenAI

# Cargar variables de entorno
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("No se encontró la API key en el archivo .env")

# Inicializar cliente OpenAI
client = OpenAI(api_key=api_key)

def codificar_scl(texto: str):
    # Pedir input al usuario
    orden = texto

    # Construir el prompt
    prompt = f"""
Devuelveme este codigo exactamente igual al ejemplo.

Formato de salida: Solo y exclusivamente el código SCL.

Ejemplo de código SCL:


IF ("MarchaF1" OR "MarchaP1") AND NOT "Salida2" THEN
    "Salida1" := TRUE;
    "Salida2" := FALSE;
END_IF;
    
IF ("MarchaF2" OR "MarchaP2") AND NOT "Salida1" THEN
    "Salida1" := FALSE;
    "Salida2" := TRUE;
END_IF;


IF "ParoP" OR NOT "ParoF" THEN
    "Salida1" := FALSE;
    "Salida2" := FALSE;
END_IF;

IF "Salida1" OR "Salida2" THEN
    "Salida3" := TRUE;
END_IF;

IF NOT "Salida1" AND NOT "Salida2" THEN
    "Salida3" := FALSE;
END_IF;

"""

    # Solicitar la respuesta al modelo
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        codigo_scl = response.choices[0].message.content
        return codigo_scl

    except Exception as e:
        print(f"Ocurrió un error al generar el código SCL: {e}")
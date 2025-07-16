import os
import json
import mss
from PIL import Image

# Ruta al archivo steps.json
script_dir = os.path.dirname(os.path.abspath(__file__))
steps_path = os.path.join(script_dir, "..", "parsed_steps", "steps.json")

# Directorio para guardar la captura
output_dir = os.path.join(script_dir, "..", "screenshots")
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "pantalla.png")

# Cargar pasos desde steps.json
with open(steps_path, "r", encoding="utf-8") as f:
    steps = json.load(f)

# Iniciar capturas por cada paso
with mss.mss() as sct:
    monitor = sct.monitors[2]  # Usa el segundo monitor. Cambia a [1] si es solo uno.

    total_steps = len(steps)

    for index, step in enumerate(steps):
        step_number = step["step"]
        action = step["action"]

        print(f"\nPaso {step_number}/{total_steps}: {action}")

        # Captura automática al mostrar el paso
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.save(output_file)
        print(f"📸 Captura guardada como 'pantalla.png'")

        # Si no es el último paso, espera al usuario para continuar
        if index < total_steps - 1:
            input("Pulsa 1 y Enter para pasar al siguiente paso... ")
        else:
            print("\n✅ Todos los pasos completados. Proceso finalizado.")
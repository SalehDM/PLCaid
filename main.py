import os
import subprocess
import time
import json

print("""
==== GPT Clicker Assistant ====
1. Audio a pasos 
2. Texto a pasos
3. Captura de pantalla
4. Imagen + pasos → coordenadas
5. Ejecutar acciones
""")

print("== ORQUESTADOR GPT CLICKER ==")
print()

# Paso 1: Ejecutar módulo Entrada y NLP
print("\n[1] Ejecutando módulo Entrada y NLP...")
print()

opcion = input("Elige la entrada de usuario (1= Voz, 2= Texto): ")

if opcion == "1":
    # Ejecuta voice_to_text_whisper.py y espera que termine
    result1 = subprocess.run(["python3", "script/voice_to_text_whisper.py"])
    if result1.returncode == 0:
        # Si el anterior terminó bien, ejecuta text_to_steps.py
        subprocess.run(["python3", "script/text_to_steps.py"])
    else:
        print("Error: voice_to_text_whisper.py no finalizó correctamente.")
elif opcion == "2":
    subprocess.run(["python3", "script/text_to_steps.py"])
else:
    print("Opción no válida.")


# Paso 2: Ejecutar módulo Captura de pantalla
print("\n[2] Ejecutando módulo Captura de pantalla...")

# Ruta al archivo steps.json
script_dir = os.path.dirname(os.path.abspath(__file__))
steps_path = os.path.join(script_dir, "..", "parsed_steps", "steps.json")

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

# Paso 3: Analizar imagen con GPT Vision (simulado)
print("\n[3] Analizando imagen con GPT Vision...")
subprocess.run(["python", "scripts/vision_prompt_api.py"])

# Paso 4: Ejecutar acción basada en coordenadas
print("\n[4] Ejecutando acción...")
subprocess.run(["python", "scripts/execute_actions.py"])

print("\n✅ Flujo completo ejecutado.")

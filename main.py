import os
import json
import subprocess
import time
import psutil

# Ruta absoluta del directorio raíz del proyecto (donde está main.py)
project_root = os.path.dirname(os.path.abspath(__file__))


####################################################################################################################


# print("== ORQUESTADOR GPT CLICKER ==")
# print()

# Paso 1: Ejecutar módulo Entrada y NLP
# print("\n[1] Ejecutando módulo Entrada y NLP...")
# print()

# opcion = input("Elige la entrada de usuario (1= Voz, 2= Texto): ")

# if opcion == "1":
    # Ejecuta voice_to_text_whisper.py y espera que termine
result1 = subprocess.run(["python3", "script/voice_to_text_whisper.py"])
if result1.returncode == 0:
    # Si el anterior terminó bien, ejecuta text_to_steps.py
    subprocess.run(["python3", "script/text_to_steps.py"])
else:
    print("Error: voice_to_text_whisper.py no finalizó correctamente.")
# elif opcion == "2":
    # subprocess.run(["python3", "script/text_to_steps.py"])
# else:
    # print("Opción no válida.")

####################################################################################################################

# Paso 2: Ejecutar módulo Captura de pantalla
print("\n[2] Ejecutando módulo Captura de pantalla...")

def is_execute_actions_running():
    """
    Devuelve True si el proceso 'execute_actions.py' está corriendo.
    """
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
        try:
            if "execute_actions.py" in proc.info["cmdline"]:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

# Paso 2.1: Cargar pasos desde steps.json
print("\n[1] Cargando pasos desde steps.json...")

steps_path = os.path.join(project_root, "parsed_steps", "steps.json")

with open(steps_path, "r", encoding="utf-8") as f:
    steps = json.load(f)

# Paso 2.2: Ejecutar bucle de pasos
total_steps = len(steps)

for index, step in enumerate(steps):
    step_number = step["step"]
    action = step["action"]

    print(f"\nPaso {step_number}/{total_steps}: {action}")

    # 1. Ejecutar módulo screenshot.py (espera a que termine)
    print("📸 Ejecutando captura de pantalla...")
    subprocess.run(["python3", "script/screenshot.py"])

    # 2. Esperar confirmación del usuario
    input("🔔 Pulse 'Enter' para continuar...")

    # 3. Lanzar proceso 'execute_actions.py'
    print("🕹️ Ejecutando 'execute_actions.py'...")
    subprocess.run(["python3", "script/execute_actions.py"])


    print("✅ Acción detectada como completada.")

print("\n🎉 Todos los pasos han sido ejecutados.")

####################################################################################################################

# Paso 3: Analizar imagen con GPT Vision (simulado)
print("\n[3] Analizando imagen con GPT Vision...")
subprocess.run(["python", "scripts/vision_prompt_api.py"])

# Paso 4: Ejecutar acción basada en coordenadas
print("\n[4] Ejecutando acción...")
subprocess.run(["python", "scripts/execute_actions.py"])

print("\n✅ Flujo completo ejecutado.")

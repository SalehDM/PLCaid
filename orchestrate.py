import os
import subprocess
import time

print("== ORQUESTADOR GPT CLICKER ==")

# Paso 1: Generar pasos desde texto
print("\n[1] Generando pasos desde texto...")
subprocess.run(["python", "scripts/text_to_steps.py"])

# Paso 2: Tomar captura de pantalla
print("\n[2] Tomando captura de pantalla...")
subprocess.run(["python", "scripts/screenshot.py"])

# Paso 3: Analizar imagen con GPT Vision (simulado)
print("\n[3] Analizando imagen con GPT Vision...")
subprocess.run(["python", "scripts/vision_prompt_api.py"])

# Paso 4: Ejecutar acción basada en coordenadas
print("\n[4] Ejecutando acción...")
subprocess.run(["python", "scripts/execute_actions.py"])

print("\n✅ Flujo completo ejecutado.")

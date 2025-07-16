# /home/reboot-student/code/labs/PLCaid/screenshots/disparador.py

import os
import time
import subprocess

WATCHED_FILE = "pantalla.png"
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(DIRECTORY, WATCHED_FILE)
TIMEOUT_SECONDS = 500

print("🕹️ Ejecutando inicialmente 'execute_actions.py'...")
subprocess.run(["python3", "script/execute_actions.py"])

print("\n⏳ Esperando nuevas modificaciones de 'pantalla.png' (máx 500 segundos)...")

start_time = time.time()
last_mtime = None

# Inicializar marca de tiempo si el archivo ya existe
if os.path.exists(FILE_PATH):
    last_mtime = os.path.getmtime(FILE_PATH)

while time.time() - start_time < TIMEOUT_SECONDS:
    time_left = TIMEOUT_SECONDS - int(time.time() - start_time)
    print(f"⏱️ Tiempo restante: {time_left} segundos", end="\r")

    if os.path.exists(FILE_PATH):
        mtime = os.path.getmtime(FILE_PATH)
        if last_mtime is None or mtime != last_mtime:
            print(f"\n🆕 Cambio detectado en '{WATCHED_FILE}' (nueva modificación).")
            print("🕹️ Ejecutando 'execute_actions.py'...\n")
            subprocess.run(["python3", "script/execute_actions.py"])
            last_mtime = mtime
    time.sleep(1)
else:
    print("\n⏱️ Tiempo agotado. No se detectó ningún nuevo cambio en 'pantalla.png'.")


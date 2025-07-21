import mss
import mss.tools
import os
import sys # Importar sys para reconfigurar stdout/stderr
import time

# --- Configurar la codificación de la salida de la consola al inicio ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass
except Exception as e:
    print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}", flush=True)

# Determinar la raíz del proyecto para la ruta de la captura de pantalla
# Asumiendo que screenshot.py está en PLCaid/script
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Sube un nivel de 'script'
SCREENSHOT_DIR = os.path.join(project_root, 'screenshots')
SCREENSHOT_FILENAME = 'pantalla.png'
SCREENSHOT_PATH = os.path.join(SCREENSHOT_DIR, SCREENSHOT_FILENAME)

def take_screenshot():
    """
    Toma una captura de pantalla del monitor principal y la guarda.
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    with mss.mss() as sct:
        # Get information of monitor 1 (primary monitor)
        # sct.monitors[0] is all monitors combined
        # sct.monitors[1] is typically the primary monitor
        # If you have multiple monitors and want to target a specific one,
        # you might need to adjust this index (e.g., sct.monitors[2] for a second external monitor)
        # For most single-monitor setups, [1] is the correct choice.
        monitor = sct.monitors[1] # Cambiado de [2] a [1]

        # Grab the data
        sct_img = sct.grab(monitor)

        # Save to the picture file
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=SCREENSHOT_PATH)
    
    print(f"INFO: Captura de pantalla guardada en: {SCREENSHOT_PATH}", flush=True)
    sys.stdout.flush() # Forzar el flush
    

if __name__ == "__main__":
    print("--- Tomando captura de pantalla ---", flush=True)
    sys.stdout.flush()
    take_screenshot()
    print("--- Captura de pantalla finalizada ---", flush=True)
    sys.stdout.flush()

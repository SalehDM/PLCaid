import mss
import mss.tools
import os
import time

# Directorio donde se guardarán las capturas de pantalla
SCREENSHOT_DIR = "screenshots"
SCREENSHOT_FILE = os.path.join(SCREENSHOT_DIR, "pantalla.png")

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
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=SCREENSHOT_FILE)
    
    print(f"INFO: Captura de pantalla guardada en: {SCREENSHOT_FILE}")

if __name__ == "__main__":
    print("--- Tomando captura de pantalla ---")
    take_screenshot()
    print("--- Captura de pantalla finalizada ---")

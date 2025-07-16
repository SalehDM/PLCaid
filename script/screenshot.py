import mss
import os
from PIL import Image

with mss.mss() as sct:
    # Captura la pantalla completa (monitor principal)
    monitor = sct.monitors[2]
    sct_img = sct.grab(monitor)

    # Convierte la imagen a formato compatible con PIL
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    # Directorio para guardar la captura
    output_dir = os.path.join("..", "screenshots")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "pantalla.png")

    # Guarda la imagen
    img.save(output_file)
    print(f"Captura de pantalla guardada como '{output_file}'.")
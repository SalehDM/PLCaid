import mss
from PIL import Image

with mss.mss() as sct:
    # Captura la pantalla completa (monitor principal)
    monitor = sct.monitors[2]
    sct_img = sct.grab(monitor)

    # Convierte la imagen a formato compatible con PIL
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    # Guarda la imagen
    img.save("/home/reboot-student/Desktop/project_PLC/PLCaid/screenshots/pantalla.png")
    print("Captura de pantalla guardada como 'pantalla.png'.")
    
import pyautogui
import time
import os

# Espera 2 segundos para darte tiempo a cambiar de ventana si es necesario
time.sleep(2)

# Ruta a la imagen en la carpeta capture (un nivel arriba)
image_path = os.path.abspath(os.path.join(os.getcwd(), 'capture', 'image.png'))

# Encuentra un objeto en la pantalla usando la ruta
location = pyautogui.locateOnScreen(image_path, confidence=0.8)

if location:
    # Obtiene las coordenadas del centro del objeto
    center_x, center_y = pyautogui.center(location)
    print(f"✔ Coordenadas del centro del objeto: x={center_x}, y={center_y}")

    # Mueve el mouse al centro del objeto y hace clic
    pyautogui.moveTo(center_x, center_y, duration=0.5)
    pyautogui.click()

    # texto = "Hola caracola!!!"
    # pyautogui.write(texto, interval=0.05)
    # print(f"✔ Escribiendo texto: {texto}")
else:
    print(f"❌ No se encontró la imagen en pantalla: {image_path}")
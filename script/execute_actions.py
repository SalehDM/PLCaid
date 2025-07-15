import pyautogui
import time

# Espera 2 segundos para darte tiempo a cambiar de ventana si es necesario
time.sleep(2)
x=2345
y=610

# Encuentra un objeto en la pantalla (ejemplo: una imagen)
location = pyautogui.locateOnScreen('image.png', confidence=0.8)

# Obtiene las coordenadas del centro del objeto
center_x, center_y = pyautogui.center(location)
print(f"Coordenadas del centro del objeto: x={center_x}, y={center_y}")

# Mueve el mouse al botón de cerrar y hace clic
pyautogui.moveTo(x, y, duration=0.5)
pyautogui.click()

texto="Hola caracola!!!"

pyautogui.write(texto, interval=0.05)
print(f"✔ Escribiendo texto: {texto}")

















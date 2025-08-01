import pyautogui
import time
import os

    
def action(step, action, texto_a_escribir=None):
    # Ruta a la imagen en la carpeta capture (un nivel arriba)
    image_path = os.path.abspath(os.path.join(os.getcwd(),"PLCaid", step))
    #image_path = os.path.abspath(os.path.join(os.getcwd(), step))
    
    time.sleep(5)

    # Encuentra un objeto en la pantalla usando la ruta
    location = pyautogui.locateOnScreen(image_path, confidence=0.8)
    if location:
        center_x = location.left + location.width / 2
        center_y = location.top + location.height / 2
        if action == "doubleClick":
            pyautogui.doubleClick(center_x, center_y)
        elif action == "texto":
            pyautogui.click(center_x, center_y)
            pyautogui.write(texto_a_escribir, interval=0.02)
        else:
            print("Acción no reconocida.")
    else:
        print("No se pudo localizar el elemento en la pantalla actual con la confianza dada.")











 










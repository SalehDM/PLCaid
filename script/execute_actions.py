import pyautogui
import os
import sys
import time
import traceback # Import traceback for detailed error info

# --- Configurar la codificación de la salida de la consola al inicio ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass
except Exception as e:
    print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}", flush=True)

# Ruta donde se espera encontrar la imagen a buscar y hacer clic
# Asumiendo que execute_actions.py está en 'script' y 'capture' está en la raíz
IMAGE_TO_CLICK_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'capture', 'image.png')

def click_on_image(image_path: str, confidence: float = 0.7): # Confianza reducida a 0.7
    """
    Busca una imagen en pantalla y hace clic en su centro.
    """
    if not os.path.exists(image_path):
        print(f"ERROR: No se encontro la imagen para hacer clic: {image_path}. Asegurate de que el script 'analizar_iconos.py' la haya generado correctamente.", flush=True)
        sys.stdout.flush()
        sys.exit(1) # Salir con error si la imagen no existe

    print(f"INFO: Buscando imagen '{image_path}' en pantalla con confianza {confidence}...", flush=True)
    sys.stdout.flush()
    try:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        
        if location:
            center_x, center_y = pyautogui.center(location)
            print(f"INFO: Imagen encontrada en {location}. Haciendo clic en el centro ({center_x}, {center_y}).", flush=True)
            sys.stdout.flush()
            pyautogui.click(center_x, center_y)
            return True
        else:
            try:
                # pyautogui.locateOnScreen no devuelve directamente la confianza máxima si no la encuentra.
                # La confianza más alta se reporta en la excepción, no directamente aquí.
                # Intentamos con baja confianza y escala de grises para obtener un mensaje de error más informativo de pyautogui.
                pyautogui.locateOnScreen(image_path, confidence=0.01, grayscale=True)
                print(f"WARNING: No se pudo localizar la imagen '{image_path}' con confianza {confidence}. Se encontró algo con muy baja confianza.", flush=True)
                sys.stdout.flush()
            except pyautogui.ImageNotFoundException as e:
                # Este es el caso más común cuando no se encuentra nada.
                print(f"WARNING: {e}", flush=True) # Mostrar el mensaje de error de pyautogui que incluye la confianza más alta
                sys.stdout.flush()
            sys.exit(1) # Salir con error si no se encuentra la imagen
    except Exception as e:
        print(f"ERROR: Ocurrio un error inesperado al intentar hacer clic en la imagen: {e}", flush=True)
        sys.stdout.flush()
        sys.exit(1) # Salir con error

def write_text(text: str):
    print(f"⌨️ Escribiendo texto: '{text}'", flush=True)
    sys.stdout.flush()
    pyautogui.write(text)
    print("INFO: Texto escrito.", flush=True)
    sys.stdout.flush()

def press_key(key: str):
    print(f"⬇️ Presionando tecla: '{key}'", flush=True)
    sys.stdout.flush()
    pyautogui.press(key)
    print("INFO: Tecla presionada.", flush=True)
    sys.stdout.flush()

if __name__ == "__main__":
    try: # <--- Added outer try-except block
        if len(sys.argv) > 1:
            action_type = sys.argv[1]
            
            if action_type == "click":
                print(f"INFO: Recibida orden de clic. Intentando hacer clic en {IMAGE_TO_CLICK_PATH}", flush=True)
                sys.stdout.flush()
                click_on_image(IMAGE_TO_CLICK_PATH)
            elif action_type == "write" and len(sys.argv) > 2:
                text_to_write = sys.argv[2]
                write_text(text_to_write)
            elif action_type == "press" and len(sys.argv) > 2:
                key_to_press = sys.argv[2]
                press_key(key_to_press)
            else:
                print("INFO: execute_actions.py ejecutado sin accion especifica o argumentos invalidos.", flush=True)
                print("Uso: python execute_actions.py [click|write|press] [argumento_opcional]", flush=True)
                sys.stdout.flush()
                sys.exit(1) # Salir con error si los argumentos son invalidos
        else:
            print(f"INFO: execute_actions.py ejecutado sin argumentos. Intentando hacer clic en {IMAGE_TO_CLICK_PATH}", flush=True)
            sys.stdout.flush()
            click_on_image(IMAGE_TO_CLICK_PATH)
    except Exception as e:
        print(f"CRITICAL ERROR in execute_actions.py main block: {e}", flush=True)
        traceback.print_exc(file=sys.stdout) # Print traceback to stdout
        sys.stdout.flush()
        sys.exit(1) # Ensure exit with error

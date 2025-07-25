from typing import Optional
import pyscreeze
from PIL import Image
from mss import mss
import screeninfo # Para obtener información detallada de los monitores

def take_screenshot(monitor_number: Optional[int] = None):
    """
    Toma una captura de pantalla.
    Args:
        monitor_number (int, optional): Índice del monitor a capturar (0 para el primer monitor físico, 1 para el segundo, etc.).
                                        Si es None, captura todos los monitores como una sola imagen.
    Returns:
        PIL.Image.Image: La imagen de la captura de pantalla.
    Raises:
        ValueError: Si el número de monitor es inválido.
    """
    with mss() as sct:
        monitors = sct.monitors
        # monitors[0] es la pantalla combinada de todos los monitores.
        # monitors[1], monitors[2], etc., son los monitores individuales.

        if monitor_number is not None:
            # Mapear el índice proporcionado (0 para el primer físico, etc.) al índice de mss (1 para el primero físico, etc.)
            mss_monitor_index = monitor_number + 1
            if not (0 < mss_monitor_index < len(monitors)):
                raise ValueError(
                    f"Número de monitor inválido: {monitor_number}. Monitores disponibles: 0 a {len(monitors) - 2}."
                    " (0 es el primer monitor físico, 1 el segundo, etc.)"
                )
            monitor_region = monitors[mss_monitor_index]
            print(f"Capturando el monitor {monitor_number} (región: {monitor_region})...")
        else:
            # Capturar todos los monitores
            monitor_region = monitors[0]
            print("Capturando todos los monitores...")

        sct_img = sct.grab(monitor_region)
        # Convertir la imagen de mss a un objeto PIL.Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img

def find_image_on_screen(template_image_path: str, screenshot_image: Image.Image, confidence: float = 0.9):
    """
    Busca una imagen (template) dentro de una imagen de captura de pantalla.
    Args:
        template_image_path (str): Ruta al archivo de imagen del recorte (template a buscar).
        screenshot_image (PIL.Image.Image): El objeto PIL.Image de la captura de pantalla completa o del monitor.
        confidence (float): Nivel de confianza para la detección de la imagen (0.0 a 1.0).
    Returns:
        tuple: Coordenadas (x, y, width, height) de la imagen encontrada, o None si no se encuentra.
    """
    try:
        # pyscreeze.locate puede tomar un objeto PIL.Image directamente
        location = pyscreeze.locate(template_image_path, screenshot_image, confidence=confidence)
        if location:
            print(f"Recorte '{template_image_path}' encontrado en la pantalla en: {location}")
            return location
        else:
            print(f"Recorte '{template_image_path}' NO encontrado en la pantalla con confianza {confidence}.")
            return None
    except pyscreeze.PyScreezeException as e:
        print(f"Error al buscar imagen '{template_image_path}': {e}. Asegúrate de que los archivos de imagen existan y sean válidos.")
        return None
    except Exception as e:
        print(f"Error inesperado en find_image_on_screen: {e}")
        return None

def get_monitor_info():
    """
    Obtiene información sobre los monitores conectados.
    Returns:
        list: Una lista de diccionarios, cada uno con información de un monitor.
              El índice 0 corresponde al primer monitor físico.
    """
    try:
        monitors_info = []
        monitors = screeninfo.get_monitors()
        for i, m in enumerate(monitors):
            # Asignamos un ID incremental a partir de 0 para los monitores físicos
            monitors_info.append({
                "id": i,
                "width": m.width,
                "height": m.height,
                "x": m.x,
                "y": m.y,
                "is_primary": m.is_primary,
                "name": m.name if hasattr(m, 'name') else f"Monitor {i}"
            })
        print("Información de monitores obtenida.")
        return monitors_info
    except Exception as e:
        print(f"Error al obtener información de los monitores: {e}")
        return []

# Ejemplo de uso (para pruebas directas de este módulo)
if __name__ == "__main__":
    print("--- Probando utilidades de pantalla (utils/screen_utils.py) ---")

    # Mostrar información de monitores
    mon_info = get_monitor_info()
    if mon_info:
        print("\nMonitores detectados:")
        for mon in mon_info:
            print(f"  ID: {mon['id']}, Nombre: {mon['name']}, Resolución: {mon['width']}x{mon['height']}, Posición: ({mon['x']},{mon['y']}), Primario: {mon['is_primary']}")
    else:
        print("No se pudo detectar información de monitores.")

    # Prueba de captura del primer monitor físico (si existe)
    if mon_info:
        try:
            print("\nIntentando capturar el primer monitor físico (ID 0)...")
            img_monitor_0 = take_screenshot(monitor_number=0)
            img_monitor_0.save("test_screenshot_monitor_0.png")
            print("Captura del monitor 0 guardada como 'test_screenshot_monitor_0.png'")
        except ValueError as e:
            print(e)
        except Exception as e:
            print(f"Error al capturar monitor 0: {e}")

    # Prueba de captura de pantalla completa
    try:
        print("\nIntentando capturar todos los monitores...")
        full_screenshot = take_screenshot()
        full_screenshot.save("test_full_screenshot.png")
        print("Captura completa guardada como 'test_full_screenshot.png'")
    except Exception as e:
        print(f"Error al capturar pantalla completa: {e}")

    # Para probar find_image_on_screen, necesitarías un recorte de prueba
    # y que la captura de pantalla completa exista.
    # Por ejemplo, si tienes 'papelera_reciclaje.png' y 'test_full_screenshot.png':
    # clipping_path = "papelera_reciclaje.png"
    # if os.path.exists(clipping_path) and os.path.exists("test_full_screenshot.png"):
    #     print(f"\nBuscando '{clipping_path}' en 'test_full_screenshot.png'...")
    #     found_loc = find_image_on_screen(clipping_path, full_screenshot)
    #     if found_loc:
    #         print(f"Encontrado en: {found_loc}")
    # else:
    #     print("\nPara probar find_image_on_screen, asegúrate de tener un recorte de imagen (ej. 'papelera_reciclaje.png')")
    #     print("y haber generado 'test_full_screenshot.png'.")
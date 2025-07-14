import pyautogui
import os
from datetime import datetime

os.makedirs("screenshots", exist_ok=True)
filename = f"screenshots/captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
screenshot = pyautogui.screenshot()
screenshot.save(filename)
print(f"Captura guardada en {filename}")

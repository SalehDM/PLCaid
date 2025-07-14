import json
import pyautogui
import time

with open("vision_outputs/output.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"Ejecutando clic en ({data['x']}, {data['y']})")
pyautogui.moveTo(data["x"], data["y"], duration=0.5)
pyautogui.click()
time.sleep(1)
pyautogui.screenshot(f"executions/post_click.png")
print("Captura tomada después del clic.")

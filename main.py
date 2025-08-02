import os
import json
import time

from script.execute_actions import action
from script.generador_scl import codificar_scl
from script.image_searcher import main_qdrant

time.sleep(4)
# Ruta absoluta del directorio raíz del proyecto (donde está main.py)
project_root = os.path.dirname(os.path.abspath(__file__))

steps_path = os.path.join(project_root, "parsed_steps", "steps.json")

with open(steps_path, "r", encoding="utf-8") as f:
    steps = json.load(f)

# Ejecutar bucle de pasos
total_steps = len(steps)
num_step = 0

while num_step < total_steps:
    step = steps[num_step]
    step_step = step["step"]
    step_action = step["action"]
    try:
        url_captura = main_qdrant(step_step)
        action(url_captura, step_action)
        num_step += 1
    except Exception as e:
        print(f"Esperando a que cargue: {e}")
        time.sleep(2)

order_path = os.path.join(project_root, "input_text", "order.txt")

with open(order_path, "r", encoding="utf-8") as f:
    order = f.read()

codigo_scl = codificar_scl(order)

print(codigo_scl)

action("../capture/i7.png", "texto", codigo_scl)

steps2_path = os.path.join(project_root, "parsed_steps", "steps2.json")

with open(steps2_path, "r", encoding="utf-8") as f:
    steps2 = json.load(f)

total_steps2 = len(steps2)
num_step2 = 0

while num_step2 < total_steps2:
    step = steps2[num_step2]
    step_step = step["step"]
    step_action = step["action"]
    try:
        time.sleep(1)
        action(step_step, step_action)
        print(step_step)
        num_step2 += 1
    except Exception as e:
        print(f"Esperando a que cargue: {e}")
        time.sleep(2)


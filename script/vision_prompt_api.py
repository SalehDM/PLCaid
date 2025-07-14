import json

# Simula que GPT Vision ha detectado coordenadas en la imagen
output = {
    "step": 1,
    "action": "click",
    "x": 250,
    "y": 400
}

with open("vision_outputs/output.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("Coordenadas guardadas en vision_outputs/output.json")

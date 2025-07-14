import os

print("""
==== GPT Clicker Assistant ====
1. Texto a pasos (NLP)
2. Captura de pantalla
3. Imagen + pasos → coordenadas
4. Ejecutar acciones
""")

opcion = input("Elige módulo a ejecutar (1-4): ")

if opcion == "1":
    os.system("python scripts/text_to_steps.py")
elif opcion == "2":
    os.system("python scripts/screenshot.py")
elif opcion == "3":
    os.system("python scripts/vision_prompt_api.py")
elif opcion == "4":
    os.system("python scripts/execute_actions.py")
else:
    print("Opción no válida.")
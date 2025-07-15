import subprocess

print("""
==== GPT Clicker Assistant ====
1. Audio a pasos 
2. Texto a pasos
3. Captura de pantalla
4. Imagen + pasos → coordenadas
5. Ejecutar acciones
""")

opcion = input("Elige módulo a ejecutar (1-5): ")

if opcion == "1":
    # Ejecuta voice_to_text_whisper.py y espera que termine
    result1 = subprocess.run(["python3", "script/voice_to_text_whisper.py"])
    if result1.returncode == 0:
        # Si el anterior terminó bien, ejecuta text_to_steps.py
        subprocess.run(["python3", "script/text_to_steps.py"])
    else:
        print("Error: voice_to_text_whisper.py no finalizó correctamente.")
elif opcion == "2":
    subprocess.run(["python3", "script/text_to_steps.py"])
elif opcion == "3":
    subprocess.run(["python3", "script/screenshot.py"])
elif opcion == "4":
    subprocess.run(["python3", "script/vision_prompt_api.py"])
elif opcion == "5":
    subprocess.run(["python3", "script/execute_actions.py"])
else:
    print("Opción no válida.")
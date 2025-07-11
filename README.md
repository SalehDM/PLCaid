# 🎯 Proyecto: Automatización basada en visión + entrada de texto/voz

## 🧠 Objetivo

Desarrollar un sistema que, dada una orden (escrita o hablada), sea capaz de:

1. **Capturar la pantalla**
2. **Analizarla visualmente** (GPT-4 Vision, manual o API)
3. **Determinar qué hacer** (clic, escribir, etc.)
4. **Ejecutar esa acción en pantalla**

Inicialmente trabajamos por **módulos separados** que luego uniremos de forma **manual** y finalmente **automática**.

---

## 📦 Estructura del proyecto

```bash
project-root/
│
├── input/                   # Entradas manuales: texto o voz
│   ├── text_orders/         # Archivos de texto con órdenes
│   └── voice_clips/         # Audios a transcribir (WAV, MP3)
│
├── parsed_steps/           # JSONs con pasos desglosados desde input
│
├── screenshots/            # Capturas de pantalla tomadas manual o automáticamente
│
├── vision_outputs/         # Output de GPT Vision: coordenadas o instrucciones por imagen
│
├── executions/             # Capturas después de ejecutar acciones
│
├── scripts/                # Todos los módulos funcionales
│   ├── text_to_steps.py
│   ├── voice_to_text.py
│   ├── screenshot.py
│   ├── vision_prompt.py
│   ├── execute_actions.py
│   └── orchestrate.py
│
├── README.md
└── requirements.txt
```
## ⚙️ Módulos funcionales

1. Entrada
text_to_steps.py
Toma una orden en texto y genera una lista de pasos en JSON.

voice_to_text.py
Transcribe una orden de voz usando Whisper o similar y guarda .txt.

2. Captura de pantalla
screenshot.py
Captura la pantalla o permite al usuario seleccionar un área. Guarda .png.

3. Visión artificial (manual con GPT-4V)
vision_prompt.py
Proporciona una plantilla de prompt para subir manualmente a ChatGPT.
El usuario pega luego el JSON de respuesta.

4. Ejecución automática
execute_actions.py
Recibe coordenadas desde un JSON y simula clics o escritura con pyautogui.

5. Orquestador (semiautomático / automático)
orchestrate.py
Conecta todas las partes en secuencia. Al principio manual, luego automático.

## 🔁 Flujo de trabajo modular (manual)

Escribir o grabar una orden → input/

Convertir a pasos con text_to_steps.py → parsed_steps/

Capturar pantalla con screenshot.py → screenshots/

Subir imagen + pasos manualmente a GPT-4V → guardar .json en vision_outputs/

Ejecutar acciones con execute_actions.py → logs en executions/

## 🔧 Requisitos

Python 3.9+

Paquetes (instalar con pip install -r requirements.txt)

pyautogui

openai

speechrecognition

pydub

whisper (si se usa entrada por voz)

pillow

## 🧪 Modo debug

Cada módulo puede ejecutarse de forma independiente con la bandera --debug para validar entrada/salida.

bash
Copiar
Editar
python scripts/text_to_steps.py --input input/text_orders/example.txt --debug

## 🚀 Objetivo de integración (semana 2)

La idea es que todo el sistema funcione con un único comando:

bash
Copiar
Editar
python scripts/orchestrate.py --input "Abre Google y busca clima en Madrid"
Que internamente haga: entrada → pasos → screenshot → GPT → coordenadas → ejecución.

## 📄 Licencia
MIT – Uso libre para fines de desarrollo, estudio y mejora de automatización con visión + LLM.

## 👥 Equipo
Proyecto desarrollado por 3 integrantes en 2 semanas. Cada módulo fue testeado individualmente y luego integrado paso a paso.


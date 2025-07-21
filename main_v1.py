import streamlit as st
import sounddevice as sd
from scipy.io.wavfile import write
import speech_recognition as sr
import numpy as np
import subprocess
import os
import time

# --- Configuración general ---
st.set_page_config(page_title="PLCaid", layout="centered")
st.title("🤖 Interfaz de Control para PLCaid")

# --- Estado de sesión ---
if "historial" not in st.session_state:
    st.session_state.historial = []

# --- Entrada de modo: texto o voz ---
modo = st.radio("Selecciona el modo de entrada:", ("📝 Texto", "🎙️ Voz"))

instruccion = ""

# --- Entrada por texto ---
if modo == "📝 Texto":
    texto = st.text_area("Escribe tus instrucciones aquí:", height=150, placeholder="Ej: abrir configuración\niniciar programa")
    if st.button("Enviar"):
        if texto.strip():
            instruccion = texto.strip()

# --- Entrada por voz ---
elif modo == "🎙️ Voz":
    if st.button("🎙️ Grabar voz (5 segundos)"):
        st.info("Grabando audio... habla ahora.")
        samplerate = 44100
        duration = 5  # segundos
        audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        audio_path = "temp_audio.wav"
        write(audio_path, samplerate, audio)

        # Transcribir
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
                transcripcion = recognizer.recognize_google(audio_data, language="es-ES")
                st.success("🗣️ Transcripción de voz:")
                st.write(transcripcion)
                instruccion = transcripcion
        except Exception as e:
            st.error(f"❌ Error en la transcripción: {e}")
        finally:
            os.remove(audio_path)

# --- Ejecutar main.py ---
if instruccion:
    st.info(f"🛠️ Ejecutando main.py con la orden: {instruccion}")
    try:
        resultado = subprocess.run(
            ["python", "main.py", instruccion],
            capture_output=True,
            text=True,
            check=True
        )
        st.text_area("🖨️ Salida de main.py", resultado.stdout, height=200)
        st.session_state.historial.append(instruccion)
    except subprocess.CalledProcessError as e:
        st.error(f"❌ Error ejecutando main.py:\n{e.stderr}")

# --- Historial ---
st.subheader("🕓 Historial de órdenes")
if st.session_state.historial:
    for idx, item in enumerate(reversed(st.session_state.historial), 1):
        st.write(f"{idx}. {item}")
    if st.button("🧹 Limpiar historial"):
        st.session_state.historial = []
        st.success("Historial limpiado.")
else:
    st.info("No hay órdenes registradas aún.")

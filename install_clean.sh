#!/bin/bash

echo "Desinstalando opencv-python, opencv-contrib-python, numpy y streamlit..."
pip uninstall -y opencv-python opencv-contrib-python numpy streamlit

echo "Instalando numpy compatible con las dependencias..."
pip install "numpy>=1.23,<2.0"

echo "Instalando opencv-python versión 4.8.1.78..."
pip install opencv-python==4.8.1.78

echo "Instalando resto de paquetes del requirements.txt sin numpy ni opencv-python..."
pip install --no-deps -r requirements.txt

echo "Instalación limpia completada."

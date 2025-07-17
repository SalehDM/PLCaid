# procesar_interfaz.py

import analizar_iconos  # Asegúrate de que esté en el mismo directorio o en el PYTHONPATH

def ejecutar_analisis():
    descripcion = "icono de compartir"  # Esta variable puede ser dinámica
    analizar_iconos.main(descripcion)

if __name__ == "__main__":
    ejecutar_analisis()

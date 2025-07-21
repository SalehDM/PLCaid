import os
from datetime import datetime
import sys # Importar sys para reconfigurar stdout/stderr

# --- Configurar la codificación de la salida de la consola al inicio ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass
except Exception as e:
    print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}", flush=True)

# Ruta al archivo donde se guardarán los recordatorios
REMINDERS_FILE = os.path.join(os.path.dirname(__file__), 'reminders.txt')

def create_reminder(text: str):
    """
    Crea un nuevo recordatorio y lo guarda en un archivo.
    """
    try:
        # Asegurarse de que el directorio exista
        os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
        with open(REMINDERS_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {text}\n")
        print(f"Recordatorio guardado: {text}", flush=True)
        sys.stdout.flush() # Forzar el flush
        return True
    except Exception as e:
        print(f"Error al guardar el recordatorio: {e}", flush=True)
        sys.stdout.flush() # Forzar el flush
        return False

def show_matching_reminders(query: str = None):
    """
    Muestra todos los recordatorios o aquellos que coincidan con una consulta.
    """
    reminders = []
    if not os.path.exists(REMINDERS_FILE):
        return []

    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    if query:
                        if query.lower() in line.lower():
                            reminders.append(line)
                    else:
                        reminders.append(line)
        return reminders
    except Exception as e:
        print(f"Error al leer recordatorios: {e}", flush=True)
        sys.stdout.flush() # Forzar el flush
        return []

if __name__ == "__main__":
    print("--- Probando generic_reminders.py ---", flush=True)
    sys.stdout.flush()
    create_reminder("Comprar leche")
    create_reminder("Llamar a Juan a las 10 AM")
    create_reminder("Revisar el PLC a las 3 PM")

    print("\nTodos los recordatorios:", flush=True)
    sys.stdout.flush()
    for r in show_matching_reminders():
        print(f"- {r}", flush=True)
        sys.stdout.flush()

    print("\nRecordatorios con 'PLC':", flush=True)
    sys.stdout.flush()
    for r in show_matching_reminders("PLC"):
        print(f"- {r}", flush=True)
        sys.stdout.flush()

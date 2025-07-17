import json
import os
import cv2

JSON_FILE = "iconos_descripciones.json"

def cargar_descripciones():
    if not os.path.exists(JSON_FILE):
        print(f"❌ No se encontró el archivo: {JSON_FILE}")
        return {}
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def buscar_iconos(keyword, descripciones):
    resultados = []
    for nombre, descripcion in descripciones.items():
        if keyword.lower() in descripcion.lower():
            resultados.append((nombre, descripcion))
    return resultados

def mostrar_imagen(ruta_imagen):
    if not os.path.exists(ruta_imagen):
        print(f"❌ No se encontró la imagen: {ruta_imagen}")
        return
    imagen = cv2.imread(ruta_imagen)
    if imagen is None:
        print(f"❌ No se pudo cargar la imagen: {ruta_imagen}")
        return
    cv2.imshow(f"Visualizando: {os.path.basename(ruta_imagen)}", imagen)
    print("Presiona cualquier tecla sobre la ventana de la imagen para cerrarla...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def manejar_visualizacion_imagen(resultados):
    ver_imagen = input("¿Quieres ver alguna imagen? Ingresa el número o 'no': ").strip()
    if ver_imagen.isdigit():
        idx = int(ver_imagen) - 1
        if 0 <= idx < len(resultados):
            ruta_imagen = os.path.join("iconos_recortados", resultados[idx][0])
            mostrar_imagen(ruta_imagen)
        else:
            print("❌ Número inválido.\n")
    else:
        print("Continuando sin mostrar imágenes.\n")

def mostrar_resultados(resultados):
    print(f"\n✅ {len(resultados)} resultado(s) encontrados:")
    for i, (nombre, descripcion) in enumerate(resultados, start=1):
        print(f"{i}. 📁 {nombre}:\n   📝 {descripcion}\n")

def main():
    print("🔎 Buscador de íconos por palabra clave\n")
    descripciones = cargar_descripciones()
    if not descripciones:
        return

    while True:
        keyword = input("🔤 Ingresa una palabra clave (o escribe 'salir'): ").strip()
        if keyword.lower() == "salir":
            print("👋 Fin de la búsqueda.")
            break

        resultados = buscar_iconos(keyword, descripciones)
        if resultados:
            mostrar_resultados(resultados)
            manejar_visualizacion_imagen(resultados)
        else:
            print("❌ No se encontraron coincidencias.\n")

if __name__ == "__main__":
    main()

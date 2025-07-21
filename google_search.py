import dataclasses
from typing import Union, Dict, List
import sys # Importar sys para reconfigurar stdout/stderr

# --- Configurar la codificación de la salida de la consola al inicio ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass
except Exception as e:
    print(f"WARNING: No se pudo reconfigurar la codificacion de la consola: {e}", flush=True)

# Definiciones de dataclasses para estructurar los resultados (como en la API de Google Search)
@dataclasses.dataclass
class PerQueryResult:
    index: str | None = None
    publication_time: str | None = None
    snippet: str | None = None
    source_title: str | None = None
    url: str | None = None


@dataclasses.dataclass
class SearchResults:
    query: str | None = None
    results: Union[List["PerQueryResult"], None] = None


def search(queries: List[str] | None = None) -> List[SearchResults]:
    """
    Simula una búsqueda en Google. Para una implementación real,
    aquí se integraría una API de búsqueda web (ej. Google Custom Search API, SerpApi).
    """
    if not queries:
        return []

    all_results = []
    for query in queries:
        print(f"Simulando búsqueda para: '{query}'", flush=True)
        sys.stdout.flush() # Forzar el flush
        # Aquí iría la lógica real para llamar a una API de búsqueda.
        # Por ahora, devolvemos resultados de ejemplo.

        if "capital de francia" in query.lower():
            simulated_results = [
                PerQueryResult(
                    index="1",
                    source_title="Wikipedia",
                    snippet="París es la capital de Francia y su ciudad más poblada.",
                    url="https://es.wikipedia.org/wiki/Par%C3%ADs"
                )
            ]
        elif "fecha de navidad" in query.lower():
            simulated_results = [
                PerQueryResult(
                    index="1",
                    source_title="Calendario",
                    snippet="La Navidad se celebra anualmente el 25 de diciembre.",
                    url="https://example.com/navidad"
                )
            ]
        elif "plc" in query.lower() and "programar" in query.lower():
            simulated_results = [
                PerQueryResult(
                    index="1",
                    source_title="Siemens",
                    snippet="La programación de PLCs Siemens se realiza con TIA Portal.",
                    url="https://www.siemens.com/tia-portal"
                ),
                PerQueryResult(
                    index="2",
                    source_title="Rockwell Automation",
                    snippet="Studio 5000 es el software para programar PLCs Allen-Bradley.",
                    url="https://www.rockwellautomation.com/studio5000"
                )
            ]
        else:
            simulated_results = [
                PerQueryResult(
                    index="1",
                    source_title="Ejemplo.com",
                    snippet=f"No se encontraron resultados reales para '{query}'. Esto es un resultado simulado.",
                    url="https://example.com/simulado"
                )
            ]
        
        all_results.append(SearchResults(query=query, results=simulated_results))
    
    return all_results

if __name__ == "__main__":
    print("--- Probando google_search.py ---", flush=True)
    sys.stdout.flush()
    
    # Ejemplo de búsqueda de la capital de Francia
    results1 = search(queries=["capital de francia"])
    print("\nResultados para 'capital de francia':", flush=True)
    sys.stdout.flush()
    for rs in results1:
        for res in rs.results:
            print(f"Título: {res.source_title}, Snippet: {res.snippet}, URL: {res.url}", flush=True)
            sys.stdout.flush()

    # Ejemplo de búsqueda de la fecha de Navidad
    results2 = search(queries=["fecha de navidad"])
    print("\nResultados para 'fecha de navidad':", flush=True)
    sys.stdout.flush()
    for rs in results2:
        for res in rs.results:
            print(f"Título: {res.source_title}, Snippet: {res.snippet}, URL: {res.url}", flush=True)
            sys.stdout.flush()

    # Ejemplo de búsqueda de programación de PLC
    results3 = search(queries=["cómo programar un plc"])
    print("\nResultados para 'cómo programar un plc':", flush=True)
    sys.stdout.flush()
    for rs in results3:
        for res in rs.results:
            print(f"Título: {res.source_title}, Snippet: {res.snippet}, URL: {res.url}", flush=True)
            sys.stdout.flush()

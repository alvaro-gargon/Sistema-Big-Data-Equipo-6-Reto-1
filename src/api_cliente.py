import requests

API_URL = "http://10.201.59.248:28000/api/v1/urgencias/novedades"


def consultar_novedades() -> dict:
    """Consulta la API y devuelve las novedades como un diccionario."""
    respuesta = requests.get(API_URL, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()

    if not isinstance(datos, dict):
        raise ValueError("La respuesta de la API no es un objeto JSON")
    return datos


datos = consultar_novedades()
print(datos)
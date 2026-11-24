import requests
import time
import triage_redis as tr
API_URL = "http://10.201.59.248:28000/api/v1/urgencias/novedades"
#API_URL ="http://host.docker.internal:8000/consultar"

def consultar_novedades() -> dict:
    """Consulta la API y devuelve las novedades como un diccionario."""
    respuesta = requests.get(API_URL, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()

    if not isinstance(datos, dict):
        raise ValueError("La respuesta de la API no es un objeto JSON")
    return datos

while True:
    novedades=consultar_novedades()

    if novedades["nuevos_ingresos"]:
        for nuevo in novedades["nuevos_ingresos"]:
            dic_nuevo={
                "id_episodio":nuevo["id_episodio"],
                "sip_paciente":nuevo["datos_admision"]["sip_paciente"],
                "nombre":nuevo["datos_admision"]["nombre"],
                "timestamp_llegada":nuevo["datos_admision"]["timestamp_llegada"],
                "tiempo_max_espera_min":nuevo["datos_triaje"]["tiempo_max_espera_min"]
            }
            tr.manejar_hashes(dic_nuevo)
    if novedades["pacientes_alta"]:
        for alta in novedades["pacientes_alta"]:
            num_box=tr.buscar_paciente(alta["id_episodio"])
            tr.delete_boxes(num_box)
            tr.de_cola_a_box()

    time.sleep(5)
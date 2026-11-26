import requests
import time
import triage_redis as tr
from pymongo import MongoClient
import config

API_URL = "http://10.201.59.248:28000/api/v1/urgencias/novedades"
#API_URL ="http://host.docker.internal:8000/consultar"

# Conexión con MongoDB
cliente = MongoClient(config.CONEXIONMONGO)
db = cliente[config.BD]
coleccion = db[config.COLECCION]

def consultar_novedades() -> dict:
    """Consulta la API y devuelve las novedades como un diccionario."""
    respuesta = requests.get(API_URL, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()

    if not isinstance(datos, dict):
        raise ValueError("La respuesta de la API no es un objeto JSON")
    return datos

def llamamiento_api():
    while True:
        novedades=consultar_novedades()
        print(novedades)
        if novedades["nuevos_ingresos"]:
            for nuevo in novedades["nuevos_ingresos"]:

                documento_clinico = {
                    "id_episodio": nuevo["id_episodio"],
                    **nuevo["datos_admision"],
                    "triaje_manchester": nuevo["datos_triaje"]
                }

                tr.guardar_documento_clinico(documento_clinico)

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
                id_episodio = alta["id_episodio"]

                num_box=tr.buscar_paciente(alta["id_episodio"])
                if num_box is None:
                    continue

                documento = tr.obtener_documento_clinico(id_episodio)
                if documento is None:
                    continue

                # Añadimos la información del alta médica.
                documento["timestamp_alta"] = alta["timestamp_alta"]
                documento["fecha_hora_alta"] = alta["fecha_hora_alta"]
                documento["destino_alta"] = alta["destino_alta"]

                coleccion.insert_one(documento)

                tr.delete_boxes(num_box)
                tr.eliminar_documento_clinico(id_episodio)

                tr.de_cola_a_box()

        time.sleep(5)
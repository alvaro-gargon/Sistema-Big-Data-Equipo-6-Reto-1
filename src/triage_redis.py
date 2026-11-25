import redis
import json

# Establecer conexión con el servidor local
r = redis.Redis(
    host='redis',
    port=6379,
    db=0,                   
    decode_responses=True
)
# clave que se utilizara en las colas
clave_urgencias="urgencias:cola_espera"

# Guarda en Redis el documento clínico completo del paciente.
# Se utiliza JSON porque el documento contiene diccionarios y listas.
def guardar_documento_clinico(documento):
    clave = f'episodio:{documento["id_episodio"]}'
    r.set(clave, json.dumps(documento))

# Recupera el documento clínico completo de un paciente.
def obtener_documento_clinico(id_episodio):
    clave = f'episodio:{id_episodio}'
    datos = r.get(clave)

    if datos is None:
        return None

    return json.loads(datos)

# Elimina el documento clínico completo de Redis.
def eliminar_documento_clinico(id_episodio):
    r.delete(f'episodio:{id_episodio}')

# Funcion que añade a la cola un nuevo paciente/episodio
def añadir_cola(diccionario):
    puntuacion={
        json.dumps(diccionario):float(diccionario["timestamp_llegada"])+(float(diccionario["tiempo_max_espera_min"])*60)
    }
    r.zadd(clave_urgencias,puntuacion)

# Funcion que coge el elemento de la cola con menor score y lo mete a los boxes
def de_cola_a_box():
    mas_urgente=r.zpopmin(clave_urgencias)
    #zpopmin devuelve una tupla (datos,score)
    if mas_urgente:
        datos=mas_urgente[0][0]
        diccionario=json.loads(datos)
        manejar_hashes(diccionario)

# Funcion cuyo proposito es buscar si hay hueco en los boxes, y si no lo hay, meter a la lista de espera
def manejar_hashes(diccionario):
    for i in range(1,6):
        clave=f"box:{i}"
        if not r.exists(clave):
            add_boxes(i,diccionario)
            return 'Hueco disponible asignado'
    añadir_cola(diccionario)
    return 'Añadido a la cola de espera'

# Funcion simple que solo mete los datos en el hash con el numero que le corresponda
def add_boxes(num_hash,datos):
    r.hset('box:'+str(num_hash),mapping=datos)
    r.set(f'id_episodio:{datos["id_episodio"]}', f'box:{num_hash}') #crea una relacion que relaciona el id del episodio con el hash del paciente, para poder hacer get mas tarde

def delete_boxes(num_hash):
    clave=f'box:{num_hash}'
    datos=r.hgetall(clave)

    if not datos:
        return None
    
    r.delete(f'id_episodio:{datos["id_episodio"]}') #al igual que se crea la relacion, se borra (No se borra automaticamente al borrar el hash)
    r.delete('box:'+str(num_hash))

    return datos

def buscar_paciente(id_episodio):
    clave=r.get("id_episodio:"+str(id_episodio))
    if clave is None:
        return "No se ha encontrado al paciente"
    return clave.split(":")[1]
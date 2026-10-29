import io
import requests as request
import pandas as pd
import json

# Funcion para descargar csv y cargar los datos en un dataframe de pandas
def descargar_csv(url):
    ### Lineas comentadas para su funcionamiento en uso local, se descomentarán en el servidor
    #descarga=request.get("/data/admisiones_historico")

    #with open('../data/admisiones_historico.csv', 'wb') as f:
    #   f.write(descarga.content)
    ###

    df_csv = pd.read_csv(
        "../data/admisiones_historico.csv",
        index_col="id_episodio", 
        na_values=["ERROR", "SIN_DATO", "N/D", "s/d", "NULL"], 
        on_bad_lines='warn', 
        engine='python', 
        parse_dates=["timestamp_llegada","timestamp_alta"],
        dayfirst=True)

    print("DataFrame leído:")
    print(df_csv)

# Funcion para descargar Json y cargar los dastos en un dataframe de pandas
def descargar_json(url):
# Se lee el json de la fuente correspondiente
    respuesta = request.get(url)
    if respuesta.status_code == 200:
        datos_json = respuesta.json()
    # Descargamos el archivo
        with open('archivo_descargado.json', 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=4)
        print('¡JSON descargado y guardado con éxito!')
    else:
        print(f'Error en la petición: {respuesta.status_code}')


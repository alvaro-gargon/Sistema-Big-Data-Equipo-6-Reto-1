import io
import requests as request
import pandas as pd
import numpy as np
import json

# Funcion para descargar csv y cargar los datos en un dataframe de pandas
def descargar_csv(url):
    ### Lineas comentadas para su funcionamiento en uso local, se descomentarán en el servidor
    #descarga=request.get("/data/admisiones_historico.csv")

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


# Función para eliminar los datos duplicados del csv.
def elimina_duplicados(df):
    df.drop_duplicates(subset=["id_episodio","sip_paciente","timestamp_llegada","timestamp_alta"])
    return df


# Función que comprueba las fechas de alta y las corrige si son anteriores a la de llegada
def corrige_fecha_alta(df):
    df["timestamp_llegada"] = pd.to_datetime(
        df["timestamp_llegada"], errors="coerce"
    )
    df["timestamp_alta"] = pd.to_datetime(
        df["timestamp_alta"], errors="coerce"
    )

    validos = df["timestamp_alta"] > df["timestamp_llegada"]

    estancias_validas_horas = (
        df.loc[validos, 'timestamp_alta'] - df.loc[validos, 'timestamp_llegada']
    ).dt.total_seconds() / 3600

    estancia_media_horas = estancias_validas_horas.mean()
    timed_media = pd.to_timedelta(estancia_media_horas, unit='hours')

    df["timestamp_alta"] = np.where(
        df["timestamp_alta"] < df["timestamp_llegada"],
        df["timestamp_llegada"] + timed_media,
        df["timestamp_alta"]
    )

    return df

# Función para gestionar las frecuencias cardiacas fuera de rango
def frecuencias_fuera_rango(df):
    pd.to_numeric(df["frecuencia_cardiaca"], erros="coerce")

    Q1 = df["frecuencia_cardiaca"].quantile(0.25)
    Q3 = df["frecuencia_cardiaca"].quantile(0.75)
    IQR = Q3-Q1

    limite_inferior = Q1 - 1.5 * IQR
    limite_superior = Q3 + 1.5 * IQR

    print(f"Límites lógicos de FC: {limite_inferior:.1f} a {limite_superior:.1f}")

    df["frecuencia_cardiaca"] = np.where(
        (df["frecuencia_cardiaca"] < limite_inferior)
        | (df["frecuencia_cardiaca"] > limite_superior),
        np.nan,
        df["frecuencia_cardiaca"],
    )

    return df
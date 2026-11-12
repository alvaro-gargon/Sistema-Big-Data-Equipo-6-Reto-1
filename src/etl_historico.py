import io
import requests as request
import pandas as pd
import numpy as np
import json
from pathlib import Path
from pymongo import MongoClient
import config


RUTA_DATA = Path(__file__).resolve().parent.parent / "data"
RUTA_CSV = RUTA_DATA / "admisiones_historico.csv"
# Funcion para descargar csv y cargar los datos en un dataframe de pandas
def descargar_csv(url):
    ### Lineas comentadas para el funcionamiento en uso local, se descomentarán en el servidor
    
    
    descarga=request.get(url,timeout=30)
    descarga.raise_for_status()

    with open(RUTA_CSV, 'wb') as f:
       f.write(descarga.content)

    df_csv = pd.read_csv(
        RUTA_CSV,
        index_col="id_episodio", 
        na_values=["ERROR", "SIN_DATO", "N/D", "s/d", "NULL"], 
        on_bad_lines='warn', 
        engine='python', 
        parse_dates=["timestamp_llegada","timestamp_alta"],
        dayfirst=True)

    print("DataFrame leído")
    return df_csv

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

def auditar(df):
    return pd.DataFrame({
        "tipo": df.dtypes.astype(str),        # TODO
        "nulos": df.isna().sum(),       # TODO
        "pct_nulos": ((df.isna().mean())*100).round(1),   # TODO
        "unicos": df.nunique(),      # TODO
    })


# Funcion que cambia los valores nulos cuando es posible por distintas calculaciones de medias o medianas
# fecha llegada, fecha alta, frecuancia cardiaca, tension arterial
def gestionar_valores_nulos(df):
    df["timestamp_llegada"] = pd.to_datetime(df["timestamp_llegada"],dayfirst=True,format="mixed",utc=True,errors="coerce")
    df["timestamp_alta"] = pd.to_datetime(df["timestamp_alta"],dayfirst=True,format="mixed",utc=True,errors="coerce")
    df["tension_arterial"] =pd.to_numeric(
        df["tension_arterial"], errors="coerce"
    )
    validos = (
        df["timestamp_llegada"].notna()
        & df["timestamp_alta"].notna()
        & (df["timestamp_alta"] > df["timestamp_llegada"])
        & df["frecuencia_cardiaca"].notna()
        & df["tension_arterial"].notna()
    )   

    estancia_media = (
        df.loc[validos, "timestamp_alta"] - df.loc[validos, "timestamp_llegada"]
    ).mean() 
    # Caso falta llegada, existe alta
    caso1 = df["timestamp_llegada"].isna() & df["timestamp_alta"].notna()
    df.loc[caso1, "timestamp_llegada"] = df.loc[caso1, "timestamp_alta"] - estancia_media

    # Caso falta alta, existe llegada
    caso2 = df["timestamp_alta"].isna() & df["timestamp_llegada"].notna()
    df.loc[caso2, "timestamp_alta"] = df.loc[caso2, "timestamp_llegada"] + estancia_media

    # Caso falta frecuencia cardiaca
    caso3 = df["frecuencia_cardiaca"].isna()
    df.loc[caso3,"frecuencia_cardiaca"]=df.loc[validos,"frecuencia_cardiaca"].median()

    # Caso falta tension arterial
    caso4 = df["tension_arterial"].isna()
    df.loc[caso4,"tension_arterial"]=df.loc[validos,"tension_arterial"].median()

    return df

# Función para eliminar los datos duplicados del csv.
def elimina_duplicados(df):
    df = df[~df.index.duplicated(keep="first")]
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
    pd.to_numeric(df["frecuencia_cardiaca"], errors="coerce")

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

def cruce_datos(df_csv):
    with open("../data/partes_clinicos.json", "r", encoding="utf-8") as archivo:
        datos_json = json.load(archivo)

    df_json = pd.DataFrame(datos_json)

    df_cruzados = pd.merge(df_csv, df_json, left_index=True, right_on="id_episodio", how="left")

    return df_cruzados

def carga_inicial_mongo(df_cruzados):
    documentos = df_cruzados.where(pd.notnull(df_cruzados), None).to_dict(orient="records")

    cliente = MongoClient(config.CONEXIONMONGO)
    db = cliente[config.BD]
    coleccion = db[config.COLECCION]

    if documentos:
        coleccion.insert_many(documentos)

def main():
    df_csv = descargar_csv("http://10.201.59.248:8088/admisiones_historico.csv")
    descargar_json("http://10.201.59.248:8088/partes_clinicos.json")

    df_csv = frecuencias_fuera_rango(df_csv)
    df_csv = corrige_fecha_alta(df_csv)
    df_csv = gestionar_valores_nulos(df_csv)
    df_csv = elimina_duplicados(df_csv)

    df_cruzados = cruce_datos(df_csv)
    carga_inicial_mongo(df_cruzados)

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
RUTA_JSON = RUTA_DATA / "partes_clinicos.json"
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
        with open(RUTA_JSON, 'w', encoding='utf-8') as f:
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

FORMATOS_FECHA = [
    "%d/%m/%Y %H:%M:%S",   # 30/08/2026 20:13:06
    "%d/%m/%Y %I:%M %p",   # 02/09/2026 01:26 PM
    "%d/%m/%Y %H:%M",      # por si aparece sin segundos
    "%Y/%m/%d %H:%M:%S",   # 2026/09/22 23:55:13
    "%Y-%m-%d %H:%M:%S",   # 2026-09-23 09:31:13
]

def parsear_fechas(serie):
    s = serie.astype("string").str.strip()
    resultado = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for fmt in FORMATOS_FECHA:
        pendientes = resultado.isna() & s.notna()
        if not pendientes.any():
            break
        resultado.loc[pendientes] = pd.to_datetime(
            s[pendientes], format=fmt, errors="coerce"
        )
    sin_parsear = s.notna() & resultado.isna()
    if sin_parsear.any():
        print(f"{serie.name}: {sin_parsear.sum()} valores sin parsear, ej.:",
              s[sin_parsear].unique()[:5])
    return resultado.dt.tz_localize("UTC")

def parsear_tension(df):
    ta = (df["tension_arterial"].astype("string")
          .str.extract(r"(\d+)\D+(\d+)"))   # acepta "/", "_", "-", etc.
    df["tension_sistolica"] = pd.to_numeric(ta[0], errors="coerce")
    df["tension_diastolica"] = pd.to_numeric(ta[1], errors="coerce")
    return df.drop(columns="tension_arterial")

# Funcion que cambia los valores nulos cuando es posible por distintas calculaciones de medias o medianas
# fecha llegada, fecha alta, frecuancia cardiaca, tension arterial
def gestionar_valores_nulos(df):
    df = df.copy()
    df["timestamp_llegada"] = parsear_fechas(df["timestamp_llegada"])
    df["timestamp_alta"] = parsear_fechas(df["timestamp_alta"])
    df["frecuencia_cardiaca"] = pd.to_numeric(df["frecuencia_cardiaca"], errors="coerce")
    df = parsear_tension(df)

    fechas_ok = (df["timestamp_llegada"].notna()
                 & df["timestamp_alta"].notna()
                 & (df["timestamp_alta"] > df["timestamp_llegada"]))
    if not fechas_ok.any():
        raise ValueError("Ninguna fila con fechas válidas")
    estancia_media = (df.loc[fechas_ok, "timestamp_alta"]
                      - df.loc[fechas_ok, "timestamp_llegada"]).mean()

    caso1 = df["timestamp_llegada"].isna() & df["timestamp_alta"].notna()
    df.loc[caso1, "timestamp_llegada"] = df.loc[caso1, "timestamp_alta"] - estancia_media

    caso2 = df["timestamp_alta"].isna() & df["timestamp_llegada"].notna()
    df.loc[caso2, "timestamp_alta"] = df.loc[caso2, "timestamp_llegada"] + estancia_media

    for col in ["frecuencia_cardiaca", "tension_sistolica", "tension_diastolica"]:
        df[col] = df[col].fillna(df[col].median())

    return df

# Función para eliminar los datos duplicados del csv.
def elimina_duplicados(df):
    df = df[~df.index.duplicated(keep="first")]
    return df

# Función que comprueba las fechas de alta y las corrige si son anteriores a la de llegada
def corrige_fecha_alta(df):

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
    print(config.CONEXIONMONGO)
    print(config.BD)
    print(config.COLECCION)
    if documentos:
        df_cruzados = df_cruzados.astype(object).where(df_cruzados.notna(), None)
        documentos = df_cruzados.to_dict("records")
        coleccion.insert_many(documentos)
        print("Documentos insertados")

def main():
    df_csv = descargar_csv("http://10.201.59.248:8088/admisiones_historico.csv")
    descargar_json("http://10.201.59.248:8088/partes_clinicos.json")

    df_csv = elimina_duplicados(df_csv)
    df_csv = frecuencias_fuera_rango(df_csv)
    df_csv = gestionar_valores_nulos(df_csv)
    df_csv = corrige_fecha_alta(df_csv)
    

    df_cruzados = cruce_datos(df_csv)
    carga_inicial_mongo(df_cruzados)
main()

import io
import requests as request
import pandas as pd
import json
from pathlib import Path


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

descargar_csv("http://10.201.59.248:8088/admisiones_historico.csv")

df_csv = pd.read_csv(
        RUTA_CSV,
        index_col="id_episodio", 
        na_values=["ERROR", "SIN_DATO", "N/D", "s/d", "NULL"], 
        on_bad_lines='warn', 
        engine='python', 
        parse_dates=["timestamp_llegada","timestamp_alta"],
        dayfirst=True)

def auditar(df):
    return pd.DataFrame({
        "tipo": df.dtypes.astype(str),        # TODO
        "nulos": df.isna().sum(),       # TODO
        "pct_nulos": ((df.isna().mean())*100).round(1),   # TODO
        "unicos": df.nunique(),      # TODO
    })

print(df_csv.info())
auditoria = auditar(df_csv)
print(auditoria)


#def gestionar_valores_nulos(df):

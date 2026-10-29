import io
import requests as request
import pandas as pd

#descarga=request.get("/data/admisiones_historico")

#with open('../data/admisiones_historico.csv', 'wb') as f:
#   f.write(descarga.content)

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
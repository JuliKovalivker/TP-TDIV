import pandas as pd

df = pd.DataFrame(columns=[
    "file_name",
    "tamano_original_bytes",
    "tamano_comprimido_bytes",
    "esta_comprimido",
    "ratio_compresion",
    "ratio_porcentaje",
    "tiempo"
])

df.to_csv("archivo_compresion.csv", index=False, encoding="utf-8")

print("CSV generado correctamente.")
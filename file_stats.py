import pandas as pd

def agregar_archivo(nombre, original, comprimido, esta_comprimido, tiempo):
    df = pd.read_csv('archivo_compresion.csv')
    if comprimido is None:
        df.loc[len(df)] = [
            nombre,
            original,
            comprimido,
            esta_comprimido,
            None,
            None,
            tiempo
        ]
        df.to_csv("archivo_compresion.csv", index=False, encoding="utf-8")
        return
    else:
        ratio = original / comprimido if comprimido != 0 else None
        ratio_pct = (1 - ratio) * 100 if ratio is not None else None
        df.loc[len(df)] = [
            nombre,
            original,
            comprimido,
            esta_comprimido,
            ratio,
            ratio_pct,
            tiempo
        ]
        df.to_csv("archivo_compresion.csv", index=False, encoding="utf-8")
        return

# Ejemplo de uso
# agregar_archivo("jk.txt", 8925, 8699, 1, 1)

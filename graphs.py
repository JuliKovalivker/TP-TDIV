import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("archivo_compresion.csv")

# Separar comprimidos y no comprimidos
df_c = df[df["esta_comprimido"] == True]
df_nc = df[df["esta_comprimido"] == False]

# Merge para comparar por archivo
df_merge = pd.merge(
    df_c[["file_name", "tamano_original_bytes", "tamano_comprimido_bytes", "tiempo"]],
    df_nc[["file_name", "tiempo"]],
    on="file_name",
    suffixes=("_comp", "_nocomp")
)

# ============================================
# Gráfico 1: Tamaño Original vs Comprimido
# ============================================
plt.figure(figsize=(12,6))
plt.bar(df_merge["file_name"], df_merge["tamano_original_bytes"], label="Original")
plt.bar(df_merge["file_name"], df_merge["tamano_comprimido_bytes"], label="Comprimido")
plt.xticks(rotation=90)
plt.title("Comparación de tamaños: Original vs Comprimido")
plt.ylabel("Bytes")
plt.legend()
plt.tight_layout()
plt.show()

# ============================================
# Gráfico 2: Tiempos de transferencia
# ============================================
plt.figure(figsize=(12,6))
plt.bar(df_merge["file_name"], df_merge["tiempo_comp"], label="Tiempo con compresión")
plt.bar(df_merge["file_name"], df_merge["tiempo_nocomp"], label="Tiempo sin compresión")
plt.xticks(rotation=90)
plt.title("Comparación de tiempos de transferencia")
plt.ylabel("Segundos")
plt.legend()
plt.tight_layout()
plt.show()

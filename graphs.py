import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ========================================
# Cargar dataset
# ========================================
df = pd.read_csv("archivo_compresion.csv")

# Extraer extensión
df["extension"] = df["file_name"].str.split(".").str[-1].str.lower()

# Clasificar tamaños
def clasificar_tamanio(valor):
    if valor <= 100_000:
        return "pequenio"
    elif valor <= 5_000_000:
        return "intermedio"
    else:
        return "grande"

df["categoria_tamanio"] = df["tamano_original_bytes"].apply(clasificar_tamanio)

# Crear carpeta de salida
output_folder = "plots"
os.makedirs(output_folder, exist_ok=True)

# ========================
# PALETA DE COLORES NUEVA
# ========================
color_no_comprimido = "#ef8fa2"   # azul vibrante
color_comprimido     = "#0f489e"  # verde divertido neon

color_ratio = {
    "pequenio":   "#0f489e", # azul vibrante
    "intermedio": "#3DACC3", # verde neon
    "grande":     "#ef8fa2"  # fucsia fuerte
}

categorias = ["pequenio", "intermedio", "grande"]

# ==========================================================
#   Gráficos de Tamaños (Original vs Comprimido)
# ==========================================================
for extension in df["extension"].unique():
    subset = df[df["extension"] == extension]

    bar_groups = []
    labels = []

    for cat in categorias:
        g = subset[subset["categoria_tamanio"] == cat]
        if g.empty:
            continue
        original_avg = g[~g["esta_comprimido"]]["tamano_original_bytes"].mean()
        compressed_avg = g[g["esta_comprimido"]]["tamano_comprimido_bytes"].mean()
        bar_groups.append([original_avg, compressed_avg])
        labels.append(cat)

    if not bar_groups:
        continue

    index = np.arange(len(bar_groups))
    width = 0.35

    plt.figure()
    plt.bar(index, [x[0] for x in bar_groups], width, label="No comprimido", color=color_no_comprimido)
    plt.bar(index + width, [x[1] for x in bar_groups], width, label="Comprimido", color=color_comprimido)

    plt.xticks(index + width/2, labels)
    plt.ylabel("Tamaño (bytes)")
    plt.title(f"Tamaños promedio {extension.upper()}")
    plt.legend()
    plt.savefig(os.path.join(output_folder, f"size_{extension}.png"))
    plt.close()

# ==========================================================
#   Gráficos de Tiempos (Comprimido vs No Comprimido)
# ==========================================================
for extension in df["extension"].unique():
    subset = df[df["extension"] == extension]

    bar_groups = []
    labels = []

    for cat in categorias:
        g = subset[subset["categoria_tamanio"] == cat]
        if g.empty:
            continue

        time_no = g[~g["esta_comprimido"]]["tiempo"].mean()
        time_yes = g[g["esta_comprimido"]]["tiempo"].mean()
        bar_groups.append([time_no, time_yes])
        labels.append(cat)

    if not bar_groups:
        continue

    index = np.arange(len(bar_groups))
    width = 0.35

    plt.figure()
    plt.bar(index, [x[0] for x in bar_groups], width, label="No comprimido", color=color_no_comprimido)
    plt.bar(index + width, [x[1] for x in bar_groups], width, label="Comprimido", color=color_comprimido)

    plt.xticks(index + width/2, labels)
    plt.ylabel("Tiempo (s)")
    plt.title(f"Tiempos promedio {extension.upper()}")
    plt.legend()
    plt.savefig(os.path.join(output_folder, f"time_{extension}.png"))
    plt.close()

# ==========================================================
#   Ratios agrupados por tipo (SIN TXT)
# ==========================================================
exts_no_txt = sorted([
    e for e in df["extension"].unique()
    if isinstance(e, str) and e.strip() != "" and e.lower() != "txt"
])

ratio_matrix_no_txt = []

for extension in exts_no_txt:
    sub = df[df["extension"] == extension]
    fila = []
    for cat in categorias:
        g = sub[sub["categoria_tamanio"] == cat]
        fila.append(g["ratio_compresion"].mean() if not g.empty else 0)
    ratio_matrix_no_txt.append(fila)

ratio_matrix_no_txt = np.array(ratio_matrix_no_txt)

x = np.arange(len(exts_no_txt))
width = 0.25

plt.figure(figsize=(10, 6))

for i, cat in enumerate(categorias):
    plt.bar(x + i*width, ratio_matrix_no_txt[:, i], width, label=cat, color=color_ratio[cat])

plt.xticks(x + width, exts_no_txt)
plt.ylabel("Ratio de compresión")
plt.title("Ratios de compresión por tipo (SIN TXT)")
plt.legend(title="Tamaño")
plt.savefig(os.path.join(output_folder, "ratio_grouped_no_txt.png"))
plt.close()

# ==========================================================
#   Ratios agrupados por tipo (CON TXT)
# ==========================================================
exts_full = sorted([
    e for e in df["extension"].unique()
    if isinstance(e, str) and e.strip() != ""
])

ratio_matrix_full = []

for extension in exts_full:
    sub = df[df["extension"] == extension]
    fila = []
    for cat in categorias:
        g = sub[sub["categoria_tamanio"] == cat]
        fila.append(g["ratio_compresion"].mean() if not g.empty else 0)
    ratio_matrix_full.append(fila)

ratio_matrix_full = np.array(ratio_matrix_full)

x = np.arange(len(exts_full))
width = 0.25

plt.figure(figsize=(10, 6))

for i, cat in enumerate(categorias):
    plt.bar(x + i*width, ratio_matrix_full[:, i], width,
            label=cat, color=color_ratio[cat])

plt.xticks(x + width, exts_full)
plt.ylabel("Ratio de compresión")
plt.title("Ratios de compresión por tipo (CON TXT)")
plt.legend(title="Tamaño")
plt.savefig(os.path.join(output_folder, "ratio_grouped.png"))
plt.close()


print("Gráficos generados con éxito en /plots")

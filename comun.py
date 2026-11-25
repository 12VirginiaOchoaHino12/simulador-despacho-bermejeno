"""Utilidades compartidas por las paginas: colores, estilo de graficos y etiquetas de origen de datos."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AZ, NA, GR, VE = "#1F4E79", "#D97B00", "#444444", "#2E7D32"

# Texto de los graficos: minimo 8 pt (observacion del docente)
plt.rcParams.update({"font.family": ["Arial", "Liberation Sans", "DejaVu Sans"], "font.size": 10,
                     "axes.labelsize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
                     "axes.spines.top": False, "axes.spines.right": False})

ETIQUETA_CATEGORIA = {
    "observado": "Observado", "historico": "Histórico (registros de la empresa)", "por_obtener": "Por obtener",
    "sintetico": "SINTÉTICO (supuesto, no observado)", "configurado": "Configurado (dato de la empresa)",
}


def coma(x, d=1):
    """Formatea con coma decimal."""
    return f"{x:.{d}f}".replace(".", ",")


def nueva_figura(ancho=6.4, alto=3.6):
    fig, ax = plt.subplots(figsize=(ancho, alto), dpi=150)
    return fig, ax


def formato_df(df, decimales=2):
    """Copia del DataFrame con numeros flotantes redondeados, para mostrar."""
    out = df.copy()
    for c in out.columns:
        if out[c].dtype.kind == "f":
            out[c] = out[c].round(decimales)
    return out

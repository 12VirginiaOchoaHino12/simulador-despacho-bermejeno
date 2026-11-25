"""Utilidades compartidas por las paginas: colores, estilo de graficos y etiquetas de origen de datos."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLOR_PRINCIPAL = "#1F3A5F"   # color de la empresa
COLOR_SECUNDARIO = "#C8102E"  # color de acento
COLOR_FONDO = "#F7F8FA"
COLOR_TEXTO = "#1A1A1A"

AZ, NA, GR, VE = COLOR_PRINCIPAL, COLOR_SECUNDARIO, "#444444", "#2E7D32"

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


def aplicar_estilo():
    """Inyecta CSS estilo empresa para tarjetas, botones y separación de secciones.
    
    Debe llamarse desde app.py cuando ya existe el objeto st de Streamlit.
    En contextos donde st no está disponible (pruebas de importación), la función hace nada.
    """
    try:
        import streamlit as _st
        _st.markdown(
            """
            <style>
            .tarjeta {
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                margin-bottom: 1rem;
            }}
            .btn-principal > button {
                background-color: #1F3A5F;
                color: white;
                border-radius: 0.3rem;
                border: none;
                padding: 0.5rem 1rem;
                font-size: 1rem;
            }}
            .espacio {
                margin-top: 2rem;
                margin-bottom: 2rem;
            }}
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass
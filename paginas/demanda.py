"""Pagina de analisis de demanda y ocupacion (Tablas 26 a 30 y Figuras 13 a 15 del Capitulo IV)."""
import numpy as np
import streamlit as st

from scipy import stats

import analisis
from comun import AZ, GR, NA, VE, coma, formato_df, nueva_figura, aplicar_estilo
import matplotlib.pyplot as plt


def mostrar(conn, usuario):
    aplicar_estilo()
    st.header("Demanda y ocupación")
    solo_ok = st.checkbox("Usar solo registros con calidad OK", value=False, key="demanda_solo_ok")
    df = analisis.cargar_viajes(conn, solo_ok=solo_ok)
    if len(df) < 8:
        st.info("Se necesitan al menos 8 viajes para el análisis.")
        return
    t1, t2, t3, t4 = st.tabs(["Descriptiva", "Ocupación por tipo de hoja", "Distribución de la demanda",
                              "Día de la semana y escenarios"])
    with t1:
        st.subheader("Estadística descriptiva")
        st.dataframe(formato_df(analisis.descriptiva(df)), hide_index=True)
        w, p = analisis.normalidad(df["pasajeros_oruro"])
        st.write(f"Pasajeros de Oruro por salida: prueba de Shapiro–Wilk W = {coma(w, 3)}, p = {coma(p, 3)}.")
    with t2:
        _ocupacion_tipo(df)
    with t3:
        _distribucion(df)
    with t4:
        _dia_escenarios(df)


def _ocupacion_tipo(df):
    st.subheader("Ocupación real por tipo de hoja")
    fig, ax = nueva_figura(6.2, 3.8)
    rng = np.random.default_rng(2026)
    for i, (clave, g) in enumerate(df.groupby("tipo")):
        y = g["ocupacion"].values
        ax.boxplot(y, positions=[i], widths=0.45, showfliers=False, medianprops=dict(color=GR, lw=2))
        x = i + rng.uniform(-0.12, 0.12, len(y))
        m49 = g["capacidad"].values >= 49
        ax.scatter(x[~m49], y[~m49], s=24, color=AZ, alpha=.85, zorder=3, label="36 asientos" if i == 0 else None)
        if m49.any():
            ax.scatter(x[m49], y[m49], s=40, marker="D", color=NA, zorder=4, label="49 asientos")
    nombres = [f"{k}\n(n = {len(g)})" for k, g in df.groupby("tipo")]
    ax.set_xticks(range(len(nombres)))
    ax.set_xticklabels(nombres)
    ax.axhline(50, color="#888", ls="--", lw=1)
    ax.set_ylabel("Ocupación real (%)")
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    c = analisis.comparar_tipos(df)
    if c:
        st.write(f"Mediana Oruro→Bermejo: {coma(c['mediana_oruro_bermejo'])} % · recorrido completo: "
                 f"{coma(c['mediana_recorrido'])} % · U de Mann–Whitney = {coma(c['U'], 1)}, p = {coma(c['p'], 3)}.")


def _distribucion(df):
    st.subheader("Ajuste de distribuciones a los pasajeros de Oruro por salida")
    aj = analisis.ajustar_distribuciones(df["pasajeros_oruro"])
    st.dataframe(formato_df(aj[["Distribución", "Parámetros", "Valor p (K–S)", "AIC"]], 3), hide_index=True)
    st.caption("Los valores p son aproximados porque los parámetros se estiman con los mismos datos.")
    fila = aj[aj["Distribución"] == "Weibull"].iloc[0]
    x = df["pasajeros_oruro"].values
    fig, ax = nueva_figura()
    ax.hist(x, bins=np.arange(0, x.max() + 5, 4), density=True, color="#9DB8D2", edgecolor="white")
    xs = np.linspace(0.5, x.max() + 3, 200)
    ax.plot(xs, stats.weibull_min.pdf(xs, fila["_forma"], loc=0, scale=fila["_escala"]), color=NA, lw=2,
            label="Weibull")
    g = aj[aj["Distribución"] == "Gamma"].iloc[0]
    ax.plot(xs, stats.gamma.pdf(xs, g["_forma"], loc=0, scale=g["_escala"]), color=GR, lw=1.5, ls="--",
            label="Gamma")
    ax.set_xlabel("Pasajeros de Oruro por salida")
    ax.set_ylabel("Densidad")
    ax.legend(frameon=False)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _dia_escenarios(df):
    st.subheader("Pasajeros de Oruro por día de la semana")
    st.dataframe(formato_df(analisis.por_dia(df), 1), hide_index=True)
    p = analisis.pruebas_dia(df)
    st.write(f"Kruskal–Wallis entre los siete días: H = {coma(p['H'], 2)}, p = {coma(p['p_H'], 3)}. "
             f"U de Mann–Whitney (lunes a jueves, mediana {coma(p['mediana_lun_jue'])}; viernes a domingo, "
             f"mediana {coma(p['mediana_vie_dom'])}): U = {coma(p['U'], 1)}, p = {coma(p['p_U'], 3)}.")
    st.subheader("Escenarios de demanda")
    esc, p25, p75 = analisis.escenarios_demanda(df)
    st.dataframe(formato_df(esc, 1), hide_index=True)
    st.caption(f"Definidos con los percentiles 25 ({coma(p25, 0)}) y 75 ({coma(p75, 0)}) de los pasajeros de Oruro "
               "por salida; son datos reales, no sintéticos.")
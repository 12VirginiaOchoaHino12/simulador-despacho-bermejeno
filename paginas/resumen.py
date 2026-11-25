"""Pagina de inicio: indicadores generales de los registros."""
import streamlit as st

import analisis
from comun import AZ, coma, formato_df, nueva_figura


def mostrar(conn, usuario):
    st.header("Resumen de la operación")
    st.caption("Sucursal Oruro · salida Oruro–Tarija–Bermejo · Expreso El Bermejeño S.R.L.")
    solo_ok = st.checkbox("Usar solo registros con calidad OK", value=False, key="resumen_solo_ok")
    df = analisis.cargar_viajes(conn, solo_ok=solo_ok)
    if df.empty:
        st.info("Aún no hay viajes. Un administrador puede importar el Excel en la página Datos.")
        return
    r = analisis.resumen_general(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Viajes", r["viajes"])
    c2.metric("Pasajes vendidos", r["pasajeros"])
    c3.metric("Ocupación media", f"{coma(r['ocupacion_media'])} %")
    c4.metric("Registros por revisar", r["revisar"])

    st.subheader("Ocupación media por mes")
    mes = analisis.por_mes(df)
    fig, ax = nueva_figura()
    ax.bar(mes["Mes"], mes["ocupacion"], color=AZ)
    ax.axhline(50, color="#888", ls="--", lw=1)
    ax.text(len(mes) - 0.5, 51.5, "Mínimo (50 %)", ha="right", fontsize=9, color="#555")
    ax.set_ylabel("Ocupación (%)")
    ax.set_ylim(0, 100)
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    st.pyplot(fig)
    st.dataframe(formato_df(mes.rename(columns={"viajes": "Viajes", "pasajeros": "Pasajes",
                                                "pasajeros_oruro": "Pasajes Oruro", "ocupacion": "Ocupación (%)"})),
                 hide_index=True)

    st.subheader("Demora de salida observada")
    obs = analisis.demoras_observadas(conn)
    if obs.empty:
        st.write("Sin salidas observadas.")
    else:
        st.dataframe(obs, hide_index=True)
        st.caption("Observación exploratoria de 3 salidas (20 a 23 de octubre de 2026). "
                   "No alcanza para probar nada; sirve solo de referencia.")

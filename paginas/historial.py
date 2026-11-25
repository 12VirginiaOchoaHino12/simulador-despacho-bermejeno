"""Pagina de historial: corridas guardadas y bitacora de acciones."""
import json

import pandas as pd
import streamlit as st

import seguridad
import simulacion
from comun import formato_df


def mostrar(conn, usuario):
    st.header("Historial")
    corridas = simulacion.listar_corridas(conn)
    st.subheader("Corridas de simulación guardadas")
    if corridas.empty:
        st.info("Aún no hay corridas guardadas. Se guardan al comparar reglas.")
    else:
        st.dataframe(corridas, hide_index=True)
        ids = list(corridas["id"])
        elegido = st.selectbox("Ver resultados de la corrida n.º", ids, key="hist_corrida")
        fila = conn.execute("SELECT parametros_json, nota FROM corridas WHERE id = ?", (int(elegido),)).fetchone()
        st.json(json.loads(fila["parametros_json"]))
        st.caption(fila["nota"])
        res = simulacion.resultados_de_corrida(conn, int(elegido))
        st.dataframe(formato_df(res.drop(columns=["id", "corrida_id"])), hide_index=True)
    if seguridad.tiene_permiso(usuario["rol"], "bitacora"):
        st.subheader("Bitácora de acciones")
        bit = pd.read_sql_query("SELECT fecha, usuario, accion, detalle FROM bitacora ORDER BY id DESC LIMIT 200",
                                conn)
        st.dataframe(bit, hide_index=True)

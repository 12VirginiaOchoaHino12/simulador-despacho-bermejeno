"""Pagina 'Decision del dia': recomendacion en vivo para decidir si esperar o salir."""
import numpy as np
import streamlit as st

import db
import recomendacion
import simulacion
from comun import AZ, GR, NA, coma, formato_df, nueva_figura

COLORES = {"cumplida": "success", "esperar": "warning", "tope": "error"}
TITULOS = {"cumplida": "Se cumple la condición de salida", "esperar": "Esperar",
           "tope": "Se alcanzó la espera máxima"}


def mostrar(conn, usuario):
    st.header("Decisión del día: ¿esperar o salir?")
    st.write("Ingrese cómo está la salida en este momento. El sistema calcula la probabilidad de que lleguen los "
             "ausentes a tiempo y cuánto habría que esperar con la regla vigente.")
    st.info(recomendacion.NOTA)
    par, k_bd = simulacion.parametros_desde_bd(conn)
    c1, c2, c3 = st.columns(3)
    cap = int(c1.selectbox("Capacidad del bus", [36, 49]))
    minutos = float(c2.number_input("Minutos desde la citación (17:00 = 0)", 0.0, 120.0, 0.0, 1.0))
    k = int(c3.number_input("Umbral k (ausentes que se toleran)", 0, 30, int(k_bd), 1))
    c4, c5, c6 = st.columns(3)
    a_bordo = int(c4.number_input("Pasajeros a bordo desde La Paz", 0, 49, 0, 1))
    vendidos = int(c5.number_input("Pasajes vendidos en Oruro", 0, 49, 0, 1))
    presentes = int(c6.number_input("De ellos, ya presentes", 0, 49, 0, 1))
    if st.button("Evaluar", key="btn_evaluar"):
        estado = recomendacion.Estado(cap, a_bordo, vendidos, presentes, minutos)
        try:
            res = recomendacion.evaluar(estado, par, k)
        except ValueError as e:
            st.error(str(e))
            return
        st.session_state["decision_ultima"] = dict(
            estado=estado, k=k, res=res, par=par,
            alt=recomendacion.alternativas(estado, par), sens=recomendacion.sensibilidad_mu(estado, par, k))
        db.registrar_bitacora(conn, usuario["usuario"], "evaluar_decision",
                              f"estado={res['estado']} p={res['prob_antes_del_tope']:.3f}")
    ultima = st.session_state.get("decision_ultima")
    if ultima:
        _resultado(conn, usuario, ultima)


def _resultado(conn, usuario, u):
    res, estado, par, k = u["res"], u["estado"], u["par"], u["k"]
    getattr(st, COLORES[res["estado"]])(f"**{TITULOS[res['estado']]}.** {res['mensaje']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ausentes", res["ausentes"])
    c2.metric("Llegadas necesarias", res["llegadas_necesarias"])
    c3.metric("Prob. de cumplirse antes del tope", f"{coma(100 * res['prob_antes_del_tope'], 0)} %")
    c4.metric("Espera mediana (min)", "—" if res["espera_mediana"] is None else coma(res["espera_mediana"]))
    if res["estado"] == "esperar":
        st.write(f"Pasajeros-minuto de espera esperados (pasajeros a bordo × minutos de espera): "
                 f"**{coma(res['pasajeros_minuto'], 0)}**. Es una medida del costo de esperar sin estimar dinero.")
        _curva(estado, res, par, k)
    st.subheader("Probabilidad según el tiempo que se espere")
    h = res["horizontes"].rename(columns={"minutos": "Minutos más", "probabilidad": "Probabilidad"})
    h["Probabilidad"] = (100 * h["Probabilidad"]).round(1)
    st.dataframe(h, hide_index=True)
    st.subheader("¿Qué pasaría con otro umbral k?")
    alt = u["alt"].rename(columns={"estado": "Estado", "llegadas_necesarias": "Llegadas necesarias",
                                   "prob_antes_del_tope": "Prob. antes del tope", "espera_esperada": "Espera esperada (min)",
                                   "pasajeros_minuto": "Pasajeros-minuto"})
    st.dataframe(formato_df(alt), hide_index=True)
    st.subheader("Sensibilidad al retraso medio de los ausentes (parámetro sintético)")
    sens = u["sens"].rename(columns={"factor": "Factor", "retraso_medio": "Retraso medio (min)",
                                     "prob_antes_del_tope": "Prob. antes del tope",
                                     "espera_mediana": "Espera mediana (min)", "espera_esperada": "Espera esperada (min)"})
    st.dataframe(formato_df(sens), hide_index=True)
    st.caption("Si el retraso real de los ausentes es distinto del supuesto, la recomendación cambia así. "
               "Al registrar salidas reales, este parámetro se podrá estimar con datos.")
    st.subheader("Guardar esta consulta")
    decision = st.radio("¿Qué se decidió finalmente?", ["No registrar", "Se esperó", "Se salió"], key="decision_real")
    obs = st.text_input("Observaciones (opcional)", key="decision_obs")
    if st.button("Guardar consulta", key="btn_guardar_consulta"):
        valor = {"No registrar": None, "Se esperó": "espero", "Se salió": "salio"}[decision]
        cid = recomendacion.guardar_consulta(conn, usuario["id"], estado, res, k, valor, obs or None)
        db.registrar_bitacora(conn, usuario["usuario"], "guardar_consulta", f"id={cid}")
        st.success(f"Consulta guardada (n.º {cid}).")
    consultas = recomendacion.listar_consultas(conn)
    if not consultas.empty:
        with st.expander("Consultas guardadas"):
            st.dataframe(formato_df(consultas), hide_index=True)


def _curva(estado, res, par, k):
    r, a, mu = res["llegadas_necesarias"], res["ausentes"], par.mu_tarde
    tope = max(res["restante_hasta_tope"], 1.0)
    w = np.linspace(0, tope, 80)
    p = [100 * recomendacion.prob_cumple_en(x, r, a, mu) for x in w]
    fig, ax = nueva_figura(6.4, 3.4)
    ax.plot(w, p, color=AZ, lw=2)
    if res["espera_mediana"]:
        ax.axvline(res["espera_mediana"], color=NA, ls="--", lw=1.5)
        ax.text(res["espera_mediana"] + 0.2, 8, "mediana", color=NA, fontsize=9)
    ax.axhline(50, color=GR, lw=0.8, ls=":")
    ax.set_xlabel("Minutos de espera adicionales")
    ax.set_ylabel("Probabilidad de que se cumpla (%)")
    ax.set_ylim(0, 102)
    fig.tight_layout()
    st.pyplot(fig)

"""Pagina de simulacion: una regla, comparacion de reglas y sensibilidad de parametros."""
import streamlit as st

import db
import simulacion
from comun import AZ, ETIQUETA_CATEGORIA, GR, coma, formato_df, nueva_figura
from simulador_despacho import Parametros, Regla
import matplotlib.pyplot as plt

ESCENARIOS = {"Todos (Weibull completa)": "todos", "Baja (≤ P25)": "baja", "Habitual": "habitual",
              "Alta (≥ P75)": "alta"}
CAPACIDADES = {"36 asientos": 36, "49 asientos (móvil 500)": 49, "Flota real (36 y 49)": None}


def mostrar(conn, usuario):
    st.header("Simulación")
    st.warning("Los resultados son del **modelo** con parámetros **sintéticos** (supuestos, no observados). "
               "Muestran cómo se comportarían las reglas bajo esos supuestos; no demuestran una mejora real.")
    par_bd, k_bd = simulacion.parametros_desde_bd(conn)
    par, esc, cap, nrep, semilla = _controles(conn, par_bd)
    t1, t2, t3 = st.tabs(["Regla vigente", "Comparar reglas", "Sensibilidad"])
    with t1:
        _una_regla(par, k_bd, esc, cap, nrep, semilla)
    with t2:
        _comparar(conn, usuario, par, k_bd, esc, cap, nrep, semilla)
    with t3:
        _sensibilidad(par, k_bd, esc, cap, nrep, semilla)


def _controles(conn, par_bd):
    cats = db.leer_parametros(conn)[1]
    with st.expander("Parámetros del modelo (editables para esta corrida)", expanded=True):
        c1, c2, c3 = st.columns(3)
        p_punt = c1.number_input("Puntualidad (prob.)", 0.0, 1.0, float(par_bd.p_puntual), 0.05)
        mu = c2.number_input("Retraso medio de quien llega tarde (min)", 0.1, 60.0, float(par_bd.mu_tarde), 0.5)
        tope = c3.number_input("Espera máxima aceptada (min)", 0.0, 120.0, float(par_bd.tope), 1.0)
        c4, c5 = st.columns(2)
        cmin = c4.number_input("Cierre mínimo (min)", 0.0, 60.0, float(par_bd.cierre_min), 1.0)
        cmax = c5.number_input("Cierre máximo (min)", 0.0, 60.0, float(par_bd.cierre_max), 1.0)
        st.caption("Origen de cada parámetro: puntualidad, retraso, cierre y espera máxima → "
                   f"{ETIQUETA_CATEGORIA[cats['p_puntual']]}; demanda (Weibull) → "
                   f"{ETIQUETA_CATEGORIA[cats['weibull_forma']]}; mínimo y umbral → "
                   f"{ETIQUETA_CATEGORIA[cats['minimo_fraccion']]}.")
    c1, c2, c3, c4 = st.columns(4)
    esc = ESCENARIOS[c1.selectbox("Escenario de demanda", list(ESCENARIOS))]
    cap = CAPACIDADES[c2.selectbox("Capacidad", list(CAPACIDADES))]
    nrep = int(c3.number_input("Réplicas", 100, 5000, 1000, 100))
    semilla = int(c4.number_input("Semilla", 1, 999999, 1000, 1))
    par = Parametros(p_puntual=p_punt, mu_tarde=mu, cierre_min=cmin, cierre_max=cmax, tope=tope)
    return par, esc, cap, nrep, semilla


def _una_regla(par, k, esc, cap, nrep, semilla):
    if not st.button("Simular regla vigente", key="btn_vigente"):
        st.info("Ajuste los parámetros y pulse el botón.")
        return
    try:
        tabla = simulacion.comparar_reglas([Regla("Vigente", k, None)], esc, cap, nrep, semilla, par)
    except ValueError as e:
        st.error(str(e))
        return
    f = tabla.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Demora media (min)", coma(f["demora_media"]))
    c2.metric("Ocupación media", f"{coma(f['ocupacion_media'])} %")
    c3.metric("Salidas que esperaron", f"{coma(f['pct_espero'])} %")
    c4.metric("Salen sin el mínimo", f"{coma(f['pct_sin_minimo'])} %")
    res = simulacion._correr(Regla("Vigente", k, None), esc, cap, nrep, semilla, par)
    fig, ax = nueva_figura()
    ax.hist([r["demora"] for r in res], bins=30, color=AZ, edgecolor="white")
    ax.set_xlabel("Demora de salida (min)")
    ax.set_ylabel("Frecuencia")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _comparar(conn, usuario, par, k, esc, cap, nrep, semilla):
    st.write("Todas las reglas se evalúan con los **mismos números aleatorios**, así que la diferencia "
             "respecto de la vigente es una diferencia pareada.")
    predef = simulacion.reglas_predefinidas(k)
    nombres = [r.nombre for r in predef[1:]]
    elegidas = st.multiselect("Reglas a comparar con la vigente", nombres, default=nombres, key="reglas_sel")
    with st.expander("Agregar una regla propia"):
        c1, c2 = st.columns(2)
        k2 = int(c1.number_input("Umbral k (ausentes permitidos)", 0, 30, k, 1))
        t2 = c2.number_input("Espera máxima T (min; 0 = sin tope)", 0.0, 120.0, 0.0, 1.0)
        propia = st.checkbox("Incluir la regla propia", value=False, key="incluir_propia")
    etiqueta = st.text_input("Etiqueta de la corrida (opcional)", key="etiqueta_corrida")
    if not st.button("Comparar reglas", key="btn_comparar"):
        return
    reglas = [predef[0]] + [r for r in predef[1:] if r.nombre in elegidas]
    if propia:
        reglas.append(Regla(f"Propia (k={k2}, T={coma(t2, 0) if t2 else 'sin tope'})", k2, t2 or None))
    try:
        tabla = simulacion.comparar_reglas(reglas, esc, cap, nrep, semilla, par)
    except ValueError as e:
        st.error(str(e))
        return
    mostrar_tabla = formato_df(tabla.rename(columns={
        "demora_media": "Demora media", "demora_mediana": "Demora mediana", "ocupacion_media": "Ocupación (%)",
        "pct_espero": "% esperó", "pct_sin_minimo": "% sin mínimo", "dif_demora": "Dif. demora",
        "dif_ic_inf": "IC inf.", "dif_ic_sup": "IC sup.", "dif_ocupacion": "Dif. ocupación"}))
    st.dataframe(mostrar_tabla, hide_index=True)
    fig, ax = nueva_figura(6.6, 3.4)
    ax.barh(tabla["Regla"][::-1], tabla["demora_media"][::-1], color=AZ)
    ax.set_xlabel("Demora media simulada (min)")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    for linea in simulacion.explicar(tabla):
        st.write("• " + linea)
    cid = simulacion.guardar_corrida(conn, tabla, esc, cap, nrep, semilla, par, usuario["id"], etiqueta or None)
    db.registrar_bitacora(conn, usuario["usuario"], "comparar_reglas", f"corrida={cid}")
    st.success(f"Corrida guardada en el historial (n.º {cid}).")


def _sensibilidad(par, k, esc, cap, nrep, semilla):
    st.write("Se varía un parámetro sintético a la vez y se mide la mediana de la demora con la regla vigente.")
    if not st.button("Calcular sensibilidad", key="btn_sens"):
        return
    variaciones = {"mu_tarde": (max(0.1, par.mu_tarde * 0.6), par.mu_tarde * 2.0),
                   "cierre_max": (max(par.cierre_min, par.cierre_max - 3), par.cierre_max + 3),
                   "p_puntual": (max(0.0, par.p_puntual - 0.1), min(1.0, par.p_puntual + 0.1)),
                   "tope": (max(0.0, par.tope * 0.75), par.tope * 1.5)}
    try:
        tabla, base = simulacion.sensibilidad(Regla("Vigente", k, None), variaciones, esc, cap, nrep, semilla, par)
    except ValueError as e:
        st.error(str(e))
        return
    fig, ax = nueva_figura(6.6, 3.4)
    for i, (_, f) in enumerate(tabla[::-1].iterrows()):
        ax.barh(i, f["mediana_bajo"] - base, left=base, color="#7FA6D0", height=.55,
                label="Valor bajo" if i == 0 else None)
        ax.barh(i, f["mediana_alto"] - base, left=base, color="#E8A760", height=.55,
                label="Valor alto" if i == 0 else None)
    ax.axvline(base, color=GR, lw=1.5)
    ax.set_yticks(range(len(tabla)))
    ax.set_yticklabels(list(tabla["Parametro"][::-1]))
    ax.set_xlabel(f"Mediana de la demora (min); línea = base {coma(base)}")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.dataframe(formato_df(tabla), hide_index=True)

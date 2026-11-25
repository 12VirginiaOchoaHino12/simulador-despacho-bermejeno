"""Modulo de simulacion: conecta la base con el simulador de eventos discretos (simulador_despacho.py).

- Los parametros se leen de la base y conservan su categoria (sintetico, historico, configurado).
- Todas las reglas se evaluan con los mismos numeros aleatorios (semilla comun), de modo que la
  diferencia respecto de la regla vigente es una diferencia pareada.
- Los resultados son del MODELO con parametros sinteticos; no demuestran una mejora real en la empresa.
"""
import dataclasses
import json

import numpy as np
import pandas as pd
from scipy import stats

import simulador_despacho as sim
from simulador_despacho import Parametros, Regla

NOTA_SINTETICA = "Resultado del modelo con parámetros sintéticos; no es evidencia de la empresa."

# Rangos aceptados para los parametros editables (validacion de entradas)
LIMITES = {"p_puntual": (0.0, 1.0), "mu_tarde": (0.1, 60.0), "cierre_min": (0.0, 60.0),
           "cierre_max": (0.0, 60.0), "tope": (0.0, 120.0)}


def parametros_desde_bd(conn):
    """Lee los parametros del modelo desde la tabla 'parametros'."""
    vals = {f[0]: f[1] for f in conn.execute("SELECT clave, valor FROM parametros").fetchall()}
    return Parametros(p_puntual=vals["p_puntual"], mu_tarde=vals["mu_tarde"], cierre_min=vals["cierre_min"],
                      cierre_max=vals["cierre_max"], tope=vals["tope"]), int(vals["umbral_k"])


def validar_parametros(par):
    for clave, (lo, hi) in LIMITES.items():
        v = getattr(par, clave)
        if not lo <= v <= hi:
            raise ValueError(f"{clave} = {v} fuera del rango [{lo}, {hi}]")
    if par.cierre_min > par.cierre_max:
        raise ValueError("cierre_min no puede ser mayor que cierre_max")
    return par


def reglas_predefinidas(k_vigente=5):
    """Regla vigente y variantes para comparar (umbral k y espera maxima T)."""
    return [Regla("Vigente", k_vigente, None),
            Regla("k = 3", 3, None), Regla("k = 8", 8, None),
            Regla("T = 10 min", k_vigente, 10.0), Regla("T = 15 min", k_vigente, 15.0),
            Regla("T = 20 min", k_vigente, 20.0)]


def _ic95(x):
    x = np.asarray(x, float)
    if len(x) < 2:
        return float(x.mean()), float("nan"), float("nan")
    m, se = x.mean(), stats.sem(x)
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return float(m), float(m - h), float(m + h)


def _correr(regla, escenario, cap, nrep, seed0, par):
    """cap = 36 o 49; cap = None usa la flota real (36 asientos y el movil 500 de 49)."""
    if cap is None:
        return sim.correr_mezcla(regla, escenario, nrep, seed0, par)
    return sim.correr(regla, escenario, cap, nrep, seed0, par)


def resumen_corrida(res):
    d = np.array([r["demora"] for r in res], float)
    o = np.array([r["ocupacion"] for r in res], float)
    return dict(demora_media=float(d.mean()), demora_mediana=float(np.median(d)), ocupacion_media=float(o.mean()),
                pct_espero=100 * float(np.mean([r["espero"] for r in res])),
                pct_sin_minimo=100 * float(np.mean([r["sin_minimo"] for r in res])), _d=d, _o=o)


def comparar_reglas(reglas, escenario="todos", cap=36, nrep=1000, seed0=1000, par=None):
    """Compara reglas con numeros aleatorios comunes. La primera regla es la referencia (vigente)."""
    par = validar_parametros(par or sim.PARAMETROS_CALIBRADOS)
    if nrep < 2:
        raise ValueError("nrep debe ser al menos 2")
    if escenario not in ("todos", "baja", "habitual", "alta"):
        raise ValueError("escenario invalido")
    ref = None
    filas = []
    for regla in reglas:
        r = resumen_corrida(_correr(regla, escenario, cap, nrep, seed0, par))
        if ref is None:
            ref = r
        dd = r["_d"] - ref["_d"]
        do = r["_o"] - ref["_o"]
        m, lo, hi = _ic95(dd)
        filas.append(dict(Regla=regla.nombre, k=regla.umbral, T=regla.espera_max,
                          demora_media=r["demora_media"], demora_mediana=r["demora_mediana"],
                          ocupacion_media=r["ocupacion_media"], pct_espero=r["pct_espero"],
                          pct_sin_minimo=r["pct_sin_minimo"], dif_demora=m, dif_ic_inf=lo, dif_ic_sup=hi,
                          dif_ocupacion=float(do.mean())))
    return pd.DataFrame(filas)


def sensibilidad(regla, variaciones, escenario="todos", cap=36, nrep=1000, seed0=1000, par=None):
    """Sensibilidad de un parametro a la vez: mediana de la demora con el valor bajo y el alto.
    variaciones = {'cierre_max': (18.0, 23.0), ...}; el resto de parametros queda en su valor base."""
    par = validar_parametros(par or sim.PARAMETROS_CALIBRADOS)
    base = resumen_corrida(_correr(regla, escenario, cap, nrep, seed0, par))["demora_mediana"]
    filas = []
    for clave, (bajo, alto) in variaciones.items():
        if clave not in LIMITES:
            raise ValueError(f"Parametro no sensibilizable: {clave}")
        med = []
        for v in (bajo, alto):
            p2 = dataclasses.replace(par, **{clave: float(v)})
            if p2.cierre_min > p2.cierre_max:  # al subir cierre_min, se mueve cierre_max para mantener el orden
                p2 = dataclasses.replace(p2, cierre_max=p2.cierre_min)
            med.append(resumen_corrida(_correr(regla, escenario, cap, nrep, seed0, validar_parametros(p2)))["demora_mediana"])
        filas.append(dict(Parametro=clave, valor_bajo=bajo, valor_alto=alto, mediana_bajo=med[0], mediana_alto=med[1],
                          rango=abs(med[1] - med[0])))
    return pd.DataFrame(filas).sort_values("rango", ascending=False).reset_index(drop=True), base


def guardar_corrida(conn, tabla, escenario, cap, nrep, semilla, par, usuario_id=None, etiqueta=None):
    """Guarda la corrida y sus resultados en el historial."""
    cur = conn.execute(
        """INSERT INTO corridas (usuario_id, etiqueta, escenario, capacidad, nrep, semilla, parametros_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (usuario_id, etiqueta, escenario, int(cap or 0), int(nrep), int(semilla),
         json.dumps(dataclasses.asdict(par), sort_keys=True)))
    cid = cur.lastrowid
    for _, f in tabla.iterrows():
        conn.execute(
            """INSERT INTO resultados_regla (corrida_id, regla, umbral_k, espera_max_T, demora_media, demora_mediana,
                   ocupacion_media, pct_espero, pct_sin_minimo, dif_demora, dif_ic_inf, dif_ic_sup, dif_ocupacion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, f["Regla"], int(f["k"]), None if pd.isna(f["T"]) else float(f["T"]), float(f["demora_media"]),
             float(f["demora_mediana"]), float(f["ocupacion_media"]), float(f["pct_espero"]),
             float(f["pct_sin_minimo"]), None if pd.isna(f["dif_demora"]) else float(f["dif_demora"]),
             None if pd.isna(f["dif_ic_inf"]) else float(f["dif_ic_inf"]),
             None if pd.isna(f["dif_ic_sup"]) else float(f["dif_ic_sup"]), float(f["dif_ocupacion"])))
    conn.commit()
    return cid


def listar_corridas(conn):
    return pd.read_sql_query(
        """SELECT c.id, c.creado, COALESCE(u.usuario, '—') AS usuario, c.etiqueta, c.escenario, c.capacidad,
                  c.nrep, c.semilla FROM corridas c LEFT JOIN usuarios u ON u.id = c.usuario_id ORDER BY c.id DESC""", conn)


def resultados_de_corrida(conn, corrida_id):
    return pd.read_sql_query("SELECT * FROM resultados_regla WHERE corrida_id = ? ORDER BY id", conn,
                             params=[corrida_id])


def _n(x, d=1, signo=False):
    """Numero con coma decimal, como en el documento."""
    return (f"{x:+.{d}f}" if signo else f"{x:.{d}f}").replace(".", ",")


def explicar(tabla, umbral_practico=0.1):
    """Texto automatico de apoyo a la decision: describe, sin exagerar, que muestra la comparacion."""
    ref = tabla.iloc[0]
    lineas = [f"Con la regla {ref['Regla']} la demora media simulada es de {_n(ref['demora_media'])} min "
              f"y la ocupación media de {_n(ref['ocupacion_media'])} %."]
    for _, f in tabla.iloc[1:].iterrows():
        if abs(f["dif_demora"]) < umbral_practico:
            lineas.append(f"La regla {f['Regla']} prácticamente no cambia la demora respecto de la vigente "
                          f"(diferencia de {_n(f['dif_demora'], 2, True)} min).")
            continue
        sig = not (f["dif_ic_inf"] <= 0 <= f["dif_ic_sup"])
        sentido = "reduce" if f["dif_demora"] < 0 else "aumenta"
        base = (f"La regla {f['Regla']} {sentido} la demora en {_n(abs(f['dif_demora']))} min "
                f"(IC 95 %: {_n(f['dif_ic_inf'])} a {_n(f['dif_ic_sup'])}) y cambia la ocupación en "
                f"{_n(f['dif_ocupacion'], 1, True)} puntos")
        lineas.append(base + ("." if sig else "; la diferencia de demora no es distinguible de cero."))
    lineas.append(NOTA_SINTETICA)
    return lineas

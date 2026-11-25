"""Recomendacion en vivo: ¿esperar o salir?

Dado el estado del dia (pasajeros a bordo, pasajes vendidos en Oruro, cuantos ya llegaron y cuantos minutos
pasaron desde la citacion), calcula la probabilidad de que se cumpla la condicion de salida de la regla
vigente y cuanto habria que esperar. El calculo es EXACTO (no una nueva simulacion) y usa el mismo modelo
de llegadas de simulador_despacho.py:

  * Cada pasajero que sigue ausente en el minuto t llega con un retraso adicional Exponencial(media = mu_tarde).
    Es la propiedad de falta de memoria de la exponencial: lo que ya espero no cambia lo que falta.
  * La condicion de salida se cumple cuando (a bordo + presentes >= minimo) y (ausentes <= k).
    Con a ausentes, se cumple al llegar el r-esimo de ellos, con r = max(a - k, minimo - a_bordo - presentes, 0).
  * El tiempo hasta la r-esima llegada de a llegadas independientes tiene distribucion conocida:
    P(R <= w) = P(Binomial(a, 1 - exp(-w/mu)) >= r)  y  cuantil q: -mu * ln(1 - Beta^-1(q; r, a - r + 1)).
  * La espera maxima aceptada (tope) acota la espera: pasado el tope, el modelo cierra y sale aunque no se cumpla.

El resultado depende de mu_tarde, que es un parametro SINTETICO (supuesto); por eso se muestra tambien
la sensibilidad a ese parametro. La decision final es de la encargada y la ATT: esto solo la apoya.
"""
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

import simulador_despacho as sim

NOTA = ("Apoyo a la decisión con un parámetro sintético (retraso medio de los ausentes). "
        "La decisión corresponde a la encargada y a la ATT.")
HORIZONTES = (5, 10, 15, 20, 30)


@dataclass(frozen=True)
class Estado:
    capacidad: int
    a_bordo: int          # pasajeros con pasaje que continuan a bordo desde La Paz
    vendidos_oruro: int   # pasajes vendidos en Oruro para esta salida
    presentes: int        # de los vendidos en Oruro, cuantos ya llegaron
    minutos: float        # minutos transcurridos desde la citacion (17:00 = 0)


def validar(e):
    if e.capacidad not in (36, 49):
        raise ValueError("La capacidad debe ser 36 o 49 asientos")
    for nombre, v in (("pasajeros a bordo", e.a_bordo), ("pasajes vendidos en Oruro", e.vendidos_oruro),
                      ("presentes", e.presentes)):
        if int(v) != v or v < 0:
            raise ValueError(f"{nombre.capitalize()} debe ser un entero no negativo")
    if e.presentes > e.vendidos_oruro:
        raise ValueError("Los presentes no pueden superar los pasajes vendidos en Oruro")
    if e.a_bordo + e.vendidos_oruro > e.capacidad:
        raise ValueError("Los pasajes (a bordo + vendidos en Oruro) superan la capacidad del bus")
    if e.minutos < 0:
        raise ValueError("Los minutos desde la citación no pueden ser negativos")
    return e


def llegadas_necesarias(e, k):
    """Cuantas de las llegadas que faltan hacen falta para cumplir la condicion de la regla.
    Devuelve (r, ausentes, minimo, por_ausentes, por_minimo)."""
    m = sim.minimo(e.capacidad)
    a = e.vendidos_oruro - e.presentes
    por_aus = max(0, a - k)
    por_min = max(0, m - e.a_bordo - e.presentes)
    return max(por_aus, por_min), a, m, por_aus, por_min


def prob_cumple_en(w, r, a, mu):
    """P(la condicion se cumple dentro de w minutos mas)."""
    if r <= 0:
        return 1.0
    if r > a or w <= 0:
        return 0.0
    q = 1.0 - math.exp(-w / mu)
    return float(stats.binom.sf(r - 1, a, q))


def cuantil_espera(p, r, a, mu):
    """Minutos de espera adicional que se superan con probabilidad 1 - p (mediana: p = 0,5). None si es imposible."""
    if r <= 0:
        return 0.0
    if r > a:
        return None
    u = float(stats.beta.ppf(p, r, a - r + 1))
    return float(-mu * math.log1p(-u)) if u < 1 else float("inf")


def espera_esperada(r, a, mu, techo, paso=0.05):
    """Espera esperada (min) acotada por 'techo': integral de P(R > w) entre 0 y techo."""
    if r <= 0 or techo <= 0:
        return 0.0
    w = np.arange(0.0, techo + paso, paso)
    sup = np.array([1.0 - prob_cumple_en(x, r, a, mu) for x in w])
    return float(np.trapezoid(sup, w))


def evaluar(e, par=None, k=5):
    """Evalua el estado del dia con la regla vigente (umbral k) y devuelve un diccionario con todo lo necesario."""
    validar(e)
    par = par or sim.PARAMETROS_CALIBRADOS
    r, a, m, por_aus, por_min = llegadas_necesarias(e, k)
    restante = max(0.0, par.tope - e.minutos)           # minutos hasta la espera maxima aceptada
    cierre_medio = (par.cierre_min + par.cierre_max) / 2
    a_bordo_total = e.a_bordo + e.presentes
    res = dict(minimo=m, ausentes=a, a_bordo_total=a_bordo_total, llegadas_necesarias=r,
               por_ausentes=por_aus, por_minimo=por_min, restante_hasta_tope=restante, cierre_medio=cierre_medio,
               imposible_minimo=r > a)
    if r == 0:
        res.update(estado="cumplida", prob_antes_del_tope=1.0, espera_mediana=0.0, espera_p80=0.0,
                   espera_esperada=0.0, pasajeros_minuto=0.0)
    elif e.minutos >= par.tope:
        res.update(estado="tope", prob_antes_del_tope=0.0, espera_mediana=0.0, espera_p80=0.0,
                   espera_esperada=0.0, pasajeros_minuto=0.0)
    else:
        mu = par.mu_tarde
        med, p80 = cuantil_espera(0.5, r, a, mu), cuantil_espera(0.8, r, a, mu)
        ee = espera_esperada(r, a, mu, restante)
        res.update(estado="esperar", prob_antes_del_tope=prob_cumple_en(restante, r, a, mu),
                   espera_mediana=None if med is None else min(med, restante),
                   espera_p80=None if p80 is None else min(p80, restante), espera_esperada=ee,
                   pasajeros_minuto=a_bordo_total * ee)
    res["horizontes"] = pd.DataFrame(
        [dict(minutos=w, probabilidad=prob_cumple_en(min(w, restante), r, a, par.mu_tarde)
              if res["estado"] == "esperar" else (1.0 if res["estado"] == "cumplida" else 0.0))
         for w in HORIZONTES])
    res["mensaje"] = _mensaje(res, e, par, k)
    return res


def alternativas(e, par=None, ks=(3, 5, 8)):
    """Que pasaria con otros umbrales k (cuantos ausentes se toleran) en este mismo estado."""
    par = par or sim.PARAMETROS_CALIBRADOS
    filas = []
    for k in ks:
        r = evaluar(e, par, k)
        filas.append(dict(k=k, estado=r["estado"], llegadas_necesarias=r["llegadas_necesarias"],
                          prob_antes_del_tope=r["prob_antes_del_tope"], espera_esperada=r["espera_esperada"],
                          pasajeros_minuto=r["pasajeros_minuto"]))
    return pd.DataFrame(filas)


def sensibilidad_mu(e, par=None, k=5, factores=(0.6, 1.0, 2.0)):
    """Como cambia la recomendacion si el retraso medio de los ausentes es distinto del supuesto."""
    import dataclasses
    par = par or sim.PARAMETROS_CALIBRADOS
    filas = []
    for f in factores:
        p2 = dataclasses.replace(par, mu_tarde=par.mu_tarde * f)
        r = evaluar(e, p2, k)
        filas.append(dict(factor=f, retraso_medio=p2.mu_tarde, prob_antes_del_tope=r["prob_antes_del_tope"],
                          espera_mediana=r["espera_mediana"], espera_esperada=r["espera_esperada"]))
    return pd.DataFrame(filas)


def _pct(x):
    return f"{100 * x:.0f} %"


def _mensaje(res, e, par, k):
    if res["estado"] == "cumplida":
        return (f"La condición de la regla vigente se cumple (a bordo {res['a_bordo_total']} de un mínimo de "
                f"{res['minimo']}; ausentes {res['ausentes']}, umbral {k}). Se puede cerrar la venta y salir "
                f"(cierre y arranque de unos {res['cierre_medio']:.0f} min).")
    if res["estado"] == "tope":
        extra = " Aún no se alcanza el mínimo de pasajeros: informe a la ATT." if res["por_minimo"] > 0 else ""
        return (f"Se alcanzó la espera máxima aceptada ({par.tope:.0f} min). El modelo cierra y sale aunque no "
                f"se cumpla la condición.{extra}")
    partes = []
    if res["por_ausentes"] > 0:
        partes.append(f"{res['por_ausentes']} llegada(s) para bajar los ausentes a {k} o menos")
    if res["por_minimo"] > 0:
        partes.append(f"{res['por_minimo']} para llegar al mínimo de {res['minimo']}")
    necesita = " y ".join(partes)
    if res["imposible_minimo"]:
        return ("No alcanzan los pasajes vendidos para llegar al mínimo, aunque lleguen todos los ausentes: "
                "consulte a la ATT. El modelo sale al cumplirse la espera máxima "
                f"({res['restante_hasta_tope']:.0f} min más).")
    mediana = f"{res['espera_mediana']:.1f}".replace(".", ",")
    return (f"Recomendación de la regla vigente: esperar. Faltan {necesita}. Probabilidad de que se cumpla antes "
            f"de la espera máxima ({res['restante_hasta_tope']:.0f} min más): {_pct(res['prob_antes_del_tope'])}. "
            f"Espera mediana: {mediana} min.")


def guardar_consulta(conn, usuario_id, e, res, k, decision=None, observaciones=None):
    """Guarda la consulta (y la decision real, si se conoce) para mejorar el modelo con datos reales."""
    if decision not in (None, "espero", "salio"):
        raise ValueError("La decisión debe ser 'espero' o 'salio'")
    cur = conn.execute(
        """INSERT INTO consultas_decision (usuario_id, capacidad, a_bordo, vendidos_oruro, presentes, minutos,
               umbral_k, estado, prob_antes_del_tope, espera_mediana, decision_tomada, observaciones)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (usuario_id, e.capacidad, e.a_bordo, e.vendidos_oruro, e.presentes, e.minutos, k, res["estado"],
         res["prob_antes_del_tope"], res["espera_mediana"], decision, observaciones))
    conn.commit()
    return cur.lastrowid


def listar_consultas(conn):
    return pd.read_sql_query(
        """SELECT c.id, c.creado, u.usuario, c.capacidad, c.a_bordo, c.vendidos_oruro, c.presentes, c.minutos,
                  c.umbral_k, c.estado, c.prob_antes_del_tope, c.espera_mediana, c.decision_tomada, c.observaciones
           FROM consultas_decision c JOIN usuarios u ON u.id = c.usuario_id ORDER BY c.id DESC""", conn)

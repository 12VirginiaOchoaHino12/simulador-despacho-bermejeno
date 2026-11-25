"""Pruebas de la recomendacion en vivo (¿esperar o salir?).

La prueba mas importante compara el calculo exacto contra el propio simulador de eventos discretos.
"""
import dataclasses

import numpy as np
import pytest

import recomendacion as R
import seguridad
import simulador_despacho as sim
from simulador_despacho import PARAMETROS_CALIBRADOS as PAR, Parametros


def test_validaciones_de_entrada():
    for malo in (R.Estado(40, 5, 10, 5, 0), R.Estado(36, -1, 10, 5, 0), R.Estado(36, 5, 10, 11, 0),
                 R.Estado(36, 30, 10, 5, 0), R.Estado(36, 5, 10, 5, -1)):
        with pytest.raises(ValueError):
            R.evaluar(malo, PAR)


def test_llegadas_necesarias():
    # 36 asientos: minimo 18; a bordo 8 + presentes 6 = 14 -> faltan 4 por minimo; ausentes 14 con k=5 -> 9 por ausentes
    r, a, m, por_aus, por_min = R.llegadas_necesarias(R.Estado(36, 8, 20, 6, 0), 5)
    assert (a, m, por_aus, por_min, r) == (14, 18, 9, 4, 9)
    assert R.llegadas_necesarias(R.Estado(36, 8, 20, 20, 0), 5)[0] == 0
    assert R.llegadas_necesarias(R.Estado(49, 10, 20, 10, 0), 5)[2] == 25  # minimo del movil 500


def test_probabilidad_exacta_coincide_con_montecarlo():
    rng = np.random.default_rng(2026)
    a, r, mu = 10, 5, PAR.mu_tarde
    t_r = np.sort(rng.exponential(mu, (200000, a)), axis=1)[:, r - 1]
    for w in (2, 5, 10, 15):
        assert R.prob_cumple_en(w, r, a, mu) == pytest.approx(float((t_r <= w).mean()), abs=0.005)
    assert R.cuantil_espera(0.5, r, a, mu) == pytest.approx(float(np.median(t_r)), abs=0.05)
    assert R.cuantil_espera(0.8, r, a, mu) == pytest.approx(float(np.quantile(t_r, 0.8)), abs=0.08)


def test_espera_esperada_coincide_con_montecarlo():
    rng = np.random.default_rng(7)
    a, r, mu, techo = 12, 6, 5.0, 15.0
    t_r = np.sort(rng.exponential(mu, (200000, a)), axis=1)[:, r - 1]
    assert R.espera_esperada(r, a, mu, techo) == pytest.approx(float(np.minimum(t_r, techo).mean()), abs=0.05)


@pytest.mark.parametrize("cap,esc", [(36, "todos"), (49, "alta"), (36, "baja"), (36, "habitual")])
def test_coincide_con_el_simulador_de_eventos_discretos(cap, esc):
    """Con el estado a las 17:00, la salida simulada = min(tope, llegada r-esima de los ausentes) + cierre."""
    comprobadas = 0
    for semilla in range(300):
        ent = sim.generar_entradas(semilla, cap, esc, PAR)
        ll = ent["llegadas"]
        e = R.Estado(cap, ent["l"], len(ll), int(np.sum(ll <= 0)), 0)
        r, a, *_ = R.llegadas_necesarias(e, sim.VIGENTE.umbral)
        tardios = np.sort(ll[ll > 0])
        listo = 0.0 if r == 0 else (float(tardios[r - 1]) if r <= len(tardios) else np.inf)
        esperado = min(listo, ent["tope"]) + ent["cierre"]
        assert sim.simular(ent, sim.VIGENTE)["salida"] == pytest.approx(esperado)
        comprobadas += 1
    assert comprobadas == 300


def test_estado_cumplida_tope_y_esperar():
    cumplida = R.evaluar(R.Estado(36, 10, 20, 18, 0), PAR)
    assert cumplida["estado"] == "cumplida" and cumplida["prob_antes_del_tope"] == 1.0
    assert "se cumple" in cumplida["mensaje"]
    tope = R.evaluar(R.Estado(36, 5, 20, 3, 20), PAR)
    assert tope["estado"] == "tope" and "espera máxima" in tope["mensaje"] and "ATT" in tope["mensaje"]
    esperar = R.evaluar(R.Estado(36, 8, 24, 14, 5), PAR)
    assert esperar["estado"] == "esperar" and 0 < esperar["espera_mediana"] <= esperar["restante_hasta_tope"]
    assert esperar["pasajeros_minuto"] == pytest.approx(esperar["a_bordo_total"] * esperar["espera_esperada"])


def test_minimo_imposible_se_avisa():
    e = R.Estado(36, 2, 10, 4, 3)   # 2 + 10 = 12 < 18 aunque lleguen todos
    r = R.evaluar(e, PAR)
    assert r["imposible_minimo"] and r["prob_antes_del_tope"] == 0 and "No alcanzan" in r["mensaje"]


def test_mas_umbral_menos_espera():
    alt = R.alternativas(R.Estado(36, 8, 24, 14, 5), PAR, (3, 5, 8)).set_index("k")
    assert alt.loc[3, "espera_esperada"] > alt.loc[5, "espera_esperada"] > alt.loc[8, "espera_esperada"]
    assert alt.loc[3, "prob_antes_del_tope"] <= alt.loc[8, "prob_antes_del_tope"]


def test_mayor_retraso_medio_mas_espera():
    s = R.sensibilidad_mu(R.Estado(36, 8, 24, 14, 5), PAR)
    assert list(s["espera_mediana"]) == sorted(s["espera_mediana"])
    assert list(s["factor"]) == [0.6, 1.0, 2.0]


def test_la_probabilidad_baja_si_queda_menos_tiempo():
    e1, e2 = R.Estado(36, 8, 24, 10, 0), R.Estado(36, 8, 24, 10, 15)
    assert R.evaluar(e2, PAR)["prob_antes_del_tope"] < R.evaluar(e1, PAR)["prob_antes_del_tope"]


def test_usa_los_parametros_de_la_base(conn):
    import simulacion
    par, k = simulacion.parametros_desde_bd(conn)
    assert R.evaluar(R.Estado(36, 8, 24, 14, 5), par, k)["estado"] == "esperar"


def test_guardar_y_listar_consultas(conn):
    seguridad.crear_usuario(conn, "maria", "clave-larga-1", "encargada")
    uid = seguridad.autenticar(conn, "maria", "clave-larga-1")["id"]
    e = R.Estado(36, 8, 24, 14, 5)
    res = R.evaluar(e, PAR)
    cid = R.guardar_consulta(conn, uid, e, res, 5, decision="espero", observaciones="prueba")
    df = R.listar_consultas(conn)
    assert len(df) == 1 and df.iloc[0]["id"] == cid and df.iloc[0]["decision_tomada"] == "espero"
    with pytest.raises(ValueError):
        R.guardar_consulta(conn, uid, e, res, 5, decision="quizas")
    assert len(R.listar_consultas(conn)) == 1


def test_la_nota_advierte_que_la_decision_es_humana():
    assert "ATT" in R.NOTA and "sintético" in R.NOTA

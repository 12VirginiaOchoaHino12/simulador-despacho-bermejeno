import copy, numpy as np
from simulador_despacho import *
PAR = Parametros(0.3, 30.0, 5.0, 10.0, 20.0)
def ent(cap, n_total, l, llegadas, cierre=7.0, tope=20.0):
    return dict(cap=cap, n=n_total, l=l, llegadas=np.sort(np.array(llegadas, float)), cierre=cierre, tope=tope)
def test_1_sin_pasajeros_sin_minimo():
    r = simular(ent(36, 0, 0, []), VIGENTE)
    assert r["sin_minimo"] and r["ocupacion"] == 0 and r["demora"] == 20.0 + 7.0
def test_2_todos_puntuales_sale_a_la_citacion_mas_cierre():
    r = simular(ent(36, 20, 0, [-10] * 20), VIGENTE)
    assert r["demora"] == 7.0 and not r["espero"] and r["ausentes_citacion"] == 0
def test_3_espera_hasta_cumplir_ausentes_y_minimo():
    # 4 puntuales, 8 tardios (5,8,10,12,15,18,20,25); L=10 -> minimo 18
    # a t=10 ausentes=5 pero total=17 < 18; a t=12 total=18 -> listo
    r = simular(ent(36, 12, 10, [-5]*4 + [5, 8, 10, 12, 15, 18, 20, 25]), VIGENTE)
    assert r["demora"] == 12.0 + 7.0 and r["espero"]
def test_4_demanda_mayor_que_capacidad():
    r = simular(ent(36, 60, 0, [-10] * 60), VIGENTE)
    assert r["abordados"] == 36 and r["ocupacion"] == 100 and r["no_atendida"] == 24
def test_5_misma_semilla_misma_regla():
    a = simular(generar_entradas(7, 49, "todos", PAR), VIGENTE)
    b = simular(generar_entradas(7, 49, "todos", PAR), VIGENTE)
    assert a == b
def test_6_misma_semilla_reglas_distintas_mismas_entradas():
    e = generar_entradas(11, 36, "alta", PAR); copia = copy.deepcopy(e)
    for regla in (VIGENTE, Regla("k3", 3), Regla("T10", 5, 10.0)):
        simular(e, regla)
    assert e["n"] == copia["n"] and e["l"] == copia["l"] and np.array_equal(e["llegadas"], copia["llegadas"]) and e["cierre"] == copia["cierre"]
def test_7_espera_maxima_T_corta_la_espera():
    e = ent(36, 12, 14, [-5]*4 + [5, 8, 10, 12, 15, 18, 20, 25])   # minimo ya cumplido
    assert simular(e, VIGENTE)["demora"] == 10.0 + 7.0              # 3.ª llegada tardia
    assert simular(e, Regla("T5", 5, 5.0))["demora"] == 5.0 + 7.0   # sale al cumplirse T
def test_8_la_salida_no_es_anterior_a_la_citacion_ni_a_la_llegada_del_bus():
    for s in range(300):
        for cap in (36, 49):
            r = simular(generar_entradas(s, cap, "todos", PAR), VIGENTE)
            assert r["salida"] >= 0 > BUS_LLEGADA and r["abordados"] <= cap
def test_9_minimo_segun_capacidad():
    assert minimo(36) == 18 and minimo(49) == 25

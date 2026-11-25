"""Pruebas del modulo de simulacion integrada (comparacion con numeros comunes, sensibilidad, historial)."""
import numpy as np
import pandas as pd
import pytest

import db
import simulacion as s
from simulador_despacho import Parametros, Regla

PAR = Parametros(0.3, 5.0, 15.0, 20.0, 20.0)


def test_parametros_desde_la_base(conn):
    par, k = s.parametros_desde_bd(conn)
    assert par == PAR and k == 5


def test_regla_de_referencia_tiene_diferencia_cero(conn):
    t = s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 200, 1000, PAR)
    f = t.iloc[0]
    assert f["Regla"] == "Vigente" and f["dif_demora"] == 0 and f["dif_ocupacion"] == 0


def test_misma_semilla_mismos_resultados():
    a = s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 300, 7, PAR)
    b = s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 300, 7, PAR)
    pd.testing.assert_frame_equal(a, b)


def test_distinta_semilla_distintos_resultados():
    a = s.comparar_reglas(s.reglas_predefinidas(5)[:1], "todos", 36, 300, 7, PAR)
    b = s.comparar_reglas(s.reglas_predefinidas(5)[:1], "todos", 36, 300, 8, PAR)
    assert a.iloc[0]["demora_media"] != b.iloc[0]["demora_media"]


def test_umbral_mayor_reduce_la_demora_y_menor_la_aumenta():
    t = s.comparar_reglas([Regla("Vigente", 5), Regla("k3", 3), Regla("k8", 8)], "todos", 36, 800, 1000, PAR).set_index("Regla")
    assert t.loc["k3", "dif_demora"] > 0 > t.loc["k8", "dif_demora"]


def test_intervalo_de_confianza_contiene_la_diferencia():
    t = s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 400, 1000, PAR)
    assert ((t["dif_ic_inf"] <= t["dif_demora"]) & (t["dif_demora"] <= t["dif_ic_sup"])).all()


def test_ocupacion_y_porcentajes_en_rango():
    t = s.comparar_reglas(s.reglas_predefinidas(5), "alta", 49, 300, 1000, PAR)
    assert t["ocupacion_media"].between(0, 100).all() and t["pct_espero"].between(0, 100).all()


@pytest.mark.parametrize("par_malo", [Parametros(1.5, 5, 15, 20, 20), Parametros(0.3, 5, 25, 20, 20),
                                      Parametros(0.3, -1, 15, 20, 20), Parametros(0.3, 5, 15, 20, -3)])
def test_parametros_invalidos_se_rechazan(par_malo):
    with pytest.raises(ValueError):
        s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 100, 1, par_malo)


def test_escenario_y_replicas_invalidos():
    with pytest.raises(ValueError):
        s.comparar_reglas(s.reglas_predefinidas(5), "inexistente", 36, 100, 1, PAR)
    with pytest.raises(ValueError):
        s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 1, 1, PAR)


def test_flota_real_funciona_con_cap_none():
    t = s.comparar_reglas(s.reglas_predefinidas(5)[:2], "todos", None, 300, 1000, PAR)
    assert len(t) == 2


def test_sensibilidad_ordena_por_rango_y_tope_no_importa():
    tabla, base = s.sensibilidad(Regla("Vigente", 5), {"mu_tarde": (3, 10), "cierre_max": (17, 23),
                                                       "p_puntual": (0.2, 0.4), "tope": (15, 30)},
                                 "todos", None, 1000, 1000, PAR)
    assert list(tabla["rango"]) == sorted(tabla["rango"], reverse=True)
    assert tabla.iloc[0]["Parametro"] == "mu_tarde"       # el mayor efecto (coincide con la Tabla 39)
    assert tabla.set_index("Parametro").loc["tope", "rango"] == pytest.approx(0, abs=0.01)
    assert base == pytest.approx(20.9, abs=0.3)            # base de la Tabla 39 (flota real, 1500 replicas)


def test_sensibilidad_rechaza_parametro_desconocido():
    with pytest.raises(ValueError):
        s.sensibilidad(Regla("Vigente", 5), {"inventado": (1, 2)}, "todos", 36, 100, 1, PAR)


def test_guardar_y_leer_historial(conn):
    t = s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 200, 1000, PAR)
    cid = s.guardar_corrida(conn, t, "todos", 36, 200, 1000, PAR, None, "prueba")
    assert s.listar_corridas(conn).iloc[0]["etiqueta"] == "prueba"
    r = s.resultados_de_corrida(conn, cid)
    assert len(r) == len(t) and r["demora_media"].round(6).tolist() == t["demora_media"].round(6).tolist()
    nota = conn.execute("SELECT nota FROM corridas WHERE id = ?", (cid,)).fetchone()[0]
    assert "sinteticos" in nota


def test_la_explicacion_siempre_advierte_que_es_sintetico():
    t = s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 200, 1000, PAR)
    txt = " ".join(s.explicar(t))
    assert "sintéticos" in txt and "Vigente" in txt


def test_los_numeros_aleatorios_son_comunes_entre_reglas():
    """Dos reglas identicas con distinto nombre deben dar exactamente los mismos resultados."""
    t = s.comparar_reglas([Regla("A", 5), Regla("B", 5)], "todos", 36, 200, 1000, PAR)
    assert t.iloc[1]["dif_demora"] == 0 and np.isclose(t.iloc[0]["demora_media"], t.iloc[1]["demora_media"])


def test_rendimiento_seis_reglas_mil_replicas_en_pocos_segundos():
    import time
    t0 = time.perf_counter()
    s.comparar_reglas(s.reglas_predefinidas(5), "todos", 36, 1000, 1000, PAR)
    assert time.perf_counter() - t0 < 10

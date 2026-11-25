"""Pruebas del analisis: debe reproducir las Tablas 26 a 30 del Capitulo IV con los datos de la base."""
import pytest

import analisis as a


@pytest.fixture()
def df(conn_datos):
    return a.cargar_viajes(conn_datos)


def test_resumen_general(df):
    r = a.resumen_general(df)
    assert (r["viajes"], r["pasajeros"], r["pasajeros_oruro"], r["revisar"]) == (45, 1233, 718, 12)
    assert r["promedio_pasajeros"] == pytest.approx(27.4, abs=0.01)
    assert r["ocupacion_media"] == pytest.approx(74.2, abs=0.05)


def test_tabla_26_descriptiva(df):
    t = a.descriptiva(df).set_index("Variable")
    o = t.loc["Pasajeros de Oruro por salida"]
    assert (round(o["Media"], 1), o["Mediana"], round(o["Desv. est."], 1), o["Mínimo"], o["Máximo"]) == (16.0, 13.0, 10.1, 2, 36)
    h = t.loc["Pasajeros por hoja de viaje"]
    assert (round(h["Media"], 1), h["Mediana"], round(h["Desv. est."], 1)) == (27.4, 28.0, 6.2)
    oc = t.loc["Ocupación por hoja, según la capacidad del bus (%)"]
    assert (round(oc["Media"], 1), oc["Mediana"], round(oc["Desv. est."], 1), round(oc["Mínimo"], 1)) == (74.2, 75.0, 14.9, 44.4)


def test_shapiro_wilk(df):
    assert a.normalidad(df["pasajeros_oruro"])[1] == pytest.approx(0.003, abs=0.0005)
    assert a.normalidad(df["pasajeros"])[1] == pytest.approx(0.210, abs=0.001)


def test_tabla_28_ajuste_de_distribuciones(df):
    aj = a.ajustar_distribuciones(df["pasajeros_oruro"]).set_index("Distribución")
    w = aj.loc["Weibull"]
    assert w["_forma"] == pytest.approx(1.659, abs=0.001) and w["_escala"] == pytest.approx(17.905, abs=0.001)
    assert w["AIC"] == pytest.approx(328.8, abs=0.1)
    assert aj.loc["Exponencial", "Valor p (K–S)"] == pytest.approx(0.043, abs=0.001)
    assert aj["AIC"].idxmin() == "Weibull"


def test_tabla_29_dia_de_la_semana(df):
    t = a.por_dia(df).set_index("Día")
    assert t.loc["Martes", "Salidas"] == 10 and t.loc["Martes", "Mediana"] == 21.5
    assert t.loc["Domingo", "Mediana"] == 30.0 and t["Salidas"].sum() == 45
    p = a.pruebas_dia(df)
    assert p["H"] == pytest.approx(5.57, abs=0.01) and p["p_H"] == pytest.approx(0.473, abs=0.001)
    assert p["U"] == 223.0 and p["p_U"] == pytest.approx(0.840, abs=0.001)


def test_tabla_30_escenarios(df):
    esc, p25, p75 = a.escenarios_demanda(df)
    assert (p25, p75) == (7.0, 23.0)
    assert list(esc["Salidas"]) == [12, 21, 12] and list(esc["Mediana"]) == [5.0, 13.0, 30.5]


def test_tabla_27_hojas_bajo_el_minimo(df):
    bajo = a.bajo_minimo(df)
    assert len(bajo) == 1 and bajo.iloc[0]["codigo"] == "1010/26"


def test_calidad_de_datos(df):
    c = a.calidad_datos(df).set_index("Tipo de hoja")
    assert c.loc["Oruro→Bermejo", "Total"] == 13 and c["Revisar"].sum() == 12 and c["OK"].sum() == 33


def test_filtro_solo_ok(conn_datos):
    assert len(a.cargar_viajes(conn_datos, solo_ok=True)) == 33
    assert len(a.cargar_viajes(conn_datos, tipo="oruro_bermejo")) == 13


def test_ocupacion_oruro_bermejo(df):
    ob = df[df["tipo_hoja"] == "oruro_bermejo"]
    assert ob["ocupacion"].mean() == pytest.approx(74.1, abs=0.5)  # Tabla 26 (13 hojas, 36 asientos)

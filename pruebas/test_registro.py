"""Pruebas del registro de salidas nuevas (validaciones y estimaciones con datos reales)."""
import pytest

import registro
import seguridad


@pytest.fixture()
def uid(conn):
    seguridad.crear_usuario(conn, "maria", "clave-larga-1", "encargada")
    return seguridad.autenticar(conn, "maria", "clave-larga-1")["id"]


def test_calcular_demora():
    assert registro.calcular_demora("17:00", "17:24") == 24.0
    assert registro.calcular_demora("17:00", "17:00") == 0.0
    with pytest.raises(ValueError):
        registro.calcular_demora("17:00", "16:59")
    with pytest.raises(ValueError):
        registro.calcular_demora("17:00", "25:61")
    with pytest.raises(ValueError):
        registro.calcular_demora("17:00", "abc")


def test_registrar_salida_valida(conn, uid):
    rid = registro.registrar_salida(conn, uid, "2026-11-24", 14, 30, 4, 3, "17:20")
    f = conn.execute("SELECT * FROM registros_salida WHERE id = ?", (rid,)).fetchone()
    assert f["demora_min"] == 20.0 and f["capacidad"] == 36 and f["ausentes"] == 4


@pytest.mark.parametrize("args", [
    dict(fecha="24/11/2026"),                 # formato de fecha
    dict(pasajeros_pasaje=40),                # excede capacidad 36
    dict(ausentes=31),                        # ausentes > pasajeros
    dict(llegaron_tarde=5, ausentes=4),       # tarde > ausentes
    dict(pasajeros_pasaje=-1),
    dict(bus=9999),                           # bus no registrado sin capacidad
])
def test_validaciones_de_entrada(conn, uid, args):
    base = dict(fecha="2026-11-24", bus=14, pasajeros_pasaje=30, ausentes=4, llegaron_tarde=3, hora_salida_real="17:20")
    base.update(args)
    with pytest.raises(ValueError):
        registro.registrar_salida(conn, uid, base.pop("fecha"), base.pop("bus"), base.pop("pasajeros_pasaje"),
                                  base.pop("ausentes"), base.pop("llegaron_tarde"), base.pop("hora_salida_real"))
    assert conn.execute("SELECT COUNT(*) FROM registros_salida").fetchone()[0] == 0


def test_estimaciones_reales(conn, uid):
    assert registro.estimaciones_reales(conn) == {"n": 0}
    registro.registrar_salida(conn, uid, "2026-11-24", 14, 30, 6, 4, "17:20")
    registro.registrar_salida(conn, uid, "2026-11-25", 14, 20, 2, 2, "17:10")
    e = registro.estimaciones_reales(conn)
    assert e["n"] == 2 and e["demora_media"] == 15.0
    assert e["pct_ausentes"] == pytest.approx(100 * 8 / 50) and e["pct_tarde_de_ausentes"] == pytest.approx(75.0)
    assert e["suficiente"] is False


def test_listar_registros(conn, uid):
    registro.registrar_salida(conn, uid, "2026-11-24", 14, 30, 6, 4, "17:20", observaciones="prueba")
    df = registro.listar_registros(conn)
    assert len(df) == 1 and df.iloc[0]["usuario"] == "maria"

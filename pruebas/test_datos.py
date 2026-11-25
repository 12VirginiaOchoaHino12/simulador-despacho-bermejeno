"""Pruebas de la capa de datos: esquema, importacion, depuracion e integridad."""
import sqlite3

import openpyxl
import pytest

import db
import importar
from conftest import EXCEL


def test_esquema_crea_todas_las_tablas(conn):
    tablas = {f[0] for f in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    esperadas = {"usuarios", "buses", "viajes", "salidas_observadas", "registros_salida", "parametros",
                 "corridas", "resultados_regla", "bitacora"}
    assert esperadas <= tablas


def test_parametros_iniciales_con_categoria(conn):
    p, cat = db.leer_parametros(conn)
    assert p["minimo_fraccion"] == 0.5 and p["umbral_k"] == 5
    assert cat["p_puntual"] == "sintetico" and cat["weibull_forma"] == "historico"


def test_importacion_reproduce_cifras_del_documento(conn):
    inf = importar.importar_excel(conn, EXCEL)
    assert inf["importados"] == 45 and inf["rechazados"] == 0 and inf["con_calidad_revisar"] == 12
    fila = conn.execute("SELECT COUNT(*), SUM(pasajeros), SUM(pasajeros_oruro) FROM viajes").fetchone()
    assert tuple(fila) == (45, 1233, 718)
    tipos = dict(conn.execute("SELECT tipo_hoja, COUNT(*) FROM viajes GROUP BY tipo_hoja").fetchall())
    assert tipos == {"oruro_bermejo": 13, "recorrido_completo": 32}


def test_importacion_repetida_no_duplica(conn):
    importar.importar_excel(conn, EXCEL)
    inf = importar.importar_excel(conn, EXCEL)
    assert inf["importados"] == 0 and inf["repetidos"] == 45
    assert conn.execute("SELECT COUNT(*) FROM viajes").fetchone()[0] == 45


def test_buses_y_capacidades(conn_datos):
    caps = dict(conn_datos.execute("SELECT numero, capacidad FROM buses").fetchall())
    assert caps[500] == 49 and caps[14] == 36


def _excel_con_filas(tmp_path, filas):
    libro = openpyxl.Workbook()
    ws = libro.active
    ws.title = "Pasajeros"
    for _ in range(4):
        ws.append([None] * 16)
    for f in filas:
        ws.append(f)
    ruta = tmp_path / "prueba.xlsx"
    libro.save(ruta)
    return ruta


def test_importacion_rechaza_filas_invalidas(conn, tmp_path):
    from datetime import datetime
    f = datetime(2026, 5, 1)
    ruta = _excel_con_filas(tmp_path, [
        ["A/1", f, "x", "Oruro→Bermejo", 14, "16:30", 20, 3000, 20, 0, 36, 0.5, 202605, 1, "OK", None],
        ["A/2", f, "x", "Oruro→Bermejo", 14, "16:30", 10, 3000, 15, 0, 36, 0.5, 202605, 1, "OK", None],   # Oruro > total
        ["A/3", f, "x", "Oruro→Bermejo", 14, "16:30", -4, 3000, 1, 0, 36, 0.5, 202605, 1, "OK", None],    # negativo
        ["A/4", f, "x", "Oruro→Bermejo", 14, "16:30", 40, 3000, 40, 0, 36, 0.5, 202605, 1, "OK", None],   # excede capacidad
        ["Total / promedio", None] + [None] * 14,
    ])
    inf = importar.importar_excel(conn, ruta)
    assert inf["importados"] == 2 and inf["rechazados"] == 2
    fila = conn.execute("SELECT calidad, nota FROM viajes WHERE codigo = 'A/4'").fetchone()
    assert fila["calidad"] == "Revisar" and "capacidad" in fila["nota"]


def test_importacion_sin_hoja_pasajeros_da_error(conn, tmp_path):
    libro = openpyxl.Workbook()
    libro.active.title = "Otra"
    ruta = tmp_path / "x.xlsx"
    libro.save(ruta)
    with pytest.raises(ValueError):
        importar.importar_excel(conn, ruta)


def test_restricciones_de_integridad(conn):
    with pytest.raises(sqlite3.IntegrityError):  # categoria invalida
        conn.execute("INSERT INTO parametros VALUES ('x', 1, 'inventado', 'f', 'd')")
    with pytest.raises(sqlite3.IntegrityError):  # oruro > total
        conn.execute("""INSERT INTO viajes (codigo, fecha, ruta, tipo_hoja, pasajeros, pasajeros_oruro, capacidad, calidad)
                        VALUES ('z', '2026-01-01', 'r', 'oruro_bermejo', 5, 9, 36, 'OK')""")
    with pytest.raises(sqlite3.IntegrityError):  # bus inexistente
        conn.execute("""INSERT INTO viajes (codigo, fecha, ruta, tipo_hoja, bus, pasajeros, pasajeros_oruro, capacidad,
                        calidad) VALUES ('y', '2026-01-01', 'r', 'oruro_bermejo', 9999, 5, 5, 36, 'OK')""")


def test_salidas_observadas_iniciales(conn):
    demoras = [f[0] for f in conn.execute("SELECT demora_min FROM salidas_observadas ORDER BY demora_min")]
    assert demoras == [15.0, 24.0, 30.0]


def test_guardar_parametro_desconocido_falla(conn):
    with pytest.raises(KeyError):
        db.guardar_parametro(conn, "no_existe", 1)
    db.guardar_parametro(conn, "umbral_k", 7)
    assert db.leer_parametros(conn)[0]["umbral_k"] == 7

"""Configuracion comun de las pruebas: ruta del proyecto y una base en memoria con los datos del Excel."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import db  # noqa: E402
import importar  # noqa: E402

EXCEL = RAIZ / "datos" / "datos_pasajeros_simulacion.xlsx"


@pytest.fixture()
def conn():
    c = db.iniciar(db.conectar(":memory:"))
    yield c
    c.close()


@pytest.fixture()
def conn_datos(conn):
    importar.importar_excel(conn, EXCEL)
    return conn

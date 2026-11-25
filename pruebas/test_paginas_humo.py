"""Prueba de humo: cada pagina del dashboard se ejecuta completa con Streamlit simulado.

No reemplaza mirar la interfaz real, pero detecta errores de codigo antes de abrir el navegador.
"""
import importlib
import sys

import pytest

import db
import importar
import seguridad
from streamlit_falso import StreamlitFalso

PAGINAS = ["resumen", "decision", "datos", "demanda", "simulacion", "historial", "administracion"]


@pytest.fixture()
def entorno(monkeypatch, conn_datos):
    seguridad.crear_usuario(conn_datos, "admin", "clave-segura-1", "administrador")
    usuario = seguridad.autenticar(conn_datos, "admin", "clave-segura-1")

    def cargar(falso):
        monkeypatch.setitem(sys.modules, "streamlit", falso)
        for nombre in ["comun"] + [f"paginas.{p}" for p in PAGINAS]:
            sys.modules.pop(nombre, None)
        return {p: importlib.import_module(f"paginas.{p}") for p in PAGINAS}

    return conn_datos, usuario, cargar


@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_se_ejecuta_sin_errores(entorno, pagina):
    conn, usuario, cargar = entorno
    falso = StreamlitFalso()
    cargar(falso)[pagina].mostrar(conn, usuario)
    assert not falso.errores
    assert falso.llamadas  # dibujo algo


def test_simulacion_con_botones_pulsados_guarda_corrida(entorno):
    conn, usuario, cargar = entorno
    falso = StreamlitFalso(pulsar={"Simular regla vigente", "Comparar reglas", "Calcular sensibilidad"},
                           textos={"Réplicas": 200})
    cargar(falso)["simulacion"].mostrar(conn, usuario)
    assert not falso.errores
    # la corrida comparada debe quedar guardada en el historial
    assert conn.execute("SELECT COUNT(*) FROM corridas").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM resultados_regla").fetchone()[0] >= 2


def test_registrar_salida_desde_la_pagina_de_datos(entorno):
    conn, usuario, cargar = entorno
    falso = StreamlitFalso(pulsar={"Guardar salida"},
                           textos={"Pasajeros con pasaje": 30, "Ausentes a la citación": 4,
                                   "De ellos, llegaron tarde": 3, "Hora real de salida (HH:MM)": "17:20"})
    cargar(falso)["datos"].mostrar(conn, usuario)
    assert not falso.errores
    fila = conn.execute("SELECT demora_min, ausentes FROM registros_salida").fetchone()
    assert fila["demora_min"] == 20.0 and fila["ausentes"] == 4


def test_pagina_administracion_rechaza_a_la_encargada(entorno):
    conn, _, cargar = entorno
    seguridad.crear_usuario(conn, "maria", "otra-clave-22", "encargada")
    encargada = seguridad.autenticar(conn, "maria", "otra-clave-22")
    falso = StreamlitFalso()
    cargar(falso)["administracion"].mostrar(conn, encargada)
    assert falso.errores  # muestra "No tiene permiso"


def test_decision_del_dia_evalua_y_guarda_la_consulta(entorno):
    conn, usuario, cargar = entorno
    falso = StreamlitFalso(pulsar={"Evaluar", "Guardar consulta"},
                           textos={"Pasajeros a bordo desde La Paz": 8, "Pasajes vendidos en Oruro": 24,
                                   "De ellos, ya presentes": 14, "Minutos desde la citación (17:00 = 0)": 5.0})
    cargar(falso)["decision"].mostrar(conn, usuario)
    assert not falso.errores
    fila = conn.execute("SELECT estado, vendidos_oruro, presentes FROM consultas_decision").fetchone()
    assert (fila["estado"], fila["vendidos_oruro"], fila["presentes"]) == ("esperar", 24, 14)


def test_decision_del_dia_rechaza_datos_incoherentes(entorno):
    conn, usuario, cargar = entorno
    falso = StreamlitFalso(pulsar={"Evaluar"}, textos={"Pasajes vendidos en Oruro": 10, "De ellos, ya presentes": 12})
    cargar(falso)["decision"].mostrar(conn, usuario)
    assert any("presentes" in e.lower() for e in falso.errores)
    assert conn.execute("SELECT COUNT(*) FROM consultas_decision").fetchone()[0] == 0

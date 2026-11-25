"""Prueba de humo de app.py (inicio de sesion y menu por rol) con Streamlit simulado."""
import importlib
import sys

import pytest

import db
import seguridad
from streamlit_falso import StreamlitFalso


def _cargar_app(monkeypatch, falso, ruta_bd):
    monkeypatch.setenv("BERMEJENO_DB", str(ruta_bd))
    monkeypatch.setitem(sys.modules, "streamlit", falso)
    for nombre in [m for m in sys.modules if m == "app" or m == "comun" or m.startswith("paginas")]:
        sys.modules.pop(nombre, None)
    return importlib.import_module("app")


def test_sin_usuarios_pide_crear_administrador(monkeypatch, tmp_path):
    falso = StreamlitFalso()
    _cargar_app(monkeypatch, falso, tmp_path / "t.db")
    assert not falso.errores


def test_crear_primer_administrador_con_clave_corta_da_error(monkeypatch, tmp_path):
    falso = StreamlitFalso(pulsar={"Crear administrador"}, textos={"Usuario": "juan", "Contraseña (mínimo 8 caracteres)": "123"})
    _cargar_app(monkeypatch, falso, tmp_path / "t.db")
    assert any("al menos 8" in e for e in falso.errores)
    conn = db.conectar(tmp_path / "t.db")
    assert not seguridad.hay_usuarios(conn)


def test_login_incorrecto_cuenta_intentos_y_no_da_acceso(monkeypatch, tmp_path):
    conn = db.iniciar(db.conectar(tmp_path / "t.db"))
    seguridad.crear_usuario(conn, "juan", "clave-larga-1", "administrador")
    conn.close()
    falso = StreamlitFalso(pulsar={"Ingresar"}, textos={"Usuario": "juan", "Contraseña": "mala"})
    _cargar_app(monkeypatch, falso, tmp_path / "t.db")
    assert falso.session_state.get("usuario") is None
    assert falso.session_state["intentos"] == 1
    assert any("incorrectos" in e for e in falso.errores)
    conn = db.conectar(tmp_path / "t.db")
    assert conn.execute("SELECT COUNT(*) FROM bitacora WHERE accion = 'login_fallido'").fetchone()[0] == 1


def test_login_correcto_guarda_sesion(monkeypatch, tmp_path):
    conn = db.iniciar(db.conectar(tmp_path / "t.db"))
    seguridad.crear_usuario(conn, "juan", "clave-larga-1", "administrador")
    conn.close()
    falso = StreamlitFalso(pulsar={"Ingresar"}, textos={"Usuario": "juan", "Contraseña": "clave-larga-1"})
    _cargar_app(monkeypatch, falso, tmp_path / "t.db")
    assert falso.session_state["usuario"]["rol"] == "administrador"


@pytest.mark.parametrize("rol,esperadas", [("administrador", 7), ("encargada", 6)])
def test_menu_segun_rol(monkeypatch, tmp_path, rol, esperadas):
    conn = db.iniciar(db.conectar(tmp_path / "t.db"))
    seguridad.crear_usuario(conn, "u", "clave-larga-1", rol)
    conn.close()
    falso = StreamlitFalso()
    falso.session_state["usuario"] = {"id": 1, "usuario": "u", "rol": rol}
    visto = {}
    original = falso.radio
    falso.radio = lambda etiqueta, opciones, **k: visto.setdefault("op", list(opciones)) and original(etiqueta, opciones)
    _cargar_app(monkeypatch, falso, tmp_path / "t.db")
    assert len(visto["op"]) == esperadas
    assert ("Administración" in visto["op"]) == (rol == "administrador")

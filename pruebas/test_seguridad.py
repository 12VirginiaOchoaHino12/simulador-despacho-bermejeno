"""Pruebas de seguridad: hash de contrasenas, autenticacion, roles e inyeccion SQL."""
import pytest

import seguridad


def test_la_clave_no_se_guarda_en_texto_plano(conn):
    seguridad.crear_usuario(conn, "juan", "mi-clave-secreta", "administrador")
    fila = conn.execute("SELECT sal, hash FROM usuarios WHERE usuario = 'juan'").fetchone()
    assert "mi-clave-secreta" not in fila["hash"] and "mi-clave-secreta" not in fila["sal"]
    assert len(fila["hash"]) == 64 and len(fila["sal"]) == 32


def test_misma_clave_distinta_sal_distinto_hash():
    s1, h1 = seguridad.hash_clave("clave-de-prueba")
    s2, h2 = seguridad.hash_clave("clave-de-prueba")
    assert s1 != s2 and h1 != h2


def test_autenticacion_correcta_e_incorrecta(conn):
    seguridad.crear_usuario(conn, "maria", "otra-clave-22", "encargada")
    assert seguridad.autenticar(conn, "maria", "otra-clave-22")["rol"] == "encargada"
    assert seguridad.autenticar(conn, "maria", "mala") is None
    assert seguridad.autenticar(conn, "nadie", "otra-clave-22") is None
    assert seguridad.autenticar(conn, "", "") is None


def test_clave_corta_o_rol_invalido_se_rechaza(conn):
    with pytest.raises(ValueError):
        seguridad.crear_usuario(conn, "a", "corta", "encargada")
    with pytest.raises(ValueError):
        seguridad.crear_usuario(conn, "b", "clave-larga-1", "superusuario")
    with pytest.raises(ValueError):
        seguridad.crear_usuario(conn, "  ", "clave-larga-1", "encargada")


def test_usuario_inactivo_no_ingresa(conn):
    seguridad.crear_usuario(conn, "pedro", "clave-larga-1", "encargada")
    conn.execute("UPDATE usuarios SET activo = 0 WHERE usuario = 'pedro'")
    assert seguridad.autenticar(conn, "pedro", "clave-larga-1") is None


def test_inyeccion_sql_en_el_login_no_funciona(conn):
    seguridad.crear_usuario(conn, "juan", "clave-larga-1", "administrador")
    assert seguridad.autenticar(conn, "juan' OR '1'='1", "x") is None
    assert seguridad.autenticar(conn, "' OR 1=1 --", "' OR 1=1 --") is None
    assert conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 1


def test_permisos_por_rol():
    assert seguridad.tiene_permiso("administrador", "usuarios")
    assert seguridad.tiene_permiso("administrador", "importar")
    assert seguridad.tiene_permiso("encargada", "registrar") and seguridad.tiene_permiso("encargada", "simular")
    for p in ("usuarios", "importar", "parametros", "bitacora"):
        assert not seguridad.tiene_permiso("encargada", p)
    assert not seguridad.tiene_permiso("desconocido", "ver")


def test_usuario_duplicado_se_rechaza(conn):
    import sqlite3
    seguridad.crear_usuario(conn, "juan", "clave-larga-1", "administrador")
    with pytest.raises(sqlite3.IntegrityError):
        seguridad.crear_usuario(conn, "juan", "clave-larga-2", "encargada")

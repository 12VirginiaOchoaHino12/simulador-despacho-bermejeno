"""Seguridad: contrasenas con hash (PBKDF2-HMAC-SHA256 con sal), roles y control de acceso.

Solo usa la biblioteca estandar de Python (hashlib, hmac, secrets).
"""
import hashlib
import hmac
import secrets

ITERACIONES = 240_000
ROLES = ("administrador", "encargada")
MIN_LARGO_CLAVE = 8

# Que puede hacer cada rol (control de acceso basado en roles)
PERMISOS = {
    "administrador": {"ver", "registrar", "importar", "simular", "parametros", "usuarios", "bitacora"},
    "encargada": {"ver", "registrar", "simular"},
}


def _derivar(clave, sal_hex):
    return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), bytes.fromhex(sal_hex), ITERACIONES).hex()


def hash_clave(clave):
    """Devuelve (sal_hex, hash_hex). La clave nunca se guarda en texto plano."""
    if not isinstance(clave, str) or len(clave) < MIN_LARGO_CLAVE:
        raise ValueError(f"La clave debe tener al menos {MIN_LARGO_CLAVE} caracteres")
    sal = secrets.token_hex(16)
    return sal, _derivar(clave, sal)


def verificar_clave(clave, sal_hex, hash_hex):
    return hmac.compare_digest(_derivar(clave, sal_hex), hash_hex)


def crear_usuario(conn, usuario, clave, rol):
    usuario = (usuario or "").strip()
    if not usuario:
        raise ValueError("El nombre de usuario no puede estar vacio")
    if rol not in ROLES:
        raise ValueError(f"Rol invalido: {rol}")
    sal, h = hash_clave(clave)
    conn.execute("INSERT INTO usuarios (usuario, rol, sal, hash) VALUES (?, ?, ?, ?)", (usuario, rol, sal, h))
    conn.commit()


def autenticar(conn, usuario, clave):
    """Devuelve {'id', 'usuario', 'rol'} si las credenciales son validas; si no, None."""
    fila = conn.execute(
        "SELECT id, usuario, rol, sal, hash FROM usuarios WHERE usuario = ? AND activo = 1",
        ((usuario or "").strip(),)).fetchone()
    if fila is None:
        # Se calcula igual el hash para no revelar por tiempo si el usuario existe
        _derivar(clave or "", "00" * 16)
        return None
    if not verificar_clave(clave or "", fila["sal"], fila["hash"]):
        return None
    return {"id": fila["id"], "usuario": fila["usuario"], "rol": fila["rol"]}


def hay_usuarios(conn):
    return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] > 0


def tiene_permiso(rol, permiso):
    return permiso in PERMISOS.get(rol, set())

"""Sistema de apoyo a la toma de decisiones - Expreso El Bermejeño S.R.L. (sucursal Oruro).

Ejecutar:  streamlit run app.py
Capas: datos (db.py, importar.py, registro.py) · logica (analisis.py, simulacion.py, simulador_despacho.py,
seguridad.py) · presentacion (app.py y carpeta paginas/).
"""
import os

import streamlit as st

import db
import seguridad
from paginas import administracion, datos, decision, demanda, historial, resumen
from paginas import simulacion as pagina_simulacion

MAX_INTENTOS = 5

PAGINAS = {
    "Resumen": (resumen.mostrar, "ver"),
    "Decisión del día": (decision.mostrar, "simular"),
    "Datos": (datos.mostrar, "ver"),
    "Demanda y ocupación": (demanda.mostrar, "ver"),
    "Simulación": (pagina_simulacion.mostrar, "simular"),
    "Historial": (historial.mostrar, "ver"),
    "Administración": (administracion.mostrar, "usuarios"),
}


def _crear_primer_administrador(conn):
    st.title("Configuración inicial")
    st.write("No hay usuarios. Cree la cuenta del administrador (la contraseña se guarda con hash y sal).")
    with st.form("primer_admin"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña (mínimo 8 caracteres)", type="password")
        enviar = st.form_submit_button("Crear administrador")
    if enviar:
        try:
            seguridad.crear_usuario(conn, usuario, clave, "administrador")
            db.registrar_bitacora(conn, usuario, "crear_primer_administrador")
            st.success("Administrador creado. Recargue la página para iniciar sesión.")
        except ValueError as e:
            st.error(str(e))


def _iniciar_sesion(conn):
    st.title("Sistema de apoyo a la decisión · El Bermejeño")
    st.caption("Despacho de la salida Oruro–Tarija–Bermejo")
    intentos = st.session_state.get("intentos", 0)
    if intentos >= MAX_INTENTOS:
        st.error("Demasiados intentos fallidos. Cierre y vuelva a abrir la página para intentar de nuevo.")
        return
    with st.form("login"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Ingresar")
    if enviar:
        datos_usuario = seguridad.autenticar(conn, usuario, clave)
        if datos_usuario is None:
            st.session_state["intentos"] = intentos + 1
            db.registrar_bitacora(conn, usuario or "?", "login_fallido")
            st.error("Usuario o contraseña incorrectos.")
        else:
            st.session_state["usuario"] = datos_usuario
            st.session_state["intentos"] = 0
            db.registrar_bitacora(conn, datos_usuario["usuario"], "login")
            st.rerun()


def principal():
    st.set_page_config(page_title="El Bermejeño · SAD", page_icon="🚌", layout="wide")
    conn = db.iniciar(db.conectar(os.environ.get("BERMEJENO_DB")))
    try:
        if not seguridad.hay_usuarios(conn):
            _crear_primer_administrador(conn)
            return
        usuario = st.session_state.get("usuario")
        if usuario is None:
            _iniciar_sesion(conn)
            return
        st.sidebar.title("El Bermejeño")
        st.sidebar.write(f"Usuario: **{usuario['usuario']}** ({usuario['rol']})")
        if st.sidebar.button("Cerrar sesión"):
            db.registrar_bitacora(conn, usuario["usuario"], "logout")
            del st.session_state["usuario"]
            st.rerun()
        permitidas = [n for n, (_, permiso) in PAGINAS.items() if seguridad.tiene_permiso(usuario["rol"], permiso)]
        eleccion = st.sidebar.radio("Menú", permitidas)
        PAGINAS[eleccion][0](conn, usuario)
    finally:
        conn.close()


principal()

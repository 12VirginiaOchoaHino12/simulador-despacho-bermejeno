"""Pagina de administracion (solo administrador): parametros del modelo y usuarios."""
import pandas as pd
import streamlit as st

import db
import seguridad
from comun import aplicar_estilo, ETIQUETA_CATEGORIA


def mostrar(conn, usuario):
    aplicar_estilo()
    st.header("Administración")
    if not seguridad.tiene_permiso(usuario["rol"], "usuarios"):
        st.error("No tiene permiso para esta página.")
        return
    t1, t2 = st.tabs(["Parámetros del modelo", "Usuarios"])
    with t1:
        _parametros(conn, usuario)
    with t2:
        _usuarios(conn, usuario)


def _parametros(conn, usuario):
    df = pd.read_sql_query("SELECT clave, valor, categoria, fuente, descripcion FROM parametros ORDER BY clave", conn)
    df["categoria"] = df["categoria"].map(ETIQUETA_CATEGORIA)
    st.dataframe(df, hide_index=True)
    st.caption("Los parámetros sintéticos son supuestos del modelo. Cuando existan datos reales "
               "(registro de salidas), reemplácelos aquí y cambie su categoría en la documentación.")
    claves = list(df["clave"])
    clave = st.selectbox("Parámetro a modificar", claves, key="adm_clave")
    nuevo = st.number_input("Nuevo valor", value=float(conn.execute("SELECT valor FROM parametros WHERE clave = ?",
                                                                     (clave,)).fetchone()[0]), key="adm_valor")
    if st.button("Guardar parámetro", key="adm_guardar"):
        try:
            db.guardar_parametro(conn, clave, nuevo)
        except ValueError as e:
            st.error(str(e))
            return
        db.registrar_bitacora(conn, usuario["usuario"], "modificar_parametro", f"{clave}={nuevo}")
        st.success(f"{clave} actualizado.")


def _usuarios(conn, usuario):
    us = pd.read_sql_query("SELECT id, usuario, rol, activo, creado FROM usuarios ORDER BY id", conn)
    st.dataframe(us, hide_index=True)
    st.subheader("Crear usuario")
    with st.form("form_usuario"):
        nombre = st.text_input("Usuario")
        clave = st.text_input("Contraseña (mínimo 8 caracteres)", type="password")
        rol = st.selectbox("Rol", list(seguridad.ROLES))
        enviar = st.form_submit_button("Crear usuario")
    if enviar:
        try:
            seguridad.crear_usuario(conn, nombre, clave, rol)
        except ValueError as e:
            st.error(str(e))
            return
        db.registrar_bitacora(conn, usuario["usuario"], "crear_usuario", f"{nombre} ({rol})")
        st.success(f"Usuario {nombre} creado.")
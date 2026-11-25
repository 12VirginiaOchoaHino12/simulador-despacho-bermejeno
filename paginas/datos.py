"""Pagina de datos: ver viajes, registrar una salida nueva, importar el Excel y revisar la calidad."""
from datetime import date

import streamlit as st

import analisis
import db
import importar
import registro
import seguridad
from comun import formato_df


def mostrar(conn, usuario):
    st.header("Datos")
    rol = usuario["rol"]
    nombres = ["Viajes", "Registrar salida", "Calidad de datos"]
    if seguridad.tiene_permiso(rol, "importar"):
        nombres.append("Importar Excel")
    pestañas = st.tabs(nombres)
    with pestañas[0]:
        _viajes(conn)
    with pestañas[1]:
        _registrar(conn, usuario)
    with pestañas[2]:
        _calidad(conn)
    if seguridad.tiene_permiso(rol, "importar"):
        with pestañas[3]:
            _importar(conn, usuario)


def _viajes(conn):
    c1, c2 = st.columns(2)
    calidad = c1.selectbox("Calidad", ["Todos", "OK", "Revisar"], key="datos_calidad")
    tipo = c2.selectbox("Tipo de hoja", ["Todos", "Oruro→Bermejo", "Recorrido completo"], key="datos_tipo")
    df = analisis.cargar_viajes(conn)
    if df.empty:
        st.info("No hay viajes cargados.")
        return
    if calidad != "Todos":
        df = df[df["calidad"] == calidad]
    if tipo != "Todos":
        df = df[df["tipo"] == tipo]
    cols = ["codigo", "fecha", "dia", "ruta", "bus", "hora_impresa", "pasajeros", "pasajeros_oruro", "capacidad",
            "ocupacion", "calidad", "nota"]
    st.dataframe(formato_df(df[cols]), hide_index=True)
    st.download_button("Descargar CSV", df[cols].to_csv(index=False).encode("utf-8-sig"), file_name="viajes.csv",
                       mime="text/csv")
    st.caption("La hora impresa es la de la hoja de viaje; su significado exacto está por confirmar con la empresa.")


def _registrar(conn, usuario):
    st.subheader("Registrar una salida nueva")
    st.caption("Estos datos reemplazan con el tiempo los parámetros sintéticos (ausentes, hora real de salida).")
    buses = [r[0] for r in conn.execute("SELECT numero FROM buses ORDER BY numero").fetchall()]
    with st.form("form_salida"):
        c1, c2 = st.columns(2)
        fecha = c1.date_input("Fecha", value=date.today())
        bus = c2.selectbox("Bus", buses)
        c3, c4, c5 = st.columns(3)
        pas = c3.number_input("Pasajeros con pasaje", min_value=0, max_value=60, value=0, step=1)
        aus = c4.number_input("Ausentes a la citación", min_value=0, max_value=60, value=0, step=1)
        tarde = c5.number_input("De ellos, llegaron tarde", min_value=0, max_value=60, value=0, step=1)
        c6, c7 = st.columns(2)
        cita = c6.text_input("Hora de citación (HH:MM)", value="17:00")
        salida = c7.text_input("Hora real de salida (HH:MM)", value="17:15")
        obs = st.text_input("Observaciones (opcional)")
        enviar = st.form_submit_button("Guardar salida")
    if enviar:
        try:
            rid = registro.registrar_salida(conn, usuario["id"], fecha.isoformat(), bus, int(pas), int(aus),
                                            int(tarde), salida, cita, obs or None)
            db.registrar_bitacora(conn, usuario["usuario"], "registrar_salida", f"id={rid}")
            st.success(f"Salida guardada (registro {rid}).")
        except ValueError as e:
            st.error(str(e))
    reg = registro.listar_registros(conn)
    if not reg.empty:
        st.dataframe(reg, hide_index=True)
        est = registro.estimaciones_reales(conn)
        st.write(f"Con {est['n']} salidas registradas: demora media {est['demora_media']:.1f} min; "
                 f"ausentes {est['pct_ausentes']:.1f} % de los pasajes.")
        if not est["suficiente"]:
            st.caption("Aún son pocos registros (menos de 30) para reemplazar los parámetros sintéticos.")


def _calidad(conn):
    df = analisis.cargar_viajes(conn)
    if df.empty:
        st.info("No hay viajes cargados.")
        return
    st.subheader("Calidad de los registros")
    st.dataframe(analisis.calidad_datos(df), hide_index=True)
    st.markdown("**Registros por revisar** (se importan, pero con la marca *Revisar* y su nota):")
    rev = df[df["calidad"] == "Revisar"][["codigo", "fecha", "ruta", "pasajeros", "nota"]]
    st.dataframe(rev, hide_index=True)
    st.markdown("**Hojas por debajo del mínimo** (la mitad de la capacidad):")
    st.dataframe(analisis.bajo_minimo(df), hide_index=True)


def _importar(conn, usuario):
    st.subheader("Importar el Excel de registros")
    st.write("Se lee la hoja *Pasajeros*. Un código de viaje ya existente no se duplica.")
    archivo = st.file_uploader("Archivo .xlsx", type=["xlsx"])
    if archivo is not None and st.button("Importar"):
        try:
            inf = importar.importar_excel(conn, archivo)
        except Exception as e:  # archivo invalido
            st.error(f"No se pudo importar: {e}")
            return
        db.registrar_bitacora(conn, usuario["usuario"], "importar_excel",
                              f"importados={inf['importados']} repetidos={inf['repetidos']} "
                              f"rechazados={inf['rechazados']}")
        st.success(f"Importados: {inf['importados']} · repetidos: {inf['repetidos']} · "
                   f"rechazados: {inf['rechazados']} · por revisar: {inf['con_calidad_revisar']}")
        for e in inf["errores"]:
            st.warning(e)

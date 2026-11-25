"""Registro de salidas nuevas: aqui la sucursal carga los datos que hoy no existen (ausentes, hora real de salida).

Con estos registros los parametros sinteticos (puntualidad, retraso, cierre) se pueden reemplazar por datos reales.
"""
from datetime import datetime

import pandas as pd


def _minutos(hhmm):
    try:
        t = datetime.strptime(hhmm.strip(), "%H:%M")
    except (AttributeError, ValueError):
        raise ValueError(f"Hora invalida: {hhmm!r} (use HH:MM, por ejemplo 17:24)")
    return t.hour * 60 + t.minute


def calcular_demora(hora_citacion, hora_salida):
    """Demora de salida en minutos = hora de salida - hora de citacion (no puede ser negativa)."""
    d = _minutos(hora_salida) - _minutos(hora_citacion)
    if d < 0:
        raise ValueError("La hora de salida no puede ser anterior a la hora de citación")
    return float(d)


def registrar_salida(conn, usuario_id, fecha, bus, pasajeros_pasaje, ausentes, llegaron_tarde,
                     hora_salida_real, hora_citacion="17:00", observaciones=None, capacidad=None):
    """Valida y guarda una salida. Devuelve el id del registro."""
    try:
        datetime.strptime(str(fecha), "%Y-%m-%d")
    except ValueError:
        raise ValueError("La fecha debe tener el formato AAAA-MM-DD")
    if bus is not None:
        fila = conn.execute("SELECT capacidad FROM buses WHERE numero = ?", (bus,)).fetchone()
        if fila is None and capacidad is None:
            raise ValueError(f"El bus {bus} no está registrado; indique la capacidad")
        capacidad = capacidad or fila["capacidad"]
    if not capacidad or capacidad <= 0:
        raise ValueError("La capacidad debe ser mayor que cero")
    for nombre, v in (("pasajeros con pasaje", pasajeros_pasaje), ("ausentes", ausentes),
                      ("llegaron tarde", llegaron_tarde)):
        if int(v) != v or v < 0:
            raise ValueError(f"{nombre.capitalize()} debe ser un entero no negativo")
    if pasajeros_pasaje > capacidad:
        raise ValueError("Los pasajeros con pasaje superan la capacidad del bus")
    if ausentes > pasajeros_pasaje:
        raise ValueError("Los ausentes no pueden superar los pasajeros con pasaje")
    if llegaron_tarde > ausentes:
        raise ValueError("Los que llegaron tarde no pueden superar a los ausentes a la citación")
    demora = calcular_demora(hora_citacion, hora_salida_real)
    cur = conn.execute(
        """INSERT INTO registros_salida (fecha, bus, capacidad, pasajeros_pasaje, ausentes, llegaron_tarde,
               hora_citacion, hora_salida_real, demora_min, observaciones, usuario_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(fecha), bus, int(capacidad), int(pasajeros_pasaje), int(ausentes), int(llegaron_tarde),
         hora_citacion, hora_salida_real, demora, observaciones, usuario_id))
    conn.commit()
    return cur.lastrowid


def listar_registros(conn):
    return pd.read_sql_query(
        """SELECT r.id, r.fecha, r.bus, r.capacidad, r.pasajeros_pasaje, r.ausentes, r.llegaron_tarde,
                  r.hora_citacion, r.hora_salida_real, r.demora_min, r.observaciones, u.usuario
           FROM registros_salida r JOIN usuarios u ON u.id = r.usuario_id ORDER BY r.fecha DESC, r.id DESC""", conn)


def estimaciones_reales(conn):
    """Estimaciones con datos reales registrados por la sucursal (reemplazan supuestos cuando n es suficiente)."""
    df = pd.read_sql_query("SELECT * FROM registros_salida", conn)
    n = len(df)
    if n == 0:
        return dict(n=0)
    pas = int(df["pasajeros_pasaje"].sum())
    return dict(n=n, demora_media=float(df["demora_min"].mean()), demora_max=float(df["demora_min"].max()),
                pct_ausentes=100 * float(df["ausentes"].sum()) / pas if pas else 0.0,
                pct_tarde_de_ausentes=100 * float(df["llegaron_tarde"].sum()) / float(df["ausentes"].sum())
                if df["ausentes"].sum() else 0.0,
                suficiente=n >= 30)

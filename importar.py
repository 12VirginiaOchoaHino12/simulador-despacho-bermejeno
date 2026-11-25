"""Importacion y depuracion de los registros historicos desde el Excel (hoja 'Pasajeros').

Reglas de depuracion (cada una queda contada en el informe devuelto):
  R1. Solo se leen filas con codigo de viaje y fecha valida (se omiten encabezados, totales y notas).
  R2. pasajeros, pasajeros de Oruro y capacidad deben ser enteros no negativos; capacidad > 0.
  R3. Los pasajeros de Oruro no pueden superar los pasajeros totales ni estos la capacidad aceptada del bus.
      (Si superan la capacidad se importa igual, pero con calidad 'Revisar' y una nota.)
  R4. Un codigo de viaje ya existente no se duplica (la importacion se puede repetir sin riesgo).
  R5. La calidad 'Revisar' y la nota que trae el Excel se conservan; nada se descarta en silencio.
"""
from datetime import date, datetime, time

import openpyxl

COL = dict(codigo=0, fecha=1, ruta=3, bus=4, hora=5, pasajeros=6, monto=7, oruro=8, capacidad=10, calidad=14, nota=15)


def _hora(valor):
    if valor is None:
        return None
    if isinstance(valor, (time, datetime)):
        return valor.strftime("%H:%M")
    texto = str(valor).strip()
    return texto or None


def _entero(valor):
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return int(numero) if numero == int(numero) and numero >= 0 else None


def _bus(valor):
    n = _entero(valor)
    return n if n else None  # '—' o vacio -> sin bus identificado


def leer_filas(archivo):
    """Lee la hoja 'Pasajeros' y devuelve (filas validas como dict, lista de errores)."""
    libro = openpyxl.load_workbook(archivo, data_only=True, read_only=False)
    if "Pasajeros" not in libro.sheetnames:
        raise ValueError("El archivo no tiene la hoja 'Pasajeros'")
    filas, errores = [], []
    for n, r in enumerate(libro["Pasajeros"].iter_rows(min_row=5, values_only=True), start=5):
        r = tuple(r) + (None,) * (16 - len(r))  # filas mas cortas si las ultimas columnas estan vacias
        codigo, fecha = r[COL["codigo"]], r[COL["fecha"]]
        if not codigo or not isinstance(fecha, (datetime, date)):
            continue  # R1: encabezados, totales y notas
        pasajeros, oruro, capacidad = _entero(r[COL["pasajeros"]]), _entero(r[COL["oruro"]]), _entero(r[COL["capacidad"]])
        if None in (pasajeros, oruro) or not capacidad:
            errores.append(f"Fila {n} ({codigo}): pasajeros, pasajeros de Oruro o capacidad invalidos")  # R2
            continue
        if oruro > pasajeros:
            errores.append(f"Fila {n} ({codigo}): pasajeros de Oruro ({oruro}) mayores que el total ({pasajeros})")  # R3
            continue
        ruta = str(r[COL["ruta"]] or "").strip()
        calidad = str(r[COL["calidad"]] or "OK").strip()
        nota = r[COL["nota"]]
        if pasajeros > capacidad:
            calidad = "Revisar"
            nota = f"{nota + ' ' if nota else ''}Pasajeros ({pasajeros}) mayores que la capacidad ({capacidad})."
        filas.append(dict(
            codigo=str(codigo).strip(),
            fecha=(fecha.date() if isinstance(fecha, datetime) else fecha).isoformat(),
            ruta=ruta,
            tipo_hoja="oruro_bermejo" if ruta.lower().startswith("oruro") else "recorrido_completo",
            bus=_bus(r[COL["bus"]]),
            hora_impresa=_hora(r[COL["hora"]]),
            pasajeros=pasajeros,
            monto_bs=float(r[COL["monto"]]) if isinstance(r[COL["monto"]], (int, float)) else None,
            pasajeros_oruro=oruro,
            capacidad=capacidad,
            calidad=calidad if calidad in ("OK", "Revisar") else "Revisar",
            nota=str(nota).strip() if nota else None,
        ))
    return filas, errores


def importar_excel(conn, archivo):
    """Importa los viajes a la base. Devuelve un informe con cifras de control."""
    filas, errores = leer_filas(archivo)
    nuevos = repetidos = 0
    for f in filas:
        if f["bus"] is not None and conn.execute("SELECT 1 FROM buses WHERE numero = ?", (f["bus"],)).fetchone() is None:
            conn.execute("INSERT INTO buses (numero, capacidad, fuente) VALUES (?, ?, ?)",
                         (f["bus"], f["capacidad"], "Tomado de la hoja importada; por confirmar"))
        existe = conn.execute("SELECT 1 FROM viajes WHERE codigo = ?", (f["codigo"],)).fetchone()
        if existe:
            repetidos += 1  # R4
            continue
        conn.execute(
            """INSERT INTO viajes (codigo, fecha, ruta, tipo_hoja, bus, hora_impresa, pasajeros, monto_bs,
                                   pasajeros_oruro, capacidad, calidad, nota, categoria)
               VALUES (:codigo, :fecha, :ruta, :tipo_hoja, :bus, :hora_impresa, :pasajeros, :monto_bs,
                       :pasajeros_oruro, :capacidad, :calidad, :nota, 'historico')""", f)
        nuevos += 1
    conn.commit()
    return dict(leidos=len(filas) + len(errores), importados=nuevos, repetidos=repetidos,
                rechazados=len(errores), errores=errores,
                con_calidad_revisar=sum(1 for f in filas if f["calidad"] == "Revisar"))

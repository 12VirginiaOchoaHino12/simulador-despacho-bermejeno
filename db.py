"""Capa de datos: esquema SQLite y acceso a la base.

Todas las consultas usan parametros (?), nunca texto concatenado, para evitar inyeccion SQL.
Cada dato lleva una categoria de origen: observado, historico, por_obtener, sintetico o configurado.
"""
import sqlite3
from pathlib import Path

# Rangos de validación de parámetros (mismo conjunto que usa simulacion.LIMITES)
LIMITES = {"p_puntual": (0.0, 1.0), "mu_tarde": (0.1, 60.0), "cierre_min": (0.0, 60.0),
           "cierre_max": (0.0, 60.0), "tope": (0.0, 120.0)}

RUTA_BD = Path(__file__).resolve().parent / "datos" / "bermejeno.db"

ESQUEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario     TEXT NOT NULL UNIQUE,
    rol         TEXT NOT NULL CHECK (rol IN ('administrador', 'encargada')),
    sal         TEXT NOT NULL,
    hash        TEXT NOT NULL,
    activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS buses (
    numero      INTEGER PRIMARY KEY,
    capacidad   INTEGER NOT NULL CHECK (capacidad > 0),
    fuente      TEXT NOT NULL DEFAULT 'Confirmado por la empresa'
);

CREATE TABLE IF NOT EXISTS viajes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo           TEXT NOT NULL UNIQUE,
    fecha            TEXT NOT NULL,                       -- AAAA-MM-DD
    ruta             TEXT NOT NULL,
    tipo_hoja        TEXT NOT NULL CHECK (tipo_hoja IN ('oruro_bermejo', 'recorrido_completo')),
    bus              INTEGER REFERENCES buses(numero),
    hora_impresa     TEXT,                                -- HH:MM, sin confirmar su significado
    pasajeros        INTEGER NOT NULL CHECK (pasajeros >= 0),
    monto_bs         REAL,
    pasajeros_oruro  INTEGER NOT NULL CHECK (pasajeros_oruro >= 0),
    capacidad        INTEGER NOT NULL CHECK (capacidad > 0),
    calidad          TEXT NOT NULL CHECK (calidad IN ('OK', 'Revisar')),
    nota             TEXT,
    categoria        TEXT NOT NULL DEFAULT 'historico'
                     CHECK (categoria IN ('observado', 'historico', 'por_obtener', 'sintetico', 'configurado')),
    CHECK (pasajeros_oruro <= pasajeros)
);

CREATE TABLE IF NOT EXISTS salidas_observadas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       TEXT,                                     -- puede ser desconocida
    citacion    TEXT NOT NULL DEFAULT '17:00',
    salida_real TEXT NOT NULL,
    demora_min  REAL NOT NULL CHECK (demora_min >= 0),
    categoria   TEXT NOT NULL DEFAULT 'observado',
    nota        TEXT
);

-- Datos nuevos que la sucursal registra salida por salida (insumo para reemplazar supuestos).
CREATE TABLE IF NOT EXISTS registros_salida (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha             TEXT NOT NULL,
    bus               INTEGER REFERENCES buses(numero),
    capacidad         INTEGER NOT NULL CHECK (capacidad > 0),
    pasajeros_pasaje  INTEGER NOT NULL CHECK (pasajeros_pasaje >= 0),
    ausentes          INTEGER NOT NULL CHECK (ausentes >= 0),
    llegaron_tarde    INTEGER NOT NULL DEFAULT 0 CHECK (llegaron_tarde >= 0),
    hora_citacion     TEXT NOT NULL DEFAULT '17:00',
    hora_salida_real  TEXT NOT NULL,
    demora_min        REAL NOT NULL CHECK (demora_min >= 0),
    observaciones     TEXT,
    usuario_id        INTEGER NOT NULL REFERENCES usuarios(id),
    creado            TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (ausentes <= pasajeros_pasaje),
    CHECK (llegaron_tarde <= ausentes)
);

CREATE TABLE IF NOT EXISTS parametros (
    clave        TEXT PRIMARY KEY,
    valor        REAL NOT NULL,
    categoria    TEXT NOT NULL
                 CHECK (categoria IN ('observado', 'historico', 'por_obtener', 'sintetico', 'configurado')),
    fuente       TEXT NOT NULL,
    descripcion  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS corridas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    creado            TEXT NOT NULL DEFAULT (datetime('now')),
    usuario_id        INTEGER REFERENCES usuarios(id),
    etiqueta          TEXT,
    escenario         TEXT NOT NULL,
    capacidad         INTEGER NOT NULL,
    nrep              INTEGER NOT NULL CHECK (nrep > 0),
    semilla           INTEGER NOT NULL,
    parametros_json   TEXT NOT NULL,
    nota              TEXT NOT NULL DEFAULT 'Parametros sinteticos: resultado del modelo, no de la empresa'
);

CREATE TABLE IF NOT EXISTS resultados_regla (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    corrida_id        INTEGER NOT NULL REFERENCES corridas(id) ON DELETE CASCADE,
    regla             TEXT NOT NULL,
    umbral_k          INTEGER NOT NULL,
    espera_max_T      REAL,
    demora_media      REAL NOT NULL,
    demora_mediana    REAL NOT NULL,
    ocupacion_media   REAL NOT NULL,
    pct_espero        REAL NOT NULL,
    pct_sin_minimo    REAL NOT NULL,
    dif_demora        REAL,
    dif_ic_inf        REAL,
    dif_ic_sup        REAL,
    dif_ocupacion     REAL
);

-- Consultas de la recomendacion en vivo y, si se conoce, la decision que realmente se tomo.
CREATE TABLE IF NOT EXISTS consultas_decision (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    creado               TEXT NOT NULL DEFAULT (datetime('now')),
    usuario_id           INTEGER NOT NULL REFERENCES usuarios(id),
    capacidad            INTEGER NOT NULL CHECK (capacidad IN (36, 49)),
    a_bordo              INTEGER NOT NULL CHECK (a_bordo >= 0),
    vendidos_oruro       INTEGER NOT NULL CHECK (vendidos_oruro >= 0),
    presentes            INTEGER NOT NULL CHECK (presentes >= 0),
    minutos              REAL NOT NULL CHECK (minutos >= 0),
    umbral_k             INTEGER NOT NULL,
    estado               TEXT NOT NULL CHECK (estado IN ('cumplida', 'esperar', 'tope')),
    prob_antes_del_tope  REAL NOT NULL,
    espera_mediana       REAL,
    decision_tomada      TEXT CHECK (decision_tomada IN ('espero', 'salio')),
    observaciones        TEXT,
    CHECK (presentes <= vendidos_oruro)
);

CREATE TABLE IF NOT EXISTS bitacora (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha     TEXT NOT NULL DEFAULT (datetime('now')),
    usuario   TEXT,
    accion    TEXT NOT NULL,
    detalle   TEXT
);

CREATE INDEX IF NOT EXISTS ix_viajes_fecha ON viajes(fecha);
CREATE INDEX IF NOT EXISTS ix_viajes_tipo ON viajes(tipo_hoja);
CREATE INDEX IF NOT EXISTS ix_resultados_corrida ON resultados_regla(corrida_id);
"""

# Parametros del modelo (valores de simulador_despacho.py y del Capitulo IV/V)
PARAMETROS_INICIALES = [
    ("hora_citacion_min", 0.0, "configurado", "Dato de la empresa", "Hora de citacion (17:00 = minuto 0)"),
    ("minimo_fraccion", 0.5, "configurado", "Regla ATT informada por la empresa",
     "Minimo de pasajeros como fraccion de la capacidad (la mitad)"),
    ("umbral_k", 5, "configurado", "Regla descrita por el personal",
     "Se espera si faltan mas de k pasajeros con pasaje"),
    ("p_puntual", 0.3, "sintetico", "Calibrado en el Capitulo V", "Probabilidad de llegar a la citacion o antes"),
    ("mu_tarde", 5.0, "sintetico", "Calibrado en el Capitulo V", "Retraso medio de quien llega tarde (min)"),
    ("cierre_min", 15.0, "sintetico", "Calibrado en el Capitulo V", "Tiempo minimo de cierre y arranque (min)"),
    ("cierre_max", 20.0, "sintetico", "Calibrado en el Capitulo V", "Tiempo maximo de cierre y arranque (min)"),
    ("tope", 20.0, "sintetico", "Calibrado en el Capitulo V", "Espera maxima aceptada sin cumplir el minimo (min)"),
    ("weibull_forma", 1.659, "historico", "Tabla 28 (45 hojas)", "Forma de la Weibull de pasajeros de Oruro"),
    ("weibull_escala", 17.905, "historico", "Tabla 28 (45 hojas)", "Escala de la Weibull de pasajeros de Oruro"),
]

BUSES_INICIALES = [
    (12, 36, "Confirmado por la empresa (36)"),
    (14, 36, "Confirmado por la empresa (36)"),
    (18, 36, "Confirmado por la empresa (36)"),
    (22, 36, "Confirmado por la empresa (36)"),
    (26, 36, "Confirmado por la empresa (36)"),
    (610, 36, "Confirmado por la empresa (36)"),
    (500, 49, "Confirmado por la empresa (49)"),
]

# Las 3 salidas de la observacion exploratoria (20 al 23 de octubre de 2026); la fecha exacta de cada una no se registro.
SALIDAS_OBSERVADAS = [("17:15", 15.0), ("17:24", 24.0), ("17:30", 30.0)]


def conectar(ruta=None):
    """Abre la base (por defecto datos/bermejeno.db). Use ':memory:' en pruebas."""
    ruta = str(ruta or RUTA_BD)
    if ruta != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def iniciar(conn):
    """Crea tablas y carga parametros, buses y salidas observadas si aun no existen."""
    conn.executescript(ESQUEMA)
    conn.executemany(
        "INSERT OR IGNORE INTO parametros (clave, valor, categoria, fuente, descripcion) VALUES (?, ?, ?, ?, ?)",
        PARAMETROS_INICIALES)
    conn.executemany("INSERT OR IGNORE INTO buses (numero, capacidad, fuente) VALUES (?, ?, ?)", BUSES_INICIALES)
    if conn.execute("SELECT COUNT(*) FROM salidas_observadas").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO salidas_observadas (fecha, salida_real, demora_min, nota) VALUES (NULL, ?, ?, ?)",
            [(h, d, "Observacion exploratoria 20-23/10/2026; fecha exacta no registrada")
             for h, d in SALIDAS_OBSERVADAS])
    conn.commit()
    return conn


def registrar_bitacora(conn, usuario, accion, detalle=""):
    conn.execute("INSERT INTO bitacora (usuario, accion, detalle) VALUES (?, ?, ?)", (usuario, accion, detalle))
    conn.commit()


def leer_parametros(conn):
    """Devuelve {clave: valor} y {clave: categoria}."""
    filas = conn.execute("SELECT clave, valor, categoria FROM parametros").fetchall()
    return {f["clave"]: f["valor"] for f in filas}, {f["clave"]: f["categoria"] for f in filas}


def guardar_parametro(conn, clave, valor):
    if conn.execute("SELECT 1 FROM parametros WHERE clave = ?", (clave,)).fetchone() is None:
        raise ValueError(f"Parametro desconocido: {clave}")
    if clave in LIMITES:
        lo, hi = LIMITES[clave]
        if not lo <= float(valor) <= hi:
            raise ValueError(f"{clave} = {float(valor)} fuera del rango [{lo}, {hi}]")
    conn.execute("UPDATE parametros SET valor = ? WHERE clave = ?", (float(valor), clave))
    conn.commit()

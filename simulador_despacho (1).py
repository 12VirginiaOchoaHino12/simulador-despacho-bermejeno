"""Simulador de eventos discretos del despacho de la salida Oruro-Tarija/Bermejo.
Tiempo en minutos con origen en la citacion (17:00 = 0). Lista de eventos propia (heapq).
Datos de entrada: ver Capitulo IV (Tablas 28, 30 y 31). Los parametros de puntualidad de los
pasajeros y el tiempo de cierre son SINTETICOS (no observados) y se calibran en el Capitulo V.
"""
from dataclasses import dataclass, field
import heapq, math
import numpy as np
BUS_LLEGADA = -30.0          # 16:30, constante (variacion no medida)
WEIBULL_FORMA, WEIBULL_ESCALA = 1.659, 17.905   # Tabla 28
P25, P75 = 7, 23             # Tabla 30
TOTAL_MEDIA, TOTAL_DE = 27.40, 6.15   # pasajes por hoja de viaje (Tabla 26); normalidad no rechazada (p = 0,210)
@dataclass(frozen=True)
class Regla:
    nombre: str
    umbral: int = 5              # espera si faltan mas de 'umbral' pasajeros con pasaje
    espera_max: float = None     # T (minutos desde la citacion); None = sin tope de la regla
VIGENTE = Regla("Vigente", 5, None)
@dataclass
class Parametros:
    p_puntual: float = 0.5       # prob. de llegar a la citacion o antes (sintetico)
    mu_tarde: float = 12.0       # media del retraso de quien llega tarde, min (sintetico)
    cierre_min: float = 10.0     # tiempo de cierre y arranque, U(min, max), min (sintetico)
    cierre_max: float = 20.0
    tope: float = 20.0           # espera maxima aceptada aun sin cumplir el minimo, min (sintetico)
PARAMETROS_CALIBRADOS = None
def minimo(cap):                 # mitad de la capacidad; enteros: 36 -> 18, 49 (24,5) -> 25
    return math.ceil(cap / 2)
def muestrear_demanda(rng, escenario="todos"):
    """Pasajes vendidos en Oruro: Weibull redondeada (Tabla 28), acotada por escenario (Tabla 30)."""
    lo, hi = {"todos": (1, 10**9), "baja": (1, P25), "habitual": (P25 + 1, P75 - 1), "alta": (P75, 10**9)}[escenario]
    while True:
        n = int(round(WEIBULL_ESCALA * rng.weibull(WEIBULL_FORMA)))
        if lo <= n <= hi:
            return n
def generar_entradas(seed, cap, escenario, par):
    """Todas las variables aleatorias de un dia; se reutilizan con todas las reglas (numeros comunes)."""
    rng = np.random.default_rng(seed)
    n = muestrear_demanda(rng, escenario)
    total = int(round(min(40, max(16, rng.normal(TOTAL_MEDIA, TOTAL_DE)))))
    l = max(0, total - n)      # pasajeros que continuan a bordo desde La Paz
    n = max(0, min(n, cap - l))
    u_punt = rng.random(n); u_t = rng.random(n); u_c = rng.random()
    llegadas = np.where(u_punt < par.p_puntual, -60.0 * u_t, -par.mu_tarde * np.log1p(-u_t))
    cierre = par.cierre_min + (par.cierre_max - par.cierre_min) * u_c
    return dict(cap=cap, n=n, l=l, llegadas=np.sort(llegadas), cierre=cierre, tope=par.tope)
def simular(ent, regla):
    """Un dia. Eventos: llegada del bus, llegada de pasajeros, citacion, limite T, tope y salida."""
    cap, l, cierre = ent["cap"], ent["l"], ent["cierre"]
    m = minimo(cap); n = len(ent["llegadas"])
    ev = []; seq = 0
    def push(t, tipo, dato=None):
        nonlocal seq; heapq.heappush(ev, (t, seq, tipo, dato)); seq += 1
    push(BUS_LLEGADA, "bus"); push(0.0, "citacion"); push(ent["tope"], "tope")
    for t in ent["llegadas"]: push(float(t), "pasajero")
    if regla.espera_max is not None: push(regla.espera_max, "limite_T")
    presentes = 0; citado = False; limite = False; listo_en = None; salida = None; sin_minimo = False
    def listo(t):
        total = l + presentes; ausentes = n - presentes
        if total < m: return False
        return ausentes <= regla.umbral or limite
    while ev:
        t, _, tipo, _d = heapq.heappop(ev)
        if tipo == "pasajero" and salida is None: presentes += 1
        elif tipo == "citacion": citado = True
        elif tipo == "limite_T": limite = True
        elif tipo == "tope" and salida is None and listo_en is None:
            sin_minimo = (l + presentes) < m; listo_en = t; push(t + cierre, "salida"); continue
        elif tipo == "salida" and salida is None:
            salida = t
            # pasajeros que llegan hasta la salida abordan: ya contados porque 'presentes' se actualiza hasta aqui
            break
        if citado and listo_en is None and listo(t):
            listo_en = max(t, 0.0); push(listo_en + cierre, "salida")
    abordados = min(cap, l + presentes)
    return dict(salida=salida, demora=salida, abordados=abordados, ocupacion=100 * abordados / cap,
                ausentes_citacion=int(np.sum(ent["llegadas"] > 0)), espero=listo_en is not None and listo_en > 0,
                sin_minimo=sin_minimo, no_atendida=max(0, l + n - cap))
# Parametros sinteticos calibrados en el Capitulo V (Tabla 36): objetivo = salidas observadas de 15 a 30 min
PARAMETROS_CALIBRADOS = Parametros(p_puntual=0.3, mu_tarde=5.0, cierre_min=15.0, cierre_max=20.0, tope=20.0)
def correr(regla, escenario="todos", cap=36, nrep=1000, seed0=1000, par=None):
    par = par or PARAMETROS_CALIBRADOS
    return [simular(generar_entradas(seed0 + i, cap, escenario, par), regla) for i in range(nrep)]
def correr_mezcla(regla, escenario="todos", nrep=1500, seed0=1000, par=None):
    """Flota real: 36 asientos en todos los buses y 49 en el movil 500 (3 de 45 hojas = 1 de cada 15)."""
    par = par or PARAMETROS_CALIBRADOS
    return [simular(generar_entradas(seed0 + i, 49 if i % 15 == 0 else 36, escenario, par), regla) for i in range(nrep)]

"""Analisis de demanda y ocupacion a partir de la base (reproduce las Tablas 26 a 30 del Capitulo IV)."""
import numpy as np
import pandas as pd
from scipy import stats

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
         9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
ETIQUETA_TIPO = {"oruro_bermejo": "Oruro→Bermejo", "recorrido_completo": "Recorrido completo"}


def cargar_viajes(conn, solo_ok=False, tipo=None):
    """Viajes como DataFrame con ocupacion (%), mes y dia de la semana. Filtros opcionales."""
    consulta, args = "SELECT * FROM viajes WHERE 1 = 1", []
    if solo_ok:
        consulta += " AND calidad = 'OK'"
    if tipo:
        consulta += " AND tipo_hoja = ?"
        args.append(tipo)
    df = pd.read_sql_query(consulta + " ORDER BY fecha, codigo", conn, params=args)
    if df.empty:
        return df
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["bus"] = df["bus"].astype("Int64")
    df["ocupacion"] = 100 * df["pasajeros"] / df["capacidad"]
    df["mes"] = df["fecha"].dt.month.map(MESES)
    df["mes_num"] = df["fecha"].dt.month
    df["dia"] = df["fecha"].dt.dayofweek.map(lambda i: DIAS[i])
    df["dia_num"] = df["fecha"].dt.dayofweek
    df["tipo"] = df["tipo_hoja"].map(ETIQUETA_TIPO)
    return df


def resumen_general(df):
    if df.empty:
        return dict(viajes=0, pasajeros=0, pasajeros_oruro=0, promedio_pasajeros=0.0, ocupacion_media=0.0,
                    revisar=0)
    return dict(viajes=len(df), pasajeros=int(df["pasajeros"].sum()), pasajeros_oruro=int(df["pasajeros_oruro"].sum()),
                promedio_pasajeros=float(df["pasajeros"].mean()), ocupacion_media=float(df["ocupacion"].mean()),
                revisar=int((df["calidad"] == "Revisar").sum()))


def por_mes(df):
    g = df.groupby(["mes_num", "mes"]).agg(viajes=("codigo", "count"), pasajeros=("pasajeros", "sum"),
                                           pasajeros_oruro=("pasajeros_oruro", "sum"),
                                           ocupacion=("ocupacion", "mean")).reset_index()
    return g.drop(columns="mes_num").rename(columns={"mes": "Mes"})


def descriptiva(df):
    """Tabla 26: estadistica descriptiva de las variables con registros."""
    def fila(nombre, x):
        x = pd.Series(x).astype(float)
        return dict(Variable=nombre, n=len(x), Media=x.mean(), Mediana=x.median(),
                    **{"Desv. est.": x.std(ddof=1) if len(x) > 1 else np.nan}, Mínimo=x.min(), Máximo=x.max())
    ob = df[df["tipo_hoja"] == "oruro_bermejo"]
    filas = [fila("Pasajeros de Oruro por salida", df["pasajeros_oruro"]),
             fila("Pasajeros por hoja de viaje", df["pasajeros"]),
             fila("Pasajeros en hojas Oruro→Bermejo", ob["pasajeros"]),
             fila("Ocupación por hoja, según la capacidad del bus (%)", df["ocupacion"])]
    return pd.DataFrame(filas)


def normalidad(x):
    """Prueba de Shapiro-Wilk (estadistico, valor p)."""
    w, p = stats.shapiro(np.asarray(x, float))
    return float(w), float(p)


def ajustar_distribuciones(x):
    """Tabla 28: ajuste de cinco distribuciones; valor p de Kolmogorov-Smirnov y AIC.
    Los valores p son aproximados porque los parametros se estiman con los mismos datos."""
    x = np.asarray(x, float)
    candidatas = [
        ("Normal", stats.norm, {}, 2),
        ("Lognormal", stats.lognorm, {"floc": 0}, 2),
        ("Gamma", stats.gamma, {"floc": 0}, 2),
        ("Weibull", stats.weibull_min, {"floc": 0}, 2),
        ("Exponencial", stats.expon, {"floc": 0}, 1),
    ]
    filas = []
    for nombre, dist, fijos, k in candidatas:
        par = dist.fit(x, **fijos)
        ll = float(np.sum(dist.logpdf(x, *par)))
        p = float(stats.kstest(x, dist.cdf, args=par).pvalue)
        if nombre == "Normal":
            txt = f"μ = {par[0]:.2f}; σ = {par[1]:.2f}"
        elif nombre == "Lognormal":
            txt = f"μ = {np.log(par[2]):.3f}; σ = {par[0]:.3f}"
        elif nombre in ("Gamma", "Weibull"):
            txt = f"forma = {par[0]:.3f}; escala = {par[2]:.3f}"
        else:
            txt = f"media = {par[1]:.2f}"
        filas.append(dict(Distribución=nombre, Parámetros=txt, **{"Valor p (K–S)": p}, AIC=2 * k - 2 * ll,
                          _forma=par[0] if nombre in ("Gamma", "Weibull") else None,
                          _escala=par[2] if nombre in ("Gamma", "Weibull") else None))
    return pd.DataFrame(filas)


def por_dia(df):
    """Tabla 29: pasajeros de Oruro por dia de la semana."""
    g = df.groupby(["dia_num", "dia"])["pasajeros_oruro"].agg(Salidas="count", Mediana="median",
                                                               Mínimo="min", Máximo="max").reset_index()
    return g.drop(columns="dia_num").rename(columns={"dia": "Día"})


def pruebas_dia(df):
    """Kruskal-Wallis entre los siete dias y U de Mann-Whitney entre lunes-jueves y viernes-domingo."""
    grupos = [g["pasajeros_oruro"].values for _, g in df.groupby("dia_num")]
    h, p_h = stats.kruskal(*grupos)
    a = df[df["dia_num"] <= 3]["pasajeros_oruro"]
    b = df[df["dia_num"] >= 4]["pasajeros_oruro"]
    u, p_u = stats.mannwhitneyu(a, b, alternative="two-sided")
    return dict(H=float(h), p_H=float(p_h), U=float(u), p_U=float(p_u),
                mediana_lun_jue=float(a.median()), mediana_vie_dom=float(b.median()))


def comparar_tipos(df):
    """U de Mann-Whitney de la ocupacion entre hojas Oruro→Bermejo y de recorrido completo."""
    a = df[df["tipo_hoja"] == "oruro_bermejo"]["ocupacion"]
    b = df[df["tipo_hoja"] == "recorrido_completo"]["ocupacion"]
    if len(a) < 2 or len(b) < 2:
        return None
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return dict(n_oruro_bermejo=len(a), n_recorrido=len(b), mediana_oruro_bermejo=float(a.median()),
                mediana_recorrido=float(b.median()), U=float(u), p=float(p))


def escenarios_demanda(df):
    """Tabla 30: escenarios baja / habitual / alta definidos con los percentiles 25 y 75."""
    x = df["pasajeros_oruro"].astype(float)
    p25, p75 = float(np.percentile(x, 25)), float(np.percentile(x, 75))
    reglas = [("Baja", f"≤ {p25:.0f}", x <= p25), ("Habitual", f"{p25 + 1:.0f} a {p75 - 1:.0f}", (x > p25) & (x < p75)),
              ("Alta", f"≥ {p75:.0f}", x >= p75)]
    return pd.DataFrame([dict(Escenario=n, Criterio=c, Salidas=int(m.sum()), Mediana=float(x[m].median()))
                         for n, c, m in reglas]), p25, p75


def bajo_minimo(df):
    """Tabla 27: hojas por debajo del minimo (la mitad de la capacidad)."""
    minimo = df["capacidad"] / 2
    sel = df[df["pasajeros"] < minimo]
    return sel[["codigo", "fecha", "bus", "pasajeros", "capacidad"]]


def calidad_datos(df):
    """Resumen de calidad de datos: cuantos viajes OK y por revisar, por tipo de hoja."""
    t = df.pivot_table(index="tipo", columns="calidad", values="codigo", aggfunc="count", fill_value=0)
    for col in ("OK", "Revisar"):
        if col not in t.columns:
            t[col] = 0
    t["Total"] = t["OK"] + t["Revisar"]
    return t[["OK", "Revisar", "Total"]].reset_index().rename(columns={"tipo": "Tipo de hoja"})


def demoras_observadas(conn):
    return pd.read_sql_query("SELECT fecha, citacion, salida_real, demora_min, nota FROM salidas_observadas", conn)

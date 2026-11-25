# AGENTS.md - Expreso El Bermejeño Decision Support System

## Quickstart

| Command | Description |
|---|---|
| `python -m pip install -r requirements.txt` | Install deps: streamlit, pandas, numpy, scipy, matplotlib, openpyxl, pytest |
| `python -m streamlit run app.py` | Start the web app (first time: create admin user via the UI) |
| `python -m pytest -q` | Run all 100+ tests (in-memory DB with Excel data via conftest) |

## Architecture

- **Capas**: datos (db.py, importar.py, registro.py) · logica (analisis.py, simulacion.py, simulador_despacho.py, seguridad.py) · presentacion (app.py y paginas/)
- **Base de datos**: SQLite en `datos/bermejeno.db`. Todas las consultas usan `?` parametrizados (nunca concatenación de texto).
- **Parametros sinteticos calibrados** (en `simulador_despacho.py:80`): p_puntual=0.3, mu_tarde=5.0, cierre_min=15.0, cierre_max=20.0, tope=20.0
- **Regla vigente**: umbral k=5, sin tope de espera (espera_max=None)
- **Flota**: 36 asientos en todos los buses; movil 500 tiene 49 asientos (cada 15° bus de 45 hojas)

## Testing

- `conftest.py` provee `conn` (base en memoria) y `conn_datos` (carga Excel).
- Para probar contra la base real: `python -m pytest -k "test_usa_los_parametros_de_la_base"` usa la fixture `conn` con datos importados.
- **Tests clave**: `test_recomendacion.py` compara calculos exactos contra el simulador de eventos discretos.
- **Nunca** ejecutes `pytest` desde fuera de la raiz del repo; la fixture `conftest` necesita la ruta RAIZ.

## Flujo de trabajo importante

1. **Siempre**: `python -m pytest -q` pasa (100 pruebas en entorno de desarrollo)
2. Si modificas `db.py` o `simulador_despacho.py`: verifica que `test_simulador.py` y `test_recomendacion.py` sigan pasando.
3. Si modificas `recomendacion.py`: los tests `test_probabilidad_exacta_coincide_con_montecarlo` y `test_espera_esperada_coincide_con_montecarlo` validan que la formula exacta coincida con simulacion Monte Carlo.

## Convenios y quirks

- **Numeros comunes**: `simulacion.py:_correr` usa la misma semilla para todas las reglas en una misma corrida, por lo que las diferencias son puramente por la regla (no por randomness).
- **Capacidad 49**: el movil 500 tiene 49 asientos; `minimo(49) = 25` (no 24.5, hay `math.ceil`). Ve `simulador_despacho.py:27-28`.
- **Escenarios de demanda**: "todos", "baja" (<=P25), "habitual" (P25+1 a P75-1), "alta" (>=P75). Definidos en `analisis.py:129-136` y usados en `simulador_despacho.py:29-35`.
- **Parametros editables en la UI** (paginas/simulacion.py): p_puntual, mu_tarde, cierre_min, cierre_max, tope. Validados en `simulacion.py:32-38` (rangos: p_puntual [0,1], mu_tarde [0.1,60], cierre_min/max [0,60], tope [0,120]).
- **La espera maxima (tope)** en `simulador_despacho.py` y `recomendacion.py` acota la espera: pasado el tope, el modelo cierra y sale aunque no se cumpla la condicion.
- **Fórmula exacta de probabilidad** (recomendacion.py:68-75): `P(R ≤ w) = P(Binomial(a, 1 − e^(−w/μ)) ≥ r)`. Verificado contra simulacion Monte Carlo en tests.
- **Passwords**: PBKDF2-HMAC-SHA256 con 240,000 iteraciones. Minimo 8 caracteres. Roles: administrador (todo), encargada (ver, registrar, simular).
- **Importar Excel**: reglas R1-R5 en `importar.py`. Las filas con calidad "Revisar" se guardan igual pero con nota. Los códigos duplicados no se insertan.
- **Base vacía**: si borras `datos/bermejeno.db`, la próxima ejecucion la recrea automaticamente con datos iniciales.
- **Sensibilidad** (recomendacion.py:142-152): muestra cómo cambia la recomendacion si mu_tarde es 0.6x, 1.0x (base), 2.0x el valor supuesto.

## Gotchas

- `streamlit` no se reconoce: usa siempre `python -m streamlit run app.py` desde la raiz del repo.
- Error importando un módulo: ejecuta siempre desde la carpeta donde está `app.py` (no desde `pruebas/` ni subcarpetas).
- Para reiniciar la base: cierra la app y borra `datos/bermejeno.db`.
- `app.py:105` usa `os.environ.get("BERMEJENO_DB")` para sobreescribir la ruta de la base.
- `test_app_humo.py` y `test_paginas_humo.py` son pruebas de humo que importan las paginas streamlit sin abrir el navegador.
- `Figura_ocupacion_por_tipo_de_hoja.png` y `Figura_sensibilidad_tornado.png` son graficos generados previamente (no outputs de tests).
- `graficos_capitulos.py` contiene codigos de generacion de graficos para los capitulos del documento academico.
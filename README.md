# Sistema de apoyo a la toma de decisiones · Expreso El Bermejeño S.R.L.

Prototipo académico para la sucursal Oruro: registra las salidas Oruro–Tarija–Bermejo, analiza la demanda y la
ocupación, compara reglas de despacho (cuánto esperar antes de salir) mediante simulación de eventos discretos y
**recomienda en vivo si conviene esperar o salir** (página *Decisión del día*).

> Los parámetros de puntualidad, retraso, cierre y espera máxima son **sintéticos** (supuestos, no observados).
> Los resultados de la simulación describen el **modelo**; no demuestran una mejora real en la empresa.

## Ejecutar

En la terminal de VS Code, dentro de esta carpeta:

```
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

La primera vez, la página pide crear el **administrador** (contraseña de al menos 8 caracteres).
Luego: menú **Datos → Importar Excel** y cargar `datos/datos_pasajeros_simulacion.xlsx`.

## Pruebas

```
python -m pytest -q
```

Deben pasar todas (100 en el entorno de desarrollo).

## Estructura (arquitectura por capas)

| Archivo | Capa | Función |
|---|---|---|
| `db.py` | Datos | Esquema SQLite, parámetros iniciales, consultas parametrizadas |
| `importar.py` | Datos | Importación y depuración del Excel (reglas R1 a R5) |
| `registro.py` | Datos | Registro de salidas nuevas y estimaciones con datos reales |
| `analisis.py` | Lógica | Tablas 26 a 30: descriptiva, ajuste de distribuciones, pruebas |
| `simulador_despacho.py` | Lógica | Simulador de eventos discretos (Capítulo V) |
| `recomendacion.py` | Lógica | Recomendación en vivo: probabilidad exacta de que se cumpla la condición de salida |
| `simulacion.py` | Lógica | Comparación de reglas con números comunes, IC, sensibilidad, historial |
| `seguridad.py` | Lógica | Hash PBKDF2, roles y permisos |
| `app.py`, `paginas/` | Presentación | Dashboard Streamlit |
| `pruebas/` | Calidad | 100 pruebas pytest |
| `docs/` | Documentación | Diagramas, diccionario de datos, matriz de validación, guía de capturas |

## Roles

| Rol | Puede |
|---|---|
| Administrador | Todo: importar, registrar, simular, parámetros, usuarios, bitácora |
| Encargada | Ver, registrar salidas y simular |

## Solución de problemas

- `streamlit` no se reconoce: use `python -m streamlit run app.py`.
- Error al importar un módulo: ejecute siempre desde esta carpeta (donde está `app.py`).
- Para reiniciar la base, cierre la app y borre `datos/bermejeno.db`.

## Decisión del día (recomendación en vivo)

La encargada ingresa cuántos pasajeros hay a bordo desde La Paz, cuántos pasajes se vendieron en Oruro, cuántos ya
llegaron y cuántos minutos pasaron desde la citación. El sistema responde:

- si la condición de la regla vigente ya se cumple;
- si no, la probabilidad de que se cumpla antes de la espera máxima y la espera mediana;
- los pasajeros-minuto de espera esperados (costo de esperar sin estimar dinero);
- qué pasaría con otro umbral k y qué tan sensible es la respuesta al retraso medio de los ausentes.

**Cómo se calcula (para la defensa).** Un ausente en el minuto t llega con un retraso adicional exponencial (propiedad
de falta de memoria, la misma distribución del simulador). Si faltan `r` llegadas de `a` ausentes, el tiempo hasta
cumplir la condición es el r-ésimo estadístico de orden de `a` exponenciales:
`P(R ≤ w) = P(Binomial(a, 1 − e^(−w/μ)) ≥ r)`. Es un cálculo exacto, no una nueva simulación, y se verifica contra
el simulador de eventos discretos en `pruebas/test_recomendacion.py`.

**Límite.** Depende del retraso medio de los ausentes, que es un parámetro sintético; por eso el sistema muestra la
sensibilidad a ese valor. La decisión es de la encargada y la ATT.

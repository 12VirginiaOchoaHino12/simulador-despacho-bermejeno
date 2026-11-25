# Guía de capturas de pantalla (Capítulo VI)

Ejecute `python -m streamlit run app.py`, cree el administrador, importe el Excel y tome estas capturas
(recorte solo el área útil; el texto del gráfico debe verse en 8 pt o más). Cada figura lleva número, título en
cursiva y nota debajo, según APA 7.

| N.º sugerido | Pantalla | Qué mostrar |
|---|---|---|
| 1 | Inicio de sesión | Formulario de ingreso |
| 2 | Resumen | Indicadores y gráfico de ocupación por mes |
| 2b | Decisión del día | Ejemplo: a bordo 8, vendidos 24, presentes 14, 5 minutos; muestre el mensaje, la curva y la tabla de umbrales k |
| 3 | Datos · Viajes | Tabla con el filtro Calidad = Revisar |
| 4 | Datos · Registrar salida | Formulario lleno y el mensaje de éxito |
| 5 | Datos · Calidad de datos | Resumen OK / Revisar y hojas bajo el mínimo |
| 6 | Datos · Importar Excel | Resultado de la importación (45 importados) |
| 7 | Demanda · Descriptiva | Tabla de estadística descriptiva |
| 8 | Demanda · Ocupación por tipo de hoja | Gráfico de cajas |
| 9 | Demanda · Distribución | Tabla de ajuste e histograma con Weibull y Gamma |
| 10 | Demanda · Día y escenarios | Tabla por día y escenarios de demanda |
| 11 | Simulación · Regla vigente | Parámetros, advertencia de datos sintéticos e indicadores |
| 12 | Simulación · Comparar reglas | Tabla comparativa, gráfico y explicación automática |
| 13 | Simulación · Sensibilidad | Gráfico de tornado |
| 14 | Historial | Corridas guardadas y detalle |
| 15 | Administración | Parámetros con su categoría y usuarios |
| 16 | Terminal | Resultado de `python -m pytest -q` (100 pruebas) |

Para la comparación (captura 12) deje los parámetros por defecto, 1 000 réplicas y semilla 1000, y escriba una
etiqueta como "Demostración". En el documento presente esa corrida solo como demostración de la funcionalidad:
la evaluación de las reglas y la prueba de la hipótesis son de la cuarta entrega.

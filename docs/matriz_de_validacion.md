# Matriz de validación funcional (borrador)

Cada requisito se verifica con pruebas automáticas (`python -m pytest -q`). Los identificadores RF y RNF son
provisionales: deben alinearse con los del Anexo D del documento antes de la entrega.

Resultado en el entorno de desarrollo (Python 3.13): **100 pruebas aprobadas, 0 fallidas**. Vuelva a ejecutarlas en su
equipo y anote ahí su resultado y la fecha.

| ID | Requisito | Prueba(s) que lo verifican | Resultado |
|---|---|---|---|
| RF-01 | Importar los registros históricos desde Excel con depuración y sin duplicar | `test_datos.py`: reproduce_cifras_del_documento, importacion_repetida_no_duplica, rechaza_filas_invalidas, sin_hoja_pasajeros | Aprobada |
| RF-02 | Registrar una salida nueva con validación de entradas | `test_registro.py`: registrar_salida_valida, validaciones_de_entrada, calcular_demora; `test_paginas_humo.py`: registrar_salida_desde_la_pagina_de_datos | Aprobada |
| RF-03 | Calcular indicadores de demanda y ocupación | `test_analisis.py`: resumen_general, tabla_26_descriptiva, ocupacion_oruro_bermejo | Aprobada |
| RF-04 | Ajustar distribuciones y aplicar pruebas estadísticas | `test_analisis.py`: shapiro_wilk, tabla_28_ajuste_de_distribuciones, tabla_29_dia_de_la_semana | Aprobada |
| RF-05 | Definir escenarios de demanda con los percentiles de los registros | `test_analisis.py`: tabla_30_escenarios | Aprobada |
| RF-06 | Simular la regla de despacho vigente con parámetros editables | `test_simulador.py` (9 pruebas de verificación); `test_simulacion.py`: parametros_desde_la_base, parametros_invalidos_se_rechazan; `test_paginas_humo.py`: simulacion_con_botones_pulsados | Aprobada |
| RF-07 | Comparar reglas con números aleatorios comunes e intervalos de confianza | `test_simulacion.py`: regla_de_referencia_tiene_diferencia_cero, umbral_mayor_reduce…, intervalo_de_confianza…, numeros_aleatorios_son_comunes | Aprobada |
| RF-08 | Analizar la sensibilidad a los parámetros sintéticos | `test_simulacion.py`: sensibilidad_ordena_por_rango…, sensibilidad_rechaza_parametro_desconocido | Aprobada |
| RF-09 | Explicar automáticamente los resultados advirtiendo su carácter sintético | `test_simulacion.py`: la_explicacion_siempre_advierte_que_es_sintetico | Aprobada |
| RF-10 | Guardar y consultar el historial de corridas | `test_simulacion.py`: guardar_y_leer_historial | Aprobada |
| RF-11 | Rotular el origen de cada dato y parámetro | `test_datos.py`: parametros_iniciales_con_categoria, restricciones_de_integridad | Aprobada |
| RF-12 | Mostrar el dashboard con sus siete páginas | `test_paginas_humo.py`: pagina_se_ejecuta_sin_errores (7 páginas); `test_app_humo.py` | Aprobada (con Streamlit simulado); falta la revisión visual en el navegador |
| RF-13 | Recomendar en vivo si esperar o salir, con la probabilidad de que se cumpla la condición, la espera mediana, los pasajeros-minuto, alternativas de umbral k y sensibilidad al retraso medio | `test_recomendacion.py` (16 pruebas, entre ellas: coincide_con_el_simulador_de_eventos_discretos, probabilidad_exacta_coincide_con_montecarlo, estado_cumplida_tope_y_esperar, minimo_imposible_se_avisa, mas_umbral_menos_espera, guardar_y_listar_consultas); `test_paginas_humo.py`: decision_del_dia_evalua_y_guarda_la_consulta, decision_del_dia_rechaza_datos_incoherentes | Aprobada |
| RNF-01 | Guardar las contraseñas con hash y sal | `test_seguridad.py`: la_clave_no_se_guarda_en_texto_plano, misma_clave_distinta_sal_distinto_hash | Aprobada |
| RNF-02 | Control de acceso por roles | `test_seguridad.py`: permisos_por_rol; `test_app_humo.py`: menu_segun_rol; `test_paginas_humo.py`: pagina_administracion_rechaza_a_la_encargada | Aprobada |
| RNF-03 | Resistir inyección SQL | `test_seguridad.py`: inyeccion_sql_en_el_login_no_funciona | Aprobada |
| RNF-04 | Integridad de los datos | `test_datos.py`: restricciones_de_integridad | Aprobada |
| RNF-05 | Reproducibilidad de la simulación | `test_simulador.py` (pruebas 5 y 6); `test_simulacion.py`: misma_semilla_mismos_resultados | Aprobada |
| RNF-06 | Trazabilidad de las acciones (bitácora) | `test_app_humo.py`: login_incorrecto_cuenta_intentos… (verifica el registro en la bitácora) | Aprobada |
| RNF-07 | Rendimiento: comparar 6 reglas con 1 000 réplicas en pocos segundos | `test_simulacion.py`: rendimiento_seis_reglas… | Aprobada |
| RNF-08 | Usabilidad: la encargada puede registrar una salida sin ayuda | Prueba manual con la encargada | Pendiente (no se ha hecho) |

Limitación: las pruebas de las páginas usan un Streamlit simulado y comprueban que el código se ejecuta sin errores;
no verifican el aspecto visual, que debe revisarse en el navegador.

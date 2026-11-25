# Diccionario de datos

Categoría de origen de cada dato: **observado**, **histórico** (registros de la empresa), **por obtener**,
**sintético** (supuesto) o **configurado** (dato dado por la empresa).

## viajes (45 hojas históricas importadas)
| Campo | Tipo | Descripción |
|---|---|---|
| id | entero, PK | Identificador interno |
| codigo | texto, único | Número de viaje de la hoja (por ejemplo 667/26) |
| fecha | texto AAAA-MM-DD | Fecha de la hoja |
| ruta | texto | Ruta rotulada en la hoja |
| tipo_hoja | texto | `oruro_bermejo` o `recorrido_completo` |
| bus | entero, FK buses | Número de bus (nulo si la hoja no lo trae) |
| hora_impresa | texto HH:MM | Hora impresa en la hoja; su significado está por confirmar |
| pasajeros | entero ≥ 0 | Pasajes vendidos en la hoja |
| monto_bs | real | Monto en bolivianos |
| pasajeros_oruro | entero ≥ 0 | Pasajes de Oruro (origen Oruro o vendidos por la Suc 6) |
| capacidad | entero > 0 | Asientos del bus (36; 49 en el móvil 500) |
| calidad | texto | `OK` o `Revisar` |
| nota | texto | Observación sobre la calidad del dato |
| categoria | texto | Origen del dato (histórico) |

Restricción: `pasajeros_oruro` no puede superar `pasajeros`.

## buses
| Campo | Tipo | Descripción |
|---|---|---|
| numero | entero, PK | Número del bus |
| capacidad | entero > 0 | Asientos |
| fuente | texto | Quién confirmó la capacidad |

## registros_salida (datos nuevos que carga la sucursal)
| Campo | Tipo | Descripción |
|---|---|---|
| id | entero, PK | Identificador |
| fecha | texto | Fecha de la salida |
| bus | entero, FK buses | Bus que salió |
| capacidad | entero | Asientos del bus |
| pasajeros_pasaje | entero | Pasajeros con pasaje |
| ausentes | entero | Ausentes a la hora de citación |
| llegaron_tarde | entero | De los ausentes, cuántos llegaron después |
| hora_citacion | texto | Por defecto 17:00 |
| hora_salida_real | texto | Hora en que salió el bus |
| demora_min | real | Salida menos citación, en minutos (calculada) |
| observaciones | texto | Comentario libre |
| usuario_id | entero, FK usuarios | Quién registró |
| creado | texto | Fecha y hora del registro |

## salidas_observadas
Tres salidas de la observación exploratoria (20 al 23 de octubre de 2026): `salida_real`, `demora_min`, `categoria` (observado), `nota`.

## parametros
| Campo | Descripción |
|---|---|
| clave | Nombre del parámetro (PK) |
| valor | Valor numérico |
| categoria | observado, histórico, por obtener, sintético o configurado |
| fuente | De dónde sale el valor |
| descripcion | Qué significa |

## corridas y resultados_regla (historial de simulación)
`corridas`: escenario, capacidad, réplicas, semilla, parámetros usados (JSON), usuario y fecha.
`resultados_regla`: por regla, umbral k, espera máxima T, demora media y mediana, ocupación media, % que esperó,
% sin mínimo, diferencia de demora con su intervalo de confianza de 95 % y diferencia de ocupación respecto de la regla vigente.

## consultas_decision (recomendación en vivo)
Cada consulta de la página *Decisión del día*: `capacidad`, `a_bordo`, `vendidos_oruro`, `presentes`, `minutos`
(desde la citación), `umbral_k`, `estado` (cumplida, esperar o tope), `prob_antes_del_tope`, `espera_mediana`,
`decision_tomada` (espero o salio; opcional), `observaciones`, `usuario_id` y `creado`. Con el tiempo, la decisión
realmente tomada permite contrastar la recomendación del modelo con la práctica.

## usuarios
`usuario` (único), `rol` (administrador o encargada), `sal` y `hash` (PBKDF2-HMAC-SHA256, 240 000 iteraciones), `activo`.

## bitacora
Registro de acciones: `fecha`, `usuario`, `accion` (login, login_fallido, importar_excel, registrar_salida, comparar_reglas, modificar_parametro, crear_usuario…) y `detalle`.

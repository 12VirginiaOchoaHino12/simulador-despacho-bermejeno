import numpy as np
import simulador_despacho as s

r = s.correr_mezcla(s.VIGENTE, nrep=1000)      # 1 000 días simulados, regla vigente
demora = np.array([x['demora'] for x in r])
print("Mediana:", round(np.median(demora), 1), "min")   # da 20,9 (Tabla 39)

alt = s.Regla("Espera máxima 15", 5, 15.0)      # regla alternativa: umbral 5, tope de 15 min
r2 = s.correr_mezcla(alt, nrep=1000)
print(np.median([x['demora'] for x in r2]))
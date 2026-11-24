"""Gráficos de los capítulos IV y V (Python 3 + pandas/openpyxl + Matplotlib).
Uso:  python graficos_capitulos.py datos_pasajeros_simulacion.xlsx
Genera: Figura_ocupacion_por_tipo_de_hoja.png y Figura_sensibilidad_tornado.png"""
import sys, openpyxl, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': ['Arial', 'Liberation Sans', 'DejaVu Sans'], 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False})
AZ, NA, GR = '#1F4E79', '#D97B00', '#444444'
arch = sys.argv[1] if len(sys.argv) > 1 else 'datos_pasajeros_simulacion.xlsx'
wb = openpyxl.load_workbook(arch, data_only=True)
F = [r for r in wb['Pasajeros'].iter_rows(min_row=5, values_only=True) if r[0] and r[1] and r[0] != 'Total / promedio']
# ---------- 1) Ocupación por tipo de hoja (Cap. IV)
grupos = {'Oruro→Bermejo': [], 'Recorrido completo': []}
for r in F:
    ruta, cap, oc = str(r[3]), r[10], r[11]
    if oc is None: continue
    grupos['Oruro→Bermejo' if ruta.startswith('Oruro') else 'Recorrido completo'].append((100 * oc, cap))
rng = np.random.default_rng(2026)
fig, ax = plt.subplots(figsize=(6.2, 3.8), dpi=200)
for i, (k, v) in enumerate(grupos.items()):
    y = np.array([a for a, _ in v]); c = np.array([b for _, b in v])
    ax.boxplot(y, positions=[i], widths=0.45, showfliers=False, medianprops=dict(color=GR, lw=2),
               boxprops=dict(color=GR), whiskerprops=dict(color=GR), capprops=dict(color=GR))
    x = i + rng.uniform(-0.12, 0.12, len(y)); m49 = c >= 49
    ax.scatter(x[~m49], y[~m49], s=24, color=AZ, alpha=.85, zorder=3, label='36 asientos' if i == 0 else None)
    if m49.any(): ax.scatter(x[m49], y[m49], s=40, marker='D', color=NA, zorder=4, label='49 asientos')
ax.axhline(50, color='#888', ls='--', lw=1); ax.text(1.45, 51, 'Mínimo (50 %)', fontsize=8, ha='right', color='#555')
ax.set_xticks([0, 1]); ax.set_xticklabels([f'{k}\n(n = {len(v)})' for k, v in grupos.items()])
ax.set_ylabel('Ocupación real (%)'); ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=9, loc='lower right')
fig.tight_layout(); fig.savefig('Figura_ocupacion_por_tipo_de_hoja.png'); plt.close(fig)
# ---------- 2) Tornado de sensibilidad (Cap. V, Tabla 39): mediana de demora en min, base 20,9
base = 20.9
S = [('Retraso medio de los ausentes (3 → 10 min)', 19.7, 24.3),
     ('Cierre de venta (12–17 → 18–23 min)', 17.9, 23.9),
     ('Puntualidad (0,2 → 0,4)', 21.6, 20.3),
     ('Tope de espera (15 → 30 min)', 20.9, 20.9)]
S.sort(key=lambda t: abs(t[2] - t[1]))
fig, ax = plt.subplots(figsize=(6.6, 3.4), dpi=200)
for i, (n, a, b) in enumerate(S):
    # azul = valor bajo del parámetro (a); naranja = valor alto (b)
    ax.barh(i, a - base, left=base, color='#7FA6D0', height=.55, label='Valor bajo del parámetro' if i == 0 else None)
    ax.barh(i, b - base, left=base, color='#E8A760', height=.55, label='Valor alto del parámetro' if i == 0 else None)
    for v in (a, b):
        ax.text(v + (.15 if v >= base else -.15), i, f'{v:.1f}'.replace('.', ','), ha='left' if v >= base else 'right', va='center', fontsize=8)
ax.axvline(base, color=GR, lw=1.5); ax.set_yticks(range(len(S))); ax.set_yticklabels([s[0] for s in S], fontsize=9)
ax.set_xlabel('Mediana de la demora de salida (min); línea = base 20,9'); ax.set_xlim(16.5, 26); ax.legend(frameon=False, fontsize=8, loc='lower right')
fig.tight_layout(); fig.savefig('Figura_sensibilidad_tornado.png'); plt.close(fig)
print({k: len(v) for k, v in grupos.items()})

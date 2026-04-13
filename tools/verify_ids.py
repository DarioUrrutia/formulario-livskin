"""Verifica que todos los getElementById en JS tengan su id= correspondiente en HTML."""
import re

with open('templates/formulario.html', 'r', encoding='utf-8') as f:
    html = f.read()

# IDs usados en JS
js_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", html))

# IDs definidos en HTML
html_ids = set(re.findall(r"id=['\"]([^'\" ]+)['\"]", html))

# IDs en JS que no existen en HTML (excluir dinámicos)
missing = js_ids - html_ids
missing_real = [m for m in sorted(missing) if not any(c in m for c in ['+', '{', 'idx'])]

if missing_real:
    print("IDs en JS sin elemento HTML:")
    for m in missing_real:
        print(f"  FALTA: {m}")
else:
    print("OK: todos los getElementById tienen su id= en el HTML")

# Dashboard IDs específicos
print("\nDashboard IDs:")
dash_ids = [
    'kpi-ventas', 'kpi-cobrado', 'kpi-pendiente', 'kpi-ticket', 'kpi-tasa', 'kpi-balance',
    'kpi-atenciones', 'kpi-clientes', 'kpi-gastos',
    'kpi-pagos-total', 'kpi-pagos-count',
    'kpi-pago-ef', 'kpi-pago-yp', 'kpi-pago-pl', 'kpi-pago-gi',
    'tabla-recientes', 'tabla-top20', 'tabla-deudores-aging',
    'tabla-pendientes-pago', 'tabla-pagos-recientes',
    'tabla-tipo-mes',
    'dash-contenido', 'dash-loading',
]
for did in dash_ids:
    in_html = did in html_ids
    status = "OK" if in_html else "MISSING"
    print(f"  {did}: {status}")

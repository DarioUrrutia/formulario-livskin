# Formulario Livskin

Sistema de gestión interno para **Livskin Professional Skincare** — registro de clientes, ventas, cobros y análisis de negocio, accesible desde cualquier celular o computadora.

🔗 **https://formulario-livskin.onrender.com**

---

## ¿Qué puede hacer el sistema?

### Pestaña Venta
- Registro completo de atenciones: cliente, fecha, tipo, categoría, zona/cantidad/envase, próxima cita
- Múltiples ítems por venta en una sola sesión
- Conversión automática de monedas (USD/EUR → Soles) usando tipo de cambio en tiempo real
- Métodos de pago: Efectivo, Yape, Plin, Giro — con distribución individual por ítem
- **Distribución automática de pago**: todos los ítems se rellenan en orden al ingresar el pago; siempre editables manualmente
- **Alerta de deuda anterior**: si el cliente tiene saldo pendiente, aparece un aviso al buscarlo y se muestra una sección para abonar a esas deudas dentro del mismo registro
- **Promociones y descuentos por ítem**: opción `Gratis` o `Descuento S/` directamente en cada ítem
  - **Gratis**: el campo de precio sigue visible como referencia, pero TOTAL = 0; no entra en facturado ni por cobrar; la distribución de pago ignora ese ítem; cualquier pago recibido queda como saldo a favor o cubre deudas anteriores
  - **Descuento**: precio cobrado = lista − descuento; se registra el monto cedido en `DESCUENTO S/`
  - Validación doble (frontend + backend) para garantizar integridad
- **Tipos, categorías y áreas dinámicos**: configurables desde la hoja "Listas" de Google Sheets sin tocar código; la hoja se crea automáticamente con valores por defecto al primer uso
- Códigos únicos automáticos: `LIVCLIENT####`, `LIVTRAT####`, `LIVPROD####`
- Protección contra doble registro (botón se deshabilita al enviar)

### Pestaña Gasto
- Registro de gastos del negocio: tipo, descripción, destinatario, monto y método de pago

### Pestaña Cobro
- Registro de cobros independientes sobre ítems con saldo pendiente
- Búsqueda de cliente y listado de ítems con deuda activa
- Asignación de monto por ítem con código único `LIVCOBRO####`
- Métodos de pago: Efectivo, Yape, Plin, Giro

### Pestaña Cliente
- Búsqueda de cliente por nombre
- Historial en dos vistas:
  - **Por ítem**: cada servicio vendido con sus cobros asociados, estado (Pagado / Debe), fecha y zona
  - **Cronológico**: agrupado por día con ventas y cobros del día, totales al pie
- Saldo a favor (crédito) mostrado cuando el cobrado supera lo facturado
- Cálculo real de deuda por ítem (basado en cobros vinculados, no en el dato original)

### Pestaña Dashboard

#### Sub-panel General
- KPIs financieros del período: Total Facturado, Total Cobrado, Por Cobrar, Ticket Promedio, Tasa de Cobro, Balance Neto
- **Comparativas siempre actualizadas**: Mes actual vs mes anterior (monto + % ▲▼) y Año actual vs año anterior
- Gráfico de evolución mensual: barras apiladas Cobrado / Pendiente
- **Tabla por tipo** (Tratamientos / Productos): mes actual vs mes anterior con variación porcentual
- Gráfico de top categorías del mes actual
- KPIs operativos: N° Atenciones, Clientes Únicos, Ítems con descuento, Tratamientos, Productos, Gastos
- **Descuentos Otorgados**: tarjeta que aparece solo cuando hay promociones en el período, muestra el costo total asumido por la empresa
- Mix de ventas (donut: Tratamientos / Productos / Otros)
- Tabla de atenciones recientes

#### Sub-panel Clientes
- **Top 20% de clientes** del período (Pareto): facturado, visitas, frecuencia por mes, categoría que más compra
- Columna de evolución: compara mes actual vs mes anterior con flecha ▲▼ por cliente
- Gráfico de barras top clientes
- Gráfico top categorías del período
- **Deudores por antigüedad** (calculado al día de hoy):
  - Menos de 1 mes
  - 1 a 2 meses
  - 2 a 3 meses
  - Más de 3 meses
  - Cada bucket muestra: cliente, categoría, monto que debe, fecha de venta y días transcurridos

#### Sub-panel Cobros
- Total cobrado y N° de cobros del período
- Desglose por método: Efectivo, Yape, Plin, Giro (con gráfico donut)
- Tabla de cobros recientes
- **Pendientes de cobro por antigüedad**: misma clasificación de buckets que deudores, con detalle por ítem

---

## Tecnologías

| Componente | Tecnología | Versión |
|---|---|---|
| Backend | Python + Flask | 3.13.13 / Flask 3.1.3 |
| Base de datos | Google Sheets vía gspread | gspread 6.2.1 |
| Auth Google | Service Account | google-auth 2.49.1 |
| Servidor producción | gunicorn (config en `gunicorn.conf.py`) | 25.3.0 |
| Hosting | Render (plan gratuito) | — |
| Frontend | HTML / CSS / JavaScript vanilla | — |
| Gráficos | Chart.js | — |
| Tipo de cambio | @fawazahmed0/currency-api | — |
| Keep-alive | cron-job.org (ping cada 14 min) | — |

> Todas las dependencias de Python están **pinneadas con `==`** en [requirements.txt](requirements.txt) y la versión exacta de Python en [.python-version](.python-version). Esto garantiza que cualquier instalación futura (Render, otra PC, dentro de 3 años) reproduzca exactamente el mismo entorno.

## Estructura del proyecto

```
formulario-livskin/
├── app.py                       # Servidor Flask: rutas, lógica de negocio, API dashboard, cache
├── gunicorn.conf.py             # Config de gunicorn para producción (workers, timeout, max_requests)
├── requirements.txt             # Dependencias Python pinneadas con ==
├── .python-version              # Versión exacta de Python (Render la respeta)
├── render.yaml                  # Configuración Render
├── .env.example                 # Template de variables de entorno
├── .gitignore
├── CLAUDE.md                    # Reglas operativas para Claude Code (R1-R7)
├── README.md                    # Este archivo
├── templates/
│   └── formulario.html          # UI completa: formularios, historial, dashboard
├── static/
│   └── logo.png
├── tools/                       # Scripts utilitarios
│   ├── importar_csv.py          # Migración one-shot de datos históricos (Inventario VF.csv)
│   ├── migrar_datos.py          # Migración legacy (asignación de COD_CLIENTE/COD_ITEM)
│   ├── sync_claude_plans.py     # Sincroniza planes de Claude Code al folder
│   ├── backup_claude_state.py   # Backup de sesiones/memoria/planes para portabilidad
│   └── restore_claude_state.py  # Restaurar estado de Claude en otra PC
└── docs/
    ├── plans/
    │   └── PLAN_MANTENIMIENTO_3_ANOS.md   # Plan a 2 años con migración Año 1 → Año 2
    └── runbooks/                # Procedimientos de emergencia (vacío, agregar según necesidad)
```

## Hojas de Google Sheets

| Hoja | Columnas principales |
|---|---|
| Ventas | #, FECHA, COD_CLIENTE, CLIENTE, TELEFONO, TIPO, COD_ITEM, CATEGORIA, ZONA, PROXIMA CITA, FECHA_NAC, MONEDA, TOTAL S/ (PEN), EFECTIVO, YAPE, PLIN, GIRO, DEBE, PAGADO, TC, PRECIO LISTA S/, DESCUENTO S/ |
| Cobros | #, FECHA, COD_CLIENTE, CLIENTE, MONTO, EFECTIVO, YAPE, PLIN, GIRO, NOTAS, COD_ITEM, CATEGORIA, COD_COBRO |
| Clientes | COD_CLIENTE, NOMBRE, TELEFONO, FECHA_NAC, FECHA_REGISTRO, EMAIL |
| Gastos | #, FECHA, TIPO, DESCRIPCION, DESTINATARIO, MONTO, METODO DE PAGO |
| Listas | LISTA, VALOR — configura tipos (`tipo`), categorías (`cat_Tipo`), áreas (`area`), precios de lista (`precio_Categoría`) |

## Setup en una PC nueva (desde cero)

> Sigue estos pasos en orden. Si todos pasan, la app va a levantar idéntica a producción.

### 1. Instalar Python 3.13.13

- **Windows:** descargar desde https://www.python.org/downloads/release/python-31313/ → ejecutar el instalador y **marcar "Add python.exe to PATH"** y **"Use admin privileges when installing py.exe"** antes de "Install Now".
- **Mac:** `brew install python@3.13`
- **Linux:** usar pyenv → `pyenv install 3.13.13 && pyenv local 3.13.13`

Verificar que se instaló:
```bash
py -3.13 --version          # Windows
python3.13 --version        # Mac/Linux
# debe imprimir: Python 3.13.13
```

> **¿Por qué exactamente 3.13?** Es la versión "sweet spot": en bugfix activo hasta oct 2027 + security hasta oct 2029, suficientemente madura (18+ meses en producción) para no tener sorpresas, soportada por Render como default. Python 3.12 entró en modo "security only" sin instaladores binarios y 3.14 todavía es muy nueva para producción.

### 2. Clonar el repo

```bash
git clone https://github.com/DarioUrrutia/formulario-livskin.git
cd formulario-livskin
```

### 3. Crear el entorno virtual e instalar dependencias

**Windows (Git Bash o PowerShell):**
```bash
py -3.13 -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Esto instala las **25 dependencias pinneadas** del proyecto. Si todo termina sin errores, el entorno está listo.

Verificar que no haya conflictos:
```bash
pip check
# debe imprimir: No broken requirements found.
```

### 4. Configurar variables de entorno y credenciales

```bash
cp .env.example .env
```

Editar `.env` y rellenar los valores reales. Las variables son:

| Variable | De dónde sale |
|---|---|
| `GOOGLE_CREDENTIALS` | Contenido del JSON de service account de Google Cloud (`livskin-formulario`). Está guardado en tu **gestor de contraseñas** o en un backup seguro. Pegalo en una sola línea. |
| `FLASK_SECRET_KEY` | Generar con `py -c "import secrets; print(secrets.token_hex(32))"`. **Distinto** en local y en producción. |
| `LIVSKIN_SHEET_ID` | Ya viene rellenado por defecto en `.env.example`. Solo cambiar si migrás a otra Sheet. |

> **Alternativa de dev local:** en lugar de pegar `GOOGLE_CREDENTIALS` en `.env`, podés copiar el archivo `livskin-formulario-XXXXXX.json` directamente a la raíz del proyecto. La app lo lee automáticamente. **NUNCA** commitees ese archivo (`.gitignore` lo bloquea).

### 5. Levantar la app local

**Modo desarrollo (Flask dev server, recarga automática):**
```bash
py app.py
```

**Modo producción (mismo servidor que usa Render):**
```bash
gunicorn app:app --config gunicorn.conf.py
```

Abrir http://localhost:5000 — debería cargar el formulario.

### 6. Verificar que todo funciona

- Tab **Dashboard** → si carga sin error, la conexión a Google Sheets está OK.
- Tab **Venta** → escribir un nombre cualquiera en "Cliente"; debería autocompletar de los clientes reales.
- Tab **Venta** → seleccionar "Tipo"; los dropdowns deberían poblarse desde la hoja `Listas` de Google Sheets.

---

## Cómo actualizar dependencias de Python

**Regla de oro:** nunca actualizar todo de golpe con `pip install -U -r requirements.txt`. Es la receta para romper la app sin entender por qué.

**Procedimiento correcto** (ver también [CLAUDE.md](CLAUDE.md) regla R1):

1. Crear branch: `git checkout -b deps/update-2026-XX`
2. Actualizar UNA dependencia a la vez:
   ```bash
   pip install -U Flask
   pip freeze | grep -i flask  # ver la nueva versión
   ```
3. Editar `requirements.txt` y cambiar **solo esa línea** con la nueva versión.
4. Probar localmente: las 5 tabs sin errores en consola, flujo completo Venta + Cobro + Dashboard.
5. Si todo OK, commit y push. Render redespliega.
6. Verificar producción durante 24h antes de actualizar la siguiente.

**Auditoría de seguridad** (correr trimestralmente):
```bash
pip install pip-audit
pip-audit -r requirements.txt
```

---

## Mantenimiento y plan a 3 años

El plan completo de mantenimiento, runbooks de emergencia, y la migración Año 1 → Año 2 (a infraestructura más robusta con techo de $120/año) está en:

📄 **[docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md](docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md)**

Incluye:
- Riesgos identificados y priorizados (R1-R14)
- Tareas recurrentes (diarias / semanales / mensuales / trimestrales / anuales)
- Roadmap P0/P1/P2/P3
- Plan de transición Año 2 (Postgres + sync invertido a Sheets como espejo)
- Runbooks de disaster recovery, rotación de credenciales, app caída
- Estimación de costos

**Léelo antes de hacer cambios estructurales o migraciones grandes.**

## Notas técnicas

- Caché en memoria por proceso gunicorn con TTL de 90 segundos — lecturas de Sheets son rápidas después de la primera
- El caché se invalida automáticamente después de cada escritura (venta, cobro, gasto)
- Endpoint `/ping` para keep-alive con cron externo, evita cold start de 30-60s en Render free tier
- Validación doble en ítems gratis: frontend zeriza `total_item` y respeta el flag en `getItemsData` y `actualizarPrecioItem`; backend fuerza TOTAL = 0 con el flag `es_gratis` + verificación `descuento >= precio_lista`

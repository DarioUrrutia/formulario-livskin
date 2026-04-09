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
- **Promociones y descuentos por ítem**: opción `Gratis` (TOTAL = 0, no entra en facturado ni por cobrar) o `Descuento S/` (precio cobrado = lista − descuento); el monto cedido queda registrado en `DESCUENTO S/` para análisis de costo de promociones
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

| Componente | Tecnología |
|---|---|
| Backend | Python 3 + Flask |
| Base de datos | Google Sheets vía gspread |
| Hosting | Render (plan gratuito) |
| Frontend | HTML / CSS / JavaScript vanilla |
| Gráficos | Chart.js |
| Tipo de cambio | @fawazahmed0/currency-api |
| Keep-alive | cron-job.org (ping cada 14 min) |

## Estructura del proyecto

```
ProyectosClaude/
├── app.py                  # Servidor Flask: rutas, lógica de negocio, API dashboard
├── requirements.txt        # Dependencias Python
├── render.yaml             # Configuración Render (gunicorn --timeout 120 --workers 2)
├── templates/
│   └── formulario.html     # UI completa: formularios, historial, dashboard
└── static/
    └── logo.png
```

## Hojas de Google Sheets

| Hoja | Columnas principales |
|---|---|
| Ventas | #, FECHA, COD_CLIENTE, CLIENTE, TELEFONO, TIPO, COD_ITEM, CATEGORIA, ZONA, PROXIMA CITA, FECHA_NAC, MONEDA, TOTAL S/ (PEN), EFECTIVO, YAPE, PLIN, GIRO, DEBE, PAGADO, TC, PRECIO LISTA S/, DESCUENTO S/ |
| Cobros | #, FECHA, COD_CLIENTE, CLIENTE, MONTO, EFECTIVO, YAPE, PLIN, GIRO, NOTAS, COD_ITEM, CATEGORIA, COD_COBRO |
| Clientes | COD_CLIENTE, NOMBRE, TELEFONO, FECHA_NAC, FECHA_REGISTRO, EMAIL |
| Gastos | #, FECHA, TIPO, DESCRIPCION, DESTINATARIO, MONTO, METODO DE PAGO |
| Listas | LISTA, VALOR — configura tipos (`tipo`), categorías (`cat_Tipo`), áreas (`area`), precios de lista (`precio_Categoría`) |

## Desarrollo local

```bash
pip install -r requirements.txt
py app.py
```

Requiere el archivo de credenciales de Google (`livskin-formulario-xxxx.json`) en la raíz del proyecto (nunca se sube a GitHub).

## Notas técnicas

- Caché en memoria por proceso gunicorn con TTL de 90 segundos — lecturas de Sheets son rápidas después de la primera
- El caché se invalida automáticamente después de cada escritura (venta, cobro, gasto)
- Endpoint `/ping` para keep-alive con cron externo, evita cold start de 30-60s en Render free tier
- Validación server-side en ítems gratis: el backend fuerza TOTAL = 0 independientemente del frontend, usando el flag `es_gratis` + verificación `descuento >= precio_lista`

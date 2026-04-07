# Formulario Livskin

Formulario web para registro de atenciones y ventas de **Livskin Professional Skincare**.

## ¿Qué hace?

Permite registrar desde cualquier celular o computadora los datos de cada atención:
- Fecha, área, tipo y categoría del tratamiento
- Zona / cantidad / envase
- Teléfono y próxima cita
- Cumpleaños del cliente
- Métodos de pago: efectivo, Yape, Plin, Giro, debe y saldo

Los datos se guardan automáticamente en **Google Sheets** en tiempo real.

## Link del formulario

🔗 https://formulario-livskin.onrender.com

## Tecnologías usadas

- **Python + Flask** — servidor web
- **Google Sheets API (gspread)** — base de datos
- **Render** — hosting gratuito
- **HTML/CSS** — diseño del formulario

## Estructura del proyecto

```
ProyectosClaude/
├── app.py                  # Servidor Flask principal
├── requirements.txt        # Dependencias de Python
├── render.yaml             # Configuración de Render
├── templates/
│   └── formulario.html     # Diseño del formulario web
└── static/
    └── logo.png            # Logo de Livskin
```

## Configuración para desarrollo local

1. Instalar dependencias:
   ```
   pip install -r requirements.txt
   ```

2. Agregar el archivo de credenciales de Google (`livskin-formulario-xxxx.json`) en la carpeta raíz.

3. Ejecutar:
   ```
   py app.py
   ```

## Notas

- El plan gratuito de Render puede tardar ~50 segundos en cargar si estuvo inactivo.
- Las credenciales de Google nunca se suben a GitHub (están en `.gitignore`).

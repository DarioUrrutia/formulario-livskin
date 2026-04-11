"""
Script de importación única: lee el CSV original y lo carga
en las 3 hojas de Google Sheets (Ventas, Gastos, Cobros).

Uso:
    python importar_csv.py                      <- busca "Inventario VF.csv" en la misma carpeta
    python importar_csv.py "ruta/al/archivo.csv"
"""

import csv
import sys
import os
import json
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1o4Vh4RN_Qfpaz8g08MReqgE3mFX0EGVSI5A69OsHB5g"

ENCABEZADOS_VENTAS = [
    "#", "FECHA", "CLIENTE", "TELEFONO", "TIPO", "CATEGORIA",
    "ZONA/CANTIDAD/ENVASE", "PROXIMA CITA", "CUMPLEANOS",
    "MONEDA", "TOTAL", "EFECTIVO", "YAPE", "PLIN", "GIRO", "DEBE"
]
ENCABEZADOS_GASTOS = [
    "#", "FECHA", "TIPO", "DESCRIPCION", "DESTINATARIO", "MONTO", "METODO DE PAGO"
]
ENCABEZADOS_COBROS = [
    "#", "FECHA", "CLIENTE", "MONTO", "EFECTIVO", "YAPE", "PLIN", "GIRO", "NOTAS"
]

def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(
            "livskin-formulario-56d6d2a0eac6.json", scopes=scopes
        )
    return gspread.authorize(creds)

def preparar_hoja(spreadsheet, nombre, encabezados):
    try:
        ws = spreadsheet.worksheet(nombre)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=nombre, rows=2000, cols=len(encabezados))
    ws.append_row(encabezados)
    return ws

def leer_csv(csv_path):
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(csv_path, encoding=enc, newline="") as f:
                rows = list(csv.reader(f, delimiter=";"))
            print(f"  Archivo leído con encoding: {enc}")
            return rows
        except UnicodeDecodeError:
            continue
    raise RuntimeError("No se pudo leer el archivo con ningún encoding conocido.")

def safe(row, i, default=""):
    try:
        return row[i].strip() if i < len(row) else default
    except Exception:
        return default

def calcular_monto_cobro(row):
    """Para filas de Pago, el monto es la suma de lo que efectivamente pagaron."""
    try:
        vals = []
        for i in [11, 12, 13, 14]:  # EFECTIVO, YAPE, PLIN, GIRO
            v = safe(row, i).replace(",", ".").replace(".", "", safe(row, i).count(".") - 1)
            if v:
                vals.append(float(v))
        return str(sum(vals)) if vals else ""
    except Exception:
        return ""

def importar(csv_path):
    print(f"\nLeyendo: {csv_path}")
    rows = leer_csv(csv_path)

    print("Conectando con Google Sheets...")
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SHEET_ID)

    ventas_ws = preparar_hoja(spreadsheet, "Ventas", ENCABEZADOS_VENTAS)
    gastos_ws = preparar_hoja(spreadsheet, "Gastos", ENCABEZADOS_GASTOS)
    cobros_ws = preparar_hoja(spreadsheet, "Cobros", ENCABEZADOS_COBROS)

    ventas_data, gastos_data, cobros_data = [], [], []
    n_v = n_g = n_c = 1

    # Saltear fila de encabezado
    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            continue  # fila vacía

        area = safe(row, 3).lower().strip()
        tipo = safe(row, 4).strip()

        # ── COBRO (paciente paga deuda) ───────────────────────────────────────
        if area == "pago":
            monto = calcular_monto_cobro(row)
            cobros_data.append([
                n_c,
                safe(row, 1),   # FECHA
                safe(row, 2),   # CLIENTE
                monto,          # MONTO
                safe(row, 11),  # EFECTIVO
                safe(row, 12),  # YAPE
                safe(row, 13),  # PLIN
                safe(row, 14),  # GIRO
                "",             # NOTAS
            ])
            n_c += 1

        # ── GASTO (costo de la clínica) ───────────────────────────────────────
        elif area == "costo":
            gastos_data.append([
                n_g,
                safe(row, 1),   # FECHA
                tipo,           # TIPO (RR.HH, etc.)
                safe(row, 5),   # DESCRIPCION (categoría)
                safe(row, 2),   # DESTINATARIO (nombre)
                safe(row, 10),  # MONTO
                "",             # METODO DE PAGO
            ])
            n_g += 1

        # ── VENTA (incluye promociones) ───────────────────────────────────────
        else:
            cliente  = safe(row, 2)
            tipo_v   = tipo

            # Sisol pasa a ser cliente
            if tipo_v.lower() == "sisol":
                cliente = "Sisol"
                tipo_v  = "Tratamiento"

            # Promociones
            if "promo" in area or "promo" in tipo_v.lower():
                tipo_v = "Promoción"

            ventas_data.append([
                n_v,
                safe(row, 1),   # FECHA
                cliente,        # CLIENTE
                safe(row, 7),   # TELEFONO
                tipo_v,         # TIPO
                safe(row, 5),   # CATEGORIA
                safe(row, 6),   # ZONA/CANTIDAD/ENVASE
                safe(row, 8),   # PROXIMA CITA
                safe(row, 17),  # CUMPLEANOS
                safe(row, 9),   # MONEDA
                safe(row, 10),  # TOTAL
                safe(row, 11),  # EFECTIVO
                safe(row, 12),  # YAPE
                safe(row, 13),  # PLIN
                safe(row, 14),  # GIRO
                safe(row, 15),  # DEBE
            ])
            n_v += 1

    # Subir en lote (mucho más rápido que fila por fila)
    print("\nSubiendo datos...")
    if ventas_data:
        ventas_ws.append_rows(ventas_data, value_input_option="USER_ENTERED")
        print(f"  Ventas:  {len(ventas_data)} filas")
    if gastos_data:
        gastos_ws.append_rows(gastos_data, value_input_option="USER_ENTERED")
        print(f"  Gastos:  {len(gastos_data)} filas")
    if cobros_data:
        cobros_ws.append_rows(cobros_data, value_input_option="USER_ENTERED")
        print(f"  Cobros:  {len(cobros_data)} filas")

    print("\n✓ Importación completada.")

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "Inventario VF.csv"
    if not os.path.exists(csv_path):
        print(f"Error: no se encontró el archivo '{csv_path}'")
        print("Copiá tu CSV a esta carpeta o pasá la ruta como argumento:")
        print("  python importar_csv.py \"C:/ruta/al/archivo.csv\"")
        sys.exit(1)
    importar(csv_path)

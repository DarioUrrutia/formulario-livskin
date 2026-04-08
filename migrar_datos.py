"""
Script de migración: asigna códigos LIVCLIENT, LIVTRAT, LIVPROD
a todos los registros existentes en Google Sheets.
Ejecutar UNA sola vez.
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

SHEET_ID = "1o4Vh4RN_Qfpaz8g08MReqgE3mFX0EGVSI5A69OsHB5g"

NUEVOS_ENCABEZADOS_VENTAS = [
    "#", "FECHA", "COD_CLIENTE", "CLIENTE", "TELEFONO", "TIPO", "COD_ITEM",
    "CATEGORIA", "ZONA/CANTIDAD/ENVASE", "PROXIMA CITA", "CUMPLEANOS",
    "MONEDA", "TOTAL", "EFECTIVO", "YAPE", "PLIN", "GIRO", "DEBE"
]

ENCABEZADOS_CLIENTES = [
    "COD_CLIENTE", "NOMBRE", "TELEFONO", "CUMPLEANOS", "FECHA_REGISTRO"
]

def conectar():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(
        "livskin-formulario-56d6d2a0eac6.json", scopes=scopes
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def migrar():
    print("Conectando a Google Sheets...")
    spreadsheet = conectar()
    ventas_ws = spreadsheet.worksheet("Ventas")

    print("Leyendo datos existentes...")
    todos = ventas_ws.get_all_values()
    if not todos:
        print("Hoja vacía, nada que migrar.")
        return

    encabezados_actuales = todos[0]
    filas = todos[1:]

    # Detectar si ya fue migrado
    if "COD_CLIENTE" in encabezados_actuales:
        print("Los datos ya tienen el formato nuevo. No se necesita migración.")
        return

    print(f"Encontradas {len(filas)} filas con formato antiguo.")
    print("Iniciando migración...\n")

    # Registro de clientes: nombre_lower -> código
    clientes_map = {}
    trat_counter = 0
    prod_counter = 0

    # Detectar contador inicial de tratamientos y productos
    # (por si ya hay algunos registrados con código)
    for fila in filas:
        if len(fila) > 4:
            tipo = fila[4].strip()
            if tipo in ("Tratamiento", "Promoción"):
                trat_counter += 1
            elif tipo == "Producto":
                prod_counter += 1

    # Reiniciar contadores para asignar desde 1
    trat_counter = 0
    prod_counter = 0

    nuevas_filas = []
    for i, fila in enumerate(filas):
        if not any(fila):
            continue  # saltar filas vacías

        # Formato antiguo: #, FECHA, CLIENTE, TELEFONO, TIPO, CATEGORIA,
        # ZONA/CANTIDAD/ENVASE, PROXIMA CITA, CUMPLEANOS, MONEDA, TOTAL,
        # EFECTIVO, YAPE, PLIN, GIRO, DEBE
        num       = fila[0]  if len(fila) > 0 else ""
        fecha     = fila[1]  if len(fila) > 1 else ""
        cliente   = fila[2]  if len(fila) > 2 else ""
        telefono  = fila[3]  if len(fila) > 3 else ""
        tipo      = fila[4]  if len(fila) > 4 else ""
        categoria = fila[5]  if len(fila) > 5 else ""
        zona      = fila[6]  if len(fila) > 6 else ""
        prox_cita = fila[7]  if len(fila) > 7 else ""
        cumple    = fila[8]  if len(fila) > 8 else ""
        moneda    = fila[9]  if len(fila) > 9 else ""
        total     = fila[10] if len(fila) > 10 else ""
        efectivo  = fila[11] if len(fila) > 11 else ""
        yape      = fila[12] if len(fila) > 12 else ""
        plin      = fila[13] if len(fila) > 13 else ""
        giro      = fila[14] if len(fila) > 14 else ""
        debe      = fila[15] if len(fila) > 15 else ""

        # Asignar código de cliente
        clave = cliente.strip().lower()
        if clave and clave not in clientes_map:
            nuevo_num = len(clientes_map) + 1
            clientes_map[clave] = f"LIVCLIENT{nuevo_num:04d}"
        cod_cliente = clientes_map.get(clave, "")

        # Asignar código de ítem
        tipo_limpio = tipo.strip()
        if tipo_limpio in ("Tratamiento", "Promoción"):
            trat_counter += 1
            cod_item = f"LIVTRAT{trat_counter:04d}"
        elif tipo_limpio == "Producto":
            prod_counter += 1
            cod_item = f"LIVPROD{prod_counter:04d}"
        else:
            cod_item = ""

        nueva_fila = [
            num, fecha, cod_cliente, cliente, telefono, tipo, cod_item,
            categoria, zona, prox_cita, cumple, moneda, total,
            efectivo, yape, plin, giro, debe
        ]
        nuevas_filas.append(nueva_fila)

        if (i + 1) % 50 == 0:
            print(f"  Procesadas {i + 1} filas...")

    print(f"\nClientes únicos encontrados: {len(clientes_map)}")
    for nombre, codigo in sorted(clientes_map.items(), key=lambda x: x[1]):
        print(f"  {codigo} - {nombre}")

    # Actualizar hoja Ventas
    print("\nActualizando hoja Ventas...")
    ventas_ws.clear()
    ventas_ws.append_row(NUEVOS_ENCABEZADOS_VENTAS)
    if nuevas_filas:
        ventas_ws.append_rows(nuevas_filas)
    print(f"OK Ventas actualizada con {len(nuevas_filas)} filas.")

    # Crear/actualizar hoja Clientes
    print("\nCreando hoja Clientes...")
    try:
        clientes_ws = spreadsheet.worksheet("Clientes")
        clientes_ws.clear()
    except gspread.WorksheetNotFound:
        clientes_ws = spreadsheet.add_worksheet(title="Clientes", rows=2000, cols=10)

    clientes_ws.append_row(ENCABEZADOS_CLIENTES)
    filas_clientes = []
    for nombre_lower, codigo in sorted(clientes_map.items(), key=lambda x: x[1]):
        # Buscar nombre original con mayúsculas en los datos
        nombre_original = next(
            (f[2] for f in filas if f[2].strip().lower() == nombre_lower),
            nombre_lower
        )
        filas_clientes.append([codigo, nombre_original, "", "", str(date.today())])

    if filas_clientes:
        clientes_ws.append_rows(filas_clientes)
    print(f"OK Hoja Clientes creada con {len(filas_clientes)} clientes.")

    print("\nOK Migración completada exitosamente.")

if __name__ == "__main__":
    migrar()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import gspread
from google.oauth2.service_account import Credentials
from collections import defaultdict
from datetime import datetime, date
import os
import json

app = Flask(__name__)
app.secret_key = "livskin2024"

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
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(
            "livskin-formulario-56d6d2a0eac6.json", scopes=scopes
        )
    return gspread.authorize(creds)

def get_or_create_worksheet(spreadsheet, nombre, encabezados):
    try:
        ws = spreadsheet.worksheet(nombre)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=nombre, rows=2000, cols=len(encabezados))
        ws.append_row(encabezados)
    return ws

def get_sheets():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    ventas  = get_or_create_worksheet(spreadsheet, "Ventas",  ENCABEZADOS_VENTAS)
    gastos  = get_or_create_worksheet(spreadsheet, "Gastos",  ENCABEZADOS_GASTOS)
    cobros  = get_or_create_worksheet(spreadsheet, "Cobros",  ENCABEZADOS_COBROS)
    return ventas, gastos, cobros

def siguiente_numero(sheet):
    todos = sheet.get_all_values()
    datos = [r for r in todos[1:] if any(r)]
    return len(datos) + 1

def obtener_clientes(sheet_ventas):
    todos = sheet_ventas.get_all_values()
    nombres = set()
    for fila in todos[1:]:
        if len(fila) > 2 and fila[2].strip():
            nombres.add(fila[2].strip())
    return sorted(nombres)

# ── Página principal ──────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    active_tab = request.args.get("tab", "venta")
    try:
        ventas, _, _ = get_sheets()
        clientes = obtener_clientes(ventas)
    except Exception:
        clientes = []
    return render_template("formulario.html", clientes=clientes, active_tab=active_tab)

# ── Guardar Venta ─────────────────────────────────────────────────────────────

@app.route("/venta", methods=["POST"])
def guardar_venta():
    categoria = request.form.get("categoria", "")
    if categoria == "__otro__":
        categoria = request.form.get("categoria_otro", "")

    try:
        ventas, _, _ = get_sheets()
        num = siguiente_numero(ventas)
        datos = [
            num,
            request.form.get("fecha", ""),
            request.form.get("cliente", ""),
            request.form.get("telefono", ""),
            request.form.get("tipo", ""),
            categoria,
            request.form.get("zona_cantidad_envase", ""),
            request.form.get("proxima_cita", ""),
            request.form.get("cumpleanos", ""),
            request.form.get("moneda", "SOLES"),
            request.form.get("total", ""),
            request.form.get("efectivo", ""),
            request.form.get("yape", ""),
            request.form.get("plin", ""),
            request.form.get("giro", ""),
            request.form.get("debe", ""),
        ]
        ventas.append_row(datos)
        flash("Venta guardada correctamente.")
    except Exception as e:
        flash(f"Error al guardar: {e}")

    return redirect(url_for("index", tab="venta"))

# ── Guardar Gasto ─────────────────────────────────────────────────────────────

@app.route("/gasto", methods=["POST"])
def guardar_gasto():
    try:
        _, gastos, _ = get_sheets()
        num = siguiente_numero(gastos)
        datos = [
            num,
            request.form.get("fecha_gasto", ""),
            request.form.get("tipo_gasto", ""),
            request.form.get("descripcion", ""),
            request.form.get("destinatario", ""),
            request.form.get("monto_gasto", ""),
            request.form.get("metodo_pago_gasto", ""),
        ]
        gastos.append_row(datos)
        flash("Gasto guardado correctamente.")
    except Exception as e:
        flash(f"Error al guardar: {e}")

    return redirect(url_for("index", tab="gasto"))

# ── Guardar Cobro ─────────────────────────────────────────────────────────────

@app.route("/cobro", methods=["POST"])
def guardar_cobro():
    try:
        _, _, cobros = get_sheets()
        num = siguiente_numero(cobros)
        datos = [
            num,
            request.form.get("fecha_cobro", ""),
            request.form.get("cliente_cobro", ""),
            request.form.get("monto_cobro", ""),
            request.form.get("efectivo_cobro", ""),
            request.form.get("yape_cobro", ""),
            request.form.get("plin_cobro", ""),
            request.form.get("giro_cobro", ""),
            request.form.get("notas_cobro", ""),
        ]
        cobros.append_row(datos)
        flash("Cobro registrado correctamente.")
    except Exception as e:
        flash(f"Error al guardar: {e}")

    return redirect(url_for("index", tab="cobro"))

# ── Vista por Cliente (JSON) ──────────────────────────────────────────────────

@app.route("/cliente")
def ver_cliente():
    nombre = request.args.get("nombre", "").strip().lower()
    if not nombre:
        return jsonify({"ventas": [], "cobros": [], "debe_total": 0, "cobrado_total": 0, "saldo": 0})

    ventas_ws, _, cobros_ws = get_sheets()

    # Ventas del cliente
    todas_ventas = ventas_ws.get_all_values()
    ventas_cliente = []
    debe_total = 0.0
    if len(todas_ventas) > 1:
        headers = todas_ventas[0]
        for fila in todas_ventas[1:]:
            if len(fila) > 2 and fila[2].strip().lower() == nombre:
                ventas_cliente.append(dict(zip(headers, fila)))
                try:
                    debe_total += float(str(fila[15]).replace(",", ".") or 0)
                except (ValueError, IndexError):
                    pass

    # Cobros del cliente
    todos_cobros = cobros_ws.get_all_values()
    cobros_cliente = []
    cobrado_total = 0.0
    if len(todos_cobros) > 1:
        headers_c = todos_cobros[0]
        for fila in todos_cobros[1:]:
            if len(fila) > 2 and fila[2].strip().lower() == nombre:
                cobros_cliente.append(dict(zip(headers_c, fila)))
                try:
                    cobrado_total += float(str(fila[3]).replace(",", ".") or 0)
                except (ValueError, IndexError):
                    pass

    return jsonify({
        "ventas": ventas_cliente,
        "cobros": cobros_cliente,
        "debe_total": debe_total,
        "cobrado_total": cobrado_total,
        "saldo": debe_total - cobrado_total
    })

# ── Dashboard ─────────────────────────────────────────────────────────────────

def parse_fecha(val):
    val = str(val).strip() if val else ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass
    try:
        partes = val.split("/")
        if len(partes) == 3:
            return date(int(partes[2]), int(partes[1]), int(partes[0]))
    except Exception:
        pass
    return None

def parse_num(val):
    if not val:
        return 0.0
    val = str(val).strip()
    if "," in val and "." in val:
        val = val.replace(".", "").replace(",", ".")
    elif "," in val:
        val = val.replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return 0.0

@app.route("/api/dashboard")
def api_dashboard():
    desde_str = request.args.get("desde", "")
    hasta_str = request.args.get("hasta", "")
    desde = parse_fecha(desde_str)
    hasta = parse_fecha(hasta_str)

    ventas_ws, gastos_ws, _ = get_sheets()
    todos       = ventas_ws.get_all_values()
    todos_gasto = gastos_ws.get_all_values()

    if len(todos) < 2:
        return jsonify({"sin_datos": True})

    # ── Leer ventas ───────────────────────────────────────────────────────────
    filas = []
    for row in todos[1:]:
        if not any(row):
            continue
        def g(i, r=row): return r[i].strip() if i < len(r) else ""
        fecha = parse_fecha(g(1))
        if not fecha:
            continue
        if desde and fecha < desde:
            continue
        if hasta and fecha > hasta:
            continue
        cobrado = parse_num(g(11)) + parse_num(g(12)) + parse_num(g(13)) + parse_num(g(14))
        filas.append({
            "fecha":     fecha,
            "cliente":   g(2),
            "tipo":      g(4),
            "categoria": g(5),
            "total":     parse_num(g(10)),
            "cobrado":   cobrado,
            "efectivo":  parse_num(g(11)),
            "yape":      parse_num(g(12)),
            "plin":      parse_num(g(13)),
            "giro":      parse_num(g(14)),
            "debe":      parse_num(g(15)),
        })

    # ── Leer gastos del mismo período ─────────────────────────────────────────
    total_gastos = 0.0
    for row in todos_gasto[1:]:
        if not any(row):
            continue
        def gg(i, r=row): return r[i].strip() if i < len(r) else ""
        fecha_g = parse_fecha(gg(1))
        if not fecha_g:
            continue
        if desde and fecha_g < desde:
            continue
        if hasta and fecha_g > hasta:
            continue
        total_gastos += parse_num(gg(5))

    if not filas:
        return jsonify({
            "ventas_total": 0, "cobrado_total": 0, "pendiente_total": 0,
            "ticket_promedio": 0, "tasa_cobro": 0, "num_atenciones": 0,
            "num_clientes": 0, "num_promociones": 0, "total_gastos": 0,
            "balance_neto": 0, "ef_efectivo": 0, "ef_yape": 0, "ef_plin": 0, "ef_giro": 0,
            "pct_tratamientos": 0, "pct_productos": 0,
            "por_mes": [], "top_clientes": [], "por_categoria": [], "recientes": []
        })

    # ── KPIs financieros ──────────────────────────────────────────────────────
    ventas_total    = sum(f["total"]   for f in filas)
    cobrado_total   = sum(f["cobrado"] for f in filas)
    pendiente_total = sum(f["debe"]    for f in filas)
    num_atenciones  = len(filas)
    num_clientes    = len({f["cliente"] for f in filas if f["cliente"]})
    num_promociones = sum(1 for f in filas if f["tipo"] == "Promoción")
    ticket_promedio = ventas_total / num_atenciones if num_atenciones else 0
    tasa_cobro      = (cobrado_total / ventas_total * 100) if ventas_total else 0
    balance_neto    = cobrado_total - total_gastos

    # ── Métodos de pago ───────────────────────────────────────────────────────
    ef_efectivo = sum(f["efectivo"] for f in filas)
    ef_yape     = sum(f["yape"]     for f in filas)
    ef_plin     = sum(f["plin"]     for f in filas)
    ef_giro     = sum(f["giro"]     for f in filas)

    # ── Tratamientos vs Productos ─────────────────────────────────────────────
    total_tratamientos = sum(f["total"] for f in filas if f["tipo"] == "Tratamiento")
    total_productos    = sum(f["total"] for f in filas if f["tipo"] == "Producto")
    total_otros        = ventas_total - total_tratamientos - total_productos

    # ── Ventas por mes (con cobrado y pendiente) ───────────────────────────────
    meses_data = defaultdict(lambda: {"total": 0.0, "cobrado": 0.0, "debe": 0.0})
    for f in filas:
        k = f["fecha"].strftime("%Y-%m")
        meses_data[k]["total"]   += f["total"]
        meses_data[k]["cobrado"] += f["cobrado"]
        meses_data[k]["debe"]    += f["debe"]
    por_mes = [
        {"mes": k, "total": round(v["total"], 2),
         "cobrado": round(v["cobrado"], 2), "debe": round(v["debe"], 2)}
        for k, v in sorted(meses_data.items())
    ]

    # ── Top 10 clientes ───────────────────────────────────────────────────────
    clientes_d = defaultdict(lambda: {"total": 0.0, "visitas": 0})
    for f in filas:
        if f["cliente"]:
            clientes_d[f["cliente"]]["total"]   += f["total"]
            clientes_d[f["cliente"]]["visitas"] += 1
    top_clientes = sorted(
        [{"cliente": k, "total": round(v["total"], 2), "visitas": v["visitas"]}
         for k, v in clientes_d.items()],
        key=lambda x: x["total"], reverse=True
    )[:10]

    # ── Top 10 categorías ─────────────────────────────────────────────────────
    cats = defaultdict(lambda: {"total": 0.0, "count": 0})
    for f in filas:
        if f["categoria"] and f["tipo"] != "Promoción":
            cats[f["categoria"]]["total"] += f["total"]
            cats[f["categoria"]]["count"] += 1
    por_categoria = sorted(
        [{"categoria": k, "total": round(v["total"], 2), "count": v["count"]}
         for k, v in cats.items()],
        key=lambda x: x["total"], reverse=True
    )[:10]

    # ── 10 ventas más recientes ───────────────────────────────────────────────
    recientes = sorted(filas, key=lambda x: x["fecha"], reverse=True)[:10]
    recientes_out = [
        {"fecha": f["fecha"].strftime("%d/%m/%Y"), "cliente": f["cliente"],
         "categoria": f["categoria"], "total": f["total"], "debe": f["debe"]}
        for f in recientes
    ]

    return jsonify({
        # KPIs financieros
        "ventas_total":    round(ventas_total, 2),
        "cobrado_total":   round(cobrado_total, 2),
        "pendiente_total": round(pendiente_total, 2),
        "ticket_promedio": round(ticket_promedio, 2),
        "tasa_cobro":      round(tasa_cobro, 1),
        "balance_neto":    round(balance_neto, 2),
        "total_gastos":    round(total_gastos, 2),
        # KPIs operativos
        "num_atenciones":  num_atenciones,
        "num_clientes":    num_clientes,
        "num_promociones": num_promociones,
        # Métodos de pago
        "ef_efectivo": round(ef_efectivo, 2),
        "ef_yape":     round(ef_yape, 2),
        "ef_plin":     round(ef_plin, 2),
        "ef_giro":     round(ef_giro, 2),
        # Mix
        "total_tratamientos": round(total_tratamientos, 2),
        "total_productos":    round(total_productos, 2),
        "total_otros":        round(total_otros, 2),
        # Gráficos
        "por_mes":       por_mes,
        "top_clientes":  top_clientes,
        "por_categoria": por_categoria,
        "recientes":     recientes_out,
    })

if __name__ == "__main__":
    app.run(debug=True)

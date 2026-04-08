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
    "#", "FECHA", "COD_CLIENTE", "CLIENTE", "TELEFONO", "TIPO", "COD_ITEM",
    "CATEGORIA", "ZONA/CANTIDAD/ENVASE", "PROXIMA CITA", "FECHA_NAC",
    "MONEDA", "TOTAL S/ (PEN)", "EFECTIVO", "YAPE", "PLIN", "GIRO", "DEBE", "PAGADO", "TC"
]

ENCABEZADOS_GASTOS = [
    "#", "FECHA", "TIPO", "DESCRIPCION", "DESTINATARIO", "MONTO", "METODO DE PAGO"
]

ENCABEZADOS_COBROS = [
    "#", "FECHA", "COD_CLIENTE", "CLIENTE", "MONTO", "EFECTIVO", "YAPE", "PLIN", "GIRO", "NOTAS",
    "COD_ITEM", "CATEGORIA"
]

ENCABEZADOS_CLIENTES = [
    "COD_CLIENTE", "NOMBRE", "TELEFONO", "FECHA_NAC", "FECHA_REGISTRO", "EMAIL"
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
        ws = spreadsheet.add_worksheet(title=nombre, rows=2000, cols=max(len(encabezados), 20))
        ws.append_row(encabezados)
    return ws

def get_sheets():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    ventas   = get_or_create_worksheet(spreadsheet, "Ventas",   ENCABEZADOS_VENTAS)
    gastos   = get_or_create_worksheet(spreadsheet, "Gastos",   ENCABEZADOS_GASTOS)
    cobros   = get_or_create_worksheet(spreadsheet, "Cobros",   ENCABEZADOS_COBROS)
    clientes = get_or_create_worksheet(spreadsheet, "Clientes", ENCABEZADOS_CLIENTES)
    return ventas, gastos, cobros, clientes

def get_or_create_cliente(clientes_ws, nombre, telefono="", cumpleanos="", email=""):
    """Retorna el código del cliente, creándolo si no existe."""
    todos = clientes_ws.get_all_values()
    nombre_lower = nombre.strip().lower()
    for fila in todos[1:]:
        if len(fila) > 1 and fila[1].strip().lower() == nombre_lower:
            return fila[0]
    # Crear nuevo cliente
    num = len([r for r in todos[1:] if any(r)]) + 1
    codigo = f"LIVCLIENT{num:04d}"
    clientes_ws.append_row([codigo, nombre.strip(), telefono, cumpleanos, str(date.today()), email])
    return codigo

def get_next_item_code(ventas_ws, tipo):
    """Genera el siguiente código LIVTRAT#### o LIVPROD####."""
    if tipo in ("Tratamiento", "Certificado"):
        prefix = "LIVTRAT"
    elif tipo == "Producto":
        prefix = "LIVPROD"
    else:
        prefix = "LIVTRAT"
    todos = ventas_ws.get_all_values()
    max_num = 0
    for fila in todos[1:]:
        # COD_ITEM está en índice 6
        if len(fila) > 6 and str(fila[6]).startswith(prefix):
            try:
                num = int(fila[6][len(prefix):])
                max_num = max(max_num, num)
            except ValueError:
                pass
    return f"{prefix}{max_num + 1:04d}"

def siguiente_numero(sheet):
    todos = sheet.get_all_values()
    # Solo contar filas que tengan datos reales (al menos fecha o nombre, no solo numero)
    datos = [r for r in todos[1:] if len(r) > 1 and any(r[1:])]
    return len(datos) + 1

def obtener_clientes(sheet_ventas):
    todos = sheet_ventas.get_all_values()
    nombres = set()
    for fila in todos[1:]:
        if not any(fila):
            continue
        # Formato nuevo: COD_CLIENTE en [2], CLIENTE en [3]
        if len(fila) > 2 and str(fila[2]).startswith("LIVCLIENT"):
            if len(fila) > 3 and fila[3].strip():
                nombres.add(fila[3].strip())
        # Formato antiguo: CLIENTE en [2]
        elif len(fila) > 2 and fila[2].strip():
            nombres.add(fila[2].strip())
    return sorted(nombres)

# ── Actualizar headers (llamar una vez después de deploy) ────────────────────

@app.route("/actualizar-headers")
def actualizar_headers():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        for nombre, enc in [
            ("Ventas",   ENCABEZADOS_VENTAS),
            ("Cobros",   ENCABEZADOS_COBROS),
            ("Clientes", ENCABEZADOS_CLIENTES),
        ]:
            try:
                ws = spreadsheet.worksheet(nombre)
                ws.update('A1', [enc])
            except Exception as e:
                pass
        return "Headers actualizados correctamente."
    except Exception as e:
        return f"Error: {e}"

# ── Página principal ──────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    active_tab = request.args.get("tab", "venta")
    clientes = []
    clientes_codigos = {}
    clientes_data = {}
    next_client_num = 1
    try:
        _, _, _, clientes_ws = get_sheets()
        todos_c = clientes_ws.get_all_values()
        for fila in todos_c[1:]:
            if not (len(fila) > 1 and fila[1].strip()):
                continue
            nombre_c = fila[1].strip()
            key = nombre_c.lower()
            clientes.append(nombre_c)
            clientes_codigos[key] = fila[0]
            clientes_data[key] = {
                "codigo":     fila[0] if len(fila) > 0 else "",
                "telefono":   fila[2] if len(fila) > 2 else "",
                "cumpleanos": fila[3] if len(fila) > 3 else "",
                "email":      fila[5] if len(fila) > 5 else "",
            }
        clientes.sort()
        next_client_num = len([r for r in todos_c[1:] if any(r)]) + 1
    except Exception:
        pass
    return render_template("formulario.html", clientes=clientes, active_tab=active_tab,
                           clientes_codigos=clientes_codigos, clientes_data=clientes_data,
                           next_client_num=next_client_num)

# ── Guardar Venta ─────────────────────────────────────────────────────────────

@app.route("/venta", methods=["POST"])
def guardar_venta():
    try:
        ventas, _, _, clientes_ws = get_sheets()

        # Datos compartidos del cliente
        fecha      = request.form.get("fecha", "")
        cliente    = request.form.get("cliente", "")
        telefono   = request.form.get("telefono", "")
        email      = request.form.get("email", "")
        cumpleanos = request.form.get("cumpleanos", "")
        moneda     = request.form.get("moneda", "SOLES")

        # Obtener o crear código de cliente
        cod_cliente = get_or_create_cliente(clientes_ws, cliente, telefono, cumpleanos, email)

        # Métodos de pago del día (van solo en la primera fila)
        efectivo = request.form.get("efectivo", "")
        yape     = request.form.get("yape", "")
        plin     = request.form.get("plin", "")
        giro     = request.form.get("giro", "")

        # Total pagado hoy (suma de métodos)
        def to_float(v):
            try: return float(v) if v else 0.0
            except: return 0.0

        total_pagado_hoy = to_float(efectivo) + to_float(yape) + to_float(plin) + to_float(giro)

        num_items = int(request.form.get("num_items", 1))
        total_contratado = 0.0

        # ── Fase 1: preparar todos los ítems con sus códigos ──────────────────
        items_prep = []
        for i in range(num_items):
            tipo = request.form.get(f"tipo_{i}", "")
            if not tipo:
                continue
            categoria = request.form.get(f"categoria_{i}", "")
            if categoria == "__otro__":
                categoria = request.form.get(f"categoria_otro_{i}", "")
            zona         = request.form.get(f"zona_{i}", "")
            moneda_item  = request.form.get(f"moneda_item_{i}", "Soles")
            tc_item      = request.form.get(f"tc_item_{i}", "") or ""
            precio_soles = to_float(request.form.get(f"total_item_{i}", "0") or "0")
            pago_item    = to_float(request.form.get(f"pago_item_{i}", "0") or "0")
            debe_item    = max(0.0, precio_soles - pago_item)
            total_contratado += precio_soles

            if tipo in ("Tratamiento", "Certificado"):
                cod_item = get_next_item_code(ventas, "Tratamiento")
            elif tipo == "Producto":
                cod_item = get_next_item_code(ventas, "Producto")
            else:
                cod_item = ""

            items_prep.append({
                "tipo": tipo, "categoria": categoria, "zona": zona,
                "moneda": moneda_item, "tc": tc_item,
                "precio": precio_soles, "pago": pago_item, "debe": debe_item,
                "cod_item": cod_item,
            })

        # ── Fase 2: guardar en Ventas ─────────────────────────────────────────
        for idx, item in enumerate(items_prep):
            ef = efectivo if idx == 0 else ""
            ya = yape     if idx == 0 else ""
            pl = plin     if idx == 0 else ""
            gi = giro     if idx == 0 else ""
            num = siguiente_numero(ventas)
            ventas.append_row([
                num, fecha, cod_cliente, cliente, telefono,
                item["tipo"], item["cod_item"], item["categoria"], item["zona"],
                "", cumpleanos, item["moneda"], round(item["precio"]) if item["precio"] else "",
                ef, ya, pl, gi,
                round(item["debe"]) if item["debe"] else "",
                round(item["pago"]) if item["pago"] else "",
                item["tc"]
            ])

        # ── Fase 3: registrar en Cobros (uno por ítem pagado, relacional) ─────
        credito_aplicado = to_float(request.form.get("credito_aplicado", "0"))
        _, _, cobros, _ = get_sheets()
        cobros_idx = 0

        if total_pagado_hoy > 0:
            for item in items_prep:
                if item["pago"] <= 0:
                    continue
                ef_c = efectivo if cobros_idx == 0 else ""
                ya_c = yape     if cobros_idx == 0 else ""
                pl_c = plin     if cobros_idx == 0 else ""
                gi_c = giro     if cobros_idx == 0 else ""
                num_cobro = siguiente_numero(cobros)
                cobros.append_row([
                    num_cobro, fecha, cod_cliente, cliente,
                    round(item["pago"]),
                    ef_c, ya_c, pl_c, gi_c,
                    f"Pago venta {fecha}",
                    item["cod_item"], item["categoria"]
                ])
                cobros_idx += 1

        # ── Fase 4: registrar crédito por exceso de pago ────────────────────
        credito_exceso = to_float(request.form.get("credito_exceso", "0"))
        nota_exceso    = request.form.get("credito_exceso_nota", "").strip()
        if credito_exceso > 0:
            num_cobro = siguiente_numero(cobros)
            categoria_credito = f"CRÉDITO: {nota_exceso}" if nota_exceso else "CRÉDITO"
            cobros.append_row([
                num_cobro, fecha, cod_cliente, cliente,
                round(credito_exceso),
                "", "", "", "",
                "Crédito generado por exceso de pago",
                "", categoria_credito
            ])

        # ── Fase 5: registrar crédito aplicado (vinculado al ítem) ───────────
        if credito_aplicado > 0 and items_prep:
            # Distribuir el crédito proporcionalmente entre los ítems
            total_items = sum(it["precio"] for it in items_prep) or 1
            credito_restante = credito_aplicado
            for idx, item in enumerate(items_prep):
                if credito_restante <= 0:
                    break
                if item["precio"] <= 0:
                    continue
                proporcion = item["precio"] / total_items
                credito_item = round(min(credito_restante, credito_aplicado * proporcion))
                if credito_item <= 0:
                    continue
                credito_restante -= credito_item
                num_cobro = siguiente_numero(cobros)
                cobros.append_row([
                    num_cobro, fecha, cod_cliente, cliente,
                    credito_item,
                    "", "", "", "",
                    "Crédito aplicado",
                    item["cod_item"], item["categoria"]
                ])

        if items_prep:
            saldo = round(total_contratado - total_pagado_hoy)
            msg = f"Venta guardada ({len(items_prep)} ítem(s)) — Cliente: {cod_cliente}"
            if saldo > 0:
                msg += f" — Saldo pendiente: S/ {saldo}"
            flash(msg)
        else:
            flash("No se ingresó ningún servicio.")
    except Exception as e:
        flash(f"Error al guardar: {e}")

    return redirect(url_for("index", tab="venta"))

# ── Guardar Gasto ─────────────────────────────────────────────────────────────

@app.route("/gasto", methods=["POST"])
def guardar_gasto():
    try:
        _, gastos, _, _ = get_sheets()
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
        _, _, cobros, clientes_ws = get_sheets()
        nombre_cobro = request.form.get("cliente_cobro", "")
        cod_cliente  = get_or_create_cliente(clientes_ws, nombre_cobro) if nombre_cobro else ""
        fecha        = request.form.get("fecha_cobro", "")
        efectivo     = request.form.get("efectivo_cobro", "")
        yape         = request.form.get("yape_cobro", "")
        plin         = request.form.get("plin_cobro", "")
        giro         = request.form.get("giro_cobro", "")
        notas        = request.form.get("notas_cobro", "")

        # Leer lista de ítems: cod_item_cobro[] y monto_item_cobro[]
        cod_items  = request.form.getlist("cod_item_cobro[]")
        montos     = request.form.getlist("monto_item_cobro[]")
        categorias = request.form.getlist("categoria_cobro[]")

        # Compatibilidad: si viene el formato antiguo (un solo ítem)
        if not cod_items:
            cod_items  = [request.form.get("cod_item_cobro", "")]
            montos     = [request.form.get("monto_cobro", "")]
            categorias = [request.form.get("categoria_cobro", "")]

        filas_guardadas = 0
        for idx, (cod, monto, cat) in enumerate(zip(cod_items, montos, categorias)):
            if not monto or float(monto or 0) <= 0:
                continue
            # Métodos de pago solo en la primera fila
            ef = efectivo if idx == 0 else ""
            ya = yape     if idx == 0 else ""
            pl = plin     if idx == 0 else ""
            gi = giro     if idx == 0 else ""
            num = siguiente_numero(cobros)
            cobros.append_row([
                num, fecha, cod_cliente, nombre_cobro,
                round(float(monto)),
                ef, ya, pl, gi,
                notas, cod, cat
            ])
            filas_guardadas += 1

        if filas_guardadas > 0:
            flash(f"Cobro registrado correctamente ({filas_guardadas} ítem(s)).")
        else:
            flash("No se ingresó ningún monto válido.")
    except Exception as e:
        flash(f"Error al guardar: {e}")

    return redirect(url_for("index", tab="cobro"))

# ── Vista por Cliente (JSON) ──────────────────────────────────────────────────

@app.route("/cliente")
def ver_cliente():
    nombre = request.args.get("nombre", "").strip().lower()
    if not nombre:
        return jsonify({"ventas": [], "cobros": [], "facturado_total": 0, "cobrado_total": 0, "saldo": 0})

    ventas_ws, _, cobros_ws, _ = get_sheets()

    # Ventas del cliente — suma TOTAL (índice 12), no DEBE
    todas_ventas = ventas_ws.get_all_values()
    ventas_cliente = []
    facturado_total = 0.0
    if len(todas_ventas) > 1:
        headers = todas_ventas[0]
        for fila in todas_ventas[1:]:
            if len(fila) > 3 and fila[3].strip().lower() == nombre:
                ventas_cliente.append(dict(zip(headers, fila)))
                try:
                    facturado_total += float(str(fila[12]).replace(",", ".") or 0)
                except (ValueError, IndexError):
                    pass

    # Cobros del cliente — suma MONTO (índice 4)
    todos_cobros = cobros_ws.get_all_values()
    cobros_cliente = []
    cobrado_total = 0.0
    if len(todos_cobros) > 1:
        headers_c = todos_cobros[0]
        for fila in todos_cobros[1:]:
            if len(fila) > 3 and fila[3].strip().lower() == nombre:
                cobros_cliente.append(dict(zip(headers_c, fila)))
                try:
                    cobrado_total += float(str(fila[4]).replace(",", ".") or 0)
                except (ValueError, IndexError):
                    pass

    # Calcular DEBE real por ítem: TOTAL - suma de cobros vinculados por COD_ITEM
    cobros_por_item = calcular_cobros_por_item(todos_cobros)
    for v in ventas_cliente:
        cod  = v.get("COD_ITEM", "").strip()
        total_v = parse_num(v.get("TOTAL S/ (PEN)") or v.get("TOTAL") or "0")
        cobrado_item = cobros_por_item.get(cod, 0.0) if cod else 0.0
        debe_real = max(0.0, total_v - cobrado_item)
        v["DEBE"] = str(round(debe_real))  # sobreescribir con el valor real calculado

    saldo = round(facturado_total - cobrado_total, 2)
    return jsonify({
        "ventas": ventas_cliente,
        "cobros": cobros_cliente,
        "facturado_total": facturado_total,
        "cobrado_total":   cobrado_total,
        "saldo":           saldo
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

def calcular_cobros_por_item(todos_cobros):
    """Retorna dict {cod_item: total_cobrado} sumando todos los cobros por COD_ITEM."""
    resultado = defaultdict(float)
    if len(todos_cobros) < 2:
        return resultado
    headers = todos_cobros[0]
    try:
        idx_cod  = headers.index("COD_ITEM")
        idx_monto = headers.index("MONTO")
    except ValueError:
        return resultado
    for fila in todos_cobros[1:]:
        if not any(fila):
            continue
        cod  = fila[idx_cod].strip()  if idx_cod  < len(fila) else ""
        monto = fila[idx_monto].strip() if idx_monto < len(fila) else ""
        if cod:
            resultado[cod] += parse_num(monto)
    return resultado

@app.route("/api/dashboard")
def api_dashboard():
    desde_str = request.args.get("desde", "")
    hasta_str = request.args.get("hasta", "")
    desde = parse_fecha(desde_str)
    hasta = parse_fecha(hasta_str)

    ventas_ws, gastos_ws, cobros_ws, _ = get_sheets()
    todos       = ventas_ws.get_all_values()
    todos_gasto = gastos_ws.get_all_values()
    todos_cobros = cobros_ws.get_all_values()

    if len(todos) < 2:
        return jsonify({"sin_datos": True})

    # Precalcular cobros por COD_ITEM (todos, sin filtro de fecha)
    cobros_por_item = calcular_cobros_por_item(todos_cobros)

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
        total_v   = parse_num(g(12))
        cod_item  = g(6)
        # cobrado real = suma de todos los cobros vinculados a este ítem (sin filtro de fecha)
        cobrado_item = cobros_por_item.get(cod_item, 0.0) if cod_item else 0.0
        cobrado_item = min(cobrado_item, total_v)  # no puede superar el total
        debe_real    = max(0.0, total_v - cobrado_item)
        filas.append({
            "fecha":     fecha,
            "cliente":   g(3),
            "tipo":      g(5),
            "cod_item":  cod_item,
            "categoria": g(7),
            "total":     total_v,
            "cobrado":   cobrado_item,
            "debe":      debe_real,
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

    # ── Leer cobros del mismo período ─────────────────────────────────────────
    cobros_list = []
    for row in todos_cobros[1:]:
        if not any(row):
            continue
        def gc(i, r=row): return r[i].strip() if i < len(r) else ""
        fecha_c = parse_fecha(gc(1))
        if not fecha_c:
            continue
        if desde and fecha_c < desde:
            continue
        if hasta and fecha_c > hasta:
            continue
        cobros_list.append({
            "fecha":     fecha_c,
            "cliente":   gc(3),
            "monto":     parse_num(gc(4)),
            "efectivo":  parse_num(gc(5)),
            "yape":      parse_num(gc(6)),
            "plin":      parse_num(gc(7)),
            "giro":      parse_num(gc(8)),
            "cod_item":  gc(10),
            "categoria": gc(11),
        })

    if not filas:
        return jsonify({
            "ventas_total": 0, "cobrado_total": 0, "pendiente_total": 0,
            "ticket_promedio": 0, "tasa_cobro": 0, "num_atenciones": 0,
            "num_clientes": 0, "num_promociones": 0, "total_gastos": 0,
            "balance_neto": 0, "ef_efectivo": 0, "ef_yape": 0, "ef_plin": 0, "ef_giro": 0,
            "pct_tratamientos": 0, "pct_productos": 0,
            "por_mes": [], "top_clientes": [], "por_categoria": [], "recientes": [],
            "cobros_recientes": [],
            "cobros_ef_efectivo": 0, "cobros_ef_yape": 0, "cobros_ef_plin": 0, "cobros_ef_giro": 0,
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
    # balance neto usa cobros reales recibidos en el período (no cobrado por venta)
    cobros_periodo_total = sum(c["monto"] for c in cobros_list)
    balance_neto    = cobros_periodo_total - total_gastos

    # ── Métodos de pago (de la hoja Cobros, período filtrado) ─────────────────
    ef_efectivo = sum(c["efectivo"] for c in cobros_list)
    ef_yape     = sum(c["yape"]     for c in cobros_list)
    ef_plin     = sum(c["plin"]     for c in cobros_list)
    ef_giro     = sum(c["giro"]     for c in cobros_list)

    # ── Tratamientos vs Productos ─────────────────────────────────────────────
    total_tratamientos = sum(f["total"] for f in filas if f["tipo"] == "Tratamiento")
    total_productos    = sum(f["total"] for f in filas if f["tipo"] == "Producto")
    total_otros        = ventas_total - total_tratamientos - total_productos

    # ── Ventas por mes (con cobrado real y pendiente real) ────────────────────
    meses_data = defaultdict(lambda: {"total": 0.0, "cobrado": 0.0, "debe": 0.0})
    for f in filas:
        k = f["fecha"].strftime("%Y-%m")
        meses_data[k]["total"]   += f["total"]
        meses_data[k]["cobrado"] += f["cobrado"]  # ya es cobrado real
        meses_data[k]["debe"]    += f["debe"]      # ya es pendiente real
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

    # ── Cobros: recientes ─────────────────────────────────────────────────────
    # ef_* ya calculados arriba desde cobros_list, reutilizamos
    cobros_ef_efectivo = ef_efectivo
    cobros_ef_yape     = ef_yape
    cobros_ef_plin     = ef_plin
    cobros_ef_giro     = ef_giro
    cobros_recientes_sorted = sorted(cobros_list, key=lambda x: x["fecha"], reverse=True)[:10]
    cobros_recientes_out = []
    for c in cobros_recientes_sorted:
        metodos = [k for k, v in [("Efectivo", c["efectivo"]), ("Yape", c["yape"]),
                                   ("Plin", c["plin"]), ("Giro", c["giro"])] if v > 0]
        cobros_recientes_out.append({
            "fecha":     c["fecha"].strftime("%d/%m/%Y"),
            "cliente":   c["cliente"],
            "monto":     round(c["monto"], 2),
            "metodo":    " + ".join(metodos) if metodos else "—",
            "categoria": c["categoria"],
            "cod_item":  c["cod_item"],
        })

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
        # Métodos de pago (ventas)
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
        # Cobros
        "cobros_ef_efectivo": round(cobros_ef_efectivo, 2),
        "cobros_ef_yape":     round(cobros_ef_yape, 2),
        "cobros_ef_plin":     round(cobros_ef_plin, 2),
        "cobros_ef_giro":     round(cobros_ef_giro, 2),
        "cobros_recientes":   cobros_recientes_out,
    })

if __name__ == "__main__":
    app.run(debug=True)

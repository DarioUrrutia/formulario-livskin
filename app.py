from flask import Flask, render_template, request, redirect, url_for, flash
import gspread
from google.oauth2.service_account import Credentials
import os
import json

app = Flask(__name__)
app.secret_key = "livskin2024"

SHEET_ID = "1o4Vh4RN_Qfpaz8g08MReqgE3mFX0EGVSI5A69OsHB5g"

ENCABEZADOS = [
    "FECHA", "AREA", "TIPO", "CATEGORIA", "ZONA/CANTIDAD/ENVASE",
    "TELEFONO", "PROXIMA CITA", "MONEDA", "TOTAL", "EFECTIVO",
    "YAPE", "PLIN", "GIRO", "DEBE", "PAGO SALDO", "CUMPLEANOS"
]

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Usar variable de entorno en Render, o archivo local en desarrollo
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(
            "livskin-formulario-56d6d2a0eac6.json", scopes=scopes
        )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet

def inicializar_sheet(sheet):
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "FECHA":
        sheet.insert_row(ENCABEZADOS, 1)

@app.route("/", methods=["GET", "POST"])
def formulario():
    if request.method == "POST":
        datos = [
            request.form.get("fecha", ""),
            request.form.get("area", ""),
            request.form.get("tipo", ""),
            request.form.get("categoria", ""),
            request.form.get("zona_cantidad_envase", ""),
            request.form.get("telefono", ""),
            request.form.get("proxima_cita", ""),
            request.form.get("moneda", ""),
            request.form.get("total", ""),
            request.form.get("efectivo", ""),
            request.form.get("yape", ""),
            request.form.get("plin", ""),
            request.form.get("giro", ""),
            request.form.get("debe", ""),
            request.form.get("pago_saldo", ""),
            request.form.get("cumpleanos", ""),
        ]

        sheet = get_sheet()
        inicializar_sheet(sheet)
        sheet.append_row(datos)

        flash("Registro guardado correctamente.")
        return redirect(url_for("formulario"))

    return render_template("formulario.html")

if __name__ == "__main__":
    app.run(debug=True)

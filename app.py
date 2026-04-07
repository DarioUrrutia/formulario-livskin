from flask import Flask, render_template, request, redirect, url_for, flash
import openpyxl
import os

app = Flask(__name__)
app.secret_key = "livskin2024"

ARCHIVO_EXCEL = "Datos_Livskin.xlsx"

ENCABEZADOS = [
    "FECHA", "AREA", "TIPO", "CATEGORIA", "ZONA/CANTIDAD/ENVASE",
    "TELEFONO", "PROXIMA CITA", "MONEDA", "TOTAL", "EFECTIVO",
    "YAPE", "PLIN", "GIRO", "DEBE", "PAGO SALDO", "CUMPLEANOS"
]

def inicializar_excel():
    if not os.path.exists(ARCHIVO_EXCEL):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Registros"
        ws.append(ENCABEZADOS)
        wb.save(ARCHIVO_EXCEL)

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

        inicializar_excel()
        wb = openpyxl.load_workbook(ARCHIVO_EXCEL)
        ws = wb.active
        ws.append(datos)
        wb.save(ARCHIVO_EXCEL)

        flash("Registro guardado correctamente.")
        return redirect(url_for("formulario"))

    return render_template("formulario.html")

if __name__ == "__main__":
    inicializar_excel()
    app.run(debug=True)

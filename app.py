from flask import Flask, render_template, request, redirect, url_for, flash
import openpyxl
import os

app = Flask(__name__)
app.secret_key = "livskin2024"

ARCHIVO_EXCEL = "Datos_Livskin.xlsx"

def inicializar_excel():
    if not os.path.exists(ARCHIVO_EXCEL):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pacientes"
        ws.append(["NOMBRE", "APELLIDO", "TRATAMIENTO", "COSTO"])
        wb.save(ARCHIVO_EXCEL)

@app.route("/", methods=["GET", "POST"])
def formulario():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        tratamiento = request.form.get("tratamiento", "").strip()
        costo = request.form.get("costo", "").strip()

        if not nombre:
            flash("El campo NOMBRE es obligatorio.")
            return redirect(url_for("formulario"))

        inicializar_excel()
        wb = openpyxl.load_workbook(ARCHIVO_EXCEL)
        ws = wb.active
        ws.append([nombre, apellido, tratamiento, costo])
        wb.save(ARCHIVO_EXCEL)

        flash(f"Datos de {nombre} {apellido} guardados correctamente.")
        return redirect(url_for("formulario"))

    return render_template("formulario.html")

if __name__ == "__main__":
    inicializar_excel()
    app.run(debug=True)

"""
backup_db.py — Backup diario de la base de datos (Google Sheets → CSVs en Google Drive)

Uso manual:
    py tools/backup_db.py

Uso automático (Windows Task Scheduler):
    Ver instrucciones al final de este archivo.

Cada ejecución crea una carpeta con timestamp en:
    G:/Il mio Drive/Livskin/Database - Formulario Livskin/Db - Produccion/Backups/YYYY-MM-DD/

Dentro: un CSV por cada hoja (Ventas.csv, Pagos.csv, Gastos.csv, Clientes.csv, Listas.csv).
Retención: mantiene los últimos 30 backups, borra los más antiguos automáticamente.
"""

import os
import sys
import csv
import json
import shutil
from datetime import datetime, date

# Agregar el directorio raíz del proyecto al path para reusar credenciales
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ── Configuración ────────────────────────────────────────────────────────────
BACKUP_DIR = r"G:\Il mio Drive\Livskin\Database - Formulario Livskin\Db - Produccion\Backups"
SHEET_ID   = "1o4Vh4RN_Qfpaz8g08MReqgE3mFX0EGVSI5A69OsHB5g"
HOJAS      = ["Ventas", "Pagos", "Gastos", "Clientes", "Listas"]
MAX_BACKUPS = 30  # mantener los últimos N backups

# ── Google Sheets auth (misma lógica que app.py) ─────────────────────────────
def get_spreadsheet():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        # Buscar archivo JSON de service account en la raíz del proyecto
        sa_file = None
        for f in os.listdir(PROJECT_ROOT):
            if f.startswith("livskin-formulario") and f.endswith(".json"):
                sa_file = os.path.join(PROJECT_ROOT, f)
                break
        if not sa_file:
            print("ERROR: No se encontró GOOGLE_CREDENTIALS ni archivo de service account.")
            sys.exit(1)
        creds = Credentials.from_service_account_file(sa_file, scopes=scopes)

    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)


def backup():
    today_str = date.today().strftime("%Y-%m-%d")
    backup_path = os.path.join(BACKUP_DIR, today_str)

    # Si ya existe backup de hoy, no duplicar
    if os.path.exists(backup_path):
        print(f"Ya existe backup de hoy: {backup_path}")
        print("Si quieres forzar, borra la carpeta manualmente y vuelve a ejecutar.")
        return

    # Verificar que la carpeta de destino existe
    if not os.path.exists(BACKUP_DIR):
        print(f"ERROR: No se encontró la carpeta de backups: {BACKUP_DIR}")
        print("Verifica que Google Drive esté sincronizado y la ruta sea correcta.")
        sys.exit(1)

    print(f"Conectando a Google Sheets...")
    spreadsheet = get_spreadsheet()

    os.makedirs(backup_path)
    print(f"Carpeta creada: {backup_path}")

    total_filas = 0
    for nombre_hoja in HOJAS:
        try:
            ws = spreadsheet.worksheet(nombre_hoja)
            datos = ws.get_all_values()
            archivo = os.path.join(backup_path, f"{nombre_hoja}.csv")
            with open(archivo, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerows(datos)
            filas = len(datos) - 1 if len(datos) > 1 else 0
            total_filas += filas
            print(f"  OK {nombre_hoja}: {filas} filas guardadas")
        except Exception as e:
            print(f"  ERROR {nombre_hoja}: {e}")

    # Escribir metadata del backup
    meta_path = os.path.join(backup_path, "_backup_info.txt")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"Fecha: {today_str}\n")
        f.write(f"Hora: {datetime.now().strftime('%H:%M:%S')}\n")
        f.write(f"Sheet ID: {SHEET_ID}\n")
        f.write(f"Hojas: {', '.join(HOJAS)}\n")
        f.write(f"Total filas: {total_filas}\n")

    print(f"\nBackup completado: {total_filas} filas totales en {backup_path}")

    # ── Retención: borrar backups antiguos ───────────────────────────────────
    limpiar_backups_antiguos()


def limpiar_backups_antiguos():
    """Mantiene solo los últimos MAX_BACKUPS backups, borra los más antiguos."""
    carpetas = []
    for nombre in os.listdir(BACKUP_DIR):
        ruta = os.path.join(BACKUP_DIR, nombre)
        if os.path.isdir(ruta) and len(nombre) == 10:
            # Verificar que sea formato YYYY-MM-DD
            try:
                datetime.strptime(nombre, "%Y-%m-%d")
                carpetas.append(nombre)
            except ValueError:
                continue

    carpetas.sort()  # orden cronológico

    if len(carpetas) > MAX_BACKUPS:
        a_borrar = carpetas[:len(carpetas) - MAX_BACKUPS]
        for nombre in a_borrar:
            ruta = os.path.join(BACKUP_DIR, nombre)
            shutil.rmtree(ruta)
            print(f"  Backup antiguo eliminado: {nombre}")
        print(f"  Retención: {len(carpetas) - len(a_borrar)}/{MAX_BACKUPS} backups")


if __name__ == "__main__":
    backup()


# ══════════════════════════════════════════════════════════════════════════════
# INSTRUCCIONES PARA BACKUP DIARIO AUTOMÁTICO (Windows Task Scheduler)
# ══════════════════════════════════════════════════════════════════════════════
#
# 1. Abrir "Programador de tareas" (buscar en Start)
# 2. Click "Crear tarea básica..."
# 3. Nombre: "Backup Livskin DB"
# 4. Trigger: Diariamente → elegir hora (ej: 23:00)
# 5. Acción: "Iniciar un programa"
#    - Programa: C:\Users\JeanUrrutia\ProyectosClaude\venv\Scripts\python.exe
#    - Argumentos: tools\backup_db.py
#    - Iniciar en: C:\Users\JeanUrrutia\ProyectosClaude
# 6. Marcar: "Abrir el diálogo de propiedades" → Finalizar
# 7. En propiedades:
#    - General → "Ejecutar tanto si el usuario inició sesión como si no"
#    - Condiciones → Desmarcar "Iniciar solo si el equipo usa AC"
#    - Configuración → Marcar "Ejecutar tarea a la mayor brevedad si no se
#      inició en el momento programado" (para que corra si la PC estaba apagada)
#
# Para verificar que funciona:
#    - Click derecho en la tarea → "Ejecutar"
#    - Revisar la carpeta de backups en Google Drive
#
# ══════════════════════════════════════════════════════════════════════════════

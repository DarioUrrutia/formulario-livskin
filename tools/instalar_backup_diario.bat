@echo off
:: ═══════════════════════════════════════════════════════════════
:: Instala el backup diario de Livskin a las 2:00 AM (hora Peru)
:: Ejecutar como Administrador (click derecho > Ejecutar como admin)
:: ═══════════════════════════════════════════════════════════════

schtasks /create ^
  /tn "Backup Livskin DB" ^
  /tr "C:\Users\JeanUrrutia\AppData\Local\Microsoft\WindowsApps\python.exe C:\Users\JeanUrrutia\ProyectosClaude\tools\backup_db.py" ^
  /sc daily ^
  /st 02:00 ^
  /rl HIGHEST ^
  /f

if %errorlevel% == 0 (
    echo.
    echo === Tarea creada correctamente ===
    echo Backup diario a las 2:00 AM
    echo Destino: G:\Il mio Drive\Livskin\...\Backups\
    echo.
    echo Para verificar: schtasks /query /tn "Backup Livskin DB"
) else (
    echo.
    echo === ERROR: Ejecuta este archivo como Administrador ===
    echo Click derecho sobre el archivo y "Ejecutar como administrador"
)

pause

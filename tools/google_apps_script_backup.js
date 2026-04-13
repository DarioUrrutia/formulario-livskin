/**
 * ═══════════════════════════════════════════════════════════════════
 * BACKUP AUTOMÁTICO — Google Apps Script
 * ═══════════════════════════════════════════════════════════════════
 *
 * Este script corre DENTRO de Google (gratis, sin servidor, sin PC encendida).
 * Copia la Sheet completa a la carpeta de Backups en Google Drive.
 *
 * INSTALACIÓN (una sola vez):
 *
 * 1. Abre la Google Sheet de Livskin en el navegador
 * 2. Menu: Extensiones > Apps Script
 * 3. Borra el contenido por defecto y pega TODO este archivo
 * 4. Click en "Guardar" (icono de diskette o Ctrl+S)
 * 5. Ejecuta la función "backupDiario" manualmente una vez:
 *    - Selecciona "backupDiario" en el dropdown de funciones
 *    - Click en "Ejecutar" (triangulo play)
 *    - Autoriza los permisos cuando te lo pida
 *    - Verifica que aparezca el backup en la carpeta de Backups
 * 6. Configura el trigger automático:
 *    - Click en el icono de reloj (Activadores / Triggers) en el panel izquierdo
 *    - Click en "+ Añadir activador"
 *    - Configurar:
 *        Función: backupDiario
 *        Evento: Basado en tiempo
 *        Tipo: Temporizador diario
 *        Hora: 2:00 a 3:00 (hora de tu cuenta Google, que debería ser Peru)
 *    - Guardar
 *
 * Listo. Cada día a las ~2 AM se crea un backup automático.
 * ═══════════════════════════════════════════════════════════════════
 */

// ── CONFIGURACIÓN ──────────────────────────────────────────────────
var BACKUP_FOLDER_ID = '1bhi0EaXZ25WweTz0JAfvGWxUbpF9zzmz';  // Carpeta "Backups" en Drive
var MAX_BACKUPS = 30;  // Mantener los últimos 30 backups
// ───────────────────────────────────────────────────────────────────

function backupDiario() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var hoy = Utilities.formatDate(new Date(), 'America/Lima', 'yyyy-MM-dd');
  var nombreBackup = 'Backup Livskin ' + hoy;

  var folder = DriveApp.getFolderById(BACKUP_FOLDER_ID);

  // Verificar si ya existe backup de hoy
  var existentes = folder.getFilesByName(nombreBackup);
  if (existentes.hasNext()) {
    Logger.log('Ya existe backup de hoy: ' + nombreBackup);
    return;
  }

  // Copiar la spreadsheet completa
  var copia = DriveApp.getFileById(ss.getId()).makeCopy(nombreBackup, folder);
  Logger.log('Backup creado: ' + nombreBackup + ' (ID: ' + copia.getId() + ')');

  // Retención: borrar backups antiguos
  limpiarBackupsAntiguos(folder);
}

function limpiarBackupsAntiguos(folder) {
  var archivos = folder.getFiles();
  var backups = [];

  while (archivos.hasNext()) {
    var file = archivos.next();
    if (file.getName().indexOf('Backup Livskin') === 0) {
      backups.push({
        file: file,
        fecha: file.getDateCreated()
      });
    }
  }

  // Ordenar por fecha descendente
  backups.sort(function(a, b) { return b.fecha - a.fecha; });

  // Borrar los que exceden MAX_BACKUPS
  if (backups.length > MAX_BACKUPS) {
    for (var i = MAX_BACKUPS; i < backups.length; i++) {
      Logger.log('Eliminando backup antiguo: ' + backups[i].file.getName());
      backups[i].file.setTrashed(true);
    }
    Logger.log('Retención: ' + MAX_BACKUPS + '/' + backups.length + ' backups');
  }
}

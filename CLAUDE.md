# CLAUDE.md — Instrucciones para Claude Code

> Este archivo es leído automáticamente por Claude Code al inicio de cada sesión que abra este directorio. Define el contexto, las convenciones y las reglas operativas del proyecto.

---

## Contexto del proyecto

**formulario-livskin** es la columna vertebral operativa y contable de **Livskin Professional Skincare**: registra ventas, tratamientos, productos, gastos, cobros, créditos y anticipos. Toda la información financiera del negocio vive en una sola Google Sheet, leída y escrita por una app Flask alojada en Render.

**Restricciones críticas:**

- Mucho dinero depende de este sistema. Las decisiones priorizan **integridad de datos > velocidad de feature**.
- Debe operar de forma continua **al menos 3 años**.
- En el horizonte 1-2 años, el sistema migrará a una infraestructura más robusta con techo de costo de **$120 USD anuales**.
- Esa migración debe ser **sin fricción**: cero pérdida de datos, cero retraining del staff, rollback siempre disponible.

**Plan completo de mantenimiento:** [docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md](docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md) — léelo antes de proponer cambios estructurales.

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.13.13 + Flask 3.1.3 |
| Datos | Google Sheets (gspread 6.2.1) — 5 hojas: `Ventas`, `Gastos`, `Cobros`, `Clientes`, `Listas` |
| Auth Google | Service Account (google-auth 2.49.1) |
| Servidor producción | gunicorn 25.3.0 con `gunicorn.conf.py` (workers=1, timeout=120s, max_requests=200) |
| Hosting | Render.com |
| Frontend | HTML + JS vanilla en `templates/formulario.html` |
| Cache | En memoria por proceso, TTL 90 s, invalidación automática tras escrituras |
| Keep-alive | Endpoint `/ping` + cron-job.org cada 14 min (evita cold start de Render) |

Todas las versiones están **pinneadas** en [requirements.txt](requirements.txt). Python en [.python-version](.python-version) (formato que Render respeta automáticamente; el viejo `runtime.txt` de Heroku NO funciona en Render moderno).

---

## Comandos comunes

```bash
# Setup en PC nueva (ver README.md para detalle completo)
py -3.13 -m venv venv && venv/Scripts/activate && pip install -r requirements.txt

# Correr local (Flask development server)
py app.py
# → http://localhost:5000

# Correr local como producción (gunicorn con la misma config que Render)
gunicorn app:app --config gunicorn.conf.py

# Verificar deps sin instalar nada
pip check

# Auditoría de seguridad
pip-audit -r requirements.txt

# Sincronizar planes desde el global de Claude al folder del proyecto
py tools/sync_claude_plans.py

# Backup del estado de Claude (memoria, sesiones, planes) para portabilidad
py tools/backup_claude_state.py

# Restaurar estado de Claude (al cambiar de PC)
py tools/restore_claude_state.py path/a/backup.zip

# Importar datos historicos del CSV (one-shot, ya ejecutado)
py tools/importar_csv.py

# Migracion legacy de codigos (one-shot, ya ejecutado)
py tools/migrar_datos.py
```

---

## Reglas operativas (IMPORTANTES)

### R1. Reproducibilidad: nunca instalar deps sin pinear

**Nunca** correr `pip install -U` sin actualizar `requirements.txt` con la versión exacta resultante. Cada dependencia que entra al proyecto debe estar pinneada con `==X.Y.Z` en `requirements.txt`. Procedimiento de actualización en [README.md](README.md#cómo-actualizar-dependencias).

**Por qué:** Sin pinning estricto, un redeploy de Render puede instalar versiones nuevas que rompan la app silenciosamente. Esto ya pasó en otros proyectos del usuario.

### R2. Planes: copiar SIEMPRE al folder antes de salir de plan mode

Cuando uses plan mode y termines un plan:

1. El harness escribe el plan en `~/.claude/plans/<random-name>.md` (path global, fuera del proyecto).
2. **Antes** de llamar a `ExitPlanMode`, **copia el archivo** a `docs/plans/<nombre-descriptivo>.md` usando el tool `Write`. El nombre debe ser descriptivo (no el random del harness): por ejemplo `PLAN_MIGRACION_POSTGRES.md`, no `compressed-squishing-babbage.md`.
3. Después llama a `ExitPlanMode`.

Como red de seguridad adicional, el hook `PostToolUse` configurado en [.claude/settings.json](.claude/settings.json) corre `python tools/sync_claude_plans.py` automáticamente, que detecta y copia planes huérfanos basándose en las sesiones del proyecto. Pero **no dependas del hook** — copia manualmente igual.

**Por qué:** Los planes en el global se mezclan con los de otros proyectos, no son versionados en git, y se pierden si formateas la PC sin backup del global. Los planes en `docs/plans/` viajan con el repo.

### R3. Credenciales: nunca commitear, siempre documentar

- `livskin-formulario-XXXX.json` (service account de Google) está gitignored. NUNCA debe entrar a git.
- Las variables de entorno reales viven en `.env` (gitignored) y en el dashboard de Render.
- El **template** de variables vive en [.env.example](.env.example) (commiteado, sin valores reales).
- Cualquier credencial debe tener backup en el gestor de contraseñas del usuario (Bitwarden / 1Password / Proton Pass).

Antes de cada commit, verificar que no se está commiteando nada sensible:
```bash
git diff --cached | grep -iE "(BEGIN PRIVATE KEY|password|secret_key.*=.*['\"][^'\"]+['\"]|api[_-]?key)"
```

### R4. `.claude/settings*.json` deben ser específicos de este proyecto

Si ves rutas en `.claude/settings.json` o `.claude/settings.local.json` que apuntan a otros usuarios (`JeanUrrutia`, otra cuenta) o a archivos que no existen en este proyecto, **bórralas**. Estos archivos se llenan automáticamente con permisos durante las sesiones, pero no deben acumular basura de proyectos anteriores.

### R5. Datos en producción: leer la sección 6 del plan de mantenimiento

Cualquier operación que toque la Google Sheet de producción debe seguir los runbooks de [docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md](docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md) §6. Hay procedimientos específicos para disaster recovery, rotación de credenciales y caída del servicio.

### R6. Cambios estructurales: siempre con red de seguridad

Antes de un refactor grande:
1. **`git fetch origin && git pull origin main`** (CRÍTICO — verificar que tu local está al día. Esto evita el desastre de mergear sobre código viejo.)
2. `git status` para confirmar que el working tree está limpio.
3. `git tag pre-<descripción>-<fecha>` (snapshot inmutable).
4. ZIP backup completo a `C:\Users\daizu\Backups\Claude Code\<fecha>\` (sin venv).
5. Branch nuevo: `git checkout -b refactor/<descripción>`.
6. Trabajar en el branch. Solo merge a main cuando esté verificado.

### R7. Múltiples computadoras: SIEMPRE pull antes de tocar nada

**Aprendido de un incidente real:** el usuario trabaja en este proyecto desde **dos computadoras distintas**, y a veces hace commits desde una sin sincronizarlos a la otra. Si abrís Claude Code en este directorio y empezás a modificar archivos sin hacer `git pull origin main` primero, podés acabar trabajando sobre código viejo y sobreescribiendo trabajo importante al hacer push.

**Procedimiento obligatorio al inicio de cualquier sesión que vaya a modificar archivos:**

```bash
git fetch origin
git status                              # ver si estás atrás del remoto
git log main..origin/main --oneline     # ver commits que NO tenés
git pull origin main                    # bajar los commits faltantes
```

Si `git log main..origin/main` muestra commits que vos no reconocés, **PARÁ y preguntá al usuario** si esos commits son suyos (de otra PC) antes de tocar nada. Nunca asumas.

---

## Estructura del proyecto

```
formulario-livskin/
├── app.py                       # Flask backend (rutas, lógica de Sheets, cache)
├── gunicorn.conf.py             # Config de gunicorn para producción (Render)
├── templates/
│   └── formulario.html          # UI completa (5 tabs: Venta/Gasto/Cobro/Cliente/Dashboard)
├── static/                      # logo.png, etc.
├── tools/                       # Scripts utilitarios
│   ├── sync_claude_plans.py     # Copia planes del global al folder
│   ├── backup_claude_state.py   # Backup memoria/sesiones/planes para portabilidad
│   ├── restore_claude_state.py  # Restaurar estado de Claude en PC nueva
│   ├── importar_csv.py          # Migración de datos históricos (Inventario VF.csv)
│   └── migrar_datos.py          # Migración legacy (asignación de COD_CLIENTE/COD_ITEM)
├── docs/                        # Documentación operativa
│   ├── plans/                   # Planes copiados desde Claude (regla R2)
│   │   └── _synced/             # Sync automático del hook (no editar a mano)
│   └── runbooks/                # Procedimientos de emergencia
├── requirements.txt             # Dependencias PINNEADAS con ==
├── .python-version              # Python 3.13.13 (Render lo respeta)
├── render.yaml                  # Configuración de Render (gunicorn --config gunicorn.conf.py)
├── .env.example                 # Template de variables de entorno
├── .gitignore
├── CLAUDE.md                    # Este archivo
└── README.md                    # Documentación funcional completa del sistema
```

## Hojas de Google Sheets (estructura)

| Hoja | Para qué |
|---|---|
| **Ventas** | Registro de atenciones (tratamientos, productos, certificados) con cliente, fecha, métodos de pago, descuentos, ítems gratis, COD_ITEM, etc. |
| **Gastos** | Pagos hacia afuera (RR.HH, proveedores, servicios, insumos) |
| **Cobros** | Pagos posteriores con `COD_COBRO` único y vinculados a `COD_ITEM` específico de Ventas |
| **Clientes** | Catálogo de clientes con `LIVCLIENT####` |
| **Listas** ⭐ | **Configuración dinámica del formulario.** Columnas: `LISTA`, `VALOR`. Valores de `LISTA`: `tipo`, `cat_Tratamiento`, `cat_Producto`, `area`, `precio_<Categoría>`. **Editás esta hoja → el formulario se actualiza automáticamente sin tocar código.** |

---

## Cosas que NO debes hacer en este proyecto

- ❌ Instalar deps sin pinear (R1).
- ❌ Salir de plan mode sin copiar el plan al folder (R2).
- ❌ Commitear credenciales o `.env` (R3).
- ❌ Dejar rutas de otros usuarios en `.claude/settings*.json` (R4).
- ❌ Refactor grande sin tag + ZIP + branch (R6).
- ❌ Usar `git push --force` a `main`. Nunca.
- ❌ Tocar la Google Sheet de producción sin backup previo. Ver runbook §6.
- ❌ Asumir que algo "es solo un cambio menor" en código que toca cobros/saldos. Cualquier cambio en cálculos financieros requiere validación manual antes de subir.

## Cosas que SIEMPRE debes hacer

- ✅ Leer este `CLAUDE.md` y el plan de mantenimiento al inicio de cualquier sesión.
- ✅ Pinear cada nueva dependencia.
- ✅ Copiar manualmente cada plan al folder antes de exit plan mode.
- ✅ Sugerir backup antes de cualquier cambio grande.
- ✅ Verificar `.claude/settings*.json` antes de commit (no debe haber rutas extranjeras).
- ✅ Cuando estés inseguro, **preguntar antes de hacer**. Mucho dinero depende de esto.

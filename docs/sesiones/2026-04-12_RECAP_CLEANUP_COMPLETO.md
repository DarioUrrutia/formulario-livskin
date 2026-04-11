# Recap de la sesión del 2026-04-11/12 — Cleanup self-contained completo

> **Documento generado al final de la sesión**, como recap definitivo de todo lo que pasó. Sirve como punto de entrada para cualquier sesión futura (humana o de Claude) que necesite entender qué se hizo, por qué, y qué viene a continuación.
>
> **Si sos Claude leyendo esto en una sesión futura:** este es el contexto completo del cleanup. Después de leer `CLAUDE.md` y la memoria del proyecto, leer este archivo te da el panorama histórico completo.
>
> **Si sos vos (Darío) volviendo en unos días o meses:** este archivo es tu mapa mental. Léelo si querés acordarte qué se hizo y cuáles son los próximos pasos.

---

## 📍 1. De dónde veníamos (estado inicial, antes del cleanup)

Cuando se abrió la sesión el 2026-04-11 ~15:00, el proyecto estaba en este estado:

| Aspecto | Estado real al inicio |
|---|---|
| **Código local** | Atrasado **28 commits** detrás del remoto (sin saberlo) — había cambios desde la otra PC nunca bajados |
| **`requirements.txt`** | Sin pinear: `flask`, `gspread`, `google-auth`, `gunicorn` (sin versiones) |
| **Python local** | 3.14.4 (recién instalado, muy nuevo) |
| **Python en producción (Render)** | Lo que Render decidiera (default ~3.11/3.12). **Divergencia local-producción** silenciosa. |
| **`runtime.txt`** | No existía |
| **`.python-version`** | No existía |
| **`CLAUDE.md`** | No existía |
| **`docs/plans/`** | No existía |
| **`tools/`** | No existía. Los scripts `importar_csv.py` y `migrar_datos.py` colgando en la raíz |
| **`.env.example`** | No existía |
| **`.gitignore`** | Mínimo: 7 líneas, varias entradas legacy (`Datos_Livskin.xlsx`, `formulario_livskin.py`) que ya no aplicaban |
| **`.claude/settings*.json`** | **Contaminados con rutas de otro usuario** (`C:\Users\JeanUrrutia\ProyectosClaude\`) — heredado de cuando el proyecto fue copiado de otro folder |
| **Memoria de Claude del proyecto** | **En carpeta huérfana** `~/.claude/projects/c--Users-daizu-Claude-Code/` en lugar del directorio correcto. Cada nueva sesión empezaba sin contexto |
| **Backups del proyecto** | Ninguno fuera del repo de GitHub |
| **Plan de mantenimiento** | Solo en la cabeza del usuario, no documentado |
| **README.md** | Básico (~60 líneas), sin instrucciones de setup en PC nueva |

### Riesgos estructurales (sin documentar entonces)

| Riesgo | Severidad |
|---|---|
| Sin backup externo de Google Sheets (solo historial nativo de 30 días) | 🔴 Crítico |
| `secret_key="livskin2024"` hardcoded en `app.py:10`, visible en GitHub | 🔴 Crítico |
| Sin autenticación en el formulario | 🔴 Crítico |
| Sin tests automatizados | 🟠 Alto |
| Sin CI/CD | 🟠 Alto |
| Sin monitoreo de uptime ni alertas | 🟠 Alto |
| Sin validación de inputs en backend | 🟠 Alto |
| Bus factor = 1 | 🟡 Medio |
| Sin logs persistentes | 🟡 Medio |
| Documentación mínima | 🟢 Bajo |

---

## 🎯 2. Lo que se debía hacer — Plan de mantenimiento de 3 años

La pregunta inicial del usuario fue:

> *"qué se necesita para que esta app se mantenga en el tiempo, una guía de mantenimiento, cosas que se deberían implementar para conseguir su funcionamiento continuo por al menos 3 años, asegurar los datos. Mucho dinero dependerá de eso."*

Eso desencadenó todo el plan de 3 años, documentado en [docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md](../plans/PLAN_MANTENIMIENTO_3_ANOS.md). Resumen:

### 🔴 P0 — Hacer YA (esta semana, riesgo de pérdida de dinero)

| # | Tarea | Por qué |
|---|---|---|
| **P0-1** | Backup automático diario de Google Sheets fuera de Google | Si Google bloquea/borra la cuenta o alguien borra filas, se pierde todo. El historial nativo solo guarda 30 días |
| **P0-2** | Mover `secret_key` a variable de entorno | Hoy el valor `"livskin2024"` está públicamente en GitHub. Cualquiera puede forjar sesiones |
| **P0-3** | Monitor de uptime con alerta (UptimeRobot) | Hoy no hay forma de saber si la app está caída salvo abrirla manualmente |

### 🟠 P1 — Hacer este mes

| # | Tarea | Por qué |
|---|---|---|
| **P1-1** | Autenticación básica del formulario | Sin auth, cualquiera con la URL puede contaminar la contabilidad |
| **P1-2** | Validación de inputs en backend | Un dedazo "100O" en lugar de "1000" rompe el dashboard |
| **P1-3** | Política de rotación de service account key (cada 90 días) | Si la key se filtra, no hay procedimiento documentado |
| **P1-4** | Mover credenciales locales a `~/.config/livskin/` | Hoy el JSON está en el directorio del proyecto (gitignored pero expuesto en backups) |

### 🟡 P2 — Hacer este trimestre

| # | Tarea | Por qué |
|---|---|---|
| **P2-1** | Suite de tests mínima (pytest + mock gspread) | Sin tests, cada deploy es una apuesta |
| **P2-2** | CI/CD con GitHub Actions | Hoy el push directo a main puede romper producción |
| **P2-3** | Logs persistentes (Better Stack o similar) | Cuando algo falla en prod, no hay forma de auditar qué pasó |
| **P2-4** | Script de validación de integridad financiera | Detectar desfases entre Ventas, Cobros y DEBE antes de que el dashboard mienta |

### 🟢 P3 — Hacer este año

| # | Tarea |
|---|---|
| **P3-1** | Cache de lectura para reducir llamadas a Sheets API |
| **P3-2** | Migrar de Render free a Render Starter ($7/mes) — elimina cold start |
| **P3-3** | Documentación operativa + segundo administrador (resolver bus factor) |

### 🎯 Año 2 — Migración sin fricción

En el horizonte 1-2 años, **migrar a una infraestructura más robusta sin pasar de $120 USD/año**:

- **Postgres** (Supabase/Neon free tier) como fuente de verdad
- **Sheets como espejo read-only** sincronizado cada 5 minutos
- **Hosting nuevo** (Fly.io / Railway / Render Starter)
- **6 fases con rollback en cada una** — cero downtime, cero retraining, cero pérdida de datos
- **Pre-requisito:** todo el Año 1 hecho (P0+P1+P2)

> **El detalle completo de riesgos, runbooks, costos, fases y checklists** está en `docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md` (634 líneas).

---

## ✅ 3. Qué se hizo en esta sesión (cleanup completo)

### Cleanup self-contained aplicado en main

1. **Limpieza de contaminación** del usuario `JeanUrrutia` en `.claude/settings*.json`
2. **Pinneo de las 25 dependencias** con `==` en `requirements.txt`
3. **Migración de Python 3.12.7 → 3.13.13** (sweet spot: bugfix activo hasta oct 2027, security hasta oct 2029)
4. **Creación de `CLAUDE.md`** con 7 reglas operativas (R7 nueva por incidente real)
5. **Plan de mantenimiento 3 años** en `docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md` (634 líneas)
6. **3 scripts en `tools/`** para portabilidad: `sync_claude_plans.py`, `backup_claude_state.py`, `restore_claude_state.py`
7. **Hook PostToolUse** en `.claude/settings.json` para sync automático de planes
8. **Migración de memoria** del proyecto al directorio correcto + actualización al estado real
9. **Detección y resolución** de los 28 commits perdidos del remoto (incidente que generó la regla R7)
10. **Re-aplicación del cleanup** sobre la base nueva sin perder nada
11. **Descubrimiento crítico**: Render no usa `runtime.txt`, migración a `.python-version`
12. **README rescrito** (125 → 270 líneas) con setup completo paso a paso
13. **Push a GitHub** y deploy exitoso en Render con Python 3.13.13
14. **5 ZIPs de backup** en Google Drive (verificados con SHA-256)
15. **Tag `pre-cleanup-2026-04-11`** como ancla de seguridad
16. **Branch viejo `refactor/self-contained-environment`** preservado como referencia

### Commits hechos en main (en orden)

```
4f63e90 README setup completo + Render usa .python-version (no runtime.txt)
c47698d Cleanup self-contained: deps pinneadas, Python 3.13.13, CLAUDE.md, hooks de planes
```

### Archivos NUEVOS

- `.python-version` (Python 3.13.13)
- `.env.example`
- `CLAUDE.md`
- `docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md`
- `tools/sync_claude_plans.py`
- `tools/backup_claude_state.py`
- `tools/restore_claude_state.py`

### Archivos MODIFICADOS

- `requirements.txt` (25 deps pinneadas)
- `README.md` (125 → 270 líneas)
- `.gitignore` (reforzado)
- `.claude/settings.json` (limpio + hook)
- `.claude/settings.local.json` (vaciado)

### Archivos MOVIDOS (con `git mv`, preserva historial)

- `importar_csv.py` → `tools/importar_csv.py`
- `migrar_datos.py` → `tools/migrar_datos.py`

---

## 📦 4. Nuevos proyectos: ¿estructura automática?

**Respuesta corta: NO automáticamente. Pero hay 3 caminos para hacerlo fácil.**

### Cómo funciona Claude Code con proyectos

Cuando se abre Claude Code en una carpeta, lo que **automáticamente** pasa:

| Cosa | Ubicación | Per-proyecto? |
|---|---|---|
| Memoria del proyecto | `~/.claude/projects/<project-id>/memory/` | ✅ Sí (por path) |
| Sesiones de chat | `~/.claude/projects/<project-id>/*.jsonl` | ✅ Sí |
| Plans nativos del harness | `~/.claude/plans/*.md` | ❌ Global, mezclados con otros |
| File history (undo) | `~/.claude/file-history/` | ❌ Global |

Lo que **NO existe por default** y hay que crear/copiar manualmente en cada proyecto nuevo:

- `CLAUDE.md`, `.env.example`, `requirements.txt` pinneado
- `.python-version`
- `docs/plans/`, `docs/runbooks/`
- `tools/sync_claude_plans.py`, `tools/backup_claude_state.py`, `tools/restore_claude_state.py`
- Hook de planes en `.claude/settings.json`
- `.gitignore` reforzado

### Tres opciones para nuevos proyectos

**Opción A — Copiar manualmente** desde formulario-livskin (lo más simple, propenso a errores).

**Opción B — Crear repo template en GitHub** (lo recomendado). Marcar un repo como "Template repository" en GitHub Settings, y usar "Use this template" para crear proyectos nuevos pre-configurados.

**Opción C — Script de scaffolding** (lo más automatizado). Un `init_new_project.py` que recibe el nombre del proyecto y genera la estructura, adaptable por stack (Python/Node/Go).

> **Recomendación:** empezar con Opción B (template en GitHub). Sweet spot entre esfuerzo y beneficio.

---

## 🐍 5. Independencia de environments

**Respuesta corta: SÍ, los environments son completamente independientes por diseño.**

### Cómo funcionan los venvs

Cada proyecto tiene su propia carpeta `venv/` adentro:

```
formulario-livskin/
└── venv/                # venv DE este proyecto
    ├── Scripts/python.exe   # copia de Python 3.13.13 (~46 MB)
    └── Lib/site-packages/   # Flask, gspread, etc. solo de este proyecto

Wepscrapper_Pavimod_Gorima/
└── venv/                # venv DE este otro proyecto (independiente)
    ├── Scripts/python.exe   # otra copia de Python (puede ser otra versión)
    └── Lib/site-packages/   # pandas, streamlit, lxml, etc. solo de este
```

### Características clave

- **Aislamiento total de paquetes**: instalar Flask en uno NO afecta al otro
- **Independencia de versión de Python**: cada venv puede tener una versión distinta
- **Aislamiento de variables de entorno**: el `.env` de cada proyecto es propio
- **Reproducibilidad cross-PC**: con `requirements.txt` pinneado + `.python-version`, el venv se recrea idéntico

### 5 reglas para garantizar independencia 100%

1. ✅ `venv/` en cada proyecto (gitignored)
2. ✅ Activar el venv antes de cualquier `pip`
3. ✅ `requirements.txt` pinneado con `==`
4. ✅ `.python-version` en cada proyecto
5. ✅ Nunca instalar deps globalmente

---

## 🛠️ 6. Cómo ejecutar el plan de mantenimiento

**Filosofía: una P0/P1 a la vez, en sesiones cortas y enfocadas.**

### Cómo arrancar cada P0/P1

Abrir Claude Code en `formulario-livskin/` y decir:

| Para implementar | Decir |
|---|---|
| Backup automático diario | *"Implementa P0-1 del plan de mantenimiento"* |
| `secret_key` en env var | *"Implementa P0-2"* |
| UptimeRobot | *"Implementa P0-3"* |
| Auth básica del formulario | *"Implementa P1-1"* |
| Validación de inputs | *"Implementa P1-2"* |
| Tests con pytest | *"Implementa P2-1"* |
| CI con GitHub Actions | *"Implementa P2-2"* |
| Etc. | *"Implementa P{X}-{N}"* |

### Lo que Claude va a hacer en cada sesión

1. Leer `CLAUDE.md` y memoria del proyecto (automático)
2. Leer la sección correspondiente del plan
3. **`git pull origin main`** (regla R7)
4. Crear branch nuevo: `git checkout -b feat/p0-1-backup-automatico`
5. Implementar la feature paso a paso explicando todo
6. Probar localmente
7. Commitear en el branch
8. Verificación visual del usuario
9. Mergear a main + push a GitHub
10. Esperar verificación de Render

**Tiempo típico por P0/P1:** 30-90 minutos.

### Orden recomendado

| Cuándo | Implementar |
|---|---|
| **Esta semana** | P0-1, P0-2, P0-3 |
| **Próxima semana** | P1-1 |
| **Mes 1** | P1-2, P1-3, P1-4 |
| **Mes 2-3** | P2-1, P2-2 |
| **Mes 3-4** | P2-3, P2-4 |
| **Mes 5-6** | Revisión y P3 |
| **Mes 7-12** | Preparación para Año 2 |

### Cómo se preserva el progreso entre sesiones

Cada vez que se implementa una P0/P1, Claude va a actualizar:

1. **`docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md`** — marcar como `[x] Implementado el YYYY-MM-DD en commit XXXXX`
2. **`memory/project_livskin.md`** — actualizar la sección de "Pendientes"

Así cualquier sesión futura sabe qué está hecho y qué falta.

---

## 🕷️ 7. Cleanup de Wepscrapper

**Respuesta corta: en sesión separada, abriendo Claude Code DIRECTAMENTE en la carpeta de Wepscrapper.**

### Por qué sesión separada

- **Memoria del proyecto**: cada proyecto tiene su propia memoria
- **Path del cwd**: cambiar mid-session es propenso a errores
- **CLAUDE.md**: el de formulario-livskin no aplica a Wepscrapper
- **Hook de planes**: cada proyecto tiene su propia config

### Cómo arrancar la sesión de Wepscrapper

1. **Cerrar la sesión actual** (la de formulario-livskin)
2. **Abrir Claude Code en `c:\Users\daizu\Claude Code\Wepscrapper_Pavimod_Gorima\`**
3. Decir:

   > *"Aplica el mismo cleanup self-contained que hicimos en formulario-livskin: pinear deps, .python-version, CLAUDE.md con las 7 reglas, hooks de planes, scripts de portabilidad, plan de mantenimiento adaptado al proyecto. Importante: chequeá primero `git pull origin main` (regla R7) y avisame si hay divergencia con el remoto."*

### Lo que ya tiene Wepscrapper (mejor que Livskin al inicio)

| Cosa | Wepscrapper hoy |
|---|---|
| `runtime.txt` | ✅ Ya existe (pero hay que migrar a `.python-version`) |
| `MAINTENANCE.md` | ✅ Ya existe (en italiano, con su propio audit) |
| `requirements.txt` pinneado | ❌ Sin pinear |
| `.claude/settings.local.json` contaminado | ✅ Limpio |
| `CLAUDE.md` | ❌ No existe |

### Plan adaptado para Wepscrapper

**Diferencias con Livskin:**
- Stack diferente (Streamlit + lxml + pandas)
- Las prioridades del plan son otras: PAT GitHub que expira, scraper HTML frágil, cache OpenCUP sin TTL
- `MAINTENANCE.md` ya existe → no reemplazarlo, complementarlo o convertirlo al formato P0/P1/P2/P3

**Pasos del cleanup (igual al patrón de Livskin):**
1. `git pull origin main` primero (R7)
2. Pinear `requirements.txt` con `==`
3. `runtime.txt` → `.python-version`
4. `CLAUDE.md` con las 7 reglas adaptadas al stack
5. Crear `tools/sync_claude_plans.py`, `tools/backup_claude_state.py`, `tools/restore_claude_state.py`
6. Hook PostToolUse en `.claude/settings.json`
7. `.env.example` con vars de Wepscrapper (PAT GitHub, etc.)
8. `docs/plans/`, `docs/runbooks/`
9. Backup ZIP a Google Drive antes de empezar
10. Verificación visual local + producción
11. Push a GitHub

**Tiempo estimado:** 1-2 horas (más rápido que Livskin porque ya hay patrón).

---

## 🗺️ 8. Mapa mental de "cómo seguir"

```
                  HOY (terminado, 2026-04-12)
                       │
                       ├─ formulario-livskin: cleanup completo en producción
                       │  con Python 3.13.13, deps pinneadas, CLAUDE.md, plan
                       ▼
              SEMANA QUE VIENE
                       ├─ P0-1: backup automático Sheets
                       ├─ P0-2: secret_key en env var
                       └─ P0-3: UptimeRobot
                       ▼
                 PRÓXIMO MES
                       ├─ P1-1: auth básica
                       ├─ P1-2: validación inputs
                       ├─ P1-3: rotación keys
                       └─ P1-4: credenciales locales
                       ▼
              EN ALGÚN MOMENTO
                       ├─ Sesión separada: cleanup Wepscrapper
                       └─ (opcional) crear template de proyectos
                       ▼
           PRÓXIMOS 3 MESES (Q2)
                       ├─ P2-1: tests
                       ├─ P2-2: CI
                       ├─ P2-3: logs
                       └─ P2-4: integridad financiera
                       ▼
            RESTO DEL AÑO 1 (Q3-Q4)
                       ├─ P3-1: cache Sheets API
                       ├─ P3-2: Render Starter
                       └─ P3-3: docs + bus factor
                       ▼
              AÑO 2 (12-24 meses)
                       └─ Migración sin fricción a Postgres + nueva infra
                          (techo $120/año)
```

---

## 📝 9. La regla más importante para el futuro

**R7: SIEMPRE `git pull origin main` antes de tocar cualquier archivo en cualquier sesión.**

Esta regla casi causa un desastre en esta sesión y la usuaria misma la evitó por instinto. Está documentada en `CLAUDE.md` y vale para todas las sesiones futuras (humanas y de Claude):

- Antes de empezar a trabajar en una PC: `git pull`
- Antes de cambiar de PC: `git push` desde la actual
- Antes de cualquier refactor: `git pull` + `git status`
- Antes de cualquier merge: `git fetch && git log main..origin/main`

Sin esta regla, podés hacer todo el cleanup del mundo y sobreescribirlo en 5 segundos por trabajar sobre código viejo.

---

## 🏁 10. Estado final post-sesión (snapshot)

### Producción

| Cosa | Estado |
|---|---|
| URL | https://formulario-livskin.onrender.com |
| Python | **3.13.13** (vía `.python-version` + env var `PYTHON_VERSION=3.13.13`) |
| Dependencias | 25 librerías pinneadas con `==` |
| Datos | 135 clientes, 47 ventas, 45 cobros — intactos |
| Hojas Sheets | 5 (Ventas, Gastos, Cobros, Clientes, Listas) |
| Cache | En memoria, TTL 90s, invalidación automática |
| Keep-alive | `/ping` + cron-job.org cada 14 min |
| Workers gunicorn | 1, timeout 120s, max_requests 200 |

### Backups en Google Drive

```
G:\Il mio Drive\Livskin\Backups\Formulario\
├── 2026-04-11\
│   ├── formulario-livskin.zip                     (snapshot del proyecto)
│   ├── Wepscrapper_Pavimod_Gorima.zip             (snapshot proyecto secundario)
│   ├── claude-state-formulario-livskin.zip        (state inicial de Claude)
│   ├── orphan-C--Users-daizu.zip                  (huérfana 1)
│   └── orphan-c--Users-daizu-Claude-Code.zip      (huérfana 2 con memoria valiosa)
└── 2026-04-12\
    └── claude-state-final.zip                     (state FINAL post-cleanup)
```

### Las 7 reglas que dejamos en CLAUDE.md

| Regla | De qué |
|---|---|
| R1 | Reproducibilidad: nunca instalar deps sin pinear |
| R2 | Planes: copiar SIEMPRE a `docs/plans/` antes de exit plan mode |
| R3 | Credenciales: nunca commitear, siempre documentar |
| R4 | `.claude/settings*.json` deben ser solo de este proyecto |
| R5 | Datos en producción: leer runbook §6 antes de tocar |
| R6 | Refactor grande: tag + ZIP + branch como red de seguridad |
| **R7** | **Múltiples computadoras: SIEMPRE `git pull origin main` antes de tocar nada** |

---

## 📚 Referencias rápidas

- [CLAUDE.md](../../CLAUDE.md) — Las 7 reglas operativas + contexto del proyecto
- [README.md](../../README.md) — Setup en PC nueva paso a paso
- [docs/plans/PLAN_MANTENIMIENTO_3_ANOS.md](../plans/PLAN_MANTENIMIENTO_3_ANOS.md) — Plan completo a 3 años con migración Año 2
- [requirements.txt](../../requirements.txt) — Las 25 dependencias pinneadas
- [.python-version](../../.python-version) — `3.13.13`
- [tools/](../../tools/) — Scripts de portabilidad

---

**Documento creado:** 2026-04-12 ~01:00
**Sesión que documenta:** 2026-04-11 ~15:00 → 2026-04-12 ~01:00 (~10 horas)
**Commits resultantes:** `c47698d`, `4f63e90`
**Tag de seguridad:** `pre-cleanup-2026-04-11`
**Branches:** `main` (al día), `cleanup/self-contained-v2` (mergeado), `refactor/self-contained-environment` (preservado como histórico)

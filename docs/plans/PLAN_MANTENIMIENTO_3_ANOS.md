# Plan de Mantenimiento y Sostenibilidad — Formulario Livskin (3 años)

## Contexto

**Formulario Livskin** es la columna vertebral operativa y contable de Livskin Professional Skincare:
registra ventas, tratamientos, productos, gastos, cobros, créditos y anticipos. Toda la información
financiera del negocio vive en una sola Google Sheet, leída y escrita por una app Flask alojada en
Render (plan gratuito). El usuario ha indicado:

- **Mucho dinero depende de este sistema.**
- Debe operar de forma continua **al menos 3 años**.
- En un horizonte de **1 a 2 años**, el sistema debe **migrar a una infraestructura más robusta**
  con un techo de costo de **$120 USD anuales** ($10/mes).
- Esa transición debe ser **sin fricción** para la operación: cero pérdida de datos, cero retraining
  del staff, y ventana de rollback durante toda la migración.

Este documento tiene cuatro objetivos:

1. **Auditoría del estado actual** — qué riesgos tiene la app hoy.
2. **Guía de mantenimiento operativo** — tareas recurrentes (diarias / semanales / mensuales / anuales).
3. **Roadmap de implementación corto plazo (Año 1)** — endurecer la app actual para que no se rompa.
4. **Plan de transición a Año 2** — migrar a una infraestructura nueva (≤ $120/año) sin fricción,
   reutilizando todo lo construido en Año 1.

> ⚠️ Este es un plan de **análisis y recomendación**, no de cambios inmediatos. Tras revisarlo, el
> usuario decidirá qué ítems P0/P1 ejecutar primero.

---

## 1. Estado actual (resumen técnico)

| Componente | Stack | Notas |
|---|---|---|
| Backend | Python 3 + Flask ([app.py](app.py), 736 líneas) | Una sola ruta por entidad, sin tests |
| Frontend | HTML + JS vanilla ([templates/formulario.html](templates/formulario.html), 1977 líneas) | 4 tabs (Venta, Gasto, Cobro, Dashboard) |
| Base de datos | Google Sheets (`SHEET_ID` hardcoded en [app.py:12](app.py#L12)) | 4 hojas: Ventas, Gastos, Cobros, Clientes |
| Auth a Google | Service Account (`livskin-formulario-56d6d2a0eac6.json`) | Local; en Render via env var `GOOGLE_CREDENTIALS` |
| Hosting | Render free tier | Cold start ~50 s; sin SLA |
| Auth de usuarios | **Ninguna** | Cualquiera con la URL puede escribir |
| Tests / CI | **Ninguno** | Sin GitHub Actions, sin linter |
| Backups | Solo el historial nativo de Google Sheets (30 días) | No hay export programado |
| Repo | Git en `main`, 1 sólo desarrollador (DarioUrrutia) | `Inventario VF.csv` sin trackear |

---

## 2. Riesgos identificados (priorizados)

| # | Riesgo | Severidad | Impacto si ocurre |
|---|---|---|---|
| R1 | **Sin backup externo de Google Sheets** | 🔴 Crítico | Si Google bloquea/borra la cuenta o alguien borra filas, se pierden meses de finanzas |
| R2 | **Sin autenticación en el formulario** | 🔴 Crítico | Cualquiera con la URL puede inyectar ventas/gastos falsos; sin trazabilidad |
| R3 | **`secret_key="livskin2024"` hardcoded** ([app.py:10](app.py#L10)) | 🔴 Crítico | Sesiones/flash forjables; debería ser env var aleatoria |
| R4 | **Sin rotación ni respaldo de la service account key** | 🟠 Alto | Si la key se filtra (ej. screenshot, repo público), no hay procedimiento de rotación |
| R5 | **Sin monitoreo de uptime ni alertas** | 🟠 Alto | La app puede estar caída horas/días sin enterarse |
| R6 | **Sin tests automatizados** | 🟠 Alto | Cada deploy es una apuesta; refactors rompen contabilidad silenciosamente |
| R7 | **Sin validación de datos** | 🟠 Alto | Errores de tipeo en montos/fechas → dashboard incorrecto → decisiones erradas |
| R8 | **Single point of failure: Google Sheets API** | 🟠 Alto | Si Sheets API está caída o se exceden cuotas (300 req/min), el negocio se detiene |
| R9 | **Render free tier: cold start 50 s + posible deprecación** | 🟡 Medio | Mala UX; Render puede eliminar el plan free o el servicio si no hay actividad |
| R10 | **1 solo desarrollador conoce el sistema** | 🟡 Medio | "Bus factor = 1": si Darío no puede mantenerlo, nadie más sabe cómo |
| R11 | **Sin logs persistentes** | 🟡 Medio | Cuando algo falla, no hay forma de auditar qué pasó |
| R12 | **Schema de Sheets sin migraciones formales** | 🟡 Medio | Agregar columnas requiere editar código + sheet manualmente; fácil desincronizar |
| R13 | **Sin rate limiting** | 🟢 Bajo | Vulnerable a abuso si la URL se filtra |
| R14 | **Documentación mínima** ([README.md](README.md) básico) | 🟢 Bajo | Onboarding lento; conocimiento tribal |

---

## 3. Guía de mantenimiento recurrente

### 📅 Diario (2 minutos)

- [ ] Verificar que `https://formulario-livskin.onrender.com` responde (ideal: monitor automático, ver P0-3).
- [ ] Confirmar que la última fila de la hoja **Ventas** tiene fecha de hoy si hubo ventas.

### 📅 Semanal (15 minutos)

- [ ] **Backup manual** de la Google Sheet a `.xlsx` y guardarlo en un disco externo o Drive personal
      (Archivo → Descargar → Microsoft Excel). *Mientras P0-1 no esté implementado, esto es obligatorio.*
- [ ] Revisar la pestaña **Dashboard** y validar que los totales cuadran con el conocimiento del negocio.
- [ ] Revisar la consola de Render: ¿errores 5xx? ¿reinicios inesperados?

### 📅 Mensual (1 hora)

- [ ] Revisar el [version history nativo de Google Sheets](https://support.google.com/docs/answer/190843)
      y confirmar que no hay borrados sospechosos.
- [ ] Conciliar manualmente: total de Ventas (TOTAL S/) − suma de Cobros − DEBE pendiente = 0.
- [ ] Revisar la cuota de la Google Sheets API en
      [Google Cloud Console](https://console.cloud.google.com/apis/api/sheets.googleapis.com/quotas).
- [ ] Actualizar dependencias menores: `pip list --outdated` y subir parches de seguridad.
- [ ] Probar el flujo completo en producción con una venta de prueba (luego borrarla).

### 📅 Trimestral (medio día)

- [ ] **Rotar la service account key** (ver runbook en §6.2).
- [ ] Probar el procedimiento de **disaster recovery** (ver §6.1) en una sheet de prueba.
- [ ] Revisar permisos de la Google Sheet: ¿quién tiene acceso? ¿alguien innecesario?
- [ ] Auditar el repo: ¿se commiteó algo sensible? `git log --all -p | grep -i "BEGIN PRIVATE KEY"`.

### 📅 Anual

- [ ] Renovar dominio si aplica (actualmente `*.onrender.com` no requiere renovación).
- [ ] Revisar el plan de Render: ¿sigue gratuito? ¿conviene migrar a paid ($7/mes) para evitar cold starts?
- [ ] Revisar versión de Python: Render puede deprecar versiones (ej. Python 3.8 → 3.11 → 3.12).
      Verificar `python_version` en `render.yaml` o agregar `runtime.txt`.
- [ ] Auditoría de seguridad: ¿alguna dependencia con CVE? `pip-audit` o `safety check`.
- [ ] Revisar este documento y actualizarlo.

---

## 4. Roadmap de implementación (priorizado)

### 🔴 P0 — Hacer YA (esta semana, riesgo de pérdida de dinero)

#### P0-1. Backup automático diario fuera de Google Sheets
**Por qué:** Si mañana Google bloquea la cuenta o alguien borra filas, se pierde todo. El historial
nativo de Sheets solo guarda 30 días y depende de la misma cuenta.

**Cómo:**
- Opción A (recomendada, simple): GitHub Action programada (cron) que corre 1×día, autenticada con
  la misma service account, descarga las 4 hojas como CSV/JSON y las commitea a un repo privado
  `formulario-livskin-backups`. Retención infinita gratis vía git.
- Opción B: Script Python en Render con `apscheduler` que sube los CSV a un bucket S3/Backblaze B2
  (~$0.005/mes para este volumen).
- Opción C: Google Apps Script dentro de la propia Sheet que envía un email diario con el `.xlsx`
  adjunto a un correo de respaldo. Cero infraestructura adicional.

**Verificación:** Borrar manualmente una fila de prueba de la sheet, ejecutar el script de
restauración y confirmar que la fila vuelve.

---

#### P0-2. Mover `secret_key` a variable de entorno
**Por qué:** El valor `"livskin2024"` en [app.py:10](app.py#L10) está públicamente en GitHub.
Cualquiera puede forjar sesiones/cookies firmadas.

**Cómo:**
```python
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)
```
Generar una clave aleatoria con `python -c "import secrets; print(secrets.token_hex(32))"` y
agregarla en Render → Environment.

**Verificación:** `echo $FLASK_SECRET_KEY` en Render shell devuelve la clave; la app inicia sin error.

---

#### P0-3. Monitor de uptime con alerta
**Por qué:** Hoy no hay forma de saber si la app está caída salvo abrirla manualmente. Para 3 años
de operación, esto es inaceptable.

**Cómo:**
- [UptimeRobot](https://uptimerobot.com) (gratis hasta 50 monitores, intervalo 5 min) o
  [Better Stack](https://betterstack.com) (gratis básico).
- Configurar 1 monitor HTTP a `https://formulario-livskin.onrender.com/` con alerta por
  email/WhatsApp/Telegram cuando devuelva no-2xx.
- **Bonus:** el monitor cada 5 min mantiene la instancia "caliente" en Render, eliminando los
  cold starts de 50 s que sufren los usuarios reales.

**Verificación:** Apagar momentáneamente el servicio en Render → debería llegar una alerta en
≤10 min.

---

### 🟠 P1 — Hacer este mes

#### P1-1. Autenticación básica del formulario
**Por qué:** Sin auth, cualquiera con la URL puede contaminar la contabilidad. Además no hay forma
de saber **quién** registró una venta.

**Cómo (de menor a mayor esfuerzo):**
1. **HTTP Basic Auth** con 1 usuario/contraseña compartida en variable de entorno
   (decorador `@requires_auth` sobre las rutas POST). Mínimo viable, ~30 líneas.
2. **PIN simple por staff** + columna `REGISTRADO_POR` en Ventas/Gastos/Cobros (mejor trazabilidad).
3. **Google OAuth Sign-In** restringido al dominio del negocio. Mejor experiencia + auditoría completa.

**Verificación:** Acceder en una ventana incógnito sin credenciales → debe rechazar. Acceder con
credenciales → debe permitir y registrar el usuario en cada fila.

---

#### P1-2. Validación de datos en backend
**Por qué:** Hoy un dedazo escribiendo "100O" en lugar de "1000" se guarda en Sheets como string y
rompe el dashboard. La fuente de verdad financiera no puede tener garbage.

**Cómo:**
- Validar tipos en cada `POST /venta`, `/gasto`, `/cobro` (montos numéricos > 0, fechas parseables,
  método de pago en lista permitida).
- Devolver 400 con mensaje claro si falla.
- Espejear la validación en frontend para mejor UX (HTML5 `pattern`, `min`, `step`, `required`).

**Verificación:** `curl -X POST .../venta -d "monto=abc"` debe devolver 400.

---

#### P1-3. Política de rotación de service account key
**Por qué:** Si la key se filtra (push accidental, screenshot, laptop robada), no hay procedimiento.

**Cómo (documento, no código):**
- Crear runbook en `docs/rotacion-credenciales.md` con pasos:
  1. Crear nueva key en Google Cloud Console (livskin-formulario project).
  2. Actualizar `GOOGLE_CREDENTIALS` en Render.
  3. Verificar que la app sigue funcionando.
  4. Borrar la key vieja en Google Cloud.
- Rotar **cada 90 días** (agendar en calendario).

---

#### P1-4. Limpiar credenciales del filesystem local
**Por qué:** El archivo `livskin-formulario-56d6d2a0eac6.json` está en el directorio de trabajo. Está
gitignored (✅), pero un backup completo del disco o una compartición de carpeta lo expone.

**Cómo:** Mover a `~/.config/livskin/credentials.json` (o equivalente Windows
`%APPDATA%\livskin\credentials.json`) y actualizar [app.py:44](app.py#L44) para leer de esa ruta.

---

### 🟡 P2 — Hacer este trimestre

#### P2-1. Suite de tests mínima
**Por qué:** Sin tests, cada cambio puede romper la contabilidad sin que nadie se entere hasta
cuadrar el mes.

**Cómo:**
- `pytest` + `pytest-flask`.
- Mockear `gspread` con un fake en memoria.
- Cubrir mínimo:
  - `get_or_create_cliente` (caso nuevo, caso existente).
  - `get_next_item_code` (incrementa correctamente, maneja vacío).
  - `calcular_cobros_por_item` (suma correcta, maneja créditos).
  - `POST /venta` con datos válidos e inválidos.
  - `POST /cobro` aplicando crédito.
- Meta inicial: 60% de cobertura del backend, 100% de las funciones de cálculo financiero.

**Verificación:** `pytest` corre verde local y en GitHub Actions.

---

#### P2-2. CI/CD con GitHub Actions
**Por qué:** Hoy se hace push directo a `main` y Render despliega. Si rompes algo, vas a
producción rota.

**Cómo:** `.github/workflows/ci.yml` que en cada push corre lint (`ruff`) + tests (`pytest`).
Render solo despliega si CI pasa (configurable en Render → Settings → Auto-Deploy).

---

#### P2-3. Logs persistentes y auditables
**Por qué:** Cuando algo falle en producción, queremos saber qué pasó.

**Cómo:**
- Agregar `logging` estructurado (JSON) en cada ruta con timestamp, usuario (cuando exista P1-1) y
  acción.
- Render guarda logs por 7 días en plan free. Para retención mayor: enviar a
  [Logtail/Better Stack](https://betterstack.com) (gratis 1GB/mes) o
  [Papertrail](https://www.papertrail.com).

---

#### P2-4. Validación de integridad financiera (script)
**Por qué:** Detectar desfases entre Ventas, Cobros y DEBE antes de que el dashboard mienta.

**Cómo:** Script `tools/check_integrity.py` que descarga las hojas y verifica:
- Para cada `COD_ITEM` en Ventas: `TOTAL = sum(cobros[COD_ITEM]) + DEBE`.
- Cada `COD_CLIENTE` en Ventas/Cobros existe en Clientes.
- No hay fechas futuras imposibles ni en formato inválido.

Correr semanalmente vía GitHub Action y enviar email si falla.

---

### 🟢 P3 — Hacer este año (mejoras de robustez a largo plazo)

#### P3-1. Cache de lectura para reducir llamadas a Sheets API
**Por qué:** La cuota es 300 req/min por proyecto. El dashboard llama varias veces seguidas. A medida
que el volumen crezca, vas a chocar con el rate limit.

**Cómo:** `flask-caching` con TTL de 30-60 s para `/api/dashboard` y `/cliente`.

---

#### P3-2. Migrar de Render free a Render paid ($7/mes) o alternativa
**Por qué:** Free tier puede deprecarse, no tiene SLA, cold start molesta a usuarios. Por $7/mes
desaparecen ambos problemas.

**Alternativas:** [Fly.io](https://fly.io) (free tier más generoso), [Railway](https://railway.app),
o un VPS pequeño ($5/mes Hetzner / DigitalOcean).

---

#### P3-3. Documentación operativa y "bus factor"
**Por qué:** Hoy solo Darío conoce el sistema. Para 3 años de operación necesitas al menos 1 persona
más capaz de mantenerlo.

**Cómo:**
- Ampliar [README.md](README.md) con secciones: arquitectura, cómo correr local, cómo desplegar, cómo restaurar
  backup, cómo rotar credenciales, contactos importantes (cuenta de Google, cuenta de Render).
- Crear `docs/runbook.md` con los procedimientos de §6.
- Compartir credenciales de cuentas (Render, Google Cloud, GitHub) con un segundo administrador
  (idealmente vía gestor de contraseñas tipo Bitwarden con vault compartido).

---

## 5. Plan de seguridad de datos (cómo proteger lo que ya está ingresado)

| Medida | Estado | Acción |
|---|---|---|
| Backup diario externo | ❌ | **P0-1** |
| Versionado nativo Sheets (30 días) | ✅ | Ya activo automáticamente |
| Backup semanal manual a disco | ❌ | Hacerlo desde **YA** mientras P0-1 no exista |
| 2FA en cuenta Google dueña de la Sheet | ⚠️ Verificar | Activar si no está |
| 2FA en cuenta GitHub | ⚠️ Verificar | Activar si no está |
| 2FA en cuenta Render | ⚠️ Verificar | Activar si no está |
| Permisos mínimos en la Sheet | ⚠️ Verificar | Solo cuentas estrictamente necesarias |
| Service account con permisos solo a esta sheet | ⚠️ Verificar | Revisar scopes |
| Rotación de keys cada 90 días | ❌ | **P1-3** |
| Validación de input | ❌ | **P1-2** |
| Auditoría de cambios (quién/cuándo) | ❌ | **P1-1** + **P2-3** |

---

## 6. Runbooks (procedimientos para emergencias)

### 6.1. Disaster Recovery: "se borraron datos de la Sheet"

1. **No tocar la Sheet** (evitar más cambios que compliquen el rollback).
2. Abrir Archivo → Historial de versiones → Ver historial de versiones.
3. Identificar la versión anterior al incidente.
4. Click en "Restaurar esta versión".
5. Si pasaron más de 30 días: usar el backup de P0-1 (restaurar desde el repo de backups o S3).
6. Documentar el incidente en `docs/incidents.md` con causa raíz.

### 6.2. Rotación de service account key

1. Google Cloud Console → IAM & Admin → Service Accounts → `livskin-formulario` → Keys → Add Key.
2. Descargar el nuevo JSON.
3. Render → Environment → editar `GOOGLE_CREDENTIALS` con el contenido del nuevo JSON.
4. Esperar el redeploy automático (~1 min).
5. Probar en `https://formulario-livskin.onrender.com` que carga.
6. Volver a Google Cloud → borrar la key vieja.
7. Borrar el JSON descargado del disco local.

### 6.3. La app está caída

1. Revisar [Render status page](https://status.render.com).
2. Revisar logs en Render dashboard → Logs.
3. Si es error 500 recurrente: rollback al último deploy verde (Render → Deploys → seleccionar
   commit anterior → Redeploy).
4. Si es problema de cuota Google Sheets: esperar reset (cada minuto) o pedir aumento de cuota.
5. Como fallback de emergencia: registrar ventas en una libreta física hasta restaurar.

---

## 7. Verificación del plan completo

Después de implementar P0+P1, validar end-to-end:

- [ ] Borrar fila de prueba en Sheets → backup la restaura ✅
- [ ] Acceder sin credenciales → rechazado ✅
- [ ] POST con monto inválido → 400 ✅
- [ ] Apagar app → alerta llega en ≤10 min ✅
- [ ] `git log -p | grep -i "secret_key"` no muestra valor real ✅
- [ ] `pytest` corre verde ✅ (después de P2-1)
- [ ] CI bloquea merge si tests fallan ✅ (después de P2-2)

---

## 8. Estimación de costo (Año 1 — app actual endurecida)

| Servicio | Costo anual | Necesidad |
|---|---|---|
| Render paid (P3-2) | $84 ($7/mes) | Alta (elimina cold start) |
| UptimeRobot free | $0 | Crítica |
| Backup en GitHub privado (P0-1) | $0 | Crítica |
| Better Stack logs (P2-3) | $0 (free tier) | Media |
| **Total Año 1** | **~$84/año** | Bajo techo de $120 ✅ |

Para una operación de la que "depende mucho dinero", **$84/año es absurdamente barato**
comparado con el costo de un solo día de inactividad o una pérdida de datos.

### Estimación de costo Año 2 (post-migración, ver §11)

| Servicio | Costo anual | Notas |
|---|---|---|
| Hosting (Fly.io / Railway / Render) | $60–$84 | Plan más chico viable; ver matriz en §11.3 |
| Postgres administrado (Supabase/Neon) | $0 | Free tier suficiente para volumen Livskin |
| Object storage (Backblaze B2) para backups | $5–$10 | ~50 GB de retención de backups versionados |
| Dominio propio `.com` (opcional) | $12–$15 | Para imagen de marca y portabilidad |
| Logs (Better Stack free) | $0 | — |
| Uptime monitor (UptimeRobot free) | $0 | — |
| Email transaccional (Resend free / Mailtrap) | $0 | Para alertas y notificaciones internas |
| **Total Año 2** | **~$77–$109/año** | Bajo techo de $120 ✅ |

> Margen de seguridad: el plan deja ~$10–$40/año libres para imprevistos (subidas de precio,
> certificados, gastos operativos puntuales).

---

## 11. Plan de transición Año 1 → Año 2 (migración sin fricción)

> 🎯 **Objetivo:** En el horizonte 12–24 meses, migrar el sistema a una infraestructura más robusta,
> sin pasar de **$120 USD/año**, sin perder un solo dato y sin que el staff note la diferencia
> operativa el día del cambio.

### 11.1. Principios rectores de la transición

1. **Cero downtime el día del switch.** El nuevo sistema debe estar funcionando en paralelo antes de
   apagar el viejo.
2. **Cero retraining.** El staff sigue viendo la misma interfaz (o una casi idéntica) y opera igual.
3. **Cero pérdida de datos.** Todo lo que está en Sheets viaja al nuevo sistema, validado fila a
   fila.
4. **Rollback en cualquier momento.** Hasta el día N+30 después del switch, debe ser posible
   revertir al sistema viejo en menos de 1 hora.
5. **Sheets sigue existiendo como espejo de visualización** durante meses, para que el dueño pueda
   seguir filtrando/auditando con la herramienta que conoce.

### 11.2. Arquitectura objetivo (Año 2)

```
                ┌─────────────────────┐
                │  Staff (mismo UI)   │
                └──────────┬──────────┘
                           │ HTTPS
                           ▼
                ┌─────────────────────┐
                │  App Flask v2       │  ← misma UI, mismo dominio
                │  (Fly.io/Railway)   │
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌──────────────────┐     ┌───────────────────┐
   │  Postgres        │     │  Sync worker      │
   │  (Supabase/Neon) │ ←─→ │  Postgres ↔ Sheet │
   │  fuente de       │     │  cada 5 min       │
   │  verdad          │     └─────────┬─────────┘
   └────────┬─────────┘               │
            │                         ▼
            │              ┌───────────────────┐
            │              │  Google Sheet     │
            │              │  (read-only       │
            │              │  espejo visual)   │
            │              └───────────────────┘
            ▼
   ┌──────────────────┐
   │  Backups diarios │
   │  → Backblaze B2  │
   └──────────────────┘
```

**Ganancias frente al sistema actual:**
- Latencia 10–50× mejor (consultas SQL vs. leer toda la hoja).
- Concurrencia segura (transacciones ACID, no race conditions).
- Joins reales entre Ventas/Cobros/Clientes (dashboard más rico).
- Sin cuotas de Sheets API.
- Backups versionados infinitos.
- Posibilidad de auth real, multi-usuario y trazabilidad completa.
- El dueño sigue viendo la Sheet como siempre.

### 11.3. Matriz de decisión de hosting (Año 2)

| Opción | Costo/año | Pros | Contras |
|---|---|---|---|
| **Fly.io** (1 shared-cpu-1x, 256 MB) | ~$0–$20 | Free tier real; deploy simple; cerca del usuario | Free tier puede cambiar |
| **Railway** Hobby | ~$60 ($5/mes) | UX excelente, Postgres incluido | Más caro que Fly |
| **Render** Starter | $84 ($7/mes) | Lo conocido; cero migración de plataforma | Más caro |
| **VPS Hetzner CX11** | ~$50 (€4.5/mes) | Control total; 2 GB RAM | Requiere admin de servidor |
| **Supabase Edge Functions + Postgres** | $0 | Todo-en-uno, free tier real | Reescritura mayor (no Flask) |

**Recomendación:** Empezar evaluando **Fly.io** (más barato, deja margen) con fallback a
**Render Starter** si Fly da problemas. Postgres gestionado en **Supabase free tier** o **Neon free
tier** (ambos ofrecen 500 MB+, suficiente para años de datos de Livskin).

### 11.4. Fases de la transición (cronograma)

#### Fase 0 — Preparación (Mes 0–2 del Año 2)

Pre-requisitos que deben estar resueltos del Año 1:
- ✅ P0-1 Backup automático funcionando (los CSV diarios serán la base del data load inicial).
- ✅ P0-2 secret_key en env var.
- ✅ P0-3 Uptime monitoring.
- ✅ P1-1 Auth básica (porque la nueva infra la asumirá desde día 1).
- ✅ P1-2 Validación de inputs (porque el schema Postgres será estricto).
- ✅ P2-1/P2-2 Tests + CI (necesarios para refactor sin romper).
- ✅ P2-4 Script de integridad financiera (será el "diff tool" durante la migración).

> **Si estos no están listos, no se puede migrar sin fricción. El Año 1 es literalmente el plan de
> preparación para el Año 2.**

#### Fase 1 — Schema design + dual-write (Mes 2–3)

1. Diseñar schema Postgres normalizado:
   ```
   clientes (cod_cliente PK, nombre, telefono, fecha_nac, fecha_registro, email)
   items    (cod_item PK, fecha, cod_cliente FK, tipo, categoria, total, moneda, tc, ...)
   cobros   (id PK, fecha, cod_cliente FK, cod_item FK, monto, metodo_pago, ...)
   gastos   (id PK, fecha, tipo, descripcion, destinatario, monto, metodo_pago)
   usuarios (id PK, nombre, pin_hash, rol)  -- nuevo, para auditoría
   ```
2. Crear migraciones con [Alembic](https://alembic.sqlalchemy.org).
3. Levantar Postgres en Supabase/Neon.
4. **Dual-write:** modificar `app.py` para que cada `POST /venta`, `/gasto`, `/cobro` escriba
   primero a Postgres y luego a Sheets. Si falla cualquiera, log a Better Stack y devolver error.

#### Fase 2 — Carga histórica + reconciliación (Mes 3)

1. Script `tools/migrate_sheets_to_postgres.py` que lee la Sheet entera y popula Postgres.
2. Correr el script de integridad de P2-4 sobre Postgres y sobre Sheets — **deben dar idénticos**.
3. Documentar cualquier discrepancia y resolverla manualmente (oportunidad de limpiar datos
   históricos sucios).
4. Desde este momento, **Postgres y Sheets están sincronizados** y el sistema sigue funcionando.

#### Fase 3 — Switch de lecturas a Postgres (Mes 4)

1. Cambiar el endpoint `/api/dashboard` y `/cliente` para leer de Postgres en vez de Sheets.
2. Cambiar `get_or_create_cliente`, `get_next_item_code`, `calcular_cobros_por_item` para usar
   Postgres.
3. Sheets ya no es fuente de verdad para reads. Pero **se sigue escribiendo** (dual-write).
4. Correr 1 mes así. Validar dashboard a diario. Si todo cuadra → Fase 4.

#### Fase 4 — Sync invertido: Postgres → Sheets como espejo (Mes 5)

1. Implementar worker `tools/sync_pg_to_sheets.py` con `apscheduler` que cada 5 minutos exporta el
   estado de Postgres a la Sheet (read-only para los humanos, pero el worker tiene permiso de
   escritura).
2. **Apagar el dual-write desde la app.** Ahora la app solo escribe a Postgres y el worker sincroniza
   a Sheets.
3. Marcar la Sheet como "ESPEJO READ-ONLY" en su título.

#### Fase 5 — Despliegue en infraestructura nueva (Mes 6)

1. Desplegar la app en Fly.io (o el hosting elegido) con dominio personalizado opcional.
2. Mantener el deploy en Render activo en paralelo durante 2–4 semanas (ambos apuntan al mismo
   Postgres → ambos sirven peticiones idénticas).
3. Cambiar el bookmark del staff a la nueva URL.
4. Después de 30 días sin incidentes: apagar Render. **Switch completado.**

#### Fase 6 — Mejoras post-migración (Mes 7+)

Ahora que hay Postgres + tests + CI + auth, se pueden agregar features que antes eran imposibles:

- Roles (admin / staff / solo-lectura).
- Dashboard en tiempo real con WebSockets.
- Reportes avanzados (rentabilidad por categoría, ranking de clientes, predicción de cumpleaños).
- Notificaciones automáticas (próxima cita, cumpleaños).
- App móvil PWA con modo offline real.

### 11.5. Plan de rollback (en cada fase)

| Fase | Cómo revertir |
|---|---|
| Fase 1 (dual-write) | Revertir commit; Sheets sigue siendo fuente de verdad sin tocar |
| Fase 2 (carga histórica) | Vaciar Postgres; nada que revertir en Sheets |
| Fase 3 (lecturas a PG) | Revertir commit; lecturas vuelven a Sheets en minutos |
| Fase 4 (sync invertido) | Apagar worker, reactivar dual-write; Sheets sigue intacto |
| Fase 5 (nuevo hosting) | Cambiar URL de vuelta a Render; ambos sirven igual |

> En **ninguna fase** se borra dato alguno de Sheets. La Sheet sigue existiendo como mínimo durante
> 1 año post-migración como red de seguridad.

### 11.6. Riesgos específicos de la migración

| Riesgo | Mitigación |
|---|---|
| Diferencias de tipo de dato (Sheets es laxo, Postgres estricto) | Validación P1-2 hecha en Año 1; script de migración con tipado estricto y reportes de filas inválidas |
| Códigos `LIVCLIENT/LIVTRAT` duplicados o faltantes en histórico | Auditar con script de integridad P2-4 antes de Fase 2 |
| Free tier de Postgres se queda chico | Exportar datos antiguos (>2 años) a tabla archivada en Backblaze; o migrar a tier pago ($25/mes Supabase, fuera de presupuesto → solo si crece mucho) |
| Staff confundido con la nueva URL | Fase 5 mantiene ambas URLs activas 30 días; comunicar con anticipación |
| Dueño extraña filtrar en Sheets | Fase 4 mantiene Sheet como espejo read-only para siempre |
| Worker de sync se cae sin que nadie note | UptimeRobot también monitorea el endpoint `/health/sync` que devuelve la fecha del último sync exitoso |

### 11.7. Checklist de "listo para migrar"

Antes de iniciar Fase 1, deben estar TODOS marcados:

- [ ] P0-1, P0-2, P0-3 implementados y funcionando ≥30 días sin incidente
- [ ] P1-1 (auth) implementado, todos los staff usándolo
- [ ] P1-2 (validación) implementado, sin garbage en Sheets nuevo
- [ ] P2-1 cobertura de tests ≥60% en cálculos financieros
- [ ] P2-2 CI bloqueando merges rotos
- [ ] P2-4 script de integridad corre verde diariamente ≥30 días seguidos
- [ ] Backups Año 1 verificados con restauración real (no solo "el script corre")
- [ ] Segundo administrador con acceso a Render, GitHub, Google Cloud (P3-3)
- [ ] Decisión final de hosting Año 2 tomada y cuenta creada
- [ ] Calendario de migración aprobado (evitando cierres de mes / fechas pico)

---

## 9. Archivos críticos de referencia

- [app.py](app.py) — backend completo (736 líneas)
- [templates/formulario.html](templates/formulario.html) — UI completa (1977 líneas)
- [requirements.txt](requirements.txt) — solo 4 dependencias
- [render.yaml](render.yaml) — configuración de deploy
- [.gitignore](.gitignore) — verifica que `*.json` y `.env` están excluidos
- `livskin-formulario-56d6d2a0eac6.json` — credenciales locales (NO en git ✅)
- `Inventario VF.csv` — datos históricos (sin trackear; **considerar moverlo a repo de backups privado**)

---

## 10. Próximos pasos sugeridos al usuario (cronograma 2 años)

### Año 1 — Endurecer el sistema actual ($84/año máx)

| Mes | Acción |
|---|---|
| **Hoy** | Backup manual `.xlsx` de la Sheet a disco/Drive personal |
| **Semana 1** | P0-1 (backup automático), P0-2 (secret key), P0-3 (uptime monitor) |
| **Semanas 2-3** | P1-1 (auth), P1-2 (validación) |
| **Mes 2** | P1-3 (rotación keys), P1-4 (limpiar credenciales locales) |
| **Mes 3-4** | P2-1 (tests), P2-2 (CI) |
| **Mes 5-6** | P2-3 (logs), P2-4 (script integridad) |
| **Mes 6** | Revisión: ¿estamos listos para Año 2? Checklist §11.7 |
| **Mes 7-9** | P3-1 (cache), P3-2 (Render Starter), P3-3 (docs/bus factor) |
| **Mes 10-12** | Decisión final de hosting Año 2 + cuenta creada + diseño de schema Postgres |

### Año 2 — Migración sin fricción ($77–$109/año máx)

| Mes | Acción |
|---|---|
| **Mes 13-14** | Fase 0–1: Schema + dual-write activo |
| **Mes 15** | Fase 2: Carga histórica + reconciliación |
| **Mes 16** | Fase 3: Switch de lecturas a Postgres |
| **Mes 17** | Fase 4: Sync invertido (Sheet vuelve read-only) |
| **Mes 18** | Fase 5: Despliegue en hosting nuevo + URL switch |
| **Mes 19+** | Fase 6: Mejoras post-migración |

### Importante

> Cada P0/P1/P2/P3 y cada Fase puede ejecutarse como una conversación independiente:
> *"Implementa P0-1 del plan de mantenimiento"* o *"Inicia Fase 1 de la migración"*.
> El plan completo vive en `C:\Users\daizu\.claude\plans\compressed-squishing-babbage.md` y sirve
> como contrato compartido entre conversaciones.

> **Regla de oro:** No iniciar el Año 2 si el checklist §11.7 no está 100% verde. La migración sin
> fricción depende enteramente de que el Año 1 haya construido las defensas.

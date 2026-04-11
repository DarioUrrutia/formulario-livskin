"""
backup_claude_state.py — Hace un ZIP completo del estado de Claude Code que
pertenece a este proyecto, para portabilidad entre PCs.

¿Qué incluye el backup?
-----------------------
1. Sesiones (transcripts) del proyecto:
   ~/.claude/projects/<project-id>/*.jsonl
   ~/.claude/projects/<project-id>/<session-id>/

2. Memoria del proyecto:
   ~/.claude/projects/<project-id>/memory/

3. Planes del proyecto (solo los exclusivos, no los compartidos):
   ~/.claude/plans/<filename>.md (filtrados con la lógica de sync_claude_plans)

4. Un archivo `MANIFEST.json` con metadata para el restore:
   - project_id original
   - project_path original (cwd al hacer backup)
   - fecha del backup
   - lista de planes incluidos
   - hostname y usuario

¿Qué NO incluye?
----------------
- File-history (~/.claude/file-history/) — es global y no project-specific.
- Telemetría (~/.claude/telemetry/) — no es necesaria para portabilidad.
- Credenciales (~/.claude/.credentials.json) — son por máquina/usuario, NO se
  deben mover entre PCs (rotarlas en su lugar).

Uso
---
    python tools/backup_claude_state.py
    python tools/backup_claude_state.py --output ruta/destino.zip

Por defecto guarda en:
    C:/Users/<user>/Backups/Claude Code/<fecha>/claude-state-<project>.zip
"""
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import platform
import shutil
import socket
import sys
import zipfile
from pathlib import Path

# Reusamos la lógica del sync para identificar planes propios del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_claude_plans as scp  # type: ignore  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_NAME = PROJECT_ROOT.name
CLAUDE_HOME = Path.home() / ".claude"


def default_output_path() -> Path:
    today = dt.date.today().isoformat()
    return Path.home() / "Backups" / "Claude Code" / today / f"claude-state-{PROJECT_NAME}.zip"


def collect_plans_for_this_project() -> list[Path]:
    """
    Usa la lógica de sync_claude_plans para identificar SOLO los planes
    exclusivos de este proyecto.
    """
    session_dir = scp.find_project_session_dir()
    if session_dir is None:
        return []
    plan_names = scp.extract_plan_filenames_from_sessions(session_dir)

    # Excluir los compartidos con otros proyectos
    other_dirs = scp.find_other_project_session_dirs(session_dir)
    shared = set()
    for od in other_dirs:
        shared.update(scp.extract_plan_filenames_from_sessions(od))

    owned = plan_names - shared
    return [scp.PLANS_DIR / name for name in sorted(owned) if (scp.PLANS_DIR / name).is_file()]


def add_to_zip(zf: zipfile.ZipFile, src: Path, arcname: str) -> int:
    """Agrega src al zip bajo el path arcname. Si es directorio, recursivo."""
    count = 0
    if src.is_file():
        zf.write(src, arcname)
        count = 1
    elif src.is_dir():
        for root, _dirs, files in os.walk(src):
            for f in files:
                full = Path(root) / f
                rel = full.relative_to(src)
                zf.write(full, f"{arcname}/{rel.as_posix()}")
                count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup del estado de Claude Code de este proyecto")
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Ruta del .zip de salida. Por defecto: ~/Backups/Claude Code/<fecha>/claude-state-<project>.zip"
    )
    parser.add_argument(
        "--no-sessions", action="store_true",
        help="No incluir transcripts de sesiones (puede ser pesado)"
    )
    args = parser.parse_args()

    output: Path = args.output or default_output_path()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Encontrar el directorio de sesiones del proyecto
    session_dir = scp.find_project_session_dir()
    if session_dir is None:
        print(f"[backup] WARN: No se encontró sesión de Claude para {PROJECT_NAME}.")
        print(f"[backup]       Buscado en: {scp.PROJECTS_DIR}")
        print(f"[backup]       El backup solo incluirá los planes (si los hay).")

    plans = collect_plans_for_this_project()

    manifest = {
        "schema_version": 1,
        "project_name": PROJECT_NAME,
        "project_path": str(PROJECT_ROOT),
        "session_dir": str(session_dir) if session_dir else None,
        "session_dir_name": session_dir.name if session_dir else None,
        "plans_count": len(plans),
        "plans": [p.name for p in plans],
        "backup_date": dt.datetime.now().isoformat(),
        "hostname": socket.gethostname(),
        "user": getpass.getuser(),
        "platform": platform.platform(),
        "include_sessions": not args.no_sessions,
    }

    total_files = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # 1. MANIFEST
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False))

        # 2. Sesiones
        if session_dir and not args.no_sessions:
            count = add_to_zip(zf, session_dir, f"sessions/{session_dir.name}")
            print(f"[backup] sessions: {count} archivos")
            total_files += count

        # 3. Planes
        for plan_path in plans:
            zf.write(plan_path, f"plans/{plan_path.name}")
            total_files += 1
        if plans:
            print(f"[backup] plans: {len(plans)} archivos ({', '.join(p.name for p in plans)})")

    size_mb = output.stat().st_size / 1024 / 1024
    print(f"[backup] OK: {output} ({total_files} archivos, {size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

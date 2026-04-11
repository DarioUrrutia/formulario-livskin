"""
restore_claude_state.py — Restaura un backup creado con backup_claude_state.py
en una PC nueva o después de formatear.

¿Qué hace?
----------
1. Lee el ZIP de backup y su MANIFEST.json.
2. Detecta el project-id ORIGINAL (donde se hizo el backup) y el ACTUAL
   (basado en el cwd donde corre este script).
3. Si los IDs difieren (cambio de PC, distinto path), renombra al vuelo:
   - sessions/<old-id>/* → ~/.claude/projects/<new-id>/*
4. Restaura los planes a ~/.claude/plans/.
5. NUNCA sobrescribe archivos existentes sin --force.

Uso
---
    python tools/restore_claude_state.py /path/al/backup.zip
    python tools/restore_claude_state.py /path/al/backup.zip --dry-run
    python tools/restore_claude_state.py /path/al/backup.zip --force

Ojo
---
- Este script asume que YA tienes Claude Code instalado en la PC nueva.
- Las credenciales (~/.claude/.credentials.json) NO se restauran. Tienes que
  loguearte de nuevo en Claude Code después del restore.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

# Reusamos la lógica de cwd_to_project_id de sync_claude_plans
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_claude_plans as scp  # type: ignore  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_HOME = Path.home() / ".claude"
PLANS_DIR = CLAUDE_HOME / "plans"
PROJECTS_DIR = CLAUDE_HOME / "projects"


def main() -> int:
    parser = argparse.ArgumentParser(description="Restaura el estado de Claude Code desde un backup")
    parser.add_argument("backup", type=Path, help="Ruta al .zip del backup")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar qué se restauraría, sin escribir nada")
    parser.add_argument("--force", action="store_true", help="Sobrescribir archivos existentes")
    args = parser.parse_args()

    if not args.backup.is_file():
        print(f"[restore] ERROR: archivo no encontrado: {args.backup}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(args.backup, "r") as zf:
        # 1. Leer manifest
        try:
            manifest_bytes = zf.read("MANIFEST.json")
        except KeyError:
            print(f"[restore] ERROR: el ZIP no contiene MANIFEST.json (¿no fue creado por backup_claude_state.py?)", file=sys.stderr)
            return 1
        manifest = json.loads(manifest_bytes.decode("utf-8"))

        old_project_path = manifest.get("project_path", "?")
        old_session_dir_name = manifest.get("session_dir_name")
        new_project_id = scp.cwd_to_project_id(PROJECT_ROOT)

        print(f"[restore] Backup info:")
        print(f"           project_name: {manifest.get('project_name')}")
        print(f"           project_path (origen): {old_project_path}")
        print(f"           session_dir_name (origen): {old_session_dir_name}")
        print(f"           backup_date: {manifest.get('backup_date')}")
        print(f"           hostname (origen): {manifest.get('hostname')}")
        print(f"           plans incluidos: {manifest.get('plans_count', 0)}")
        print(f"")
        print(f"[restore] Destino actual:")
        print(f"           project_path: {PROJECT_ROOT}")
        print(f"           session_dir_name (nuevo): {new_project_id}")
        if old_session_dir_name and old_session_dir_name != new_project_id:
            print(f"[restore] !! El project-id CAMBIA: {old_session_dir_name} → {new_project_id}")
            print(f"[restore]    Las sesiones se restaurarán bajo el nuevo nombre.")
        print(f"")

        if args.dry_run:
            print(f"[restore] DRY-RUN. Estos archivos se restaurarían:")

        plans_restored = 0
        sessions_restored = 0
        skipped_existing = 0

        for info in zf.infolist():
            name = info.filename
            if name == "MANIFEST.json":
                continue

            # Plans
            if name.startswith("plans/"):
                fname = name[len("plans/"):]
                if not fname:
                    continue
                dst = PLANS_DIR / fname
                if dst.is_file() and not args.force:
                    skipped_existing += 1
                    print(f"[restore] SKIP (existe): plans/{fname}")
                    continue
                if args.dry_run:
                    print(f"[restore] [DRY] plans/{fname} → {dst}")
                else:
                    PLANS_DIR.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, dst.open("wb") as out:
                        out.write(src.read())
                    plans_restored += 1
                    print(f"[restore] OK plans/{fname}")
                continue

            # Sessions: sessions/<old-id>/<rest>
            if name.startswith("sessions/"):
                rest = name[len("sessions/"):]
                # Reemplazar el primer componente (old-id) con el nuevo
                parts = rest.split("/", 1)
                if len(parts) == 2:
                    _old_id, sub = parts
                    dst = PROJECTS_DIR / new_project_id / sub
                else:
                    # Solo un componente — saltar
                    continue
                if dst.is_file() and not args.force:
                    skipped_existing += 1
                    continue
                if args.dry_run:
                    print(f"[restore] [DRY] sessions/{rest} → {dst}")
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, dst.open("wb") as out:
                        out.write(src.read())
                    sessions_restored += 1
                continue

    print(f"")
    print(f"[restore] Resumen: plans={plans_restored} sessions={sessions_restored} skipped={skipped_existing}")
    if skipped_existing and not args.force:
        print(f"[restore] Archivos existentes saltados. Usa --force para sobrescribir.")
    if args.dry_run:
        print(f"[restore] (DRY-RUN: no se escribió nada)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

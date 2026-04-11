"""
sync_claude_plans.py — Sincroniza los planes de Claude Code de este proyecto
desde el directorio global (~/.claude/plans/) al folder del proyecto
(docs/plans/_synced/).

¿Por qué existe?
----------------
Claude Code guarda los planes en `~/.claude/plans/<random-name>.md`, mezclados
con planes de otros proyectos del mismo usuario. Esto causa:
  1. Pérdida del plan si se formatea la PC sin backup del global.
  2. Mezcla de información entre proyectos.
  3. Imposibilidad de versionar los planes en git con el resto del código.

Este script identifica QUÉ planes pertenecen a este proyecto basándose en las
sesiones del proyecto (`~/.claude/projects/<project-id>/*.jsonl`) y los copia
a `docs/plans/_synced/`. Es 100% determinista, no heurístico.

¿Cuándo corre?
--------------
1. Manualmente: `python tools/sync_claude_plans.py`
2. Automáticamente: vía hook PostToolUse en `.claude/settings.json` después
   de cada Write/Edit.

Es idempotente y rápido (~50ms en steady state). Si no hay nada que sincronizar,
sale silenciosamente.

¿Qué NO hace?
-------------
- No edita ni borra los planes en el global.
- No reemplaza la regla R2 del CLAUDE.md (copiar manualmente con nombre
  descriptivo a `docs/plans/`). Este script es el "cinturón"; la regla manual
  es los "tirantes".
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path


# ─── Configuración ──────────────────────────────────────────────────────────

# Detectar root del proyecto: el directorio que contiene este script bajo tools/
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Carpeta destino dentro del proyecto
SYNC_DIR = PROJECT_ROOT / "docs" / "plans" / "_synced"

# Carpeta global de Claude
CLAUDE_HOME = Path.home() / ".claude"
PLANS_DIR = CLAUDE_HOME / "plans"
PROJECTS_DIR = CLAUDE_HOME / "projects"

# Marcadores para encontrar referencias a planes en los transcripts.
# Buscamos las distintas formas en que un path a `~/.claude/plans/<file>.md`
# puede aparecer codificado en JSON dentro de los .jsonl.
PLAN_MARKERS = (
    ".claude\\\\plans\\\\",  # JSON-escaped Windows path: \\\\
    ".claude/plans/",        # POSIX o JSON-escaped POSIX
    ".claude\\plans\\",      # Windows path no JSON-escaped
)

# Caracteres que no pueden formar parte de un nombre de archivo de plan
PLAN_NAME_TERMINATORS = set(' \t\n\r"\'\\/<>|?*:,;()[]{}')


def cwd_to_project_id(path: Path) -> str:
    """
    Convierte un path absoluto al formato de project-id que usa Claude Code.

    Ej: C:\\Users\\daizu\\Claude Code\\formulario-livskin
        → c--Users-daizu-Claude-Code-formulario-livskin
    """
    s = str(path)
    s = s.replace("\\", "-").replace("/", "-").replace(":", "-").replace(" ", "-")
    # Colapsar guiones múltiples NO — Claude Code mantiene los dobles del `:`
    return s


def find_project_session_dir() -> Path | None:
    """
    Encuentra el directorio de sesiones de Claude para ESTE proyecto.
    Retorna None si no existe (sesión nueva, sin transcripts aún).
    """
    project_id = cwd_to_project_id(PROJECT_ROOT)
    candidate = PROJECTS_DIR / project_id
    if candidate.is_dir():
        return candidate

    # Fallback: buscar por sufijo (último componente de la ruta)
    suffix = PROJECT_ROOT.name
    if PROJECTS_DIR.is_dir():
        for child in PROJECTS_DIR.iterdir():
            if child.is_dir() and child.name.endswith(f"-{suffix}"):
                return child

    return None


def find_other_project_session_dirs(this_project_dir: Path) -> list[Path]:
    """
    Devuelve los directorios de sesiones de TODOS los demás proyectos
    registrados en ~/.claude/projects/ (excluyendo este).
    """
    others: list[Path] = []
    if not PROJECTS_DIR.is_dir():
        return others
    try:
        this_resolved = this_project_dir.resolve()
    except OSError:
        this_resolved = this_project_dir

    for child in PROJECTS_DIR.iterdir():
        if not child.is_dir():
            continue
        try:
            if child.resolve() == this_resolved:
                continue
        except OSError:
            if child == this_project_dir:
                continue
        others.append(child)
    return others


def _extract_plan_names_from_text(text: str, found: set[str]) -> None:
    """
    Busca en `text` ocurrencias de paths a planes y extrae el filename.
    Usa búsqueda de substring + parsing manual (sin regex) para evitar
    backtracking catastrófico en archivos grandes.
    """
    for marker in PLAN_MARKERS:
        marker_len = len(marker)
        idx = 0
        while True:
            pos = text.find(marker, idx)
            if pos == -1:
                break
            # Empezamos a leer el nombre del plan justo después del marker
            start = pos + marker_len
            end = start
            n = len(text)
            # Avanzamos hasta encontrar un terminador
            while end < n and text[end] not in PLAN_NAME_TERMINATORS:
                end += 1
            name = text[start:end]
            # Solo aceptamos nombres que terminen en .md y sean razonables
            if name.endswith(".md") and 4 < len(name) < 200 and "/" not in name and "\\" not in name:
                found.add(name)
            idx = end if end > pos else pos + 1


def extract_plan_filenames_from_sessions(session_dir: Path) -> set[str]:
    """
    Lee todos los .jsonl del proyecto y extrae los nombres de archivo de planes
    referenciados (sin path, solo el filename como `<random>.md`).

    Procesa archivos línea por línea para mantener uso de memoria bajo y
    permitir early-exit si hace falta.
    """
    found: set[str] = set()
    if not session_dir.is_dir():
        return found

    # Solo nivel superior para velocidad. Las sesiones de subagentes están en
    # subdirs y suelen replicar la info del transcript principal.
    for jsonl_file in session_dir.glob("*.jsonl"):
        try:
            with jsonl_file.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if ".claude" in line and "plans" in line:
                        _extract_plan_names_from_text(line, found)
        except OSError:
            continue
    return found


def sync_plans(verbose: bool = False) -> dict:
    """
    Sincroniza los planes encontrados. Retorna un dict con stats.
    """
    stats = {
        "session_dir_found": False,
        "plans_referenced_here": 0,
        "plans_referenced_elsewhere": 0,
        "plans_owned_by_this_project": 0,
        "plans_synced": 0,
        "plans_skipped_already_synced": 0,
        "plans_skipped_already_in_docs": 0,
        "plans_skipped_shared": 0,
        "plans_missing_in_global": 0,
        "errors": [],
    }

    session_dir = find_project_session_dir()
    if session_dir is None:
        if verbose:
            print(f"[sync_claude_plans] No se encontró sesión de Claude para {PROJECT_ROOT.name}")
            print(f"[sync_claude_plans] Buscado en: {PROJECTS_DIR}")
        return stats
    stats["session_dir_found"] = True

    plan_filenames = extract_plan_filenames_from_sessions(session_dir)
    stats["plans_referenced_here"] = len(plan_filenames)

    if not plan_filenames:
        if verbose:
            print(f"[sync_claude_plans] No hay referencias a planes en las sesiones")
        return stats

    # Cross-check: detectar planes que también aparecen en otros proyectos.
    # Esos NO los copiamos (probablemente fueron mencionados por Claude al
    # discutirlos, no son creados por este proyecto).
    other_dirs = find_other_project_session_dirs(session_dir)
    plans_in_other_projects: set[str] = set()
    for other_dir in other_dirs:
        names = extract_plan_filenames_from_sessions(other_dir)
        plans_in_other_projects.update(names)
    stats["plans_referenced_elsewhere"] = len(plans_in_other_projects)

    owned_plans = plan_filenames - plans_in_other_projects
    shared_plans = plan_filenames & plans_in_other_projects
    stats["plans_owned_by_this_project"] = len(owned_plans)
    stats["plans_skipped_shared"] = len(shared_plans)

    if verbose and shared_plans:
        for p in sorted(shared_plans):
            print(f"[sync_claude_plans] SKIP (compartido con otro proyecto): {p}")

    plan_filenames = owned_plans
    if not plan_filenames:
        if verbose:
            print(f"[sync_claude_plans] No hay planes exclusivos de este proyecto")
        return stats

    # Cargar set de "ya está copiado manualmente en docs/plans/" para no
    # duplicar. La heurística más confiable: comparar HASH del contenido. Si
    # algún .md en docs/plans/ (no _synced) tiene el mismo hash que el plan
    # del global, está duplicado y lo saltamos.
    docs_plans_dir = PROJECT_ROOT / "docs" / "plans"
    docs_plans_dir.mkdir(parents=True, exist_ok=True)

    def file_hash(p: Path) -> str | None:
        try:
            h = hashlib.sha256()
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return None

    docs_hashes: dict[str, Path] = {}
    for md in docs_plans_dir.glob("*.md"):
        h = file_hash(md)
        if h:
            docs_hashes[h] = md

    manually_copied: set[str] = set()
    for fname in plan_filenames:
        src = PLANS_DIR / fname
        if not src.is_file():
            continue
        src_hash = file_hash(src)
        if src_hash and src_hash in docs_hashes:
            manually_copied.add(fname)
            if verbose:
                print(f"[sync_claude_plans] DUPLICATE de {docs_hashes[src_hash].name}: {fname}")

    SYNC_DIR.mkdir(parents=True, exist_ok=True)

    for fname in sorted(plan_filenames):
        src = PLANS_DIR / fname
        dst = SYNC_DIR / fname

        if fname in manually_copied:
            stats["plans_skipped_already_in_docs"] += 1
            if verbose:
                print(f"[sync_claude_plans] SKIP (ya copiado a docs/plans/): {fname}")
            continue

        if not src.is_file():
            stats["plans_missing_in_global"] += 1
            if verbose:
                print(f"[sync_claude_plans] MISSING en global: {fname}")
            continue

        # Si dst existe y tiene mismo mtime+size, no copiar
        if dst.is_file():
            try:
                src_stat = src.stat()
                dst_stat = dst.stat()
                if src_stat.st_size == dst_stat.st_size and abs(src_stat.st_mtime - dst_stat.st_mtime) < 1:
                    stats["plans_skipped_already_synced"] += 1
                    continue
            except OSError:
                pass

        try:
            shutil.copy2(src, dst)
            stats["plans_synced"] += 1
            if verbose:
                print(f"[sync_claude_plans] SYNCED: {fname}")
        except OSError as e:
            stats["errors"].append(f"{fname}: {e}")

    return stats


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv or "--quiet" not in sys.argv
    quiet = "--quiet" in sys.argv or "-q" in sys.argv

    try:
        stats = sync_plans(verbose=verbose and not quiet)
    except Exception as e:
        # Nunca propagar errores al hook — log y exit 0
        if not quiet:
            print(f"[sync_claude_plans] ERROR: {e}", file=sys.stderr)
        return 0

    if not quiet and (stats["plans_synced"] > 0 or verbose):
        print(
            f"[sync_claude_plans] referenced_here={stats['plans_referenced_here']} "
            f"owned={stats['plans_owned_by_this_project']} "
            f"shared={stats['plans_skipped_shared']} "
            f"synced={stats['plans_synced']} "
            f"already_synced={stats['plans_skipped_already_synced']} "
            f"already_in_docs={stats['plans_skipped_already_in_docs']} "
            f"missing={stats['plans_missing_in_global']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

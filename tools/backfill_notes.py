#!/usr/bin/env python3
"""Gera release.json para as releases legadas do evotech_releases (backfill unico).

- Toda release sem notas recebe `notes_kind: "auto"`: so a parte calculada, o
  `map_diff` contra a release anterior da mesma placa e do mesmo canal (prod contra
  prod, dev contra dev). A primeira de cada serie fica sem `map_diff` e sem `base`.
- As prods de 2026-06 a 2026-09 recebem `notes_kind: "backfill"` com as entradas
  em pt-BR de tools/backfill_curated_2026.json, reescritas a partir dos CHANGELOG.md
  arquivados e do git log do evotech-firmware entre as datas de prod.
- O manifest ganha `has_notes`, `notes_kind`, `notes_path` e `title` nas entradas
  antigas, sem tocar nos 8 campos originais (contrato 8.4). Idempotente.
- Nunca sobrescreve um release.json gerado pelo deploy (`release` ou `preview`) e
  ignora entradas do manifest schema 2 com build_id.

O diff de INI usa tools/ini_diff.py, copia vendorizada de
evotech-firmware/tools/release_notes/ini_diff.py (modulo puro, sem dependencias).

Uso: python3 tools/backfill_notes.py [--root .] [--dry-run]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ini_diff  # noqa: E402

CURATED_FILE = Path(__file__).resolve().parent / "backfill_curated_2026.json"
TIPO_ORDER = ("novo", "melhoria", "correcao", "seguranca", "removido")
PROTECTED_KINDS = {"release", "preview"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _release_id(entry: Dict[str, Any]) -> str:
    return entry.get("release_id") or "/".join(entry["ini_path"].split("/")[:2])


def _entries_for(curated: Dict[str, Any], board: str) -> List[Dict[str, Any]]:
    out = []
    for e in curated["entries"]:
        placas = e.get("placas")
        if placas and board not in placas and "todas" not in placas:
            continue
        e = {k: v for k, v in e.items() if k != "placas"}
        out.append(e)
    return sorted(out, key=lambda e: (TIPO_ORDER.index(e["tipo"]), e["id"]))


def _load_model(root: Path, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    p = root / entry["ini_path"]
    if not p.exists():
        return None
    try:
        return ini_diff.parse_ini(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:  # INI antigo fora do padrao: sem diff, nao aborta o backfill
        print(f"[!] nao foi possivel ler {p}: {e}")
        return None


def build_release_json(root: Path, entry: Dict[str, Any], prev: Optional[Dict[str, Any]],
                       prev_model: Optional[Dict[str, Any]], model: Optional[Dict[str, Any]],
                       prev_fdv: Optional[int], curated: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    rid = _release_id(entry)
    folder = root / Path(entry["ini_path"]).parent
    fdv = curated.get("flash_data_version") if curated else None
    map_diff = None
    base = None
    if prev is not None:
        base = {"release_id": _release_id(prev), "flash_data_version": prev_fdv}
        if prev_model is not None and model is not None:
            map_diff = ini_diff.diff_models(prev_model, model, prev_fdv, fdv)
    bin_file = folder / "rusefi.bin"
    kind = "backfill" if curated else "auto"
    return {
        "schema": 1,
        "release_id": rid,
        "board": entry["hardware"],
        "channel": entry["environment"],
        "full_signature": entry["full_signature"],
        "build_id": "",
        "git_commit": "",
        "dirty": False,
        "built_at": entry["timestamp"],
        "flash_data_version": fdv,
        "bin_sha256": _sha256(bin_file) if bin_file.exists() else "",
        "notes_kind": kind,
        "title": curated["title"] if curated else "",
        "summary": curated["summary"] if curated else "",
        "base": base,
        "entries": _entries_for(curated, entry["hardware"]) if curated else [],
        "map_diff": map_diff,
    }


def run(root: Path, dry_run: bool = False, curated_path: Path = CURATED_FILE) -> Dict[str, int]:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    curated_all = json.loads(curated_path.read_text(encoding="utf-8")) if curated_path.exists() else {}
    stats = {"auto": 0, "backfill": 0, "skipped": 0, "no_diff": 0, "missing_folder": 0}

    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for e in manifest["releases"]:
        groups.setdefault((e["hardware"], e["environment"]), []).append(e)

    for (board, env), entries in sorted(groups.items()):
        entries.sort(key=lambda e: (e["timestamp"], e["date"], e["signature"]))
        prev: Optional[Dict[str, Any]] = None
        prev_model: Optional[Dict[str, Any]] = None
        prev_fdv: Optional[int] = None
        for e in entries:
            folder = root / Path(e["ini_path"]).parent
            if not folder.is_dir():  # entrada orfa do manifest (pasta sobrescrita ou removida)
                stats["missing_folder"] += 1
                continue
            rj = folder / "release.json"
            existing = None
            if rj.exists():
                try:
                    existing = json.loads(rj.read_text(encoding="utf-8"))
                except ValueError:
                    existing = None
            model = _load_model(root, e)
            protected = (existing and existing.get("notes_kind") in PROTECTED_KINDS) or e.get("build_id")
            curated = curated_all.get(e["date"]) if env == "prod" else None
            if protected:
                stats["skipped"] += 1
                prev, prev_model, prev_fdv = e, model, (existing or {}).get("flash_data_version", e.get("flash_data_version"))
                continue
            data = build_release_json(root, e, prev, prev_model, model, prev_fdv, curated)
            if prev is not None and data["map_diff"] is None:
                stats["no_diff"] += 1
            stats[data["notes_kind"]] += 1
            if not dry_run:
                rj.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                e["has_notes"] = data["notes_kind"] == "backfill"
                e["notes_kind"] = data["notes_kind"]
                e["notes_path"] = str(rj.relative_to(root)).replace("\\", "/")
                e["title"] = data["title"]
            prev, prev_model, prev_fdv = e, model, data["flash_data_version"]

    if not dry_run:
        out = {"schema": 2}
        out.update({k: v for k, v in manifest.items() if k != "schema"})
        manifest_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="raiz do evotech_releases")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    stats = run(Path(args.root).resolve(), args.dry_run)
    print(f"[OK] auto={stats['auto']} backfill={stats['backfill']} protegidas={stats['skipped']} sem_diff={stats['no_diff']} pasta_ausente={stats['missing_folder']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

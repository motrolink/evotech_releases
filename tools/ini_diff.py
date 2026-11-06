# COPIA VENDORIZADA de evotech-firmware/tools/release_notes/ini_diff.py (modulo puro,
# so biblioteca padrao). Nao edite aqui: altere na firmware e copie de novo
# (tests/test_backfill.py::test_vendored_ini_diff_matches_firmware confere quando o
# repo da firmware esta ao lado). Contrato do map_diff: secao 8.2 do design
# docs/design/release-notes-e-pagina-de-update.md da firmware.
#!/usr/bin/env python3
"""Diff do mapa (INI) entre duas builds da evoTech.

Modulo puro, sem dependencias alem da biblioteca padrao: pode ser copiado ou
vendorizado em outros projetos (o backend do Manager usa o mesmo contrato).
A saida (`map_diff`) segue exatamente o contrato 8.2 de
docs/design/release-notes-e-pagina-de-update.md.

Compara apenas `[Constants]` (todas as paginas) e `[OutputChannels]`.
O que o INI nao mostra (conversao feita uma vez no load da firmware, por
exemplo) nao aparece aqui: so um fragmento `mapa.impacto: convertido` descreve.
"""

import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

KINDS = ("scalar", "array", "bits", "string")

_SECTION_RE = re.compile(r"^\[([A-Za-z0-9_]+)\]\s*$")
_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(scalar|array|bits|string)\s*,(.*)$")
_PAGE_RE = re.compile(r"^page\s*=\s*(\d+)\s*$", re.IGNORECASE)
_PAGE_SIZE_RE = re.compile(r"^pageSize\s*=\s*(.*)$", re.IGNORECASE)


def _split_args(text: str) -> List[str]:
    """Separa por virgula respeitando aspas, chaves e colchetes; remove comentario `;`."""
    out: List[str] = []
    cur: List[str] = []
    in_quote = False
    depth = 0
    for ch in text:
        if in_quote:
            cur.append(ch)
            if ch == '"':
                in_quote = False
            continue
        if ch == '"':
            in_quote = True
            cur.append(ch)
        elif ch == ";" and depth == 0:
            break
        elif ch in "{[(":
            depth += 1
            cur.append(ch)
        elif ch in "}])":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    tail = "".join(cur).strip()
    if tail or out:
        out.append(tail)
    return out


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _num(s: str) -> Any:
    """Converte para int/float quando possivel; senao devolve o texto cru."""
    s = s.strip()
    try:
        f = float(s)
    except ValueError:
        return s
    return int(f) if f == int(f) and abs(f) < 1e15 else f


def _int(s: str) -> Optional[int]:
    try:
        return int(s.strip(), 0)
    except ValueError:
        return None


def _parse_field(name: str, kind: str, rest: str, section: str, page: int) -> Dict[str, Any]:
    a = _split_args(rest)
    fld: Dict[str, Any] = {
        "name": name, "kind": kind, "section": section, "page": page,
        "type": a[0] if a else "", "offset": _int(a[1]) if len(a) > 1 else None,
        "shape": None, "bits": None, "units": "", "scale": 1, "translate": 0,
        "min": 0, "max": 0,
    }
    if kind in ("scalar", "array"):
        i = 2
        if kind == "array":
            fld["shape"] = a[2] if len(a) > 2 else ""
            i = 3
        fld["units"] = _unquote(a[i]) if len(a) > i else ""
        fld["scale"] = _num(a[i + 1]) if len(a) > i + 1 else 1
        fld["translate"] = _num(a[i + 2]) if len(a) > i + 2 else 0
        fld["min"] = _num(a[i + 3]) if len(a) > i + 3 else 0
        fld["max"] = _num(a[i + 4]) if len(a) > i + 4 else 0
    elif kind == "bits":
        fld["bits"] = a[2] if len(a) > 2 else ""
    elif kind == "string":
        fld["shape"] = a[2] if len(a) > 2 else ""
    return fld


def parse_ini(text: str) -> Dict[str, Any]:
    """Le um INI e devolve {page_sizes, constants, channels, signature}.

    Em nomes repetidos (blocos #if/#else) vale a primeira definicao.
    """
    section = ""
    page = 0
    page_sizes: List[int] = []
    constants: Dict[str, Dict[str, Any]] = {}
    channels: Dict[str, Dict[str, Any]] = {}
    signature = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        m = _SECTION_RE.match(line)
        if m:
            section = m.group(1)
            continue
        if section == "TunerStudio":
            ms = re.search(r'signature\s*=\s*"([^"]+)"', line, re.IGNORECASE)
            if ms and not signature:
                signature = ms.group(1)
            continue
        if section == "Constants":
            mp = _PAGE_RE.match(line)
            if mp:
                page = int(mp.group(1))
                continue
            mz = _PAGE_SIZE_RE.match(line)
            if mz:
                page_sizes = [v for v in (_int(x) for x in _split_args(mz.group(1))) if v is not None]
                continue
            mf = _FIELD_RE.match(line)
            if mf:
                constants.setdefault(mf.group(1), _parse_field(mf.group(1), mf.group(2), mf.group(3), section, page))
        elif section == "OutputChannels":
            mf = _FIELD_RE.match(line)
            if mf:
                channels.setdefault(mf.group(1), _parse_field(mf.group(1), mf.group(2), mf.group(3), section, 0))
    return {"page_sizes": page_sizes, "constants": constants, "channels": channels, "signature": signature}


def _shape_of(f: Dict[str, Any]) -> str:
    if f["kind"] in ("array", "string"):
        return f["shape"] or ""
    return "scalar" if f["kind"] == "scalar" else "bits"


def _props(f: Dict[str, Any]) -> Dict[str, Any]:
    return {"scale": f["scale"], "offset": f["translate"], "units": f["units"],
            "min": f["min"], "max": f["max"]}


def _type_label(f: Dict[str, Any]) -> str:
    return f["type"]


def diff_models(old: Dict[str, Any], new: Dict[str, Any],
                old_flash_version: Optional[int] = None,
                new_flash_version: Optional[int] = None) -> Dict[str, Any]:
    """Diff de dois modelos ja parseados. Listas ordenadas por nome."""
    oc, nc = old["constants"], new["constants"]
    added, removed, rescaled, retyped, reshaped = [], [], [], [], []
    for name in sorted(set(oc) | set(nc)):
        o, n = oc.get(name), nc.get(name)
        if o is None:
            added.append({"name": name, "kind": n["kind"], "units": n["units"]})
            continue
        if n is None:
            removed.append({"name": name, "kind": o["kind"]})
            continue
        # forma: array<->escalar/bits ou shape diferente
        ao, an = o["kind"] in ("array", "string"), n["kind"] in ("array", "string")
        if (ao or an) and (o["kind"] != n["kind"] or _shape_of(o) != _shape_of(n)):
            reshaped.append({"name": name, "from": _shape_of(o), "to": _shape_of(n)})
            continue
        if o["kind"] != n["kind"]:
            retyped.append({"name": name, "from": f"{o['kind']}:{_type_label(o)}",
                            "to": f"{n['kind']}:{_type_label(n)}"})
            continue
        if _type_label(o) != _type_label(n):
            retyped.append({"name": name, "from": _type_label(o), "to": _type_label(n)})
        if o["kind"] in ("scalar", "array") and _props(o) != _props(n):
            rescaled.append({"name": name, "from": _props(o), "to": _props(n)})

    oco, nco = old["channels"], new["channels"]
    moved = False
    for name, o in oco.items():
        n = nco.get(name)
        if n is None:
            continue
        if (o["offset"], o["type"], o["bits"]) != (n["offset"], n["type"], n["bits"]):
            moved = True
            break

    osz = old["page_sizes"]
    nsz = new["page_sizes"]
    page_size = {"from": osz[0] if osz else 0, "to": nsz[0] if nsz else 0}
    size_changed = bool(osz and nsz and osz != nsz)
    version_changed = (old_flash_version is not None and new_flash_version is not None
                       and old_flash_version != new_flash_version)
    return {
        "config_reset": bool(size_changed or version_changed),
        "page_size": page_size,
        "added": added,
        "removed": removed,
        "rescaled": rescaled,
        "retyped": retyped,
        "reshaped": reshaped,
        "output_channels_moved": moved,
    }


def diff_ini_text(old_text: str, new_text: str,
                  old_flash_version: Optional[int] = None,
                  new_flash_version: Optional[int] = None) -> Dict[str, Any]:
    return diff_models(parse_ini(old_text), parse_ini(new_text), old_flash_version, new_flash_version)


def diff_ini_files(old_path: str, new_path: str,
                   old_flash_version: Optional[int] = None,
                   new_flash_version: Optional[int] = None) -> Dict[str, Any]:
    with open(old_path, "r", encoding="utf-8", errors="ignore") as f:
        old_text = f.read()
    with open(new_path, "r", encoding="utf-8", errors="ignore") as f:
        new_text = f.read()
    return diff_ini_text(old_text, new_text, old_flash_version, new_flash_version)


def is_empty(diff: Dict[str, Any]) -> bool:
    """True quando nao ha nenhuma diferenca no mapa."""
    return not (diff["config_reset"] or diff["added"] or diff["removed"] or diff["rescaled"]
                or diff["retyped"] or diff["reshaped"] or diff["output_channels_moved"])


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("uso: ini_diff.py <ini_antigo> <ini_novo>", file=sys.stderr)
        return 2
    print(json.dumps(diff_ini_files(argv[0], argv[1]), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

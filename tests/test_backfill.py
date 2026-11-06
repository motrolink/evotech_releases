"""Testes do tools/backfill_notes.py e do ini_diff vendorizado."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import backfill_notes  # noqa: E402
import ini_diff  # noqa: E402

LEGACY_KEYS = {"timestamp", "signature", "hardware", "date", "environment", "ini_path", "full_signature"}


def ini(sig, page=100, extra="", branch="motrolink_prod", date="2026.08.19", board="evotech12"):
    return (f'[TunerStudio]\n\tsignature= "rusEFI {branch}.{date}.{board}.{sig}"\n'
            f"[Constants]\n\tpageSize = {page}, 256\npage = 1\nfoo = scalar, U08, 0, \"\", 1, 0, 0, 10, 0\n{extra}\n"
            "[OutputChannels]\nrpm = scalar, U16, 4, \"RPM\", 1, 0\n")


def add(root, entries, board, date, sig, ts, env, text, with_bin=True):
    folder = root / board / f"{date}_{sig}"
    folder.mkdir(parents=True)
    (folder / f"evotech_{board}.ini").write_text(text)
    if with_bin:
        (folder / "rusefi.bin").write_bytes(b"bin" + sig.encode())
    entries.append({"timestamp": ts, "signature": sig, "hardware": board, "date": date, "environment": env,
                    "ini_path": f"{board}/{date}_{sig}/evotech_{board}.ini",
                    "full_signature": f"rusEFI motrolink_{env}.{date}.{board}.{sig}"})


@pytest.fixture
def repo(tmp_path):
    entries = []
    add(tmp_path, entries, "evotech12", "2026.08.06", "1", "2026-08-06T10:00:00+00:00", "prod", ini("1"))
    add(tmp_path, entries, "evotech12", "2026.08.19", "2", "2026-08-19T10:00:00+00:00", "prod",
        ini("2", page=120, extra='bar = scalar, U08, 4, "%", 1, 0, 0, 5, 0\n'))
    add(tmp_path, entries, "evotech4", "2026.08.19", "3", "2026-08-19T10:00:00+00:00", "prod", ini("3", board="evotech4"))
    add(tmp_path, entries, "evotech12", "2026.08.20", "4", "2026-08-20T10:00:00+00:00", "dev", ini("4", branch="motrolink_dev"))
    add(tmp_path, entries, "evotech12", "2026.08.21", "5", "2026-08-21T10:00:00+00:00", "dev",
        ini("5", branch="motrolink_dev", extra='baz = scalar, U08, 8, "", 1, 0, 0, 5, 0\n'))
    entries.append({**entries[0], "timestamp": "2026-01-01T00:00:00+00:00", "signature": "9",
                    "ini_path": "evotech12/2026.01.01_9/evotech_evotech12.ini"})  # pasta ausente
    (tmp_path / "manifest.json").write_text(json.dumps({"releases": entries}, indent=2))
    curated = {"2026.08.19": {"flash_data_version": 260815, "title": "T", "summary": "S", "entries": [
        {"id": "a-b", "tipo": "correcao", "publico": "usuario", "titulo": "A", "descricao": "d",
         "mapa": {"impacto": "nenhum", "campos": [], "acao": ""}},
        {"id": "so-12", "tipo": "novo", "publico": "usuario", "titulo": "B", "descricao": "d", "placas": ["evotech12"],
         "mapa": {"impacto": "nenhum", "campos": [], "acao": ""}}]},
        "2026.08.06": {"flash_data_version": 251031, "title": "Antes", "summary": "S", "entries": []}}
    cp = tmp_path / "curated.json"
    cp.write_text(json.dumps(curated))
    return tmp_path, cp


def load(root):
    return json.loads((root / "manifest.json").read_text())


def test_auto_and_backfill_release_json(repo):
    root, cp = repo
    stats = backfill_notes.run(root, curated_path=cp)
    assert stats["backfill"] == 3 and stats["auto"] == 2 and stats["missing_folder"] == 1
    r19 = json.loads((root / "evotech12/2026.08.19_2/release.json").read_text())
    assert (r19["notes_kind"], r19["channel"], r19["board"], r19["schema"]) == ("backfill", "prod", "evotech12", 1)
    assert r19["release_id"] == "evotech12/2026.08.19_2"
    assert r19["base"] == {"release_id": "evotech12/2026.08.06_1", "flash_data_version": 251031}
    assert r19["flash_data_version"] == 260815
    assert r19["map_diff"]["config_reset"] is True
    assert [a["name"] for a in r19["map_diff"]["added"]] == ["bar"]
    assert [e["id"] for e in r19["entries"]] == ["so-12", "a-b"] or [e["id"] for e in r19["entries"]] == ["a-b", "so-12"]
    assert all("placas" not in e for e in r19["entries"])
    assert len(r19["bin_sha256"]) == 64
    r4 = json.loads((root / "evotech4/2026.08.19_3/release.json").read_text())
    assert [e["id"] for e in r4["entries"]] == ["a-b"]  # so-12 e so da evoTech 12
    assert r4["base"] is None and r4["map_diff"] is None  # primeira prod da evoTech 4


def test_dev_diffed_against_previous_dev_not_prod(repo):
    root, cp = repo
    backfill_notes.run(root, curated_path=cp)
    d1 = json.loads((root / "evotech12/2026.08.20_4/release.json").read_text())
    d2 = json.loads((root / "evotech12/2026.08.21_5/release.json").read_text())
    assert d1["notes_kind"] == "auto" and d1["base"] is None and d1["entries"] == []
    assert d2["base"]["release_id"] == "evotech12/2026.08.20_4"
    assert [a["name"] for a in d2["map_diff"]["added"]] == ["baz"]
    assert d2["map_diff"]["config_reset"] is False


def test_manifest_original_fields_untouched_and_idempotent(repo):
    root, cp = repo
    before = load(root)
    backfill_notes.run(root, curated_path=cp)
    after = load(root)
    assert after["schema"] == 2
    assert len(after["releases"]) == len(before["releases"])
    for old, new in zip(before["releases"], after["releases"]):
        for k, v in old.items():
            assert new[k] == v
        assert set(new) - set(old) <= {"has_notes", "notes_kind", "notes_path", "title"}
    by = {(e["hardware"], e["date"]): e for e in after["releases"] if e["environment"] == "prod"}
    e = by[("evotech12", "2026.08.19")]
    assert (e["has_notes"], e["notes_kind"], e["title"]) == (True, "backfill", "T")
    assert e["notes_path"] == "evotech12/2026.08.19_2/release.json"
    dev = [x for x in after["releases"] if x["environment"] == "dev"][0]
    assert dev["has_notes"] is False and dev["notes_kind"] == "auto"
    backfill_notes.run(root, curated_path=cp)
    assert load(root) == after


def test_deploy_generated_notes_are_never_overwritten(repo):
    root, cp = repo
    rj = root / "evotech12/2026.08.19_2/release.json"
    rj.write_text(json.dumps({"schema": 1, "notes_kind": "release", "title": "do deploy", "flash_data_version": 5}))
    stats = backfill_notes.run(root, curated_path=cp)
    assert stats["skipped"] == 1
    assert json.loads(rj.read_text())["title"] == "do deploy"
    m = {(e["hardware"], e["date"]): e for e in load(root)["releases"]}
    assert "notes_kind" not in m[("evotech12", "2026.08.19")]


def test_dry_run_writes_nothing(repo):
    root, cp = repo
    before = (root / "manifest.json").read_text()
    backfill_notes.run(root, dry_run=True, curated_path=cp)
    assert (root / "manifest.json").read_text() == before
    assert not list(root.rglob("release.json"))


def test_curated_file_is_valid_for_the_contract():
    curated = json.loads((ROOT / "tools" / "backfill_curated_2026.json").read_text())
    tipos = {"novo", "melhoria", "correcao", "removido", "seguranca"}
    impactos = {"nenhum", "campos_novos", "convertido", "revisar", "reset"}
    ids = set()
    for date, c in curated.items():
        assert c["title"] and c["summary"] and isinstance(c["flash_data_version"], int)
        for e in c["entries"]:
            assert e["id"] not in ids and e["id"].replace("-", "").isalnum()
            ids.add(e["id"])
            assert e["tipo"] in tipos and e["publico"] in {"usuario", "preparador"}
            assert 0 < len(e["titulo"]) <= 90 and e["descricao"].strip()
            assert e["mapa"]["impacto"] in impactos
            if e["mapa"]["impacto"] in ("revisar", "reset"):
                assert e["mapa"]["acao"].strip(), e["id"]


def test_vendored_ini_diff_matches_firmware():
    fw = Path.home() / "MotroLink/worktrees/evotech-release-notes/tools/release_notes/ini_diff.py"
    alt = ROOT.parent / "evotech-firmware/tools/release_notes/ini_diff.py"
    src = next((p for p in (fw, alt) if p.exists()), None)
    if src is None:
        pytest.skip("repo da firmware nao encontrado ao lado")
    vendored = (ROOT / "tools" / "ini_diff.py").read_text().split("\n", 5)[5]
    assert vendored == src.read_text()
    assert ini_diff.diff_ini_text("[Constants]\n", "[Constants]\n")["config_reset"] is False

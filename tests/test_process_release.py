"""Testes do process_release.py (pasta com build_id, manifest schema 2, sem sobrescrita)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import process_release  # noqa: E402

INI = '[TunerStudio]\n\tsignature= "rusEFI {branch}.{date}.{board}.{sig}"\n[Constants]\n\tpageSize = 100, 256\n'
COMMIT_A = "a" * 8 + "1" * 32
COMMIT_B = "b" * 8 + "2" * 32


def make_upload(root: Path, name="evotech12_deploy_temp", board="evotech12", date="2026.11.20",
                sig="1095591036", branch="motrolink_prod", commit=COMMIT_A, with_build=True,
                notes_kind="release", binary=b"BIN-A", extra_files=None):
    d = root / name
    d.mkdir()
    (d / f"evotech_{board}.ini").write_text(INI.format(branch=branch, date=date, board=board, sig=sig))
    (d / "rusefi.bin").write_bytes(binary)
    (d / "ini_strings_pt-BR.json").write_text("{}")
    (d / "junk.txt").write_text("x")
    if with_build:
        (d / "build.json").write_text(json.dumps({
            "git_commit": commit, "build_id": commit[:8], "dirty": False, "branch": branch,
            "built_at": "2026-11-20T14:02:11Z", "flash_data_version": 261027, "bin_sha256": "0" * 64}))
    if notes_kind:
        rid = f"{board}/{date}_{sig}_{commit[:8]}"
        (d / "release.json").write_text(json.dumps({
            "schema": 1, "release_id": rid, "notes_kind": notes_kind, "title": "Titulo da versao", "entries": []}))
        (d / "CHANGELOG.md").write_text("# Titulo\n")
    for n, c in (extra_files or {}).items():
        (d / n).write_text(c)
    return d


def run(root: Path):
    p = process_release.ReleaseProcessor(str(root))
    p.process_all()
    return p


def manifest(root: Path):
    return json.loads((root / "manifest.json").read_text())


def test_new_folder_with_build_id_and_schema2_fields(tmp_path):
    make_upload(tmp_path)
    run(tmp_path)
    folder = tmp_path / "evotech12" / f"2026.11.20_1095591036_{COMMIT_A[:8]}"
    assert sorted(p.name for p in folder.iterdir()) == [
        "CHANGELOG.md", "build.json", "evotech_evotech12.ini", "ini_strings_pt-BR.json", "release.json", "rusefi.bin"]
    m = manifest(tmp_path)
    assert m["schema"] == 2 and list(m)[0] == "schema"
    e = m["releases"][0]
    legacy = {"timestamp", "signature", "hardware", "date", "environment", "ini_path", "full_signature", "translation_path"}
    assert legacy <= set(e)
    assert e["environment"] == "prod" and e["signature"] == "1095591036"
    assert e["release_id"] == f"evotech12/2026.11.20_1095591036_{COMMIT_A[:8]}"
    assert e["ini_path"] == f"evotech12/2026.11.20_1095591036_{COMMIT_A[:8]}/evotech_evotech12.ini"
    assert (e["build_id"], e["git_commit"], e["flash_data_version"]) == (COMMIT_A[:8], COMMIT_A, 261027)
    assert e["bin_path"].endswith("/rusefi.bin")
    import hashlib
    assert e["bin_sha256"] == hashlib.sha256(b"BIN-A").hexdigest()  # o do arquivo vence o declarado
    assert (e["has_notes"], e["notes_kind"], e["title"]) == (True, "release", "Titulo da versao")
    assert e["notes_path"].endswith("/release.json")
    assert not (tmp_path / "evotech12_deploy_temp").exists()


def test_auto_notes_are_not_human_notes(tmp_path):
    make_upload(tmp_path, branch="motrolink_dev", notes_kind="auto")
    run(tmp_path)
    e = manifest(tmp_path)["releases"][0]
    assert e["environment"] == "dev" and e["has_notes"] is False and e["notes_kind"] == "auto"


def test_build_without_release_json_has_no_notes(tmp_path):
    make_upload(tmp_path, notes_kind=None)
    run(tmp_path)
    e = manifest(tmp_path)["releases"][0]
    assert e["has_notes"] is False and "notes_path" not in e


def test_legacy_upload_without_build_json_keeps_old_behaviour(tmp_path):
    make_upload(tmp_path, with_build=False, notes_kind=None)
    run(tmp_path)
    assert (tmp_path / "evotech12" / "2026.11.20_1095591036" / "rusefi.bin").exists()
    e = manifest(tmp_path)["releases"][0]
    assert set(e) == {"timestamp", "signature", "hardware", "date", "environment", "ini_path",
                      "full_signature", "translation_path"}
    assert e["ini_path"] == "evotech12/2026.11.20_1095591036/evotech_evotech12.ini"


def test_two_builds_same_day_same_hash_coexist(tmp_path):
    make_upload(tmp_path, commit=COMMIT_A, binary=b"A")
    run(tmp_path)
    make_upload(tmp_path, commit=COMMIT_B, binary=b"B")
    run(tmp_path)
    names = sorted(p.name for p in (tmp_path / "evotech12").iterdir())
    assert names == [f"2026.11.20_1095591036_{COMMIT_A[:8]}", f"2026.11.20_1095591036_{COMMIT_B[:8]}"]
    assert len(manifest(tmp_path)["releases"]) == 2


def test_same_build_reprocessed_updates_in_place(tmp_path):
    make_upload(tmp_path, binary=b"A")
    run(tmp_path)
    make_upload(tmp_path, binary=b"A2")
    run(tmp_path)
    m = manifest(tmp_path)
    assert len(m["releases"]) == 1
    folder = tmp_path / "evotech12" / f"2026.11.20_1095591036_{COMMIT_A[:8]}"
    assert (folder / "rusefi.bin").read_bytes() == b"A2"


def test_legacy_upload_does_not_clobber_identified_build(tmp_path, capsys):
    """Mesma pasta, build diferente: nada e sobrescrito em silencio e a origem e mantida."""
    make_upload(tmp_path, commit=COMMIT_A, binary=b"A")
    run(tmp_path)
    folder = tmp_path / "evotech12" / f"2026.11.20_1095591036_{COMMIT_A[:8]}"
    # outro commit chegando com o mesmo build_id (colisao de 8 hex) nao pode sobrescrever
    clash = "a" * 8 + "9" * 32
    make_upload(tmp_path, commit=clash, binary=b"CLASH")
    p = run(tmp_path)
    assert (folder / "rusefi.bin").read_bytes() == b"A"
    assert len(p.conflicts) == 1 and "NAO sobrescreve" in p.conflicts[0]
    assert (tmp_path / "evotech12_deploy_temp").exists()  # origem preservada
    assert "::error::" in capsys.readouterr().out
    assert len(manifest(tmp_path)["releases"]) == 1


def test_legacy_folder_overwrite_is_still_allowed_without_build_ids(tmp_path):
    make_upload(tmp_path, with_build=False, notes_kind=None, binary=b"1")
    run(tmp_path)
    make_upload(tmp_path, with_build=False, notes_kind=None, binary=b"2")
    p = run(tmp_path)
    assert p.conflicts == []
    assert (tmp_path / "evotech12" / "2026.11.20_1095591036" / "rusefi.bin").read_bytes() == b"2"
    assert len(manifest(tmp_path)["releases"]) == 1


def test_existing_legacy_entries_are_preserved_untouched(tmp_path):
    legacy = {"timestamp": "2026-09-07T15:43:57+00:00", "signature": "2751015660", "hardware": "evotech12",
              "date": "2026.09.07", "environment": "prod",
              "ini_path": "evotech12/2026.09.07_2751015660/evotech_evotech12.ini",
              "full_signature": "rusEFI motrolink_prod.2026.09.07.evotech12.2751015660"}
    old_dir = tmp_path / "evotech12" / "2026.09.07_2751015660"
    old_dir.mkdir(parents=True)
    (old_dir / "evotech_evotech12.ini").write_text("x")
    (tmp_path / "manifest.json").write_text(json.dumps({"releases": [legacy]}))
    make_upload(tmp_path)
    run(tmp_path)
    m = manifest(tmp_path)
    assert m["schema"] == 2 and len(m["releases"]) == 2
    assert legacy in m["releases"]  # entrada antiga identica, sem campos novos
    assert m["releases"][0]["release_id"].startswith("evotech12/2026.11.20")  # mais novo primeiro


def test_board_with_only_new_style_folders_is_not_a_candidate(tmp_path):
    make_upload(tmp_path)
    run(tmp_path)
    p = process_release.ReleaseProcessor(str(tmp_path))
    assert [c.name for c in p._get_candidate_directories()] == []


def test_invalid_build_id_falls_back_to_legacy(tmp_path):
    d = make_upload(tmp_path, notes_kind=None)
    (d / "build.json").write_text(json.dumps({"git_commit": "zz", "build_id": "zz"}))
    run(tmp_path)
    assert (tmp_path / "evotech12" / "2026.11.20_1095591036").is_dir()

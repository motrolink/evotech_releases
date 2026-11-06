"""Compatibilidade: o backend ANTIGO do Manager (tag V3.0.12-prod) precisa listar o
manifest novo e resolver os caminhos de download de uma pasta no formato novo.

O backend e extraido com `git show` do repo motrolink_manager (somente leitura) para
uma pasta temporaria e roda num subprocesso com um Python que tenha aiohttp. O acesso
ao GitHub e trocado por um cliente que serve os arquivos de um diretorio local."""
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from test_process_release import COMMIT_A, make_upload, run

ROOT = Path(__file__).resolve().parents[1]
MANAGER_REPO = Path(os.environ.get("MOTROLINK_MANAGER_REPO", Path.home() / "MotroLink/workspace/motrolink_manager"))
TAG = "V3.0.12-prod"
BACKEND_DIR = "frontend_flutter/assets/backend"


def _python_with_aiohttp():
    cands = [sys.executable, os.environ.get("MANAGER_BACKEND_PYTHON", ""),
             str(Path.home() / "MotroLink/worktrees/venv_backend/bin/python")]
    for c in cands:
        if c and Path(c).exists():
            r = subprocess.run([c, "-c", "import aiohttp"], capture_output=True)
            if r.returncode == 0:
                return c
    return None


@pytest.fixture(scope="module")
def old_backend(tmp_path_factory):
    if not (MANAGER_REPO / ".git").exists() and not (MANAGER_REPO / ".git").is_file():
        pytest.skip(f"repo do manager ausente: {MANAGER_REPO}")
    py = _python_with_aiohttp()
    if not py:
        pytest.skip("nenhum Python com aiohttp (defina MANAGER_BACKEND_PYTHON)")
    d = tmp_path_factory.mktemp("old_manager_backend")
    for name in ("backend_firmware_manager.py", "backend_http_resilient.py"):
        r = subprocess.run(["git", "-C", str(MANAGER_REPO), "show", f"{TAG}:{BACKEND_DIR}/{name}"],
                           capture_output=True)
        if r.returncode != 0:
            pytest.skip(f"tag {TAG} indisponivel no repo do manager: {r.stderr.decode()[:200]}")
        (d / name).write_bytes(r.stdout)
    return py, d


DRIVER = textwrap.dedent('''
    import asyncio, json, sys, tempfile
    from pathlib import Path
    backend, root, hw, env = sys.argv[1:5]
    sys.path.insert(0, backend)
    import backend_firmware_manager as m

    class FakeHttp:
        def __init__(self, root): self.root = Path(root)
        async def fetch_raw_text(self, repo, branch, path): return (self.root / path).read_text(encoding="utf-8")
        async def fetch_raw_content(self, repo, branch, path): return (self.root / path).read_bytes()

    async def main():
        fm = m.FirmwareManager(cache_dir=Path(tempfile.mkdtemp()))
        fm.http_client = FakeHttp(root)
        versions = await fm.get_available_versions(hw, env)
        out = {"count": len(versions), "ini_paths": [v.ini_path for v in versions], "downloads": {}}
        for v in versions[:int(sys.argv[5])]:
            files = await fm.download_release(v, force_refresh=True)
            out["downloads"][v.ini_path] = {k: (Path(p).name if p else None) for k, p in files.to_dict().items()}
        print("JSON:" + json.dumps(out))
    asyncio.run(main())
''')


def drive(py, backend, root, hw, env, n):
    drv = backend / "driver.py"
    drv.write_text(DRIVER)
    r = subprocess.run([py, str(drv), str(backend), str(root), hw, env, str(n)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("JSON:")][-1]
    return json.loads(line[5:])


def test_old_manager_lists_and_resolves_new_style_folder(old_backend, tmp_path):
    py, backend = old_backend
    # release legada + release nova (pasta com build_id) no mesmo manifest schema 2
    make_upload(tmp_path, with_build=False, notes_kind=None, date="2026.09.07", sig="2751015660",
                branch="motrolink_prod", name="legacy_up")
    run(tmp_path)
    make_upload(tmp_path, commit=COMMIT_A)
    run(tmp_path)
    m = json.loads((tmp_path / "manifest.json").read_text())
    assert m["schema"] == 2 and len(m["releases"]) == 2
    res = drive(py, backend, tmp_path, "evotech12", "prod", 2)
    new_ini = f"evotech12/2026.11.20_1095591036_{COMMIT_A[:8]}/evotech_evotech12.ini"
    assert res["count"] == 2
    assert new_ini in res["ini_paths"] and "evotech12/2026.09.07_2751015660/evotech_evotech12.ini" in res["ini_paths"]
    got = res["downloads"][new_ini]
    assert got["rusefi_bin"] == "rusefi.bin" and got["ini_file"] == "evotech_evotech12.ini"
    assert got["translation_file"] == "ini_strings_pt-BR.json"
    assert got["changelog_file"] is None  # o backend antigo pede `changelog.md` (minusculo): bug conhecido, nao regressao


def test_old_manager_parses_the_real_committed_manifest(old_backend, tmp_path):
    py, backend = old_backend
    manifest = ROOT / "manifest.json"
    (tmp_path / "manifest.json").write_bytes(manifest.read_bytes())
    data = json.loads(manifest.read_text())
    res = drive(py, backend, tmp_path, "evotech12", "prod", 0)
    assert res["count"] == sum(1 for r in data["releases"] if r["hardware"] == "evotech12" and r["environment"] == "prod")
    res = drive(py, backend, tmp_path, "evotech4", "dev", 0)
    assert res["count"] == sum(1 for r in data["releases"] if r["hardware"] == "evotech4" and r["environment"] == "dev")

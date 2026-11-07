# evotech_releases

Artefatos de release da evoTech (`.bin`, `.ini`, traduções, notas) por placa. Não edite à
mão: o `deploy.py` da firmware gera e `process_release.py` organiza (também roda no CI).

## Pastas

- Novas: `<placa>/<YYYY.MM.DD>_<hash>_<build_id>/` (`build_id` = 8 primeiros hex do commit).
  Dois builds do mesmo dia com o mesmo hash não se sobrescrevem mais.
- Antigas: `<placa>/<YYYY.MM.DD>_<hash>/`, mantidas como estão. O Manager usa `ini_path`, não
  depende do formato da pasta.
- Arquivos: `rusefi.bin`, `evotech_<placa>.ini`, `ini_strings_*.json`, `setup_wizard_<placa>.json`
  (assistente de primeiro acerto da build), `CHANGELOG.md`, `release.json` (notas e `map_diff`),
  `build.json` (metadados do build) e `script_api_<placa>.json` (referência das funções, canais e
  configurações Lua da build).

## manifest.json (schema 2)

Topo `{"schema": 2, "releases": [...]}`. Cada entrada tem os 8 campos originais
(`timestamp, signature, hardware, date, environment, ini_path, full_signature` e
`translation_path` e `wizard_path` quando há) mais, opcionais: `script_api_path` (quando a build traz o
`script_api_<placa>.json`), `release_id, build_id, git_commit,
flash_data_version, bin_path, bin_sha256, has_notes, notes_kind, notes_path, title`.
Entrada sem esses campos é uma release legada. `wizard_path` só é gravado se o
`signature` do `setup_wizard_<placa>.json` for igual ao do INI da pasta; JSON de outra
assinatura é ignorado com aviso `[!]` e a release segue sem a chave. `notes_kind`: `release` (prod com
fragmentos), `preview` (dev com fragmentos), `auto` (só o diff calculado), `backfill`
(escrito depois). `has_notes` é verdadeiro para `release`, `preview` e `backfill`.

## Ferramentas

- `process_release.py`: reorganiza pastas enviadas pelo deploy e atualiza o manifest.
- `tools/backfill_notes.py`: gera `release.json` das releases antigas (uso único, idempotente).
  Notas escritas das prods de 2026-06 a 2026-09 ficam em `tools/backfill_curated_2026.json`.
- `tools/ini_diff.py`: cópia vendorizada de `evotech-firmware/tools/release_notes/ini_diff.py`.
- Testes: `python3 -m pytest -q tests` (o de compatibilidade com o Manager V3.0.12 usa um
  Python com `aiohttp`, ver `tests/test_manager_compat.py`).

Contratos completos: `docs/design/release-notes-e-pagina-de-update.md` no evotech-firmware.

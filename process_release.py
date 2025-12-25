#!/usr/bin/env python3
"""
Script para processar releases do MotroLink.
Detecta novas pastas com arquivos .ini, extrai metadados e reorganiza na estrutura hardware/signature.
"""

import os
import re
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List


class ReleaseProcessor:
    """Processa releases e gerencia o manifest."""

    MANIFEST_FILE = "manifest.json"
    EXCLUDED_DIRS = {".git", ".github", ".claude"}

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.manifest_path = self.root_dir / self.MANIFEST_FILE
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict:
        """Carrega o manifest.json existente ou cria um novo."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"releases": []}

    def _save_manifest(self):
        """Salva o manifest.json ordenado por timestamp."""
        # Ordena por timestamp decrescente (mais recente primeiro)
        self.manifest["releases"].sort(
            key=lambda x: x["timestamp"],
            reverse=True
        )

        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)

        print(f"[OK] Manifest atualizado: {self.MANIFEST_FILE}")

    def _find_ini_file(self, directory: Path) -> Optional[Path]:
        """Encontra o arquivo .ini na pasta (deve haver apenas um)."""
        ini_files = list(directory.rglob("*.ini"))

        if len(ini_files) == 0:
            print(f"[!] Nenhum arquivo .ini encontrado em {directory.name}")
            return None

        if len(ini_files) > 1:
            print(f"[!] Multiplos arquivos .ini encontrados em {directory.name}: {[f.name for f in ini_files]}")
            print(f"  Usando o primeiro: {ini_files[0].name}")

        return ini_files[0]

    def _find_translation_files(self, directory: Path) -> List[Path]:
        """Encontra arquivos de tradução (ini_strings_*.json) na pasta."""
        translation_files = list(directory.rglob("ini_strings_*.json"))
        return translation_files

    def _extract_signature_from_ini(self, ini_path: Path) -> Optional[str]:
        """Extrai a signature completa da seção [TunerStudio] do arquivo .ini."""
        try:
            with open(ini_path, 'r', encoding='utf-8', errors='ignore') as f:
                in_tunerstudio_section = False

                for line in f:
                    line = line.strip()

                    # Detecta início da seção [TunerStudio]
                    if line == "[TunerStudio]":
                        in_tunerstudio_section = True
                        continue

                    # Detecta fim da seção (nova seção começando)
                    if in_tunerstudio_section and line.startswith("["):
                        break

                    # Procura pela linha signature=
                    if in_tunerstudio_section and "signature" in line.lower():
                        # Formato: signature= "rusEFI dev-traducao.2025.09.05.evotech12.3371204103"
                        match = re.search(r'signature\s*=\s*"([^"]+)"', line, re.IGNORECASE)
                        if match:
                            return match.group(1)

            print(f"[!] Signature nao encontrada em {ini_path.name}")
            return None

        except Exception as e:
            print(f"[X] Erro ao ler {ini_path.name}: {e}")
            return None

    def _parse_signature(self, full_signature: str) -> Optional[Dict[str, str]]:
        """
        Extrai hardware, data e assinatura da signature completa.
        Exemplo: "rusEFI dev-traducao.2025.09.05.evotech12.3371204103"
        Retorna: {"hardware": "evotech12", "signature": "3371204103", "date": "2025.09.05"}
        """
        # Remove "rusEFI " ou "evoTech " do início se existir
        signature = full_signature.replace("rusEFI ", "").replace("evoTech ", "").strip()

        # Split por pontos
        parts = signature.split(".")

        if len(parts) < 5:
            print(f"[!] Formato invalido de signature: {full_signature}")
            return None

        # Extrai os componentes da signature
        # Formato: <prefix>.<YYYY>.<MM>.<DD>.<hardware>.<signature>
        # Exemplo: motrolink_release.2025.05.28.evotech12.415604078
        hardware = parts[-2]    # Penúltimo valor
        sig_number = parts[-1]  # Último valor

        # Extrai data (YYYY.MM.DD) - posições -5, -4, -3 a partir do fim
        if len(parts) >= 6:
            year = parts[-5]
            month = parts[-4]
            day = parts[-3]
            date = f"{year}.{month}.{day}"

            # Valida se é uma data válida (formato básico)
            if not (year.isdigit() and month.isdigit() and day.isdigit() and len(year) == 4):
                print(f"[!] Data invalida na signature: {full_signature}")
                return None
        else:
            print(f"[!] Formato invalido de signature (data nao encontrada): {full_signature}")
            return None

        return {
            "hardware": hardware,
            "signature": sig_number,
            "date": date,
            "full_signature": full_signature
        }

    def _determine_environment(self, full_signature: str) -> str:
        """Determina o ambiente baseado na signature (dev ou prod)."""
        return "dev" if "dev" in full_signature.lower() else "prod"

    def _is_hardware_directory(self, dir_path: Path) -> bool:
        """Verifica se o diretório é uma pasta de hardware já organizada."""
        # Uma pasta de hardware contém subpastas no formato date_signature
        if not dir_path.is_dir():
            return False

        # Verifica se o nome da pasta é um hardware conhecido
        if dir_path.name not in ("evotech4", "evotech8", "evotech12"):
            return False

        subdirs = [d for d in dir_path.iterdir() if d.is_dir()]
        if not subdirs:
            return False

        # Verifica se pelo menos uma subpasta segue o formato YYYY.MM.DD_signature
        import re
        date_sig_pattern = re.compile(r'^\d{4}\.\d{2}\.\d{2}_\d+$')
        return any(date_sig_pattern.match(d.name) for d in subdirs)

    def _get_candidate_directories(self) -> List[Path]:
        """Retorna lista de diretórios candidatos a serem processados."""
        candidates = []

        for item in self.root_dir.iterdir():
            if not item.is_dir():
                continue

            # Ignora diretórios excluídos
            if item.name in self.EXCLUDED_DIRS:
                continue

            # Ignora diretórios de hardware já organizados
            if self._is_hardware_directory(item):
                continue

            candidates.append(item)

        return candidates

    def _release_exists(self, hardware: str, date: str, signature: str) -> bool:
        """Verifica se o release já existe no manifest."""
        return any(
            r["hardware"] == hardware and
            r.get("date") == date and
            r["signature"] == signature
            for r in self.manifest["releases"]
        )

    def _is_translation_file(self, filename: str) -> bool:
        """Verifica se o arquivo é um arquivo de tradução."""
        return filename.startswith("ini_strings_") and filename.endswith(".json")

    def _should_keep_file(self, item: Path) -> bool:
        """Verifica se o arquivo deve ser mantido no release."""
        if not item.is_file():
            return False

        filename = item.name.lower()

        # Mantém arquivos .ini
        if item.suffix.lower() == '.ini':
            return True

        # Mantém rusefi.bin
        if filename == 'rusefi.bin':
            return True

        # Mantém arquivos de tradução (ini_strings_*.json)
        if self._is_translation_file(item.name):
            return True

        # Mantém changelog
        if filename in ('changelog.md', 'changelog.txt'):
            return True

        return False

    def process_release(self, source_dir: Path) -> bool:
        """
        Processa um diretório de release.
        Retorna True se processado com sucesso, False caso contrário.
        """
        print(f"\n{'='*60}")
        print(f"Processando: {source_dir.name}")
        print(f"{'='*60}")

        # 1. Encontra o arquivo .ini
        ini_file = self._find_ini_file(source_dir)
        if not ini_file:
            return False

        print(f"[OK] Arquivo .ini encontrado: {ini_file.name}")

        # 2. Encontra arquivos de tradução
        translation_files = self._find_translation_files(source_dir)
        if translation_files:
            print(f"[OK] Arquivos de traducao encontrados: {[f.name for f in translation_files]}")
        else:
            print(f"[!] Nenhum arquivo de traducao encontrado")

        # 3. Extrai a signature
        full_signature = self._extract_signature_from_ini(ini_file)
        if not full_signature:
            return False

        print(f"[OK] Signature extraida: {full_signature}")

        # 4. Parse da signature
        parsed = self._parse_signature(full_signature)
        if not parsed:
            return False

        hardware = parsed["hardware"].lower()  # Normaliza para minúsculas
        signature = parsed["signature"]
        date = parsed["date"]

        print(f"[OK] Hardware: {hardware}")
        print(f"[OK] Data: {date}")
        print(f"[OK] Assinatura: {signature}")

        # 5. Verifica se release já existe (será atualizado)
        updating = self._release_exists(hardware, date, signature)
        if updating:
            print(f"[!] Release ja existe: {hardware}/{date}_{signature}")
            print(f"  Atualizando arquivos...")

        # 6. Cria estrutura de destino
        dest_dir = self.root_dir / hardware / f"{date}_{signature}"

        if dest_dir.exists():
            print(f"[!] Diretorio destino ja existe: {dest_dir.relative_to(self.root_dir)}")
            print(f"  Removendo diretorio existente...")
            shutil.rmtree(dest_dir)

        dest_dir.mkdir(parents=True, exist_ok=True)

        # 7. Move apenas os arquivos necessários
        print(f"[->] Movendo arquivos para: {dest_dir.relative_to(self.root_dir)}")

        files_moved = 0
        translation_file_moved = None

        for item in source_dir.iterdir():
            if self._should_keep_file(item):
                dest_item = dest_dir / item.name
                shutil.move(str(item), str(dest_item))
                print(f"  [OK] Movido: {item.name}")
                files_moved += 1

                # Rastreia arquivo de tradução movido
                if self._is_translation_file(item.name):
                    translation_file_moved = item.name
            elif item.is_file():
                print(f"  [X] Ignorado: {item.name}")

        # 8. Remove diretório original (incluindo arquivos não movidos)
        shutil.rmtree(source_dir)
        print(f"[OK] Diretorio original removido: {source_dir.name}")
        print(f"[OK] Arquivos mantidos: {files_moved}")

        # 9. Atualiza manifest
        # Remove entrada antiga se estiver atualizando
        if updating:
            self.manifest["releases"] = [
                r for r in self.manifest["releases"]
                if not (r["hardware"] == hardware and r.get("date") == date and r["signature"] == signature)
            ]

        # Caminho relativo do .ini a partir da raiz
        ini_relative_path = (dest_dir / ini_file.name).relative_to(self.root_dir)

        release_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": signature,
            "hardware": hardware,
            "date": date,
            "environment": self._determine_environment(full_signature),
            "ini_path": str(ini_relative_path).replace("\\", "/"),  # Normaliza para formato Unix
            "full_signature": full_signature
        }

        # Adiciona caminho do arquivo de tradução se existir
        if translation_file_moved:
            translation_relative_path = (dest_dir / translation_file_moved).relative_to(self.root_dir)
            release_entry["translation_path"] = str(translation_relative_path).replace("\\", "/")

        self.manifest["releases"].append(release_entry)

        action = "atualizado" if updating else "processado"
        print(f"[OK] Release {action} com sucesso!")
        print(f"  Ambiente: {release_entry['environment']}")
        print(f"  Caminho INI: {release_entry['ini_path']}")
        if translation_file_moved:
            print(f"  Caminho Traducao: {release_entry['translation_path']}")

        return True

    def process_all(self):
        """Processa todos os diretórios candidatos."""
        candidates = self._get_candidate_directories()

        if not candidates:
            print("Nenhum diretório candidato encontrado para processar.")
            return

        print(f"Diretórios candidatos encontrados: {len(candidates)}")
        for c in candidates:
            print(f"  - {c.name}")

        processed_count = 0

        for candidate in candidates:
            if self.process_release(candidate):
                processed_count += 1

        if processed_count > 0:
            self._save_manifest()
            print(f"\n{'='*60}")
            print(f"[OK] Processamento concluido: {processed_count} release(s) processado(s)")
            print(f"{'='*60}")
        else:
            print("\nNenhum release foi processado.")


def main():
    """Função principal."""
    import sys

    # Permite passar diretório raiz como argumento
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    processor = ReleaseProcessor(root_dir)
    processor.process_all()


if __name__ == "__main__":
    main()
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
        Extrai hardware e assinatura da signature completa.
        Exemplo: "rusEFI dev-traducao.2025.09.05.evotech12.3371204103"
        Retorna: {"hardware": "evotech12", "signature": "3371204103"}
        """
        # Remove "rusEFI " do início se existir
        signature = full_signature.replace("rusEFI ", "").strip()

        # Split por pontos e pega os últimos 2 valores
        parts = signature.split(".")

        if len(parts) < 2:
            print(f"[!] Formato invalido de signature: {full_signature}")
            return None

        hardware = parts[-2]  # Penúltimo valor
        sig_number = parts[-1]  # Último valor

        return {
            "hardware": hardware,
            "signature": sig_number,
            "full_signature": full_signature
        }

    def _determine_environment(self, full_signature: str) -> str:
        """Determina o ambiente baseado na signature (dev ou prod)."""
        return "dev" if "dev" in full_signature.lower() else "prod"

    def _is_hardware_directory(self, dir_path: Path) -> bool:
        """Verifica se o diretório é uma pasta de hardware já organizada."""
        # Uma pasta de hardware contém subpastas que são apenas números (signatures)
        if not dir_path.is_dir():
            return False

        subdirs = [d for d in dir_path.iterdir() if d.is_dir()]
        if not subdirs:
            return False

        # Verifica se pelo menos uma subpasta é um número (signature)
        return any(d.name.isdigit() for d in subdirs)

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

    def _release_exists(self, hardware: str, signature: str) -> bool:
        """Verifica se o release já existe no manifest."""
        return any(
            r["hardware"] == hardware and r["signature"] == signature
            for r in self.manifest["releases"]
        )

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

        # 2. Extrai a signature
        full_signature = self._extract_signature_from_ini(ini_file)
        if not full_signature:
            return False

        print(f"[OK] Signature extraida: {full_signature}")

        # 3. Parse da signature
        parsed = self._parse_signature(full_signature)
        if not parsed:
            return False

        hardware = parsed["hardware"]
        signature = parsed["signature"]

        print(f"[OK] Hardware: {hardware}")
        print(f"[OK] Assinatura: {signature}")

        # 4. Verifica duplicatas
        if self._release_exists(hardware, signature):
            print(f"[!] Release ja existe: {hardware}/{signature}")
            print(f"  Ignorando diretorio: {source_dir.name}")
            return False

        # 5. Cria estrutura de destino
        dest_dir = self.root_dir / hardware / signature

        if dest_dir.exists():
            print(f"[!] Diretorio destino ja existe: {dest_dir.relative_to(self.root_dir)}")
            print(f"  Removendo diretorio existente...")
            shutil.rmtree(dest_dir)

        dest_dir.mkdir(parents=True, exist_ok=True)

        # 6. Move os arquivos
        print(f"[->] Movendo arquivos para: {dest_dir.relative_to(self.root_dir)}")

        for item in source_dir.iterdir():
            dest_item = dest_dir / item.name
            shutil.move(str(item), str(dest_item))

        # 7. Remove diretório original
        source_dir.rmdir()
        print(f"[OK] Diretorio original removido: {source_dir.name}")

        # 8. Atualiza manifest
        # Caminho relativo do .ini a partir da raiz
        ini_relative_path = (dest_dir / ini_file.name).relative_to(self.root_dir)

        release_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": signature,
            "hardware": hardware,
            "environment": self._determine_environment(full_signature),
            "ini_path": str(ini_relative_path).replace("\\", "/"),  # Normaliza para formato Unix
            "full_signature": full_signature
        }

        self.manifest["releases"].append(release_entry)

        print(f"[OK] Release processado com sucesso!")
        print(f"  Ambiente: {release_entry['environment']}")
        print(f"  Caminho: {release_entry['ini_path']}")

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

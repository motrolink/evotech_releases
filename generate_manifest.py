import os
import json
import re
import configparser
from datetime import datetime, timezone
from decimal import Decimal, getcontext

# Define a precisão para cálculos com Decimal
getcontext().prec = 5

# --- CONFIGURAÇÃO ---
MANIFEST_FILE = 'manifest.json'
CONFIG_ROOT_DIR = '.'
# Número de linhas a serem lidas do início de cada arquivo .ini
LINES_TO_READ = 200

def get_existing_manifest():
    """Carrega o manifesto existente ou cria um novo se não existir."""
    if not os.path.exists(MANIFEST_FILE):
        print(f"Arquivo '{MANIFEST_FILE}' não encontrado. Criando um novo.")
        return {"versoes": [], "assinaturas": {}}
    
    try:
        # Tenta ler como UTF-8 (padrão para JSON), mas se falhar, tenta latin-1 por retrocompatibilidade.
        try:
            with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except UnicodeDecodeError:
            with open(MANIFEST_FILE, 'r', encoding='latin-1') as f:
                data = json.load(f)

        if "versoes" not in data: data["versoes"] = []
        if "assinaturas" not in data: data["assinaturas"] = {}
        return data
    except (json.JSONDecodeError, FileNotFoundError):
        print("AVISO: Manifesto existente não encontrado ou corrompido. Criando um novo.")
        return {"versoes": [], "assinaturas": {}}

def get_next_version(current_highest_version, force_major_version=None):
    """Calcula a próxima versão."""
    if force_major_version:
        return f"{force_major_version}.0"
    
    if not current_highest_version:
        return "1.0"
        
    next_version = Decimal(current_highest_version) + Decimal('0.1')
    return f"{next_version}"

def generate_manifest():
    """Gera o manifesto varrendo os diretórios e arquivos .ini."""
    manifest_data = get_existing_manifest()
    existing_signatures = set(manifest_data.get("assinaturas", {}).keys())
    
    versions_list = [Decimal(v['versao']) for v in manifest_data.get("versoes", [])]
    current_highest_version = str(max(versions_list)) if versions_list else "0.9"

    new_entries = []

    for folder_name in os.listdir(CONFIG_ROOT_DIR):
        folder_path = os.path.join(CONFIG_ROOT_DIR, folder_name)
        if os.path.isdir(folder_path) and not folder_name.startswith('.'):
            
            ini_files = [f for f in os.listdir(folder_path) if f.endswith('.ini')]
            if not ini_files:
                continue

            ini_file_path = os.path.join(folder_path, ini_files[0])
            
            config = configparser.ConfigParser(strict=False)
            try:
                with open(ini_file_path, 'r', encoding='latin-1') as f:
                    head_lines = [next(f) for _ in range(LINES_TO_READ)]
                ini_content = "".join(head_lines)
                
                config.read_string("[DUMMY_SECTION]\n" + ini_content)
                
                # --- LÓGICA DE LIMPEZA DA ASSINATURA ---
                assinatura_raw = config.get('TunerStudio', 'signature')
                # 1. Remove comentários (tudo após ';')
                assinatura_limpa = assinatura_raw.split(';')[0]
                # 2. Remove aspas e espaços em branco das bordas
                assinatura_limpa = assinatura_limpa.strip().strip('"')
                # 3. Remove o prefixo conhecido "rusEFI "
                if assinatura_limpa.startswith("rusEFI "):
                    assinatura_limpa = assinatura_limpa.replace("rusEFI ", "", 1)
                
                assinatura = assinatura_limpa.strip()

            except StopIteration:
                ini_content = "".join(head_lines)
                config.read_string("[DUMMY_SECTION]\n" + ini_content)
                assinatura_raw = config.get('TunerStudio', 'signature')
                assinatura_limpa = assinatura_raw.split(';')[0].strip().strip('"')
                if assinatura_limpa.startswith("rusEFI "):
                    assinatura_limpa = assinatura_limpa.replace("rusEFI ", "", 1)
                assinatura = assinatura_limpa.strip()
            except Exception as e:
                print(f"AVISO: Erro ao processar o arquivo '{ini_file_path}'. Pulando. Erro: {e}")
                continue

            if not assinatura or assinatura in existing_signatures:
                continue

            print(f"Nova configuração encontrada! Assinatura: {assinatura}")

            # --- LÓGICA DE LEITURA DO CHANGELOG ---
            changelog_path = os.path.join(folder_path, 'changelog.txt')
            changelog_content = ""
            if os.path.exists(changelog_path):
                try:
                    with open(changelog_path, 'r', encoding='utf-8') as f:
                        changelog_content = f.read().strip()
                except Exception as e:
                    print(f"  - AVISO: Não foi possível ler o changelog.txt em '{folder_path}'. Erro: {e}")
            
            ambiente = 'dev' if 'dev' in folder_name.lower() else 'prod'
            force_release_match = re.search(r'_v(\d+)_', folder_name)
            force_major_version = int(force_release_match.group(1)) if force_release_match else None
            
            current_highest_version = get_next_version(current_highest_version, force_major_version)
            
            new_entry = {
                "assinatura": assinatura,
                "versao": current_highest_version,
                "ambiente": ambiente,
                "caminho_arquivo": ini_file_path.replace('\\', '/'),
                "data_adicao": datetime.now(timezone.utc).isoformat(),
                "changelog": changelog_content # Adiciona o changelog ao registro
            }
            new_entries.append(new_entry)
            existing_signatures.add(assinatura)

    if not new_entries:
        print("Nenhuma nova configuração encontrada. Manifesto já está atualizado.")
        return

    all_versions = manifest_data.get("versoes", []) + new_entries
    all_versions.sort(key=lambda x: Decimal(x['versao']), reverse=True)
    
    assinaturas_map = {item['assinatura']: item['caminho_arquivo'] for item in all_versions}

    final_manifest = {
        "versoes": all_versions,
        "assinaturas": assinaturas_map
    }

    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Manifesto '{MANIFEST_FILE}' atualizado com sucesso com {len(new_entries)} nova(s) entrada(s).")

if __name__ == "__main__":
    generate_manifest()

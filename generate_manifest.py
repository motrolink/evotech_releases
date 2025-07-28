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

def get_existing_manifest():
    """Carrega o manifesto existente ou cria um novo se não existir."""
    if not os.path.exists(MANIFEST_FILE):
        print(f"Arquivo '{MANIFEST_FILE}' não encontrado. Criando um novo.")
        return {"versoes": [], "assinaturas": {}}
    
    # Usamos 'latin-1' para evitar erros de decodificação em manifestos antigos
    with open(MANIFEST_FILE, 'r', encoding='latin-1') as f:
        try:
            data = json.load(f)
            if "versoes" not in data: data["versoes"] = []
            if "assinaturas" not in data: data["assinaturas"] = {}
            return data
        except json.JSONDecodeError:
            print("ERRO: Manifesto existente está corrompido. Criando um novo.")
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
            
            config = configparser.ConfigParser()
            try:
                # <<< MUDANÇA PRINCIPAL AQUI >>>
                # Lemos o conteúdo do arquivo usando 'latin-1' para evitar erros de codec.
                with open(ini_file_path, 'r', encoding='latin-1') as f:
                    ini_content = f.read()
                
                # Adicionamos uma seção "dummy" para lidar com arquivos sem cabeçalho inicial.
                config.read_string("[DUMMY_SECTION]\n" + ini_content)

                assinatura = config.get('TunerStudio', 'signature')

            except (configparser.NoSectionError, configparser.NoOptionError) as e:
                print(f"AVISO: Não foi possível encontrar '[TunerStudio] -> signature' em '{ini_file_path}'. Pulando. Erro: {e}")
                continue
            except Exception as e:
                print(f"AVISO: Erro genérico ao ler o arquivo '{ini_file_path}'. Pulando. Erro: {e}")
                continue

            if assinatura in existing_signatures:
                continue

            print(f"Nova configuração encontrada! Assinatura: {assinatura}")

            ambiente = 'dev' if 'dev' in folder_name.lower() else 'prod'
            force_release_match = re.search(r'_v(\d+)_', folder_name)
            force_major_version = int(force_release_match.group(1)) if force_release_match else None
            
            current_highest_version = get_next_version(current_highest_version, force_major_version)
            
            new_entry = {
                "assinatura": assinatura,
                "versao": current_highest_version,
                "ambiente": ambiente,
                "caminho_arquivo": ini_file_path.replace('\\', '/'),
                "data_adicao": datetime.now(timezone.utc).isoformat()
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

    # Escrevemos o manifesto final em UTF-8, que é o padrão correto para JSON.
    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Manifesto '{MANIFEST_FILE}' atualizado com sucesso com {len(new_entries)} nova(s) entrada(s).")

if __name__ == "__main__":
    generate_manifest()

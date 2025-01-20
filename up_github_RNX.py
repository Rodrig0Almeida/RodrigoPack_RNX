# -*- coding: utf-8 -*-
import requests
import os
import zipfile
import json
import time
from datetime import datetime
from tqdm import tqdm
from requests_toolbelt.multipart.encoder import MultipartEncoderMonitor, MultipartEncoder

def fix_timestamp(file_path):
    """Corrige timestamps inválidos antes de 1980."""
    current_time = time.time()
    try:
        file_stat = os.stat(file_path)
        if file_stat.st_mtime < 315532800:  # Timestamp de 01/01/1980
            os.utime(file_path, (current_time, current_time))
    except Exception:
        pass

def create_zip(source_dir, output_zip):
    """Cria um arquivo ZIP da pasta especificada com barra de progresso."""
    total_files = sum(len(files) for _, _, files in os.walk(source_dir))
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        with tqdm(total=total_files, desc="Criando arquivo ZIP", unit="arquivo") as pbar:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    fix_timestamp(file_path)
                    zipf.write(file_path, arcname)
                    pbar.update(1)

def upload_release(config_path, zip_path, release_name):
    """Faz upload do ZIP como um release no GitHub com barra de progresso."""
    with open(config_path, 'r', encoding='utf-8-sig') as file:
        config = json.load(file)

    repository = config["repository"]
    token = config["token"]

    # Lê o conteúdo do README.md
    readme_path = "README.md"
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as readme_file:
            readme_content = readme_file.read()
    else:
        readme_content = "README.md não encontrado. Release gerado automaticamente."

    # API para criar o release
    release_url = f"https://api.github.com/repos/{repository}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }

    release_data = {
        "tag_name": release_name,
        "name": release_name,
        "body": readme_content,
        "draft": False,
        "prerelease": False
    }

    response = requests.post(release_url, headers=headers, json=release_data)
    if response.status_code == 201:
        release_info = response.json()
        upload_url = release_info["upload_url"].split("{")[0]
    else:
        raise Exception(f"Erro ao criar o release: {response.status_code} - {response.text}")

    # Faz o upload do arquivo ZIP
    with open(zip_path, 'rb') as zip_file:
        file_name = os.path.basename(zip_path)
        file_size = os.path.getsize(zip_path)

        params = {"name": file_name}
        upload_headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/zip"
        }

        # Corrigir a barra de progresso para exibir MB
        with tqdm(total=file_size, desc="Enviando arquivo ZIP", unit="MB", unit_scale=True, unit_divisor=1024) as pbar:
            def update_progress(monitor):
                pbar.update(monitor.bytes_read - pbar.n)  # Atualiza apenas os bytes novos

            encoder = MultipartEncoder(fields={'file': (file_name, zip_file, 'application/zip')})
            monitor = MultipartEncoderMonitor(encoder, update_progress)

            upload_response = requests.post(upload_url, headers=upload_headers, params=params, data=monitor)
            if upload_response.status_code == 201:
                print(f"\nArquivo {file_name} enviado com sucesso para o release.")
            else:
                raise Exception(f"Erro ao enviar o arquivo: {upload_response.status_code} - {upload_response.text}")

def main():
    source_dir = "."  # Diretório atual
    output_zip = "RodrigoPack_RNX.zip"  # Nome do arquivo ZIP
    config_path = "github.json"  # Caminho do arquivo de configuração

    create_zip("RodrigoPack_RNX", output_zip)

    release_name = f"Release-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    upload_release(config_path, output_zip, release_name)

if __name__ == "__main__":
    main()
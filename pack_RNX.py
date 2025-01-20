import requests
import json
import os
import zipfile
import tarfile
import shutil
from tqdm import tqdm


def get_latest_release(url, file_type):
    """Obtém o link do último lançamento na página de releases do GitHub usando a API."""
    headers = {"User-Agent": "Termux-Script"}

    api_url = url.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        print(f"Erro ao acessar {url}: {response.status_code}")
        return None, None, None

    release_data = response.json()

    for asset in release_data["assets"]:
        if asset["name"].endswith(file_type):
            return asset["browser_download_url"], asset["name"], release_data["tag_name"]

    print(f"Nenhum arquivo do tipo {file_type} encontrado na última release de {url}.")
    return None, None, None


def download_file(url, file_name, output_dir="downloads"):
    """Faz o download de um arquivo com barra de progresso."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, file_name)

    if os.path.exists(file_path):
        print(f"Arquivo {file_name} já existe. Não será feito o download novamente.")
        return file_path

    headers = {"User-Agent": "Termux-Script"}
    response = requests.get(url, headers=headers, stream=True)

    if response.status_code == 200:
        total_size = int(response.headers.get("content-length", 0))
        with open(file_path, "wb") as file, tqdm(
            desc=file_name,
            total=total_size,
            unit="B",
            unit_scale=True,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                bar.update(len(chunk))
        return file_path
    else:
        print(f"Erro ao baixar {url}: {response.status_code}")
        return None


def extract_file(file_path, extract_to="RodrigoPack_RNX", extract_folder=None, file_type="zip", copy_to=None, rename_to=None):
    """Extrai ou copia um arquivo baseado no seu tipo. Renomeia se necessário."""
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)

    try:
        if file_type == "zip":
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                if extract_folder:
                    for file_info in zip_ref.infolist():
                        if file_info.filename.startswith(extract_folder + os.sep):
                            file_info.filename = file_info.filename[len(extract_folder) + 1:]
                            if file_info.filename:
                                extracted_path = zip_ref.extract(file_info, extract_to)
                                if rename_to and file_info.filename == os.path.basename(file_info.filename):
                                    os.rename(extracted_path, os.path.join(extract_to, rename_to))
                else:
                    zip_ref.extractall(extract_to)

        elif file_type in ["tar.gz", "tar.xz"]:
            with tarfile.open(file_path, "r:*") as tar_ref:
                if extract_folder:
                    for member in tar_ref.getmembers():
                        if member.name.startswith(extract_folder + os.sep):
                            member.name = member.name[len(extract_folder) + 1:]
                            tar_ref.extract(member, extract_to)
                else:
                    tar_ref.extractall(extract_to)

        else:
            dest_dir = copy_to or extract_to
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            dest_path = os.path.join(dest_dir, rename_to or os.path.basename(file_path))
            shutil.copy(file_path, dest_path)

    except (zipfile.BadZipFile, tarfile.TarError) as e:
        print(f"Erro: O arquivo {file_path} não é válido. ({e})")


def generate_readme(repos, versions, output_file="README.md"):
    """Gera um README.md com os programas baixados."""
    with open(output_file, "w") as readme:
        readme.write("# Programas Baixados\n\n")
        for name, data in repos.items():
            version = versions.get(name, "Desconhecida")
            readme.write(f"- **{name}**\n")
            readme.write(f"  - Repositório: {data['url']}\n")
            readme.write(f"  - Tipo: {data.get('file_type', 'Desconhecido')}\n")
            readme.write(f"  - Versão: {version}\n\n")


def main():
    with open("links.json", "r") as file:
        repos = json.load(file)

    versions = {}
    for name, data in repos.items():
        file_type = data.get("file_type", "zip")
        release_url, file_name, version = get_latest_release(data["url"], file_type)
        if release_url and file_name:
            versions[name] = version
            file_path = download_file(release_url, file_name)
            if file_path:
                extract_file(
                    file_path,
                    extract_to="RodrigoPack_RNX",
                    extract_folder=data.get("extract_folder"),
                    file_type=file_type,
                    copy_to=data.get("copy_to"),
                    rename_to=data.get("Rename_to"),
                )
        else:
            versions[name] = "Não encontrado"

    generate_readme(repos, versions)


if __name__ == "__main__":
    main()
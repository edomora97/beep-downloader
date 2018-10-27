#!/usr/bin/env python3

import json
import requests
import re
import os
import getpass
import argparse
import shutil
import subprocess
import tempfile
from colorama import init, Fore, Style
from requests.auth import HTTPBasicAuth
from html import unescape
from urllib.parse import quote

GET_FILES_URL = "https://beep.metid.polimi.it/api/secure/jsonws/dlapp/get-file-entries?repositoryId=%d&folderId=%d"
GET_SUBFOLDERS_URL = "https://beep.metid.polimi.it/api/secure/jsonws/dlapp/get-folders?repositoryId=%d&parentFolderId=%d"
BEEP_LOGIN_URL = "https://aunicalogin.polimi.it/aunicalogin/aunicalogin/controller/IdentificazioneUnica.do?&jaf_currentWFID=main&polij_step=0&__pj0=0&__pj1=5111b95d3a1ad2c39f675fd752d1b1f0"
BEEP_LOGIN_URL2 = "https://aunicalogin.polimi.it/aunicalogin/aunicalogin/controller/AunicaLogin.do?evn_checkCookieSSO=evento&COOKIES_VALUES_SSO_LOGOUT=S436_-S557_-&id_servizio=557&id_servizio_idp=436&ID_SERVIZIO_VERIFICATO=557&id_servizio_idp=436&__pj0=0&__pj1=ac291c86988ea187fc152a44be9f3679"
DOWNLOAD_FILE_URL = "https://beep.metid.polimi.it/documents/%d/%d/%s"


def format_size(num_bytes):
    if num_bytes < 1024:
        return "%dB" % num_bytes
    if num_bytes < 1024**2:
        return "%dKB" % (num_bytes // 1024)
    return "%.1fMB" % (num_bytes // 1024 / 1024)


def perform_beep_login(username, password):
    session = requests.Session()
    print("    Setting up session")
    session.get("https://beep.metid.polimi.it/polimi/login")
    print("    Aunicalogin step 1/3")
    session.post(BEEP_LOGIN_URL, data={
        "login": username, "password": password, "evn_conferma": ""})
    print("    Aunicalogin step 2/3")
    session.get("https://beep.metid.polimi.it/polimi/login")
    print("    Aunicalogin step 3/3")
    sso_step = session.post(BEEP_LOGIN_URL2, data={
        "SSO_LOGIN": session.cookies.get("SSO_LOGIN"),
        "MATRICOLA_SCELTA": "",
        "COOKIE_HCSS": "",
        "impersonificato": "",
        "RESTA_CONNESSO": "",
        "polij_device_category": "DESKTOP"
    }).content.decode("latin")
    sso_data = {}
    for group in re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)"\/>', sso_step):
        sso_data[unescape(group[0])] = unescape(group[1])
    print("    Shibboleth SAML login")
    session.post(
        "https://beep.metid.polimi.it/Shibboleth.sso/SAML2/POST", data=sso_data)
    print("    Login succesful: JSESSIONID=%s" %
          session.cookies.get("JSESSIONID"))
    return session.cookies


def get_json(url, username, password):
    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)
    response = session.get(url, stream=True)
    return json.loads(response.content.decode("latin"))


def get_folder(name, repo_id, folder_id, indent, username, password):
    files = get_json(GET_FILES_URL % (repo_id, folder_id), username, password)
    folders = get_json(GET_SUBFOLDERS_URL %
                       (repo_id, folder_id), username, password)
    structure = {
        "files": files,
        "folders": folders
    }
    print("    %s%s (%d files)" % ("    " * indent, name, len(files)))
    for folder in structure["folders"]:
        folder["structure"] = get_folder(
            folder["name"], repo_id, folder["folderId"], indent+1, username, password)
    return structure


def get_all(include_beep, username, password):
    url = "https://beep.metid.polimi.it/api/secure/jsonws/group/get-user-sites"
    sites = get_json(url, username, password)
    structure = {"sites": []}

    for site in sites:
        if not site["site"]:
            continue
        if not include_beep and site["name"] == "BeeP channel":
            continue
        site["structure"] = get_folder(
            site["name"], site["groupId"], 0, 0, username, password)
        structure["sites"].append(site)
    return structure


def get_site_from_cache(cache, id):
    for site in cache.get("sites", []):
        if site.get("classPK", 0) == id:
            return site
    return {}


def get_file_from_cache(cache, id):
    for f in cache.get("files", []):
        if f.get("fileEntryId", 0) == id:
            return f
    return {}


def get_folder_from_cache(cache, id):
    for f in cache.get("folders", []):
        if f.get("folderId", 0) == id:
            return f
    return {}


def get_download_list_site(site, cache, base_dir):
    size = 0
    download_size = 0
    to_download = list()
    for f in site["structure"]["files"]:
        id = f["fileEntryId"]
        cached_file = get_file_from_cache(cache.get("structure", {}), id)
        if cached_file.get("modifiedDate") != f["modifiedDate"]:
            download_size += f["size"]
            download_url = DOWNLOAD_FILE_URL % (
                f["groupId"], site.get("folderId", 0), quote(f["title"]))
            download_path = os.path.join(base_dir, f["title"])
            if not download_path.endswith(f["extension"]):
                download_path += "." + f["extension"]
            to_download.append((download_url, download_path))
        size += f["size"]
    for f in site["structure"]["folders"]:
        id = f["folderId"]
        cached_dir = get_folder_from_cache(cache.get("structure", {}), id)
        sz, down_sz, to_dl = get_download_list_site(
            f, cached_dir, os.path.join(base_dir, f["name"]))
        size += sz
        download_size += down_sz
        to_download.extend(to_dl)
    return size, download_size, to_download


def get_download_list(data, cache, out_dir):
    downloads = list()
    total_size = 0
    total_download_size = 0
    for site in data["sites"]:
        cache_site = get_site_from_cache(cache, site["classPK"])
        size, download_size, to_download = get_download_list_site(
            site, cache_site, os.path.join(out_dir, site["name"]))
        print(Style.BRIGHT + "  %s" % site["name"])
        print("      Total size: %s | To download: %s | Files to download: %d" %
              (format_size(size), format_size(download_size), len(to_download)))
        downloads.extend(to_download)
    print("  Total size: %s | To download: %s | Files to download: %d" %
          (format_size(total_size), format_size(total_download_size), len(downloads)))
    return downloads


def has_aria2():
    if shutil.which("aria2c"):
        return True
    return False


def aria2_download(to_download, cookies):
    stdin = ""
    for url, path in to_download:
        stdin += "%s\n out=%s\n" % (url, path)

    cookie_jar = ""
    for cookie in cookies:
        cookie_jar += "%s\tTRUE\t%s\t%s\t%d\t%s\t%s\n" % (
            cookie.domain, cookie.path,
            "TRUE" if cookie.secure else "FALSE",
            2000000000, cookie.name, cookie.value)

    with tempfile.NamedTemporaryFile() as f:
        f.write(cookie_jar.encode())
        f.flush()
        subprocess.run(["aria2c", "-i", "-",
                        "--load-cookies", f.name,
                        "--optimize-concurrent-downloads=true",
                        "--console-log-level=warn",
                        "--auto-save-interval=0",
                        "--allow-overwrite=true",
                        "--auto-file-renaming=false",
                        "--summary-interval=0"],
                       input=stdin.encode())


def python_download(to_download, cookies):
    session = requests.Session()
    session.cookies = cookies
    for i, (url, path) in enumerate(to_download):
        print("    Downloading %3d / %d: %s" % (i+1, len(to_download), path))
        response = session.get(url)
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)
        with open(path, "wb") as f:
            f.write(response.content)


def download(to_download, cookies):
    if has_aria2():
        print(Fore.LIGHTGREEN_EX + "  Using fast aria2 download")
        aria2_download(to_download, cookies)
    else:
        print(Fore.LIGHTRED_EX + "  aria2c not found, using slow python downloader")
        python_download(to_download, cookies)


def get_cache(cache_path):
    if not os.path.exists(cache_path):
        return {"sites": []}
    with open(cache_path, "r") as f:
        try:
            return json.loads(f.read())
        except:
            print(Style.BRIGHT + Fore.RED + "Corrupted cache!")
            os.remove(cache_path)
            return {"sites": []}


def parse_args():
    parser = argparse.ArgumentParser(description="BeeP downloader")
    parser.add_argument("--person-code", help="Person code of BeeP")
    parser.add_argument("--password", help="Password of BeeP")
    parser.add_argument("--out-dir", default="results",
                        help="Destination directory")
    parser.add_argument("--no-cache", action="store_true",
                        help="Download everything again ignoring the cache")
    parser.add_argument("--include-beep", action="store_true",
                        help="Include useless 'BeeP channe' course")
    return parser.parse_args()


if __name__ == "__main__":
    init(autoreset=True)
    print(Style.BRIGHT + Fore.LIGHTGREEN_EX + "Welcome to Beep downloader")
    args = parse_args()

    if not args.person_code or not args.password:
        print(Style.BRIGHT + Fore.LIGHTCYAN_EX +
              "Step 0: Please enter polimi credentials")
        if not args.person_code:
            username = input("Person code: " + Fore.RESET)
        else:
            username = args.person_code
        if not args.password:
            password = getpass.getpass()
        else:
            password = args.password
    else:
        username = args.person_code
        password = args.password

    print(Style.BRIGHT + Fore.LIGHTCYAN_EX + "Step 1: Fetch list of courses")
    try:
        data = get_all(args.include_beep, username, password)
    except json.decoder.JSONDecodeError:
        print(Style.BRIGHT + Fore.RED + "Login failed, maybe wrong credentials?")
        exit(1)

    cache_path = os.path.join(args.out_dir, "cache.json")
    if args.no_cache:
        cache = {"sites": []}
    else:
        cache = get_cache(cache_path)

    print(Style.BRIGHT + Fore.LIGHTCYAN_EX + "Step 2: Computing download size")
    to_download = get_download_list(data, cache, args.out_dir)

    if not to_download:
        print(Style.BRIGHT + Fore.LIGHTGREEN_EX + "Done! Enjoy c:")
        exit(0)

    print(Style.BRIGHT + Fore.LIGHTCYAN_EX + "Step 3: Performing BeeP login")
    cookies = perform_beep_login(username, password)

    print(Style.BRIGHT + Fore.LIGHTCYAN_EX +
          "Step 4: Downloading files into %s" % args.out_dir)
    download(to_download, cookies)

    with open(cache_path, "w") as f:
        f.write(json.dumps(data))

    print(Style.BRIGHT + Fore.LIGHTGREEN_EX + "Done! Enjoy c:")

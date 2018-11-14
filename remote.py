#!/usr/bin/env python3

import json
import requests
import os.path
from requests.auth import HTTPBasicAuth
from colorama import init, Fore, Style

from cache import get_file_from_cache, get_folder_from_cache, get_site_from_cache
from utils import format_size

GET_FILES_URL = "https://beep.metid.polimi.it/api/secure/jsonws/dlapp/get-file-entries?repositoryId=%d&folderId=%d"
GET_SUBFOLDERS_URL = "https://beep.metid.polimi.it/api/secure/jsonws/dlapp/get-folders?repositoryId=%d&parentFolderId=%d"
USER_SITES_URL = "https://beep.metid.polimi.it/api/secure/jsonws/group/get-user-sites"
DOWNLOAD_FILE_URL = "https://beep.metid.polimi.it/c/document_library/get_file?groupId=%d&folderId=%d&title=%s"


def get_json(url, username, password):
    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)
    response = session.get(url, stream=True)
    return json.loads(response.content.decode("latin"))


def get_structure(folder, repo_id, folder_id, indent, username, password):
    files = get_json(GET_FILES_URL % (repo_id, folder_id), username, password)
    folders = get_json(GET_SUBFOLDERS_URL % (repo_id, folder_id),
                       username, password)
    folder["files"] = files
    folder["folders"] = dict()
    print("    %s%s (%d files)" %
          ("    " * indent, folder["name"], len(files)))
    for f in folders:
        folder["folders"][f["folderId"]] = get_structure(f, repo_id, f["folderId"],
                                                         indent+1, username, password)
    return folder


def get_user_sites(include_beep, username, password):
    sites = get_json(USER_SITES_URL, username, password)
    structure = dict()
    for site in sites:
        if not site.get("site", True):
            continue
        if not include_beep and site["name"] == "BeeP channel":
            continue
        groupId = site["groupId"]
        folder = {"name": site["name"], "groupId": groupId}
        get_structure(folder, groupId, 0, 0, username, password)
        structure[groupId] = folder
    return structure


def download_file_url(groupId, folderId, title):
    return DOWNLOAD_FILE_URL % (groupId, folderId, title)


def get_download_list_site(site, cache, base_dir, forbidden_files):
    size = 0
    download_size = 0
    to_download = list()

    for f in site["files"]:
        fileEntryId = f["fileEntryId"]
        if fileEntryId in forbidden_files:
            continue
        cached_file = get_file_from_cache(cache, fileEntryId)
        size += f["size"]
        if cached_file.get("modifiedDate") == f["modifiedDate"]:
            continue
        groupId = f["groupId"]
        folderId = f["folderId"]
        title = f["title"]

        download_size += f["size"]
        download_url = download_file_url(groupId, folderId, title)
        download_path = os.path.join(base_dir, f["title"])
        if not download_path.endswith(f["extension"]):
            download_path += "." + f["extension"]
        to_download.append((download_url, download_path, fileEntryId))

    for folderId, f in site["folders"].items():
        cached_dir = get_folder_from_cache(cache, folderId)
        sz, down_sz, to_dl = get_download_list_site(
            f, cached_dir, os.path.join(base_dir, f["name"]), forbidden_files)
        size += sz
        download_size += down_sz
        to_download.extend(to_dl)
    return size, download_size, to_download


def get_download_list(sites, cache, out_dir, forbidden_files):
    downloads = list()
    total_size = 0
    total_download_size = 0
    for groupId, site in sites.items():
        groupId = str(groupId)
        cache_site = get_site_from_cache(cache, groupId)
        size, download_size, to_download = get_download_list_site(
            site, cache_site, os.path.join(out_dir, site["name"]), forbidden_files)
        print(Style.BRIGHT + "  %s" % site["name"])
        print("      Total size: %s | To download: %s | Files to download: %d" %
              (format_size(size), format_size(download_size), len(to_download)))
        downloads.extend(to_download)
        total_size += size
        total_download_size += download_size
    print("  Total size: %s | To download: %s | Files to download: %d" %
          (format_size(total_size), format_size(total_download_size), len(downloads)))
    return downloads

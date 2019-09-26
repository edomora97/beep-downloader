#!/usr/bin/env python3

import os.path
import json
from colorama import init, Fore, Style


def get_file_from_cache(cache, fileEntryId):
    for f in cache.get("files", []):
        if f.get("classPK") == fileEntryId or f.get("fileEntryId") == fileEntryId:
            return f
    return {}


def get_folder_from_cache(cache, folderId):
    return cache.get("folders", dict()).get(str(folderId), dict())


def get_site_from_cache(cache, groupId):
    return cache.get(groupId, dict())


def get_cache(cache_path):
    if not os.path.exists(cache_path):
        return dict()
    with open(cache_path, "r") as f:
        try:
            return json.loads(f.read())
        except:
            print(Style.BRIGHT + Fore.RED + "Corrupted cache!")
            os.remove(cache_path)
            return dict()


def get_forbidden_files(forbidden_files_path):
    if not os.path.exists(forbidden_files_path):
        return set()
    with open(forbidden_files_path, "r") as f:
        try:
            return set(json.loads(f.read()))
        except:
            print(Style.BRIGHT + Fore.RED + "Corrupted forbidden files!")
            os.remove(forbidden_files_path)
            return set()

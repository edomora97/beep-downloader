#!/usr/bin/env python3

import getpass
import argparse
import json
import os.path
from colorama import init, Fore, Style
from requests.auth import HTTPBasicAuth

from login import perform_beep_login
from remote import get_user_sites, get_download_list
from cache import get_cache, get_forbidden_files
from download import python_parallel_downloader


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
    parser.add_argument("--no-overwrite", action="store_true",
                        help="Do not overwrite existing files")
    parser.add_argument("--download-threads", type=int, default=10,
                        help="Number of threads used to download")
    parser.add_argument("--structure", action="store",
                        help="Do not query the API to get the structure but use this file instead")
    return parser.parse_args()


if __name__ == "__main__":
    init(autoreset=True)
    print(Style.BRIGHT + Fore.LIGHTGREEN_EX + "Welcome to Beep downloader")
    args = parse_args()

    if not args.person_code or not args.password:
        print(Style.BRIGHT + Fore.LIGHTCYAN_EX +
              "Please enter polimi credentials")
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

    if args.structure:
        with open(args.structure) as f:
            structure = json.load(f)
            print("Loaded %d courses" % len(structure))
    else:
        print(Style.BRIGHT + Fore.LIGHTCYAN_EX + "Fetch list of courses")
        try:
            structure = get_user_sites(args.include_beep, username, password)
        except json.decoder.JSONDecodeError:
            print(Style.BRIGHT + Fore.RED +
                  "Login failed, maybe wrong credentials?")
            exit(1)

    cache_path = os.path.join(args.out_dir, "cache.json")
    forbidden_files_path = os.path.join(args.out_dir, "forbidden.json")
    if args.no_cache:
        cache = dict()
        forbidden_files = set()
    else:
        cache = get_cache(cache_path)
        forbidden_files = get_forbidden_files(forbidden_files_path)

    print(Style.BRIGHT + Fore.LIGHTCYAN_EX + "Computing download size")
    to_download = get_download_list(
        structure, cache, args.out_dir, forbidden_files)

    if not to_download:
        print(Style.BRIGHT + Fore.LIGHTGREEN_EX + "Done! Enjoy c:")
        exit(0)

    print(Style.BRIGHT + Fore.LIGHTCYAN_EX +
          "Downloading files into %s" % args.out_dir)
    forbidden_files = python_parallel_downloader(
        username, password, to_download, args.download_threads, not args.no_overwrite,
        forbidden_files, forbidden_files_path)

    with open(cache_path, "w") as f:
        f.write(json.dumps(structure))
    with open(forbidden_files_path, "w") as f:
        f.write(json.dumps(list(forbidden_files)))

    print(Style.BRIGHT + Fore.LIGHTGREEN_EX + "Done! Enjoy c:")

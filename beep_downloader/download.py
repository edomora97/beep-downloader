#!/usr/bin/env python3

import requests
import tempfile
import subprocess
import os.path
import queue
import threading
import traceback
import json
import re
from colorama import init, Fore, Style

from beep_downloader.login import perform_beep_login
from beep_downloader.download_ui import DownloadUI, thread_print

CHUNK_SIZE = 4096


class LoginFailed(Exception):
    pass


class Unauthorized(Exception):
    pass


def _do_download(url, path, cookies, ui):
    session = requests.Session()
    session.cookies = cookies
    with session.get(url, stream=True, allow_redirects=False) as res:
        if res.status_code >= 300 and res.status_code <= 399:
            raise LoginFailed()
        if res.status_code >= 400 and res.status_code <= 499:
            raise Unauthorized()
        if "Content-Disposition" in res.headers:
            match = re.search(r'filename="([^"]+)"',
                              res.headers["Content-Disposition"])
            if match:
                filename = match.group(1)
                ext = filename.rsplit(".")[1]
                if not path.endswith(ext):
                    path = path + "." + ext
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)
        with open(path, "wb") as f:
            for chunk in res.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    ui.add_download(len(chunk))
                    f.write(chunk)


def python_parallel_downloader(username, password, to_download, parallel,
                               overwrite, forbidden_files,
                               forbidden_files_path):
    todo = queue.Queue()
    cookies = None
    done = False
    login_needed = threading.Condition()
    login_required = threading.Condition()
    done_cv = threading.Condition()
    ui = DownloadUI(len(to_download))

    for f in to_download:
        todo.put(f)

    def download_thread(num):
        nonlocal cookies
        prefix = "Downloader[%d] " % num
        while True:
            item = todo.get()
            if item is None:
                break
            url, path, fileEntryId = item
            with login_required:
                if cookies is None:
                    login_required.notify()
            with login_needed:
                while cookies is None and not done:
                    login_needed.wait()
            if done:
                todo.task_done()
                break
            try:
                ui.start_download(num, path)
                if overwrite or not os.path.exists(path):
                    _do_download(url, path, cookies, ui)
                    ui.done_download(num, path)
                else:
                    ui.done_download(num, path, skipped=True)
            except Unauthorized:
                ui.fail_download(num, "Unauthorized", path, done=True)
                forbidden_files.add(fileEntryId)
            except LoginFailed:
                ui.fail_download(num, "Session expired", path)
                todo.put(item)
                cookies = None
            except:
                ui.fail_download(num, "Download failed", path)
                traceback.print_exc()
                todo.put(item)
            finally:
                todo.task_done()

    def login_thread():
        nonlocal cookies, done
        while not done:
            with login_required:
                while cookies is not None and not done:
                    login_required.wait()
            if done:
                break
            with login_needed:
                ui.silent = True
                cookies = perform_beep_login(username, password)
                ui.silent = False
                if not cookies:
                    done = True
                    with done_cv:
                        done_cv.notify_all()
                    while not todo.empty():
                        todo.get()
                        todo.task_done()
                    login_needed.notify_all()
                    break
                login_needed.notify_all()

    def printer_thread():
        while not done:
            ui.snapshot()
            ui.print_status()
            with done_cv:
                done_cv.wait(2)

    def forbidden_files_thread():
        os.makedirs(os.path.dirname(forbidden_files_path), exist_ok=True)
        while not done:
            with open(forbidden_files_path, "w") as f:
                f.write(json.dumps(list(forbidden_files)))
                ui.silent = True
                thread_print("Saved snapshot of forbidden files: %d files" %
                             len(forbidden_files))
                ui.silent = False
            with done_cv:
                done_cv.wait(10)

    login = threading.Thread(target=login_thread)
    login.start()
    printer = threading.Thread(target=printer_thread)
    printer.start()
    forbidden_files_thr = threading.Thread(target=forbidden_files_thread)
    forbidden_files_thr.start()
    threads = []
    for num in range(parallel):
        thread = threading.Thread(target=download_thread, args=(num, ))
        thread.start()
        threads.append(thread)

    todo.join()
    for _ in range(parallel):
        todo.put(None)
    for thread in threads:
        thread.join()
    done = True
    with done_cv:
        done_cv.notify_all()
    with login_required:
        login_required.notify_all()
    login.join()
    printer.join()
    forbidden_files_thr.join()
    ui.done()

    return forbidden_files

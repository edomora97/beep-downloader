#!/usr/bin/env python3

import math
import time
from colorama import init, Fore, Style

from beep_downloader.utils import format_size


def thread_print(*args, end="\n"):
    print(" ".join(map(str, args)) + end, end="")


class DownloadUI:
    def __init__(self, num_files):
        self.num_files = num_files
        self.todo = num_files
        self.doing = 0
        self.silent = False
        self.digits = int(math.log10(num_files or 1))+1
        self.downloaded = 0
        self.current_speed = 0
        self.last_snapshot = None

    def start_download(self, thread, path):
        thread_print(
            "{}[Downloader{:2}] Downloading | {}".format(Fore.YELLOW, thread, path))
        self.doing += 1
        self.print_status()

    def done_download(self, thread, path, skipped=False):
        skipped = " [skipped]" if skipped else ""
        thread_print(
            "{}[Downloader{:2}] Downloaded  | {} {}".format(Fore.GREEN, thread, path, skipped))
        self.doing -= 1
        self.todo -= 1
        self.print_status()

    def fail_download(self, thread, reason, path, done=False):
        thread_print(
            "{}[Downloader{:2}]   Failed    | {} | {}".format(Fore.RED, thread, reason, path))
        self.doing -= 1
        if done:
            self.todo -= 1
        self.print_status()

    def print_status(self):
        if self.silent:
            return
        done = self.num_files - self.todo
        perc = done / self.num_files * 100
        thread_print(
            "\r[{:{digits}} / {}] ({:5.2f}%) CN:{} -- {}/s   \r".format(done, self.num_files, perc, self.doing, format_size(self.current_speed), digits=self.digits), end="")

    def done(self):
        thread_print(" " * 80, end="\r")

    def snapshot(self):
        now = time.monotonic()
        if self.last_snapshot is None:
            self.last_snapshot = now
            self.downloaded = 0
            return
        delta = now - self.last_snapshot
        self.current_speed = self.downloaded / delta
        self.last_snapshot = now
        self.downloaded = 0

    def add_download(self, size):
        self.downloaded += size

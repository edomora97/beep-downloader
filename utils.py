#!/usr/bin/env python3

import shutil


def format_size(num_bytes):
    if num_bytes < 1024:
        return "%dB" % num_bytes
    if num_bytes < 1024**2:
        return "%dKB" % (num_bytes // 1024)
    if num_bytes < 1024**3:
        return "%.1fMB" % (num_bytes / 1024**2)
    if num_bytes < 1024**4:
        return "%.1fGB" % (num_bytes / 1024**3)
    return "%.1fTB" % (num_bytes / 1024**4)

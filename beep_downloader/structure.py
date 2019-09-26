#!/usr/bin/env python3


def get_size(folder):
    size = 0
    for f in folder["files"]:
        size += f["size"]
    for d in folder["folders"].values():
        size += get_size(d)
    return size

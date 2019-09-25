#!/usr/bin/env python3

import json
import requests
import queue
import threading
import time
import sys
import traceback
import os.path
from requests.auth import HTTPBasicAuth

GET_SUBFOLDERS_URL = "https://beep.metid.polimi.it/api/secure/jsonws/dlapp/get-folders?repositoryId=%s&parentFolderId=%s"
GET_FILES_URL = "https://beep.metid.polimi.it/api/secure/jsonws/dlapp/get-file-entries?repositoryId=%s&folderId=%s"

USERNAME = "XXXXXXXX"
PASSWORD = "XXXXXXXX"
NUM_WORKERS = 10


def get_json(url, username, password):
    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)
    response = session.get(url, stream=True)
    return json.loads(response.content.decode("latin"))


def visit(startPoints):
    todo = queue.Queue()
    structure = dict()
    doing = set()
    done = False

    if os.path.exists("snapshot.json"):
        print("starting from snapshot")
        with open("snapshot.json") as f:
            snapshot = json.loads(f.read())
        structure = snapshot["structure"]
        print(json.dumps(structure, indent=4))
        for item in snapshot["todo"]:
            todo.put(tuple(item))
    else:
        for groupId, name in list(startPoints.items())[:50]:
            structure[groupId] = {"name": name}
            todo.put((groupId,))

    def worker():
        while True:
            item = todo.get()
            if item is None:
                break
            doing.add(item)
            try:
                d = structure[item[0]]

                print(item)
                for i in item[1:]:
                    d = d["folders"][i]
                currentId = item[-1] if len(item) > 1 else '0'
                folders = get_json(GET_SUBFOLDERS_URL % (item[0], currentId),
                                   USERNAME, PASSWORD)
                files = get_json(GET_FILES_URL % (item[0], currentId),
                                 USERNAME, PASSWORD)
                d["files"] = files
                d["folders"] = dict()
                for f in folders:
                    folderId = str(f["folderId"])
                    d["folders"][folderId] = f
                    todo.put(item + (folderId,))
                todo.task_done()
            except:
                traceback.print_exc()
                todo.task_done()
                if item is not None:
                    todo.put(item)
            doing.remove(item)

    def watchdog():
        while not done:
            print("TODO LEN:", todo.qsize(), file=sys.stderr)
            time.sleep(2)

    def snapshotter():
        while not done:
            print("saving snapshot", file=sys.stderr)
            with open("snapshot.json", "w") as f:
                f.write(json.dumps(
                    {"structure": structure, "todo": list(todo.queue)+list(doing)}))
            time.sleep(10)

    threads = []
    for _ in range(NUM_WORKERS):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)
    watchdog_thread = threading.Thread(target=watchdog)
    watchdog_thread.start()
    snapshot_thread = threading.Thread(target=snapshotter)
    snapshot_thread.start()

    todo.join()
    done = True

    for _ in range(NUM_WORKERS):
        todo.put(None)
    for thread in threads:
        thread.join()
    watchdog_thread.join()
    snapshot_thread.join()
    with open("structure.json", "w") as f:
        f.write(json.dumps(structure))


def main():
    sites = json.load(open("courses.json"))
    visit(sites)


if __name__ == "__main__":
    main()

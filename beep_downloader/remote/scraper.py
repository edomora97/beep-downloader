import requests
from bs4 import BeautifulSoup
import re
import datetime

from beep_downloader.remote import Remote
from beep_downloader.remote.json import get_download_list
from beep_downloader.login import perform_beep_login


class ScraperRemote(Remote):
    def get_user_sites(self, include_beep, username, password):
        cookies = perform_beep_login(username, password)
        session = requests.Session()
        session.cookies = cookies
        res = session.get("https://beep.metid.polimi.it/polimi/login")
        content = BeautifulSoup(res.content.decode("latin"), 'html.parser')
        data = get_user_sites(session, content)
        return data

    def get_download_list(self, sites, cache, out_dir, forbidden_files):
        return get_download_list(sites, cache, out_dir, forbidden_files)


def get_user_sites(session, content):
    sites = dict()
    for td in content.find_all("td"):
        links = td.find_all("a")
        if len(links) != 1:
            continue
        link = links[0]
        href = link["href"]
        name = link.find("strong")
        if name is None:
            continue
        name = name.get_text()
        id = extract_site_id(href)
        if id is None:
            print("Cannot extract id of", name)
            continue
        print(name)
        files, folders = extract_course_structure(session, href, id)
        sites[id] = {"name": name, "files": files, "folders": folders}

    next = content.find("a", class_="next")
    if next is not None:
        res = session.get(next["href"])
        content = BeautifulSoup(res.content.decode("latin"), 'html.parser')
        sites.update(get_user_sites(session, content))

    return sites


def extract_site_id(href):
    res = re.search(r'groupId=(\d+)', href)
    return int(res.group(1))


def extract_course_structure(session, link, group_id):
    res = session.get(link)
    prefix = res.url.rsplit("/", 1)[0]
    suffix = "?p_p_id=20&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1&"
    data = {
        "_20_folderId": 0,
        "_20_displayStyle": "list",
        "_20_viewEntries": 0,
        "_20_viewFolders": 0,
        "_20_entryEnd": 500,
        "_20_entryStart": 0,
        "_20_folderEnd": 20,
        "_20_folderStart": 0,
        "_20_viewEntriesPage": 1,
        "p_p_id": 20,
        "p_p_lifecycle": 0,
    }
    url = prefix + "/documenti-e-media" + suffix
    res = session.post(url, data)
    content = res.content.decode("latin")
    if res.status_code == 404 or "Not Found" in content:
        url = prefix + "/materiali" + suffix
        res = session.post(url, data)
        content = res.content.decode("latin")
    if res.status_code == 404:
        return [], dict()
    content = BeautifulSoup(content, 'html.parser')
    return extract_folder(session, content, group_id, 0)


def extract_folder(session, content, group_id, folder_id):
    data = {
        "_20_folderId": 0,
        "_20_displayStyle": "list",
        "_20_viewEntries": 0,
        "_20_viewFolders": 0,
        "_20_entryEnd": 500,
        "_20_entryStart": 0,
        "_20_folderEnd": 20,
        "_20_folderStart": 0,
        "_20_viewEntriesPage": 1,
        "p_p_id": 20,
        "p_p_lifecycle": 0,
    }
    files = []
    folders = dict()
    for tr in content.find_all("tr", class_="results-row"):
        if "data-folder-id" in tr.attrs:
            new_folder_id = int(tr["data-folder-id"])
            name = tr["data-title"]
            link = tr.find("a", attrs={"data-folder": "true"})
            if link is not None:
                res = session.post(link["href"], data)
                content = res.content.decode("latin")
                content = BeautifulSoup(content, 'html.parser')
                new_files, new_folders = extract_folder(
                    session, content, group_id, new_folder_id)
                folders[new_folder_id] = {
                    "folderId": new_folder_id,
                    "name": name,
                    "files": new_files,
                    "folders": new_folders
                }
            else:
                print("??")
        elif "data-title" in tr.attrs:
            file_name = tr["data-title"]
            a = tr.find("a")
            file_id = a["data-file-entry-id"]
            size = tr.find("td", class_="col-3")
            if size is not None:
                try:
                    size = size.get_text().strip().replace(",", "")
                    num, unit = size[:-1], size[-1]
                    if unit == "k":
                        scale = 1024
                    else:
                        scale = 1
                    size = float(num) * scale
                except:
                    size = 0
            else:
                size = 0
            modified_date = tr.find("td", class_="col-5")
            if modified_date is not None:
                try:
                    modified_date = modified_date.get_text().strip()
                    modified_date = int(
                        datetime.datetime.strptime(
                            modified_date, "%d/%m/%y %H:%M").timestamp())
                except:
                    modified_date = 0
            else:
                modified_date = 0

            files.append({
                "fileEntryId": int(file_id),
                "title": file_name,
                "modifiedDate": modified_date,
                "size": size,
                "groupId": group_id,
                "folderId": folder_id,
                "extension": ""
            })
    return files, folders

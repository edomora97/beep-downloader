#!/usr/bin/env python3

import re
import requests
from html import unescape

BEEP_LOGIN_URL = "https://aunicalogin.polimi.it/aunicalogin/aunicalogin/controller/IdentificazioneUnica.do?&jaf_currentWFID=main&polij_step=0&__pj0=0&__pj1=5d4116fc58f397506f8c792adf1b1270"


login_cache = dict()


def perform_beep_login(username, password):
    if username in login_cache:
        return login_cache[username]
    session = requests.Session()
    print("    Setting up session")
    session.get("https://beep.metid.polimi.it/polimi/login")
    print("    Aunicalogin")
    res = session.post(BEEP_LOGIN_URL, data={
        "login": username, "password": password, "evn_conferma": ""})
    sso_data = {}
    for group in re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)"\/>', res.content.decode("latin")):
        sso_data[unescape(group[0])] = unescape(group[1])
    print("    Shibboleth SAML login")
    session.post(
        "https://beep.metid.polimi.it/Shibboleth.sso/SAML2/POST", data=sso_data)
    print("    Back to beep")
    session.get("https://beep.metid.polimi.it/polimi/login")
    if session.cookies.get("JSESSIONID") is None:
        print("    Login failed!")
        return None
    print("    Login succesful: JSESSIONID=%s" %
          session.cookies.get("JSESSIONID"))
    login_cache[username] = session.cookies
    return session.cookies

#!/usr/bin/env python3

import glob
import re
import html
import json


def main():
    regex = re.compile(
        r"""<a href="[^>]*groupId=([0-9]+)[^>]*><strong>([^>]*)<\/strong><\/a>""")
    courses = dict()
    for f in glob.glob("pages/*.html"):
        with open(f) as f:
            content = f.read()
            for groups in regex.findall(content):
                courses[int(groups[0])] = html.unescape(groups[1])
    print(json.dumps(courses, indent=4))


if __name__ == "__main__":
    main()

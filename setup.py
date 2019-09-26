#!/usr/bin/env python3

import os
from setuptools import setup, find_packages

setup(
    name="beep-downloader",
    version="0.0.1",
    author="Edoardo Morassutto",
    author_email="edoardo.morassutto@gmail.com",
    description="Beep downloader",
    license="MPL-2.0",
    keywords="informatics",
    url="https://github.com/edomora97/beep-downloader",
    packages=find_packages(exclude="test"),
    long_description="Beep downloader",
    entry_points={
        "console_scripts": [
            "beep-downloader = beep_downloader.__main__:main"
        ]
    })

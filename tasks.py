import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import keepachangelog
import tomli
from invoke import task
from jinja2 import Template
from writio import dump, load
from pkg_tasks import lint, test, release, coverage

@task
def docs(c, deploy=False):
    if not deploy:
        webbrowser.open("http://localhost:8000")
        c.run("mkdocs serve --verbose")
    
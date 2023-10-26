import sys
from datetime import datetime
from pathlib import Path

import keepachangelog
from invoke import task
from jinja2 import Template
from writio import dump, load
import tomli
import webbrowser


@task
def lint(c):
    c.run("isort src")
    c.run("black src")
    for file in Path("src/pylacoan/static/css").iterdir():
        c.run(f"prettier {file} -w")
    for file in Path("src/pylacoan/static/js").iterdir():
        c.run(f"prettier {file} -w")

@task
def test(c):
    c.run("pytest")
    c.run("prospector src")


@task
def docs(c, deploy=False):
    if not deploy:
        webbrowser.open("http://localhost:8000")
        c.run("mkdocs serve --verbose")
    else:
        c.run("mkdocs gh-deploy")


@task
def load_version(c):
    with open("pyproject.toml", mode="rb") as fp:
        return tomli.load(fp)["tool"]["poetry"]["version"]


@task
def release(c):
    lint(c)
    test(c)
    c.run("git commit -am 'preparing for release'")

    # current version
    version = load_version(c)

    # remove .dev suffix
    if ".dev" in version:
        c.run("poetry version patch")
    else:
        raise ValueError("No .dev in version number, aborting")
        sys.exit()

    # current version
    version = load_version(c)

    # changelog
    clpath = Path("CHANGELOG.md")
    if clpath.is_file():
        if "dev" not in version and version not in keepachangelog.to_dict(
            "CHANGELOG.md"
        ):
            keepachangelog.release(clpath, new_version=version)

    # update CITATION.cff
    citpath = Path("etc/CITATION.cff")
    if citpath.is_file():
        metadata = {
            "version": version,
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        template = load(citpath)
        j2_template = Template(template)
        dump(j2_template.render(metadata), "CITATION.cff")
    c.run("git add CITATION.cff")

    # push
    c.run(f"git commit -am 'release v{version}'")
    c.run(f"git tag -a 'v{version}' -m 'v{version} release'")
    c.run("git push --tags")

    # release to pypi
    c.run("poetry publish --build --skip-existing")
    c.run("rm -rf dist")

    # increase version number (default: patch)
    c.run("poetry version patch")

    # add .dev suffix
    new_version = load_version(c)
    c.run(f"poetry version {new_version}.dev")
    c.run("git commit -am 'bump'; git push")
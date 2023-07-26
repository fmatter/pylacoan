import logging
import sys
from pathlib import Path
import click
import colorlog
from pylacoan.clitools import parse_csvs


handler = colorlog.StreamHandler(None)
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(levelname)-7s%(reset)s %(message)s")
)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.propagate = False
log.addHandler(handler)


sys.path.append(str(Path.cwd()))
PIPELINE = "conf.py"


@click.group()
def main():
    pass


@main.command()
@click.option("--limit", default=None, type=int)
@click.option("--text", default=None)
def cli(limit, text):
    from cliconf import (
        INPUT_FILE,
    )  # pylint: disable=import-outside-toplevel,import-error
    from cliconf import OUTPUT_FILE
    from cliconf import pipeline
    from cliconf import pos_list

    parse_csvs(pipeline, INPUT_FILE, OUTPUT_FILE, pos_list)


@main.command()
def web():
    from pylacoan.server import run_server

    run_server()

import logging
from pylacoan import run_pipeline
import click
from pathlib import Path
import sys

sys.path.append(str(Path.cwd()))

log = logging.getLogger(__name__)

PIPELINE = "pylacoan_pipeline.py"


def load_pipeline():
    if Path(PIPELINE).is_file():
        print("WEE")
        print(Path.cwd())
        print(sys.path)
        from pylacoan_pipeline import parser_list
        return parser_list
    else:
        log.error(f"{PIPELINE} not found")
        sys.exit(1)


@click.group()
def main():
    pass


@main.command()
def run():
    parser_list = load_pipeline()
    run_pipeline(parser_list)


@main.command()
@click.argument('key')
@click.argument('value')
def reparse(key, value):
    parser_list = load_pipeline()
    print(parser_list)

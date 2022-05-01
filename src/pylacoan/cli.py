import logging
import sys
from pathlib import Path
import click
from pylacoan import run_pipeline
from pylacoan import reparse as preparse


sys.path.append(str(Path.cwd()))

log = logging.getLogger(__name__)

PIPELINE = "pylacoan_pipeline.py"


def load_pipeline():
    if Path(PIPELINE).is_file():
        from pylacoan_pipeline import parser_list
        from pylacoan_pipeline import OUTPUT_FILE
        from pylacoan_pipeline import INPUT_FILE
        return parser_list, INPUT_FILE, OUTPUT_FILE
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
@click.argument("key")
def reparse(key):
    parser_list, in_f, out_f = load_pipeline()
    for parser in parser_list:
        parser.clear(key)
    preparse(parser_list, out_f, key)
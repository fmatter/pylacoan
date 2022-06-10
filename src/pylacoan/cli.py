import logging
import sys
from pathlib import Path
import click
from pylacoan import run_pipeline
from pylacoan.annotator import (
    INPUT_DIR,
    define_file_path,
    reparse_text,
    reparse_ex,
    parse_df,
)
import pandas as pd

sys.path.append(str(Path.cwd()))

log = logging.getLogger(__name__)

PIPELINE = "pylacoan_pipeline.py"


def load_pipeline():
    if Path(PIPELINE).is_file():
        from pylacoan_pipeline import INPUT_FILE
        from pylacoan_pipeline import OUTPUT_FILE
        from pylacoan_pipeline import parser_list

        return parser_list, INPUT_FILE, OUTPUT_FILE
    else:
        log.error(f"{PIPELINE} not found")
        sys.exit(1)


@click.group()
def main():
    pass


@main.command()
def run():
    parser_list, in_f, out_f = load_pipeline()
    run_pipeline(parser_list, in_f, out_f)


@main.command()
@click.argument("keys", nargs=-1)
@click.option("--file", nargs=1, default="all")
@click.option("--keep", is_flag=True, default=False)
@click.option("--automatic", is_flag=True, default=False)
def reparse(keys, file, keep, automatic):
    parser_list, in_f, out_f = load_pipeline()
    if keys == ():
        for filename in define_file_path(in_f, INPUT_DIR):
            if file == "all" or filename.stem == file:
                df = pd.read_csv(filename, index_col="ID", keep_default_na=False)
                if not keep:
                    for i, row in df.iterrows():
                        for parser in parser_list:
                            parser.clear(i)
                reparse_text(parser_list, out_f, filename.stem, interactive=not automatic)
    else:
        for sentence_id in keys:
            if not keep:
                for parser in parser_list:
                    parser.clear(sentence_id)
            reparse_ex(parser_list, out_f, sentence_id, interactive=not automatic)


@main.command()
@click.argument("keys", nargs=-1)
@click.option("--file", nargs=1, default="all")
@click.option("--automatic", is_flag=True, default=False)
def parse(keys, file, automatic):
    parser_list, in_f, out_f = load_pipeline()
    if keys == ():
        for filename in define_file_path(in_f, INPUT_DIR):
            if file == "all" or filename.stem == file:
                df = pd.read_csv(filename, index_col="ID", keep_default_na=False)
                parse_df(parser_list, out_f, df, interactive=not automatic)
    else:
        for key in keys:
            for filename in define_file_path(in_f, INPUT_DIR):
                if filename.stem == key:
                    df = pd.read_csv(filename, index_col="ID", keep_default_na=False)
                    parse_df(parser_list, out_f, df, interactive=not automatic)

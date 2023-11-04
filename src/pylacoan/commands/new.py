"""
Initialize a new pylocan project.
"""
# credit to https://github.com/clld/clld/blob/05b9fb415fe52ec7573b537de41fd6711f75be97/src/clld/commands/create.py

import pathlib

from cookiecutter.exceptions import OutputDirExistsException
from cookiecutter.main import cookiecutter

import pylacoan


def register(parser):
    parser.add_argument(
        "-f",
        "--force",
        default=True,
        help="Overwrite an existing project directory",
        action="store_true",
    )
    parser.add_argument(
        "--out",
        help="Directory in which to create the skeleton",
        type=pathlib.Path,
        default=pathlib.Path("."),
    )


def run(args):
    try:
        cookiecutter(
            str(pathlib.Path(pylacoan.__file__).parent / "project_template"),
            overwrite_if_exists=args.force,
            output_dir=str(args.out),
        )
    except OutputDirExistsException as e:
        print(e)
        print("Run with --force option to overwrite!")
        raise ValueError()

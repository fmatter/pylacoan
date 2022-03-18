# credit to https://github.com/clld/clld/blob/f18f67f78e25a55eac31f4b8cb5ba8bb60ce39dd/src/clld/__main__.py
from clldutils.clilib import register_subcommands, get_parser_and_subparsers
from clldutils.loglib import Logging
import pylacoan.commands
import contextlib


def main(args=None, catch_all=False, parsed_args=None, log=None):
    parser, subparsers = get_parser_and_subparsers("pylacoan")
    register_subcommands(subparsers, pylacoan.commands)

    args = parsed_args or parser.parse_args(args=args)

    if not hasattr(args, "main"):  # pragma: no cover
        parser.print_help()
        return 1

    with contextlib.ExitStack() as stack:
        if not log:
            stack.enter_context(Logging(args.log, level=args.log_level))
        else:
            args.log = log
        try:
            return args.main(args) or 0
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            if catch_all:
                print(e)
                return 1
            raise


if __name__ == "__main__":
    sys.exit(main() or 0)

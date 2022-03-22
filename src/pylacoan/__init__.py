"""Top-level package for pylacoan."""

from pylacoan.annotator import *  # noqa: F401, F403

__author__ = """Florian Matter"""
__email__ = "florianmatter@gmail.com"
__version__ = "0.0.2.dev"

import colorlog
import logging


level = logging.DEBUG
logging.basicConfig(level=level)
handler = colorlog.StreamHandler(None)
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(levelname)-7s%(reset)s %(message)s")
)
log = logging.getLogger(__name__)
log.setLevel(level)
log.propagate = False
log.addHandler(handler)

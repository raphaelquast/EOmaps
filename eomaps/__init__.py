from pathlib import Path

__version__ = (Path(__file__).parents[1] / "VERSION").read_text().strip()

__author__ = "Raphael Quast"

from .eomaps import Maps

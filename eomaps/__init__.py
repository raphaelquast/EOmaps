from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    pass

__author__ = "Raphael Quast"

from .eomaps import Maps

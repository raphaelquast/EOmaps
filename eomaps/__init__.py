from .eomaps import Maps
from .mapsgrid import MapsGrid
from ._version import __version__

__author__ = "Raphael Quast"


# Follow conventions used by cartopy to setup cache directory
# (copied from cartopy's __init__.py file)
import os.path

# for the writable data directory (i.e. the one where new data goes), follow
# the XDG guidelines found at
# https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html

_writable_dir = os.path.join(os.path.expanduser("~"), ".local", "share")
_data_dir = os.path.join(os.environ.get("XDG_DATA_HOME", _writable_dir), "eomaps")

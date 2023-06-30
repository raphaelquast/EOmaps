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


# -----------------------------------------------------------------------------------
# The following loggin config is adapted from matplotlibs way of dealing with logging
# (see https://github.com/matplotlib/matplotlib/blob/main/lib/matplotlib/__init__.py)

import logging
import functools

_log = logging.getLogger(__name__)
_log.setLevel(logging.WARNING)


@functools.cache
def _ensure_handler():
    """
    The first time this function is called, attach a `StreamHandler` using the
    same format as `logging.basicConfig` to the EOmaps root logger.

    Return this handler every time this function is called.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    _log.addHandler(handler)
    return handler


def set_loglevel(level):
    """
    Configure EOmaps's logging levels.

    EOmaps uses the standard library `logging` framework under the root
    logger 'eomaps'.  This is a helper function to:

    - set EOmaps's root logger level
    - set the root logger handler's level, creating the handler
      if it does not exist yet

    Typically, one should call ``set_loglevel("info")`` or
    ``set_loglevel("debug")`` to get additional debugging information.

    Users or applications that are installing their own logging handlers
    may want to directly manipulate ``logging.getLogger('eomaps')`` rather
    than use this function.

    Parameters
    ----------
    level : {"notset", "debug", "info", "warning", "error", "critical"}
        The log level of the handler.

    Notes
    -----
    The first time this function is called, an additional handler is attached
    to the root handler of EOmaps; this handler is reused every time and this
    function simply manipulates the logger and handler's level.

    """
    _log.setLevel(level.upper())
    _ensure_handler().setLevel(level.upper())


# -----------------------------------------------------------------------------------

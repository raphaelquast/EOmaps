# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

import importlib.metadata
from .helpers import register_modules as _register_modules

# address numpy runtime warning concerning binary incompatibility when
# reading NetCDF files (see https://github.com/pydata/xarray/issues/7259)
_register_modules("netCDF4", raise_exception=False)

from .eomaps import Maps
from .mapsgrid import MapsGrid

__version__ = importlib.metadata.version("eomaps")
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
# The following login config is adapted from matplotlibs way of dealing with logging
# (see https://github.com/matplotlib/matplotlib/blob/main/lib/matplotlib/__init__.py)

import logging
from functools import lru_cache

_log = logging.getLogger(__name__)
_log.setLevel(logging.WARNING)


@lru_cache()
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


def _set_logfmt(fmt=None, datefmt=None):
    """
    Set the format string for the logger.
    See `logging.Formatter` for details.

    Parameters
    ----------
    fmt : str
        The logging format string.
        The default is:  "%(levelname)s: %(asctime)s: %(message)s"
    datefmt : str
        The datetime format string. ('%Y-%m-%d,%H:%M:%S.%f')
    """
    if fmt is None:
        fmt = "%(levelname)s: %(asctime)s: %(message)s"

    handler = _ensure_handler()
    if datefmt is None:
        handler.setFormatter(logging.Formatter(fmt))
    else:
        handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))


_log_format_presets = {
    "minimal": ("%(asctime)s.%(msecs)03d: %(message)s", "%H:%M:%S"),
    "timed": (
        "%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        "%H:%M:%S",
    ),
    "debug": (
        "%(asctime)s.%(msecs)03d %(levelname)s: %(name)s: %(message)s",
        "%H:%M:%S",
    ),
    "plain": ("%(message)s", None),
}


def set_loglevel(level, fmt="timed"):
    """
    Configure EOmaps's logging levels (and formatting).

    EOmaps uses the standard library `logging` framework under the root
    logger 'eomaps'.  This is a helper function to:

    - set EOmaps's root logger level
    - set the root logger handler's level, creating the handler
      if it does not exist yet
    - set the root logger handler's formatter

    Typically, one should call ``set_loglevel("info")`` or
    ``set_loglevel("debug")`` to get additional debugging information.

    Users or applications that are installing their own logging handlers
    may want to directly manipulate ``logging.getLogger('eomaps')`` rather
    than use this function.

    Parameters
    ----------
    level : {"notset", "debug", "info", "warning", "error", "critical"} or int
        The log level of the handler.
    fmt : str
        A short-name or a logging format-string.

        Available short-names:

        - "plain": ``message``
        - "basic": ``<TIME>: message``
        - "timed": ``<TIME>: <LEVEL>: message``
        - "debug": ``<TIME>: <LEVEL>: <MODULE>: message``

        The default is ``logging.BASIC_FORMAT``

        >>> "%(levelname)s:%(name)s:%(message)s"

    Notes
    -----
    The first time this function is called, an additional handler is attached
    to the root handler of EOmaps; this handler is reused every time and this
    function simply manipulates the logger and handler's level.

    """
    if isinstance(level, str):
        level = level.upper()

    _log.setLevel(level)
    _ensure_handler().setLevel(level)

    if fmt is not None:
        _set_logfmt(*_log_format_presets.get(fmt, (fmt,)))


# -----------------------------------------------------------------------------------

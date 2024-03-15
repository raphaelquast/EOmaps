# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

import logging
from textwrap import dedent, indent, fill
from operator import attrgetter
from inspect import signature, _empty
from types import SimpleNamespace

from .helpers import register_modules

_log = logging.getLogger(__name__)


class DataSpecs(object):
    """Container for accessing the data-properties."""

    def __init__(
        self,
        m,
        data=None,
        x=None,
        y=None,
        crs=4326,
        parameter=None,
        encoding=None,
        cpos="c",
        cpos_radius=None,
    ):
        self._m = m
        self.data = data
        self.x = x
        self.y = y
        self.crs = crs
        self.parameter = parameter

        self._encoding = encoding
        self._cpos = cpos
        self._cpos_radius = cpos_radius

    def delete(self):
        self._data = None
        self._x = None
        self._y = None
        self._crs = None
        self._parameter = None
        self._encoding = False
        self._cpos = "c"
        self._cpos_radius = False

    def __repr__(self):
        try:
            txt = f"""\
                  # parameter: {self.parameter}
                  # x: {indent(fill(self.x.__repr__(), 60),
                                    "                      ").strip()}
                  # y: {indent(fill(self.y.__repr__(), 60),
                                    "                      ").strip()}

                  # crs: {indent(fill(self.crs.__repr__(), 60),
                                 "                      ").strip()}

                  # data: {indent(self.data.__repr__(),
                                  "                ").lstrip()}
                  """
            if self.encoding:
                txt += dedent(
                    f"""\
                    # encoding: {indent(fill(self.encoding.__repr__(), 60),
                    "                ").lstrip()}
                    """
                )
            if self.cpos_radius:
                txt += f"# cpos: {'self.cpos'} (cpos_radius={self.cpos_radius})"

            return dedent(txt)
        except:
            return object.__repr__(self)

    def __getitem__(self, key):
        if isinstance(key, (list, tuple)):
            for i in key:
                assert i in self.keys(), f"{i} is not a valid data-specs key!"
            if len(key) == 0:
                item = dict()
            else:
                key = list(key)
                if len(key) == 1:
                    item = {key[0]: getattr(self, key[0])}
                else:
                    item = dict(zip(key, attrgetter(*key)(self)))
        else:
            assert key in self.keys(), f"{key} is not a valid data-specs key!"
            item = getattr(self, key)
        return item

    def __setitem__(self, key, val):
        key = self._sanitize_keys(key)
        return setattr(self, key, val)

    def __setattr__(self, key, val):
        key = self._sanitize_keys(key)
        super().__setattr__(key, val)

    def __iter__(self):
        return iter(self[self.keys()].items())

    def _sanitize_keys(self, key):
        # pass any keys starting with _
        if key.startswith("_"):
            return key

        assert key in [
            *self.keys(),
        ], f"{key} is not a valid data-specs key!"

        return key

    def keys(self):
        return (
            "parameter",
            "x",
            "y",
            "crs",
            "data",
            "encoding",
            "cpos",
            "cpos_radius",
        )

    @property
    def data(self):
        """The data assigned to this Maps-object."""
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    @property
    def crs(self):
        """The projection of the data-coordinates."""
        return self._crs

    @crs.setter
    def crs(self, crs):
        self._crs = crs

    @property
    def x(self):
        """The x-coordinate values of the data (or the name of the column to use)."""
        return self._x

    @x.setter
    def x(self, x):
        self._x = x

    @property
    def y(self):
        """The y-coordinate values of the data (or the name of the column to use)."""
        return self._y

    @y.setter
    def y(self, y):
        self._y = y

    @property
    def parameter(self):
        """The name of the parameter (or the name of the column to use as parameter)."""
        return self._parameter

    @parameter.setter
    def parameter(self, parameter):
        self._parameter = parameter

    @parameter.getter
    def parameter(self):
        if self._parameter is None:
            (pd,) = register_modules("pandas", raise_exception=False)

            if (
                pd
                and isinstance(self.data, pd.DataFrame)
                and not any(i is None for i in (self.data, self.x, self.y))
            ):
                try:
                    self.parameter = next(
                        i for i in self.data.keys() if i not in [self.x, self.y]
                    )
                    _log.info(f"EOmaps: Parameter was set to: '{self.parameter}'")

                except Exception:
                    _log.error(
                        "EOmaps: Parameter-name could not be identified!"
                        "Check the data-specs!"
                    )

        return self._parameter

    @property
    def encoding(self):
        """The encoding of the data-values."""
        return self._encoding

    @encoding.setter
    def encoding(self, encoding):
        if encoding not in [None, False]:
            assert isinstance(encoding, dict), "EOmaps: encoding must be a dictionary!"
        self._encoding = encoding

    @property
    def cpos(self):
        """Indicator if the coordinates represent center- or corner-positions."""
        return self._cpos

    @cpos.setter
    def cpos(self, cpos):
        self._cpos = cpos

    @property
    def cpos_radius(self):
        """The pixel-extent used for determining corner-positions."""
        return self._cpos_radius

    @cpos_radius.setter
    def cpos_radius(self, cpos_radius):
        self._cpos_radius = cpos_radius


class ClassifySpecs(object):
    """
    a container for accessing the data classification specifications

    SCHEMES : accessor Namespace for the available classification-schemes

    """

    def __init__(self, m):
        self._defaults = dict()

        self._keys = set()
        self._m = m
        self.scheme = None

    def __repr__(self):
        txt = f"# scheme: {self.scheme}\n" + "\n".join(
            f"# {key}: {indent(fill(self[key].__repr__(), 60),  ' '*(len(key) + 4)).strip()}"
            for key in list(self.keys())
        )
        return txt

    def __getitem__(self, key):
        if isinstance(key, (list, tuple, set)):
            if len(key) == 0:
                item = dict()
            else:
                key = list(key)
                if len(key) == 1:
                    item = {key[0]: getattr(self, key[0])}
                else:
                    item = dict(zip(key, attrgetter(*key)(self)))
        else:
            item = getattr(self, key)
        return item

    def __setitem__(self, key, val):
        return setattr(self, key, val)

    def __setattr__(self, key, val):
        if not key.startswith("_") and key != "scheme":
            assert self.scheme is not None, "please specify the scheme first!"
            assert key in self._defaults, (
                f"The key is not a valid argument of the '{self.scheme}' classification!"
                + f" ...possible parameters are: {self._defaults}"
            )

            self._keys.add(key)

        super().__setattr__(key, val)

    def __iter__(self):
        return iter(self[self.keys()].items())

    def keys(self):
        return self._keys

    @property
    def scheme(self):
        """The name of the used classification scheme"""
        return self._scheme

    @scheme.setter
    def scheme(self, val):
        self._scheme = val
        self._keys = set()
        s = self._get_default_args()
        if len(self._keys) > 0:
            _log.info(f"EOmaps: classification has been reset to '{val}{s}'")
        for key, val in self._defaults.items():
            if val != _empty:
                setattr(self, key, val)

    def _get_default_args(self):
        if hasattr(self, "_scheme") and self._scheme is not None:
            (mapclassify,) = register_modules("mapclassify")

            assert self._scheme in mapclassify.CLASSIFIERS, (
                f"the classification-scheme '{self._scheme}' is not valid... "
                + " use one of:"
                + ", ".join(mapclassify.CLASSIFIERS)
            )
            s = signature(getattr(mapclassify, self._scheme))
            self._defaults = {
                key: val.default for key, val in s.parameters.items() if str(key) != "y"
            }
        else:
            self._defaults = dict()
            s = None
        return s

    def _set_scheme_and_args(self, scheme, **kwargs):
        reset = False
        if len(self._keys) > 0:
            reset = True
            self._keys = set()

        self._scheme = scheme
        _ = self._get_default_args()
        for key, val in self._defaults.items():
            setattr(self, key, val)
        for key, val in kwargs.items():
            setattr(self, key, val)

        args = (
            "("
            + ", ".join([f"{key}={self[key]}" for key, val in self._defaults.items()])
            + ")"
        )

        if reset:
            _log.info(f"EOmaps: classification has been reset to '{scheme}{args}'")

    @property
    def SCHEMES(self):
        """
        accessor for possible classification schemes
        """
        (mapclassify,) = register_modules("mapclassify")

        return SimpleNamespace(
            **dict(zip(mapclassify.CLASSIFIERS, mapclassify.CLASSIFIERS))
        )

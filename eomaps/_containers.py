from textwrap import dedent, indent, fill

from warnings import warn
from operator import attrgetter
from inspect import signature, _empty
from types import SimpleNamespace


pd = None


def _register_pandas():
    global pd
    try:
        import pandas as pd
    except ImportError:
        return False

    return True


gpd = None


def _register_geopandas():
    global gpd
    try:
        import geopandas as gpd
    except ImportError:
        return False

    return True


mapclassify = None


def _register_mapclassify():
    global mapclassify
    try:
        import mapclassify
    except ImportError:
        return False

    return True


class data_specs(object):
    """
    a container for accessing the data-properties
    """

    def __init__(
        self,
        m,
        data=None,
        x="lon",
        y="lat",
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
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    @property
    def crs(self):
        return self._crs

    @crs.setter
    def crs(self, crs):
        self._crs = crs

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        self._x = x

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, y):
        self._y = y

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, parameter):
        self._parameter = parameter

    @parameter.getter
    def parameter(self):

        if (
            self._parameter is None
            and _register_pandas()
            and isinstance(self.data, pd.DataFrame)
        ):
            if self.data is not None and self.x is not None and self.y is not None:

                try:
                    self.parameter = next(
                        i for i in self.data.keys() if i not in [self.x, self.y]
                    )
                    print(f"EOmaps: Parameter was set to: '{self.parameter}'")

                except Exception:
                    warn(
                        "EOmaps: Parameter-name could not be identified!"
                        + "\nCheck the data-specs!"
                    )

        return self._parameter

    @property
    def encoding(self):
        return self._encoding

    @encoding.setter
    def encoding(self, encoding):
        if encoding not in [None, False]:
            assert isinstance(encoding, dict), "EOmaps: encoding must be a dictionary!"
        self._encoding = encoding

    @property
    def cpos(self):
        return self._cpos

    @cpos.setter
    def cpos(self, cpos):
        self._cpos = cpos

    @property
    def cpos_radius(self):
        return self._cpos_radius

    @cpos_radius.setter
    def cpos_radius(self, cpos_radius):
        self._cpos_radius = cpos_radius


class classify_specs(object):
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
        return self._scheme

    @scheme.setter
    def scheme(self, val):
        self._scheme = val
        self._keys = set()
        s = self._get_default_args()
        if len(self._keys) > 0:
            print(f"EOmaps: classification has been reset to '{val}{s}'")
        for key, val in self._defaults.items():
            if val != _empty:
                setattr(self, key, val)

    def _get_default_args(self):
        if hasattr(self, "_scheme") and self._scheme is not None:
            assert _register_mapclassify(), (
                "EOmaps: Missing dependency: 'mapclassify' \n ... please install"
                + " (conda install -c conda-forge mapclassify) to use data-classifications."
            )

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
            print(f"EOmaps: classification has been reset to '{scheme}{args}'")

    @property
    def SCHEMES(self):
        """
        accessor for possible classification schemes
        """
        assert _register_mapclassify(), (
            "EOmaps: Missing dependency: 'mapclassify' \n ... please install"
            + " (conda install -c conda-forge mapclassify) to use data-classifications."
        )

        return SimpleNamespace(
            **dict(zip(mapclassify.CLASSIFIERS, mapclassify.CLASSIFIERS))
        )

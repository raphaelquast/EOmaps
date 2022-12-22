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


class map_objects(object):
    """
    A container for accessing objects of the generated figure

        - f : the matplotlib figure
        - ax : the geo-axes used for plotting the map
        - ax_cb : the axis of the colorbar
        - ax_cb_plot : the axis used to plot the histogram on top of the colorbar
        - cb : the matplotlib colorbar-instance
        - gridspec : the matplotlib GridSpec instance
        - cb_gridspec : the GridSpecFromSubplotSpec for the colorbar and the histogram
        - coll : the collection representing the data on the map

    """

    def __init__(
        self,
        m=None,
    ):
        self._m = m

        self._coll = None  # self.coll is assigned in "m.plot_map()"
        self._figure_closed = False

    @property
    def coll(self):
        return self._coll

    @coll.setter
    def coll(self, val):
        self._coll = val

    @coll.getter
    def coll(self):
        warn(
            "EOmaps: Using `m.figure.coll` is depreciated in EOmaps v5.x."
            "Use `m.coll` instead!"
        )
        return self._coll

    @property
    def f(self):
        warn(
            "EOmaps: Using `m.figure.f` is depreciated in EOmaps v5.x."
            "Use `m.f` instead!"
        )
        # always return the figure of the parent object
        return self._m.f

    @property
    def ax(self):
        warn(
            "EOmaps: Using `m.figure.ax` is depreciated in EOmaps v5.x."
            "Use `m.ax` instead!"
        )
        ax = self._m.ax
        return ax

    @property
    def gridspec(self):
        warn(
            "EOmaps: Using `m.figure.gridspec` is depreciated in EOmaps v5.x."
            "Use `m._gridspec` instead!"
        )
        return getattr(self._m, "_gridspec", None)

    @property
    def ax_cb(self):
        warn(
            "EOmaps: Using `m.figure.ax_cb` is depreciated in EOmaps v5.x."
            "Use `m.colorbar.ax_cb` instead!"
        )
        colorbar = getattr(self._m, "colorbar", None)
        if colorbar is not None:
            return colorbar.ax_cb

    @property
    def ax_cb_plot(self):
        warn(
            "EOmaps: Using `m.figure.ax_cb_plot` is depreciated in EOmaps v5.x."
            "Use `m.colorbar.ax_cb_plot` instead!"
        )
        colorbar = getattr(self._m, "colorbar", None)
        if colorbar is not None:
            return colorbar.ax_cb_plot

    def set_colorbar_position(self, pos=None, ratio=None, cb=None):
        """
        This function is depreciated in EOmaps v5.x!

        Use the following methods instead:
        - m.colorbar.set_position
        - m.colorbar.set_hist_size
        """
        raise AssertionError(
            "EOmaps: `m.figure.set_colorbar_position` is depreciated in EOmaps v5.x! "
            "use `m.colorbar.set_position` and `m.colorbar.set_hist_size` instead."
        )


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
        **kwargs,
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
            if "crs" in key:
                key[key.index("crs")] = "in_crs"

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
            if key == "crs":
                key = "in_crs"
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

        if key == "crs":
            key = "in_crs"

        assert key in [
            *self.keys(),
            "xcoord",
            "ycoord",
        ], f"{key} is not a valid data-specs key!"

        return key

    def keys(self):
        return (
            "parameter",
            "x",
            "y",
            "in_crs",
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

    in_crs = crs

    @property
    def xcoord(self):
        warn(
            "EOmaps: `m.data_specs.xcoord` is depreciated."
            + "use `m.data_specs.x` instead!",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._x

    @xcoord.setter
    def xcoord(self, xcoord):
        warn(
            "EOmaps: `m.data_specs.xcoord` is depreciated."
            + "use `m.data_specs.x` instead!",
            DeprecationWarning,
            stacklevel=2,
        )
        self._x = xcoord

    @property
    def ycoord(self):
        warn(
            "EOmaps: `m.data_specs.ycoord` is depreciated."
            + "use `m.data_specs.y` instead!",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._y

    @ycoord.setter
    def ycoord(self, ycoord):
        warn(
            "EOmaps: `m.data_specs.ycoord` is depreciated."
            + "use `m.data_specs.y` instead!",
            DeprecationWarning,
            stacklevel=2,
        )
        self._y = ycoord

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

            # assert all(
            #     i in ["scale_factor", "add_offset"] for i in encoding
            # ), "EOmaps: encoding accepts only 'scale_factor' and 'add_offset' as keys!"

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

from textwrap import dedent, indent, fill
from warnings import warn
from operator import attrgetter
from inspect import signature, _empty
from types import SimpleNamespace
from matplotlib.pyplot import get_cmap
import mapclassify


class data_specs(object):
    """
    a container for accessing the data-properties
    """

    def __init__(
        self,
        m,
        data=None,
        xcoord=None,
        ycoord=None,
        crs=None,
        parameter=None,
    ):
        self._m = m
        self._data = None
        self._xcoord = None
        self._ycoord = None
        self._crs = None
        self._parameter = None

    def __repr__(self):
        txt = f"""\
              # parameter = {self.parameter}
              # coordinates = ({self.xcoord}, {self.ycoord})
              # crs: {indent(fill(self.crs.__repr__(), 60),
                              "                      ").strip()}

              # data:\
              {indent(self.data.__repr__(), "                ")}
              """

        return dedent(txt)

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
        if key == "crs":
            key = "in_crs"
        assert key in self.keys(), f"{key} is not a valid data-specs key!"
        return setattr(self, key, val)

    def __iter__(self):
        return iter(self[self.keys()].items())

    def keys(self):
        return ("parameter", "xcoord", "ycoord", "in_crs", "data")

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
        return self._xcoord

    @xcoord.setter
    def xcoord(self, xcoord):
        self._xcoord = xcoord

    @property
    def ycoord(self):
        return self._ycoord

    @ycoord.setter
    def ycoord(self, ycoord):
        self._ycoord = ycoord

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, parameter):
        self._parameter = parameter

    @parameter.getter
    def parameter(self):
        if self._parameter is None:
            if (
                self.data is not None
                and self.xcoord is not None
                and self.ycoord is not None
            ):

                try:
                    self.parameter = next(
                        i
                        for i in self.data.keys()
                        if i not in [self.xcoord, self.ycoord]
                    )
                    print(f"EOmaps: Parameter was set to: '{self.parameter}'")

                except Exception:
                    warn(
                        "EOmaps: Parameter-name could not be identified!"
                        + "\nCheck the data-specs!"
                    )
        return self._parameter


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
        f=None,
        ax=None,
        ax_cb=None,
        ax_cb_plot=None,
        cb=None,
        gridspec=None,
        cb_gridspec=None,
        coll=None,
    ):

        self.f = f
        self.ax = ax
        self.ax_cb = ax_cb
        self.ax_cb_plot = ax_cb_plot
        self.gridspec = gridspec
        self.cb_gridspec = cb_gridspec
        self.coll = coll

    def set_items(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    @classmethod
    def reinit(cls, **kwargs):
        return cls(**kwargs)

    # @wraps(plt.Axes.set_position)
    def set_colorbar_position(self, pos):
        """
        a wrapper to set the position of the colorbar and the histogram at
        the same time

        Parameters
        ----------
        pos : list    [left, bottom, width, height]
              in relative units [0,1] (with respect to the figure)
        """

        # get the desired height-ratio
        hratio = self.cb_gridspec.get_height_ratios()
        hratio = hratio[0] / hratio[1]

        hcb = pos[3] / (1 + hratio)
        hp = hratio * hcb

        if self.ax_cb is not None:
            self.ax_cb.set_position(
                [pos[0], pos[1], pos[2], hcb],
            )
        if self.ax_cb_plot is not None:
            self.ax_cb_plot.set_position(
                [pos[0], pos[1] + hcb, pos[2], hp],
            )


class plot_specs(object):
    """
    a container for accessing the plot specifications
    """

    def __init__(self, m, **kwargs):
        self._m = m

        for key in kwargs:
            assert key in self.keys(), f"'{key}' is not a valid data-specs key"

        for key in self.keys():
            setattr(self, key, kwargs.get(key, None))

    def __repr__(self):
        txt = "\n".join(
            f"# {key}: {indent(fill(self[key].__repr__(), 60),  ' '*(len(key) + 4)).strip()}"
            for key in self.keys()
        )
        return txt

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
        assert key in self.keys(), f"{key} is not a valid data-specs key!"
        return setattr(self, key, val)

    def __iter__(self):
        return iter(self[self.keys()].items())

    def keys(self):
        # fmt: off
        return ('label', 'title', 'cmap', 'plot_epsg', 'radius_crs', 'radius',
                'histbins', 'tick_precision', 'vmin', 'vmax', 'cpos', 'alpha',
                'add_colorbar', 'coastlines', 'density', 'shape')
        # fmt: on

    @property
    def cmap(self):
        return self._cmap

    @cmap.getter
    def cmap(self):
        return self._cmap

    @cmap.setter
    def cmap(self, val):
        self._cmap = get_cmap(val)


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
        return SimpleNamespace(
            **dict(zip(mapclassify.CLASSIFIERS, mapclassify.CLASSIFIERS))
        )

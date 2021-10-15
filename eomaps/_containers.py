from textwrap import dedent, indent, fill
from warnings import warn
from operator import attrgetter
from matplotlib.pyplot import get_cmap


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

    def keys(self):
        return ("parameter", "xcoord", "ycoord", "in_crs", "data")

    def items(self):
        return self[self.keys()].items()

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
                    print(f"Parameter was set to: '{self.parameter}'")

                except Exception:
                    warn(
                        "Parameter-name could not be identified!"
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
            item = dict(zip(key, attrgetter(*key)(self)))
        else:
            assert key in self.keys(), f"{key} is not a valid data-specs key!"
            item = getattr(self, key)
        return item

    def __setitem__(self, key, val):
        assert key in self.keys(), f"{key} is not a valid data-specs key!"
        return setattr(self, key, val)

    def keys(self):
        # fmt: off
        return ('label', 'title', 'cmap', 'plot_epsg', 'radius_crs', 'radius',
                'histbins', 'tick_precision', 'vmin', 'vmax', 'cpos', 'alpha',
                'add_colorbar', 'coastlines', 'density', 'shape')
        # fmt: on

    def items(self):
        return self[self.keys()].items()

    @property
    def cmap(self):
        return self._cmap

    @cmap.getter
    def cmap(self):
        return self._cmap

    @cmap.setter
    def cmap(self, val):
        self._cmap = get_cmap(val)

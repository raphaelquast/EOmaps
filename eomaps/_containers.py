from textwrap import dedent, indent, fill
from warnings import warn
from operator import attrgetter
from inspect import signature, _empty
from types import SimpleNamespace
from functools import lru_cache
from pathlib import Path
import json
from warnings import warn

import matplotlib.pyplot as plt
from matplotlib.pyplot import get_cmap
from matplotlib.gridspec import SubplotSpec
from matplotlib.colors import rgb2hex

import mapclassify

import cartopy.feature as cfeature
from cartopy.io import shapereader
from cartopy import crs as ccrs

from ._webmap import _import_OK

if _import_OK:
    from ._webmap import (
        _WebServiec_collection,
        REST_API_services,
        _xyz_tile_service,
    )

try:
    import pandas as pd

    _pd_OK = True
except ImportError:
    _pd_OK = False

try:
    import geopandas as gpd

    _gpd_OK = True
except ImportError:
    _gpd_OK = False


def combdoc(*args):
    return "\n".join(dedent(str(i)) for i in args)


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

        self.coll = None  # self.coll is assigned in "m.plot_map()"
        self._figure_closed = False

    @property
    def f(self):
        # always return the figure of the parent object
        return self._m.parent._f

    @property
    def ax(self):
        ax = self._m._ax

        # return None in case the plot is not yet initialized
        if isinstance(ax, SubplotSpec):
            ax = None
        return ax

    @property
    def ax_cb(self):
        return getattr(self._m, "_ax_cb", None)

    @property
    def ax_cb_plot(self):
        return getattr(self._m, "_ax_cb_plot", None)

    @property
    def gridspec(self):
        return getattr(self._m, "_gridspec", None)

    @property
    def cb_gridspec(self):
        return getattr(self._m, "_cb_gridspec", None)

    # @wraps(plt.Axes.set_position)
    def set_colorbar_position(self, pos=None, ratio=None, cb=None):
        """
        a wrapper to set the position of the colorbar and the histogram at
        the same time

        Parameters
        ----------
        pos : list    [left, bottom, width, height]
            The bounding-box of the colorbar & histogram in relative
            units [0,1] (with respect to the figure)
            If None the current position is maintained.
        ratio : float, optional
            The ratio between the size of the colorbar and the size of the histogram.
            'ratio=10' means that the histogram is 10 times as large as the colorbar!
            The default is None in which case the current ratio is maintained.
        cb : list, optional
            The colorbar-objects (as returned by `m.add_colorbar()`)
            If None, the existing colorbar will be used.
        """

        if cb is None:
            _, _, ax_cb, ax_cb_plot, orientation, _ = self._m._colorbar
        else:
            _, _, ax_cb, ax_cb_plot, orientation, _ = cb

        if orientation == "horizontal":
            pcb = ax_cb.get_position()
            pcbp = ax_cb_plot.get_position()
            if pos is None:
                pos = [pcb.x0, pcb.y0, pcb.width, pcb.height + pcbp.height]
            if ratio is None:
                ratio = pcbp.height / pcb.height

            hcb = pos[3] / (1 + ratio)
            hp = ratio * hcb

            ax_cb.set_position(
                [pos[0], pos[1], pos[2], hcb],
            )
            ax_cb_plot.set_position(
                [pos[0], pos[1] + hcb, pos[2], hp],
            )

        elif orientation == "vertical":
            pcb = ax_cb.get_position()
            pcbp = ax_cb_plot.get_position()
            if pos is None:
                pos = [pcbp.x0, pcbp.y0, pcb.width + pcbp.width, pcb.height]
            if ratio is None:
                ratio = pcbp.width / pcb.width

            wcb = pos[2] / (1 + ratio)
            wp = ratio * wcb

            ax_cb.set_position(
                [pos[0] + wp, pos[1], wcb, pos[3]],
            )
            ax_cb_plot.set_position(
                [pos[0], pos[1], wp, pos[3]],
            )
        else:
            raise TypeError(f"EOmaps: '{orientation}' is not a valid orientation")

        # re-fetch the background layer to make changes visible
        self._m.BM.fetch_bg(self._m.layer)


class data_specs(object):
    """
    a container for accessing the data-properties
    """

    def __init__(
        self,
        m,
        data=None,
        xcoord="lon",
        ycoord="lat",
        crs=4326,
        parameter=None,
    ):
        self._m = m
        self.data = data
        self.xcoord = xcoord
        self.ycoord = ycoord
        self.crs = crs
        self.parameter = parameter

    def delete(self):
        self._data = None
        self._xcoord = None
        self._ycoord = None
        self._crs = None
        self._parameter = None

    def __repr__(self):
        try:
            txt = f"""\
                  # parameter = {self.parameter}
                  # coordinates = ({self.xcoord}, {self.ycoord})
                  # crs: {indent(fill(self.crs.__repr__(), 60),
                                  "                      ").strip()}

                  # data:\
                  {indent(self.data.__repr__(), "                ")}
                  """
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

        assert key in self.keys(), f"{key} is not a valid data-specs key!"

        return key

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
        if _pd_OK and isinstance(self.data, pd.DataFrame) and self._parameter is None:
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


class plot_specs(object):
    """
    a container for accessing the plot specifications
    """

    def __init__(self, m, **kwargs):
        self._m = m

        for key in kwargs:
            assert key in self.keys(), f"'{key}' is not a valid data-specs key"

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
                assert i in self.keys(), f"{i} is not a valid plot-specs key!"
            if len(key) == 0:
                item = dict()
            else:
                key = list(key)
                if len(key) == 1:
                    item = {key[0]: getattr(self, key[0])}
                else:
                    item = dict(zip(key, attrgetter(*key)(self)))
        else:
            assert key in self.keys(), f"'{key}' is not a valid plot-specs key!"
            item = getattr(self, key)
        return item

    def __setitem__(self, key, val):
        key = self._sanitize_keys(key)
        if key is not None:
            return setattr(self, key, val)

    def __setattr__(self, key, val):
        key = self._sanitize_keys(key)
        if key is not None:
            super().__setattr__(key, val)

    def __iter__(self):
        return iter(self[self.keys()].items())

    def _sanitize_keys(self, key):
        # pass any keys starting with _
        if key.startswith("_"):
            return key

        if key in ["crs", "plot_crs"]:
            warn(
                "\n▲▲▲ In EOmaps > v3.0 the plot-crs is set on "
                + "initialization of the Maps-object!"
                + "\n▲▲▲ Use `m = Maps(crs=...)` instead to set the plot-crs!\n"
            )
            return None

        if key in ["title"]:
            warn(
                "\n▲▲▲ In EOmaps > v3.1 passing a 'title' to the plot-specs is depreciated. "
                + "\n▲▲▲ Use `m.ax.set_title()` instead!\n"
            )
            return None

        assert key in self.keys(), f"{key} is not a valid plot-specs key!"

        return key

    def keys(self):
        # fmt: off
        return ('label', 'cmap', 'histbins', 'tick_precision',
                'vmin', 'vmax', 'cpos', 'cpos_radius', 'alpha', 'density')
        # fmt: on

    @property
    def cmap(self):
        return self._cmap

    @cmap.setter
    def cmap(self, val):
        self._cmap = get_cmap(val)

    @property
    @lru_cache()
    def plot_crs(self):
        return self._m._crs_plot


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


class _NaturalEarth_presets:
    def __init__(self, m):
        self._m = m

    @property
    def coastline(self):
        """
        Add a coastline to the map.

        All provided arguments are passed to `m.add_feature`
        (and further to `m.add_gdf` if geopandas is available)

        The default args are:

        - fc="none", ec="k", zorder=100
        """
        return self._feature(
            self._m,
            "physical",
            "coastline",
            fc="none",
            ec="k",
            zorder=100,
        )

    @property
    def ocean(self):
        """
        Add ocean-coloring to the map.

        All provided arguments are passed to `m.add_feature`
        (and further to `m.add_gdf` if geopandas is available)

        The default args are:

        - fc=(0.59375, 0.71484375, 0.8828125), ec="none", zorder=0, reproject="cartopy"
        """

        # convert color to hex to avoid issues with geopandas
        color = rgb2hex(cfeature.COLORS["water"])
        return self._feature(
            self._m,
            "physical",
            "ocean",
            fc=color,
            ec="none",
            zorder=-1,
            reproject="cartopy",
        )

    @property
    def land(self):
        """
        Add a land-coloring to the map.

        All provided arguments are passed to `m.add_feature`
        (and further to `m.add_gdf` if geopandas is available)

        The default args are:

        - fc=(0.9375, 0.9375, 0.859375), ec="none", zorder=0

        """

        # convert color to hex to avoid issues with geopandas
        color = rgb2hex(cfeature.COLORS["land"])

        return self._feature(
            self._m,
            "physical",
            "land",
            fc=color,
            ec="none",
            zorder=-1,
        )

    @property
    def countries(self):
        """
        Add country-boundaries to the map.

        All provided arguments are passed to `m.add_feature`
        (and further to `m.add_gdf` if geopandas is available)

        The default args are:

        - fc="none", ec=".5", lw=0.5, zorder=99

        """

        return self._feature(
            self._m,
            "cultural",
            "admin_0_countries",
            fc="none",
            ec=".5",
            lw=0.5,
            zorder=99,
        )

    class _feature:
        def __init__(self, m, category, name, **kwargs):
            self._m = m
            self.category = category
            self.name = name

            self.kwargs = kwargs

            self.feature = getattr(
                getattr(self._m.add_feature, f"{self.category}_10m"), self.name
            )

            add_params = """
            Other Parameters
            ----------------
            scale : str
                Set the scale of the feature preset ("10m", "50m" or "110m")
                The default is "50m"
            """

            self.__doc__ = combdoc(
                f"PRESET using {kwargs} ", self.feature.__doc__, add_params
            )

        def __call__(self, scale="50m", **kwargs):
            k = dict(**self.kwargs)
            k.update(kwargs)

            self.feature = getattr(
                getattr(self._m.add_feature, f"{self.category}_{scale}"), self.name
            )

            self.__doc__ = self.feature.__doc__

            return self.feature(**k)


class NaturalEarth_features(object):
    """
    Interface to the feature-layers provided by NaturalEarth

    (see https://www.naturalearthdata.com)

    The features are grouped into the categories "cultural" and "physical"
    at 3 different scales:

    - 1:10m : Large-scale data
    - 1:50m : Medium-scale data
    - 1:110m : Small-scale data

    For available features and additional info, check the docstring of the
    individual categories!

    >>> m.add_feature.cultural_10m.< feature-name >( ... style-kwargs ...)


    Examples
    --------

    - add black (coarse resolution) coastlines
      >>> m.add_feature.physical_110m.coastline(fc="none", ec="k")

    - color all land red with 50% transparency
      >>> m.add_feature.physical_110m.land(fc="r", alpha=0.5)

    - color all countries with respect to their area
      >>> countries = m.add_feature.cultural_10m.admin_0_countries
      >>> areas = np.argsort([i.area for i in countries.feature.geometries()])
      >>> countries(ec="k", fc= [i for i in plt.cm.viridis(areas / areas.max())])
    """

    def __init__(self, m):
        self._m = m

        with open(Path(__file__).parent / "NE_features.json", "r") as file:
            features = json.load(file)

        for scale, scale_items in features.items():
            for category, category_items in scale_items.items():
                ns = {
                    name: self._feature(self._m, category, name, scale)
                    for name in category_items
                }

                c = self._category(scale, category, **ns)
                setattr(self, category + "_" + scale, c)

    @property
    def preset(self):
        """
        Access to commonly used NaturalEarth features with pre-defined styles.

        - "coastline" - black coastlines
        - "ocean" - blue ocean coloring
        - "land" - beige land coloring
        - "countries" - gray country boarder lines
        """
        return _NaturalEarth_presets(self._m)

    def __getitem__(self, key):
        return getattr(self, key)

    class _category:
        def __init__(self, scale, category, **kwargs):

            self._s = scale
            self._c = category

            for key, val in kwargs.items():
                setattr(self, key, val)

            self.__doc__ = combdoc(
                NaturalEarth_features.__doc__,
                "\nNotes\n-----\n Available NaturalEarth features for:   |   "
                + scale
                + "  "
                + category
                + "   |\n\n - "
                + "\n - ".join(kwargs),
            )

        def __repr__(self):
            return (
                f"EOmaps interface for {self._s} {self._c} " + "NaturalEarth features"
            )

    class _feature:
        def __init__(self, m, category, name, scale):
            self._m = m
            if not _gpd_OK:
                # use cartopy to add the features
                self.feature = cfeature.NaturalEarthFeature(
                    category=category, name=name, scale=scale
                )
            else:
                # just get the path to the cached download and use
                # geopandas to add the feature (provides more flexibility!)
                self.feature = dict(resolution=scale, category=category, name=name)

            if not _gpd_OK:
                self.__doc__ = dedent(
                    f"""
                    NaturalEarth feature:  {scale} | {category} | {name}

                    Call this class like a function to add the feature to the map.

                    Common style-keywords can be used to customize the appearance
                    of the added features.

                    - "facecolor" (or "fc")
                    - "edgecolor" (or "ec")
                    - "linewidth" (or "lw")
                    - "linestyle" (or "ls")
                    - "alpha", "hatch", "dashes", ...
                    - "zoder"

                    Parameters
                    ----------

                    layer : int, str or None, optional
                        The name of the layer at which map-features are plotted.

                        - If "all": the corresponding feature will be added to ALL layers
                        - If None, the layer of the parent object is used.

                        The default is None.

                    Note
                    ----
                    Some shapes consist of point-geometries which cannot be
                    properly added without `geopandas`!

                    Run the following command to install geopandas and activate
                    additional NaturalEarth features in EOmaps!

                        `conda install -c conda-forge geopandas`

                    (check the docstring again after installing to get more infos)

                    Examples
                    --------

                    >>> m = Maps()
                    >>> feature = m.add_feature.physical_10m.coastline
                    >>> feature(fc="none",
                    >>>         ec="k",
                    >>>         lw=.5,
                    >>>         ls="--",
                    >>>         )
                    """
                )
            else:
                self.__doc__ = dedent(
                    f"""
                    NaturalEarth feature:  {scale} | {category} | {name}

                    Call this class like a function to add the feature to the map.

                    All keyword-arguments are passed to `m.add_gdf` and the
                    NaturalEarth features are added to the map just like any
                    other GeoDataFrame!
                    (e.g. you can even attach callbacks if you like!)


                    Parameters
                    ----------
                    picker_name : str or None
                        A unique name that is used to identify the pick-method.

                        If a `picker_name` is provided, a new pick-container will be
                        created that can be used to pick geometries of the GeoDataFrame.

                        The container can then be accessed via:
                            >>> m.cb.pick__<picker_name>
                            or
                            >>> m.cb.pick[picker_name]
                        and it can be used in the same way as `m.cb.pick...`

                    pick_method : str or callable
                        if str :
                            The operation that is executed on the GeoDataFrame to identify
                            the picked geometry.
                            Possible values are:

                            - "contains":
                              pick a geometry only if it contains the clicked point
                              (only works with polygons! (not with lines and points))
                            - "centroids":
                              pick the closest geometry with respect to the centroids
                              (should work with any geometry whose centroid is defined)

                            The default is "centroids"
                        if callable :
                            A callable that is used to identify the picked geometry.
                            The call-signature is:

                            >>> def picker(artist, mouseevent):
                            >>>     # if the pick is NOT successful:
                            >>>     return False, dict()
                            >>>     ...
                            >>>     # if the pick is successful:
                            >>>     return True, dict(ID, pos, val, ind)
                        The default is "contains"
                    val_key : str
                        The dataframe-column used to identify values for pick-callbacks.
                        The default is None.

                    kwargs :
                        All remaining kwargs are passed to the plotting function
                        of geopandas (e.g. `gdf.plot(**kwargs)`)

                        (facecolor, edgecolor, etc.)

                    layer : int, str or None, optional
                        The name of the layer at which map-features are plotted.

                        - If "all": the corresponding feature will be added to ALL layers
                        - If None, the layer of the parent object is used.

                        The default is None.


                    Examples
                    --------

                    >>> m = Maps()
                    >>> feature = m.add_feature.physical_10m.coastline
                    >>> feature(fc="none",
                    >>>         ec="k",
                    >>>         lw=.5,
                    >>>         ls="--",
                    >>>         )

                    - make the features from NaturalEarth interactive!
                    >>> m = Maps()
                    >>> feature = m.add_feature.physical_110m.admin_0_countries
                    >>> feature(fc="none", ec="k", picker_name="countries", val_key="NAME_EN")
                    >>> m.cb.pick["countries"].attach.highlite_geometry()
                    >>> m.cb.pick["countries"].attach.annotate()


                    """
                )

        def __call__(self, layer=None, **kwargs):
            from . import MapsGrid  # do this here to avoid circular imports!

            if not _gpd_OK:
                for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                    if layer is None:
                        uselayer = m.layer
                    else:
                        uselayer = layer
                    self.feature._kwargs.update(kwargs)
                    art = m.figure.ax.add_feature(self.feature)

                    m.BM.add_bg_artist(art, layer=uselayer)
            else:
                s = self.get_gdf()
                for m in (
                    self._m if self._m.__class__.__name__ == "MapsGrid" else [self._m]
                ):
                    if layer is None:
                        uselayer = m.layer
                    else:
                        uselayer = layer

                    m.add_gdf(s, layer=uselayer, **kwargs)

        if _gpd_OK:

            def get_gdf(self):
                """
                Get a geopandas.GeoDataFrame for the selected NaturalEarth feature

                Returns
                -------
                gdf : geopandas.GeoDataFrame
                    A GeoDataFrame with all geometries and properties of the feature
                """
                gdf = gpd.read_file(shapereader.natural_earth(**self.feature))
                gdf.set_crs(ccrs.PlateCarree(), inplace=True, allow_override=True)
                return gdf


# avoid defining containers if import is not OK
if not _import_OK:
    wms_container = None
    wmts_container = None

else:

    class wms_container(object):
        """
        A collection of open-access WebMap services that can be added to the maps

        Layers can be added in 2 ways (either with . access or with [] access):
            >>> m.add_wms.< SERVICE > ... .add_layer.<LAYER-NAME>(**kwargs)
            >>> m.add_wms.< SERVICE > ... [<LAYER-NAME>](**kwargs)

        Services might be nested directory structures!
        The actual layer is always added via the `add_layer` directive.

            >>> m.add_wms.<...>. ... .<...>.add_layer.<...>()

        Some of the services dynamically fetch the structure via HTML-requests.
        Therefore it can take a short moment before autocompletion is capable
        of showing you the available options!
        A list of available layers from a sub-folder can be fetched via:

            >>> m.add_wms.<...>. ... .<...>.layers

        Note
        ----
        Make sure to check the individual service-docstrings and the links to
        the providers for licensing and terms-of-use!
        """

        def __init__(self, m):

            self._m = m

        @property
        @lru_cache()
        def ISRIC_SoilGrids(self):
            # make this a property to avoid fetching layers on
            # initialization of Maps-objects
            """
            Interface to the ISRIC SoilGrids database
            https://www.isric.org/explore/soilgrids/faq-soilgrids

            ...
            SoilGrids is a system for global digital soil mapping that makes
            use of global soil profile information and covariate data to model
            the spatial distribution of soil properties across the globe.
            SoilGrids is a collections of soil property maps for the world
            produced using machine learning at 250 m resolution.
            ...

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            check: https://www.isric.org/about/data-policy

            """
            return self._ISRIC(self._m)

        class _ISRIC:
            # since this is not an ArcGIS REST API it needs some special treatment...
            def __init__(self, m, service_type="wms"):
                self._m = m
                self._service_type = service_type
                self._fetched = False

                # default layers (see REST_API_services for details)
                self._layers = {
                    "nitrogen",
                    "phh2o",
                    "soc",
                    "silt",
                    "ocd",
                    "cfvo",
                    "cec",
                    "ocs",
                    "sand",
                    "clay",
                    "bdod",
                }

                for i in self._layers:
                    setattr(self, i, "NOT FOUND")

            def __getattribute__(self, name):
                # make sure all private properties are directly accessible
                if name.startswith("_"):
                    return object.__getattribute__(self, name)

                # fetch layers on first attempt to get a non-private attribute
                if not self._fetched:
                    self._fetch_services()

                return object.__getattribute__(self, name)

            def _fetch_services(self):
                print("EOmaps: fetching IRIS layers...")

                import requests
                import json

                if self._fetched:
                    return
                # set _fetched to True immediately to avoid issues in __getattribute__
                self._fetched = True

                layers = requests.get(
                    "https://rest.isric.org/soilgrids/v2.0/properties/layers"
                )
                _layers = json.loads(layers.content.decode())["layers"]

                found_layers = set()
                for i in _layers:
                    name = i["property"]
                    setattr(
                        self, name, _WebServiec_collection(self._m, service_type="wms")
                    )
                    getattr(
                        self, name
                    )._url = f"https://maps.isric.org/mapserv?map=/map/{name}.map"

                    found_layers.add(name)

                new_layers = found_layers - self._layers
                if len(new_layers) > 0:
                    print(f"EOmaps: ... found some new folders: {new_layers}")

                invalid_layers = self._layers - found_layers
                if len(invalid_layers) > 0:
                    print(f"EOmaps: ... could not find the folders: {invalid_layers}")
                for i in invalid_layers:
                    delattr(self, i)

                self._layers = found_layers

        @property
        @lru_cache()
        def ESA_WorldCover(self):
            """
            ESA Worldwide land cover mapping
            https://esa-worldcover.org/en

            This service can be used both as WMS and WMTS service. The default
            is to use WMS. You can change the preferred service-type on the
            initialization of the Maps-object via:

                >>> m = Maps(preferred_wms_service="wms")
                or
                >>> m = Maps(preferred_wms_service="wmts")

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            (check: https://esa-worldcover.org/en/data-access for full details)

            The ESA WorldCover product is provided free of charge,
            without restriction of use. For the full license information see the
            Creative Commons Attribution 4.0 International License.

            Publications, models and data products that make use of these
            datasets must include proper acknowledgement, including citing the
            datasets and the journal article as in the following citation.
            """
            if self._m.parent._preferred_wms_service == "wms":
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wms",
                    url="https://services.terrascope.be/wms/v2",
                )
            elif self._m.parent._preferred_wms_service == "wmts":
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wmts",
                    url="https://services.terrascope.be/wmts/v2",
                )

            WMS.__doc__ = type(self).ESA_WorldCover.__doc__
            return WMS

        @property
        @lru_cache()
        def GEBCO(self):
            """
            Global ocean & land terrain models
            https://www.gebco.net/

            GEBCO aims to provide the most authoritative, publicly available bathymetry
            data sets for the world’s oceans.

            GEBCO's current gridded bathymetric data set, the GEBCO_2021 Grid, is a
            global terrain model for ocean and land, providing elevation data, in
            meters, on a 15 arc-second interval grid. It is accompanied by a Type
            Identifier (TID) Grid that gives information on the types of source data
            that the GEBCO_2021 Grid is based.

            For this release, we are making available a version of the grid with
            under-ice topography/bathymetry information for Greenland and Antarctica.


            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            The GEBCO Grid is placed in the public domain and may be used free of charge.

            If imagery from the WMS is included in web sites, reports and digital and
            printed imagery then we request that the source of the data set is
            acknowledged and be of the form

            "Imagery reproduced from the GEBCO_2021 Grid, GEBCO Compilation Group (2021)
            GEBCO 2021 Grid (doi:10.5285/c6612cbe-50b3-0cff-e053-6c86abc09f8f)"

            (check: https://www.gebco.net/ for full details)

            """
            WMS = _WebServiec_collection(
                m=self._m,
                service_type="wms",
                url="https://www.gebco.net/data_and_products/gebco_web_services/web_map_service/mapserv?request=getcapabilities&service=wms&version=1.1.1",
            )

            WMS.__doc__ = type(self).GEBCO.__doc__
            return WMS

        @property
        @lru_cache()
        def NASA_GIBS(self):
            """
            NASA Global Imagery Browse Services (GIBS)
            https://wiki.earthdata.nasa.gov/display/GIBS/

            This service can be used both as WMS and WMTS service. The default
            is to use WMS. You can change the preferred service-type on the
            initialization of the Maps-object via:

                >>> m = Maps(preferred_wms_service="wms")
                or
                >>> m = Maps(preferred_wms_service="wmts")

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            (check: https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs)

            NASA supports an open data policy. We ask that users who make use of
            GIBS in their clients or when referencing it in written or oral
            presentations to add the following acknowledgment:

            We acknowledge the use of imagery provided by services from NASA's
            Global Imagery Browse Services (GIBS), part of NASA's Earth Observing
            System Data and Information System (EOSDIS).
            """
            if self._m._preferred_wms_service == "wms":
                WMS = self._NASA_GIBS(self._m)
            elif self._m._preferred_wms_service == "wmts":
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wmts",
                    url="https://gibs.earthdata.nasa.gov/wmts/epsg4326/all/1.0.0/WMTSCapabilities.xml",
                )

            WMS.__doc__ = type(self).NASA_GIBS.__doc__
            return WMS

        class _NASA_GIBS:
            # WMS links for NASA GIBS
            def __init__(self, m):
                self._m = m

            @property
            @lru_cache()
            def EPSG_4326(self):
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wms",
                    url="https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1",
                )
                WMS.__doc__ = type(self).__doc__
                return WMS

            @property
            @lru_cache()
            def EPSG_3857(self):
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wms",
                    url="https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1",
                )
                WMS.__doc__ = type(self).__doc__
                return WMS

            @property
            @lru_cache()
            def EPSG_3413(self):
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wms",
                    url="https://gibs.earthdata.nasa.gov/wms/epsg3413/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1",
                )
                WMS.__doc__ = type(self).__doc__
                return WMS

            @property
            @lru_cache()
            def EPSG_3031(self):
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wms",
                    url="https://gibs.earthdata.nasa.gov/wms/epsg3031/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1",
                )
                WMS.__doc__ = type(self).__doc__
                return WMS

        @property
        def OpenStreetMap(self):
            """
            (global) OpenStreetMap WebMap layers
            https://wiki.openstreetmap.org/wiki/WMS

            Available styles are:

                - default: standard OSM layer
                - default_german: standard OSM layer in german
                - standard: standard OSM layer
                - stamen_toner: Black and white style by stamen
                    - stamen_toner_lines
                    - stamen_toner_background
                    - stamen_toner_lite
                    - stamen_toner_hybrid
                    - stamen_toner_labels
                - stamen_watercolor: a watercolor-like style by stamen
                - stamen_terrain: a terrain layer by stamen
                    - stamen_terrain_lines
                    - stamen_terrain_labels
                    - stamen_terrain_background
                - OSM_terrestis: Styles hosted as free WMS service by Terrestis
                - OSM_mundialis: Styles hosted as free WMS service by Mundialis

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            Make sure to check the usage-policies at
            https://wiki.openstreetmap.org/wiki/WMS
            """

            WMS = self._OpenStreetMap(self._m)
            WMS.__doc__ = type(self)._OpenStreetMap.__doc__
            return WMS

        class _OpenStreetMap:
            """
            (global) OpenStreetMap WebMap layers
            https://wiki.openstreetmap.org/wiki/WMS

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            Make sure to check the usage-policies at
            https://wiki.openstreetmap.org/wiki/WMS
            """

            def __init__(self, m):
                self._m = m
                self.add_layer = self._OSM(self._m)

            class _OSM:
                def __init__(self, m):
                    self._m = m

                    self.default = _xyz_tile_service(
                        self._m,
                        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                        name="OSM_default",
                    )
                    self.default.__doc__ = combdoc(
                        """
                        OpenStreetMap's standard tile layer
                        https://www.openstreetmap.org/

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**

                        check: https://operations.osmfoundation.org/policies/tiles/
                        """,
                        self.default.__call__.__doc__,
                    )

                    self.default_german = _xyz_tile_service(
                        self._m,
                        "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
                        name="OSM_default_german",
                    )
                    self.default_german.__doc__ = combdoc(
                        """
                        German fork of OpenStreetMap's standard tile layer
                        https://www.openstreetmap.de/

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**

                        check: https://www.openstreetmap.de/germanstyle.html
                        """,
                        self.default_german.__call__.__doc__,
                    )

                    self.OpenTopoMap = _xyz_tile_service(
                        m=self._m,
                        url="https://c.tile.opentopomap.org/{z}/{x}/{y}.png",
                        maxzoom=16,
                        name="OSM_OpenTopoMap",
                    )
                    self.OpenTopoMap.__doc__ = combdoc(
                        """
                        A project aiming at rendering topographic maps from OSM
                        and SRTM data. The map style is similar to some official
                        German or French topographic maps, such as TK50 or TOP 25.
                        https://www.opentopomap.org/

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**

                        check: https://wiki.openstreetmap.org/wiki/OpenTopoMap
                        """,
                        self.default_german.__call__.__doc__,
                    )

                    self.stamen_toner = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png",
                        name="OSM_stamen_toner",
                    )
                    self.stamen_toner_lines = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-lines/{z}/{x}/{y}.png",
                        name="OSM_stamen_toner_lines",
                    )
                    self.stamen_toner_background = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-background/{z}/{x}/{y}.png",
                        name="OSM_stamen_toner_background",
                    )
                    self.stamen_toner_lite = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png",
                        name="OSM_stamen_toner_lite",
                    )
                    self.stamen_toner_hybrid = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-hybrid/{z}/{x}/{y}.png",
                        name="OSM_stamen_toner_hybrid",
                    )
                    self.stamen_toner_labels = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-labels/{z}/{x}/{y}.png",
                        name="OSM_stamen_toner_labels",
                    )

                    self.stamen_watercolor = _xyz_tile_service(
                        self._m,
                        "http://c.tile.stamen.com/watercolor/{z}/{x}/{y}.jpg",
                        name="OSM_stamen_watercolor",
                        maxzoom=18,
                    )

                    self.stamen_terrain = _xyz_tile_service(
                        self._m,
                        "http://c.tile.stamen.com/terrain/{z}/{x}/{y}.jpg",
                        name="OSM_stamen_terrain",
                    )
                    self.stamen_terrain_lines = _xyz_tile_service(
                        self._m,
                        "http://c.tile.stamen.com/terrain-lines/{z}/{x}/{y}.jpg",
                        name="OSM_stamen_terrain_lines",
                    )
                    self.stamen_terrain_labels = _xyz_tile_service(
                        self._m,
                        "http://c.tile.stamen.com/terrain-labels/{z}/{x}/{y}.jpg",
                        name="OSM_stamen_terrain_labels",
                    )
                    self.stamen_terrain_background = _xyz_tile_service(
                        self._m,
                        "http://c.tile.stamen.com/terrain-background/{z}/{x}/{y}.jpg",
                        name="OSM_stamen_terrain_background",
                    )

                    stamen_doc = """

                        http://maps.stamen.com/

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**

                        Make sure to check http://maps.stamen.com/ for up-to-date
                        license policies.

                        Except otherwise noted, each of these map tile sets are
                        © Stamen Design, under a Creative Commons Attribution
                        (CC BY 3.0) license.

                        We’d love to see these maps used around the web, so we’ve
                        included some brief instructions to help you use them in
                        the mapping system of your choice. These maps are available
                        free of charge. If you use these tiles, you must use the
                        attribution provided in the link above.
                        """

                    stamen_toner_doc = combdoc(
                        """
                        **Stamen Toner**

                        High-contrast B+W (black and white) maps provided by Stamen
                        """,
                        stamen_doc,
                        self.stamen_toner.__call__.__doc__,
                    )

                    stamen_terrain_doc = combdoc(
                        """
                        **Stamen Terrain**

                        Terrain maps with hill-shading and natural vegetation colors
                        provided by Stamen
                        """,
                        stamen_doc,
                        self.stamen_toner.__call__.__doc__,
                    )

                    stamen_watercolor_doc = combdoc(
                        """
                        **Stamen Watercolor**

                        A maps-style reminiscent of hand-drawn watercolor maps
                        provided by Stamen
                        """,
                        stamen_doc,
                        self.stamen_toner.__call__.__doc__,
                    )

                    self.stamen_toner.__doc__ = stamen_toner_doc
                    self.stamen_toner_lines.__doc__ = stamen_toner_doc
                    self.stamen_toner_background.__doc__ = stamen_toner_doc
                    self.stamen_toner_lite.__doc__ = stamen_toner_doc
                    self.stamen_toner_hybrid.__doc__ = stamen_toner_doc
                    self.stamen_toner_labels.__doc__ = stamen_toner_doc

                    self.stamen_terrain.__doc__ = stamen_terrain_doc
                    self.stamen_terrain_lines.__doc__ = stamen_terrain_doc
                    self.stamen_terrain_labels.__doc__ = stamen_terrain_doc
                    self.stamen_terrain_background.__doc__ = stamen_terrain_doc

                    self.stamen_watercolor.__doc__ = stamen_watercolor_doc

            @property
            @lru_cache()
            def OSM_terrestis(self):
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wms",
                    url="https://ows.terrestris.de/osm/service?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities",
                )
                WMS.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... this service is hosted by Terrestris... check:
                    https://www.terrestris.de/en/openstreetmap-wms/
                    """,
                )
                return WMS

            @property
            @lru_cache()
            def OSM_mundialis(self):
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wms",
                    url="http://ows.mundialis.de/services/service?",
                )
                WMS.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... this service is hosted by Mundialis... check:
                    https://www.mundialis.de/en/ows-mundialis/
                    """,
                )
                return WMS

        @property
        @lru_cache()
        def EEA_DiscoMap(self):
            """
            European Environment Agency Discomap services
            https://discomap.eea.europa.eu/Index/

            A wide range of environmental data for Europe from the
            European Environment Agency covering thematic areas such as air,
            water, climate change, biodiversity, land and noise.

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            check: https://discomap.eea.europa.eu/

            EEA standard re-use policy: Unless otherwise indicated, reuse of
            content on the EEA website for commercial or non-commercial
            purposes is permitted free of charge, provided that the source is
            acknowledged.
            """
            WMS = self._EEA_DiscoMap(self._m)
            WMS.__doc__ = type(self).EEA_DiscoMap.__doc__
            return WMS

        class _EEA_DiscoMap:
            """
            European Environment Agency discomap Image collection
            https://discomap.eea.europa.eu/Index/
            """

            def __init__(self, m):
                self._m = m

            @property
            @lru_cache()
            def Image(self):
                """
                European Environment Agency discomap Image collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://image.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_Image",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'Image' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

            @property
            @lru_cache()
            def Land(self):
                """
                European Environment Agency discomap Land collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://land.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_Land",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'Land' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

            @property
            @lru_cache()
            def Climate(self):
                """
                European Environment Agency discomap Climate collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://climate.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_Climate",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'Climate' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

            @property
            @lru_cache()
            def Bio(self):
                """
                European Environment Agency discomap Bio collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://bio.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_Bio",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'Bio' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

            @property
            @lru_cache()
            def Copernicus(self):
                """
                European Environment Agency discomap Copernicus collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://copernicus.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_Copernicus",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'Copernicus' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

            @property
            @lru_cache()
            def Water(self):
                """
                European Environment Agency discomap Water collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://water.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_Water",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'Water' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

            @property
            @lru_cache()
            def SOER(self):
                """
                European Environment Agency discomap SOER collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://soer.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_SOER",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'SOER' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

            @property
            @lru_cache()
            def MARATLAS(self):
                """
                European Environment Agency discomap MARATLAS collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://maratlas.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_SOER",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'MARATLAS' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

            @property
            @lru_cache()
            def MARINE(self):
                """
                European Environment Agency discomap MARINE collection
                https://discomap.eea.europa.eu/Index/
                """
                API = REST_API_services(
                    m=self._m,
                    url="https://marine.discomap.eea.europa.eu/arcgis/rest/services",
                    name="EEA_REST_SOER",
                    service_type="wms",
                )
                API.__doc__ = combdoc(
                    type(self).__doc__,
                    """
                    ... access to the 'MARINE' subfolder

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    ... make sure to check the link above...

                    EEA standard re-use policy: Unless otherwise indicated, reuse of
                    content on the EEA website for commercial or non-commercial
                    purposes is permitted free of charge, provided that the source is
                    acknowledged.
                    """,
                )

                return API

        @property
        def S1GBM(self):
            """
            Sentinel-1 Global Backscatter Model
            https://researchdata.tuwien.ac.at/records/n2d1v-gqb91

            A global C-band backscatter layer from Sentinel-1 in either
            VV or VH polarization.

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            Citation:
                B. Bauer-Marschallinger, et.al (2021): The Sentinel-1 Global Backscatter Model (S1GBM) -
                Mapping Earth's Land Surface with C-Band Microwaves (1.0) [Data set]. TU Wien.

            - https://researchdata.tuwien.ac.at/records/n2d1v-gqb91
            - https://s1map.eodc.eu/


            With this dataset publication, we open up a new perspective on
            Earth's land surface, providing a normalised microwave backscatter
            map from spaceborne Synthetic Aperture Radar (SAR) observations.
            The Sentinel-1 Global Backscatter Model (S1GBM) describes Earth
            for the period 2016-17 by the mean C-band radar cross section
            in VV- and VH-polarization at a 10 m sampling, giving a
            high-quality impression on surface- structures and -patterns.

            https://s1map.eodc.eu/
            """

            ret = SimpleNamespace(
                add_layer=self._S1GBM_layers(self._m), layers=["vv", "vh"]
            )

            ret.__doc__ = type(self).S1GBM.__doc__

            return ret

        class _S1GBM_layers:
            def __init__(self, m):
                self._m = m

            @property
            def vv(self):
                WMS = _xyz_tile_service(
                    self._m,
                    lambda x, y, z: f"https://s1map.eodc.eu/vv/{z}/{x}/{2**z-1-y}.png",
                    13,
                    name="S1GBM_vv",
                )

                WMS.__doc__ = combdoc("Polarization: VV", type(self).__doc__)
                return WMS

            @property
            def vh(self):
                WMS = _xyz_tile_service(
                    self._m,
                    lambda x, y, z: f"https://s1map.eodc.eu/vh/{z}/{x}/{2**z-1-y}.png",
                    13,
                    name="S1GBM_vh",
                )
                WMS.__doc__ = combdoc("Polarization: VH", type(self).__doc__)
                return WMS

        @property
        @lru_cache()
        def ESRI_ArcGIS(self):
            """
            Interface to the ERSI ArcGIS REST Services Directory
            http://services.arcgisonline.com/arcgis/rest/services

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            For licensing etc. check the individual layer-descriptions at
            http://services.arcgisonline.com/arcgis/rest/services

            """
            API = REST_API_services(
                m=self._m,
                url="http://server.arcgisonline.com/arcgis/rest/services",
                name="ERSI_ArcGIS_REST",
                service_type="wmts",
                layers={
                    "Canvas",
                    "Elevation",
                    "Ocean",
                    "Polar",
                    "Reference",
                    "SERVICES",
                    "Specialty",
                },
            )

            return API

        @property
        @lru_cache()
        def Austria(self):
            """
            Services specific to Austria (Europe).
            (They ONLY work if the extent is set to a location inside Austria!)

                - AT_basemap: Basemaps for whole of austria
                - Wien: Basemaps for the city of Vienna
            """
            WMS = Austria(self._m)
            WMS.__doc__ = type(self).Austria.__doc__
            return WMS

        def get_service(self, url, service_type="wms", rest_API=False, maxzoom=19):
            """
            Get a object that can be used to add WMS, WMTS or XYZ services based on
            a GetCapabilities-link or a link to a ArcGIS REST API

            The general usage is as follows (see examples below for more details):

            >>> m = Maps()
            >>> s = m.add_wms.get_service(...)
            >>> wms = s.add_layer.<...>
            >>> wms.set_extent_to_bbox() # set the extent of the map to the wms-extent
            >>> wms(transparent=True) # add the service to the map

            Parameters
            ----------
            url : str
                The service-url
            service_type: str
                The type of service (either "wms" or "wmts")

                - "wms" : `url` represents a link to a GetCapabilities.xml file for a
                  WebMap service
                - "wmts" : same as "wms" but for a WebMapTile service
                - "xyz" : A direct link to a xyz-TileServer
                  (the name of the layer is set to "xyz_layer")

                  The url can be provided either as a string of the form:

                  >>> "https://.../{z}/{x}/{y}.png"

                  Or (for non-standard urls) as a function with the following
                  call-signature:

                  >>> def url(x, y, z):
                  >>>     return "the url with x, y, z replaced by the arguments"

                See the examples below for more details on common use-cases.

            rest_API : bool, optional
                ONLY relevant if service_type is either "wms" or "wmts"!

                Indicator if a GetCapabilities link (True) or a link to a
                rest-API is provided (False). The default is False
            maxzoom : int
                ONLY relevant if service_type="xyz"!

                The maximum zoom-level available (to avoid http-request errors) for too
                high zoom levels. The default is 19.

            Returns
            -------
            service : _WebServiec_collection
                An object that behaves just like `m.add_wms.<service>`
                and provides easy-access to available WMS layers

            Examples
            --------

            WMS Example:

            - Copernicus Global Land Mosaics for Austria, Germany and Slovenia
              from Sentinel-2

              - https://land.copernicus.eu/imagery-in-situ/global-image-mosaics/
              >>> url = "https://s2gm-wms.brockmann-consult.de/cgi-bin/qgis_mapserv.fcgi?MAP=/home/qgis/projects/s2gm-wms_mosaics_vrt.qgs&service=WMS&request=GetCapabilities&version=1.1.1"
              >>> s = m.add_wms.get_service(url, "wms")

            - Web Map Services of the city of Vienna (Austria)

              >>> url = "https://data.wien.gv.at/daten/geo?version=1.3.0&service=WMS&request=GetCapabilities"
              >>> s = m.add_wms.get_service(url, "wms")

            WMTS Example:

            - WMTS service for NASA GIBS datasets

              >>> url = https://gibs.earthdata.nasa.gov/wmts/epsg4326/all/1.0.0/WMTSCapabilities.xml
              >>> s = m.add_wms.get_service(url, "wmts")

            Rest API Example:

            - Interface to the ArcGIS REST Services Directory for the
              Austrian Federal Institute of Geology (Geologische Bundesanstalt)

              >>> url = "https://gisgba.geologie.ac.at/arcgis/rest/services"
              >>> s = m.add_wms.get_service(url, "wms", rest_API=True)

            XYZ Example:

            - OpenStreetMap Tiles (https://wiki.openstreetmap.org/wiki/Tiles)

              >>> url = r"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              >>> s = m.add_wms.get_service(url, "xyz")


              >>> def url(x, y, z):
              >>>     return rf"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              >>> s = m.add_wms.get_service(url, "xyz")

            """
            if service_type == "xyz":
                if rest_API:
                    print(
                        "EOmaps: rest_API=True is not supported for service_type='xyz'"
                    )

                s = _xyz_tile_service(self._m, url, maxzoom=maxzoom)
                service = SimpleNamespace(add_layer=SimpleNamespace(xyz_layer=s))

            else:
                if rest_API:
                    service = REST_API_services(
                        m=self._m,
                        url=url,
                        name="custom_service",
                        service_type=service_type,
                    )
                else:
                    service = _WebServiec_collection(
                        self._m, service_type="wms", url=url
                    )

            return service

    class Austria:
        # container for WebMap services specific to Austria
        def __init__(self, m):
            self._m = m

        @property
        @lru_cache()
        def AT_basemap(self):
            """
            Basemap for Austria
            https://basemap.at/

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            (check: https://basemap.at/#lizenz for full details)

            basemap.at ist gemäß der Open Government Data Österreich Lizenz
            CC-BY 4.0 sowohl für private als auch kommerzielle Zwecke frei
            sowie entgeltfrei nutzbar.
            """
            WMTS = _WebServiec_collection(
                m=self._m,
                service_type="wmts",
                url="http://maps.wien.gv.at/basemap/1.0.0/WMTSCapabilities.xml",
            )
            WMTS.__doc__ = type(self).AT_basemap.__doc__
            return WMTS

        @property
        @lru_cache()
        def Wien_basemap(self):
            """
            Basemaps for the city of Vienna (Austria)
            https://www.wien.gv.at

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            check: https://www.data.gv.at/katalog/dataset/stadt-wien_webmaptileservicewmtswien

            Most services are under CC-BY 4.0
            """
            WMTS = _WebServiec_collection(
                m=self._m,
                service_type="wmts",
                url="http://maps.wien.gv.at/wmts/1.0.0/WMTSCapabilities.xml",
            )
            WMTS.__doc__ = type(self).Wien_basemap.__doc__
            return WMTS

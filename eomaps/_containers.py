from textwrap import dedent, indent, fill

from warnings import warn
from operator import attrgetter
from inspect import signature, _empty
from types import SimpleNamespace
from pathlib import Path
import json
from matplotlib.colors import rgb2hex


from cartopy import crs as ccrs

cfeature = None
shapereader = None


def _register_cartopy_feature_io():
    global cfeature
    global shapereader
    import cartopy.feature as cfeature
    from cartopy.io import shapereader


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


class _NaturalEarth_presets:
    def __init__(self, m):
        _register_cartopy_feature_io()
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
            facecolor="none",
            edgecolor="k",
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
            self._m, "physical", "ocean", facecolor=color, edgecolor="none", zorder=-1
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
            self._m, "physical", "land", facecolor=color, edgecolor="none", zorder=-1
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
            facecolor="none",
            edgecolor=".5",
            linewidth=0.5,
            zorder=99,
        )

    @property
    def urban_areas(self):
        """
        Add urban-areas to the map.

        All provided arguments are passed to `m.add_feature`
        (and further to `m.add_gdf` if geopandas is available)

        The default args are:

        - fc="r", lw=0., zorder=99

        """

        return self._feature(
            self._m,
            "cultural",
            "urban_areas",
            facecolor="r",
            linewidth=0.0,
            zorder=99,
        )

    @property
    def lakes(self):
        """
        Add lakes to the map.

        All provided arguments are passed to `m.add_feature`
        (and further to `m.add_gdf` if geopandas is available)

        The default args are:

        - fc="b", ec="none", lw=0., zorder=99

        """

        return self._feature(
            self._m,
            "physical",
            "lakes",
            facecolor="b",
            linewidth=0,
            zorder=99,
        )

    @property
    def rivers_lake_centerlines(self):
        """
        Add rivers_lake_centerlines to the map.

        All provided arguments are passed to `m.add_feature`
        (and further to `m.add_gdf` if geopandas is available)

        The default args are:

        - fc="none", ec="b", lw=0.75, zorder=99

        """

        return self._feature(
            self._m,
            "physical",
            "rivers_lake_centerlines",
            facecolor="none",
            edgecolor="b",
            linewidth=0.75,
            zorder=99,
        )

    class _feature:
        def __init__(self, m, category, name, **kwargs):
            self._m = m
            self.category = category
            self.name = name
            self.kwargs = kwargs

            self.feature = self._m.add_feature._get_feature(
                category=self.category, name=self.name
            )

            add_params = """
            Other Parameters
            ----------------
            scale : int or str
                Set the scale of the feature preset (10, 50, 110 or "auto")
                The default is "auto"
            """

            self.__doc__ = combdoc(
                f"PRESET using {kwargs} \n", self.feature.__doc__, add_params
            )

        def __call__(self, scale="auto", **kwargs):
            k = dict(**self.kwargs)
            k.update(kwargs)

            if scale != "auto":
                self.feature = self._m.add_feature._get_feature(
                    category=self.category, name=self.name
                )

            self.__doc__ = self.feature.__doc__
            return self.feature(scale=scale, **k)


_NE_features_path = Path(__file__).parent / "NE_features.json"

try:
    with open(_NE_features_path, "r") as file:
        _NE_features = json.load(file)

        _NE_features_all = dict()
        for scale, scale_items in _NE_features.items():
            for category, category_items in scale_items.items():
                _NE_features_all.setdefault(category, set()).update(category_items)

except Exception:
    print(
        "EOmaps: Could not load available NaturalEarth features from\n"
        f"{_NE_features_path}"
    )
    _NE_features = dict()
    _NE_features_all = dict()


class NaturalEarth_features(object):
    """
    Interface to the feature-layers provided by NaturalEarth

    (see https://www.naturalearthdata.com)

    The features are grouped into the categories "cultural" and "physical"
    and available at 3 different scales:

    - 10 : Large-scale data (1:10m)
    - 50 : Medium-scale data (1:50m)
    - 110 : Small-scale data (1:110m)

    If you use scale="auto", the appropriate scale of the feature will be determined
    based on the map-extent.

    For available features and additional info, check the docstring of the
    individual categories!

    >>> m.add_feature.< category >.< feature-name >(scale=10, ... style-kwargs ...)

    Examples
    --------

    - add black (coarse resolution) coastlines

      >>> from eomaps import Maps
      >>> m = Maps()
      >>> m.add_feature.physical.coastline(scale=110, fc="none", ec="k")

    - color all land red with 50% transparency and automatically determine the
      appropriate scale if you zoom the map

      >>> from eomaps import Maps
      >>> m = Maps()
      >>> m.add_feature.physical.land(scale="auto", fc="r", alpha=0.5)

    - fetch features as geopandas.GeoDataFrame
      (to color all countries with respect to the area)

      >>> from eomaps import Maps
      >>> m = Maps()
      >>> countries = m.add_feature.cultural.admin_0_countries.get_gdf(scale=10)
      >>> countries["area_rank"] = countries.area.rank()
      >>> m.add_gdf(countries, column="area_rank")

    """

    def __init__(self, m):
        _register_cartopy_feature_io()

        self._m = m

        self._depreciated_names = dict()

        for scale, scale_items in _NE_features.items():
            for category, category_items in scale_items.items():
                ns = dict()
                for name in category_items:
                    ns[name] = self._get_feature(category, name)

                c = self._category(scale, category, **ns)
                self._depreciated_names[f"{category}_{scale}"] = c

        for category, names in _NE_features_all.items():
            func = lambda name: self._feature(self._m, category, name)
            ns = dict(zip(names, map(func, names)))

            c = self._category(scale, category, **ns)
            setattr(self, category, c)

    def __call__(self, category, scale, name, **kwargs):
        feature = self._get_feature(category, name)
        return feature(**kwargs)

    def __getattribute__(self, key):
        if key != "_depreciated_names" and key in self._depreciated_names:
            warn(
                f"EOmaps: Using 'm.add_feature.{key}.< name >()' is depreciated! "
                f"use 'm.add_feature.{key.split('_')[0]}.< name >(scale=...)' instead! ",
                stacklevel=99,
            )
            return self._depreciated_names[key]
        else:
            return object.__getattribute__(self, key)

    def __getitem__(self, key):
        return getattr(self, key)

    def _get_feature(self, category, name):
        if category not in ["cultural", "physical"]:
            raise AssertionError(
                "EOmaps: Use one of ['cultural', 'physical']" + " as category!"
            )

        available_names = _NE_features_all[category]

        if name not in available_names:
            from difflib import get_close_matches

            matches = get_close_matches(name, available_names, 3)
            raise AssertionError(
                f"EOmaps: {name} is not a valid feature-name... "
                + (f"did you mean one of {matches}?" if matches else "")
            )

        return self._feature(self._m, category, name)

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

    class _category:
        def __init__(self, scale, category, **kwargs):

            self._s = scale
            self._c = category

            for key, val in kwargs.items():
                setattr(self, key, val)

            if scale == "auto":
                header = (
                    f"Auto-scaled feature interface for: {category}\n"
                    "------------------------------------------------"
                    "\n"
                    "Note\n"
                    "----\n"
                    "Features will be added to the map using cartopy's Feature "
                    "interface and the scale (10m, 50m or 110m) is automatically "
                    "adjusted based on the extent of the map."
                    "\n\n"
                    "--------------------------------------------------------------"
                    "\n\n"
                )
            else:
                header = (
                    f"Feature interface for: {category} - {scale}\n"
                    "----------------------------------------------"
                )

            self.__doc__ = combdoc(header, NaturalEarth_features.__doc__)

        def __repr__(self):
            return (
                f"EOmaps interface for {self._s} {self._c} " + "NaturalEarth features"
            )

    class _feature:
        """
        Natural Earth Feature

        Call this class like a function to add the feature to the map.

        By default, the scale of the feature is automatically adjusted based on the
        map-extent. Use `scale=...` to use a fixed scale.

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
        scale : (10, 50, 110 or 'auto'), optional
            The (preferred) scale of the NaturalEarth feature.

            If the scale is not available for the selected feature, the next available
            scale will be used (and a warning is issued)!

            If 'auto' the scale is automatically adjusted based on the map-extent.

        layer : int, str or None, optional
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.

        Methods
        -------

        get_gdf : Get a GeoDataFrame of the feature-geometries


        Note
        ----
        Some shapes consist of point-geometries which cannot be
        properly added without `geopandas`!

        To use those features, first fetch the GeoDataFrame using `.get_gdf()`
        and then plot the shapes with `m.add_gdf()` (see example below).


        Examples
        --------

        >>> m = Maps()
        >>> feature = m.add_feature.physical.coastline
        >>> feature(scale=10,
        >>>         fc="none",
        >>>         ec="k",
        >>>         lw=.5,
        >>>         ls="--",
        >>>         )

        For more advanced plotting, fetch the data first and use geopandas
        to plot the features!

        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>> # get the data for a feature that consists of point-geometries
        >>> m.add_feature.cultural.populated_places.get_gdf()
        >>> # plot the features with geopandas
        >>> m.add_gdf(gdf, column="SOV0NAME", markersize=gdf.SCALERANK)
        """

        def __init__(self, m, category, name, scale=None):
            self._m = m

            self._category = category
            self._name = name
            self._scale = scale
            self._cartopy_feature = None

            self.__doc__ = (
                "NaturalEarth feature: "
                f"{self._category} | {self._name}\n\n"
                "----------------------------------------\n\n"
            ) + self.__doc__

        def __call__(self, layer=None, scale="auto", **kwargs):
            self._set_scale(scale)

            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                if layer is None:
                    uselayer = m.layer
                else:
                    uselayer = layer

                feature = self._get_cartopy_feature(self._scale)
                feature._kwargs.update(kwargs)
                art = m.ax.add_feature(feature)
                m.BM.add_bg_artist(art, layer=uselayer)

        def _set_scale(self, scale):
            if scale == "auto":
                self._scale = "auto"
                return

            if isinstance(scale, int):
                scale = f"{scale}m"

            assert scale in [
                "10m",
                "50m",
                "110m",
                "auto",
            ], "scale must be one of  [10, 50, 110, 'auto']"

            self._scale = self._get_available_scale(scale)

            if self._scale != scale:
                print(
                    f"EOmaps: The NaturalEarth feature '{self._name}' is not "
                    f"available at 1:{scale} scale... using 1:{self._scale} instead!"
                )

        def get_validated_scaler(self, *args, **kwargs):
            _register_cartopy_feature_io()

            class AdaptiveValidatedScaler(cfeature.AdaptiveScaler):
                # subclass of the AdaptiveScaler to make sure the dataset exists
                def __init__(self, default_scale, limits, validator=None):
                    super().__init__(default_scale, limits)

                    self.validator = validator

                def scale_from_extent(self, extent):
                    scale = super().scale_from_extent(extent)

                    if self.validator is not None:
                        scale = self.validator(scale)

                    self._scale = scale
                    return self._scale

            return AdaptiveValidatedScaler(*args, **kwargs)

        def _get_cartopy_feature(self, scale):
            self._set_scale(scale)

            if (
                self._cartopy_feature is not None
                and self._scale == self._cartopy_feature.scale
            ):

                return self._cartopy_feature

            if self._scale == "auto":
                usescale = self.get_validated_scaler(
                    "110m",
                    (("50m", 50), ("10m", 15)),
                    validator=self._get_available_scale,
                )
            else:
                usescale = self._scale

            # get an instance of the corresponding cartopy-feature
            self._cartopy_feature = cfeature.NaturalEarthFeature(
                category=self._category, name=self._name, scale=usescale
            )

            return self._cartopy_feature

        def _get_available_scale(self, scale):
            # return the optimal scale for the selected feature
            scaleorder = ["110m", "50m", "10m"]
            while True:
                if self._name in _NE_features[scale][self._category]:
                    break

                scale = scaleorder[(scaleorder.index(scale) + 1) % len(scaleorder)]

            return scale

        def get_gdf(self, scale=50, what="full"):
            """
            Get a geopandas.GeoDataFrame for the selected NaturalEarth feature

            Parameters
            ----------
            scale : (10, 50, 110), optional
                The scale to use when fetching the data for the NaturalEarth feature.

                If the scale is not available for the selected feature, the next
                available scale will be used (and a warning is issued)!
            what: str, optional
                Set what information is included in the returned GeoDataFrame.

                - "full": return all geometries AND metadata
                - "geoms" : return only geometries (NO metadata)
                - "geoms_intersecting": return only geometries that intersect with the
                  current axis-extent (NO metadata)

                The default is False

            Returns
            -------
            gdf : geopandas.GeoDataFrame
                A GeoDataFrame with all geometries of the feature
            """
            assert (
                _register_geopandas()
            ), "EOmaps: Missing dependency `geopandas` for `feature.get_gdf()`"

            self._set_scale(scale)

            if what == "full":
                gdf = gpd.read_file(
                    shapereader.natural_earth(
                        resolution=self._scale, category=self._category, name=self._name
                    )
                )
            elif what.startswith("geoms"):
                feature = self._get_cartopy_feature(self._scale)

                if what == "geoms_intersecting":
                    try:
                        extent = self._m.ax.get_extent(feature.crs)
                        feature.scaler.scale_from_extent(extent)
                    except:
                        print("EOmaps: unable to determine extent")
                        pass
                    geoms = list(feature.geometries())
                elif what == "geoms":
                    try:
                        extent = self._m.ax.get_extent(feature.crs)
                        geoms = list(feature.intersecting_geometries(extent))
                    except ValueError:
                        geoms = list(feature.geometries())
                else:
                    raise TypeError("EOmaps: what='{what}' is not a valid input!")

                gdf = gpd.GeoDataFrame(geometry=geoms, crs=feature.crs)

            else:
                raise TypeError(
                    "EOmaps: what='{what}' is not a valid input!"
                    "Use one of: ['full' ,'geoms', 'geoms_intersecting']"
                )

            if gdf.crs is None:
                # make sure the CRS is properly set
                # (NE-features come in epsg=4326 projection)
                gdf.set_crs(ccrs.PlateCarree(), inplace=True, allow_override=True)

            return gdf

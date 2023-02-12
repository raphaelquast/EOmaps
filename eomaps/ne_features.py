from textwrap import dedent
from warnings import warn
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


gpd = None


def _register_geopandas():
    global gpd
    try:
        import geopandas as gpd
    except ImportError:
        return False

    return True


def combdoc(*args):
    """Dedent and combine strings."""
    return "\n".join(dedent(str(i)) for i in args)


class _NaturalEarth_presets:
    def __init__(self, m):
        _register_cartopy_feature_io()
        self._m = m

    @property
    def coastline(self):
        """
        Add a coastline to the map.

        All provided arguments are passed to `m.add_feature`

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

        The default args are:

        - fc=(0.59375, 0.71484375, 0.8828125), ec="none", zorder=-2, reproject="cartopy"
        """
        # convert color to hex to avoid issues with geopandas
        color = rgb2hex(cfeature.COLORS["water"])

        return self._feature(
            self._m, "physical", "ocean", facecolor=color, edgecolor="none", zorder=-2
        )

    @property
    def land(self):
        """
        Add a land-coloring to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc=(0.9375, 0.9375, 0.859375), ec="none", zorder=-1

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

        The default args are:

        - fc="r", lw=0., zorder=100

        """
        return self._feature(
            self._m,
            "cultural",
            "urban_areas",
            facecolor="r",
            linewidth=0.0,
            zorder=100,
        )

    @property
    def lakes(self):
        """
        Add lakes to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc="b", ec="none", lw=0., zorder=98

        """
        return self._feature(
            self._m,
            "physical",
            "lakes",
            facecolor="b",
            linewidth=0,
            zorder=98,
        )

    @property
    def rivers_lake_centerlines(self):
        """
        Add rivers_lake_centerlines to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc="none", ec="b", lw=0.75, zorder=97

        """
        return self._feature(
            self._m,
            "physical",
            "rivers_lake_centerlines",
            facecolor="none",
            edgecolor="b",
            linewidth=0.75,
            zorder=97,
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

        def __call__(self, scale=50, **kwargs):
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
    Interface to the feature-layers provided by NaturalEarth.

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
        Natural Earth Feature.

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
            Get a geopandas.GeoDataFrame for the selected NaturalEarth feature.

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

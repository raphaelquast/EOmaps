# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Classes to fetch and draw NaturalEarth features."""

import logging
from textwrap import dedent
from pathlib import Path
import json

from cartopy import crs as ccrs

from .helpers import register_modules, _submit_on_activation

_log = logging.getLogger(__name__)


# ------ Load available features from NE_features.json file.

_NE_features_path = Path(__file__).parent / "NE_features.json"

try:
    with open(_NE_features_path, "r") as file:
        _NE_features = json.load(file)

        _NE_features_all = dict()
        for scale, scale_items in _NE_features.items():
            for category, category_items in scale_items.items():
                _NE_features_all.setdefault(category, set()).update(category_items)


except Exception:
    _log.error(
        "EOmaps: Could not load available NaturalEarth features from\n"
        f"{_NE_features_path}",
        exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
    )
    _NE_features = dict()
    _NE_features_all = dict()

# ---------------------


def _combdoc(*args):
    """Dedent and combine strings."""
    return "\n".join(dedent(str(i)) for i in args)


class _Category:
    """
    Interface to features provided by NaturalEarth.

    (see https://www.naturalearthdata.com)

    The features are grouped into the categories "cultural" and "physical"
    and available at 3 different scales:

    - 10 : Large-scale data (1:10m)
    - 50 : Medium-scale data (1:50m)
    - 110 : Small-scale data (1:110m)

    If you use scale="auto", the appropriate scale of the feature will be determined
    based on the map-extent.

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

    _category = "???"

    def __init__(self, m):
        self._m = m

    def __getattribute__(self, key):
        if key.startswith("_"):
            return object.__getattribute__(self, key)
        elif key in _NE_features_all.get(self._category, []):
            feature = _Feature(self._category, key)
            feature._set_map(self._m)
            return feature
        else:
            return object.__getattribute__(self, key)

    def __repr__(self):
        return f"EOmaps interface for {self._category} " + "NaturalEarth features"

    @classmethod
    def _setup(cls, category):
        # this is used to setup the namespace so that it is accessible for sphinx

        for i in _NE_features_all[category]:
            # we need to init new classes to avoid issues with immutuable attributes
            setattr(cls, i, type(i, (_Feature,), {}))  # (category, i))

        cls.__doc__ = _combdoc(
            f"NaturalEarth feature interface for: **{category}**.\n",
            _Category.__doc__,
        )


class _Feature:
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

    layer : str or None, optional
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

    def __init__(self, category, name, scale=None):
        self._category = category
        self._name = name
        self._scale = scale
        self._cartopy_feature = None

        self.__doc__ = (
            "NaturalEarth feature: "
            f"{self._category} | {self._name}\n\n"
            "----------------------------------------\n\n"
        ) + self.__doc__

    def _set_map(self, m):
        self._m = m

    @_submit_on_activation("_m", "Maps.add_feature.{_category}.{_name}(...)")
    def __call__(self, layer=None, scale="auto", **kwargs):
        assert hasattr(
            self, "_m"
        ), "EOmaps: This feature is not associated to a map and cannot be added!"
        _log.debug(f"EOmaps: Adding feature: {self._category}: {self._name}")

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
            art.set_label(
                f"NaturalEarth feature: {feature.category}  |  {feature.name}"
            )

            try:
                str_kwargs = json.dumps(feature._kwargs)
            except Exception:
                str_kwargs = ""
                _log.debug(
                    "There was something wrong while trying to convert "
                    f"the following kwargs to a string: {kwargs}"
                )

            source_code = (
                f"feature_kwargs = {str_kwargs}\n\n"
                f"m.add_feature.{feature.category}.{feature.name}(**feature_kwargs)"
            )

            # try to auto-format code in case black is installed
            try:
                import black

                source_code = black.format_str(source_code, mode=black.Mode())
            except Exception:
                pass

            art._EOmaps_info = f"""
                NaturalEarth feature: {feature.category}  |  {feature.name}

                https://www.naturalearthdata.com/

                """
            art._EOmaps_source_code = source_code

            m.l[uselayer].add_bg_artist(art)

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
            _log.warning(
                f"EOmaps: The NaturalEarth feature '{self._name}' is not "
                f"available at 1:{scale} scale... using 1:{self._scale} instead!"
            )

    def _get_validated_scaler(self, *args, **kwargs):
        from cartopy.feature import AdaptiveScaler

        class AdaptiveValidatedScaler(AdaptiveScaler):
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
        from cartopy.feature import NaturalEarthFeature

        self._set_scale(scale)

        if (
            self._cartopy_feature is not None
            and self._scale == self._cartopy_feature.scale
        ):

            return self._cartopy_feature

        if self._scale == "auto":
            usescale = self._get_validated_scaler(
                "110m",
                (("50m", 50), ("10m", 15)),
                validator=self._get_available_scale,
            )
        else:
            usescale = self._scale

        # get an instance of the corresponding cartopy-feature
        self._cartopy_feature = NaturalEarthFeature(
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
        if what == "geoms_intersecting":
            assert hasattr(self, "_m"), (
                "EOmaps: If the feature is not called form a Maps-instance, you can "
                "only use 'what=full' or 'what=geoms'!"
            )

        (gpd,) = register_modules("geopandas")

        self._set_scale(scale)

        if what == "full":
            from cartopy.io import shapereader

            gdf = gpd.read_file(
                shapereader.natural_earth(
                    resolution=self._scale, category=self._category, name=self._name
                )
            )
        elif what.startswith("geoms"):
            feature = self._get_cartopy_feature(self._scale)

            if what == "geoms_intersecting":
                extent = self._m.get_extent(feature.crs)
                geoms = list(feature.intersecting_geometries(extent))
            elif what == "geoms":
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


class _PresetFeature:
    def __init__(self, m, category, name, **kwargs):
        self._m = m
        self.category = category
        self.name = name
        self.kwargs = kwargs

        self.feature = _Feature(category=self.category, name=self.name)
        self.feature._set_map(self._m)

        add_params = """
        Other Parameters
        ----------------
        scale : int or str
            Set the scale of the feature preset (10, 50, 110 or "auto")
            The default is "auto"
        """

        self.__doc__ = _combdoc(
            f"PRESET using {kwargs} \n", self.feature.__doc__, add_params
        )

    def _handle_synonyms(self, kwargs):
        # make sure to replace shortcuts with long names
        # (since "facecolor=..." will override "fc=..." if both are specified)
        subst = dict(fc="facecolor", ec="edgecolor", lw="linewidth", ls="linestyle")
        return {subst.get(key, key): val for key, val in kwargs.items()}

    def __call__(self, scale=50, layer=None, **kwargs):
        k = dict(**self.kwargs)
        k.update(kwargs)

        self.__doc__ = self.feature.__doc__
        return self.feature(scale=scale, layer=layer, **self._handle_synonyms(k))


# to make namespace accessible for autocompletion and sphinx-autodoc
class _Physical(_Category):
    _category = "physical"

    antarctic_ice_shelves_lines: _Feature
    antarctic_ice_shelves_polys: _Feature
    bathymetry_A_10000: _Feature
    bathymetry_B_9000: _Feature
    bathymetry_C_8000: _Feature
    bathymetry_D_7000: _Feature
    bathymetry_E_6000: _Feature
    bathymetry_F_5000: _Feature
    bathymetry_G_4000: _Feature
    bathymetry_H_3000: _Feature
    bathymetry_I_2000: _Feature
    bathymetry_J_1000: _Feature
    bathymetry_K_200: _Feature
    bathymetry_L_0: _Feature
    coastline: _Feature
    geographic_lines: _Feature
    geography_marine_polys: _Feature
    geography_regions_elevation_points: _Feature
    geography_regions_points: _Feature
    geography_regions_polys: _Feature
    glaciated_areas: _Feature
    graticules_1: _Feature
    graticules_10: _Feature
    graticules_15: _Feature
    graticules_20: _Feature
    graticules_30: _Feature
    graticules_5: _Feature
    lakes: _Feature
    lakes_australia: _Feature
    lakes_europe: _Feature
    lakes_historic: _Feature
    lakes_north_america: _Feature
    lakes_pluvial: _Feature
    land: _Feature
    land_ocean_label_points: _Feature
    land_ocean_seams: _Feature
    land_scale_rank: _Feature
    minor_islands: _Feature
    minor_islands_coastline: _Feature
    minor_islands_label_points: _Feature
    ocean: _Feature
    ocean_scale_rank: _Feature
    playas: _Feature
    reefs: _Feature
    rivers_australia: _Feature
    rivers_europe: _Feature
    rivers_lake_centerlines: _Feature
    rivers_lake_centerlines_scale_rank: _Feature
    rivers_north_america: _Feature
    wgs84_bounding_box: _Feature


_Physical._setup("physical")


class _Cultural(_Category):
    _category = "cultural"

    admin_0_antarctic_claim_limit_lines: _Feature
    admin_0_antarctic_claims: _Feature
    admin_0_boundary_lines_disputed_areas: _Feature
    admin_0_boundary_lines_land: _Feature
    admin_0_boundary_lines_map_units: _Feature
    admin_0_boundary_lines_maritime_indicator: _Feature
    admin_0_boundary_lines_maritime_indicator_chn: _Feature
    admin_0_boundary_map_units: _Feature
    admin_0_breakaway_disputed_areas: _Feature
    admin_0_countries: _Feature
    admin_0_countries_arg: _Feature
    admin_0_countries_bdg: _Feature
    admin_0_countries_bra: _Feature
    admin_0_countries_chn: _Feature
    admin_0_countries_deu: _Feature
    admin_0_countries_egy: _Feature
    admin_0_countries_esp: _Feature
    admin_0_countries_fra: _Feature
    admin_0_countries_gbr: _Feature
    admin_0_countries_grc: _Feature
    admin_0_countries_idn: _Feature
    admin_0_countries_ind: _Feature
    admin_0_countries_iso: _Feature
    admin_0_countries_isr: _Feature
    admin_0_countries_ita: _Feature
    admin_0_countries_jpn: _Feature
    admin_0_countries_kor: _Feature
    admin_0_countries_lakes: _Feature
    admin_0_countries_mar: _Feature
    admin_0_countries_nep: _Feature
    admin_0_countries_nld: _Feature
    admin_0_countries_pak: _Feature
    admin_0_countries_pol: _Feature
    admin_0_countries_prt: _Feature
    admin_0_countries_pse: _Feature
    admin_0_countries_rus: _Feature
    admin_0_countries_sau: _Feature
    admin_0_countries_swe: _Feature
    admin_0_countries_tlc: _Feature
    admin_0_countries_tur: _Feature
    admin_0_countries_twn: _Feature
    admin_0_countries_ukr: _Feature
    admin_0_countries_usa: _Feature
    admin_0_countries_vnm: _Feature
    admin_0_disputed_areas: _Feature
    admin_0_disputed_areas_scale_rank_minor_islands: _Feature
    admin_0_label_points: _Feature
    admin_0_map_subunits: _Feature
    admin_0_map_units: _Feature
    admin_0_pacific_groupings: _Feature
    admin_0_scale_rank: _Feature
    admin_0_scale_rank_minor_islands: _Feature
    admin_0_seams: _Feature
    admin_0_sovereignty: _Feature
    admin_0_tiny_countries: _Feature
    admin_0_tiny_countries_scale_rank: _Feature
    admin_1_label_points: _Feature
    admin_1_label_points_details: _Feature
    admin_1_seams: _Feature
    admin_1_states_provinces: _Feature
    admin_1_states_provinces_lakes: _Feature
    admin_1_states_provinces_lines: _Feature
    admin_1_states_provinces_scale_rank: _Feature
    admin_2_counties: _Feature
    admin_2_counties_lakes: _Feature
    admin_2_counties_scale_rank: _Feature
    admin_2_counties_scale_rank_minor_islands: _Feature
    admin_2_label_points: _Feature
    admin_2_label_points_details: _Feature
    airports: _Feature
    parks_and_protected_lands: _Feature
    populated_places: _Feature
    populated_places_simple: _Feature
    ports: _Feature
    railroads: _Feature
    railroads_north_america: _Feature
    roads: _Feature
    roads_north_america: _Feature
    time_zones: _Feature
    urban_areas: _Feature
    urban_areas_landscan: _Feature


_Cultural._setup("cultural")


class NaturalEarthPresets:
    """
    Feature presets.

    To add single preset-features (or customize the appearance), use:

    >>> m.add_feature.preset.coastline(ec="r", scale=50, ...)

    To quickly add multiple features in one go, use:

    >>> m.add_feature.preset("coastline", "ocean", "land")

    """

    def __init__(self, m):
        self._m = m

    def __call__(self, *args, scale=50, layer=None, **kwargs):
        """
        Add multiple preset-features in one go.

        >>> m.add_feature.preset("coastline", "ocean", "land")

        Parameters
        ----------
        args : str
            The names of the features to add.
        scale : int or str
            Set the scale of the feature preset (10, 50, 110 or "auto")
            The default is "auto"
        layer : str or None, optional
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.
        kwargs:
            Additional style kwargs passed to all features
            (e.g. alpha, facecolor, edgecolor, linewidth, ...)
        """
        wrong_names = set(args).difference(self._feature_names)
        assert len(wrong_names) == 0, (
            f"EOmaps: {wrong_names} are not valid preset-feature names!\n"
            f"Use one of: {self._feature_names}."
        )

        for a in args:
            getattr(self, a)(scale=scale, layer=layer, **kwargs)

    @property
    def _feature_names(self):
        return [i for i in self.__dir__() if not i.startswith("_")]

    @property
    def coastline(self) -> _Feature:
        """
        Add a coastline to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc="none", ec="k", zorder=100
        """

        return _PresetFeature(
            self._m,
            "physical",
            "coastline",
            facecolor="none",
            edgecolor="k",
            zorder=100,
        )

    @property
    def ocean(self) -> _Feature:
        """
        Add ocean-coloring to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc=(0.59375, 0.71484375, 0.8828125), ec="none", zorder=-2, reproject="cartopy"
        """
        # convert color to hex to avoid issues with geopandas
        color = "#97b6e1"  # rgb2hex(cfeature.COLORS["water"])

        return _PresetFeature(
            self._m, "physical", "ocean", facecolor=color, edgecolor="none", zorder=-2
        )

    @property
    def land(self) -> _Feature:
        """
        Add a land-coloring to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc=(0.9375, 0.9375, 0.859375), ec="none", zorder=-1

        """
        # convert color to hex to avoid issues with geopandas
        color = "#efefdb"  # rgb2hex(cfeature.COLORS["land"])

        return _PresetFeature(
            self._m, "physical", "land", facecolor=color, edgecolor="none", zorder=-1
        )

    @property
    def countries(self) -> _Feature:
        """
        Add country-boundaries to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc="none", ec=".5", lw=0.5, zorder=99

        """
        return _PresetFeature(
            self._m,
            "cultural",
            "admin_0_countries",
            facecolor="none",
            edgecolor=".5",
            linewidth=0.5,
            zorder=99,
        )

    @property
    def urban_areas(self) -> _Feature:
        """
        Add urban-areas to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc="r", lw=0., zorder=100

        """
        return _PresetFeature(
            self._m,
            "cultural",
            "urban_areas",
            facecolor="r",
            linewidth=0.0,
            zorder=100,
        )

    @property
    def lakes(self) -> _Feature:
        """
        Add lakes to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc="b", ec="none", lw=0., zorder=98

        """
        return _PresetFeature(
            self._m,
            "physical",
            "lakes",
            facecolor="b",
            linewidth=0,
            zorder=98,
        )

    @property
    def rivers_lake_centerlines(self) -> _Feature:
        """
        Add rivers_lake_centerlines to the map.

        All provided arguments are passed to `m.add_feature`

        The default args are:

        - fc="none", ec="b", lw=0.75, zorder=97

        """
        return _PresetFeature(
            self._m,
            "physical",
            "rivers_lake_centerlines",
            facecolor="none",
            edgecolor="b",
            linewidth=0.75,
            zorder=97,
        )


class NaturalEarthFeatures:
    """
    Interface to features provided by NaturalEarth.

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

    preset: NaturalEarthPresets = NaturalEarthPresets
    cultural: _Cultural = _Cultural
    physical: _Physical = _Physical

    def __init__(self, m):
        self._m = m

        self.preset = NaturalEarthPresets(self._m)
        self.cultural = _Cultural(self._m)
        self.physical = _Physical(self._m)

    def __call__(self, category, name, **kwargs):
        feature = self._get_feature(category, name)
        return feature(**kwargs)

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

        return _Feature(category, name)

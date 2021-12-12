from textwrap import dedent, indent, fill
from warnings import warn
from operator import attrgetter
from inspect import signature, _empty
from types import SimpleNamespace
from functools import lru_cache

import matplotlib.pyplot as plt
from matplotlib.pyplot import get_cmap
from matplotlib.gridspec import SubplotSpec
import mapclassify

from ._webmap import _import_OK

if _import_OK:
    from ._webmap import (
        _WebServiec_collection,
        REST_API_services,
        _xyz_tile_service,
    )


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

        self.coll = None
        # self.coll is assigned in "m.plot_map()"

    @property
    def f(self):
        # always return the figure of the parent object
        if self._m.parent._f is None:
            self._m.parent._BM = None  # reset the blit-manager
            self._m.parent._f = plt.figure(figsize=(12, 8))
            plt.draw()

        return self._m.parent._f

    @property
    def ax(self):
        ax = self._m._ax
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
            _, ax_cb, ax_cb_plot, orientation = [
                self.cb_gridspec,
                self.ax_cb,
                self.ax_cb_plot,
                "vertical" if self._m._orientation == "horizontal" else "horizontal",
            ]
        else:
            _, ax_cb, ax_cb_plot, orientation, _ = cb

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

        if key == "plot_epsg":
            warn(
                "EOmaps: the plot-spec 'plot_epsg' has been depreciated... "
                + "try to use 'crs' or 'plot_crs' instead!"
            )
            key = "plot_crs"
        elif key == "crs":
            key = "plot_crs"

        assert key in self.keys(), f"{key} is not a valid plot-specs key!"

        return key

    def keys(self):
        # fmt: off
        return ('label', 'title', 'cmap', 'plot_crs', 'histbins', 'tick_precision',
                'vmin', 'vmax', 'cpos', 'cpos_radius', 'alpha', 'density')
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
            print("EOmaps: fetching IRIS layers...")
            return self._ISRIC(self._m)

        class _ISRIC:
            # since this is not an ArcGIS REST API it needs some special treatment...
            def __init__(self, m, service_type="wms"):
                import requests
                import json

                self._m = m
                self._service_type = service_type
                layers = requests.get(
                    "https://rest.isric.org/soilgrids/v2.0/properties/layers"
                )
                self._layers = json.loads(layers.content.decode())["layers"]

                for i in self._layers:
                    name = i["property"]
                    setattr(
                        self, name, _WebServiec_collection(self._m, service_type="wms")
                    )
                    getattr(
                        self, name
                    )._url = f"https://maps.isric.org/mapserv?map=/map/{name}.map"

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
            if self._m._preferred_wms_service == "wms":
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wms",
                    url="https://services.terrascope.be/wms/v2",
                )
            elif self._m._preferred_wms_service == "wmts":
                WMS = _WebServiec_collection(
                    m=self._m,
                    service_type="wmts",
                    url="https://services.terrascope.be/wmts/v2",
                )

            WMS.__doc__ = type(self).ESA_WorldCover.__doc__
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
                        self._m, "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
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
                        self._m, "https://tile.openstreetmap.de/{z}/{x}/{y}.png"
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
                    )
                    self.stamen_toner_lines = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-lines/{z}/{x}/{y}.png",
                    )
                    self.stamen_toner_background = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-background/{z}/{x}/{y}.png",
                    )
                    self.stamen_toner_lite = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png",
                    )
                    self.stamen_toner_hybrid = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-hybrid/{z}/{x}/{y}.png",
                    )
                    self.stamen_toner_labels = _xyz_tile_service(
                        self._m,
                        "https://stamen-tiles.a.ssl.fastly.net/toner-labels/{z}/{x}/{y}.png",
                    )

                    self.stamen_watercolor = _xyz_tile_service(
                        self._m, "http://c.tile.stamen.com/watercolor/{z}/{x}/{y}.jpg"
                    )

                    self.stamen_terrain = _xyz_tile_service(
                        self._m, "http://c.tile.stamen.com/terrain/{z}/{x}/{y}.jpg"
                    )
                    self.stamen_terrain_lines = _xyz_tile_service(
                        self._m,
                        "http://c.tile.stamen.com/terrain-lines/{z}/{x}/{y}.jpg",
                    )
                    self.stamen_terrain_labels = _xyz_tile_service(
                        self._m,
                        "http://c.tile.stamen.com/terrain-labels/{z}/{x}/{y}.jpg",
                    )
                    self.stamen_terrain_background = _xyz_tile_service(
                        self._m,
                        "http://c.tile.stamen.com/terrain-background/{z}/{x}/{y}.jpg",
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
            return

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

                API.fetch_services()
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
                API.fetch_services()

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
                API.fetch_services()

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
                API.fetch_services()

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
                API.fetch_services()

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
                API.fetch_services()

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
                API.fetch_services()

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
                API.fetch_services()

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
                API.fetch_services()

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
                )

                WMS.__doc__ = combdoc("Polarization: VV", type(self).__doc__)
                return WMS

            @property
            def vh(self):
                WMS = _xyz_tile_service(
                    self._m,
                    lambda x, y, z: f"https://s1map.eodc.eu/vh/{z}/{x}/{2**z-1-y}.png",
                    13,
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
                name="EEA_REST",
                service_type="wmts",
            )
            API.fetch_services()

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

        def get_service(self, url, service_type="wms", rest_API=False):
            """
            Get a object that can be used to add WMS or WMTS services based on
            a GetCapabilities-link or a link to a ArcGIS REST API

            Examples (WMS):
            - Copernicus Global Land Mosaics for Austria, Germany and Slovenia
              from Sentinel-2

              - https://land.copernicus.eu/imagery-in-situ/global-image-mosaics/
              >>> "https://s2gm-wms.brockmann-consult.de/cgi-bin/qgis_mapserv.fcgi?MAP=/home/qgis/projects/s2gm-wms_mosaics_vrt.qgs&service=WMS&request=GetCapabilities&version=1.1.1"
            - Web Map Services of the city of Vienna (Austria)

              - https://www.data.gv.at/katalog/dataset/stadt-wien_webmapservicewmsgeoserverwien
              >>> "https://data.wien.gv.at/daten/geo?version=1.3.0&service=WMS&request=GetCapabilities"

            Examples (WMTS):
            - WMTS service for NASA GIBS datasets

              >>> https://gibs.earthdata.nasa.gov/wmts/epsg4326/all/1.0.0/WMTSCapabilities.xml

            Examples (rest_API):
            - Interface to the ArcGIS REST Services Directory for the
              Austrian Federal Institute of Geology (Geologische Bundesanstalt)
              - https://www.geologie.ac.at/services/web-services
              >>> "https://gisgba.geologie.ac.at/arcgis/rest/services"

            Parameters
            ----------
            url : str
                The service-url
            service_type: str
                The type of service (either "wms" or "wmts")
            rest_API : bool, optional
                Indicator if a GetCapabilities link (True) or a link to a
                rest-API is provided (False). The default is False

            Returns
            -------
            service : _WebServiec_collection
                An object that behaves just like `m.add_wms.<service>`
                and provides easy-access to available WMS layers

            """

            if rest_API:
                service = REST_API_services(
                    m=self._m,
                    url=url,
                    name="custom_service",
                    service_type=service_type,
                )
                service.fetch_services()
            else:
                service = _WebServiec_collection(self._m, service_type="wms", url=url)

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

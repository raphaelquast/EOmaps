from functools import lru_cache
from textwrap import dedent

from types import SimpleNamespace


def combdoc(*args):
    """Combine docstrings."""
    return "\n".join(dedent(str(i)) for i in args)


def _register_imports():
    global _WebServiec_collection
    global REST_API_services
    global _xyz_tile_service
    global _xyz_tile_service_nonearth

    from ._webmap import (
        _WebServiec_collection,
        REST_API_services,
        _xyz_tile_service,
        _xyz_tile_service_nonearth,
    )


class wms_container(object):
    """
    A collection of open-access WebMap services that can be added to the maps.

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
        _register_imports()

        self._m = m

    class _ISRIC:
        """
        Interface to the ISRIC SoilGrids database
        https://www.isric.org

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
                setattr(self, name, _WebServiec_collection(self._m, service_type="wms"))
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
    def ISRIC_SoilGrids(self):
        return self._ISRIC(self._m)

    ISRIC_SoilGrids.__doc__ = _ISRIC.__doc__

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
    def GMRT(self):
        """
        Global Multi-Resolution Topography (GMRT) Synthesis
        https://gmrt.org/

        The Global Multi-Resolution Topography (GMRT) synthesis is a multi-resolutional
        compilation of edited multibeam sonar data collected by scientists and
        institutions worldwide, that is reviewed, processed and gridded by the GMRT
        Team and merged into a single continuously updated compilation of global
        elevation data. The synthesis began in 1992 as the Ridge Multibeam
        Synthesis (RMBS), was expanded to include multibeam bathymetry data from the
        Southern Ocean, and now includes bathymetry from throughout the global and
        coastal oceans. GMRT is included in the ocean basemap in Google Earth
        (since June 2011) and the GEBCO compilation since 2014.

        Note
        ----
        **LICENSE-info (without any warranty for correctness!!)**

        For use of the GMRT synthesis, an appropriate reference is:

        Ryan, W. B. F., S.M. Carbotte, J. Coplan, S. O'Hara, A. Melkonian, R. Arko,
        R.A. Weissel, V. Ferrini, A. Goodwillie, F. Nitsche, J. Bonczkowski, and
        R. Zemsky (2009), Global Multi-Resolution Topography (GMRT) synthesis data set,
        Geochem. Geophys. Geosyst., 10, Q03014, doi:10.1029/2008GC002332.
        Data doi: 10.1594/IEDA.100001

        (check: https://gmrt.org/about/terms_of_use.php for full details)

        """
        WMS = _WebServiec_collection(
            m=self._m,
            service_type="wms",
            url="https://www.gmrt.org/services/mapserver/wms_merc?request=GetCapabilities&service=WMS&version=1.3.0",
        )

        WMS.__doc__ = type(self).GMRT.__doc__
        return WMS

    @property
    @lru_cache()
    def GLAD(self):
        """
        Datasets from University of Maryland, Global Land Analysis and Discovery Team
        https://glad.umd.edu/

        https://glad.earthengine.app/

        Note
        ----
        **LICENSE-info (without any warranty for correctness!!)**

        (check: https://glad.earthengine.app/ for full details)

        """
        WMS = _WebServiec_collection(
            m=self._m,
            service_type="wms",
            url="https://glad.umd.edu/mapcache/?SERVICE=WMS",
        )

        WMS.__doc__ = type(self).GLAD.__doc__
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

    class _OpenStreetMap:
        """
        OpenStreetMap WebMap layers
        https://wiki.openstreetmap.org/wiki/WMS

        Available styles are:

            - default: standard OSM layer
            - default_german: standard OSM layer in german
            - CyclOSM: a bycicle oriented style
            - OEPNV_public_transport: a layer indicating global public transportation
            - OpenRiverboatMap: a style to navigate waterways
            - OpenTopoMap: SRTM + OSM for nice topography
            - stamen_toner: Black and white style by stamen

                - stamen_toner_lines
                - stamen_toner_background
                - stamen_toner_lite
                - stamen_toner_hybrid
                - stamen_toner_labels

            - stamen_terrain: a terrain layer by stamen

                - stamen_terrain_lines
                - stamen_terrain_labels
                - stamen_terrain_background

            - stamen_watercolor: a watercolor-like style by stamen
            - OSM_terrestis: Styles hosted as free WMS service by Terrestis
            - OSM_mundialis: Styles hosted as free WMS service by Mundialis
            - OSM_cartodb: Styles hosted as free WMS service by CartoDB
            - OSM_wheregroup: Styles hosted as free WMS service by WhereGroup
            - OSM_openrailwaymap: layers provided by OSM-OpenRailwayMap
            - OSM_waymarkedtrails: layers provided by OSM-WayMarkedTrails
            - OSM_wms and OSM_landuse: WMS hosted by Heidelberg Institute for
              Geoinformation Technology

        Note
        ----
        **LICENSE-info (without any warranty for correctness!!)**

        Make sure to check the usage-policies at

        - https://operations.osmfoundation.org/policies/tiles/
        - https://www.openstreetmap.org/copyright

        - for OSM_terrestis: https://www.terrestris.de/en/openstreetmap-wms/
        - for OSM_mundialis: https://www.mundialis.de/en/ows-mundialis/
        - for OSM_cartodb: https://github.com/CartoDB/basemap-styles
        - for OSM_WhereGroup: https://wheregroup.com/kontakt/
        - for OSM_wms and OSM_landuse : https://heigit.org
        - for CyclOSM: https://www.cyclosm.org
        - for OEPNV: http://öpnvkarte.de
        - for Stamen: http://maps.stamen.com
        - for OpenRailwayMap: https://wiki.openstreetmap.org/wiki/OpenRailwayMap
        - for OSM_WaymarkedTrails: https://waymarkedtrails.org
        - for OpenTopoMap: https://wiki.openstreetmap.org/wiki/OpenTopoMap
        """

        def __init__(self, m):
            self._m = m
            self.add_layer = self._OSM(self._m)

            self.OSM_waymarkedtrails = self._OSM_waymarkedtrails(self._m)
            self.OSM_openrailwaymap = self._OSM_openrailwaymap(self._m)
            self.OSM_cartodb = self._OSM_cartodb(self._m)

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

                self.humanitarian = _xyz_tile_service(
                    self._m,
                    "https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
                    name="OSM_humanitarian",
                )
                self.humanitarian.__doc__ = combdoc(
                    """
                    OpenStreetMap's Humanitarian style

                    Focuses on the developing countries with an emphasis on features
                    related to development and humanitarian work.

                    Good contrasting style in terms of overall colour choices. Terrain
                    shading. Many new/different icons (particularly for basic amenities
                    in developing countries) and more nuanced surface track-type
                    rendering.

                    https://www.openstreetmap.org/
                    https://wiki.openstreetmap.org/wiki/HOT_style
                    https://wiki.openstreetmap.org/wiki/Humanitarian_OSM_Team

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    check:

                    - https://operations.osmfoundation.org/policies/tiles/
                    - https://www.openstreetmap.fr/fonds-de-carte/
                    """,
                    self.humanitarian.__call__.__doc__,
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
                    self.OpenTopoMap.__call__.__doc__,
                )

                self.OpenRiverboatMap = _xyz_tile_service(
                    m=self._m,
                    url="https://a.tile.openstreetmap.fr/openriverboatmap/{z}/{x}/{y}.png",
                    maxzoom=16,
                    name="OSM_OpenRiverboatMap",
                )
                self.OpenRiverboatMap.__doc__ = combdoc(
                    """
                    Open Riverboat Map plans to make an open source CartoCSS map style
                    of navigable waterways, on top of OpenStreetMap project.

                    https://github.com/tilery/OpenRiverboatMap

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    check:

                        - https://github.com/tilery/OpenRiverboatMap
                        - https://openstreetmap.fr
                        - https://operations.osmfoundation.org/policies/tiles/

                    """,
                    self.OpenRiverboatMap.__call__.__doc__,
                )

                self.OpenSeaMap = _xyz_tile_service(
                    m=self._m,
                    url="http://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",
                    maxzoom=16,
                    name="OSM_OpenSeaMap",
                )
                self.OpenSeaMap.__doc__ = combdoc(
                    """
                    OpenSeaMap is an open source, worldwide project to create a free
                    nautical chart. There is a great need for freely accessible maps
                    for navigation purposes, so in 2009, OpenSeaMap came into life.
                    The goal of OpenSeaMap is to record interesting and useful nautical
                    information for the sailor which is then incorporated into a free
                    map of the world. This includes beacons, buoys and other navigation
                    aids as well as port information, repair shops and chandlerys.
                    OpenSeaMap is a subproject of OpenStreetMap and uses its database.

                    http://openseamap.org

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    check:

                        - https://wiki.openstreetmap.org/wiki/OpenSeaMap
                        - https://operations.osmfoundation.org/policies/tiles/

                    """,
                    self.OpenSeaMap.__call__.__doc__,
                )

                self.CyclOSM = _xyz_tile_service(
                    m=self._m,
                    url="https://a.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
                    maxzoom=16,
                    name="CyclOSM",
                )
                self.CyclOSM.__doc__ = combdoc(
                    """
                    CyclOSM is a bicycle-oriented map built on top of OpenStreetMap data.
                    It aims at providing a beautiful and practical map for cyclists, no
                    matter their cycling habits or abilities.

                    https://www.cyclosm.org/

                    A legend is available here: https://www.cyclosm.org/legend.html

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    check:

                        - https://www.cyclosm.org/
                        - https://openstreetmap.fr
                        - https://operations.osmfoundation.org/policies/tiles/

                    """,
                    self.CyclOSM.__call__.__doc__,
                )

                self.CyclOSM_lite = _xyz_tile_service(
                    m=self._m,
                    url="https://a.tile-cyclosm.openstreetmap.fr/cyclosm-lite/{z}/{x}/{y}.png",
                    maxzoom=16,
                    name="CyclOSM",
                )

                self.CyclOSM_lite.__doc__ = combdoc(
                    """
                    CyclOSM is a bicycle-oriented map built on top of OpenStreetMap data.
                    It aims at providing a beautiful and practical map for cyclists, no
                    matter their cycling habits or abilities.

                    https://www.cyclosm.org/

                    A legend is available here: https://www.cyclosm.org/legend.html

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    check:

                        - https://www.cyclosm.org/
                        - https://openstreetmap.fr
                        - https://operations.osmfoundation.org/policies/tiles/

                    """,
                    self.CyclOSM_lite.__call__.__doc__,
                )

                self.OEPNV_public_transport = _xyz_tile_service(
                    m=self._m,
                    url="http://tile.memomaps.de/tilegen/{z}/{x}/{y}.png",
                    maxzoom=16,
                    name="CyclOSM",
                )

                self.OEPNV_public_transport.__doc__ = combdoc(
                    """
                    We display worldwide public transport facilities on a uniform map,
                    so that you can forget about browsing individual operators websites.

                    https://www.öpnvkarte.de

                    Note
                    ----
                    **LICENSE-info (without any warranty for correctness!!)**

                    check:

                        - https://www.öpnvkarte.de
                        - https://memomaps.de/
                        - https://operations.osmfoundation.org/policies/tiles/

                    """,
                    self.OEPNV_public_transport.__call__.__doc__,
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

        class _OSM_waymarkedtrails:
            """
            OSM layers from WaymarkedTrails.

            Note
            ----
            **LICENSE-info (withowayut any warranty for correctness!!)**

            check:

            - https://waymarkedtrails.org
            - https://hiking.waymarkedtrails.org/#help-legal

            """

            def __init__(self, m):
                self._m = m

                self.add_layer = self._add_layer(m)
                self.layers = list(self.add_layer.__dict__)

            class _add_layer:
                def __init__(self, m):
                    for v in [
                        "hiking",
                        "cycling",
                        "mtb",
                        "slopes",
                        "riding",
                        "skating",
                    ]:

                        srv = _xyz_tile_service(
                            m,
                            (
                                "https://tile.waymarkedtrails.org/"
                                + v
                                + "/{z}/{x}/{y}.png"
                            ),
                            name=f"OSM_WaymarkedTrails_{v}",
                        )

                        setattr(self, v, srv)

                        getattr(self, v).__doc__ = combdoc(
                            (
                                f"WaymarkedTrails {v} layer\n"
                                "\n"
                                "Note\n"
                                "----\n"
                                "**LICENSE-info (without any warranty for correctness!!)**\n"
                                "\n"
                                f"check: https://{v}.waymarkedtrails.org/#help-legal\n"
                            ),
                            getattr(self, v).__call__.__doc__,
                        )

        class _OSM_openrailwaymap:
            """
            OSM layers from OpenRailwayMap.

            Note
            ----
            **LICENSE-info (withowayut any warranty for correctness!!)**

            check:

            - https://wiki.openstreetmap.org/wiki/OpenRailwayMap/API

            """

            def __init__(self, m):
                self._m = m

                self.add_layer = self._add_layer(m)
                self.layers = list(self.add_layer.__dict__)

            class _add_layer:
                def __init__(self, m):
                    for v in [
                        "standard",
                        "maxspeed",
                        "signals",
                        "electrification",
                        "gauge",
                    ]:

                        srv = _xyz_tile_service(
                            m,
                            (
                                "https://a.tiles.openrailwaymap.org/"
                                + v
                                + "/{z}/{x}/{y}.png"
                            ),
                            name=f"OSM_OpenRailwayMap_{v}",
                        )

                        setattr(self, v, srv)

                        getattr(self, v).__doc__ = combdoc(
                            (
                                f"OpenRailwayMap {v} layer\n"
                                "\n"
                                "Note\n"
                                "----\n"
                                "**LICENSE-info (without any warranty for correctness!!)**\n"
                                "\n"
                                f"check: https://wiki.openstreetmap.org/wiki/OpenRailwayMap/API\n"
                            ),
                            getattr(self, v).__call__.__doc__,
                        )

        class _OSM_cartodb:
            """
            OSM basemap styles hosted by CartoDB.

            Note
            ----
            **LICENSE-info (without any warranty for correctness!!)**

            check:

            - https://github.com/CartoDB/basemap-styles
            - https://carto.com

            """

            def __init__(self, m):
                self._m = m

                self.add_layer = self._add_layer(m)
                self.layers = list(self.add_layer.__dict__)

            class _add_layer:
                def __init__(self, m):
                    for v in [
                        "light_all",
                        "dark_all",
                        "light_nolabels",
                        "light_only_labels",
                        "dark_nolabels",
                        "dark_only_labels",
                        "base-antique",
                        "rastertiles/voyager",
                        "rastertiles/voyager_nolabels",
                        "rastertiles/voyager_only_labels",
                        "rastertiles/voyager_labels_under",
                    ]:

                        srv = _xyz_tile_service(
                            m,
                            (
                                "https://cartodb-basemaps-a.global.ssl.fastly.net/"
                                + v
                                + "/{z}/{x}/{y}.png"
                            ),
                            name=f"OSM_CartoDB_{v}",
                        )

                        name = v.replace(r"/", "_").replace("-", "_")

                        setattr(self, name, srv)

                        getattr(self, name).__doc__ = combdoc(
                            (
                                f"CartoDB basemap {v} layer\n"
                                "\n"
                                "Note\n"
                                "----\n"
                                "**LICENSE-info (without any warranty for correctness!!)**\n"
                                "\n"
                                f"check: https://github.com/CartoDB/basemap-styles\n"
                            ),
                            getattr(self, name).__call__.__doc__,
                        )

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
        def OSM_wheregroup(self):
            WMS = _WebServiec_collection(
                m=self._m,
                service_type="wms",
                url="https://osm-demo.wheregroup.com/service?REQUEST=GetCapabilities",
            )
            WMS.__doc__ = combdoc(
                type(self).__doc__,
                """
                Note
                ----
                **LICENSE-info (without any warranty for correctness!!)**

                ... this service is hosted by WhereGroup...

                It is ONLY allowed for private use and testing! For more details, check:

                https://wheregroup.com/kontakt/
                """,
            )
            return WMS

        @property
        @lru_cache()
        def OSM_wms(self):
            WMS = _WebServiec_collection(
                m=self._m,
                service_type="wms",
                url=r"https://maps.heigit.org/osm-wms/service?REQUEST=GetCapabilities&SERVICE=WMS",
            )
            WMS.__doc__ = combdoc(
                type(self).__doc__,
                """
                The first version of osm-wms.de was put online at 13th of February
                2009. Since these days it serves OpenStreetMap based maps. As the
                name indicates it does provide the maps via the OGC-WMS format
                other than the usual map tile providers. This increases the
                flexibility of the usage of this service as you are able to use the
                map not only by using this website, but also by registering the wms
                service in any GIS software that supports the standard protocol of
                the OpenGeospatialConsortium OGC-WMS.

                Note
                ----
                **LICENSE-info (without any warranty for correctness!!)**

                Terms of Use
                The usage for non-commercial, scientific or personal use is free.
                If you use our services, please acknowledge and refer to our
                website: osm-wms.de

                Acknowledgements:

                This work has kindly been supported by the Klaus Tschira Foundation
                (KTS) Heidelberg in the context of establishing the Heidelberg
                Institute for Geoinformation Technology (HeiGIT).

                Attributions:

                OSM Data: Licensed under ODbL, © OpenStreetMap contributors
                Original Data for Hillshade: CIAT-CSI SRTM
                Terms of use from CIAT: Users are prohibited from any commercial,
                non-free resale, or redistribution without explicit written
                permission from CIAT. Original data by Jarvis A., H.I. Reuter,
                A. Nelson, E. Guevara, 2008, Hole-filled seamless SRTM data V4,
                International Centre for Tropical Agriculture (CIAT), available
                from https://srtm.csi.cgiar.org.

                For more details, please visit:
                https://osm-wms.de
                """,
            )
            return WMS

        @property
        @lru_cache()
        def OSM_landuse(self):
            WMS = _WebServiec_collection(
                m=self._m,
                service_type="wms",
                url=r"https://maps.heigit.org/osmlanduse/service?REQUEST=GetCapabilities",
            )
            WMS.__doc__ = combdoc(
                type(self).__doc__,
                """
                OSM Landuse Landcover is a WebGIS application to explore the
                OpenStreetMap database specifically in terms of landuse and
                landcover information. Land use tags were predicted when absent
                using belows (Schultz et al. 2020 in prep, Schultz et al. 2017)
                method. This was first addressed for Germany (2017) and now (2020)
                - with the improved methods - for all EU countries.

                Note
                ----
                **LICENSE-info (without any warranty for correctness!!)**

                Terms of use:

                Overlay tiles of "OSM Landuse Landcover" can be used freely and
                without charge by any individuals through this website.
                If you intend to use tiles or statistics from
                "OSM Landuse Landcover" services in your own applications please
                contact us.
                Commercial usage of the services provided by "OSM Landuse Landcover"
                does need approval!
                OpenStreetMap data is available under the Open Database License.

                Acknowledgements:

                This work is supported by Heidelberg Institute for Geoinformation
                Technology (https://heigit.org)


                For more details, plese visit:
                https://osmlanduse.org
                """,
            )
            return WMS

    @property
    def OpenStreetMap(self):
        WMS = self._OpenStreetMap(self._m)
        WMS.__doc__ = type(self)._OpenStreetMap.__doc__
        return WMS

    OpenStreetMap.__doc__ = _OpenStreetMap.__doc__

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

    class _OpenPlanetary:
        """
        Planetary layers (Moon & Mars) provided by OpenPlanetary
        https://www.openplanetary.org

        """

        def __init__(self, m):
            self._m = m

            self.Moon = self._OPM_moon_basemap(self._m)
            self.Mars = self._OPM_mars_basemap(self._m)

        class _OPM_moon_basemap:
            """
            This basemap of the Moon in a combination of multiple raster and vector
            datasets that provides a characteristic view for a broader audience.

            https://www.openplanetary.org/opm-basemaps/opm-moon-basemap-v0-1

            Note
            ----
            **LICENSE-info (withowayut any warranty for correctness!!)**

            check:  https://www.openplanetary.org

            """

            def __init__(self, m):
                self._m = m

                self.add_layer = self._add_layer(m)
                self.layers = list(self.add_layer.__dict__)

            class _add_layer:
                def __init__(self, m):
                    self._m = m
                    for i, v in [
                        ("all", "all"),
                        (1, "basemap_layer"),
                        (2, "hillshaded_albedo"),
                        (3, "opm_301_moon_contours_polygons_1km_interval"),
                        (4, "opm_301_moon_nomenclature_polygons"),
                        (5, "opm_301_apollo_sites"),
                        (6, "opm_301_luna_sites"),
                    ]:

                        url = (
                            "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/"
                            + str(i)
                            + "/{z}/{x}/{y}.png"
                        )

                        docstring = (
                            f"OpenPlanetary Moon basemap {v} layer\n"
                            "\n"
                            "Note\n"
                            "----\n"
                            "**LICENSE-info (without any warranty for correctness!!)**\n"
                            "\n"
                            f"check: https://www.openplanetary.org\n"
                        )

                        self._addlayer(v, url, f"OPM_Moon_{v}", docstring)

                def _addlayer(self, name, url, srv_name, docstring, maxzoom=19):
                    srv = _xyz_tile_service_nonearth(
                        self._m, url, name=srv_name, maxzoom=maxzoom
                    )

                    setattr(self, name, srv)

                    getattr(self, name).__doc__ = combdoc(
                        docstring,
                        getattr(self, name).__call__.__doc__,
                    )

        class _OPM_mars_basemap:
            """
            This basemap of the Mars in a combination of multiple raster and vector
            datasets that provides a characteristic view for a broader audience.

            https://www.openplanetary.org/opm-basemaps/opm-mars-basemap-v0-2

            Note
            ----
            **LICENSE-info (withowayut any warranty for correctness!!)**

            check:  https://www.openplanetary.org

            """

            def __init__(self, m):
                self._m = m

                self.add_layer = self._add_layer(m)
                self.layers = [
                    i for i in self.add_layer.__dict__ if not i.startswith("_")
                ]

            class _add_layer:
                def __init__(self, m):
                    self._m = m

                    for i, v in [
                        ("all", "all"),
                        (1, "mars_hillshade"),
                        (2, "opm_499_mars_contours_200m_polygons"),
                        (3, "opm_499_mars_albedo_tes_7classes"),
                        (4, "opm_499_mars_contours_200m_lines"),
                        (5, "opm_499_mars_nomenclature_polygons"),
                    ]:

                        url = (
                            "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/"
                            + str(i)
                            + "/{z}/{x}/{y}.png"
                        )

                        docstring = (
                            f"OpenPlanetary Mars basemap {v} layer\n"
                            "\n"
                            "Note\n"
                            "----\n"
                            "**LICENSE-info (without any warranty for correctness!!)**\n"
                            "\n"
                            f"check: https://www.openplanetary.org\n"
                        )

                        self._addlayer(v, url, f"OPM_Mars_{v}", docstring)

                    docstring = f"""
                        OpenPlanetary Mars hillshade basemap

                        This basemap is a single hillshade raster data layer based on
                        MOLA dataset.

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**\n"

                        check: https://www.openplanetary.org
                        """

                    self._addlayer(
                        "hillshade",
                        "https://s3.us-east-2.amazonaws.com/opmmarstiles/hillshade-tiles/{z}/{x}/{y}.png",
                        f"OPM_Mars_hillshade",
                        docstring=docstring,
                        maxzoom=6,
                    )

                    docstring = f"""
                        OpenPlanetary Mars viking_mdim21_global basemap

                        This basemap is a single raster data layer based on Viking
                        MDIM 2.1 dataset.

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**\n"

                        check: https://www.openplanetary.org
                        """

                    self._addlayer(
                        "viking_mdim21_global",
                        lambda x, y, z: f"http://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/viking_mdim21_global/{z}/{x}/{2**z-1-y}.png",
                        f"OPM_Mars_viking_mdim21_global",
                        docstring=docstring,
                        maxzoom=7,
                    )

                    docstring = f"""
                        OpenPlanetary Mars celestia_mars_shaded_16k basemap

                        This basemap is a single Mars texture raster data layer based
                        on a Celestia community dataset.

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**\n"

                        check: https://www.openplanetary.org
                        """

                    self._addlayer(
                        "celestia_mars_shaded_16k",
                        lambda x, y, z: f"http://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/celestia_mars-shaded-16k_global/{z}/{x}/{2**z-1-y}.png",
                        f"OPM_Mars_celestia_mars_shaded_16k",
                        docstring=docstring,
                        maxzoom=5,
                    )

                    docstring = f"""
                        OpenPlanetary Mars mola_gray basemap

                        This basemap is a single shared grayscale raster data layer
                        based on MOLA dataset.

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**\n"

                        check: https://www.openplanetary.org
                        """

                    self._addlayer(
                        "mola_gray",
                        lambda x, y, z: f"http://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/mola-gray/{z}/{x}/{2**z-1-y}.png",
                        f"OPM_Mars_mola_gray",
                        docstring=docstring,
                        maxzoom=9,
                    )

                    docstring = f"""
                        OpenPlanetary Mars mola_color basemap

                        This basemap is a single shared color-coded raster data layer
                        based on MOLA dataset.

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**\n"

                        check: https://www.openplanetary.org
                        """

                    self._addlayer(
                        "mola_color",
                        lambda x, y, z: f"http://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/mola-color/{z}/{x}/{2**z-1-y}.png",
                        f"OPM_Mars_mola_color",
                        docstring=docstring,
                        maxzoom=6,
                    )

                    docstring = f"""
                        OpenPlanetary Mars mola_color_noshade basemap

                        This basemap is a single color-coded raster data layer based
                        on MOLA dataset.

                        Note
                        ----
                        **LICENSE-info (without any warranty for correctness!!)**\n"

                        check: https://www.openplanetary.org
                        """

                    self._addlayer(
                        "mola_color_noshade",
                        lambda x, y, z: f"http://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/mola_color-noshade_global/{z}/{x}/{2**z-1-y}.png",
                        f"OPM_Mars_mola_color_noshade",
                        docstring=docstring,
                        maxzoom=6,
                    )

                def _addlayer(self, name, url, srv_name, docstring, maxzoom=19):
                    srv = _xyz_tile_service_nonearth(
                        self._m, url, name=srv_name, maxzoom=maxzoom
                    )

                    setattr(self, name, srv)

                    getattr(self, name).__doc__ = combdoc(
                        docstring,
                        getattr(self, name).__call__.__doc__,
                    )

    @property
    def OpenPlanetary(self):
        WMS = self._OpenPlanetary(self._m)
        WMS.__doc__ = type(self)._OpenPlanetary.__doc__
        return WMS

    OpenPlanetary.__doc__ = _OpenPlanetary.__doc__

    class _GOOGLE_layers:
        def __init__(self, m):
            self._m = m
            self.add_layer = self._add_layer(m)
            self.layers = [i for i in self.add_layer.__dict__ if not i.startswith("_")]

        class _add_layer:
            def __init__(self, m):
                self._m = m

                for i, v in [
                    ("h", "roadmap_overlay"),
                    ("m", "roadmap_standard"),
                    ("p", "roadmap_terrain"),
                    ("r", "roadmap_white_streets"),
                    ("s", "satellite"),
                    ("t", "terrain_shade"),
                    ("y", "hybrid"),
                ]:

                    url = (
                        "http://mt.google.com/vt/lyrs="
                        + str(i)
                        + "&hl=en&x={x}&y={y}&z={z}&s=Ga"
                    )

                    docstring = (
                        f"GOOGLE Maps {v} layer\n"
                        "\n"
                        "Note\n"
                        "----\n"
                        "**LICENSE-info (without any warranty for correctness!!)**\n"
                        "\n"
                        f"check: https://www.google.com\n"
                    )

                    self._addlayer(v, url, f"GOOGLE_{v}", docstring)

            def _addlayer(self, name, url, srv_name, docstring, maxzoom=19):
                srv = _xyz_tile_service(self._m, url, name=srv_name, maxzoom=maxzoom)

                setattr(self, name, srv)

                getattr(self, name).__doc__ = combdoc(
                    docstring,
                    getattr(self, name).__call__.__doc__,
                )

    @property
    def GOOGLE(self):
        WMS = self._GOOGLE_layers(self._m)
        WMS.__doc__ = type(self)._GOOGLE_layers.__doc__
        return WMS

    GOOGLE.__doc__ = _GOOGLE_layers.__doc__

    @property
    @lru_cache()
    def S2_cloudless(self):
        """
        Global cloudless Sentinel-2 maps, crafted by EOX
        https://s2maps.eu/

        Endless sunshine, eternal summer - the Sentinel-2 cloudless layer combines
        trillions of pixels collected during differing weather conditions during
        the whole year of 2020 and merges them into a sunny homogeneous mosaic,
        almost free from satellite and atmospheric effects. Our thanks go to the
        European Commission and the European Space Agency for the free, full,
        and open Sentinel-2 data.

        Note
        ----
        **LICENSE-info (without any warranty for correctness!!)**

        You are free to use Sentinel-2 cloudless as long as you follow the
        applicable license conditions. The conditions for use are the attribution
        when publishing any imagery or content from Sentinel-2 cloudless as well as
        the non-commercial use for the 2018 and 2019 data. The attribution shall be
        displayed legibly and in proximity to the usage, in on-line publications
        (social-networks etc.) it shall include the links and show the text as
        described below.

        (check: https://s2maps.eu/ for full details)

        """
        WMS = _WebServiec_collection(
            m=self._m,
            service_type="wms",
            url="https://tiles.maps.eox.at/wms?service=wms&request=getcapabilities",
        )

        WMS.__doc__ = type(self).S2_cloudless.__doc__
        return WMS

    @property
    @lru_cache()
    def CAMS(self):
        """
        Copernicus Atmosphere Monitoring Service (Global and European)
        https://atmosphere.copernicus.eu/

        A selection of global and European air quality products hosted by ECMWF
        (http://eccharts.ecmwf.int)

        For details on the available layers, see:
        https://confluence.ecmwf.int/display/CKB/WMS+for+CAMS+Global+and+European+air+quality+products

        Note
        ----
        **LICENSE-info (without any warranty for correctness!!)**

        Access to Copernicus Products is given for any purpose in so far as it
        is lawful, whereas use may include, but is not limited to: reproduction;
        distribution; communication to the public; adaptation, modification and
        combination with other data and information; or any combination of the
        foregoing.

        All users of Copernicus Products must provide clear and visible attribution
        to the Copernicus programme. The Licensee will communicate to the public
        the source of the Copernicus Products by crediting the Copernicus Climate
        Change and Atmosphere Monitoring Services.

        (check: https://apps.ecmwf.int/datasets/licences/copernicus/ for full details)
        """
        WMS = _WebServiec_collection(
            m=self._m,
            service_type="wms",
            url="https://eccharts.ecmwf.int/wms/?token=public",
        )

        WMS.__doc__ = type(self).CAMS.__doc__
        return WMS

    @property
    @lru_cache()
    def DLR_basemaps(self):
        """
        Basemaps hosted by DLR's EOC Geoservice
        https://geoservice.dlr.de

        A collection of basemaps provided by the EOC Geoservice of the Earth
        Observation Center (EOC) of the German Aerospace Center (DLR).

        Note
        ----
        **LICENSE-info (without any warranty for correctness!!)**

        The background maps and overlays used on this site are created and published
        by DLR for informational and illustration purposes only. The user assumes
        the entire risk related to the use of these data. These maps may contain
        errors and therefore users of these maps should review or consult the
        primary data and information sources to ascertain the usability of the
        information.

        Disclaimer

        Although DLR is making these maps available to others, DLR does not warrant,
        endorse, or recommend the use of these maps for any given purpose. DLR is
        providing these data "as is", and disclaims any and all warranties, whether
        expressed or implied. In no event will DLR be liable to you or to any third
        party for any direct, indirect, incidental, consequential, special, or
        exemplary damages or lost profits resulting from any use or misuse of
        these data. The user of these maps cannot claim any rights pertaining to
        its usage.

        (check: https://geoservice.dlr.de/web/about for full details)
        """

        WMS = _WebServiec_collection(
            m=self._m,
            service_type="wms",
            url="https://geoservice.dlr.de/eoc/basemap/wms?SERVICE=WMS&REQUEST=GetCapabilities",
        )

        WMS.__doc__ = type(self).CAMS.__doc__
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
            service_type="xyz",
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
                print("EOmaps: rest_API=True is not supported for service_type='xyz'")

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
                service = _WebServiec_collection(self._m, service_type="wms", url=url)

        return service


class Austria:
    # container for WebMap services specific to Austria
    def __init__(self, m):
        _register_imports()

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

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

    from ._webmap import (
        _WebServiec_collection,
        REST_API_services,
        _xyz_tile_service,
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

    @property
    @lru_cache()
    def ISRIC_SoilGrids(self):
        # make this a property to avoid fetching layers on
        # initialization of Maps-objects
        """
        Interface to the ISRIC SoilGrids database.
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
        OpenStreetMap WebMap layers
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
        - for OSM_wms and OSM_landuse : https://heigit.org

        """

        WMS = self._OpenStreetMap(self._m)
        WMS.__doc__ = type(self)._OpenStreetMap.__doc__
        return WMS

    class _OpenStreetMap:
        """
        (global) OpenStreetMap WebMap layers
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

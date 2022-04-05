from functools import lru_cache
from warnings import warn, filterwarnings, catch_warnings
from types import SimpleNamespace
from collections import defaultdict

from PIL import Image
from io import BytesIO
from pprint import PrettyPrinter

from cartopy.io.img_tiles import GoogleWTS
from cartopy import crs as ccrs
import numpy as np

from pyproj import CRS, Transformer

try:
    from owslib.wmts import WebMapTileService
    from owslib.wms import WebMapService
    import requests
    from urllib3.exceptions import InsecureRequestWarning

    _import_OK = True

except ImportError:
    warn("EOmaps: adding WebMap services requires 'owslib'")
    _import_OK = False

from .helpers import _sanitize

from cartopy.io import ogc_clients
from cartopy.io import RasterSource
from cartopy.io.ogc_clients import _target_extents


class _WebMap_layer:
    # base class for adding methods to the _wms_layer- and wmts_layer objects
    def __init__(self, m, wms, name):
        self._m = m
        self.name = name
        self._wms = wms
        self.wms_layer = self._wms.contents[name]

        # hardcode support for EPSG:3857 == GOOGLE_MERCATOR for now since cartopy
        # hardcoded only  EPSG:900913
        # (see from cartopy.io.ogc_clients import _CRS_TO_OGC_SRS)
        if hasattr(self.wms_layer, "crsOptions"):
            if "EPSG:3857" in self.wms_layer.crsOptions:
                ogc_clients._CRS_TO_OGC_SRS[ccrs.GOOGLE_MERCATOR] = "EPSG:3857"
            if "epsg:3857" in self.wms_layer.crsOptions:
                ogc_clients._CRS_TO_OGC_SRS[ccrs.GOOGLE_MERCATOR] = "epsg:3857"

    @property
    def info(self):
        """
        pretty-print the available properties of the wms_layer to the console
        """

        txt = ""
        for key, val in self.wms_layer.__dict__.items():
            if not val:
                continue
            p = PrettyPrinter(depth=1, indent=len(key) + 4, width=60 - len(key))
            s = p.pformat(val).split("\n")
            s = "\n".join([s[0].replace(" " * (len(key) + 3), ""), *s[1:]])

            txt += f"{key} : {s}\n"

        try:
            _ = self.wms_layer.styles["default"]["legend"]
            legQ = True
        except Exception:
            legQ = False

        print(f"\n LEGEND available: {legQ}\n\n" + txt)

    def fetch_legend(self, style="default"):
        try:
            url = self.wms_layer.styles["default"]["legend"]
            legend = requests.get(url)

            if url.endswith(".svg"):
                try:
                    import cairosvg

                    img = cairosvg.svg2png(legend.content)

                except ImportError:
                    warn("EOmaps: the legend is '.svg'... please install 'cairosvg'")
            else:
                img = legend.content

            img = Image.open(BytesIO(img))
        except Exception:
            warn("EOmaps: could not fetch the legend")
            img = None
        return img

    def add_legend(self, style="default"):
        """
        Add a legend to the plot (if available)

        If you click on the legend you can drag it around!
        The size of the legend can be changed by turning the mouse-wheel
        while clicking on the legend.

        Parameters
        ----------
        style : str, optional
            The style to use. The default is "default".

        Returns
        -------
        legax : matpltolib.axes
            The axes-object.

        """
        from matplotlib.transforms import Bbox

        self._legend_picked = False

        legend = self.fetch_legend()
        if legend is not None:
            axpos = self._m.figure.ax.get_position()
            legax = self._m.figure.f.add_axes((axpos.x0, axpos.y0, 0.25, 0.5))

            legax.patch.set_visible(False)
            legax.tick_params(
                left=False, labelleft=False, bottom=False, labelbottom=False
            )
            legax.set_frame_on(False)
            legax.set_aspect(1, anchor="SW")
            legax.imshow(legend)

            self._m.BM.add_artist(legax)

            def cb_move(event):
                if not self._legend_picked:
                    return

                # only execute action if no toolbar action is active
                if (
                    hasattr(self._m.figure.f.canvas, "toolbar")
                    and self._m.figure.f.canvas.toolbar is not None
                    and self._m.figure.f.canvas.toolbar.mode != ""
                ):
                    return

                if not event.button:
                    legax.set_frame_on(False)
                    return

                bbox = Bbox.from_bounds(
                    event.x - legax.bbox.width / 2,
                    event.y - legax.bbox.height / 2,
                    legax.bbox.width,
                    legax.bbox.height,
                )

                bbox = bbox.transformed(self._m.figure.f.transFigure.inverted())
                legax.set_position(bbox)

            def cb_release(event):
                self._legend_picked = False
                legax.set_frame_on(False)

            def cb_pick(event):
                if event.inaxes == legax:
                    legax.set_frame_on(True)
                    self._legend_picked = True
                else:
                    legax.set_frame_on(False)
                    self._legend_picked = False

            def cb_scroll(event):
                if not self._legend_picked:
                    return

                pos = legax.get_position()

                steps = event.step

                legax.set_position(
                    (
                        pos.x0,
                        pos.y0,
                        pos.width + steps * pos.width * 0.025,
                        pos.height + steps * pos.height * 0.025,
                    )
                )

                self._m.BM.update()

            self._m.figure.f.canvas.mpl_connect("scroll_event", cb_scroll)
            self._m.figure.f.canvas.mpl_connect("button_press_event", cb_pick)
            self._m.figure.f.canvas.mpl_connect("button_release_event", cb_release)
            self._m.figure.f.canvas.mpl_connect("motion_notify_event", cb_move)

            self._m.BM.update()
            return legax

    def set_extent_to_bbox(self, shrink=False):
        """
        Set the extent of the axis to the bounding-box of the WebMap service.

        This is particularly useful for non-global WebMap services.

        Shrinking the bbox can help to avoid HTTP-request errors for tiles outside
        the bbox of the WebMap service.

        Error-messages that might be solved by shrinking the extent before adding
        the layer:

        - `RuntimeError: You must first set the image array`
        - `requests.exceptions.HTTPError: 404 Client Error: Not Found for url`

        Parameters
        ----------
        shrink : float, optional
            Shrink the bounding-box by the provided shrinking factor (must be in [0, 1]).

            - 0 : no shrinking (e.g. use the original bbox)
            - < 1 : shrink the bbox by the factor (e.g. 0.5 = 50% smaller bbox)

            The default is False.

        Examples:
        ---------

        >>> m = Maps()
        >>> layer = m.add_wms.Austria.Wien_basemap.add_layer.lb
        >>> layer.set_extent_to_bbox(shrink=0.5)
        >>> layer()
        """

        bbox = getattr(self.wms_layer, "boundingBox", None)
        try:
            (x0, y0, x1, y1, crs) = bbox
            incrs = CRS.from_user_input(crs)
        except Exception:
            print(
                "EOmaps: could not determine bbox from 'boundingBox'... "
                + "defaulting to 'boundingBoxWGS84'"
            )
            (x0, y0, x1, y1) = getattr(self.wms_layer, "boundingBoxWGS84", None)
            incrs = CRS.from_user_input(4326)

        if shrink:
            assert shrink >= 0, "EOmaps: shrink must be > 0!"
            assert shrink < 1, "EOmaps: shrink must be < 1!"
            dx = abs(x1 - x0) / 2
            dy = abs(y1 - y0) / 2
            x0 += dx * shrink
            x1 -= dx * shrink
            y0 += dy * shrink
            y1 -= dy * shrink

        transformer = Transformer.from_crs(
            incrs,
            self._m.crs_plot,
            always_xy=True,
        )

        (x0, x1), (y0, y1) = transformer.transform((x0, x1), (y0, y1))

        self._m.figure.ax.set_xlim(x0, x1)
        self._m.figure.ax.set_ylim(y0, y1)


class _wmts_layer(_WebMap_layer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass

    def __call__(self, layer=None, **kwargs):
        """
        Add the WMTS layer to the map

        Parameters
        ----------
        layer : int, str or None, optional
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.
        **kwargs :
            additional kwargs passed to the WebMap service request.
            (e.g. transparent=True, time='2020-02-05', etc.)
        """
        from . import MapsGrid  # do this here to avoid circular imports!

        for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
            self._kwargs = kwargs
            if layer is None:
                self._layer = m.layer
            else:
                self._layer = layer

            if self._layer == "all" or self._m.BM.bg_layer == self._layer:
                # add the layer immediately if the layer is already active
                self._do_add_layer(self._m, self._layer)
            else:
                # delay adding the layer until it is effectively activated
                self._m.BM.on_layer(
                    func=self._do_add_layer, layer=self._layer, persistent=False, m=m
                )

    def _do_add_layer(self, m, l):
        # actually add the layer to the map.
        print(f"EOmaps: Adding wmts-layer: {self.name}")

        art = m.figure.ax.add_wmts(
            self._wms, self.name, wmts_kwargs=self._kwargs, interpolation="spline36"
        )

        m.BM.add_bg_artist(art, l)


class _wms_layer(_WebMap_layer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass

    def __call__(self, layer=None, **kwargs):
        """
        Add the WMS layer to the map

        Parameters
        ----------
        layer : int, str or None, optional
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.
        **kwargs :
            additional kwargs passed to the WebMap service request.
            (e.g. transparent=True, time='2020-02-05', etc.)
        """
        from . import MapsGrid  # do this here to avoid circular imports!

        for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
            self._kwargs = kwargs
            if layer is None:
                self._layer = m.layer
            else:
                self._layer = layer

            if self._layer == "all" or m.BM.bg_layer == self._layer:
                # add the layer immediately if the layer is already active
                self._do_add_layer(m, self._layer)
            else:
                # self._do_add_layer(m, self._layer)

                # delay adding the layer until it is effectively activated

                m.BM.on_layer(
                    func=self._do_add_layer, layer=self._layer, persistent=False, m=m
                )

    def _do_add_layer(self, m, l, usem=None):
        # actually add the layer to the map.
        print(f"EOmaps: ... adding wms-layer {self.name}")
        art = m.figure.ax.add_wms(
            self._wms, self.name, wms_kwargs=self._kwargs, interpolation="spline36"
        )

        m.BM.add_bg_artist(art, l)


class _WebServiec_collection(object):
    def __init__(self, m, service_type="wmts", url=None):
        self._m = m
        self._service_type = service_type
        if url is not None:
            self._url = url

    def __getitem__(self, key):
        return self.add_layer.__dict__[key]

    def __repr__(self):
        if hasattr(self, "info"):
            return self.info
        else:
            return object.__repr__(self)

    @property
    @lru_cache()
    def layers(self):
        """
        get a list of all available layers
        """
        return list(self.add_layer.__dict__)

    def findlayer(self, name):
        """
        A convenience function to return any layer-name that contains the
        provided "name"-string (the search is NOT case-sensitive!)

        Parameters
        ----------
        name : str
            the string to search for in the layers.

        Returns
        -------
        list
            A list of all available layers that contain the provided string.

        """
        return [i for i in self.layers if name.lower() in i.lower()]

    @staticmethod
    def _get_wmts(url):
        # TODO expose useragent
        return WebMapTileService(url)

    @staticmethod
    def _get_wms(url):
        # TODO expose useragent
        return WebMapService(url)

    @property
    @lru_cache()
    def add_layer(self):
        if self._service_type == "wmts":
            wmts = self._get_wmts(self._url)
            layers = dict()
            for key in wmts.contents.keys():
                layers[_sanitize(key)] = _wmts_layer(self._m, wmts, key)

        elif self._service_type == "wms":
            wms = self._get_wms(self._url)
            layers = dict()
            for key in wms.contents.keys():
                layers[_sanitize(key)] = _wms_layer(self._m, wms, key)

        return SimpleNamespace(**layers)


class REST_API_services:
    def __init__(
        self, m, url, name, service_type="wmts", layers=None, _params={"f": "pjson"}
    ):
        """
        fetch layers from a Rest API

        Parameters
        ----------
        m : eomaps.Maps
            the parent maps object.
        url : str
            the url to the API.
        name : str
            The name of the API.
        service_type : str, optional
            the service-type to use ("wms" or "wmts"). The default is "wmts".
        layers : set, optional
            A set of default layers used for delayed fetching (and autocompletion...)
            As soon as one of the layers is accessed, the API is fetched and the
            layers are updated according to the current status of the Server.
            If None or empty, layers are immediately fetched!
            The default is None.
        _params : set, optional
            additional parameters passed to the API. The default is {"f": "pjson"}.

        """
        self._m = m
        self._REST_url = url
        self._name = name
        self._service_type = service_type
        self._params = _params
        self._fetched = False
        if layers is None:
            layers = set()
        self._layers = layers

        for i in self._layers:
            setattr(self, i, "NOT FOUND")

        if len(self._layers) == 0:
            self._fetch_services()

    def __getattribute__(self, name):
        # make sure all private properties are directly accessible
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        # fetch layers on first attempt to get a non-private attribute
        if not self._fetched:
            self._fetch_services()

        return object.__getattribute__(self, name)

    def _fetch_services(self):
        if self._fetched:
            return
        # set _fetched to True immediately to avoid issues in __getattribute__
        self._fetched = True

        print(f"EOmaps: ... fetching services for '{self._name}'")

        self._REST_API = _REST_API(self._REST_url, _params=self._params)

        found_folders = set()
        for foldername, services in self._REST_API._structure.items():
            setattr(
                self,
                foldername,
                _multi_REST_WMSservice(
                    m=self._m,
                    services=services,
                    service_type=self._service_type,
                    url=self._REST_url,
                ),
            )
            found_folders.add(foldername)

        new_layers = found_folders - self._layers
        if len(new_layers) > 0:
            print(f"EOmaps: ... found some new folders: {new_layers}")

        invalid_layers = self._layers - found_folders
        if len(invalid_layers) > 0:
            print(f"EOmaps: ... could not find the folders: {invalid_layers}")
        for i in invalid_layers:
            delattr(self, i)

        print("EOmaps: done!")


class _REST_WMSservice(_WebServiec_collection):
    def __init__(self, service, s_name, s_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service = service
        self._s_name = s_name
        self._s_type = s_type

        self._layers = None

    @property
    def _url(self):
        print(self._s_name)
        url = "/".join([self._service, self._s_name, self._s_type])

        if self._service_type == "wms":
            suffix = "/WMSServer?request=GetCapabilities&service=WMS"
            WMSurl = url.replace("/rest/", "/") + suffix
            if requests.get(WMSurl).status_code == 200:
                url = WMSurl
            else:
                url = None
        elif self._service_type == "wmts":
            suffix = "/WMTS/1.0.0/WMTSCapabilities.xml"
            WMSurl = url + suffix
            if requests.get(WMSurl).status_code == 200:
                url = WMSurl
            else:
                url = None
        return url

    def _fetch_layers(self):
        self._layers = dict()
        url = self._url
        if url is not None:
            if self._service_type == "wms":
                wms = self._get_wms(url)
                layer_names = list(wms.contents.keys())
                for lname in layer_names:
                    self._layers["layer_" + _sanitize(lname)] = _wms_layer(
                        self._m, wms, lname
                    )
            elif self._service_type == "wmts":
                wmts = self._get_wmts(url)
                layer_names = list(wmts.contents.keys())
                for lname in layer_names:
                    self._layers["layer_" + _sanitize(lname)] = _wmts_layer(
                        self._m, wmts, lname
                    )

    @property
    @lru_cache()
    def add_layer(self):
        self._fetch_layers()
        if len(self._layers) == 0:
            print(f"EOmaps: found no {self._service_type} layers for {self._s_name}")
            return
        else:
            return SimpleNamespace(**self._layers)


class _multi_REST_WMSservice:
    def __init__(self, m, services, service_type, url, *args, **kwargs):
        self._m = m
        self._services = services
        self._service_type = service_type
        self._url = url

        self._fetch_services()

    @lru_cache()
    def _fetch_services(self):
        for (s_name, s_type) in self._services:
            wms_layer = _REST_WMSservice(
                m=self._m,
                service=self._url,
                s_name=s_name,
                s_type=s_type,
                service_type=self._service_type,
            )

            setattr(self, _sanitize(s_name), wms_layer)


class _REST_API(object):
    # adapted from https://gis.stackexchange.com/a/113213
    def __init__(self, url, _params={"f": "pjson"}):
        self._url = url
        self._params = _params

        self._structure = self._get_structure(self._url)

    def _post(self, service, _params={"f": "pjson"}, ret_json=True):
        """Post Request to REST Endpoint

        Required:
        service -- full path to REST endpoint of service

        Optional:
        _params -- parameters for posting a request
        ret_json -- return the response as JSON.  Default is True.
        """
        r = requests.post(service, params=_params, verify=False)

        # make sure return
        if r.status_code != 200:
            raise NameError(
                '"{0}" service not found!\n{1}'.format(service, r.raise_for_status())
            )
        else:
            if ret_json:
                return r.json()
            else:
                return r

    def _get_structure(self, service):
        """returns a list of all services

        Optional:
        service -- full path to a rest service
        """

        with catch_warnings():
            filterwarnings("ignore", category=InsecureRequestWarning)

            all_services = defaultdict(list)
            r = self._post(service, _params=self._params)
            # parse all services that are not inside a folder
            for s in r["services"]:
                all_services["SERVICES"].append((s["name"], s["type"]))
            for s in r["folders"]:
                new = "/".join([service, s])
                endpt = self._post(new, _params=self._params)

                for serv in endpt["services"]:
                    if str(serv["type"]) == "MapServer":
                        all_services[s].append((serv["name"], serv["type"]))
        return all_services


class TileFactory(GoogleWTS):
    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = url

    def _image_url(self, tile):
        x, y, z = tile

        if isinstance(self._url, str):
            return self._url.format(x=x, y=y, z=z)
        if callable(self._url):
            return self._url(x=x, y=y, z=z)


class xyzRasterSource(RasterSource):
    """
    A RasterSource that can be used with a SlippyImageArtist to fetch tiles.
    """

    def __init__(self, url, crs, maxzoom=19, transparent=True):
        """
        Parameters
        ----------
        service: string or WebMapService instance
            The WebMapService instance, or URL of a WMS service,
            from whence to retrieve the image.
        layers: string or list of strings
            The name(s) of layers to use from the WMS service.
        """
        self.url = url

        self._crs = crs
        self._maxzoom = maxzoom

        if transparent is True:
            self.desired_tile_form = "RGBA"
        else:
            self.desired_tile_form = "RGB"

        self._factory = TileFactory(self.url, desired_tile_form=self.desired_tile_form)

    # function to estimate a proper zoom-level
    @staticmethod
    def _getz(d, zmax):
        z = int(np.clip(np.ceil(np.log2(1 / d * 40075016.68557849)), 0, zmax))
        return z

    def getz(self, extent, target_resolution, zmax):
        import shapely.geometry as sgeom

        x0, x1, y0, y1 = extent
        d = x1 - x0

        domain = sgeom.box(x0, y0, x1, y1)

        z = self._getz(d, zmax)
        ntiles = len(list(self._factory.find_images(domain, z)))

        # use the target resolution to increase the zoom-level until we use a
        # reasonable amount of tiles
        nimgs = np.ceil(max(target_resolution) / 256) ** 2

        while ntiles < nimgs:
            if z >= self._maxzoom:
                break

            z += 1
            ntiles = len(list(self._factory.find_images(domain, z)))

        return min(z, self._maxzoom)

    def _native_srs(self, projection):
        # Return the SRS which corresponds to the given projection when
        # known, otherwise return None.
        return self._crs

    def validate_projection(self, projection):
        # no need to validate the projection, we're always in 3857
        pass

    def _image_and_extent(
        self,
        wms_proj,
        wms_srs,
        wms_extent,
        output_proj,
        output_extent,
        target_resolution,
    ):
        import shapely.geometry as sgeom

        x0, x1, y0, y1 = wms_extent

        domain = sgeom.box(x0, y0, x1, y1)

        img, extent, origin = self._factory.image_for_domain(
            domain,
            self.getz(wms_extent, target_resolution, self._maxzoom),
        )

        # import PIL.Image
        # output_extent = _target_extents(extent, self._crs, output_proj)[0]
        # return _warped_located_image(PIL.Image.fromarray(img), wms_srs, extent,
        #                               output_proj,
        #                               output_extent,
        #                               target_resolution
        #                               )

        # ------------- ---------------------------------------------------------------
        # ------------- the following is copied from cartopy's version of ax.imshow
        # ------------- since the above lines don't work for some reason...

        if output_proj == wms_srs:
            pass
        else:
            img = np.asanyarray(img)
            if origin == "upper":
                # It is implicitly assumed by the regridding operation that the
                # origin of the image is 'lower', so simply adjust for that
                # here.
                img = img[::-1]

            # reproject the extent to the output-crs

            target_extent = ogc_clients._target_extents(extent, self._crs, output_proj)
            if len(target_extent) > 0:
                target_extent = target_extent[0]
            else:
                # TODO properly check what's going on here
                # (only relevant for Equi7Grid projections if a xyz-layer is added
                # without zooming first)
                target_extent = output_extent

            regrid_shape = [int(i * 2) for i in target_resolution]
            # check  self._m.ax._regrid_shape_aspect for a more proper regrid_shape

            # Lazy import because scipy/pykdtree in img_transform are only
            # optional dependencies
            from cartopy.img_transform import warp_array

            original_extent = extent
            img, extent = warp_array(
                img,
                source_proj=self._crs,
                source_extent=original_extent,
                target_proj=output_proj,
                target_res=regrid_shape,
                target_extent=target_extent,
                mask_extrapolated=True,
            )

            if origin == "upper":
                # revert to the initial origin
                img = img[::-1]

        from cartopy.io.ogc_clients import LocatedImage

        return LocatedImage(img, extent)

    def fetch_raster(self, projection, extent, target_resolution):
        target_resolution = [np.ceil(val) for val in target_resolution]

        if projection == self._crs:
            wms_extents = [extent]
        else:
            # Calculate the bounding box(es) in WMS projection.
            wms_extents = _target_extents(extent, projection, self._crs)

        located_images = []
        for wms_extent in wms_extents:
            img = self._image_and_extent(
                self._crs,
                self._crs,
                wms_extent,
                projection,
                extent,
                target_resolution,
            )
            if img:
                located_images.append(img)

        return located_images


class _xyz_tile_service:
    """
    general class for using x/y/z tile-service urls as WebMap layers
    """

    def __init__(self, m, url, maxzoom=19, name=None):
        self._m = m
        self._factory = None
        self._artist = None

        self.url = url
        self._maxzoom = maxzoom
        self.name = name

    def _reinit(self, m):
        return _xyz_tile_service(m, self.url, self._maxzoom)

    def __call__(
        self,
        layer=None,
        transparent=False,
        alpha=1,
        interpolation="spline36",
        **kwargs,
    ):
        """
        Parameters
        ----------
        layer : int, str or None, optional
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.
        transparent : bool, optional
            Indicator if the WMS images should be read as RGB or RGBA
            (e.g. with or without transparency). The default is False.
        alpha : float, optional (passed to matplotlib imshow)
            The alpha-transparency of the image.
            NOTE: This changes the global transparency of the images... it does
            not control whether the images include transparency! (check the
            "transparent" kwarg)
        interpolation : str, optional (passed to matplotlib imshow)
            The interpolation-method to use. The default is "spline36".
        regrid_shape : int, optional
            The target resolution for warping images in case a re-projection is
            required (e.g. if you don't use the native projection of the WMS)
            changing this value will slow down re-projection but it can
            provide a huge boost in image quality! The default is 750.
        **kwargs :
            Additional kwargs passed to the cartopy-wrapper for
            matplotlib's `imshow`.
        """

        from . import MapsGrid  # do this here to avoid circular imports!

        if layer is None:
            self._layer = self._m.layer
        else:
            self._layer = layer

        self._transparent = transparent
        if isinstance(self._m, MapsGrid):
            for m in self._m:
                self._reinit(m).__call__(
                    layer, transparent, alpha, interpolation, **kwargs
                )
        else:

            self._kwargs = dict(
                interpolation=interpolation, alpha=alpha, origin="lower"
            )
            self._kwargs.update(kwargs)

            if self._layer == "all" or self._m.BM.bg_layer == self._layer:
                # add the layer immediately if the layer is already active
                self._do_add_layer(self._m, self._layer)
            else:
                # delay adding the layer until it is effectively activated
                self._m.BM.on_layer(
                    func=self._do_add_layer,
                    layer=self._layer,
                    persistent=False,
                    m=self._m,
                )

    def _do_add_layer(self, m, l):
        # actually add the layer to the map.
        print(f"EOmaps: ... adding wms-layer {self.name}")

        self._raster_source = xyzRasterSource(
            self.url,
            crs=ccrs.GOOGLE_MERCATOR,
            maxzoom=self._maxzoom,
            transparent=self._transparent,
        )

        # avoid using "add_raster" and use the subclassed SlippyImageArtist
        # self._artist = self._m.ax.add_raster(self._raster_source, **self.kwargs)

        # ------- following lines are equivalent to ax.add_raster
        #         (only SlippyImageArtist has been subclassed)

        self._raster_source.validate_projection(m.ax.projection)
        img = SlippyImageArtist_NEW(m.ax, self._raster_source, **self._kwargs)
        with self._m.ax.hold_limits():
            m.ax.add_image(img)
        self._artist = img

        m.BM.add_bg_artist(self._artist, l)


from cartopy.mpl.slippy_image_artist import SlippyImageArtist

# subclass cartopy's SlippyImageArtist but handle draw-capture within EOmaps
class SlippyImageArtist_NEW(SlippyImageArtist):
    def __init__(self, ax, *args, **kwargs):
        super().__init__(ax, *args, **kwargs)

    def on_press(self, event=None):
        # don't capture user interaction since this is handled internally by EOmaps
        # (e.g. draw-events are already only issued if necessary!)
        # This is required to ensure correct fetching of backgrounds with a draggable
        # slider (e.g. button is pressed but new background should be fetched!)
        # self.user_is_interacting = True
        return

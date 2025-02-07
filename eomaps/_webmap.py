# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

import logging

import requests
from functools import lru_cache, partial
from warnings import warn, filterwarnings, catch_warnings
from types import SimpleNamespace
from contextlib import contextmanager
from urllib3.exceptions import InsecureRequestWarning
from io import BytesIO
from pprint import PrettyPrinter

from packaging import version

from PIL import Image
import numpy as np
from pyproj import CRS, Transformer

import cartopy
from cartopy import crs as ccrs
from cartopy.io.img_tiles import GoogleWTS
from cartopy.io import RasterSource

from .helpers import _sanitize

_log = logging.getLogger(__name__)


def _add_pending_webmap(m, layer, name):
    # indicate that there is a pending webmap in the companion-widget editor
    m.BM._pending_webmaps.setdefault(layer, []).append(name)


class _WebMapLayer:
    # base class for adding methods to the _WMSLayer- and _WMTSLayer objects
    def __init__(self, m, wms, name):
        from cartopy.io.ogc_clients import _CRS_TO_OGC_SRS

        self._m = m
        self.name = name
        self._wms = wms
        self.wms_layer = self._wms.contents[name]

        styles = list(self.wms_layer.styles)
        if len(styles) == 0:
            self._style = ""
        else:
            self._style = "default" if "default" in styles else styles[0]

        # fix of OCG_CRS assignments for older cartopy versions
        # ...ported to cartopy >= 0.21.2:
        #    https://github.com/SciTools/cartopy/pull/2138
        if version.parse(cartopy.__version__) < version.parse("0.21.2"):
            # hardcode support for EPSG:3857 == GOOGLE_MERCATOR for now
            # since cartopy hardcoded only  EPSG:900913
            # (see from cartopy.io.ogc_clients import _CRS_TO_OGC_SRS)
            if hasattr(self.wms_layer, "crsOptions"):
                if "EPSG:3857" in self.wms_layer.crsOptions:
                    _CRS_TO_OGC_SRS[ccrs.GOOGLE_MERCATOR] = "EPSG:3857"
                    if "epsg:3857" in self.wms_layer.crsOptions:
                        _CRS_TO_OGC_SRS[ccrs.GOOGLE_MERCATOR] = "epsg:3857"

    @property
    def info(self):
        """Pretty-print the available properties of the wms_layer to the console."""
        txt = ""
        for key, val in self.wms_layer.__dict__.items():
            if not val:
                continue
            p = PrettyPrinter(depth=1, indent=len(key) + 4, width=60 - len(key))
            s = p.pformat(val).split("\n")
            s = "\n".join([s[0].replace(" " * (len(key) + 3), ""), *s[1:]])

            txt += f"{key} : {s}\n"

        try:
            legQ = any(("legend" in val for key, val in self.wms_layer.styles.items()))
        except Exception:
            legQ = False

        print(f"\n LEGEND available: {legQ}\n\n" + txt)

    def fetch_legend(self, style=None):
        if style is None:
            style = self._style
        try:
            url = self.wms_layer.styles[style]["legend"]
            legend = requests.get(url)

            if url.endswith(".svg"):
                try:
                    import cairosvg

                    img = cairosvg.svg2png(legend.content)

                except ImportError:
                    _log.warning(
                        "EOmaps: The legend image is provided as a '.svg' graphic. "
                        "To add svg graphics to a map, you must install the optional "
                        "dependency 'cairosvg'! (see: https://cairosvg.org/)",
                        exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                    )
                    return None
            else:
                img = legend.content

            img = Image.open(BytesIO(img))
        except Exception:
            if _log.getEffectiveLevel() <= logging.DEBUG:
                _log.warning("EOmaps: could not fetch the wms legend", exc_info=True)
            return None
        return img

    def add_legend(self, style=None, img=None):
        """
        Add a legend to the plot (if available).

        If you click on the legend you can drag it around!
        The size of the legend can be changed by turning the mouse-wheel
        while clicking on the legend.

        Parameters
        ----------
        style : str, optional
            The style to use. The default is "default".
        img : BytesIO
            A pre-fetched legend (if provided the "style" kwarg is ignored!)

        Returns
        -------
        legax : matplotlib.axes
            The axes-object.

        """
        from matplotlib.transforms import Bbox

        if style is None:
            style = self._style

        self._legend_picked = False
        if img is None:
            legend = self.fetch_legend()
        else:
            legend = img

        if legend is not None:
            if not hasattr(self, "_layer"):
                # use the currently active layer if the webmap service has not yet
                # been added to the map
                _log.warning(
                    "EOmaps: The WebMap for the legend is not yet added to the map!"
                )
                self._layer = self._m.BM._bg_layer

            axpos = self._m.ax.get_position()
            legax = self._m.f.add_axes((axpos.x0, axpos.y0, 0.25, 0.5))

            legax.patch.set_visible(False)
            legax.tick_params(
                left=False, labelleft=False, bottom=False, labelbottom=False
            )
            legax.set_frame_on(False)
            legax.set_aspect(1, anchor="SW")
            legax.imshow(legend)

            # hide the legend if the corresponding layer is not active at the moment
            if not self._m.BM._layer_visible(self._layer):
                legax.set_visible(False)

            self._m.BM.add_artist(legax, self._layer)

            def cb_move(event):
                if not self._legend_picked:
                    return

                # only execute action if no toolbar action is active
                if (
                    hasattr(self._m.f.canvas, "toolbar")
                    and self._m.f.canvas.toolbar is not None
                    and self._m.f.canvas.toolbar.mode != ""
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

                bbox = bbox.transformed(self._m.f.transFigure.inverted())
                legax.set_position(bbox)

                self._m.BM.blit_artists([legax])

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

            def cb_keypress(event):
                if not self._legend_picked:
                    return

                if event.key in ["delete", "backspace"]:
                    self._m.BM.remove_artist(legax, self._layer)
                    legax.remove()

                self._m.BM.update()

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

                self._m.BM.blit_artists([legax])

            self._m.f.canvas.mpl_connect("scroll_event", cb_scroll)
            self._m.f.canvas.mpl_connect("button_press_event", cb_pick)
            self._m.f.canvas.mpl_connect("button_release_event", cb_release)
            self._m.f.canvas.mpl_connect("motion_notify_event", cb_move)
            self._m.f.canvas.mpl_connect("key_press_event", cb_keypress)

            self._m.parent._wms_legend.setdefault(self._layer, list()).append(legax)

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
            _log.error(
                "EOmaps: could not determine bbox from 'boundingBox'... "
                + "defaulting to 'boundingBoxWGS84'",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
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

        self._m.ax.set_xlim(x0, x1)
        self._m.ax.set_ylim(y0, y1)

    def _set_style(self, style=None):
        # style is a list with 1 entry!

        styles = list(self.wms_layer.styles)

        if style is not None:
            assert (
                style[0] in styles
            ), f"EOmaps: WebMap style {style} is not available, use one of {styles}"
            self._style = style[0]
        else:
            style = [self._style]

        return style


class _WMTSLayer(_WebMapLayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, layer=None, zorder=0, alpha=1, **kwargs):
        """
        Add the WMTS layer to the map

        Parameters
        ----------
        layer : int, str or None, optional
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.
        zorder : float
            The zorder of the artist (e.g. the stacking level of overlapping artists)
            The default is -5
        alpha : float, optional
            The alpha-transparency of the image.
            NOTE: This changes the global transparency of the images... it does
            not control whether the images are served with included transparency!
            (check the "transparent" kwarg)
        **kwargs :
            additional kwargs passed to the WebMap service request.
            (e.g. transparent=True, time='2020-02-05', etc.)

        Additional Parameters
        ---------------------
        transparent : bool, optional
            Indicator if the WMS images should be read as RGB or RGBA
            (e.g. with or without transparency). The default is False.

        """
        from . import MapsGrid  # do this here to avoid circular imports!

        styles = self._set_style(kwargs.get("styles", None))
        if styles is not None:
            kwargs["styles"] = styles

        for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
            if layer is None:
                self._layer = m.layer
            else:
                self._layer = layer

            if self._layer == "all" or m.BM._layer_visible(self._layer):
                # add the layer immediately if the layer is already active
                self._do_add_layer(
                    self._m,
                    layer=self._layer,
                    wms_kwargs=kwargs,
                    zorder=zorder,
                    alpha=alpha,
                )
            else:
                # delay adding the layer until it is effectively activated
                _add_pending_webmap(self._m, self._layer, self.name)
                self._m.BM.on_layer(
                    func=partial(
                        self._do_add_layer,
                        wms_kwargs=kwargs,
                        zorder=zorder,
                        alpha=alpha,
                    ),
                    layer=self._layer,
                    persistent=False,
                    m=m,
                )

    # ------------------------
    # The following is very much a copy of "cartopy.mpl.geoaxes.GeoAxes.add_raster"
    # and "cartopy.mpl.geoaxes.GeoAxes.add_wmts", using a different implementation
    # for SlippyImageArtist
    @staticmethod
    def _add_wmts(ax, wms, layers, wms_kwargs=None, **kwargs):
        from cartopy.io.ogc_clients import WMTSRasterSource

        wms = WMTSRasterSource(wms, layers, gettile_extra_kwargs=wms_kwargs)

        # Allow a fail-fast error if the raster source cannot provide
        # images in the current projection.
        wms.validate_projection(ax.projection)
        img = SlippyImageArtistNew(ax, wms, **kwargs)
        with ax.hold_limits():
            ax.add_image(img)
        return img

    def _do_add_layer(self, m, layer, **kwargs):
        # actually add the layer to the map.
        _log.info(f"EOmaps: Adding wmts-layer: {self.name}")

        # use slightly adapted implementation of cartopy's ax.add_wmts
        art = self._add_wmts(
            m.ax, self._wms, self.name, interpolation="spline36", **kwargs
        )

        art.set_label(f"WebMap service: {self.name}")

        # attach the info to the artist so it can be identified by the companion widget
        if hasattr(self, "_EOmaps_info"):
            art._EOmaps_info = self._EOmaps_info
        if hasattr(self, "_EOmaps_source_code"):
            art._EOmaps_source_code = self._EOmaps_source_code

        m.BM.add_bg_artist(art, layer=layer)


class _WMSLayer(_WebMapLayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, layer=None, zorder=0, alpha=1, **kwargs):
        """
        Add the WMS layer to the map

        Parameters
        ----------
        layer : int, str or None, optional
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.
        zorder : float
            The zorder of the artist (e.g. the stacking level of overlapping artists)
            The default is -5
        alpha : float, optional
            The alpha-transparency of the image.
            NOTE: This changes the global transparency of the images... it does
            not control whether the images are served with included transparency!
            (check the "transparent" kwarg)
        **kwargs :
            additional kwargs passed to the WebMap service request.
            (e.g. transparent=True, time='2020-02-05', etc.)

        Additional Parameters
        ---------------------
        transparent : bool, optional
            Indicator if the WMS images should be read as RGB or RGBA
            (e.g. with or without transparency). The default is False.

        """
        from . import MapsGrid  # do this here to avoid circular imports!

        styles = self._set_style(kwargs.get("styles", None))
        if styles is not None:
            kwargs["styles"] = styles

        for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:

            if layer is None:
                self._layer = m.layer
            else:
                self._layer = layer

            if m.BM._layer_visible(self._layer):
                # add the layer immediately if the layer is already active
                self._do_add_layer(
                    m=m,
                    layer=self._layer,
                    wms_kwargs=kwargs,
                    zorder=zorder,
                    alpha=alpha,
                )
            else:
                # delay adding the layer until it is effectively activated
                _add_pending_webmap(self._m, self._layer, self.name)
                m.BM.on_layer(
                    func=partial(
                        self._do_add_layer,
                        wms_kwargs=kwargs,
                        zorder=zorder,
                        alpha=alpha,
                    ),
                    layer=self._layer,
                    persistent=False,
                    m=m,
                )

    # ------------------------
    # The following is very much a copy of "cartopy.mpl.geoaxes.GeoAxes.add_raster"
    # and "cartopy.mpl.geoaxes.GeoAxes.add_wms", using a different implementation
    # for SlippyImageArtist

    @staticmethod
    def _add_wms(ax, wms, layers, wms_kwargs=None, **kwargs):
        # fix of native-crs identifications for older cartopy versions
        # ...ported to cartopy >= 0.21.2:
        #    https://github.com/SciTools/cartopy/pull/2136
        from cartopy.io.ogc_clients import WMSRasterSource

        if version.parse(cartopy.__version__) < version.parse("0.21.2"):

            class WMSRasterSourceNew(WMSRasterSource):

                # Temporary fix for WMS services provided in a known srs but not
                # in the srs of the axis
                # (for example ESA_WorldCover.add_layer.WORLDCOVER_2020_MAP())
                def _native_srs(self, *args, **kwargs):
                    native_srs = super()._native_srs(*args, **kwargs)

                    # if native_srs cannot be identified, try to use fallback
                    if native_srs is None:
                        return None

                    else:
                        # check if the native_srs is actually provided.
                        # if not try to use fallback srs
                        contents = self.service.contents
                        native_OK = all(
                            native_srs in contents[layer].crsOptions
                            for layer in self.layers
                        )

                        if native_OK:
                            return native_srs
                        else:
                            return None

            wms = WMSRasterSourceNew(wms, layers, getmap_extra_kwargs=wms_kwargs)
        else:
            wms = WMSRasterSource(wms, layers, getmap_extra_kwargs=wms_kwargs)

        # Allow a fail-fast error if the raster source cannot provide
        # images in the current projection.
        wms.validate_projection(ax.projection)
        img = SlippyImageArtistNew(ax, wms, **kwargs)
        with ax.hold_limits():
            ax.add_image(img)

        return img

    def _do_add_layer(self, m, layer, **kwargs):
        # actually add the layer to the map.
        _log.info(f"EOmaps: ... adding wms-layer {self.name}")

        # use slightly adapted implementation of cartopy's ax.add_wms
        art = self._add_wms(
            m.ax, self._wms, self.name, interpolation="spline36", **kwargs
        )

        art.set_label(f"WebMap service: {self.name}")

        # attach the info to the artist so it can be identified by the companion widget
        if hasattr(self, "_EOmaps_info"):
            art._EOmaps_info = self._EOmaps_info
        if hasattr(self, "_EOmaps_source_code"):
            art._EOmaps_source_code = self._EOmaps_source_code

        m.BM.add_bg_artist(art, layer=layer)


class _WebServiceCollection:
    def __init__(self, m, service_type="wmts", url=None, **kwargs):
        self._m = m
        self._service_type = service_type
        if url is not None:
            self._url = url

        # additional kwargs that will be passed to owslib.WebMapService()
        self._service_kwargs = kwargs.copy()

    def __getitem__(self, key):
        return self.add_layer.__dict__[key]

    def __repr__(self):
        if hasattr(self, "info"):
            return self.info

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
    def _get_wmts(url, **kwargs):
        # TODO expose useragent

        # lazy import used to avoid long import times
        from owslib.wmts import WebMapTileService

        return WebMapTileService(url, **kwargs)

    @staticmethod
    def _get_wms(url, **kwargs):
        # TODO expose useragent

        # lazy import used to avoid long import times
        from owslib.wms import WebMapService

        return WebMapService(url, **kwargs)

    @property
    @lru_cache()
    def add_layer(self):
        if self._service_type == "wmts":
            wmts = self._get_wmts(self._url, **self._service_kwargs)
            layers = dict()
            for key in wmts.contents.keys():
                layername = _sanitize(key)
                wmtslayer = _WMTSLayer(self._m, wmts, key)
                # attach the info to the artist so it can be identified by the companion
                if hasattr(self, "_EOmaps_info") and self._EOmaps_info is not None:
                    wmtslayer._EOmaps_info = self._EOmaps_info.replace("<layer>", key)
                if (
                    hasattr(self, "_EOmaps_source_code")
                    and self._EOmaps_source_code is not None
                ):
                    wmtslayer._EOmaps_source_code = self._EOmaps_source_code.replace(
                        "<layer>", layername
                    )
                layers[layername] = wmtslayer

        elif self._service_type == "wms":
            wms = self._get_wms(self._url, **self._service_kwargs)
            layers = dict()
            for key in wms.contents.keys():
                layername = _sanitize(key)

                wmslayer = _WMSLayer(self._m, wms, key)
                # attach the info to the artist so it can be identified by the companion
                if hasattr(self, "_EOmaps_info") and self._EOmaps_info is not None:
                    wmslayer._EOmaps_info = self._EOmaps_info.replace("<layer>", key)

                if (
                    hasattr(self, "_EOmaps_source_code")
                    and self._EOmaps_source_code is not None
                ):
                    wmslayer._EOmaps_source_code = self._EOmaps_source_code.replace(
                        "<layer>", layername
                    )
                layers[layername] = wmslayer

        return SimpleNamespace(**layers)


class RestApiServices:
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
            the service-type to use ("wms", "wmts" or "xyz"). The default is "wmts".
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
        self._rest_url = url
        self._name = name
        self._service_type = service_type
        self._params = _params
        self._fetched = False
        self._rest_api = None

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

        if self._rest_api is None:
            _log.info(f"EOmaps: ... fetching services for '{self._name}'")
            self._rest_api = _RestApi(self._rest_url, _params=self._params)

            found_folders = set()
            for foldername, services in self._rest_api._structure.items():
                setattr(
                    self,
                    foldername,
                    _MultiRestWmsService(
                        m=self._m,
                        services=services,
                        service_type=self._service_type,
                        url=self._rest_url,
                    ),
                )
                found_folders.add(foldername)

            new_layers = found_folders - self._layers
            if len(new_layers) > 0:
                _log.info(f"EOmaps: ... found some new folders: {new_layers}")

            invalid_layers = self._layers - found_folders
            if len(invalid_layers) > 0:
                _log.info(f"EOmaps: ... could not find the folders: {invalid_layers}")
            for i in invalid_layers:
                delattr(self, i)

            _log.info("EOmaps: done!")


class _RestWmsService(_WebServiceCollection):
    def __init__(self, service, s_name, s_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service = service
        self._s_name = s_name
        self._s_type = s_type

        self._layers = None

    @property
    def _url(self):
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
        elif self._service_type == "xyz":
            suffix = "/tile/{z}/{y}/{x}"
            WMSurl = url + suffix
            if requests.get(url + "/tile/{2}/{1}/{1}").status_code == 200:
                url = WMSurl
            else:
                url = None
        return url

    def _fetch_layers(self):
        self._layers = dict()
        url = self._url
        if url is not None:
            if self._service_type == "wms":
                wms = self._get_wms(url, **self._service_kwargs)
                layer_names = list(wms.contents.keys())
                for lname in layer_names:
                    self._layers["layer_" + _sanitize(lname)] = _WMSLayer(
                        self._m, wms, lname
                    )
            elif self._service_type == "wmts":
                wmts = self._get_wmts(url, **self._service_kwargs)
                layer_names = list(wmts.contents.keys())
                for lname in layer_names:
                    self._layers["layer_" + _sanitize(lname)] = _WMTSLayer(
                        self._m, wmts, lname
                    )
            elif self._service_type == "xyz":
                self._layers["xyz_layer"] = _XyzTileService(
                    self._m, url, 19, "xyz_layer"
                )

    @property
    @lru_cache()
    def add_layer(self):
        self._fetch_layers()
        if len(self._layers) == 0:
            _log.error(
                f"EOmaps: found no {self._service_type} layers for {self._s_name}"
            )
            return

        return SimpleNamespace(**self._layers)


class _MultiRestWmsService:
    def __init__(self, m, services, service_type, url, *args, **kwargs):
        self._m = m
        self._services = services
        self._service_type = service_type
        self._url = url

        self._fetch_services()

    @lru_cache()
    def _fetch_services(self):
        for (s_name, s_type) in self._services:
            wms_layer = _RestWmsService(
                m=self._m,
                service=self._url,
                s_name=s_name,
                s_type=s_type,
                service_type=self._service_type,
            )

            setattr(self, _sanitize(s_name), wms_layer)


class _RestApi(object):
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

            all_services = dict()
            r = self._post(service, _params=self._params)
            # parse all services that are not inside a folder
            for s in r["services"]:
                all_services.setdefault("SERVICES", []).append((s["name"], s["type"]))
            for s in r["folders"]:
                new = "/".join([service, s])
                endpt = self._post(new, _params=self._params)

                for serv in endpt["services"]:
                    if str(serv["type"]) == "MapServer":
                        all_services.setdefault(s, []).append(
                            (serv["name"], serv["type"])
                        )
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


class XyzRasterSource(RasterSource):
    """RasterSource that can be used with a SlippyImageArtist to fetch tiles."""

    def __init__(self, url, crs, maxzoom=19, transparent=True):
        """
        Class to fetch tiles from xyz services with a SlippyImageArtist.

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

        self._factory = TileFactory(
            self.url,
            desired_tile_form=self.desired_tile_form,
        )

    # function to estimate a proper zoom-level
    @staticmethod
    def _getz(d, zmax):
        # see https://wiki.openstreetmap.org/wiki/Zoom_levels
        # see https://stackoverflow.com/a/75251360/9703451

        equatorial_circumfence = 40075016.68557849
        # (e.g. self._crs.globe.semiminor_axis * np.pi * 2)

        z = int(np.clip(np.ceil(np.log2(1 / d * equatorial_circumfence)), 0, zmax))
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
        from cartopy.io.ogc_clients import LocatedImage, _target_extents

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

            target_extent = _target_extents(extent, wms_proj, output_proj)
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
                source_proj=wms_proj,
                source_extent=original_extent,
                target_proj=output_proj,
                target_res=regrid_shape,
                target_extent=target_extent,
                mask_extrapolated=True,
            )

            if origin == "upper":
                # revert to the initial origin
                img = img[::-1]

        return LocatedImage(img, extent)

    def fetch_raster(self, projection, extent, target_resolution):
        from cartopy.io.ogc_clients import _target_extents

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


class _XyzTileService:
    """General class for using x/y/z tile-service urls as WebMap layers."""

    def __init__(self, m, url, maxzoom=19, name=None):
        self._m = m
        self._factory = None
        self._artist = None

        self.url = url
        self._maxzoom = maxzoom
        self.name = name

    def _reinit(self, m):
        return _XyzTileService(m, url=self.url, maxzoom=self._maxzoom, name=self.name)

    def __call__(
        self,
        layer=None,
        transparent=False,
        alpha=1,
        interpolation="spline36",
        zorder=0,
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
        zorder : float
            The zorder of the artist (e.g. the stacking level of overlapping artists)
            The default is -5
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
                    layer, transparent, alpha, interpolation, zorder, **kwargs
                )
        else:

            kwargs.setdefault("interpolation", interpolation)
            kwargs.setdefault("zorder", zorder)
            kwargs.setdefault("alpha", alpha)
            kwargs.setdefault("origin", "lower")

            if self._layer in ["all", self._m.BM.bg_layer]:
                # add the layer immediately if the layer is already active
                self._do_add_layer(self._m, layer=self._layer, **kwargs)
            else:
                # delay adding the layer until it is effectively activated
                _add_pending_webmap(self._m, self._layer, self.name)
                self._m.BM.on_layer(
                    func=partial(self._do_add_layer, **kwargs),
                    layer=self._layer,
                    persistent=False,
                    m=self._m,
                )

    def _do_add_layer(self, m, layer, **kwargs):
        # actually add the layer to the map.
        _log.info(f"EOmaps: ... adding wms-layer {self.name}")

        self._raster_source = XyzRasterSource(
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
        img = SlippyImageArtistNew(m.ax, self._raster_source, **kwargs)
        with self._m.ax.hold_limits():
            m.ax.add_image(img)
        self._artist = img

        self._artist.set_label(f"WebMap service: {self.name}")

        # attach the info to the artist so it can be identified by the companion widget
        if hasattr(self, "_EOmaps_info"):
            self._artist._EOmaps_info = self._EOmaps_info
        if hasattr(self, "_EOmaps_source_code"):
            self._artist._EOmaps_source_code = self._EOmaps_source_code

        m.BM.add_bg_artist(self._artist, layer=layer)


class _XyzTileServiceNonEarth(_XyzTileService):
    def __call__(self, *args, **kwargs):
        _log.info(
            f"EOmaps: The WebMap service '{self.name}' shows images from a "
            "different celestrial body projected to an earth-based crs! "
            "Units used in scalebars, geod_crices etc. represent earth-based units!"
        )
        super().__call__(*args, **kwargs)


# ------------------------------------------------------------------------------
# The following is very much copied from cartopy.mpl.slippy_image_artist.py
# https://github.com/SciTools/cartopy/blob/main/lib/cartopy/mpl/slippy_image_artist.py

# The only changes are that user-interaction is handled internally by EOmaps
# instead of using the self.user_is_interacting sentinel.

# ------------------------------------------------------------------------------

from matplotlib.image import AxesImage
import matplotlib.artist


def refetch_wms_on_size_change(refetch):
    """
    Set the behavior of WebMap services with respect to size changes.

    A size change is triggered if:

    - The axis that shows the wms-service is re-sized
    - The figure is re-sized
    - The figure dpi changes
    - The figure is saved with a dpi-value other than the current figure dpi

    By default, WebMap services are dynamically re-fetched on any size-change.
    (this also means that saving figures at high dpi-values will cause a
    re-fetch of webmap services which might result in a different look
    of the exported image!)

    Note
    ----
    This will set the GLOBAL behavior for ALL EOmaps WebMap services!

    Parameters
    ----------
    refetch : bool

        - If True: WebMap services are dynamically re-fetched on size changes
        - If False: WebMap services are only re-fetched if the axis-extent
          changes.
    """
    SlippyImageArtistNew._refetch_on_size_change = refetch


@contextmanager
def _cx_refetch_wms_on_size_change(refetch):
    val = SlippyImageArtistNew._refetch_on_size_change

    try:
        SlippyImageArtistNew._refetch_on_size_change = refetch
        yield
    finally:
        SlippyImageArtistNew._refetch_on_size_change = val


class SlippyImageArtistNew(AxesImage):
    """
    A subclass of :class:`~matplotlib.image.AxesImage` which provides an
    interface for getting a raster from the given object with interactive
    slippery map type functionality.

    Kwargs are passed to the AxesImage constructor.

    """

    # Indicator if WebMap services should be dynamically re-fetched
    # if the size of the axes or figure changes
    # (NOTE: a size-change also triggers if the figure dpi changes
    # or if m.savefig() is called with a dpi value different than the current
    # dpi!)
    _refetch_on_size_change = True

    def __init__(self, ax, raster_source, **kwargs):
        self.raster_source = raster_source
        # This artist fills the Axes, so should not influence layout.
        kwargs.setdefault("in_layout", False)
        kwargs.setdefault("zorder", -5)
        kwargs.setdefault("animated", True)

        super().__init__(ax, **kwargs)

        self.cache = []

        ax.callbacks.connect("xlim_changed", self.on_xlim)
        self._prev_extent = (0, 0)
        self._prev_size = (ax.bbox.width, ax.bbox.height)

        # indicator if WebMaps should be re-fetched if the size of the
        # axes (e.g. also the figure size or dpi) changes.

    def on_xlim(self, *args, **kwargs):
        self.stale = True

    def get_window_extent(self, renderer=None):
        return self.axes.get_window_extent(renderer=renderer)

    @matplotlib.artist.allow_rasterization
    def draw(self, renderer, *args, **kwargs):
        if not self.get_visible():
            return

        try:
            ax = self.axes
            window_extent = ax.get_window_extent()
            [x1, y1], [x2, y2] = ax.viewLim.get_points()

            # only fetch images if one of the following is true:
            # - the map extent changed
            # - the size of the axis, figure or the figure-dpi changed
            # - the cache is empty

            extent_changed = self._prev_extent != (x1, x2, y1, y2)
            axsize_changed = self._prev_size != (ax.bbox.width, ax.bbox.height)

            if (
                extent_changed
                or (self._refetch_on_size_change and axsize_changed)
                or len(self.cache) == 0
            ):
                # only re-fetch tiles if the extent has changed
                located_images = self.raster_source.fetch_raster(
                    ax.projection,
                    extent=[x1, x2, y1, y2],
                    target_resolution=(window_extent.width, window_extent.height),
                )
                self.cache = located_images
                self._prev_extent = (x1, x2, y1, y2)
                self._prev_size = (ax.bbox.width, ax.bbox.height)

            for img, extent in self.cache:
                try:
                    clippath = self.axes.spines["geo"]
                    # make sure the geo-spine is updated before setting it as clippath
                    # (otherwise the path might still correspond to a previous extent)
                    clippath._adjust_location()

                    self.set_clip_path(
                        clippath.get_path(),
                        transform=self.axes.projection._as_mpl_transform(self.axes),
                    )
                except Exception:
                    _log.error(
                        "EOmaps: unable to set clippath for WMS images",
                        exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                    )

                with ax.hold_limits():
                    self.set_array(img)
                    self.set_extent(extent)
                    super().draw(renderer, *args, **kwargs)
            self.stale = False

        except Exception:
            _log.error(
                "EOmaps: ... could not fetch WebMap service",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

            if self in self.axes._mouseover_set:
                self.axes._mouseover_set.remove(self)

    def can_composite(self):
        # As per https://github.com/SciTools/cartopy/issues/689, disable
        # compositing multiple raster sources.
        return False

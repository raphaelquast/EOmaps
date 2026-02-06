# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""General definition of Maps objects."""

import logging

_log = logging.getLogger(__name__)

import importlib.metadata
from functools import wraps
from contextlib import ExitStack
import copy

import matplotlib.pyplot as plt
import matplotlib.path as mpath
from cartopy import crs as ccrs
import numpy as np

from .helpers import _add_to_docstring

from ._maps_base import MapsBase, MapsLayerBase
from .mixins.add_mixin import AddMixin
from .mixins.gpd_mixin import GeopandasMixin
from .mixins.clipboard_mixin import ClipboardMixin
from .mixins.companion_mixin import CompanionMixin
from .mixins.tools_mixin import ToolsMixin
from .mixins.data_mixin import DataMixin
from .mixins.callback_mixin import CallbackMixin


__version__ = importlib.metadata.version("eomaps")


class Maps(
    MapsLayerBase,
    MapsBase,
    AddMixin,
    GeopandasMixin,
    ClipboardMixin,
    CallbackMixin,
    CompanionMixin,
    ToolsMixin,
    DataMixin,
):
    """
    The base-class for generating plots with EOmaps.

    The first Maps object that is initialized will create a new matplotlib `Figure`
    and a cartopy `GeoAxes` for a map.

    You can then create additional `Maps` objects on the same figure with the following
    methods:


    See Also
    --------
    Maps.l : :py:class:`~eomaps._maps_base.LayerAccessor` to create/access layers on the map

    Maps.new_layer : Create a new layer for the map.

    Maps.new_map : Add a new map to the figure.

    Maps.new_inset_map : Add a new inset-map to the figure.

    :py:class:`~eomaps.mapsgrid.MapsGrid` : Initialize a grid of Maps objects

    Parameters
    ----------
    crs : int or a cartopy-projection, optional
        The projection of the map.
        If int, it is identified as an epsg-code
        Otherwise you can specify any projection supported by `cartopy.crs`
        A list for easy-accses is available as `Maps.CRS`

        The default is 4326.
    layer : str, optional
        The name of the plot-layer assigned to this Maps-object.
        The default is "base".

    Other Parameters
    ----------------
    f : matplotlib.Figure, optional
        Explicitly specify the matplotlib figure instance to use.
        (ONLY useful if you want to add a map to an already existing figure!)

          - If None, a new figure will be created (accessible via m.f)
          - Connected maps-objects will always share the same figure! You do
            NOT need to specify it (just provide the parent and you're fine)!

        The default is None
    ax : int, list, tuple, matplotlib.Axes, matplotlib.gridspec.SubplotSpec or None
        Explicitly specify the position of the axes or use already existing axes.

        Possible values are:

        - None:
            Initialize a new axes at the center of the figure (the default)
        - A tuple of 4 floats (*left*, *bottom*, *width*, *height*)
            The absolute position of the axis in relative figure-coordinates
            (e.g. in the range [0 , 1])
            NOTE: since the axis-size is dependent on the plot-extent, the size of
            the map will be adjusted to fit in the provided bounding-box.
        - A tuple of 3 integers (*nrows*, *ncols*, *index*)
            The map will be positioned at the *index* position of a grid
            with *nrows* rows and *ncols* columns. *index* starts at 1 in the
            upper left corner and increases to the right. *index* can also be
            a two-tuple specifying the (*first*, *last*) indices (1-based, and
            including *last*) of the subplot, e.g., ``ax = (3, 1, (1, 2))``
            makes a map that spans the upper 2/3 of the figure.
        - A 3-digit integer
            Same as using a tuple of three single-digit integers.
            (e.g. 111 is the same as (1, 1, 1) )
        - `matplotlib.gridspec.SubplotSpec`:
            Use the SubplotSpec for initializing the axes.
        - `matplotlib.Axes`:
            Directly use the provided figure and axes instances for plotting.
            NOTE: The axes MUST be a geo-axes with `m.crs_plot` projection!
    preferred_wms_service : str, optional
        Set the preferred way for accessing WebMap services if both WMS and WMTS
        capabilities are possible.
        The default is "wms"
    kwargs :
        additional kwargs are passed to `matplotlib.pyplot.figure()`
        - e.g. figsize=(10,5)

    Examples
    --------
    Create a new Maps object and initialize a figure and axes for a map.

    >>> from eomaps import Maps
    >>> m = Maps()
    >>> # add basic background features to the map
    >>> m.add_feature.preset("coastline", "ocean", "land")
    >>> # create a new layer and add more features
    >>> m.l.my_layer.add_feature.physical.coastline(fc="none", ec="b", lw=2, scale=50)
    >>> m.l.my_layer.add_feature.cultural.admin_0_countries(fc=(.2,.1,.4,.2), ec="b", lw=1, scale=50)
    >>> # overlay a part of the new layer in a circle if you click on the map
    >>> m.cb.click.attach.peek_layer("my_layer", how=0.4, shape="round")

    Use Maps-objects as context-manager to close the map and free memory
    once the map is exported.

    >>> from eomaps import Maps
    >>> with Maps() as m:
    >>>     m.add_feature.preset.coastline()
    >>>     m.savefig(...)

    Note
    ----

    You can access possible crs via the `CRS` accessor (alias of `cartopy.crs`):

    >>> m = Maps(crs=Maps.CRS.Orthographic())

    """

    __version__ = __version__
    CRS = ccrs

    def __init__(
        self,
        crs=None,
        layer=None,
        f=None,
        ax=None,
        *args,
        **kwargs,
    ):

        super().__init__(
            crs=crs,
            layer=layer,
            f=f,
            ax=ax,
            *args,
            **kwargs,
        )

        if self.parent == self:
            self._cid_keypress = self.f.canvas.mpl_connect(
                "key_press_event", self._on_keypress
            )

    def new_map(
        self,
        ax=None,
        keep_on_top=False,
        inherit_data=False,
        inherit_classification=False,
        inherit_shape=False,
        **kwargs,
    ):
        """
        Create a new map that shares the figure with this Maps-object.

        Note
        ----
        Using this function, for example:

        >>> m = Maps(ax=211)
        >>> m2 = m.new_map(ax=212, ...)

        is equivalent to:

        >>> m = Maps(ax=211)
        >>> m2 = Maps(f=m.f, ax=212, ...)


        Parameters
        ----------
        ax : int, list, tuple, matplotlib.Axes, matplotlib.gridspec.SubplotSpec or None
            Explicitly specify the position of the axes or use already existing axes.

            Possible values are:

            - None:
                Initialize a new axes at the center of the figure (the default)
            - A tuple of 4 floats (*left*, *bottom*, *width*, *height*)
                The absolute position of the axis in relative figure-coordinates
                (e.g. in the range [0 , 1])
                NOTE: since the axis-size is dependent on the plot-extent, the size of
                the map will be adjusted to fit in the provided bounding-box.
            - A tuple of 3 integers (*nrows*, *ncols*, *index*)
                The map will be positioned at the *index* position of a grid
                with *nrows* rows and *ncols* columns. *index* starts at 1 in the
                upper left corner and increases to the right. *index* can also be
                a two-tuple specifying the (*first*, *last*) indices (1-based, and
                including *last*) of the subplot, e.g., ``ax = (3, 1, (1, 2))``
                makes a map that spans the upper 2/3 of the figure.
            - A 3-digit integer
                Same as using a tuple of three single-digit integers.
                (e.g. 111 is the same as (1, 1, 1) )
            - `matplotlib.gridspec.SubplotSpec`:
                Use the SubplotSpec for initializing the axes.
            - `matplotlib.Axes`:
                Directly use the provided figure and axes instances for plotting.
                NOTE: The axes MUST be a geo-axes with `m.crs_plot` projection!
        keep_on_top : bool
            If True, this map will be drawn on top of all other axes.
            (e.g. similar to InsetMaps)
            The default is False.
        preferred_wms_service : str, optional
            Set the preferred way for accessing WebMap services if both WMS and WMTS
            capabilities are possible.
            The default is "wms"
        inherit_data, inherit_classification, inherit_shape : bool
            Indicator if the corresponding properties should be inherited from
            the parent Maps-object.

            By default only the shape is inherited.

            For more details, see :py:meth:`Maps.inherit_data` and
            :py:meth:`Maps.inherit_classification`
        kwargs :
            additional kwargs are passed to `matplotlib.pyplot.figure()`
            - e.g. figsize=(10,5)

        Returns
        -------
        m: EOmaps.Maps
            The Maps object representing the new map.

        """
        m2 = Maps(f=self.f, ax=ax, parent=self.parent, **kwargs)

        if inherit_data:
            m2.inherit_data(self)
        if inherit_classification:
            m2.inherit_classification(self)
        if inherit_shape and self._shape_assigned:
            getattr(m2.set_shape, self.shape.name)(**self.shape._initargs)

        if np.allclose(self.ax.bbox.bounds, m2.ax.bbox.bounds):
            _log.warning(
                "EOmaps:The new map overlaps exactly with the parent map! "
                "Use `ax=...` or the LayoutEditor to adjust the position of the map."
            )

        if keep_on_top is True:
            m2.ax.set_label("inset_map")

            spine = m2.ax.spines["geo"]
            if spine in self.BM._bg_artists.get("___SPINES__", []):
                self.BM.remove_bg_artist(spine, layer="___SPINES__")
            if spine not in self.BM._bg_artists.get("__inset___SPINES__", []):
                self.BM.add_bg_artist(spine, layer="__inset___SPINES__")

        return m2

    def new_layer(
        self,
        layer=None,
        inherit_data=False,
        inherit_classification=False,
        inherit_shape=True,
        **kwargs,
    ):
        """
        Create a new Maps-object that shares the same plot-axes.

        Parameters
        ----------
        layer : str or None
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.
        inherit_data, inherit_classification, inherit_shape : bool
            Indicator if the corresponding properties should be inherited from
            the parent Maps-object.

            By default only the shape is inherited.

            For more details, see :py:meth:`Maps.inherit_data` and
            :py:meth:`Maps.inherit_classification`

        Returns
        -------
        eomaps.Maps
            A connected copy of the Maps-object that shares the same plot-axes.

        Examples
        --------
        Create a new Maps-object **on an existing layer**

        >>> from eomaps import Maps
        >>> m = Maps(layer="base")    # m.layer == "base"
        >>> m2 = m.new_layer()        # m2.layer == "base"


        Create a new Maps-object representing a **new layer**

        >>> from eomaps import Maps
        >>> m = Maps(layer="base")           # m.layer == "base"
        >>> m2 = m.new_layer("a new layer")  # m2.layer == "a new layer"


        Create a new layer and immediately delete it after it has been exported.
        (useful to free memory if a lot of layers are be exported)

        >>> from eomaps import Maps
        >>> m = Maps(layer="base")
        >>> with m.new_layer("a new layer") as m2:
        >>>     ...
        >>>     m2.show()                           # make the layer visible
        >>>     m2.savefig(...)                     # save it as an image


        See Also
        --------
        Maps.copy : general way for copying Maps objects

        """

        inherit_data = kwargs.get("copy_data_specs", inherit_data)
        inherit_classification = kwargs.get(
            "copy_classify_specs", inherit_classification
        )
        inherit_shape = kwargs.get("copy_shape", inherit_shape)

        if layer is None:
            layer = self.layer
        else:
            layer = str(layer)
            if len(layer) == 0:
                raise SyntaxError(
                    "EOmaps: Unable to create a layer with an empty layer-name!"
                )

        layer_name, *postfix = layer.split("__", 1)
        if postfix:
            _log.debug(
                f"EOmaps: New sublayer {postfix[0]} on layer '{layer_name}' created."
            )
        else:
            _log.debug(f"EOmaps: New layer '{layer_name}' created.")

        m = self.copy(
            data_specs=False,
            classify_specs=False,
            shape=False,
            ax=self.ax,
            layer=layer_name,
            parent=self.parent,
        )

        if inherit_data:
            m.inherit_data(self)
        if inherit_classification:
            m.inherit_classification(self)
        if inherit_shape and self._shape_assigned:
            getattr(m.set_shape, self.shape.name)(**self.shape._initargs)

        # make sure the new layer does not attempt to reset the extent if
        # it has already been set on the parent layer
        m._set_extent_on_plot = self._set_extent_on_plot

        # re-initialize all sliders and buttons to include the new layer
        self.util._reinit_widgets()

        # share the companion-widget with the parent
        m._companion_widget = self._companion_widget

        self.l._ingest_layer(m, name=layer)

        return m

    def new_inset_map(
        self,
        xy=(45, 45),
        xy_crs=4326,
        radius=5,
        radius_crs=None,
        plot_position=(0.5, 0.5),
        plot_size=0.5,
        inset_crs=4326,
        layer=None,
        boundary=True,
        background_color="w",
        shape="ellipses",
        indicate_extent=True,
        indicator_line=False,
    ):
        """
        Create a new (empty) inset-map that shows a zoomed-in view on a given extent.

        The returned Maps-object can then be used to populate the inset-map with
        features, datasets etc.

        See examples below on how to use inset-maps.


        Note
        ----
        - By default NO features are added to the inset-map!
          Use it just like any other Maps-object to add features or plot datasets!
        - Zooming is disabled on inset-maps for now due to issues with zoom-events on
          overlapping axes.
        - Non-rectangular cropping of WebMap services is not yet supported.
          (e.g. use "rectangles" as shape and the native CRS of the WebMap service
          for the inset map.)

        Parameters
        ----------
        xy : tuple, optional
            The center-coordinates of the area to indicate.
            (provided in the xy_crs projection)
            The default is (45., 45.).
        xy_crs : any, optional
            The crs used for specifying the center position of the inset-map.
            (can be any crs definition supported by PyProj)
            The default is 4326 (e.g. lon/lat).
        radius : float or tuple, optional
            The radius of the extent to indicate.
            (provided in units of the radius_crs projection)
            The default is 5.
        radius_crs : None or a crs-definition, optional
            The crs used for specifying the radius. (can be any crs definition
            supported by PyProj)

            - If None:  The crs provided as "xy_crs" is used
            - If shape == "geod_circles", "radius_crs" must be None since the radius
              of a geodesic circle is defined in meters!

            The default is None.
        plot_position : tuple, optional
            The center-position of the inset map in relative units (0-1) with respect to
            the figure size. The default is (.5,.5).
        plot_size : float, optional
            The relative size of the inset-map compared to the figure width.
            The default is 0.5.
        inset_crs : any, optional
            The crs that is used in the inset-map.
            The default is 4326.
        layer : str or None, optional
            The layer associated with the inset-map.
            If None (the default), the layer of the Maps-object used to create
            the inset-map is used.
        boundary: bool, str or dict, optional
            - If True: indicate the boundary of the inset-map with default colors
              (e.g.: {"ec":"r", "lw":2})
            - If False: don't add edgecolors to the boundary of the inset-map
            - If a string is provided, it is identified as the edge-color of the
              boundary (e.g. any named matplotlib color like "r", "g", "darkblue"...)
            - if dict: use the provided values for "ec" (e.g. edgecolor) and
              "lw" (e.g. linewidth)

            The default is True.
        background_color: str, tuple or None
            The background color to use.

            - if str: a matplotlib color identifier (e.g. "r", "#162347")
            - if tuple: a RGB or RGBA tuple (values must be in the range 0-1)
            - If None, no background patch will be drawn (e.g. transparent)

            The default is "w" (e.g. white)
        shape : str, optional
            The shape to use. Can be either "ellipses", "rectangles" or "geod_circles".
            The default is "ellipses".
        indicate_extent : bool or dict, optional

            - If True: add a polygon representing the inset-extent to the parent map.
            - If a dict is provided, it will be used to update the appearance of the
              added polygon (e.g. facecolor, edgecolor, linewidth etc.)

            NOTE: you can also use `m_inset.add_extent_indicator(...)` to manually
            indicate the inset-shape on arbitrary Maps-objects.

            The default is True.
        indicator_line : bool or dict, optional

            - If True: add a line that connects the inset-map to the indicated extent
              on the parent map
            - If a dict is provided, it is used to update the appearance of the line
              (e.g. c="r", lw=2, ...)

            NOTE: you can also use `m_inset.add_indicator_line(...)` to manually
            indicate the inset-shape on arbitrary Maps-objects.

            The default is False.

        Returns
        -------
        m : eomaps.inset_maps.InsetMaps
            A InsetMaps-object of the inset-map.
            (you can use it just like any other Maps-object!)

        See Also
        --------
        Maps.add_extent_indicator : Indicate inset-extent on another map (as polygon).
        Maps.set_inset_position : Set the (center) position and size of the inset-map.

        Examples
        --------
        Simple example:

        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>> m2 = m.new_inset_map(xy=(45, 45), radius=10,
        >>>                      plot_position=(.3, .5), plot_size=.7)
        >>> m2.add_feature.preset.ocean()

        ... a bit more complexity:

        >>> m = Maps(Maps.CRS.Orthographic())
        >>> m.add_feature.preset.coastline() # add some coastlines
        >>> m2 = m.new_inset_map(xy=(5, 45),
        >>>                      xy_crs=4326,
        >>>                      shape="geod_circles",
        >>>                      radius=1000000,
        >>>                      plot_position=(.3, .4),
        >>>                      plot_size=.5,
        >>>                      inset_crs=3035,
        >>>                      edgecolor="g",
        >>>                      indicate_extent=False)
        >>>
        >>> m2.add_feature.preset.coastline()
        >>> m2.add_feature.preset.ocean()
        >>> m2.add_feature.preset.land()
        >>> m2.set_data([1, 2, 3], [5, 6, 7], [45, 46, 47], crs=4326)
        >>> m2.plot_map()
        >>> m2.add_annotation(ID=1)
        >>> m2.add_extent_indicator(m, ec="g", fc=(0,1,0,.25))

        Multi-layer inset-maps:

        >>> m = Maps(layer="first")
        >>> m.add_feature.preset.coastline()
        >>> m3 = m.new_layer("second")
        >>> m3.add_feature.preset.ocean()
        >>> # create an inset-map on the "first" layer
        >>> m2 = m.new_inset_map(layer="first")
        >>> m2.add_feature.preset.coastline()
        >>> # create a new layer of the inset-map that will be
        >>> # visible if the "second" layer is visible
        >>> m3 = m2.new_layer(layer="second")
        >>> m3.add_feature.preset.coastline()
        >>> m3.add_feature.preset.land()

        >>> m.util.layer_selector()

        """
        # to avoid circular imports
        from .inset_maps import InsetMaps

        m2 = InsetMaps(
            parent=self,
            crs=inset_crs,
            layer=layer,
            xy=xy,
            radius=radius,
            plot_position=plot_position,
            plot_size=plot_size,
            xy_crs=xy_crs,
            radius_crs=radius_crs,
            boundary=boundary,
            background_color=background_color,
            shape=shape,
            indicate_extent=indicate_extent,
            indicator_line=indicator_line,
        )

        return m2

    @_add_to_docstring(
        prefix=(
            "Convenience wrapper around `Figure.add_subplot` to"
            " add a new matpltolib-subplot to a figure.\n "
        ),
        insert={
            "Other Parameters": (
                "layer : str\n"
                "    The layer at which the subplot should be visible.\n"
                "    If None, the layer of the calling Maps-object is used.",
                1,
            )
        },
    )
    @wraps(
        plt.Figure.add_subplot,
        assigned=("__doc__", "__annotations__", "__type_params__"),
    )
    def new_subplot(self, *args, layer=None, **kwargs):
        ax = self.f.add_subplot(*args, **kwargs)
        self.BM.add_artist(ax, layer=layer)
        return ax

    def set_frame(self, rounded=0, gdf=None, countries=None, **kwargs):
        """
        Set the properties of the map boundary and the background patch.

        - use `rounded` kwarg to get a rectangle border with rounded corners
        - use `gdf` kwarg to use `geopandas.GeoDataFrame` geometries as map-border
        - use `countries` kwarg to set the map-border to one (or more) countries.

        All additional kwargs are used to style the border-line.

        Parameters
        ----------
        rounded : float, optional
            If provided, use a rectangle with rounded corners as map boundary
            line. The corners will be rounded with respect to the provided
            fraction (0=no rounding, 1=max. radius). The default is None.
        gdf : geopandas.GeoDataFrame or path
            A geopandas.GeoDataFrame that contains geometries that should be used as
            map-frame.

            If a path (string or pathlib.Path) is provided, the corresponding file
            will be read as a geopandas.GeoDataFrame and the boundaries of the
            contained geometries will be used as map-boundary.

            The default is None.
        kwargs :
            Additional kwargs to style the boundary line (e.g. the spine)
            and the background patch

            Possible args for the boundary-line:

            - "edgecolor" or "ec": The line color
            - "linewidth" or "lw": The line width
            - "linestyle" or "ls": The line style
            - "path_effects": A list of path-effects to apply to the line

            Possible args for the background-patch:

            - "facecolor" or "fc": The color of the background patch

        Other Parameters
        ----------------
        set_extent : bool, optional
            Only relevant if `gdf` is used.
            If True, the map-extent is set to the extent of the provided geometry.
            The default is True.
        scale : int, optional
            Only relevant if `countries` is used.
            The scale factor of the used NaturalEarth dataset.
            Must be one of [10, 50, 110]. The default is 50.

        Examples
        --------

        >>> m = Maps()
        >>> m.add_feature.preset.ocean()
        >>> m.set_frame(fc="r", ec="b", lw=3, rounded=.2)

        Customize the map-boundary style

        >>> import matplotlib.patheffects as pe
        >>> m = Maps()
        >>> m.add_feature.preset.ocean(fc="k")
        >>> m.set_frame(
        >>>     facecolor=(.8, .8, 0, .5), edgecolor="w", linewidth=2,
        >>>     rounded=.5,
        >>>     path_effects=[pe.withStroke(linewidth=7, foreground="m")])

        Set the map-boundary to a custom polygon (in this case the boarder of Austria)

        >>> m = Maps()
        >>> m.add_feature.preset.land(fc="k")
        >>> # Get a GeoDataFrame with all country-boarders from NaturalEarth
        >>> gdf = m.add_feature.cultural.admin_0_countries.get_gdf()
        >>> # set the map-boundary to the Austrian country-boarder
        >>> m.set_frame(gdf = gdf[gdf.NAME=="Austria"])

        Set the map-boundary to the country-border of Austria and Italy

        >>> m = Maps(facecolor="0.4")
        >>> m.set_frame(countries=["Austria", "Italy"], ec="r", lw=2, fc="k")

        """
        set_extent = kwargs.pop("set_extent", True)

        for key in ("fc", "facecolor"):
            if key in kwargs:
                self.ax.patch.set_facecolor(kwargs.pop(key))

        if countries is not None:
            assert gdf is None, "You cannot specify both 'gdf' and 'countries'"

            gdf = self._get_country_frame(countries, scale=kwargs.pop("scale", 50))

        if gdf is not None:
            assert (
                rounded == 0
            ), "EOmaps: using rounded > 0 is not supported for gdf frames!"

            self._set_gdf_path_boundary(self._handle_gdf(gdf), set_extent=set_extent)

        elif rounded:
            assert (
                rounded <= 1
            ), "EOmaps: rounded corner fraction must be between 0 and 1"

            self.ax._EOmaps_rounded_spine_frac = rounded
            theta = np.linspace(0, np.pi / 2, 50)  # use 50 intermediate points
            s, c = np.sin(theta), np.cos(theta)

            # attach a function to dynamically update the corners of the
            # map boundary prior to fetching a background
            # Note: this function is only attached once and the relevant
            # properties are fetched from the axes!
            if not getattr(self.ax, "_EOmaps_rounded_spine_attached", False):

                def cb(*args, **kwargs):
                    if self.ax._EOmaps_rounded_spine_frac == 0:
                        return

                    x0, x1, y0, y1 = self.get_extent(self.crs_plot)
                    r = min(x1 - x0, y1 - y0) * self.ax._EOmaps_rounded_spine_frac / 2

                    xs = [
                        x0,
                        *(x0 + r - r * c),
                        x0 + r,
                        x1 - r,
                        *(x1 - r + r * s),
                        x1,
                        x1,
                        *(x1 - r + r * c),
                        x1 - r,
                        x0 + r,
                        *(x0 + r - r * s),
                        x0,
                    ]

                    ys = [
                        y1 - r,
                        *(y1 - r + r * s),
                        y1,
                        y1,
                        *(y1 - r + r * c),
                        y1 - r,
                        y0 + r,
                        *(y0 + r - r * s),
                        y0,
                        y0,
                        *(y0 + r - r * c),
                        y0 + r,
                    ]

                    path = mpath.Path(np.column_stack((xs, ys)))
                    self.ax.set_boundary(path, transform=self.crs_plot)

                self.BM._before_fetch_bg_actions.append(cb)
                self.ax._EOmaps_rounded_spine_attached = True

        self.ax.spines["geo"].update(kwargs)

        self.redraw()

    def copy(
        self,
        data_specs=False,
        classify_specs=True,
        shape=True,
        **kwargs,
    ):
        """
        Create a (deep)copy of the Maps object that shares selected specifications.

        -> useful to quickly create plots with similar configurations

        Parameters
        ----------
        data_specs, classify_specs, shape : bool or "shared", optional
            Indicator if the corresponding properties should be copied.

            - if True: ALL corresponding properties are copied

            By default, "classify_specs" and the "shape" are copied.

        kwargs :
            Additional kwargs passed to `m = Maps(**kwargs)`
            (e.g. crs, f, ax, orientation, layer)

        Returns
        -------
        copy_cls : eomaps.Maps object
            a new Maps class.
        """
        copy_cls = Maps(**kwargs)

        if data_specs is True:
            data_specs = list(self.data_specs.keys())
            copy_cls.set_data(
                **{key: copy.deepcopy(val) for key, val in self.data_specs}
            )

        if shape is True:
            if self.shape is not None:
                getattr(copy_cls.set_shape, self.shape.name)(**self.shape._initargs)

        if classify_specs is True:
            classify_specs = list(self._classify_specs.keys())
            copy_cls.set_classify_specs(
                scheme=self._classify_specs.scheme, **self._classify_specs
            )

        return copy_cls

    def redraw(self, *args):
        self._data_manager.last_extent = None
        super().redraw(*args)

    @wraps(MapsBase.snapshot)
    def snapshot(self, *args, **kwargs):
        self._hide_all_companion_widget_indicators()
        super().snapshot(*args, **kwargs)

    @_add_to_docstring(
        insert={
            "Other Parameters": (
                "refetch_wms : bool\n"
                "    If True, re-fetch EOmaps WebMap services with respect to "
                "the dpi of the exported figure before exporting the image. "
                "\n\n    NOTE: This might fail for high-dpi exports and might "
                "result in a completely different appearance of the wms-images "
                "in the exported file! "
                "\n\n    See `m.refetch_wms_on_size_change()` for more details. "
                "The default is False",
                1,
            )
        }
    )
    @wraps(MapsBase.savefig)
    def savefig(self, *args, refetch_wms=False, rasterize_data=True, **kwargs):
        with ExitStack() as stack:
            # re-fetch webmap services if required
            if refetch_wms is False:
                if getattr(self, "add_wms", None) is not None:
                    stack.enter_context(
                        self.add_wms._cx_refetch_wms_on_size_change(refetch_wms)
                    )

            self._hide_all_companion_widget_indicators()

            for m in (self, *self._children):
                # handle colorbars
                for cb in m._colorbars:
                    for a in (cb.ax_cb, cb.ax_cb_plot):
                        stack.enter_context(a._cm_set(animated=False))

                # set if data should be rasterized on vector export
                if m.coll is not None:
                    stack.enter_context(m.coll._cm_set(rasterized=rasterize_data))

            dpi = kwargs.get("dpi", None)

            shade_dpi_changed = False
            if dpi is not None and dpi != self.f.dpi:
                shade_dpi_changed = True
                # set the shading-axis-size to reflect the used dpi setting
                self._update_shade_axis_size(dpi=dpi)

            super().savefig(*args, **kwargs)

        if shade_dpi_changed:
            # reset the shading-axis-size to the used figure dpi
            self._update_shade_axis_size()

    def cleanup(self):
        """
        Cleanup all references to the object so that it can be safely deleted.

        This function is primarily used internally to clear objects if the figure
        is closed.

        Note
        ----
        Executing this function will remove ALL attached callbacks
        and delete all assigned datasets & pre-computed values.

        ONLY execute this if you do not need to do anything with the layer
        """

        # close the companion-widget
        self._close_companion_widget()

        # de-register colormaps
        for cmap in self._registered_cmaps:
            plt.colormaps.unregister(cmap)

        try:
            # clear data-specs and all cached properties of the data
            try:
                self._coll = None
                self._data_manager.cleanup()

                if hasattr(self, "tree"):
                    del self.tree
                self.data_specs.delete()
            except Exception:
                _log.error(
                    "EOmaps-cleanup: Problem while clearing data specs",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

            # disconnect all click, pick and keypress callbacks
            try:
                self.cb._reset_cids()
                # cleanup callback-containers
                self.cb._clear_callbacks()
            except Exception:
                _log.error(
                    "EOmaps-cleanup: Problem while clearing callbacks",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

        except Exception:
            _log.error(
                "EOmaps: Cleanup problem!",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

        super().cleanup()

    def _on_keypress(self, event):
        if plt.get_backend().lower() == "webagg":
            return

        # NOTE: callback is only attached to the parent Maps object!
        self._ClipboardMixin__on_keypress(event)
        self._CompanionMixin__on_keypress(event)

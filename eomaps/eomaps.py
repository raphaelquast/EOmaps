# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""General definition of Maps objects."""

import logging

_log = logging.getLogger(__name__)

from types import SimpleNamespace
from contextlib import ExitStack
from functools import wraps
import importlib.metadata
import weakref
import copy

from pyproj import CRS
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.path as mpath
import matplotlib as mpl

from cartopy import crs as ccrs

from ._maps_base import MapsBase
from .mixins.add_mixin import AddMixin
from .mixins.gpd_mixin import GeopandasMixin
from .mixins.clipboard_mixin import ClipboardMixin
from .mixins.companion_mixin import CompanionMixin
from .mixins.tools_mixin import ToolsMixin

from .helpers import cmap_alpha, SearchTree, register_modules, _add_to_docstring
from .shapes import Shapes
from .colorbar import ColorBar
from ._containers import DataSpecs, ClassifySpecs
from .cb_container import CallbackContainer
from .reader import read_file, from_file, new_layer_from_file
from ._data_manager import DataManager


__version__ = importlib.metadata.version("eomaps")


class Maps(
    MapsBase,
    AddMixin,
    GeopandasMixin,
    ClipboardMixin,
    CompanionMixin,
    ToolsMixin,
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

    from_file = from_file
    new_layer_from_file = new_layer_from_file
    read_file = read_file

    CRS = ccrs

    # to make namespace accessible for sphinx
    set_shape = Shapes
    cb = CallbackContainer

    data_specs = DataSpecs

    def __init__(
        self,
        crs=None,
        layer=None,
        f=None,
        ax=None,
        preferred_wms_service="wms",
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

        self._inherit_classification = None

        self._colorbars = []
        self._coll = None  # slot for the collection created by m.plot_map()

        # a list to remember newly registered colormaps
        self._registered_cmaps = []

        # preferred way of accessing WMS services (used in the WMS container)
        assert preferred_wms_service in [
            "wms",
            "wmts",
        ], "preferred_wms_service must be either 'wms' or 'wmts' !"
        self._preferred_wms_service = preferred_wms_service

        # default classify specs
        self._classify_specs = ClassifySpecs(weakref.proxy(self))

        self.data_specs = DataSpecs(
            weakref.proxy(self),
            x=None,
            y=None,
            crs=4326,
        )

        # initialize the data-manager
        self._data_manager = DataManager(self._proxy(self))
        self._data_plotted = False
        self._set_extent_on_plot = True

        self.cb = self.cb(weakref.proxy(self))  # accessor for the callbacks

        # initialize the callbacks
        self.cb._init_cbs()

        self.new_layer_from_file = new_layer_from_file(weakref.proxy(self))

        self.set_shape = self.set_shape(weakref.proxy(self))
        self._shape = None
        # the dpi used for shade shapes
        self._shade_dpi = None

        # the radius is estimated when plot_map is called
        self._estimated_radius = None

        # a set to hold references to the compass objects
        self._compass = set()

        # evaluate and cache crs boundary bounds (for extent clipping)
        self._crs_boundary_bounds = self.crs_plot.boundary.bounds

        if self.parent == self:
            self._cid_keypress = self.f.canvas.mpl_connect(
                "key_press_event", self._on_keypress
            )

            self._wms_legend = dict()
            self._execute_callbacks = True

    @property
    def coll(self):
        """The collection representing the dataset plotted by m.plot_map()."""
        return self._coll

    @property
    def shape(self):
        """
        The shape that is used to represent the dataset if `m.plot_map()` is called.

        By default "ellipses" is used for datasets < 500k datapoints and for plots
        where no explicit data is assigned, and otherwise "shade_raster" is used
        for 2D datasets and "shade_points" is used for unstructured datasets.

        """

        if not self._shape_assigned:
            self._set_default_shape()
            self._shape._is_default = True

        return self._shape

    @property
    def colorbar(self):
        """
        Get the **most recently added** colorbar of this Maps-object.

        Returns
        -------
        ColorBar
            EOmaps colorbar object.
        """
        if len(self._colorbars) > 0:
            return self._colorbars[-1]

    @property
    def data(self):
        """The data assigned to this Maps-object."""
        return self.data_specs.data

    @data.setter
    def data(self, val):
        # for downward-compatibility
        self.data_specs.data = val

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
        m2 = Maps(f=self.f, ax=ax, **kwargs)

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

    def set_data(
        self,
        data=None,
        x=None,
        y=None,
        crs=None,
        encoding=None,
        cpos="c",
        cpos_radius=None,
        parameter=None,
    ):
        """
        Set the properties of the dataset you want to plot.

        Use this function to update multiple data-specs in one go
        Alternatively you can set the data-specifications via

            >>> m.data_specs.< property > = ...`

        Parameters
        ----------
        data : array-like
            The data of the Maps-object.
            Accepted inputs are:

            - a pandas.DataFrame with the coordinates and the data-values
            - a pandas.Series with only the data-values
            - a 1D or 2D numpy-array with the data-values
            - a 1D list of data values

        x, y : array-like or str, optional
            Specify the coordinates associated with the provided data.
            Accepted inputs are:

            - a string (corresponding to the column-names of the `pandas.DataFrame`)

              - ONLY if "data" is provided as a pandas.DataFrame!

            - a pandas.Series
            - a 1D or 2D numpy-array
            - a 1D list

            The default is "lon" and "lat".
        crs : int, dict or str
            The coordinate-system of the provided coordinates.
            Can be one of:

            - PROJ string
            - Dictionary of PROJ parameters
            - PROJ keyword arguments for parameters
            - JSON string with PROJ parameters
            - CRS WKT string
            - An authority string [i.e. 'epsg:4326']
            - An EPSG integer code [i.e. 4326]
            - A tuple of ("auth_name": "auth_code") [i.e ('epsg', '4326')]
            - An object with a `to_wkt` method.
            - A :class:`pyproj.crs.CRS` class

            (see `pyproj.CRS.from_user_input` for more details)

            The default is 4326 (e.g. geographic lon/lat crs)
        parameter : str, optional
            MANDATORY IF a pandas.DataFrame that specifies both the coordinates
            and the data-values is provided as `data`!

            The name of the column that should be used as parameter.

            If None, the first column (despite of the columns assigned as "x" and "y")
            will be used. The default is None.
        encoding : dict or False, optional
            A dict containing the encoding information in case the data is provided as
            encoded values (useful to avoid decoding large integer-encoded datasets).

            If provided, the data will be decoded "on-demand" with respect to the
            provided "scale_factor" and "add_offset" according to the formula:

            >>> actual_value = encoding["add_offset"] + encoding["scale_factor"] * value

            Note: Colorbars and pick-callbakcs will use the encoding-information to
            display the actual data-values!

            If False, no value-transformation is performed.
            The default is False
        cpos : str, optional
            Indicator if the provided x-y coordinates correspond to the center ("c"),
            upper-left corner ("ul"), lower-left corner ("ll") etc.  of the pixel.
            If any value other than "c" is provided, a "cpos_radius" must be set!
            The default is "c".
        cpos_radius : int or tuple, optional
            The pixel-radius (in the input-crs) that will be used to set the
            center-position of the provided data.
            If a number is provided, the pixels are treated as squares.
            If a tuple (rx, ry) is provided, the pixels are treated as rectangles.
            The default is None.

        Examples
        --------
        - using a single `pandas.DataFrame`

          >>> data = pd.DataFrame(dict(lon=[...], lat=[...], a=[...], b=[...]))
          >>> m.set_data(data, x="lon", y="lat", parameter="a", crs=4326)

        - using individual `pandas.Series`

          >>> lon, lat, vals = pd.Series([...]), pd.Series([...]), pd.Series([...])
          >>> m.set_data(vals, x=lon, y=lat, crs=4326)

        - using 1D lists

          >>> lon, lat, vals = [...], [...], [...]
          >>> m.set_data(vals, x=lon, y=lat, crs=4326)

        - using 1D or 2D numpy.arrays

          >>> lon, lat, vals = np.array([[...]]), np.array([[...]]), np.array([[...]])
          >>> m.set_data(vals, x=lon, y=lat, crs=4326)

        - integer-encoded datasets

          >>> lon, lat, vals = [...], [...], [1, 2, 3, ...]
          >>> encoding = dict(scale_factor=0.01, add_offset=1)
          >>> # colorbars and pick-callbacks will now show values as (1 + 0.01 * value)
          >>> # e.g. the "actual" data values are [0.01, 0.02, 0.03, ...]
          >>> m.set_data(vals, x=lon, y=lat, crs=4326, encoding=encoding)

        """
        if data is not None:
            self.data_specs.data = data

        if x is not None:
            self.data_specs.x = x

        if y is not None:
            self.data_specs.y = y

        if crs is not None:
            self.data_specs.crs = crs

        if encoding is not None:
            self.data_specs.encoding = encoding

        if cpos is not None:
            self.data_specs.cpos = cpos

        if cpos_radius is not None:
            self.data_specs.cpos_radius = cpos_radius

        if parameter is not None:
            self.data_specs.parameter = parameter

    @property
    def set_classify(self):
        """
        Interface to the classifiers provided by the 'mapclassify' module.

        To set a classification scheme for a given Maps-object, simply use:

        >>> m.set_classify.< SCHEME >(...)

        Where `< SCHEME >` is the name of the desired classification and additional
        parameters are passed in the call. (check docstrings for more info!)

        A list of available classification-schemes is accessible via
        `mapclassify.CLASSIFIERS`

            - BoxPlot (hinge)
            - EqualInterval (k)
            - FisherJenks (k)
            - FisherJenksSampled (k, pct, truncate)
            - HeadTailBreaks ()
            - JenksCaspall (k)
            - JenksCaspallForced (k)
            - JenksCaspallSampled (k, pct)
            - MaxP (k, initial)
            - MaximumBreaks (k, mindiff)
            - NaturalBreaks (k, initial)
            - Quantiles (k)
            - Percentiles (pct)
            - StdMean (multiples)
            - UserDefined (bins)

        Examples
        --------
        >>> m.set_classify.Quantiles(k=5)

        >>> m.set_classify.EqualInterval(k=5)

        >>> m.set_classify.UserDefined(bins=[5, 10, 25, 50])

        """
        (mapclassify,) = register_modules("mapclassify")

        s = SimpleNamespace(
            **{
                i: self._get_mcl_subclass(getattr(mapclassify, i))
                for i in mapclassify.CLASSIFIERS
            }
        )

        s.__doc__ = Maps.set_classify.__doc__

        return s

    def set_classify_specs(self, scheme=None, **kwargs):
        """
        Set classification specifications for the data.

        The classification is ultimately performed by the `mapclassify` module!

        Note
        ----
        The following calls have the same effect:

        >>> m.set_classify.Quantiles(k=5)
        >>> m.set_classify_specs(scheme="Quantiles", k=5)

        Using `m.set_classify()` is the same as using `m.set_classify_specs()`!
        However, `m.set_classify()` will provide autocompletion and proper
        docstrings once the Maps-object is initialized which greatly enhances
        the usability.

        Parameters
        ----------
        scheme : str
            The classification scheme to use.
            (the list is accessible via `mapclassify.CLASSIFIERS`)

            E.g. one of (possible kwargs in brackets):

                - BoxPlot (hinge)
                - EqualInterval (k)
                - FisherJenks (k)
                - FisherJenksSampled (k, pct, truncate)
                - HeadTailBreaks ()
                - JenksCaspall (k)
                - JenksCaspallForced (k)
                - JenksCaspallSampled (k, pct)
                - MaxP (k, initial)
                - MaximumBreaks (k, mindiff)
                - NaturalBreaks (k, initial)
                - Quantiles (k)
                - Percentiles (pct)
                - StdMean (multiples)
                - UserDefined (bins)

        kwargs :
            kwargs passed to the call to the respective mapclassify classifier
            (dependent on the selected scheme... see above)

        """
        register_modules("mapclassify")
        self._classify_specs._set_scheme_and_args(scheme, **kwargs)

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

    def set_shade_dpi(self, dpi=None):
        """
        Set the dpi used by "shade shapes" to aggregate datasets.

        This only affects the plot-shapes "shade_raster" and "shade_points".

        Note
        ----
        If dpi=None is used (the default), datasets in exported figures will be
        re-rendered with respect to the requested dpi of the exported image!

        Parameters
        ----------
        dpi : int or None, optional
            The dpi to use for data aggregation with shade shapes.
            If None, the figure-dpi is used.

            The default is None.

        """
        self._shade_dpi = dpi
        self._update_shade_axis_size()

    def inherit_data(self, m):
        """
        Use the data of another Maps-object (without copying).

        NOTE
        ----
        If the data is inherited, any change in the data of the parent
        Maps-object will be reflected in this Maps-object as well!

        Parameters
        ----------
        m : eomaps.Maps or None
            The Maps-object that provides the data.
        """
        if m is not None:
            self.data_specs = m.data_specs

            def set_data(*args, **kwargs):
                raise AssertionError(
                    "EOmaps: You cannot set data for a Maps object that "
                    "inherits data!"
                )

            self.set_data = set_data

    def inherit_classification(self, m):
        """
        Use the classification of another Maps-object when plotting the data.

        NOTE
        ----
        If the classification is inherited, the following arguments
        for `m.plot_map()` will have NO effect (they are inherited):

            - "cmap"
            - "vmin"
            - "vmax"

        Parameters
        ----------
        m : eomaps.Maps or None
            The Maps-object that provides the classification specs.
        """
        if m is not None:
            self._inherit_classification = self._proxy(m)
        else:
            self._inherit_classification = None

    def plot_map(
        self,
        layer=None,
        dynamic=False,
        set_extent=True,
        assume_sorted=True,
        indicate_masked_points=False,
        **kwargs,
    ):
        """
        Plot the dataset assigned to this Maps-object.

        - To set the data, see `m.set_data()`
        - To change the "shape" that is used to represent the datapoints, see
          `m.set_shape`.
        - To classify the data, see `m.set_classify` or `m.set_classify_specs()`

        NOTE
        ----
        Each call to `plot_map(...)` will override the previously plotted dataset!

        If you want to plot multiple datasets, use a new layer for each dataset!
        (e.g. via `m2 = m.new_layer()`)

        Parameters
        ----------
        layer : str or None
            The layer at which the dataset will be plotted.
            ONLY relevant if `dynamic = False`!

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer assigned to the Maps object is used (e.g. `m.layer`)

            The default is None.
        dynamic : bool
            If True, the collection will be dynamically updated.
        set_extent : bool
            Set the plot-extent to the data-extent.

            - if True: The plot-extent will be set to the extent of the data-coordinates
            - if False: The plot-extent is kept as-is

            The default is True
        assume_sorted : bool, optional
            ONLY relevant for the shapes "raster" and "shade_raster"
            (and only if coordinates are provided as 1D arrays and data is a 2D array)

            Sort values with respect to the coordinates prior to plotting
            (required for QuadMesh if unsorted coordinates are provided)

            The default is True.
        indicate_masked_points : bool or dict
            If False, masked points are not indicated.

            If True, any datapoints that could not be properly plotted
            with the currently assigned shape are indicated with a
            circle with a red boundary.

            If a dict is provided, it can be used to update the appearance of the
            masked points (arguments are passed to matplotlibs `plt.scatter()`)
            ('s': markersize, 'marker': the shape of the marker, ...)

            The default is False

        Other Parameters
        ----------------
        vmin, vmax : float, optional
            Min- and max. values assigned to the colorbar. The default is None.
        zorder : float
            The zorder of the artist (e.g. the stacking level of overlapping artists)
            The default is 1
        kwargs
            kwargs passed to the initialization of the matplotlib collection
            (dependent on the plot-shape) [linewidth, edgecolor, facecolor, ...]

            For "shade_points" or "shade_raster" shapes, kwargs are passed to
            `datashader.mpl_ext.dsshow`

        """
        verbose = kwargs.pop("verbose", None)
        if verbose is not None:
            _log.error("EOmaps: The parameter verbose is ignored.")

        # make sure zorder is set to 1 by default
        # (by default shading would use 0 while ordinary collections use 1)
        if self.shape.name != "contour":
            kwargs.setdefault("zorder", 1)
        else:
            # put contour lines by default at level 10
            if self.shape._filled:
                kwargs.setdefault("zorder", 1)
            else:
                kwargs.setdefault("zorder", 10)

        if getattr(self, "coll", None) is not None and len(self.cb.pick.get.cbs) > 0:
            _log.info(
                "EOmaps: Calling `m.plot_map()` or "
                "`m.make_dataset_pickable()` more than once on the "
                "same Maps-object overrides the assigned PICK-dataset!"
            )

        if layer is None:
            layer = self.layer
        else:
            if not isinstance(layer, str):
                _log.info("EOmaps: The layer-name has been converted to a string!")
                layer = str(layer)

        useshape = self.shape  # invoke the setter to set the default shape
        shade_q = useshape.name.startswith("shade_")  # indicator if shading is used

        # make sure the colormap is properly set and transparencies are assigned
        cmap = kwargs.pop("cmap", "viridis")

        if "alpha" in kwargs and kwargs["alpha"] < 1:
            # get a unique name for the colormap
            cmapname = self._get_alpha_cmap_name(kwargs["alpha"])

            cmap = cmap_alpha(
                cmap=cmap,
                alpha=kwargs["alpha"],
                name=cmapname,
            )

            plt.colormaps.register(name=cmapname, cmap=cmap)
            self._emit_signal("cmapsChanged")
            # remember registered colormaps (to de-register on close)
            self._registered_cmaps.append(cmapname)

        # ---------------------- prepare the data

        _log.debug("EOmaps: Preparing dataset")

        # ---------------------- assign the data to the data_manager

        # shade shapes use datashader to update the data of the collections!
        update_coll_on_fetch = False if shade_q else True

        self._data_manager.set_props(
            layer=layer,
            assume_sorted=assume_sorted,
            update_coll_on_fetch=update_coll_on_fetch,
            indicate_masked_points=indicate_masked_points,
            dynamic=dynamic,
        )

        # ---------------------- classify the data
        self._set_vmin_vmax(
            vmin=kwargs.pop("vmin", None), vmax=kwargs.pop("vmax", None)
        )

        if not self._inherit_classification:
            if self._classify_specs.scheme is not None:
                _log.debug("EOmaps: Classifying...")
            elif self.shape.name == "contour" and kwargs.get("levels", None) is None:
                # TODO use custom contour-levels as UserDefined classification?
                self.set_classify.EqualInterval(k=5)

        cbcmap, norm, bins, classified = self._classify_data(
            vmin=self._vmin,
            vmax=self._vmax,
            cmap=cmap,
            classify_specs=self._classify_specs,
        )

        if norm is not None:
            if "norm" in kwargs:
                raise TypeError(
                    "EOmaps: You cannot provide an explicit norm for the dataset if a "
                    "classification scheme is used!"
                )
        else:
            if "norm" in kwargs:
                norm = kwargs.pop("norm")
                if not isinstance(norm, str):  # to allow datashader "eq_hist" norm
                    norm.vmin = self._vmin
                    norm.vmax = self._vmax
            else:
                norm = plt.Normalize(vmin=self._vmin, vmax=self._vmax)

        # todo remove duplicate attributes
        self._classify_specs._cbcmap = cbcmap
        self._classify_specs._norm = norm
        self._classify_specs._bins = bins
        self._classify_specs._classified = classified

        self._cbcmap = cbcmap
        self._norm = norm
        self._bins = bins
        self._classified = classified

        # ---------------------- plot the data

        if shade_q:
            self._shade_map(
                layer=layer,
                dynamic=dynamic,
                set_extent=set_extent,
                assume_sorted=assume_sorted,
                **kwargs,
            )
            self.f.canvas.draw_idle()
        else:
            # dont set extent if "m.set_extent" was called explicitly
            if set_extent and self._set_extent_on_plot:
                # note bg-layers are automatically triggered for re-draw
                # if the extent changes!
                self._data_manager._set_lims()

            self._plot_map(
                layer=layer,
                dynamic=dynamic,
                set_extent=set_extent,
                assume_sorted=assume_sorted,
                **kwargs,
            )

            self.BM._refetch_layer(layer)

        if getattr(self, "_data_mask", None) is not None and not np.all(
            self._data_mask
        ):
            _log.info("EOmaps: Some datapoints could not be drawn!")

        self._data_plotted = True

        self._emit_signal("dataPlotted")

        self.BM.update()

    @wraps(ColorBar._new_colorbar)
    def add_colorbar(self, *args, **kwargs):
        """Add a colorbar to the map."""
        if self.coll is None:
            raise AttributeError(
                "EOmaps: You must plot a dataset before " "adding a colorbar!"
            )
        colorbar = ColorBar._new_colorbar(self, *args, **kwargs)

        self._colorbars.append(colorbar)
        self.BM._refetch_layer(self.layer)
        self.BM._refetch_layer("__SPINES__")

        return colorbar

    def make_dataset_pickable(
        self,
    ):
        """
        Make the associated dataset pickable **without plotting** it first.

        After executing this function, `m.cb.pick` callbacks can be attached to the
        `Maps` object.

        NOTE
        ----
        This function is ONLY necessary if you want to use pick-callbacks **without**
        actually plotting the data**! Otherwise a call to `m.plot_map()` is sufficient!

        - Each `Maps` object can always have only one pickable dataset.
        - The used data is always the dataset that was assigned in the last call to
          `m.plot_map()` or `m.make_dataset_pickable()`.
        - To get multiple pickable datasets, use an individual layer for each of the
          datasets (e.g. first `m2 = m.new_layer()` and then assign the data to `m2`)

        Examples
        --------
        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>> ...
        >>> # a dataset that should be pickable but NOT visible...
        >>> m2 = m.new_layer()
            >>> m2.set_data(*np.linspace([0, -180,-90,], [100, 180, 90], 100).T)
        >>> m2.make_dataset_pickable()
        >>> m2.cb.pick.attach.annotate()  # get an annotation for the invisible dataset
        >>> # ...call m2.plot_map() to make the dataset visible...
        """
        if self.coll is not None:
            _log.error(
                "EOmaps: There is already a dataset plotted on this Maps-object. "
                "You MUST use a new layer (`m2 = m.new_layer()`) to use "
                "`m2.make_dataset_pickable()`!"
            )
            return

        # ---------------------- prepare the data
        self._data_manager = DataManager(self._proxy(self))
        self._data_manager.set_props(layer=self.layer, only_pick=True)

        x0, x1 = self._data_manager.x0.min(), self._data_manager.x0.max()
        y0, y1 = self._data_manager.y0.min(), self._data_manager.y0.max()

        # use a transparent rectangle of the data-extent as artist for picking
        (art,) = self.ax.fill([x0, x1, x1, x0], [y0, y0, y1, y1], fc="none", ec="none")

        self._coll = art

        self.tree = SearchTree(m=self._proxy(self))
        self.cb.pick._set_artist(art)
        self.cb.pick._init_cbs()
        self.cb._methods.add("pick")

        self._coll_kwargs = dict()
        self._coll_dynamic = True

        # set _data_plotted to True to trigger updates in the data-manager
        self._data_plotted = True

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

            for m in (self.parent, *self.parent._children):
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

    def _plot_map(
        self,
        layer=None,
        dynamic=False,
        set_extent=True,
        assume_sorted=True,
        **kwargs,
    ):
        _log.info(
            "EOmaps: Plotting "
            f"{self._data_manager.z_data.size} datapoints ({self.shape.name})"
        )

        for key in ("array",):
            assert (
                key not in kwargs
            ), f"The key '{key}' is assigned internally by EOmaps!"

        try:
            self._set_extent = set_extent

            # ------------- plot the data
            self._coll_kwargs = kwargs
            self._coll_dynamic = dynamic

            # NOTE: the actual plot is performed by the data-manager
            # at the next call to m.BM.fetch_bg() for the corresponding layer
            # this is called to make sure m.coll is properly set
            self._data_manager.on_fetch_bg(check_redraw=False)

        except Exception as ex:
            raise ex

    def _shade_map(
        self,
        layer=None,
        dynamic=False,
        set_extent=True,
        assume_sorted=True,
        **kwargs,
    ):
        """
        Plot the dataset using the (very fast) "datashader" library.

        Requires `datashader`... use `conda install -c conda-forge datashader`

        - This method is intended for extremely large datasets
          (up to millions of datapoints)!

        A dynamically updated "shaded" map will be generated.
        Note that the datapoints in this case are NOT represented by the shapes
        defined as `m.set_shape`!

        - By default, the shading is performed using a "mean"-value aggregation hook

        kwargs :
            kwargs passed to `datashader.mpl_ext.dsshow`

        """
        _log.info(
            "EOmaps: Plotting "
            f"{self._data_manager.z_data.size} datapoints ({self.shape.name})"
        )

        ds, mpl_ext, pd, xar = register_modules(
            "datashader", "datashader.mpl_ext", "pandas", "xarray"
        )

        # remove previously fetched backgrounds for the used layer
        if dynamic is False:
            self.BM._refetch_layer(layer)

        # in case the aggregation does not represent data-values
        # (e.g. count, std, var ... ) use an automatic "linear" normalization

        # get the name of the used aggretation reduction
        aggname = self.shape.aggregator.__class__.__name__

        if aggname in ["first", "last", "max", "min", "mean", "mode"]:
            kwargs.setdefault("norm", self._classify_specs._norm)
        else:
            kwargs.setdefault("norm", "linear")

        zdata = self._data_manager.z_data
        if len(zdata) == 0:
            _log.error("EOmaps: there was no data to plot")
            return

        plot_width, plot_height = self._get_shade_axis_size()

        # get rid of unnecessary dimensions in the numpy arrays
        zdata = zdata.squeeze()
        x0 = self._data_manager.x0.squeeze()
        y0 = self._data_manager.y0.squeeze()

        # the shape is always set after _prepare data!
        if self.shape.name == "shade_points" and self._data_manager.x0_1D is None:
            # fill masked-values with None to avoid issues with numba not being
            # able to deal with numpy-arrays
            # TODO report this to datashader to get it fixed properly?
            if isinstance(zdata, np.ma.masked_array):
                zdata = zdata.filled(None)

            df = pd.DataFrame(
                dict(
                    x=x0.ravel(),
                    y=y0.ravel(),
                    val=zdata.ravel(),
                ),
                copy=False,
            )

        else:
            if len(zdata.shape) == 2:
                if (zdata.shape == x0.shape) and (zdata.shape == y0.shape):
                    # 2D coordinates and 2D raster

                    # use a curvilinear QuadMesh
                    if self.shape.name == "shade_raster":
                        self.shape.glyph = ds.glyphs.QuadMeshCurvilinear(
                            "x", "y", "val"
                        )

                    df = xar.Dataset(
                        data_vars=dict(val=(["xx", "yy"], zdata)),
                        # dims=["x", "y"],
                        coords=dict(
                            x=(["xx", "yy"], x0),
                            y=(["xx", "yy"], y0),
                        ),
                    )

                elif (
                    ((zdata.shape[1],) == x0.shape)
                    and ((zdata.shape[0],) == y0.shape)
                    and (x0.shape != y0.shape)
                ):
                    raise AssertionError(
                        "EOmaps: it seems like you need to transpose your data! \n"
                        + f"the dataset has a shape of {zdata.shape}, but the "
                        + f"coordinates suggest ({x0.shape}, {y0.shape})"
                    )
                elif (zdata.T.shape == x0.shape) and (zdata.T.shape == y0.shape):
                    raise AssertionError(
                        "EOmaps: it seems like you need to transpose your data! \n"
                        + f"the dataset has a shape of {zdata.shape}, but the "
                        + f"coordinates suggest {x0.shape}"
                    )

                elif ((zdata.shape[0],) == x0.shape) and (
                    (zdata.shape[1],) == y0.shape
                ):
                    # 1D coordinates and 2D data

                    # use a rectangular QuadMesh
                    if self.shape.name == "shade_raster":
                        self.shape.glyph = ds.glyphs.QuadMeshRectilinear(
                            "x", "y", "val"
                        )

                    df = xar.DataArray(
                        data=zdata,
                        dims=["x", "y"],
                        coords=dict(x=x0, y=y0),
                    )
                    df = xar.Dataset(dict(val=df))
            else:
                try:
                    # try if reprojected coordinates can be used as 2d grid and if yes,
                    # directly use a curvilinear QuadMesh based on the reprojected
                    # coordinates to display the data
                    idx = pd.MultiIndex.from_arrays(
                        [x0.ravel(), y0.ravel()], names=["x", "y"]
                    )

                    df = pd.DataFrame(
                        data=dict(val=zdata.ravel()), index=idx, copy=False
                    )
                    df = df.to_xarray()
                    xg, yg = np.meshgrid(df.x, df.y)
                except Exception:
                    # first convert original coordinates of the 1D inputs to 2D,
                    # then reproject the grid and use a curvilinear QuadMesh to display
                    # the data
                    _log.warning(
                        "EOmaps: 1D data is converted to 2D prior to reprojection... "
                        "Consider using 'shade_points' as plot-shape instead!"
                    )
                    xorig = self._data_manager.xorig.ravel()
                    yorig = self._data_manager.yorig.ravel()

                    idx = pd.MultiIndex.from_arrays([xorig, yorig], names=["x", "y"])

                    df = pd.DataFrame(
                        data=dict(val=zdata.ravel()), index=idx, copy=False
                    )
                    df = df.to_xarray()
                    xg, yg = np.meshgrid(df.x, df.y)

                    # transform the grid from input-coordinates to the plot-coordinates
                    crs1 = CRS.from_user_input(self.data_specs.crs)
                    crs2 = CRS.from_user_input(self._crs_plot)
                    if crs1 != crs2:
                        transformer = self._get_transformer(
                            crs1,
                            crs2,
                        )
                        xg, yg = transformer.transform(xg, yg)

                # use a curvilinear QuadMesh
                if self.shape.name == "shade_raster":
                    self.shape.glyph = ds.glyphs.QuadMeshCurvilinear("x", "y", "val")

                df = xar.Dataset(
                    data_vars=dict(val=(["xx", "yy"], df.val.values.T)),
                    coords=dict(x=(["xx", "yy"], xg), y=(["xx", "yy"], yg)),
                )

            if self.shape.name == "shade_points":
                df = df.to_dataframe().reset_index()

        if set_extent is True and self._set_extent_on_plot is True:
            # convert to a numpy-array to support 2D indexing with boolean arrays
            x, y = np.asarray(df.x), np.asarray(df.y)
            xf, yf = np.isfinite(x), np.isfinite(y)
            x_range = (np.nanmin(x[xf]), np.nanmax(x[xf]))
            y_range = (np.nanmin(y[yf]), np.nanmax(y[yf]))
        else:
            # update here to ensure bounds are set
            self.BM.update()
            x0, x1, y0, y1 = self.get_extent(self.crs_plot)
            x_range = (x0, x1)
            y_range = (y0, y1)

        coll = mpl_ext.dsshow(
            df,
            glyph=self.shape.glyph,
            aggregator=self.shape.aggregator,
            shade_hook=self.shape.shade_hook,
            agg_hook=self.shape.agg_hook,
            # norm="eq_hist",
            # norm=plt.Normalize(vmin, vmax),
            cmap=self._cbcmap,
            ax=self.ax,
            plot_width=plot_width,
            plot_height=plot_height,
            # x_range=(x0, x1),
            # y_range=(y0, y1),
            # x_range=(df.x.min(), df.x.max()),
            # y_range=(df.y.min(), df.y.max()),
            x_range=x_range,
            y_range=y_range,
            vmin=self._vmin,
            vmax=self._vmax,
            **kwargs,
        )

        coll.set_label("Dataset " f"({self.shape.name}  |  {zdata.shape})")

        self._coll = coll

        if dynamic is True:
            self.BM.add_artist(coll, layer=layer)
        else:
            self.BM.add_bg_artist(coll, layer=layer)

        if dynamic is True:
            self.BM.update(clear=False)

    def _on_keypress(self, event):
        if plt.get_backend().lower() == "webagg":
            return

        # NOTE: callback is only attached to the parent Maps object!
        self._ClipboardMixin__on_keypress(event)
        self._CompanionMixin__on_keypress(event)

    @property
    def _shape_assigned(self):
        """Return True if the shape is explicitly assigned and False otherwise"""
        # the shape is considered assigned if an explicit shape is set
        # or if the data has been plotted with the default shape

        q = self._shape is None or (
            getattr(self._shape, "_is_default", False) and not self._data_plotted
        )

        return not q

    def _classify_data(
        self,
        z_data=None,
        cmap=None,
        vmin=None,
        vmax=None,
        classify_specs=None,
    ):

        if self._inherit_classification is not None:
            try:
                return (
                    self._inherit_classification._cbcmap,
                    self._inherit_classification._norm,
                    self._inherit_classification._bins,
                    self._inherit_classification._classified,
                )
            except AttributeError:
                raise AssertionError(
                    "EOmaps: A Maps object can only inherit the classification "
                    "if the parent Maps object called `m.plot_map()` first!!"
                )

        if z_data is None:
            z_data = self._data_manager.z_data

        if isinstance(cmap, str):
            cmap = plt.get_cmap(cmap).copy()
        else:
            cmap = cmap.copy()

        # evaluate classification
        if classify_specs is not None and classify_specs.scheme is not None:
            (mapclassify,) = register_modules("mapclassify")

            classified = True
            if self._classify_specs.scheme == "UserDefined":
                bins = self._classify_specs.bins
            else:
                # use "np.ma.compressed" to make sure values excluded via
                # masked-arrays are not used to evaluate classification levels
                # (normal arrays are passed through!)
                mapc = getattr(mapclassify, classify_specs.scheme)(
                    np.ma.compressed(z_data[~np.isnan(z_data)]), **classify_specs
                )
                bins = mapc.bins

            bins = np.unique(np.clip(bins, vmin, vmax))

            if vmin < min(bins):
                bins = [vmin, *bins]

            if vmax > max(bins):
                bins = [*bins, vmax]

            # TODO Always use resample once mpl>3.6 is pinned
            if hasattr(cmap, "resampled") and len(bins) > cmap.N:
                # Resample colormap to contain enough color-values
                # as needed by the boundary-norm.
                cbcmap = cmap.resampled(len(bins))
            else:
                cbcmap = cmap

            norm = mpl.colors.BoundaryNorm(bins, cbcmap.N)

            self._emit_signal("cmapsChanged")

            if cmap._rgba_bad:
                cbcmap.set_bad(cmap._rgba_bad)
            if cmap._rgba_over:
                cbcmap.set_over(cmap._rgba_over)
            if cmap._rgba_under:
                cbcmap.set_under(cmap._rgba_under)

        else:
            classified = False
            bins = None
            cbcmap = cmap
            norm = None

        return cbcmap, norm, bins, classified

    def _get_mcl_subclass(self, s):
        # get a subclass that inherits the docstring from the corresponding
        # mapclassify classifier

        class scheme:
            @wraps(s)
            def __init__(_, *args, **kwargs):
                pass

                if "y" in kwargs:
                    _log.error(
                        "EOmaps: The values (e.g. the 'y' parameter) are "
                        + "assigned internally... only provide additional "
                        + "parameters that specify the classification scheme!"
                    )
                    kwargs.pop("y")

                self._classify_specs._set_scheme_and_args(scheme=s.__name__, **kwargs)

        scheme.__doc__ = s.__doc__
        return scheme

    def _set_default_shape(self):
        if self.data is not None:
            # size = np.size(self.data)
            size = np.size(self._data_manager.z_data)
            shape = np.shape(self._data_manager.z_data)

            if len(shape) == 2 and size > 200_000:
                self.set_shape.raster()
            else:
                if size > 500_000:
                    if all(
                        register_modules(
                            "datashader", "datashader.mpl_ext", raise_exception=False
                        )
                    ):
                        # shade_points should work for any dataset
                        self.set_shape.shade_points()
                    else:
                        _log.warning(
                            "EOmaps: Attempting to plot a large dataset "
                            f"({size} datapoints) but the 'datashader' library "
                            "could not be imported! The plot might take long "
                            "to finish! ... defaulting to 'ellipses' "
                            "as plot-shape."
                        )
                        self.set_shape.ellipses()
                else:
                    self.set_shape.ellipses()
        else:
            self.set_shape.ellipses()

    def _find_ID(self, ID):
        # explicitly treat range-like indices (for very large datasets)
        ids = self._data_manager.ids
        if isinstance(ids, range):
            ind, mask = [], []
            for i in np.atleast_1d(ID):
                if i in ids:

                    found = ids.index(i)
                    ind.append(found)
                    mask.append(found)
                else:
                    ind.append(None)

        elif isinstance(ids, (list, np.ndarray)):
            mask = np.isin(ids, ID)
            ind = np.where(mask)[0]

        return mask, ind

    def _get_alpha_cmap_name(self, alpha):
        # get a unique name for the colormap
        try:
            ncmaps = max(
                [
                    int(i.rsplit("_", 1)[1])
                    for i in plt.colormaps()
                    if i.startswith("EOmaps_alpha_")
                ]
            )
        except Exception:
            ncmaps = 0

        return f"EOmaps_alpha_{ncmaps + 1}"

    def _encode_values(self, val):
        """
        Encode values with respect to the provided  "scale_factor" and "add_offset".

        Encoding is performed via the formula:

            `encoded_value = val / scale_factor - add_offset`

        NOTE: the data-type is not altered!!
        (e.g. no integer-conversion is performed, only values are adjusted)

        Parameters
        ----------
        val : array-like
            The data-values to encode

        Returns
        -------
        encoded_values
            The encoded data values
        """
        encoding = self.data_specs.encoding

        if encoding is not None and encoding is not False:
            try:
                scale_factor = encoding.get("scale_factor", None)
                add_offset = encoding.get("add_offset", None)
                fill_value = encoding.get("_FillValue", None)

                if val is None:
                    return fill_value

                if add_offset:
                    val = val - add_offset
                if scale_factor:
                    val = val / scale_factor

                return val
            except Exception:
                _log.exception(f"EOmaps: Error while trying to encode the data: {val}")
                return val
        else:
            return val

    def _decode_values(self, val):
        """
        Decode data-values with respect to the provided "scale_factor" and "add_offset".

        Decoding is performed via the formula:

            `actual_value = add_offset + scale_factor * val`

        The encoding is defined in `m.data_specs.encoding`

        Parameters
        ----------
        val : array-like
            The encoded data-values

        Returns
        -------
        decoded_values
            The decoded data values
        """
        if val is None:
            return None

        encoding = self.data_specs.encoding
        if not any(encoding is i for i in (None, False)):
            try:
                scale_factor = encoding.get("scale_factor", None)
                add_offset = encoding.get("add_offset", None)

                if scale_factor:
                    val = val * scale_factor
                if add_offset:
                    val = val + add_offset

                return val
            except Exception:
                _log.exception(f"EOmaps: Error while trying to decode the data {val}.")
                return val
        else:
            return val

    def _calc_vmin_vmax(self, vmin=None, vmax=None):
        if self.data is None:
            return vmin, vmax

        calc_min, calc_max = vmin is None, vmax is None

        # ignore fill_values when evaluating vmin/vmax on integer-encoded datasets
        if (
            self.data_specs.encoding is not None
            and isinstance(self._data_manager.z_data, np.ndarray)
            and issubclass(self._data_manager.z_data.dtype.type, np.integer)
        ):

            # note the specific way how to check for integer-dtype based on issubclass
            # since isinstance() fails to identify all integer dtypes!!
            #   isinstance(np.dtype("uint8"), np.integer)       (incorrect) False
            #   issubclass(np.dtype("uint8").type, np.integer)  (correct)   True
            # for details, see https://stackoverflow.com/a/934652/9703451

            fill_value = self.data_specs.encoding.get("_FillValue", None)
            if fill_value and any([calc_min, calc_max]):
                # find values that are not fill-values
                use_vals = self._data_manager.z_data[
                    self._data_manager.z_data != fill_value
                ]

                if calc_min:
                    vmin = np.min(use_vals)
                if calc_max:
                    vmax = np.max(use_vals)

                return vmin, vmax

        # use nanmin/nanmax for all other arrays
        if calc_min:
            vmin = np.nanmin(self._data_manager.z_data)
        if calc_max:
            vmax = np.nanmax(self._data_manager.z_data)

        return vmin, vmax

    def _set_vmin_vmax(self, vmin=None, vmax=None):
        # don't encode nan-vailes to avoid setting the fill-value as vmin/vmax
        if vmin is not None:
            vmin = self._encode_values(vmin)
        if vmax is not None:
            vmax = self._encode_values(vmax)

        # handle inherited bounds
        if self._inherit_classification is not None:
            if not (vmin is None and vmax is None):
                raise TypeError(
                    "EOmaps: 'vmin' and 'vmax' cannot be set explicitly "
                    "if the classification is inherited!"
                )

            # in case data is NOT inherited, warn if vmin/vmax is None
            # (different limits might cause a different appearance of the data!)
            if self.data_specs._m == self:
                if self._vmin is None:
                    _log.warning("EOmaps: Inherited value for 'vmin' is None!")
                if self._vmax is None:
                    _log.warning(
                        "EOmaps: Inherited inherited value for 'vmax' is None!"
                    )

            self._vmin = self._inherit_classification._vmin
            self._vmax = self._inherit_classification._vmax
            return

        if not self.shape.name.startswith("shade_"):
            # ignore fill_values when evaluating vmin/vmax on integer-encoded datasets
            self._vmin, self._vmax = self._calc_vmin_vmax(vmin=vmin, vmax=vmax)
        else:
            # get the name of the used aggretation reduction
            aggname = self.shape.aggregator.__class__.__name__
            if aggname in ["first", "last", "max", "min", "mean", "mode"]:
                # set vmin/vmax in case the aggregation still represents data-values
                self._vmin, self._vmax = self._calc_vmin_vmax(vmin=vmin, vmax=vmax)
            else:
                # set vmin/vmax for aggregations that do NOT represent data values
                # allow vmin/vmax = None (e.g. autoscaling)
                self._vmin, self._vmax = vmin, vmax
                if "count" in aggname:
                    # if the reduction represents a count, don't count empty pixels
                    if vmin and vmin <= 0:
                        _log.warning(
                            "EOmaps: setting vmin=1 to avoid counting empty pixels..."
                        )
                        self._vmin = 1

    def _get_shade_axis_size(self, dpi=None, flush=True):
        if flush:
            # flush events before evaluating shade sizes to make sure axes dimensions have
            # been properly updated
            self.f.canvas.flush_events()

        if self._shade_dpi is not None:
            dpi = self._shade_dpi

        fig_dpi = self.f.dpi
        w, h = self.ax.bbox.width, self.ax.bbox.height

        # TODO for now, only handle numeric dpi-values to avoid issues.
        # (savefig also seems to support strings like "figure" etc.)
        if isinstance(dpi, (int, float, np.number)):
            width = int(w / fig_dpi * dpi)
            height = int(h / fig_dpi * dpi)
        else:
            width = int(w)
            height = int(h)

        return width, height

    def _update_shade_axis_size(self, dpi=None, flush=True):
        # method to update all shade-dpis
        # NOTE: provided dpi value is only used if no explicit "_shade_dpi" is set!

        # set the axis-size that is used to determine the number of pixels used
        # when using "shade" shapes for ALL maps objects of a figure
        for m in (self.parent, *self.parent._children):
            if m.coll is not None and m.shape.name.startswith("shade_"):
                w, h = m._get_shade_axis_size(dpi=dpi, flush=flush)
                m.coll.plot_width = w
                m.coll.plot_height = h

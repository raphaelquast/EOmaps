# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""General definition of Maps objects."""

import logging

_log = logging.getLogger(__name__)

from contextlib import ExitStack, contextmanager
from functools import lru_cache, wraps
from itertools import repeat, chain
from pathlib import Path
from types import SimpleNamespace
from textwrap import fill
from difflib import get_close_matches

import copy
import importlib.metadata
import weakref

import numpy as np
from pyproj import CRS

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.path as mpath

from cartopy import crs as ccrs

from ._maps_base import MapsBase
from .helpers import (
    pairwise,
    cmap_alpha,
    progressbar,
    SearchTree,
    _TransformedBoundsLocator,
    register_modules,
    _key_release_event,
    _add_to_docstring,
)

from .shapes import Shapes
from .colorbar import ColorBar
from ._containers import DataSpecs, ClassifySpecs
from .ne_features import NaturalEarthFeatures
from .cb_container import CallbackContainer, GeoDataFramePicker
from .scalebar import ScaleBar
from .compass import Compass
from .reader import read_file, from_file, new_layer_from_file
from .grid import GridFactory
from .utilities import Utilities
from .draw import ShapeDrawer
from .annotation_editor import AnnotationEditor
from ._data_manager import DataManager

try:
    from ._webmap import refetch_wms_on_size_change, _cx_refetch_wms_on_size_change
    from .webmap_containers import WebMapContainer
except ImportError as ex:
    _log.error(f"EOmaps: Unable to import dependencies required for WebMaps: {ex}")
    refetch_wms_on_size_change = None
    _cx_refetch_wms_on_size_change = None
    WebMapContainer = None

__version__ = importlib.metadata.version("eomaps")

# hardcoded list of available mapclassify-classifiers
# (to avoid importing it on startup)
_CLASSIFIERS = (
    "BoxPlot",
    "EqualInterval",
    "FisherJenks",
    "FisherJenksSampled",
    "HeadTailBreaks",
    "JenksCaspall",
    "JenksCaspallForced",
    "JenksCaspallSampled",
    "MaxP",
    "MaximumBreaks",
    "NaturalBreaks",
    "Quantiles",
    "Percentiles",
    "StdMean",
    "UserDefined",
)


class Maps(MapsBase):
    """
    The base-class for generating plots with EOmaps.

    The first Maps object that is initialized will create a new matplotlib `Figure`
    and a cartopy `GeoAxes` for a map.

    You can then create additional `Maps` objects on the same figure with the following
    methods:


    See Also
    --------
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
    >>> m1 = m.new_layer("layer 1")
    >>> m1.add_feature.physical.coastline(fc="none", ec="b", lw=2, scale=50)
    >>> m1.add_feature.cultural.admin_0_countries(fc=(.2,.1,.4,.2), ec="b", lw=1, scale=50)
    >>> # overlay a part of the new layer in a circle if you click on the map
    >>> m.cb.click.attach.peek_layer(m1.layer, how=0.4, shape="round")

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

    # the keyboard shortcut to activate the companion-widget
    _companion_widget_key = "w"
    # max. number of layers to show all layers as tabs in the widget
    # (otherwise only recently active layers are shown as tabs)
    _companion_widget_n_layer_tabs = 50

    CLASSIFIERS = SimpleNamespace(**dict(zip(_CLASSIFIERS, _CLASSIFIERS)))
    "Accessor for available classification schemes."

    # arguments passed to m.savefig when using "ctrl+c" to export figure to clipboard
    _clipboard_kwargs = dict()

    # to make namespace accessible for sphinx
    set_shape = Shapes
    draw = ShapeDrawer
    add_feature = NaturalEarthFeatures
    util = Utilities
    cb = CallbackContainer

    classify_specs = ClassifySpecs
    data_specs = DataSpecs

    if WebMapContainer is not None:
        add_wms = WebMapContainer

    def __init__(
        self,
        crs=None,
        layer="base",
        f=None,
        ax=None,
        preferred_wms_service="wms",
        **kwargs,
    ):
        super().__init__(
            crs=crs,
            layer=layer,
            f=f,
            ax=ax,
            **kwargs,
        )

        self._log_on_event_messages = dict()
        self._log_on_event_cids = dict()

        try:
            from .qtcompanion.signal_container import _SignalContainer

            # initialize the signal container (MUST be done before init of the widget!)
            self._signal_container = _SignalContainer()
        except Exception:
            _log.debug("SignalContainer could not be initialized", exc_info=True)
            self._signal_container = None

        self._inherit_classification = None

        self._util = None

        self._colorbars = []
        self._coll = None  # slot for the collection created by m.plot_map()

        self._companion_widget = None  # slot for the pyqt widget

        self._cid_keypress = None  # callback id for PyQt5 keypress callbacks
        # attach a callback to show/hide the companion-widget with the "w" key
        if self.parent._cid_keypress is None:
            # NOTE the companion-widget is ONLY attached to the parent map
            # since it will identify the clicked map automatically! The
            # widget will only be initialized on Maps-objects that create
            # NEW axes. This is required to make sure that any additional
            # Maps-object on the same axes will then always use the
            # same widget. (otherwise each layer would get its own widget)

            self.parent._cid_keypress = self.f.canvas.mpl_connect(
                "key_press_event", self.parent._on_keypress
            )

        # a list to remember newly registered colormaps
        self._registered_cmaps = []

        # a list of actions that are executed whenever the widget is shown
        self._on_show_companion_widget = []

        # preferred way of accessing WMS services (used in the WMS container)
        assert preferred_wms_service in [
            "wms",
            "wmts",
        ], "preferred_wms_service must be either 'wms' or 'wmts' !"
        self._preferred_wms_service = preferred_wms_service

        # default classify specs
        self.classify_specs = ClassifySpecs(weakref.proxy(self))

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

        if WebMapContainer is not None:
            self.add_wms = self.add_wms(weakref.proxy(self))

        self.new_layer_from_file = new_layer_from_file(weakref.proxy(self))

        self.set_shape = self.set_shape(weakref.proxy(self))
        self._shape = None
        # the dpi used for shade shapes
        self._shade_dpi = None

        # the radius is estimated when plot_map is called
        self._estimated_radius = None

        # a set to hold references to the compass objects
        self._compass = set()

        if not hasattr(self.parent, "_wms_legend"):
            self.parent._wms_legend = dict()

        if not hasattr(self.parent, "_execute_callbacks"):
            self.parent._execute_callbacks = True

        # evaluate and cache crs boundary bounds (for extent clipping)
        self._crs_boundary_bounds = self.crs_plot.boundary.bounds

        # a factory to create gridlines
        if self.parent == self:
            self._grid = GridFactory(self.parent)

            if Maps._always_on_top:
                self._set_always_on_top(True)

        self.add_feature = self.add_feature(weakref.proxy(self))
        self.draw = self.draw(weakref.proxy(self))

        if self.parent == self:
            self.util = Utilities(self)
        else:
            self.util = self.parent.util

    @contextmanager
    def delay_draw(self):
        """
        A contextmanager to delay drawing until the context exits.

        This is particularly useful to avoid intermediate draw-events when plotting
        a lot of features or datasets on the currently visible layer.


        Examples
        --------

        >>> m = Maps()
        >>> with m.delay_draw():
        >>>     m.add_feature.preset.coastline()
        >>>     m.add_feature.preset.ocean()
        >>>     m.add_feature.preset.land()

        """
        try:
            self.BM._disable_draw = True
            self.BM._disable_update = True

            yield
        finally:
            self.BM._disable_draw = False
            self.BM._disable_update = False
            self.redraw()

    @property
    def coll(self):
        """The collection representing the dataset plotted by m.plot_map()."""
        return self._coll

    @property
    def _shape_assigned(self):
        """Return True if the shape is explicitly assigned and False otherwise"""
        # the shape is considered assigned if an explicit shape is set
        # or if the data has been plotted with the default shape

        q = self._shape is None or (
            getattr(self._shape, "_is_default", False) and not self._data_plotted
        )

        return not q

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

    @lru_cache()
    def get_crs(self, crs="plot"):
        """
        Get the pyproj CRS instance of a given crs specification.

        Parameters
        ----------
        crs : "in", "out" or a crs definition
            the crs to return

            - if "in" : the crs defined in m.data_specs.crs
            - if "out" or "plot" : the crs used for plotting

        Returns
        -------
        crs : pyproj.CRS
            the pyproj CRS instance

        """
        # check for strings first to avoid expensive equality checking for CRS objects!
        if isinstance(crs, str):
            if crs == "in":
                crs = self.data_specs.crs
            elif crs == "out" or crs == "plot":
                crs = self.crs_plot

        crs = CRS.from_user_input(crs)
        return crs

    @property
    def _edit_annotations(self):
        if getattr(self.parent, "_edit_annotations_parent", None) is None:
            self.parent._edit_annotations_parent = AnnotationEditor(self.parent)
        return self.parent._edit_annotations_parent

    @wraps(AnnotationEditor.__call__)
    def edit_annotations(self, b=True, **kwargs):
        self._edit_annotations(b, **kwargs)

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
        layer : int, str or None
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
        depreciated_names = [
            ("copy_data_specs", "inherit_data"),
            ("copy_classify_specs", "inherit_classification"),
            ("copy_shape", "inherit_shape"),
        ]

        for old, new in depreciated_names:
            if old in kwargs:
                from warnings import warn

                warn(
                    f"EOmaps: Using '{old}' is depreciated! Use '{new}' instead! "
                    "NOTE: Datasets are now inherited (e.g. shared) and not copied. "
                    "To explicitly copy attributes, see m.copy(...)!",
                    category=FutureWarning,
                    stacklevel=2,
                )

        inherit_data = kwargs.get("copy_data_specs", inherit_data)
        inherit_classification = kwargs.get(
            "copy_classify_specs", inherit_classification
        )
        inherit_shape = kwargs.get("copy_shape", inherit_shape)

        if layer is None:
            layer = copy.deepcopy(self.layer)
        else:
            layer = str(layer)
            if len(layer) == 0:
                raise SyntaxError(
                    "EOmaps: Unable to create a layer with an empty layer-name!"
                )

        m = self.copy(
            data_specs=False,
            classify_specs=False,
            shape=False,
            ax=self.ax,
            layer=layer,
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
        `m.classify_specs.SCHEMES`

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
            (the list is accessible via `m.classify_specs.SCHEMES`)

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
        self.classify_specs._set_scheme_and_args(scheme, **kwargs)

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

    def set_extent_to_location(self, location, annotate=False, user_agent=None):
        """
        Set the map-extent based on a given location query.

        The bounding-box is hereby resolved via the OpenStreetMap Nominatim service.

        Note
        ----
        The OSM Nominatim service has a strict usage policy that explicitly
        disallows "heavy usage" (e.g.: an absolute maximum of 1 request per second).

        EOMaps caches requests so using a location multiple times in the same
        session does not cause multiple requests!

        For more details, see:
            https://operations.osmfoundation.org/policies/nominatim/
            https://openstreetmap.org/copyright

        Parameters
        ----------
        location : str
            An arbitrary string used to identify the region of interest.
            (e.g. a country, district, address etc.)

            For example:
                "Austria", "Vienna"

        annotate : bool, optional
            Indicator if an annotation should be added to the center of the identified
            location or not. The default is False.
        user_agent: str, optional
            The user-agent used for the Nominatim request

        Examples
        --------
        >>> m = Maps()
        >>> m.set_extent_to_location("Austria")
        >>> m.add_feature.preset.countries()

        >>> m = Maps(Maps.CRS.GOOGLE_MERCATOR)
        >>> m.set_extent_to_location("Vienna")
        >>> m.add_wms.OpenStreetMap.add_layer.default()

        """
        r = self._get_nominatim_response(location)

        # get bbox of found location
        lon0, lon1, lat0, lat1 = map(float, r["boundingbox"])

        # set extent to found bbox
        self.set_extent((lat0, lat1, lon0, lon1), crs=Maps.CRS.PlateCarree())

        # add annotation
        if annotate is not False:
            if isinstance(annotate, str):
                text = annotate
            else:
                text = fill(r["display_name"], 20)

            self.add_annotation(
                xy=(r["lon"], r["lat"]), xy_crs=4326, text=text, fontsize=8
            )
        else:
            _log.info(f"Centering Map to:\n    {r['display_name']}")

    def _set_gdf_path_boundary(self, gdf, set_extent=True):
        geom = gdf.to_crs(self.crs_plot).unary_union
        if "Polygon" in geom.geom_type:
            geom = geom.boundary

        if geom.geom_type == "MultiLineString":
            boundary_linestrings = geom.geoms
        elif geom.geom_type == "LineString":
            boundary_linestrings = [geom]
        else:
            raise TypeError(
                f"Geometries of type {geom.type} cannot be used as map-boundary."
            )

        vertices, codes = [], []
        for g in boundary_linestrings:
            x, y = g.xy
            codes.extend(
                [mpath.Path.MOVETO, *[mpath.Path.LINETO] * len(x), mpath.Path.CLOSEPOLY]
            )
            vertices.extend([(x[0], y[0]), *zip(x, y), (x[-1], y[-1])])

        path = mpath.Path(vertices, codes)

        self.ax.set_boundary(path, self.ax.transData)
        if set_extent:
            x0, y0 = np.min(vertices, axis=0)
            x1, y1 = np.max(vertices, axis=0)

            self.set_extent([x0, x1, y0, y1], gdf.crs)

    def _set_country_frame(self, countries, scale=50):
        """
        Set the map-frame to one (or more) country boarders defined by
        the NaturalEarth admin_0_countries dataset.

        For more details, see:

            https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/

        Parameters
        ----------
        countries : str or list of str
            The countries who should be included in the map-frame.
        scale : int, optional
            The scale factor of the used NaturalEarth dataset.
            One of 10, 50, 110.
            The default is 50.

        """
        countries = [i.lower() for i in np.atleast_1d(countries)]
        gdf = self.add_feature.cultural.admin_0_countries.get_gdf(scale=scale)
        names = gdf.NAME.str.lower().values

        q = np.isin(names, countries)

        if np.count_nonzero(q) == len(countries):
            self.set_frame(gdf=gdf[q])
        else:
            for c in countries:
                if c not in names:
                    print(
                        f"Unable to identify the country '{c}'. "
                        f"Fid you mean {get_close_matches(c, gdf.NAME)}"
                    )

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

        for key in ("fc", "facecolor"):
            if key in kwargs:
                self.ax.patch.set_facecolor(kwargs.pop(key))

        self.ax.spines["geo"].update(kwargs)

        if gdf is not None:
            assert (
                rounded == 0
            ), "EOmaps: using rounded > 0 is not supported for gdf frames!"
            assert countries is None, "You cannot specify both 'gdf' and 'countries'"

            self._set_gdf_path_boundary(
                self._handle_gdf(gdf), set_extent=kwargs.pop("set_extent", True)
            )
        elif countries is not None:
            assert (
                rounded == 0
            ), "EOmaps: using rounded > 0 is not supported for country-border frames!"
            assert gdf is None, "You cannot specify both 'gdf' and 'countries'"

            self._set_country_frame(countries, scale=kwargs.pop("scale", 50))

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

        self.redraw()

    @staticmethod
    def set_clipboard_kwargs(**kwargs):
        """
        Set GLOBAL savefig parameters for all Maps objects on export to the clipboard.

        - press "control + c" to export the figure to the clipboard

        All arguments are passed to :meth:`Maps.savefig`

        Useful options are

        - dpi : the dots-per-inch of the figure
        - refetch_wms: re-fetch webmaps with respect to the export-`dpi`
        - bbox_inches: use "tight" to export figure with a tight boundary
        - pad_inches: the size of the boundary if `bbox_inches="tight"`
        - transparent: if `True`, export with a transparent background
        - facecolor: the background color


        Parameters
        ----------
        kwargs :
            Keyword-arguments passed to :meth:`Maps.savefig`.

        Note
        ----
        This function sets the clipboard kwargs for all Maps-objects!

        Exporting to the clipboard only works if `PyQt5` is used as matplotlib backend!
        (the default if `PyQt` is installed)

        See Also
        --------
        Maps.savefig : Save the figure as jpeg, png, etc.

        """
        # use Maps to make sure InsetMaps do the same thing!
        Maps._set_clipboard_kwargs(**kwargs)
        # trigger companion-widget setter for all open figures that contain maps
        for i in plt.get_fignums():
            try:
                m = getattr(plt.figure(i), "_EOmaps_parent", None)
                if m is not None:
                    if m._companion_widget is not None:
                        m._emit_signal("clipboardKwargsChanged")
            except Exception:
                _log.exception("UPS")

    @staticmethod
    def _set_clipboard_kwargs(**kwargs):
        # use Maps to make sure InsetMaps do the same thing!
        Maps._clipboard_kwargs = kwargs

    def add_title(self, title, x=0.5, y=1.01, **kwargs):
        """
        Convenience function to add a title to the map.

        (The title will be visible at the assigned layer.)

        Parameters
        ----------
        title : str
            The title.
        x, y : float, optional
            The position of the text in axis-coordinates (0-1).
            The default is 0.5, 1.01.
        kwargs :
            Additional kwargs are passed to `m.text()`
            The defaults are:

            - `"fontsize": "large"`
            - `horizontalalignment="center"`
            - `verticalalignment="bottom"`

        See Also
        --------

        :py:meth:`Maps.text` : General function to add text to the figure.

        """
        kwargs.setdefault("fontsize", "large")
        kwargs.setdefault("horizontalalignment", "center")
        kwargs.setdefault("verticalalignment", "bottom")
        kwargs.setdefault("transform", self.ax.transAxes)

        self.text(x, y, title, layer=self.layer, **kwargs)

    def add_gdf(
        self,
        gdf,
        picker_name=None,
        pick_method="contains",
        val_key=None,
        layer=None,
        temporary_picker=None,
        clip=False,
        reproject="gpd",
        verbose=False,
        only_valid=False,
        set_extent=False,
        permanent=True,
        **kwargs,
    ):
        """
        Plot a `geopandas.GeoDataFrame` on the map.

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame, str or pathlib.Path
            A GeoDataFrame that should be added to the plot.

            If a string (or pathlib.Path) is provided, it is identified as the path to
            a file that should be read with `geopandas.read_file(gdf)`.

        picker_name : str or None
            A unique name that is used to identify the pick-method.

            If a `picker_name` is provided, a new pick-container will be
            created that can be used to pick geometries of the GeoDataFrame.

            The container can then be accessed via:
            >>> m.cb.pick__<picker_name>
            or
            >>> m.cb.pick[picker_name]
            and it can be used in the same way as `m.cb.pick...`

        pick_method : str or callable
            if str :
                The operation that is executed on the GeoDataFrame to identify
                the picked geometry.
                Possible values are:

                - "contains":
                  pick a geometry only if it contains the clicked point
                  (only works with polygons! (not with lines and points))
                - "centroids":
                  pick the closest geometry with respect to the centroids
                  (should work with any geometry whose centroid is defined)

                The default is "centroids"

            if callable :
                A callable that is used to identify the picked geometry.
                The call-signature is:

                >>> def picker(artist, mouseevent):
                >>>     # if the pick is NOT successful:
                >>>     return False, dict()
                >>>     ...
                >>>     # if the pick is successful:
                >>>     return True, dict(ID, pos, val, ind)

                The default is "contains"

        val_key : str
            The dataframe-column used to identify values for pick-callbacks.
            The default is the value provided via `column=...` or None.
        layer : int, str or None
            The name of the layer at which the dataset will be plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer assigned to the Maps-object is used (e.g. `m.layer`)

            The default is None.
        temporary_picker : str, optional
            The name of the picker that should be used to make the geometry
            temporary (e.g. remove it after each pick-event)
        clip : str or False
            This feature can help with re-projection issues for non-global crs.
            (see example below)

            Indicator if geometries should be clipped prior to plotting or not.

            - if "crs": clip with respect to the boundary-shape of the crs
            - if "crs_bounds" : clip with respect to a rectangular crs boundary
            - if "extent": clip with respect to the current extent of the plot-axis.
            - if the 'gdal' python-bindings are installed, you can use gdal to clip
              the shapes with respect to the crs-boundary. (slower but more robust)
              The following logical operations are supported:

              - "gdal_SymDifference" : symmetric difference
              - "gdal_Intersection" : intersection
              - "gdal_Difference" : difference
              - "gdal_Union" : union

            If a suffix "_invert" is added to the clip-string (e.g. "crs_invert"
            or "gdal_Intersection_invert") the obtained (clipped) polygons will be
            inverted.


            >>> mg = MapsGrid(2, 3, crs=3035)
            >>> mg.m_0_0.add_feature.preset.ocean(use_gpd=True)
            >>> mg.m_0_1.add_feature.preset.ocean(use_gpd=True, clip="crs")
            >>> mg.m_0_2.add_feature.preset.ocean(use_gpd=True, clip="extent")
            >>> mg.m_1_0.add_feature.preset.ocean(use_gpd=False)
            >>> mg.m_1_1.add_feature.preset.ocean(use_gpd=False, clip="crs")
            >>> mg.m_1_2.add_feature.preset.ocean(use_gpd=False, clip="extent")

        reproject : str, optional
            Similar to "clip" this feature mainly addresses issues in the way how
            re-projected geometries are displayed in certain coordinate-systems.
            (see example below)

            - if "gpd": re-project geometries geopandas
            - if "cartopy": re-project geometries with cartopy (slower but more robust)

            The default is "gpd".

            >>> mg = MapsGrid(2, 1, crs=Maps.CRS.Stereographic())
            >>> mg.m_0_0.add_feature.preset.ocean(reproject="gpd")
            >>> mg.m_1_0.add_feature.preset.ocean(reproject="cartopy")

        verbose : bool, optional
            Indicator if a progressbar should be printed when re-projecting
            geometries with "use_gpd=False". The default is False.
        only_valid : bool, optional
            - If True, only valid geometries (e.g. `gdf.is_valid`) are plotted.
            - If False, all geometries are attempted to be plotted
              (this might result in errors for infinite geometries etc.)

            The default is True
        set_extent: bool, optional
            - if True, set map extent to the extent of the geometries with +-5% margin.
            - if float, use the value as margin (0-1).

            The default is True.
        permanent : bool, optional
            If True, all created artists are added as "permanent" background
            artists. If  False, artists are added as dynamic artists.
            The default is True.
        kwargs :
            all remaining kwargs are passed to `geopandas.GeoDataFrame.plot(**kwargs)`

        Returns
        -------
        new_artists : matplotlib.Artist
            The matplotlib-artists added to the plot

        """
        (gpd,) = register_modules("geopandas")

        if val_key is None:
            val_key = kwargs.get("column", None)

        gdf = self._handle_gdf(
            gdf,
            val_key=val_key,
            only_valid=only_valid,
            clip=clip,
            reproject=reproject,
            verbose=verbose,
        )

        # plot gdf and identify newly added collections
        # (geopandas always uses collections)
        colls = [id(i) for i in self.ax.collections]
        artists, prefixes = [], []

        # drop all invalid geometries
        if only_valid:
            valid = gdf.is_valid
            n_invald = np.count_nonzero(~valid)
            gdf = gdf[valid]
            if len(gdf) == 0:
                _log.error("EOmaps: GeoDataFrame contains only invalid geometries!")
                return
            elif n_invald > 0:
                _log.warning(
                    "EOmaps: {n_invald} invalid GeoDataFrame geometries are ignored!"
                )

        if set_extent:
            extent = np.array(
                [
                    gdf.bounds["minx"].min(),
                    gdf.bounds["maxx"].max(),
                    gdf.bounds["miny"].min(),
                    gdf.bounds["maxy"].max(),
                ]
            )

            if isinstance(set_extent, (int, float, np.number)):
                margin = set_extent
            else:
                margin = 0.05

            dx = extent[1] - extent[0]
            dy = extent[3] - extent[2]

            d = max(dx, dy) * margin
            extent[[0, 2]] -= d
            extent[[1, 3]] += d

            self.set_extent(extent, crs=gdf.crs)

        for geomtype, geoms in gdf.groupby(gdf.geom_type):
            gdf.plot(ax=self.ax, aspect=self.ax.get_aspect(), **kwargs)
            artists = [i for i in self.ax.collections if id(i) not in colls]
            for i in artists:
                prefixes.append(f"_{i.__class__.__name__.replace('Collection', '')}")

        if picker_name is not None:
            if isinstance(pick_method, str):
                picker_cls = GeoDataFramePicker(
                    gdf=gdf, pick_method=pick_method, val_key=val_key
                )
                picker = picker_cls.get_picker()
            elif callable(pick_method):
                picker = pick_method
                picker_cls = None
            else:
                _log.error(
                    "EOmaps: The provided pick_method is invalid."
                    "Please provide either a string or a function."
                )
                return

            if len(artists) > 1:
                log_names = [picker_name + prefix for prefix in np.unique(prefixes)]
                _log.warning(
                    "EOmaps: Multiple geometry types encountered in `m.add_gdf`. "
                    + "The pick containers are re-named to"
                    + f"{log_names}"
                )
            else:
                prefixes = [""]

            for artist, prefix in zip(artists, prefixes):
                # make the newly added collection pickable
                self.cb.add_picker(picker_name + prefix, artist, picker=picker)
                # attach the re-projected GeoDataFrame to the pick-container
                self.cb.pick[picker_name + prefix].data = gdf
                self.cb.pick[picker_name + prefix].val_key = val_key
                self.cb.pick[picker_name + prefix]._picker_cls = picker_cls

        if layer is None:
            layer = self.layer

        if temporary_picker is not None:
            if temporary_picker == "default":
                for art, prefix in zip(artists, prefixes):
                    self.cb.pick.add_temporary_artist(art)
            else:
                for art, prefix in zip(artists, prefixes):
                    self.cb.pick[temporary_picker].add_temporary_artist(art)
        else:
            for art, prefix in zip(artists, prefixes):
                art.set_label(f"EOmaps GeoDataframe ({prefix.lstrip('_')}, {len(gdf)})")
                if permanent is True:
                    self.BM.add_bg_artist(art, layer)
                else:
                    self.BM.add_artist(art, layer)
        return artists

    def _handle_gdf(
        self,
        gdf,
        val_key=None,
        only_valid=True,
        clip=False,
        reproject="gpd",
        verbose=False,
    ):
        (gpd,) = register_modules("geopandas")

        if isinstance(gdf, (str, Path)):
            gdf = gpd.read_file(gdf)

        if only_valid:
            gdf = gdf[gdf.is_valid]

        try:
            # explode the GeoDataFrame to avoid picking multi-part geometries
            gdf = gdf.explode(index_parts=False)
        except Exception:
            # geopandas sometimes has problems exploding geometries...
            # if it does not work, just continue with the Multi-geometries!
            _log.error("EOmaps: Exploding geometries did not work!")
            pass

        if clip:
            gdf = self._clip_gdf(gdf, clip)
        if reproject == "gpd":
            gdf = gdf.to_crs(self.crs_plot)
        elif reproject == "cartopy":
            # optionally use cartopy's re-projection routines to re-project
            # geometries

            cartopy_crs = self._get_cartopy_crs(gdf.crs)
            if self.ax.projection != cartopy_crs:
                geoms = gdf.geometry
                if len(geoms) > 0:
                    proj_geoms = []

                    if verbose:
                        for g in progressbar(geoms, "EOmaps: re-projecting... ", 20):
                            proj_geoms.append(
                                self.ax.projection.project_geometry(g, cartopy_crs)
                            )
                    else:
                        for g in geoms:
                            proj_geoms.append(
                                self.ax.projection.project_geometry(g, cartopy_crs)
                            )
                    gdf = gdf.set_geometry(proj_geoms)
                    gdf = gdf.set_crs(self.ax.projection, allow_override=True)
                gdf = gdf[~gdf.is_empty]
        else:
            raise AssertionError(
                f"EOmaps: '{reproject}' is not a valid reproject-argument."
            )

        return gdf

    def _clip_gdf(self, gdf, how="crs"):
        """
        Clip the shapes of a GeoDataFrame with respect to the given boundaries.

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame
            The GeoDataFrame containing the geometries.
        how : str, optional
            Identifier how the clipping should be performed.

            If a suffix "_invert" is added to the string, the polygon will be
            inverted (via a symmetric-difference to the clip-shape)

            - clipping with geopandas:
              - "crs" : use the actual crs boundary polygon
              - "crs_bounds" : use the boundary-envelope of the crs
              - "extent" : use the current plot-extent

            - clipping with gdal (always uses the crs domain as clip-shape):
              - "gdal_Intersection"
              - "gdal_SymDifference"
              - "gdal_Difference"
              - "gdal_Union"

            The default is "crs".

        Returns
        -------
        gdf
            A GeoDataFrame with the clipped geometries
        """
        (gpd,) = register_modules("geopandas")

        if how.startswith("gdal"):
            methods = ["SymDifference", "Intersection", "Difference", "Union"]
            # "SymDifference", "Intersection", "Difference"
            method = how.split("_")[1]
            assert method in methods, "EOmaps: '{how}' is not a valid clip-method"
            try:
                from osgeo import gdal
                from shapely import wkt
            except ImportError:
                raise ImportError(
                    "EOmaps: Missing dependency: 'osgeo'\n"
                    + "...clipping with gdal requires 'osgeo.gdal'"
                )

            e = self.ax.projection.domain
            e2 = gdal.ogr.CreateGeometryFromWkt(e.wkt)
            if not e2.IsValid():
                e2 = e2.MakeValid()

            # only reproject geometries if crs cannot be identified
            # as the initially provided (or cartopy converted) crs
            if gdf.crs != self.crs_plot and gdf.crs != self._crs_plot:
                gdf = gdf.to_crs(self.crs_plot)

            clipgeoms = []
            for g in gdf.geometry:
                g2 = gdal.ogr.CreateGeometryFromWkt(g.wkt)

                if g2 is None:
                    continue

                if not g2.IsValid():
                    g2 = g2.MakeValid()

                i = getattr(g2, method)(e2)

                if how.endswith("_invert"):
                    i = i.SymDifference(e2)

                gclip = wkt.loads(i.ExportToWkt())
                clipgeoms.append(gclip)

            gdf = gpd.GeoDataFrame(geometry=clipgeoms, crs=self.crs_plot)

            return gdf

        if how == "crs" or how == "crs_invert":
            clip_shp = gpd.GeoDataFrame(
                geometry=[self.ax.projection.domain], crs=self.crs_plot
            ).to_crs(gdf.crs)
        elif how == "extent" or how == "extent_invert":
            self.BM.update()
            x0, x1, y0, y1 = self.get_extent()
            clip_shp = self._make_rect_poly(x0, y0, x1, y1, self.crs_plot).to_crs(
                gdf.crs
            )
        elif how == "crs_bounds" or how == "crs_bounds_invert":
            x0, x1, y0, y1 = self.get_extent()
            clip_shp = self._make_rect_poly(
                *self.crs_plot.boundary.bounds, self.crs_plot
            ).to_crs(gdf.crs)
        else:
            raise TypeError(f"EOmaps: '{how}' is not a valid clipping method")

        clip_shp = clip_shp.buffer(0)  # use this to make sure the geometry is valid

        # add 1% of the extent-diameter as buffer
        bnd = clip_shp.boundary.bounds
        d = np.sqrt((bnd.maxx - bnd.minx) ** 2 + (bnd.maxy - bnd.miny) ** 2)
        clip_shp = clip_shp.buffer(d / 100)

        # clip the geo-dataframe with the buffered clipping shape
        clipgdf = gdf.clip(clip_shp)

        if how.endswith("_invert"):
            clipgdf = clipgdf.symmetric_difference(clip_shp)

        return clipgdf

    def add_marker(
        self,
        ID=None,
        xy=None,
        xy_crs=None,
        radius=None,
        radius_crs=None,
        shape="ellipses",
        buffer=1,
        n=100,
        layer=None,
        update=True,
        **kwargs,
    ):
        """
        Add a marker to the plot.

        Parameters
        ----------
        ID : any
            The index-value of the pixel in m.data.
        xy : tuple
            A tuple of the position of the pixel provided in "xy_crs".
            If "xy_crs" is None, xy must be provided in the plot-crs!
            The default is None
        xy_crs : any
            the identifier of the coordinate-system for the xy-coordinates
        radius : float or "pixel", optional
            - If float: The radius of the marker.
            - If "pixel": It will represent the dimensions of the selected pixel.
              (check the `buffer` kwarg!)

            The default is None in which case "pixel" is used if a dataset is
            present and otherwise a shape with 1/10 of the axis-size is plotted
        radius_crs : str or a crs-specification
            The crs specification in which the radius is provided.
            Either "in", "out", or a crs specification (e.g. an epsg-code,
            a PROJ or wkt string ...)
            The default is "in" (e.g. the crs specified via `m.data_specs.crs`).
            (only relevant if radius is NOT specified as "pixel")
        shape : str, optional
            Indicator which shape to draw. Currently supported shapes are:
            - geod_circles
            - ellipses
            - rectangles

            The default is "circle".
        buffer : float, optional
            A factor to scale the size of the shape. The default is 1.
        n : int
            The number of points to calculate for the shape.
            The default is 100.
        layer : str, int or None
            The name of the layer at which the marker should be drawn.
            If None, the layer associated with the used Maps-object (e.g. m.layer)
            is used. The default is None.
        kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `zorder`, `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)
        update : bool, optional
            If True, call m.BM.update() to immediately show dynamic annotations
            If False, dynamic annotations will only be shown at the next update

        Examples
        --------
            >>> m.add_marker(ID=1, buffer=5)
            >>> m.add_marker(ID=1, radius=2, radius_crs=4326, shape="rectangles")
            >>> m.add_marker(xy=(4, 3), xy_crs=4326, radius=20000, shape="geod_circles")
        """
        if ID is not None:
            assert xy is None, "You can only provide 'ID' or 'pos' not both!"
        else:
            if isinstance(radius, str) and radius != "pixel":
                raise TypeError(f"I don't know what to do with radius='{radius}'")

        if xy is not None:
            ID = None
            if xy_crs is not None:
                # get coordinate transformation
                transformer = self._get_transformer(
                    self.get_crs(xy_crs),
                    self.crs_plot,
                )
                # transform coordinates
                xy = transformer.transform(*xy)

        if layer is None:
            layer = self.layer

        # using permanent=None results in permanent makers that  are NOT
        # added to the "m.cb.click.get.permanent_markers" list that is
        # used to manage callback-markers

        permanent = kwargs.pop("permanent", None)

        # call the "mark" callback function to add the marker
        marker = self.cb.click._attach.mark(
            self.cb.click.attach,
            ID=ID,
            pos=xy,
            radius=radius,
            radius_crs=radius_crs,
            ind=None,
            shape=shape,
            buffer=buffer,
            n=n,
            layer=layer,
            permanent=permanent,
            **kwargs,
        )

        if permanent is False and update:
            self.BM.update()

        return marker

    def add_annotation(
        self,
        ID=None,
        xy=None,
        xy_crs=None,
        text=None,
        update=True,
        **kwargs,
    ):
        """
        Add an annotation to the plot.

        Parameters
        ----------
        ID : str, int, float or array-like
            The index-value of the pixel in m.data.
        xy : tuple of float or array-like
            A tuple of the position of the pixel provided in "xy_crs".
            If None, xy must be provided in the coordinate-system of the plot!
            The default is None.
        xy_crs : any
            the identifier of the coordinate-system for the xy-coordinates
        text : callable or str, optional
            if str: the string to print
            if callable: A function that returns the string that should be
            printed in the annotation with the following call-signature:

                >>> def text(m, ID, val, pos, ind):
                >>>     # m   ... the Maps object
                >>>     # ID  ... the ID
                >>>     # pos ... the position
                >>>     # val ... the value
                >>>     # ind ... the index of the clicked pixel
                >>>
                >>>     return "the string to print"

            The default is None.
        update : bool, optional
            If True, call m.BM.update() to immediately show dynamic annotations
            If False, dynamic annotations will only be shown at the next update
        **kwargs
            kwargs passed to m.cb.annotate

        Examples
        --------
        >>> m.add_annotation(ID=1)
        >>> m.add_annotation(xy=(45, 35), xy_crs=4326)

        NOTE: You can provide lists to add multiple annotations in one go!

        >>> m.add_annotation(ID=[1, 5, 10, 20])
        >>> m.add_annotation(xy=([23.5, 45.8, 23.7], [5, 6, 7]), xy_crs=4326)

        The text can be customized by providing either a string

        >>> m.add_annotation(ID=1, text="some text")

        or a callable that returns a string with the following signature:

        >>> def addtxt(m, ID, val, pos, ind):
        >>>     return f"The ID {ID} at position {pos} has a value of {val}"
        >>> m.add_annotation(ID=1, text=addtxt)

        **Customizing the appearance**

        For the full set of possibilities, see:
        https://matplotlib.org/stable/tutorials/text/annotations.html

        >>> m.add_annotation(xy=[7.10, 45.16], xy_crs=4326,
        >>>                  text="blubb", xytext=(30,30),
        >>>                  horizontalalignment="center", verticalalignment="center",
        >>>                  arrowprops=dict(ec="g",
        >>>                                  arrowstyle='-[',
        >>>                                  connectionstyle="angle",
        >>>                                  ),
        >>>                  bbox=dict(boxstyle='circle,pad=0.5',
        >>>                            fc='yellow',
        >>>                            alpha=0.3
        >>>                            )
        >>>                  )

        """
        inp_ID = ID

        if xy is None and ID is None:
            x = self.ax.bbox.x0 + self.ax.bbox.width / 2
            y = self.ax.bbox.y0 + self.ax.bbox.height / 2
            xy = self.ax.transData.inverted().transform((x, y))

        if ID is not None:
            assert xy is None, "You can only provide 'ID' or 'pos' not both!"
            # avoid using np.isin directly since it needs a lot of ram
            # for very large datasets!
            mask, ind = self._find_ID(ID)

            xy = (
                self._data_manager.xorig.ravel()[mask],
                self._data_manager.yorig.ravel()[mask],
            )
            val = self._data_manager.z_data.ravel()[mask]
            ID = np.atleast_1d(ID)
            xy_crs = self.data_specs.crs

            is_ID_annotation = False
        else:
            val = repeat(None)
            ind = repeat(None)
            ID = repeat(None)

            is_ID_annotation = True

        assert (
            xy is not None
        ), "EOmaps: you must provide either ID or xy to position the annotation!"

        xy = (np.atleast_1d(xy[0]), np.atleast_1d(xy[1]))

        if xy_crs is not None:
            # get coordinate transformation
            transformer = self._get_transformer(
                CRS.from_user_input(xy_crs),
                self.crs_plot,
            )
            # transform coordinates
            xy = transformer.transform(*xy)
        else:
            transformer = None

        kwargs.setdefault("permanent", None)

        if isinstance(text, str) or callable(text):
            usetext = repeat(text)
        else:
            try:
                usetext = iter(text)
            except TypeError:
                usetext = repeat(text)

        for x, y, texti, vali, indi, IDi in zip(xy[0], xy[1], usetext, val, ind, ID):
            ann = self.cb.click._attach.annotate(
                self.cb.click.attach,
                ID=IDi,
                pos=(x, y),
                val=vali,
                ind=indi,
                text=texti,
                **kwargs,
            )

            if kwargs.get("permanent", False) is not False:
                self._edit_annotations._add(
                    a=ann,
                    kwargs={
                        "ID": inp_ID,
                        "xy": (x, y),
                        "xy_crs": xy_crs,
                        "text": text,
                        **kwargs,
                    },
                    transf=transformer,
                    drag_coords=is_ID_annotation,
                )

        if update:
            self.BM.update(clear=False)
        return ann

    @wraps(Compass.__call__)
    def add_compass(self, *args, **kwargs):
        """Add a compass (or north-arrow) to the map."""
        c = Compass(weakref.proxy(self))
        c(*args, **kwargs)
        # store a reference to the object (required for callbacks)!
        self._compass.add(c)
        return c

    @wraps(ScaleBar.__init__)
    def add_scalebar(
        self,
        pos=None,
        rotation=0,
        scale=None,
        n=10,
        preset=None,
        autoscale_fraction=0.25,
        auto_position=(0.8, 0.25),
        scale_props=None,
        patch_props=None,
        label_props=None,
        line_props=None,
        layer=None,
        size_factor=1,
        pickable=True,
    ):
        """Add a scalebar to the map."""
        s = ScaleBar(
            m=self,
            preset=preset,
            scale=scale,
            n=n,
            autoscale_fraction=autoscale_fraction,
            auto_position=auto_position,
            scale_props=scale_props,
            patch_props=patch_props,
            label_props=label_props,
            line_props=line_props,
            layer=layer,
            size_factor=size_factor,
        )

        # add the scalebar to the map at the desired position
        s._add_scalebar(pos=pos, azim=rotation, pickable=pickable)
        self.BM.update()
        return s

    def add_line(
        self,
        xy,
        xy_crs=4326,
        connect="geod",
        n=None,
        del_s=None,
        mark_points=None,
        layer=None,
        **kwargs,
    ):
        """
        Draw a line by connecting a set of anchor-points.

        The points can be connected with either "geodesic-lines", "straight lines" or
        "projected straight lines with respect to a given crs" (see `connect` kwarg).

        Parameters
        ----------
        xy : list, set or numpy.ndarray
            The coordinates of the anchor-points that define the line.
            Expected shape:  [(x0, y0), (x1, y1), ...]
        xy_crs : any, optional
            The crs of the anchor-point coordinates.
            (can be any crs definition supported by PyProj)
            The default is 4326 (e.g. lon/lat).
        connect : str, optional
            The connection-method used to draw the segments between the anchor-points.

            - "geod": Connect the anchor-points with geodesic lines
            - "straight": Connect the anchor-points with straight lines
            - "straight_crs": Connect the anchor-points with straight lines in the
              `xy_crs` projection and reproject those lines to the plot-crs.

            The default is "geod".
        n : int, list or None optional
            The number of intermediate points to use for each line-segment.

            - If an integer is provided, each segment is equally divided into n parts.
            - If a list is provided, it is used to specify "n" for each line-segment
              individually.

              (NOTE: The number of segments is 1 less than the number of anchor-points!)

            If both n and del_s is None, n=100 is used by default!

            The default is None.
        del_s : int, float or None, optional
            Only relevant if `connect="geod"`!

            The target-distance in meters between the subdivisions of the line-segments.

            - If a number is provided, each segment is equally divided.
            - If a list is provided, it is used to specify "del_s" for each line-segment
              individually.

              (NOTE: The number of segments is 1 less than the number of anchor-points!)

            The default is None.
        mark_points : str, dict or None, optional
            Set the marker-style for the anchor-points.

            - If a string is provided, it is identified as a matplotlib "format-string",
              e.g. "r." for red dots, "gx" for green x markers etc.
            - if a dict is provided, it will be used to set the style of the markers
              e.g.: dict(marker="o", facecolor="orange", edgecolor="g")

            See https://matplotlib.org/stable/gallery/lines_bars_and_markers/marker_reference.html
            for more details

            The default is "o"

        layer : str, int or None
            The name of the layer at which the line should be drawn.
            If None, the layer associated with the used Maps-object (e.g. m.layer)
            is used. Use "all" to add the line to all layers!
            The default is None.
        kwargs :
            additional keyword-arguments passed to plt.plot(), e.g.
            "c" (or "color"), "lw" (or "linewidth"), "ls" (or "linestyle"),
            "markevery", etc.

            See https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.plot.html
            for more details.

        Returns
        -------
        out_d_int : list
            Only relevant for `connect="geod"`! (An empty list is returned otherwise.)
            A list of the subdivision distances of the line-segments (in meters).
        out_d_tot : list
            Only relevant for `connect="geod"` (An empty list is returned otherwise.)
            A list of total distances of the line-segments (in meters).

        """
        if layer is None:
            layer = self.layer

        # intermediate and total distances
        out_d_int, out_d_tot = [], []

        if len(xy) <= 1:
            _log.error("you must provide at least 2 points")

        if n is not None:
            assert del_s is None, "EOmaps: Provide either `del_s` or `n`, not both!"
            del_s = 0  # pyproj's geod uses 0 as identifier!

            if not isinstance(n, int):
                assert len(n) == len(xy) - 1, (
                    "EOmaps: The number of subdivisions per line segment (n) must be"
                    + " 1 less than the number of points!"
                )

        elif del_s is not None:
            assert n is None, "EOmaps: Provide either `del_s` or `n`, not both!"
            n = 0  # pyproj's geod uses 0 as identifier!

            assert connect in ["geod"], (
                "EOmaps: Setting a fixed subdivision-distance (e.g. `del_s`) is only "
                + "possible for `geod` lines! Use `n` instead!"
            )

            if not isinstance(del_s, (int, float, np.number)):
                assert len(del_s) == len(xy) - 1, (
                    "EOmaps: The number of subdivision-distances per line segment "
                    + "(`del_s`) must be 1 less than the number of points!"
                )
        else:
            # use 100 subdivisions by default
            n = 100
            del_s = 0

        t_xy_plot = self._get_transformer(
            self.get_crs(xy_crs),
            self.crs_plot,
        )
        xplot, yplot = t_xy_plot.transform(*zip(*xy))

        if connect == "geod":
            # connect points via geodesic lines
            if xy_crs != 4326:
                t = self._get_transformer(
                    self.get_crs(xy_crs),
                    self.get_crs(4326),
                )
                x, y = t.transform(*zip(*xy))
            else:
                x, y = zip(*xy)

            geod = self.crs_plot.get_geod()

            if n is None or isinstance(n, int):
                n = repeat(n)

            if del_s is None or isinstance(del_s, (int, float, np.number)):
                del_s = repeat(del_s)

            xs, ys = [], []
            for (x0, x1), (y0, y1), ni, di in zip(pairwise(x), pairwise(y), n, del_s):
                npts, d_int, d_tot, lon, lat, _ = geod.inv_intermediate(
                    lon1=x0,
                    lat1=y0,
                    lon2=x1,
                    lat2=y1,
                    del_s=di,
                    npts=ni,
                    initial_idx=0,
                    terminus_idx=0,
                )

                out_d_int.append(d_int)
                out_d_tot.append(d_tot)

                lon, lat = lon.tolist(), lat.tolist()
                xi, yi = self._transf_lonlat_to_plot.transform(lon, lat)
                xs += xi
                ys += yi
            (art,) = self.ax.plot(xs, ys, **kwargs)

        elif connect == "straight":
            (art,) = self.ax.plot(xplot, yplot, **kwargs)

        elif connect == "straight_crs":
            # draw a straight line that is defined in a given crs

            x, y = zip(*xy)
            if isinstance(n, int):
                # use same number of points for all segments
                xs = np.linspace(x[:-1], x[1:], n).T.ravel()
                ys = np.linspace(y[:-1], y[1:], n).T.ravel()
            else:
                # use different number of points for individual segments

                xs = list(
                    chain(
                        *(np.linspace(a, b, ni) for (a, b), ni in zip(pairwise(x), n))
                    )
                )
                ys = list(
                    chain(
                        *(np.linspace(a, b, ni) for (a, b), ni in zip(pairwise(y), n))
                    )
                )

            x, y = t_xy_plot.transform(xs, ys)

            (art,) = self.ax.plot(x, y, **kwargs)
        else:
            raise TypeError(f"EOmaps: '{connect}' is not a valid connection-method!")

        art.set_label(f"Line ({connect})")
        self.BM.add_bg_artist(art, layer)

        if mark_points:
            zorder = kwargs.get("zorder", 10)

            if isinstance(mark_points, dict):
                # only use zorder of the line if no explicit zorder is provided
                mark_points["zorder"] = mark_points.get("zorder", zorder)

                art2 = self.ax.scatter(xplot, yplot, **mark_points)

            elif isinstance(mark_points, str):
                # use matplotlib's single-string style identifiers,
                # (e.g. "r.", "go", "C0x" etc.)
                (art2,) = self.ax.plot(xplot, yplot, mark_points, zorder=zorder, lw=0)

            art2.set_label(f"Line Marker ({connect})")
            self.BM.add_bg_artist(art2, layer)

        return out_d_int, out_d_tot

    def add_logo(
        self,
        filepath=None,
        position="lr",
        size=0.12,
        pad=0.1,
        layer=None,
        fix_position=False,
    ):
        """
        Add a small image (png, jpeg etc.) to the map.

        The position of the image is dynamically updated if the plot is resized or
        zoomed.

        Parameters
        ----------
        filepath : str, optional
            if str: The path to the image-file.
            The default is None in which case an EOmaps logo is added to the map.
        position : str, optional
            The position of the logo.
            - "ul", "ur" : upper left, upper right
            - "ll", "lr" : lower left, lower right
            The default is "lr".
        size : float, optional
            The size of the logo as a fraction of the axis-width.
            The default is 0.15.
        pad : float, tuple optional
            Padding between the axis-edge and the logo as a fraction of the logo-width.
            If a tuple is passed, (x-pad, y-pad)
            The default is 0.1.
        layer : str or None, optional
            The layer at which the logo should be visible.
            If None, the logo will be added to all layers and will be drawn on
            top of all background artists. The default is None.
        fix_position : bool, optional
            If True, the relative position of the logo (with respect to the map-axis)
            is fixed (and dynamically updated on zoom / resize events)

            NOTE: If True, the logo can NOT be moved with the layout_editor!
            The default is False.

        """
        if layer is None:
            layer = "__SPINES__"

        if filepath is None:
            filepath = Path(__file__).parent / "logo.png"

        im = mpl.image.imread(filepath)

        def getpos(pos):
            s = size
            if isinstance(pad, tuple):
                pwx, pwy = (s * pad[0], s * pad[1])
            else:
                pwx, pwy = (s * pad, s * pad)

            if position == "lr":
                p = dict(rect=[pos.x1 - s - pwx, pos.y0 + pwy, s, s], anchor="SE")
            elif position == "ll":
                p = dict(rect=[pos.x0 + pwx, pos.y0 + pwy, s, s], anchor="SW")
            elif position == "ur":
                p = dict(rect=[pos.x1 - s - pwx, pos.y1 - s - pwy, s, s], anchor="NE")
            elif position == "ul":
                p = dict(rect=[pos.x0 + pwx, pos.y1 - s - pwy, s, s], anchor="NW")
            return p

        figax = self.f.add_axes(
            **getpos(self.ax.get_position()), label="logo", zorder=999, animated=True
        )

        figax.set_navigate(False)
        figax.set_axis_off()
        _ = figax.imshow(im, aspect="equal", zorder=999, interpolation_stage="rgba")

        self.BM.add_bg_artist(figax, layer)

        if fix_position:
            fixed_pos = (
                figax.get_position()
                .transformed(self.f.transFigure)
                .transformed(self.ax.transAxes.inverted())
            )

            figax.set_axes_locator(
                _TransformedBoundsLocator(fixed_pos.bounds, self.ax.transAxes)
            )

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

    @wraps(GridFactory.add_grid)
    def add_gridlines(self, *args, **kwargs):
        """Add gridlines to the Map."""
        return self.parent._grid.add_grid(m=self, *args, **kwargs)

    def indicate_extent(self, x0, y0, x1, y1, crs=4326, npts=100, **kwargs):
        """
        Indicate a rectangular extent in a given crs on the map.

        Parameters
        ----------
        x0, y0, y1, y1 : float
            the boundaries of the shape
        npts : int, optional
            The number of points used to draw the polygon-lines.
            (e.g. to correctly display the distortion of the extent-rectangle when
            it is re-projected to another coordinate-system)
            The default is 100.
        crs : any, optional
            A coordinate-system identifier.
            The default is 4326 (e.g. lon/lat).
        kwargs :
            Additional keyword-arguments passed to `m.add_gdf()`.
        """
        register_modules("geopandas")

        gdf = self._make_rect_poly(x0, y0, x1, y1, self.get_crs(crs), npts)
        self.add_gdf(gdf, **kwargs)

    @wraps(plt.Figure.text)
    def text(self, *args, layer=None, **kwargs):
        """Add text to the map."""
        kwargs.setdefault("animated", True)
        kwargs.setdefault("horizontalalignment", "center")
        kwargs.setdefault("verticalalignment", "center")

        a = self.f.text(*args, **kwargs)

        if layer is None:
            layer = self.layer
        self.BM.add_artist(a, layer=layer)
        self.BM.update()

        return a

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
            if self.classify_specs.scheme is not None:
                _log.debug("EOmaps: Classifying...")
            elif self.shape.name == "contour" and kwargs.get("levels", None) is None:
                # TODO use custom contour-levels as UserDefined classification?
                self.set_classify.EqualInterval(k=5)

        cbcmap, norm, bins, classified = self._classify_data(
            vmin=self._vmin,
            vmax=self._vmax,
            cmap=cmap,
            classify_specs=self.classify_specs,
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
        self.classify_specs._cbcmap = cbcmap
        self.classify_specs._norm = norm
        self.classify_specs._bins = bins
        self.classify_specs._classified = classified

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
            kwargs.setdefault("norm", self.classify_specs._norm)
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
            self.BM.add_artist(coll, layer)
        else:
            self.BM.add_bg_artist(coll, layer)

        if dynamic is True:
            self.BM.update(clear=False)

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
            classify_specs = list(self.classify_specs.keys())
            copy_cls.set_classify_specs(
                scheme=self.classify_specs.scheme, **self.classify_specs
            )

        return copy_cls

    def redraw(self, *args):
        self._data_manager.last_extent = None
        super().redraw(*args)

    def snapshot(self, *args, **kwargs):
        # hide companion-widget indicator
        for m in (self.parent, *self.parent._children):
            # hide companion-widget indicator
            m._indicate_companion_map(False)

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
                if _cx_refetch_wms_on_size_change is not None:
                    stack.enter_context(_cx_refetch_wms_on_size_change(refetch_wms))

            for m in (self.parent, *self.parent._children):
                # hide companion-widget indicator
                m._indicate_companion_map(False)

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

        # close the pyqt widget if there is one
        if self._companion_widget is not None:
            self._companion_widget.close()

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

    def _save_to_clipboard(self, **kwargs):
        """
        Export the figure to the clipboard.

        Parameters
        ----------
        kwargs :
            Keyword-arguments passed to :py:meth:`Maps.savefig`
        """
        import io
        import mimetypes
        from qtpy.QtCore import QMimeData
        from qtpy.QtWidgets import QApplication
        from qtpy.QtGui import QImage

        # guess the MIME type from the provided file-extension
        fmt = kwargs.get("format", "png")
        mimetype, _ = mimetypes.guess_type(f"dummy.{fmt}")

        message = f"EOmaps: Exporting figure as '{fmt}' to clipboard..."
        _log.info(message)

        # TODO remove dependency on companion widget here
        if getattr(self, "_companion_widget", None) is not None:
            self._companion_widget.window().statusBar().showMessage(message, 2000)

        with io.BytesIO() as buffer:
            self.savefig(buffer, **kwargs)
            data = QMimeData()

            cb = QApplication.clipboard()

            # TODO check why files copied with setMimeData(...) cannot be pasted
            # properly in other apps
            if fmt in ["svg", "svgz", "pdf", "eps"]:
                data.setData(mimetype, buffer.getvalue())
                cb.clear(mode=cb.Clipboard)
                cb.setMimeData(data, mode=cb.Clipboard)
            else:
                cb.setImage(QImage.fromData(buffer.getvalue()))

    def _on_keypress(self, event):
        if plt.get_backend().lower() == "webagg":
            return

        # NOTE: callback is only attached to the parent Maps object!
        if event.key == self._companion_widget_key:
            try:
                self._open_companion_widget((event.x, event.y))
            except Exception:
                _log.exception(
                    "EOmaps: Encountered a problem while trying to open "
                    "the companion widget",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )
        elif event.key == "ctrl+c":
            try:
                self._save_to_clipboard(**Maps._clipboard_kwargs)
            except Exception:
                _log.exception(
                    "EOmaps: Encountered a problem while trying to export the figure "
                    "to the clipboard.",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

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
            if self.classify_specs.scheme == "UserDefined":
                bins = self.classify_specs.bins
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

            def __new__(cls, **kwargs):
                if "y" in kwargs:
                    _log.error(
                        "EOmaps: The values (e.g. the 'y' parameter) are "
                        + "assigned internally... only provide additional "
                        + "parameters that specify the classification scheme!"
                    )
                    kwargs.pop("y")

                self.classify_specs._set_scheme_and_args(scheme=s.__name__, **kwargs)

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

    @lru_cache()
    def _get_nominatim_response(self, q, user_agent=None):
        import requests

        _log.info(f"Querying {q}")
        if user_agent is None:
            user_agent = f"EOMaps v{Maps.__version__}"

        headers = {
            "User-Agent": user_agent,
        }

        resp = requests.get(
            rf"https://nominatim.openstreetmap.org/search?q={q}&format=json&addressdetails=1&limit=1",
            headers=headers,
        ).json()

        if len(resp) == 0:
            raise TypeError(f"Unable to resolve the location: {q}")

        return resp[0]

    def _indicate_companion_map(self, visible):
        if hasattr(self, "_companion_map_indicator"):
            self.BM.remove_artist(self._companion_map_indicator)
            try:
                self._companion_map_indicator.remove()
            except ValueError:
                # ignore errors resulting from the fact that the artist
                # has already been removed!
                pass
            del self._companion_map_indicator

        if self._companion_widget is None:
            return

        # don't draw an indicator if only one map is present in the figure
        if all(m.ax == self.ax for m in (self.parent, *self.parent._children)):
            return

        if visible:
            path = self.ax.patch.get_path()
            self._companion_map_indicator = mpatches.PathPatch(
                path, fc="none", ec="g", lw=5, zorder=9999
            )

            self.ax.add_artist(self._companion_map_indicator)
            self.BM.add_artist(self._companion_map_indicator, "all")

        self.BM.update()

    def _open_companion_widget(self, xy=None):
        """
        Open the companion-widget.

        Parameters
        ----------
        xy : tuple, optional
            The click position to identify the relevant Maps-object
            (in figure coordinates).
            If None, the calling Maps-object is used

            The default is None.

        """

        clicked_map = self
        if xy is not None:
            for m in (self.parent, *self.parent._children):
                if not m._new_axis_map:
                    # only search for Maps-object that initialized new axes
                    continue

                if m.ax.contains_point(xy):
                    clicked_map = m

        if clicked_map is None:
            _log.error(
                "EOmaps: To activate the 'Companion Widget' you must "
                "position the mouse on top of an EOmaps Map!"
            )
            return

        # hide all other companion-widgets
        for m in (self.parent, *self.parent._children):
            if m == clicked_map:
                continue
            if m._companion_widget is not None and m._companion_widget.isVisible():
                m._companion_widget.hide()
                m._indicate_companion_map(False)

        if clicked_map._companion_widget is None:
            clicked_map._init_companion_widget()

        if clicked_map._companion_widget is not None:
            if clicked_map._companion_widget.isVisible():
                clicked_map._companion_widget.hide()
                clicked_map._indicate_companion_map(False)
            else:
                clicked_map._companion_widget.show()
                clicked_map._indicate_companion_map(True)
                # execute all actions that should trigger before opening the widget
                # (e.g. update tabs to show visible layers etc.)
                for f in clicked_map._on_show_companion_widget:
                    f()

                # Do NOT activate the companion widget in here!!
                # Activating the window during the callback steals focus and
                # as a consequence the key-released-event is never triggered
                # on the figure and "w" would remain activated permanently.

                _key_release_event(clicked_map.f.canvas, "w")
                clicked_map._companion_widget.activateWindow()

    def _init_companion_widget(self, show_hide_key="w"):
        """
        Create and show the EOmaps Qt companion widget.

        Note
        ----
        The companion-widget requires using matplotlib with the Qt5Agg backend!
        To activate, use: `plt.switch_backend("Qt5Agg")`

        Parameters
        ----------
        show_hide_key : str or None, optional
            The keyboard-shortcut that is assigned to show/hide the widget.
            The default is "w".
        """
        try:
            from .qtcompanion.app import MenuWindow

            if self._companion_widget is not None:
                _log.error(
                    "EOmaps: There is already an existing companinon widget for this"
                    " Maps-object!"
                )
                return
            if plt.get_backend().lower() in ["qtagg", "qt5agg"]:
                # only pass parent if Qt is used as a backend for matplotlib!
                self._companion_widget = MenuWindow(m=self, parent=self.f.canvas)
            else:
                self._companion_widget = MenuWindow(m=self)
                self._companion_widget.toggle_always_on_top()

            # connect any pending signals
            for key, funcs in getattr(self, "_connect_signals_on_init", dict()).items():
                while len(funcs) > 0:
                    self._connect_signal(key, funcs.pop())

            # make sure that we clear the colormap-pixmap cache on startup
            self._emit_signal("cmapsChanged")

        except Exception:
            _log.exception(
                "EOmaps: Unable to initialize companion widget.",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

    def _connect_signal(self, name, func):
        parent = self.parent
        widget = parent._companion_widget

        # NOTE: use Maps.config(log_level=5) to get signal log messages!
        if widget is None:
            if not hasattr(parent, "_connect_signals_on_init"):
                parent._connect_signals_on_init = dict()

            parent._connect_signals_on_init.setdefault(name, set()).add(func)

        if widget is not None:
            try:
                getattr(parent._signal_container, name).connect(func)
                _log.log(1, f"Signal connected: {name} ({func.__name__})")

            except Exception:
                _log.log(
                    1,
                    f"There was a problem while trying to connect the function {func} "
                    f"to the signal {name} ",
                    exc_info=True,
                )

    def _emit_signal(self, name, *args):
        parent = self.parent
        widget = parent._companion_widget

        # NOTE: use Maps.config(log_level=5) to get signal log messages!
        if widget is not None:
            try:
                getattr(parent._signal_container, name).emit(*args)
                _log.log(1, f"Signal emitted: {name} {args}")
            except Exception:
                _log.log(
                    1,
                    f"There was a problem while trying to emit the signal {name} "
                    f"with the args {args}",
                    exc_info=True,
                )

    def _get_always_on_top(self):
        if "qt" in plt.get_backend().lower():
            from qtpy import QtCore

            w = self.f.canvas.window()
            return bool(w.windowFlags() & QtCore.Qt.WindowStaysOnTopHint)

        return False

    def _set_always_on_top(self, q):
        # keep pyqt window on top
        try:
            from qtpy import QtCore

            if q:
                # only do this if necessary to avoid flickering
                # see https://stackoverflow.com/a/40007740/9703451
                if not self._get_always_on_top():
                    # in case pyqt is used as backend, also keep the figure on top
                    if "qt" in plt.get_backend().lower():
                        w = self.f.canvas.window()
                        ws = w.size()
                        w.setWindowFlags(
                            w.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
                        )
                        w.resize(ws)
                        w.show()

                    # handle the widget in case it was activated (possible also for
                    # backends other than qt)
                    if self._companion_widget is not None:
                        cw = self._companion_widget.window()
                        cws = cw.size()
                        cw.setWindowFlags(
                            cw.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
                        )
                        cw.resize(cws)
                        cw.show()

            else:
                if self._get_always_on_top():
                    if "qt" in plt.get_backend().lower():
                        w = self.f.canvas.window()
                        ws = w.size()
                        w.setWindowFlags(
                            w.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint
                        )
                        w.resize(ws)
                        w.show()

                    if self._companion_widget is not None:
                        cw = self._companion_widget.window()
                        cws = cw.size()
                        cw.setWindowFlags(
                            cw.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint
                        )
                        cw.resize(cws)
                        cw.show()
        except Exception:
            pass

    @staticmethod
    def _make_rect_poly(x0, y0, x1, y1, crs=None, npts=100):
        """
        Return a geopandas.GeoDataFrame with a rectangle in the given crs.

        Parameters
        ----------
        x0, y0, y1, y1 : float
            the boundaries of the shape
        npts : int, optional
            The number of points used to draw the polygon-lines. The default is 100.
        crs : any, optional
            a coordinate-system identifier.  (e.g. output of `m.get_crs(crs)`)
            The default is None.

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            the geodataframe with the shape and crs defined

        """
        (gpd,) = register_modules("geopandas")

        from shapely.geometry import Polygon

        xs, ys = np.linspace([x0, y0], [x1, y1], npts).T
        x0, y0, x1, y1, xs, ys = np.broadcast_arrays(x0, y0, x1, y1, xs, ys)
        verts = np.column_stack(((x0, ys), (xs, y1), (x1, ys[::-1]), (xs[::-1], y0))).T

        gdf = gpd.GeoDataFrame(geometry=[Polygon(verts)])
        gdf.set_crs(crs, inplace=True)

        return gdf

    def fetch_companion_wms_layers(self, refetch=True):
        """
        Fetch (and cache) WebMap layer names for the companion-widget.

        The cached layers are stored at the following location:

        >>> from eomaps import _data_dir
        >>> print(_data_dir)

        Parameters
        ----------
        refetch : bool, optional
            If True, the layers will be re-fetched and the cache will be updated.
            If False, the cached dict is loaded and returned.
            The default is True.
        """
        from .qtcompanion.widgets.wms import AddWMSMenuButton

        return AddWMSMenuButton.fetch_all_wms_layers(self, refetch=refetch)

    if refetch_wms_on_size_change is not None:

        @wraps(refetch_wms_on_size_change)
        def refetch_wms_on_size_change(self, *args, **kwargs):
            """Set the behavior for WebMap services on axis or figure size changes."""
            refetch_wms_on_size_change(*args, **kwargs)

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

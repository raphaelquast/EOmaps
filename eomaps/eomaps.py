"""A collection of helper-functions to generate map-plots."""

from functools import lru_cache, wraps
from itertools import repeat
from textwrap import dedent
import warnings
import copy
from types import SimpleNamespace
from pathlib import Path
import weakref
import gc
from textwrap import fill
from contextlib import contextmanager, ExitStack

import numpy as np

# ------- perform lazy delayed imports
# (for optional dependencies that take long time to import)


pd = None


def _register_pandas():
    global pd
    try:
        import pandas as pd
    except ImportError:
        return False

    return True


gpd = None


def _register_geopandas():
    global gpd
    try:
        import geopandas as gpd
    except ImportError:
        return False

    return True


xar = None


def _register_xarray():
    global xar
    try:
        import xarray as xar
    except ImportError:
        return False

    return True


ds, mpl_ext = None, None


def _register_datashader():
    global ds
    global mpl_ext

    try:
        import datashader as ds
        from datashader import mpl_ext
    except ImportError:
        return False

    return True


mapclassify = None


def _register_mapclassify():
    global mapclassify
    try:
        import mapclassify
    except ImportError:
        return False

    return True


from pyproj import CRS, Transformer

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, SubplotSpec

import matplotlib.patches as mpatches

from cartopy import crs as ccrs
from cartopy.mpl.geoaxes import GeoAxes

from .helpers import (
    pairwise,
    cmap_alpha,
    BlitManager,
    LayoutEditor,
    progressbar,
    searchtree,
    _TransformedBoundsLocator,
    _add_to_docstring,
)
from ._shapes import shapes
from .colorbar import ColorBar

from ._containers import (
    data_specs,
    classify_specs,
)

try:
    from ._webmap import refetch_wms_on_size_change, _cx_refetch_wms_on_size_change
    from ._webmap_containers import wms_container
except ImportError as ex:
    print("EOmaps: Unable to import required WebMap dependencies:", ex)
    refetch_wms_on_size_change = None
    _cx_refetch_wms_on_size_change = None
    wms_container = None

from .ne_features import NaturalEarth_features

from ._cb_container import cb_container, _gpd_picker
from .scalebar import ScaleBar, Compass
from .projections import Equi7Grid_projection  # import to supercharge cartopy.ccrs
from .reader import read_file, from_file, new_layer_from_file
from .grid import GridFactory

from .utilities import utilities
from .draw import ShapeDrawer

from ._data_manager import DataManager

from ._version import __version__

_backend_warning_shown = False


def _handle_backends():
    global _backend_warning_shown

    if plt.isinteractive():
        if plt.get_backend() in [
            "module://ipympl.backend_nbagg",
            "module://matplotlib_inline.backend_inline",
        ]:
            plt.ioff()

            if not _backend_warning_shown:
                warnings.warn(
                    "EOmaps disables matplotlib's interactive mode (e.g. 'plt.ioff()') "
                    f"for the backend {plt.get_backend()}.\n"
                    "Call `m.snapshot()` to print a static snapshot of the map "
                    "to a Jupyter Notebook cell (or an IPython console)!"
                )

                _backend_warning_shown = True


_handle_backends()

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


class Maps(object):
    """
    The base-class for generating plots with EOmaps.

    See Also
    --------
    Maps.new_layer : Create a new layer for the map.

    Maps.new_map : Add a new map to the figure.

    Maps.new_inset_map : Add a new inset-map to the figure.

    MapsGrid : Initialize a grid of Maps objects

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
        - `matplotilb.gridspec.SubplotSpec`:
            Use the SubplotSpec for initializing the axes.
        - `matplotilb.Axes`:
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
    Create a new figure and axes

    >>> m = Maps()
    >>> ...

    Create a new figure and position the map at (left, bottom, width, height)

    >>> m = Maps(ax=(.25, .5, .5, .5))

    Use an existing figure and position the map at (left, bottom, width, height)

    >>> import matplotlib.pyplot as plt
    >>> from matplotlib.gridspec import GridSpec
    >>> f = plt.figure()
    >>> m = Maps(f=f, ax=(.25, .5, .5, .5))

    Use a 3-digit integer to set the grid-position of the map
    (nrows, ncols, index)

    >>> from matplotlib.gridspec import GridSpec
    >>> m = Maps(ax=221)

    Use a tuple of 3 integers to set the grid-position of the map
    (nrows, ncols, index)

    >>> from matplotlib.gridspec import GridSpec
    >>> m = Maps(ax=(2, 2, 1))

    Put the map at a grid-position of an existing figure

    >>> import matplotlib.pyplot as plt
    >>> f = plt.figure()
    >>> ax = f.add_subplot(211)
    >>> m = Maps(f=f, ax=212)

    Use a subplotspec to set the axis position

    >>> from matplotlib.gridspec import GridSpec
    >>> gs = GridSpec(2,2)
    >>> m = Maps(ax=gs[0,0])

    Use an existing axis to create the Maps-object
    (the associated figure is automatically detected)

    >>> import matplotlib.pyplot as plt
    >>> from eomaps import Maps
    >>> f = plt.figure()
    >>> ax = f.add_subplot(projection=Maps.CRS.Mollweide())
    >>> m = Maps(ax=ax)

    Use Maps-objects as context-manager to close the map and free memory
    once the map is exported.

    >>> import matplotlib
    >>> matplotlib.use("agg") # we can use a non-GUI backend since we only export png's
    >>> from eomaps import Maps
    >>> with Maps() as m:
    >>>     m.add_feature.preset.coastline()
    >>>     m.savefig(...)

    Attributes
    ----------
    CRS : Accessor for available projections (Supercharged version of cartopy.crs)

    CLASSIFIERS : Accessor for available classifiers (provided by mapclassify)

    _companion_widget_key : Keyboard shortcut assigned to show/hide the companion-widget.

    """

    __version__ = __version__

    from_file = from_file
    read_file = read_file

    CRS = ccrs

    _companion_widget_key = "w"

    CLASSIFIERS = SimpleNamespace(**dict(zip(_CLASSIFIERS, _CLASSIFIERS)))

    def __init__(
        self,
        crs=None,
        layer="base",
        f=None,
        ax=None,
        preferred_wms_service="wms",
        **kwargs,
    ):
        # make sure the used layer-name is valid
        layer = self._check_layer_name(layer)

        self._inherit_classification = None

        if isinstance(ax, plt.Axes) and hasattr(ax, "figure"):
            if isinstance(ax.figure, plt.Figure):
                if f is not None:
                    assert (
                        f == ax.figure
                    ), "EOmaps: The provided axis is in a different figure!"

                self._f = ax.figure
        else:
            self._f = f

        self._ax = None
        self._parent = None
        self._BM = None
        self._util = None
        self._children = set()  # weakref.WeakSet()
        self._after_add_child = list()

        self._colorbars = []
        self._coll = None  # slot for the collection created by m.plot_map()

        self._layer = layer

        # check if the self represents a new-layer or an object on an existing layer
        if any(
            i.layer == layer for i in (self.parent, *self.parent._children) if i != self
        ):
            self._is_sublayer = True
        else:
            self._is_sublayer = False

        self._companion_widget = None  # slot for the pyqt widget
        self._cid_companion_key = None  # callback id for the companion-cb
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

        if isinstance(ax, plt.Axes):
            # set the plot_crs only if no explicit axes is provided
            if crs is not None:
                raise AssertionError(
                    "You cannot set the crs if you already provide an explicit axes!"
                )
            if ax.projection == Maps.CRS.PlateCarree():
                self._crs_plot = 4326
            else:
                self._crs_plot = ax.projection
        else:
            if crs is None or crs == Maps.CRS.PlateCarree():
                crs = 4326

            self._crs_plot = crs

        self._crs_plot_cartopy = self._get_cartopy_crs(self._crs_plot)

        # default classify specs
        self.classify_specs = classify_specs(weakref.proxy(self))

        self.data_specs = data_specs(
            weakref.proxy(self),
            x="lon",
            y="lat",
            crs=4326,
        )

        self._layout_editor = None

        self._cb = cb_container(weakref.proxy(self))  # accessor for the callbacks

        self._init_figure(ax=ax, plot_crs=crs, **kwargs)
        if wms_container is not None:
            self._wms_container = wms_container(weakref.proxy(self))
        self._new_layer_from_file = new_layer_from_file(weakref.proxy(self))

        self._shapes = shapes(weakref.proxy(self))
        self._shape = None

        # the radius is estimated when plot_map is called
        self._estimated_radius = None

        # cache commonly used transformers
        self._transf_plot_to_lonlat = Transformer.from_crs(
            self.crs_plot,
            self.get_crs(4326),
            always_xy=True,
        )
        self._transf_lonlat_to_plot = Transformer.from_crs(
            self.get_crs(4326),
            self.crs_plot,
            always_xy=True,
        )

        # a set to hold references to the compass objects
        self._compass = set()

        if not hasattr(self.parent, "_wms_legend"):
            self.parent._wms_legend = dict()

        if not hasattr(self.parent, "_execute_callbacks"):
            self.parent._execute_callbacks = True

        # initialize the shape-drawer
        self._shape_drawer = ShapeDrawer(weakref.proxy(self))

        # initialize the data-manager
        self._data_manager = DataManager(self._proxy(self))
        self._data_plotted = False
        self._set_extent_on_plot = True

        # Make sure the figure-background patch is on an explicit layer
        # This is used to avoid having the background patch on each fetched
        # background while maintaining the capability of restoring it
        if self.f.patch not in self.BM._bg_artists.get("__BG__", []):
            self.BM.add_bg_artist(self.f.patch, layer="__BG__")

        # Treat cartopy geo-spines separately in the blit-manager
        # to avoid issues with overlapping spines that are drawn on each layer
        # if multiple layers of a map are combined.
        # (Note: spines need to be visible on each layer in case the layer
        # is viewed on its own, but overlapping spines cause blurry boundaries)
        # TODO find a better way to deal with this!
        self._handle_spines()

        # a factory to create gridlines
        if self.parent == self:
            self._grid = GridFactory(self.parent)

    def _handle_spines(self):
        spine = self.ax.spines["geo"]
        if spine not in self.BM._bg_artists.get("__SPINES__", []):
            self.BM.add_bg_artist(spine, layer="__SPINES__")

    def __getattribute__(self, key):
        if key == "set_layout":
            raise AttributeError(
                "'Maps' object has no attribute 'set_layout'... "
                "did you mean 'apply_layout'?"
            )
        else:
            return object.__getattribute__(self, key)

    def __enter__(self):
        assert not self._is_sublayer, (
            "EOmaps: using a Maps-object as a context-manager is only possible "
            "if you create a NEW layer (not a Maps-object on an existing layer)!"
        )

        return self

    def __exit__(self, type, value, traceback):
        self.cleanup()
        if self.parent == self:
            plt.close(self.f)
        gc.collect()

    @property
    def layer(self):
        """The layer-name associated with this Maps-object."""
        return self._layer

    @property
    def all(self):
        """
        Get a Maps-object on the "all" layer.

        Use it just as any other Maps-object. (It's the same as `Maps(layer="all")`)

        >>> m.all.cb.click.attach.annotate()

        """
        if not hasattr(self, "_all"):
            self._all = self.new_layer("all")
        return self._all

    @property
    def ax(self):
        """The matplotlib (cartopy) GeoAxes associated with this Maps-object."""
        return self._ax

    @property
    def f(self):
        """The matplotlib Figure associated with this Maps-object."""
        # always return the figure of the parent object
        return self._f

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
        if self._shape is None:
            self._set_default_shape()

        return self._shape

    @property
    @wraps(cb_container)
    def cb(self):
        """Accessor to attach callbacks to the map."""
        return self._cb

    @property
    @wraps(utilities)
    def util(self):
        """Add utilities to the map."""
        if self.parent._util is None:
            self.parent._util = utilities(self.parent)
        return self.parent._util

    @property
    @wraps(ShapeDrawer)
    def draw(self):
        """Draw simple shapes on the map."""
        return self._shape_drawer

    @property
    def BM(self):
        """The Blit-Manager used to dynamically update the plots."""
        m = weakref.proxy(self)
        if self.parent._BM is None:
            self.parent._BM = BlitManager(m)
            self.parent._BM._bg_layer = m.parent.layer
        return self.parent._BM

    @property
    def parent(self):
        """
        The parent-object to which this Maps-object is connected to.

        If None, `self` is returned!
        """
        if self._parent is None:
            self._set_parent()

        return self._parent

    @property
    def _real_self(self):
        # workaround to obtain a non-weak reference for the parent
        # (e.g. self.parent._real_self is a non-weak ref to parent)
        # see https://stackoverflow.com/a/49319989/9703451
        return self

    @property
    def crs_plot(self):
        """The crs used for plotting."""
        return self._crs_plot_cartopy

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

    @property
    @wraps(new_layer_from_file)
    def new_layer_from_file(self):
        """Create a new layer from a file."""
        return self._new_layer_from_file

    def new_map(self, ax=None, keep_on_top=False, **kwargs):
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
            - `matplotilb.gridspec.SubplotSpec`:
                Use the SubplotSpec for initializing the axes.
            - `matplotilb.Axes`:
                Directly use the provided figure and axes instances for plotting.
                NOTE: The axes MUST be a geo-axes with `m.crs_plot` projection!
        keep_on_top : bool
            If True, this axis will be drawn on top of all other maps.
            (same as InsetMaps)
            The default is False.
        preferred_wms_service : str, optional
            Set the preferred way for accessing WebMap services if both WMS and WMTS
            capabilities are possible.
            The default is "wms"
        kwargs :
            additional kwargs are passed to `matplotlib.pyplot.figure()`
            - e.g. figsize=(10,5)

        Returns
        -------
        m: EOmaps.Maps
            The Maps object representing the new map.

        """
        m2 = Maps(f=self.f, ax=ax, **kwargs)

        if np.allclose(self.ax.bbox.bounds, m2.ax.bbox.bounds):
            print(
                "EOmaps: Warning! The new map overlaps exactly with the parent map! "
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
        copy_data_specs=False,
        copy_classify_specs=False,
        copy_shape=True,
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
        copy_data_specs, copy_shape, copy_classify_specs : bool
            Indicator if the corresponding properties should be copied to
            the new layer. By default no settings are copied.

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
        copy : general way for copying Maps objects
        """
        if layer is None:
            layer = copy.deepcopy(self.layer)

        m = self.copy(
            data_specs=copy_data_specs,
            classify_specs=copy_classify_specs,
            shape=copy_shape,
            ax=self.ax,
            layer=layer,
        )
        # make sure the new layer does not attempt to reset the extent if
        # it has already been set on the parent layer
        m._set_extent_on_plot = self._set_extent_on_plot

        # re-initialize all sliders and buttons to include the new layer
        self.util._reinit_widgets()
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
        shape="ellipses",
        indicate_extent=True,
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
        boundary: bool or dict, optional
            - If True: indicate the boundary of the inset-map with default colors
              (e.g.: {"ec":"r", "lw":2})
            - If False: don't add edgecolors to the boundary of the inset-map
            - if dict: use the provided values for "ec" (e.g. edgecolor) and
              "lw" (e.g. linewidth)

            The default is True.
        shape : str, optional
            The shape to use. Can be either "ellipses", "rectangles" or "geod_circles".
            The default is "ellipses".
        indicate_extent : bool or dict, optional

            - If True: add a polygon representing the inset-extent to the parent map.
            - If a dict is provided, it will be used to update the appearance of the
              added polygon (e.g. facecolor, edgecolor, linewidth etc.)

            NOTE: you can also use `m_inset.indicate_inset_extent(...)` to manually
            indicate the inset-shape on arbitrary Maps-objects.

        Returns
        -------
        m : eomaps.Maps
            A eomaps.Maps-object of the inset-map.
            (use it just like any other Maps-object)

        See Also
        --------
        The following additional methods are defined on `_InsetMaps` objects

        m.indicate_inset_extent :
            Plot a polygon representing the extent of the inset map on another Maps
            object.
        m.set_inset_position :
            Set the (center) position and size of the inset-map.

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
        >>> m2.indicate_inset_extent(m, ec="g", fc=(0,1,0,.25))

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
        m2 = _InsetMaps(
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
            shape=shape,
            indicate_extent=indicate_extent,
        )

        return m2

    @property
    @wraps(shapes)
    def set_shape(self):
        """Set the plot-shape."""
        return self._shapes

    def set_data_specs(
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

    set_data = set_data_specs

    @property
    def set_classify(self):
        """Accessor to set the data-classification."""
        assert _register_mapclassify(), (
            "EOmaps: Missing dependency: 'mapclassify' \n ... please install"
            + " (conda install -c conda-forge mapclassify) to use data-classifications."
        )

        s = SimpleNamespace(
            **{
                i: self._get_mcl_subclass(getattr(mapclassify, i))
                for i in mapclassify.CLASSIFIERS
            }
        )

        s.__doc__ = dedent(
            """
            Interface to the classifiers provided by the 'mapclassify' module.

            To set a classification scheme for a given Maps-object, simply use:

            >>> m.set_classify.<SCHEME>(...)

            Where `<SCHEME>` is the name of the desired classification and additional
            parameters are passed in the call. (check docstrings for more info!)


            Note
            ----
            The following calls have the same effect:

            >>> m.set_classify.Quantiles(k=5)
            >>> m.set_classify_specs(scheme="Quantiles", k=5)

            Using `m.set_classify()` is the same as using `m.set_classify_specs()`!
            However, `m.set_classify()` will provide autocompletion and proper
            docstrings once the Maps-object is initialized which greatly enhances
            the usability.

            """
        )

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
        assert _register_mapclassify(), (
            "EOmaps: Missing dependency: 'mapclassify' \n ... please install"
            + " (conda install -c conda-forge mapclassify) to use data-classifications."
        )

        self.classify_specs._set_scheme_and_args(scheme, **kwargs)

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
            print("Centering Map to:\n    ", r["display_name"])

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
        if not hasattr(self, "_crs_cache"):
            self._crs_cache = dict()

        # check for strings first to avoid expensive equality checking for CRS objects!
        if isinstance(crs, str):
            if crs == "in":
                crs = self.data_specs.crs
            elif crs == "out" or crs == "plot":
                crs = self.crs_plot

        h = hash(crs)
        if h in self._crs_cache:
            crs = self._crs_cache[h]
        else:
            crs = CRS.from_user_input(crs)
            self._crs_cache[h] = crs
        return crs

    @wraps(LayoutEditor.get_layout)
    def get_layout(self, *args, **kwargs):
        """Get the current layout."""
        return self.parent._layout_editor.get_layout(*args, **kwargs)

    @wraps(LayoutEditor.apply_layout)
    def apply_layout(self, *args, **kwargs):
        """Apply a given layout."""
        return self.parent._layout_editor.apply_layout(*args, **kwargs)

    def edit_layout(self, filepath=None):
        """
        Activate the "layout-editor" to quickly re-arrange the positions of subplots.

        - This is the same as pressing "alt + l" on the keyboard!
        - To exit the editor, press "escape" or "alt + l" on the keyboard!

        Parameters
        ----------
        filepath : str, pathlib.Path or None, optional
            A path to a file that will be used to store the layout after you exit
            the layout-editor.
            This file can then be used to apply the layout to the map with

            >>> m.apply_layout(filepath=filepath)

            NOTE: The file will be overwritten if it already exists!!
            The default is None.

        """
        self.parent._layout_editor._make_draggable(filepath=filepath)

    @property
    @wraps(NaturalEarth_features)
    def add_feature(self):
        """Add features from NaturalEarth."""
        # lazily initialize NaturalEarth features
        if not hasattr(self, "_add_feature"):
            self._add_feature = NaturalEarth_features(self)
        return self._add_feature

    @contextmanager
    def _disable_autoscale(self, set_extent):
        if set_extent is False:
            init_extent = self.ax.get_extent()

        try:

            yield
        finally:
            if set_extent is False:
                self.ax.set_extent(init_extent)

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
        only_valid=True,
        set_extent=True,
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

            >>> mg = MapsGrid(2, 1, crs=Maps.CRS.Stereographic())
            >>> mg.m_0_0.add_feature.preset.ocean(reproject="gpd")
            >>> mg.m_1_0.add_feature.preset.ocean(reproject="cartopy")

            The default is "gpd".

        verbose : bool, optional
            Indicator if a progressbar should be printed when re-projecting
            geometries with "use_gpd=False".
            The default is False.

        only_valid : bool, optional

            - If True, only valid geometries (e.g. `gdf.is_valid`) are plotted.
            - If False, all geometries are attempted to be plotted
              (this might result in errors for infinite geometries etc.)

            The default is True

        kwargs :
            all remaining kwargs are passed to `geopandas.GeoDataFrame.plot(**kwargs)`

        Returns
        -------
        new_artists : matplotlib.Artist
            The matplotlib-artists added to the plot

        """
        assert _register_geopandas(), (
            "EOmaps: Missing dependency `geopandas`!\n"
            + "please install '(conda install -c conda-forge geopandas)'"
            + "to use `m.add_gdf()`."
        )

        if isinstance(gdf, (str, Path)):
            gdf = gpd.read_file(gdf)

        if val_key is None:
            val_key = kwargs.get("column", None)

        if only_valid:
            gdf = gdf[gdf.is_valid]

        try:
            # explode the GeoDataFrame to avoid picking multi-part geometries
            gdf = gdf.explode(index_parts=False)
        except Exception:
            # geopandas sometimes has problems exploding geometries...
            # if it does not work, just continue with the Multi-geometries!
            print("EOmaps: Exploding geometries did not work!")
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
                # TODO this results in problems and sometimes masks way too much!!
                # select only polygons that actually intersect with the CRS-boundary
                # mask = gdf.buffer(1).intersects(
                #     gpd.GeoDataFrame(
                #         geometry=[self.ax.projection.domain], crs=self.ax.projection
                #     )
                #     .to_crs(gdf.crs)
                #     .geometry[0]
                # )
                # gdf = gdf.copy()[mask]

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
        # plot gdf and identify newly added collections
        # (geopandas always uses collections)
        colls = [id(i) for i in self.ax.collections]
        artists, prefixes = [], []

        # drop all invalid geometries
        if only_valid:
            gdf = gdf[gdf.is_valid]

        with self._disable_autoscale(set_extent):
            for geomtype, geoms in gdf.groupby(gdf.geom_type):
                gdf.plot(ax=self.ax, aspect=self.ax.get_aspect(), **kwargs)
                artists = [i for i in self.ax.collections if id(i) not in colls]
                for i in artists:
                    prefixes.append(
                        f"_{i.__class__.__name__.replace('Collection', '')}"
                    )

        if picker_name is not None:
            if isinstance(pick_method, str):
                picker_cls = _gpd_picker(
                    gdf=gdf, pick_method=pick_method, val_key=val_key
                )
                picker = picker_cls.get_picker()
            elif callable(pick_method):
                picker = pick_method
                picker_cls = None
            else:
                print("EOmaps: I don't know what to do with the provided pick_method")
                return

            if len(artists) > 1:
                warnings.warn(
                    "EOmaps: Multiple geometry types encountered in `m.add_gdf`. "
                    + "The pick containers are re-named to"
                    + f"{[picker_name + prefix for prefix in prefixes]}"
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
                self.BM.add_bg_artist(art, layer)
        return artists

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
            If None, xy must be provided in the coordinate-system of the plot!
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

        Examples
        --------
            >>> m.add_marker(ID=1, buffer=5)
            >>> m.add_marker(ID=1, radius=2, radius_crs=4326, shape="rectangles")
            >>> m.add_marker(xy=(45, 35), xy_crs=4326, radius=20000, shape="geod_circles")
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
                transformer = Transformer.from_crs(
                    self.get_crs(xy_crs),
                    self.crs_plot,
                    always_xy=True,
                )
                # transform coordinates
                xy = transformer.transform(*xy)

        if layer is None:
            layer = self.layer

        # using permanent=None results in permanent makers that  are NOT
        # added to the "m.cb.click.get.permanent_markers" list that is
        # used to manage callback-markers

        permanent = kwargs.pop("permanent", False)

        # add marker
        marker = self.cb.click._cb.mark(
            ID=ID,
            pos=xy,
            radius=radius,
            radius_crs=radius_crs,
            ind=None,
            shape=shape,
            buffer=buffer,
            n=n,
            layer=layer,
            permanent=None,
            **kwargs,
        )

        if permanent is True:
            self.BM.add_bg_artist(marker, layer=layer)
        else:
            self.BM.add_artist(marker, layer=layer)

            self.BM.update()

        return marker

    def add_annotation(
        self,
        ID=None,
        xy=None,
        xy_crs=None,
        text=None,
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
        else:
            val = repeat(None)
            ind = repeat(None)
            ID = repeat(None)

        assert (
            xy is not None
        ), "EOmaps: you must provide either ID or xy to position the annotation!"

        xy = (np.atleast_1d(xy[0]), np.atleast_1d(xy[1]))

        if xy_crs is not None:
            # get coordinate transformation
            transformer = Transformer.from_crs(
                CRS.from_user_input(xy_crs),
                self.crs_plot,
                always_xy=True,
            )
            # transform coordinates
            xy = transformer.transform(*xy)

        kwargs.setdefault("permanent", None)

        if isinstance(text, str) or callable(text):
            text = repeat(text)
        else:
            try:
                iter(text)
            except TypeError:
                text = repeat(text)

        for x, y, texti, vali, indi, IDi in zip(xy[0], xy[1], text, val, ind, ID):

            # add marker
            self.cb.click._cb.annotate(
                ID=IDi,
                pos=(x, y),
                val=vali,
                ind=indi,
                text=texti,
                **kwargs,
            )
        self.BM.update(clear=False)

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
        lon=None,
        lat=None,
        azim=0,
        preset=None,
        scale=None,
        autoscale_fraction=0.25,
        auto_position=(0.75, 0.25),
        scale_props=None,
        patch_props=None,
        label_props=None,
        layer=None,
    ):
        """Add a scalebar to the map."""
        s = ScaleBar(
            m=self,
            preset=preset,
            scale=scale,
            autoscale_fraction=autoscale_fraction,
            auto_position=auto_position,
            scale_props=scale_props,
            patch_props=patch_props,
            label_props=label_props,
            layer=layer,
        )

        if lon is None or lat is None:
            s._auto_position = auto_position
            lon, lat = s._get_autopos(auto_position)
        else:
            # don't auto-reposition if lon/lat has been provided
            s._auto_position = None

        s._add_scalebar(lon, lat, azim)
        s._make_pickable()

        return s

    if wms_container is not None:

        @property
        @wraps(wms_container)
        def add_wms(self):
            """Accessor to attach WebMap services to the map."""
            return self._wms_container

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

            - If a string is provided, it is identified as a matploltib "format-string",
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
            Only relevant for `connect="geod"`! (An empty ist is returned otherwise.)
            A list of the subdivision distances of the line-segments (in meters).
        out_d_tot : list
            Only relevant for `connect="geod"` (An empty ist is returned otherwise.)
            A list of total distances of the line-segments (in meters).

        """
        if layer is None:
            layer = self.layer

        # intermediate and total distances
        out_d_int, out_d_tot = [], []

        if len(xy) <= 1:
            print("you must provide at least 2 points")

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

        t_xy_plot = Transformer.from_crs(
            self.get_crs(xy_crs), self.crs_plot, always_xy=True
        )
        xplot, yplot = t_xy_plot.transform(*zip(*xy))

        if connect == "geod":
            # connect points via geodesic lines
            if xy_crs != 4326:
                t = Transformer.from_crs(
                    self.get_crs(xy_crs), self.get_crs(4326), always_xy=True
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
                    x0, y0, x1, y1, del_s=di, npts=ni, initial_idx=0, terminus_idx=0
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
                from itertools import chain

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
        _ = figax.imshow(im, aspect="equal", zorder=999)

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

    @wraps(ColorBar.__init__)
    def add_colorbar(self, *args, **kwargs):
        """Add a colorbar to the map."""
        if self.coll is None:
            raise AttributeError(
                "EOmaps: You must plot a dataset before " "adding a colorbar!"
            )

        colorbar = ColorBar(
            self,
            *args,
            **kwargs,
        )

        colorbar._plot_histogram()
        colorbar._plot_colorbar()

        self._colorbars.append(colorbar)
        self.BM._refetch_layer(self.layer)
        self.BM._refetch_layer("__SPINES__")

        return colorbar

    @wraps(GridFactory.add_grid)
    def add_gridlines(self, *args, **kwargs):
        """Add gridlines to the Map."""
        return self.parent._grid.add_grid(m=self, *args, **kwargs)

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

    @wraps(GeoAxes.set_extent)
    def set_extent(self, extent, crs=None):
        """Set the extent of the map."""
        # just a wrapper to make sure that previously set extents are not
        # resetted when plotting data!

        # ( e.g. once .set_extent is called .plot_map does NOT set the extent!)
        self.ax.set_extent(extent)
        self._set_extent_on_plot = False

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
        Each call to plot_map will replace the collection used for picking!
        (only the last collection remains interactive on multiple calls to `m.plot_map()`)

        If you need multiple responsive datasets, use a new layer for each dataset!
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
            masked points (arguments are passed to matpltolibs `plt.scatter()`)
            ('s': markersize, 'marker': the shape of the marker, ...)

            The default is False

        Other Parameters
        ----------------
        vmin, vmax : float, optional
            Min- and max. values assigned to the colorbar. The default is None.
        zorder : float
            The zorder of the artist (e.g. the stacking level of overlapping artists)
            The default is 1
        verbose : int
            The print-message level.

            - 0: don't print warning and info messages to the console
            - >= 1: print warnings
            - >= 10: print warnings and info messages

            The default is 1
        kwargs
            kwargs passed to the initialization of the matpltolib collection
            (dependent on the plot-shape) [linewidth, edgecolor, facecolor, ...]

            For "shade_points" or "shade_raster" shapes, kwargs are passed to
            `datashader.mpl_ext.dsshow`

        """
        verbose = kwargs.pop("verbose", 1)
        if verbose >= 1:
            if getattr(self, "coll", None) is not None:
                print(
                    "EOmaps-warning: Calling `m.plot_map()` or "
                    "`m.make_dataset_pickable()` more than once on the "
                    "same Maps-object will override the assigned PICK-dataset!"
                )

        # convert vmin/vmax values to respect the encoding of the data
        vmin = kwargs.get("vmin", None)
        if vmin is not None:
            kwargs["vmin"] = self._encode_values(vmin)
        vmax = kwargs.get("vmax", None)
        if vmax is not None:
            kwargs["vmax"] = self._encode_values(vmax)

        if layer is None:
            layer = self.layer
        else:
            if (verbose > 0) and not isinstance(layer, str):
                print("EOmaps: The layer-name has been converted to a string!")
                layer = str(layer)

        useshape = self.shape  # invoke the setter to set the default shape

        # make sure the colormap is properly set and transparencies are assigned
        cmap = kwargs.setdefault("cmap", "viridis")
        if "alpha" in kwargs and kwargs["alpha"] < 1:
            # get a unique name for the colormap
            cmapname = self._get_alpha_cmap_name(kwargs["alpha"])

            kwargs["cmap"] = cmap_alpha(
                cmap=cmap,
                alpha=kwargs["alpha"],
                name=cmapname,
            )

            plt.colormaps.register(name=cmapname, cmap=kwargs["cmap"])
            if self._companion_widget is not None:
                self._companion_widget.cmapsChanged.emit()
            # remember registered colormaps (to de-register on close)
            self._registered_cmaps.append(cmapname)

        # make sure zorder is set to 1 by default
        # (by default shading would use 0 while ordinary collections use 1)
        kwargs.setdefault("zorder", 1)

        # ---------------------- prepare the data
        if verbose >= 10:
            print("EOmaps: Preparing the data")

        if useshape.name.startswith("shade"):
            # shade shapes use datashader to update the data of the collections!
            self._data_manager.set_props(
                layer=layer,
                assume_sorted=assume_sorted,
                update_coll_on_fetch=False,
                indicate_masked_points=indicate_masked_points,
                dynamic=dynamic,
            )

            self._shade_map(
                layer=layer,
                dynamic=dynamic,
                set_extent=set_extent,
                assume_sorted=assume_sorted,
                **kwargs,
            )
            self.BM._refetch_layer(layer)

        else:
            self._data_manager.set_props(
                layer=layer,
                assume_sorted=assume_sorted,
                update_coll_on_fetch=True,
                indicate_masked_points=indicate_masked_points,
                dynamic=dynamic,
            )

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

            # if dynamic is False:
            #     self.BM._refetch_layer(layer)

        if verbose >= 1:
            if getattr(self, "_data_mask", None) is not None and not np.all(
                self._data_mask
            ):
                print("EOmaps: Warning: some datapoints could not be drawn!")

        self._data_plotted = True

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
            print(
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

        self.tree = searchtree(m=self._proxy(self))
        self.cb.pick._set_artist(art)
        self.cb.pick._init_cbs()
        self.cb._methods.add("pick")

        self._coll_kwargs = dict()
        self._coll_dynamic = True

        # set _data_plotted to True to trigger updates in the data-manager
        self._data_plotted = True

    def _get_combined_layer_name(self, *args):
        if len(args) == 1:
            assert isinstance(
                args[0], str
            ), "EOmaps: Single arguments passed to 'show_layer()', must be strings!"
            return args[0]

        try:
            combnames = []
            for i in args:
                if isinstance(i, str):
                    combnames.append(i)
                elif isinstance(i, (list, tuple)):
                    assert (
                        len(i) == 2 and isinstance(i[0], str) and i[1] > 0 and i[1] < 1
                    ), (
                        f"EOmaps: unable to identify the layer-assignment: {i} .\n"
                        "You can provide either a single layer-name as string, a list "
                        "of layer-names or a list of tuples of the form: "
                        "(< layer-name (str) >, < layer-transparency [0-1] > )"
                    )
                    combnames.append(i[0] + "{" + str(i[1]) + "}")
                else:
                    raise TypeError(
                        f"EOmaps: unable to identify the layer-assignment: {i} .\n"
                        "You can provide either a single layer-name as string, a list "
                        "of layer-names or a list of tuples of the form: "
                        "(< layer-name (str) >, < layer-transparency [0-1] > )"
                    )
            return "|".join(combnames)
        except Exception:
            raise TypeError(f"EOmaps: Unable to combine the layer-names {args}")

    def show_layer(self, *args):
        """
        Show a single layer or (transparently) overlay multiple selected layers.

        Parameters
        ----------
        args : str, tuple

            - if str: The name of the layer to show.
            - if tuple: A combination of a layer-name and a transparency assignment
              ( < layer name >, < transparency [0-1] > )

        Examples
        --------
        Show a **single layer** by providing the name of the layer as string:

        >>> m.show_layer("A")

        To show **multiple layers**, use one of the following options:

        Provide multiple layer-names (stacking is done from left to right), e.g.:

        >>> m.show_layer("A", "B", "C")

        Provide the combined layer-name, e.g.:

        >>> m.show_layer("A|B|C")

        To **transparently overlay multiple layers**, use one of the following options:

        Provide tuples of layer-names and transparency-assignments, e.g.:

        >>> m.show_layer("A", ("B", 0.5), ("C", 0.25))

        Provide the combined layer-name, e.g.:

        >>> m.show_layer("A|B{0.5}|C{0.25}")

        See Also
        --------
        - Maps.util.layer_selector
        - Maps.util.layer_slider

        """
        name = self._get_combined_layer_name(*args)

        layers = self._get_layers()

        if not isinstance(name, str):
            print("EOmaps: All layer-names are converted to strings!")
            name = str(name)

        if "|" in name:
            # take special care of "_" to allow 'private' (e.g. hidden) multi-layers
            names = [i.strip() for i in name.split("|") if i != "_"]
        else:
            names = [name]

        for i in names:
            # ignore non-existing private layers
            if i.startswith("__"):
                continue

            if "{" in i and i.endswith("}"):
                i = i.split("{")[0]  # strip off transparency assignments

            if i not in layers:
                lstr = " - " + "\n - ".join(map(str, layers))

                print(
                    f"EOmaps: The layer '{i}' does not exist...\n"
                    + f"Use one of: \n{lstr}"
                )
                return

        # invoke the bg_layer setter of the blit-manager
        self.BM.bg_layer = name
        self.BM.update()

    def show(self):
        """
        Make the layer of this `Maps`-object visible.

        This is just a shortcut for `m.show_layer(m.layer)`

        If matploltib is used in non-interactive mode, (e.g. `plt.ioff()`)
        `plt.show()` is called as well!
        """
        self.show_layer(self.layer)

        if not plt.isinteractive():
            plt.show()

    def snapshot(self, clear=False, layer=None):
        """
        Print a static image of the figure to the active IPython display.

        This is useful if you want to print a snapshot of the current state of the map
        to the active Jupyter Notebook cell or the currently active IPython console
        while using a backend that creates popup-plots (e.g. `qt` or `tkinter`)

        ONLY use this if you work in an interactive IPython terminal, a Jupyter
        Notebook or a Jupyter Lab environment!

        Parameters
        ----------
        clear: bool
            Indicator if the current cell-output should be cleared prior
            to showing the snapshot or not. The default is False

        Examples
        --------
        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>> m.snapshot(clear=True)

        """
        from PIL import Image
        from IPython.display import display

        # hide companion-widget indicator
        self._indicate_companion_map(False)

        sn = self._get_snapshot(layer=layer)

        display(Image.fromarray(sn, "RGBA"), display_id=True, clear=clear)

    @wraps(plt.Figure.text)
    def text(self, *args, **kwargs):
        """Add text to the map."""
        kwargs.setdefault("animated", True)
        kwargs.setdefault("horizontalalignment", "center")
        kwargs.setdefault("verticalalignment", "center")

        a = self.f.text(*args, **kwargs)
        self.BM.add_artist(a)

        return a

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
    @wraps(plt.savefig)
    def savefig(self, *args, refetch_wms=False, **kwargs):
        """Save the figure."""
        with ExitStack() as stack:
            if refetch_wms is False:
                if _cx_refetch_wms_on_size_change is not None:
                    stack.enter_context(_cx_refetch_wms_on_size_change(refetch_wms))

                # don't clear on layer-changes
                stack.enter_context(self.BM._cx_dont_clear_on_layer_change())

            # hide companion-widget indicator
            self._indicate_companion_map(False)

            dpi = kwargs.get("dpi", None)

            # add the figure background patch as the bottom layer
            transparent = kwargs.get("transparent", False)
            if transparent is False:
                initial_layer = self.BM.bg_layer
                showlayer_name = self.BM._get_showlayer_name(initial_layer)
                layer_with_bg = "|".join(["__BG__", showlayer_name])
                self.show_layer(layer_with_bg)

            redraw = False
            if dpi is not None and dpi != self.f.dpi:
                redraw = True

                # clear all cached background layers before saving to make sure they
                # are re-drawn with the correct dpi-settings
                self.BM._refetch_bg = True

                # set the shading-axis-size to reflect the used dpi setting
                self._update_shade_axis_size(dpi=dpi)

            self.f.savefig(*args, **kwargs)

        if redraw is True:
            # reset the shading-axis-size to the used figure dpi
            self._update_shade_axis_size()
            # redraw after the save to ensure that backgrounds are correctly cached
            self.redraw()

        # restore the previous layer
        if transparent is False:
            self.BM._refetch_layer(layer_with_bg)
            self.show_layer(initial_layer)
            self.BM.on_draw(None)

    def fetch_layers(self, layers=None, verbose=True):
        """
        Fetch (and cache) the layers of a map.

        This is particularly useful if you want to use sliders or buttons to quickly
        switch between the layers (e.g. once the backgrounds are cached, switching
        layers will be fast).

        Note: After zooming or re-sizing the map, the cache is cleared and
        you need to call this function again.

        Parameters
        ----------
        layers : list or None, optional
            A list of layer-names that should be fetched.
            If None, all layers (except the "all" layer) are fetched.
            The default is None.
        verbose : bool
            Indicator if status-messages should be printed or not.
            The default is True.

        See Also
        --------
        m.cb.keypress.attach.fetch_layers : use a keypress callback to fetch layers

        """
        active_layer = self.BM._bg_layer
        all_layers = self._get_layers()

        if layers is None:
            layers = all_layers
            if "all" in layers:
                layers.remove("all")  # don't explicitly fetch the "all" layer
        else:
            if not set(layers).issubset(all_layers):
                raise AssertionError(
                    "EOmaps: Unable to fetch the following layers:\n - "
                    + "\n - ".join(set(layers).difference(all_layers))
                )

        nlayers = len(layers)
        assert nlayers > 0, "EOmaps: There are no layers to fetch."

        for i, l in enumerate(layers):
            if verbose:
                print("EOmaps: fetching layer", f"{i + 1}/{nlayers}:", l)
            self.show_layer(l)

        self.show_layer(active_layer)
        self.BM.update()

    def join_limits(self, *args):
        """
        Join the x- and y- limits of the axes (e.g. on zoom).

        Parameters
        ----------
        *args :
            the axes to join.
        """
        for m in args:
            if m is not self:
                self._join_axis_limits(weakref.proxy(m))

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
            copy_cls.set_data_specs(
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
        assert _register_geopandas(), (
            "EOmaps: Missing dependency `geopandas`!\n"
            + "please install '(conda install -c conda-forge geopandas)'"
            + "to use `m.indicate_extent()`."
        )

        gdf = self._make_rect_poly(x0, y0, x1, y1, self.get_crs(crs), npts)
        self.add_gdf(gdf, **kwargs)

    def redraw(self, *args):
        """
        Force a re-draw of cached background layers.

        - Use this at the very end of your code to trigger a final re-draw
          to make sure artists not managed by EOmaps are properly drawn!

        Note
        ----
        Don't use this to interactively update artists on a map!
        since it will trigger a re-draw background-layers!

        To dynamically re-draw an artist whenever you interact with the map, use:

        >>> m.BM.add_artist(artist)

        To make an artist temporary (e.g. remove it on the next event), use
        one of :

        >>> m.cb.click.add_temporary_artist(artist)
        >>> m.cb.pick.add_temporary_artist(artist)
        >>> m.cb.keypress.add_temporary_artist(artist)
        >>> m.cb.move.add_temporary_artist(artist)

        Parameters
        ----------
        *args : str
            Positional arguments provided to redraw are identified as layer-names
            that should be re-drawn. If no arguments are provided, all layers
            are re-drawn!

        """
        if len(args) == 0:
            # in case no argument is provided, force a complete re-draw of
            # all layers (and datasets) of the map
            self.BM._refetch_bg = True
            self._data_manager.last_extent = None
        else:
            # only re-fetch the required layers
            for l in args:
                self.BM._refetch_layer(l)

        self.f.canvas.draw_idle()

    @wraps(GridSpec.update)
    def subplots_adjust(self, **kwargs):
        """Adjust the margins of subplots."""
        self.parent._gridspec.update(**kwargs)
        # after changing margins etc. a redraw is required
        # to fetch the updated background!

        self.redraw()

    def on_layer_activation(self, func, persistent=False, **kwargs):
        """
        Attach a callback that is executed if the associated layer is activated.

        Useful to "lazily" populate layers with features that are expensive to
        create (e.g. fetching data from files etc.).

        Parameters
        ----------
        func : callable
            The callable to use.
            The call-signature is:

            >>> def func(m, **kwargs):
            >>>    # m... the Maps-object used for calling this function

        persistent : bool, optional
            Indicator if the function should be called only once (False) or if it
            should be called each time the layer is activated (True).
            The default is False.
        kwargs :
            Additional keyword-arguments passed to the call of the function.

        See Also
        --------
        m.layer : The layer-name associated with the Maps-object
        m.fetch_layers() : Fetch and cache all layers of the map

        Examples
        --------
        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>>
        >>> def f(m, ocean_color, coastline_color):
        >>>     print(f"EOmaps: creating features for the layer {m.layer}")
        >>>     m.add_feature.preset.coastline(ec=coastline_color)
        >>>     m.add_feature.preset.ocean(fc=ocean_color)
        >>>
        >>> # create a new (initially empty) layer "ocean"
        >>> m2 = m.new_layer("ocean")
        >>> # add features to the layer only if it is activated
        >>> m2.on_layer_activation(f, ocean_color="b", coastline_color="r")
        >>> s = m.util.layer_selector()

        """

        def cb(m, layer):
            func(m=m, **kwargs)

        self.BM.on_layer(func=cb, layer=self.layer, persistent=persistent, m=self)

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
        # disconnect callback on xlim-change (only relevant for parent)
        if not self._is_sublayer:
            try:
                if hasattr(self, "_cid_xlim"):
                    self.ax.callbacks.disconnect(self._cid_xlim)
                    del self._cid_xlim
            except Exception:
                print("EOmaps-cleanup: Problem while clearing xlim-cid")

        # clear data-specs and all cached properties of the data
        try:
            self._coll = None
            self._data_manager.cleanup()

            if hasattr(self, "tree"):
                del self.tree
            self.data_specs.delete()
        except Exception:
            print("EOmaps-cleanup: Problem while clearing data specs")

        # disconnect all click, pick and keypress callbacks
        try:
            self.cb._reset_cids()
            # cleanup callback-containers
            self.cb._clear_callbacks()
        except Exception:
            print("EOmaps-cleanup: Problem while clearing callbacks")

        # cleanup all artists and cached background-layers from the blit-manager
        if not self._is_sublayer:
            self.BM.cleanup_layer(self.layer)

        # remove the child from the parent Maps object
        if self in self.parent._children:
            self.parent._children.remove(self)

        # activate the base-layer (and re-initialize widgets)
        try:
            if self.parent != self:
                self.show_layer(self.parent.layer)
        except Exception:
            print("EOmaps-cleanup: Problem while updating map to reflect changes")

    def _check_layer_name(self, layer):
        if not isinstance(layer, str):
            print("EOmaps: All layer-names are converted to strings!")
            layer = str(layer)

        if layer.startswith("__") and not layer.startswith("__inset_"):
            raise TypeError(
                "EOmaps: Layer-names starting with '__' are reserved "
                "for internal use and cannot be used as Maps-layer-names!"
            )

        reserved_symbs = {
            # "|": (
            #     "It is used as a separation-character to combine multiple "
            #     "layers (e.g. m.show_layer('A|B') will overlay the layer 'B' "
            #     "on top of 'A'."
            # ),
            "{": (
                "It is used to specify transparency when combining multiple "
                "layers (e.g. m.show_layer('A|B{0.5}') will overlay the layer "
                "'B' with 50% transparency on top of the layer 'A'."
            ),
        }

        reserved_symbs["}"] = reserved_symbs["{"]

        for symb, explanation in reserved_symbs.items():
            if symb in layer:
                raise TypeError(
                    f"EOmaps: The symbol '{symb}' is not allowed in layer-names!\n"
                    + explanation
                )

        return layer

    def _init_figure(self, ax=None, plot_crs=None, **kwargs):
        # do this on any new figure since "%matpltolib inline" tries to re-activate
        # interactive mode all the time!

        _handle_backends()

        if self.parent.f is None:
            self._f = plt.figure(**kwargs)

            # make sure we keep a "real" reference otherwise overwriting the
            # variable of the parent Maps-object while keeping the figure open
            # causes all weakrefs to be garbage-collected!
            self.parent.f._EOmaps_parent = self.parent._real_self
            newfig = True
        else:
            newfig = False
            if not hasattr(self.parent.f, "_EOmaps_parent"):
                self.parent.f._EOmaps_parent = self.parent._real_self
            self.parent._add_child(self)

        if isinstance(ax, plt.Axes):
            # check if the axis is already used by another maps-object
            if ax not in (i.ax for i in (self.parent, *self.parent._children)):
                newax = True
            else:
                newax = False
        else:
            newax = True
            # create a new axis
            if ax is None:
                gs = GridSpec(
                    nrows=1, ncols=1, left=0.01, right=0.99, bottom=0.05, top=0.95
                )
                gsspec = [gs[:]]
            elif isinstance(ax, SubplotSpec):
                gsspec = [ax]
            elif isinstance(ax, (list, tuple)) and len(ax) == 4:
                # absolute position
                l, b, w, h = ax

                gs = GridSpec(
                    nrows=1, ncols=1, left=l, bottom=b, right=l + w, top=b + h
                )
                gsspec = [gs[:]]
            elif isinstance(ax, int) and len(str(ax)) == 3:
                gsspec = [ax]
            elif isinstance(ax, tuple) and len(ax) == 3:
                gsspec = ax
            else:
                raise TypeError("EOmaps: The provided value for 'ax' is invalid.")

            projection = self._get_cartopy_crs(plot_crs)

            ax = self.f.add_subplot(
                *gsspec,
                projection=projection,
                aspect="equal",
                adjustable="box",
                label=self._get_ax_label(),
            )

        self._ax = ax
        self._gridspec = ax.get_gridspec()

        # add support for "frameon" kwarg
        if kwargs.get("frameon", True) is False:
            self.ax.spines["geo"].set_edgecolor("none")

        # initialize the callbacks
        self.cb._init_cbs()

        if newax:  # only if a new axis has been created

            # explicitly set initial limits to global to avoid issues if NE-features
            # are added (and clipped) before actual limits are set
            self.ax.set_global()

            # do this only on xlims and NOT on ylims to avoid recursion
            # (plot aspect ensures that y changes if x changes)
            self._cid_xlim = self.ax.callbacks.connect(
                "xlim_changed", self._on_xlims_change
            )
            self._cid_xlim = self.ax.callbacks.connect(
                "ylim_changed", self._on_ylims_change
            )

            if self._cid_companion_key is None:
                # attach a callback to show/hide the window with the "w" key

                # NOTE the companion-widget is ONLY initialized on Maps-objects that
                # create NEW axes. This is required to make sure that any additional
                # Maps-object on the same axes will then always use the same widget.
                # (otherwise each layer would get its own widget)
                self._cid_companion_key = self.f.canvas.mpl_connect(
                    "key_press_event", self._open_companion_widget_cb
                )

        if self.parent == self:  # use == instead of "is" since the parent is a proxy!
            # only attach resize- and close-callbacks if we initialize a parent
            # Maps-object
            # attach a callback that is executed when the figure is closed
            self._cid_onclose = self.f.canvas.mpl_connect("close_event", self._on_close)
            # attach a callback that is executed if the figure canvas is resized
            self._cid_resize = self.f.canvas.mpl_connect(
                "resize_event", self._on_resize
            )

        # if we haven't attached an axpicker so far, do it!
        if self.parent._layout_editor is None:
            self.parent._layout_editor = LayoutEditor(self.parent, modifier="alt+l")

        if newfig:
            # we only need to call show if a new figure has been created!
            if (
                plt.isinteractive()
                or plt.get_backend() == "module://ipympl.backend_nbagg"
            ):
                # make sure to call show only if we use an interactive backend...
                # or within the ipympl backend (otherwise it will block subsequent code!)
                plt.show()

    def _get_ax_label(self):
        return "map"

    def _on_xlims_change(self, *args, **kwargs):
        self.BM._refetch_bg = True

    def _on_ylims_change(self, *args, **kwargs):
        self.BM._refetch_bg = True

    def _on_resize(self, event):
        # make sure the background is re-fetched if the canvas has been resized
        # (required for peeking layers after the canvas has been resized
        #  and for webagg and nbagg backends to correctly re-draw the layer)
        self.BM._refetch_bg = True
        self.BM._refetch_blank = True

        # update the figure dimensions in case shading is used
        self._update_shade_axis_size()

    def _update_shade_axis_size(self, dpi=None):

        # set the axis-size that is used to determine the number of pixels used
        # when using "shade" shapes

        if self.coll is not None and self.shape.name.startswith("shade_"):
            if dpi is None:
                self.coll.plot_width = int(self.ax.bbox.width)
                self.coll.plot_height = int(self.ax.bbox.height)
            else:
                self.coll.plot_width = int(self.ax.bbox.width / self.f.dpi * dpi)
                self.coll.plot_height = int(self.ax.bbox.height / self.f.dpi * dpi)

    def _on_close(self, event):
        # reset attributes that might use up a lot of memory when the figure is closed
        for m in [self.parent, *self.parent._children]:
            if hasattr(m.f, "_EOmaps_parent"):
                m.f._EOmaps_parent = None

            m.cleanup()

        # close the pyqt widget if there is one
        if self._companion_widget is not None:
            self._companion_widget.close()

        # de-register colormaps
        for cmap in self._registered_cmaps:
            plt.colormaps.unregister(cmap)

        # run garbage-collection to immediately free memory
        gc.collect

    def _join_axis_limits(self, m):
        if self.ax.projection != m.ax.projection:
            warnings.warn(
                "EOmaps: joining axis-limits is only possible for "
                + "axes with the same projection!"
            )
            return

        self.ax._EOmaps_joined_action = False
        m.ax._EOmaps_joined_action = False

        # Declare and register callbacks
        def child_xlims_change(event_ax):
            if event_ax._EOmaps_joined_action is not m.ax:
                m.ax._EOmaps_joined_action = event_ax
                m.ax.set_xlim(event_ax.get_xlim())
            event_ax._EOmaps_joined_action = False

        def child_ylims_change(event_ax):
            if event_ax._EOmaps_joined_action is not m.ax:
                m.ax._EOmaps_joined_action = event_ax
                m.ax.set_ylim(event_ax.get_ylim())
            event_ax._EOmaps_joined_action = False

        def parent_xlims_change(event_ax):
            if event_ax._EOmaps_joined_action is not self.ax:
                self.ax._EOmaps_joined_action = event_ax
                self.ax.set_xlim(event_ax.get_xlim())
            event_ax._EOmaps_joined_action = False

        def parent_ylims_change(event_ax):
            if event_ax._EOmaps_joined_action is not self.ax:
                self.ax._EOmaps_joined_action = event_ax
                self.ax.set_ylim(event_ax.get_ylim())

            event_ax._EOmaps_joined_action = False

        self.ax.callbacks.connect("xlim_changed", child_xlims_change)
        self.ax.callbacks.connect("ylim_changed", child_ylims_change)

        m.ax.callbacks.connect("xlim_changed", parent_xlims_change)
        m.ax.callbacks.connect("ylim_changed", parent_ylims_change)

    def _add_child(self, m):
        self.parent._children.add(m)

        # execute hooks to notify the gui that a new child was added
        for action in self._after_add_child:
            try:
                action()
            except Exception as ex:
                print("EOmaps: Problem executing 'on_add_child' action:", ex)

    def _identify_data(self, data=None, x=None, y=None, parameter=None):
        # identify the way how the data has been provided and convert to the internal
        # structure

        if data is None:
            data = self.data_specs.data
        if x is None:
            x = self.data_specs.x
        if y is None:
            y = self.data_specs.y
        if parameter is None:
            parameter = self.data_specs.parameter

        # check other types before pandas to avoid unnecessary import
        if data is not None and not isinstance(data, (list, tuple, np.ndarray)):
            if _register_pandas() and isinstance(data, pd.DataFrame):

                if parameter is not None:
                    # get the data-values
                    z_data = data[parameter].values
                else:
                    z_data = np.repeat(np.nan, len(data))

                # get the index-values
                ids = data.index.values

                if isinstance(x, str) and isinstance(y, str):
                    # get the data-coordinates
                    xorig = data[x].values
                    yorig = data[y].values
                else:
                    assert isinstance(x, (list, np.ndarray, pd.Series)), (
                        "'x' must be either a column-name, or explicit values "
                        " specified as a list, a numpy-array or a pandas"
                        + f" Series object if you provide the data as '{type(data)}'"
                    )
                    assert isinstance(y, (list, np.ndarray, pd.Series)), (
                        "'y' must be either a column-name, or explicit values "
                        " specified as a list, a numpy-array or a pandas"
                        + f" Series object if you provide the data as '{type(data)}'"
                    )

                    xorig = np.asanyarray(x)
                    yorig = np.asanyarray(y)

                return z_data, xorig, yorig, ids, parameter

        # identify all other types except for pandas.DataFrames

        # lazily check if pandas was used
        pandas_series_data = False
        for iname, i in zip(("x", "y", "data"), (x, y, data)):
            if iname == "data" and i is None:
                # allow empty datasets
                continue

            if not isinstance(i, (list, tuple, np.ndarray)):
                if _register_pandas() and not isinstance(i, pd.Series):
                    raise AssertionError(
                        f"{iname} values must be a list, numpy-array or pandas.Series"
                    )
                else:
                    if iname == "data":
                        pandas_series_data = True

        # set coordinates by extent

        if isinstance(x, tuple) and isinstance(y, tuple):
            assert data is not None, (
                "EOmaps: If x- and y are provided as tuples, the data must be a 2D list "
                "or numpy-array!"
            )

            shape = np.shape(data)
            assert len(shape) == 2, (
                "EOmaps: If x- and y are provided as tuples, the data must be a 2D list "
                "or numpy-array!"
            )

            # get the data-coordinates
            xorig = np.linspace(*x, shape[0])
            yorig = np.linspace(*y, shape[1])

        else:
            # get the data-coordinates
            xorig = np.asanyarray(x)
            yorig = np.asanyarray(y)

        if data is not None:
            # get the data-values
            z_data = np.asanyarray(data)
        else:
            if xorig.shape == yorig.shape:
                z_data = np.full(xorig.shape, np.nan)
            elif (
                (xorig.shape != yorig.shape)
                and (len(xorig.shape) == 1)
                and (len(yorig.shape) == 1)
            ):
                z_data = np.full((xorig.shape[0], yorig.shape[0]), np.nan)

        # get the index-values
        if pandas_series_data is True:
            # use actual index values if pd.Series was passed as "data"
            ids = data.index.values
        else:
            # use numeric index values for all other types
            ids = range(z_data.size)

        if len(xorig.shape) == 1 and len(yorig.shape) == 1 and len(z_data.shape) == 2:
            assert (
                z_data.shape[0] == xorig.shape[0] and z_data.shape[0] == xorig.shape[0]
            ), (
                "The shape of the coordinate-arrays is not valid! "
                f"data={z_data.shape} expects x={(z_data.shape[0],)}, "
                f"y={(z_data.shape[1],)}, but the provided shapes are:"
                f"x={xorig.shape}, y={yorig.shape}"
            )

        if len(xorig.shape) == len(z_data.shape):
            assert xorig.shape == z_data.shape and yorig.shape == z_data.shape, (
                f"EOmaps: The data-shape {z_data.shape} and coordinate-shape "
                + f"x={xorig.shape}, y={yorig.shape} do not match!"
            )

        return z_data, xorig, yorig, ids, parameter

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
            self.set_data_specs = lambda *args, **kwargs: (
                "EOmaps: You cannot set data_specs for a Maps object that "
                "inherits data!"
            )
            self.set_data = self.set_data_specs

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
            assert _register_mapclassify(), (
                "EOmaps: Missing dependency: 'mapclassify' \n ... please install "
                "(conda install -c conda-forge mapclassify) to use classifications."
            )

            classified = True
            if self.classify_specs.scheme == "UserDefined":
                bins = self.classify_specs.bins
            else:
                mapc = getattr(mapclassify, classify_specs.scheme)(
                    z_data[~np.isnan(z_data)], **classify_specs
                )
                bins = mapc.bins
            if vmin < min(bins):
                bins = [vmin, *bins]

            if vmax > max(bins):
                bins[np.argmax(bins)] = vmax

            cbcmap = cmap
            norm = mpl.colors.BoundaryNorm(bins, cmap.N)

            if self._companion_widget is not None:
                self._companion_widget.cmapsChanged.emit()

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
            norm = mpl.colors.Normalize(vmin, vmax)

        return cbcmap, norm, bins, classified

    def _set_parent(self):
        """Identify the parent object."""
        assert self._parent is None, "EOmaps: There is already a parent Maps object!"
        # check if the figure to which the Maps-object is added already has a parent
        parent = None
        if getattr(self._f, "_EOmaps_parent", False):
            parent = self._proxy(self._f._EOmaps_parent)

        if parent is None:
            parent = self

        self._parent = self._proxy(parent)

        if parent not in [self, None]:
            # add the child to the topmost parent-object
            self.parent._add_child(self)

    def _set_default_shape(self):
        if self.data is not None:
            size = np.size(self.data)

            if len(np.shape(self.data)) == 2 and size > 200_000:
                if size > 5e6 and _register_datashader():
                    # only try to use datashader for very large 2D datasets
                    self.set_shape.shade_raster()
                else:
                    self.set_shape.raster()
            else:
                if size > 500_000:
                    if _register_datashader():
                        # shade_points should work for any dataset
                        self.set_shape.shade_points()
                    else:
                        print(
                            "EOmaps-Warning: Attempting to plot a large dataset "
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
            if ID in ids:
                return [ID], [ID]
            else:
                return None, None
        elif isinstance(ids, (list, np.ndarray)):
            mask = np.isin(ids, ID)
            ind = np.where(mask)[0]

        return mask, ind

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
        assert _register_geopandas(), (
            "EOmaps: Missing dependency `geopandas`!\n"
            + "please install '(conda install -c conda-forge geopandas)'"
            + "to use `m.add_gdf()`."
        )

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
            x0, x1, y0, y1 = self.ax.get_extent()
            clip_shp = self._make_rect_poly(x0, y0, x1, y1, self.crs_plot).to_crs(
                gdf.crs
            )
        elif how == "crs_bounds" or how == "crs_bounds_invert":
            x0, x1, y0, y1 = self.ax.get_extent()
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

    def _get_mcl_subclass(self, s):
        # get a subclass that inherits the docstring from the corresponding
        # mapclassify classifier

        class scheme:
            @wraps(s)
            def __init__(_, *args, **kwargs):
                pass

            def __new__(cls, **kwargs):
                if "y" in kwargs:
                    print(
                        "EOmaps: The values (e.g. the 'y' parameter) are "
                        + "assigned internally... only provide additional "
                        + "parameters that specify the classification scheme!"
                    )
                    kwargs.pop("y")

                self.classify_specs._set_scheme_and_args(scheme=s.__name__, **kwargs)

        scheme.__doc__ = s.__doc__
        return scheme

    def _plot_map(
        self,
        layer=None,
        dynamic=False,
        set_extent=True,
        assume_sorted=True,
        **kwargs,
    ):

        cmap = kwargs.pop("cmap", "viridis")
        vmin = kwargs.pop("vmin", None)
        vmax = kwargs.pop("vmax", None)

        for key in ("array", "norm"):
            assert (
                key not in kwargs
            ), f"The key '{key}' is assigned internally by EOmaps!"

        try:
            if vmin is None and self.data is not None:
                vmin = np.nanmin(self._data_manager.z_data)
            if vmax is None and self.data is not None:
                vmax = np.nanmax(self._data_manager.z_data)

            # clip the data to properly account for vmin and vmax
            # (do this only if we don't intend to use the full dataset!)
            # if vmin or vmax:
            #     props["z_data"] = props["z_data"].clip(vmin, vmax)

            # ---------------------- classify the data
            cbcmap, norm, bins, classified = self._classify_data(
                vmin=vmin,
                vmax=vmax,
                cmap=cmap,
                classify_specs=self.classify_specs,
            )

            # TODO remove duplicated attributes!!
            self.classify_specs._cbcmap = cbcmap
            self.classify_specs._norm = norm
            self.classify_specs._bins = bins
            self.classify_specs._classified = classified

            self._cbcmap = cbcmap
            self._norm = norm
            self._bins = bins
            self._classified = classified

            self._vmin = vmin
            self._vmax = vmax
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

    def _sel_c_transp(self, c):
        return self._data_manager._select_vals(
            c.T if self._data_manager._z_transposed else c
        )

    def _handle_explicit_colors(self, color):
        if isinstance(color, (int, float, str, np.number)):
            # if a scalar is provided, broadcast it
            pass
        elif isinstance(color, (list, tuple)) and len(color) in [3, 4]:
            if all(map(lambda i: isinstance(i, (int, float, np.number)), color)):
                # check if a tuple of numbers is provided, and if so broadcast
                # it as a rgb or rgba tuple
                pass
            elif all(map(lambda i: isinstance(i, (list, np.ndarray)), color)):
                # check if a tuple of lists or arrays is provided, and if so,
                # broadcast them as RGB arrays
                color = self._sel_c_transp(
                    np.rec.fromarrays(np.broadcast_arrays(*color))
                )
        elif isinstance(color, np.ndarray) and (color.shape[-1] in [3, 4]):
            color = self._sel_c_transp(np.rec.fromarrays(color.T))
        elif isinstance(color, np.ndarray) and (color.shape[-1] in [3, 4]):
            color = self._sel_c_transp(np.rec.fromarrays(color.T))
        else:
            # still use np.asanyarray in here in case lists are provided
            color = self._sel_c_transp(np.asanyarray(color).reshape(self._zshape))

        return color

    def _get_coll(self, props, **kwargs):
        # handle selection of explicitly provided facecolors
        # (e.g. for rgb composits)

        # allow only one of the synonyms "color", "fc" and "facecolor"
        if (
            np.count_nonzero(
                [kwargs.get(i, None) is not None for i in ["color", "fc", "facecolor"]]
            )
            > 1
        ):
            raise TypeError(
                "EOmaps: only one of 'color', 'facecolor' or 'fc' " "can be specified!"
            )

        explicit_fc = False
        for key in ("color", "facecolor", "fc"):
            if kwargs.get(key, None) is not None:
                explicit_fc = True
                kwargs[key] = self._handle_explicit_colors(kwargs[key])

        # don't pass the array if explicit facecolors are set
        if explicit_fc:
            args = dict(array=None, cmap=None, norm=None, **kwargs)
        else:
            args = dict(
                array=props["z_data"], cmap=self._cbcmap, norm=self._norm, **kwargs
            )

        if self.shape.name in ["raster"]:
            # if input-data is 1D, try to convert data to 2D (required for raster)
            # TODO make an explicit data-conversion function for 2D-only shapes
            if len(self._xshape) == 2 and len(self._yshape) == 2:
                coll = self.shape.get_coll(props["xorig"], props["yorig"], "in", **args)
            elif _register_pandas():
                if (
                    (len(self._xshape) == 1)
                    and (len(self._yshape) == 1)
                    and (len(self._zshape) == 1)
                    and (props["x0"].size == props["y0"].size)
                    and (props["x0"].size == props["z_data"].size)
                ):

                    df = (
                        pd.DataFrame(
                            dict(
                                x=props["x0"].ravel(),
                                y=props["y0"].ravel(),
                                val=props["z_data"].ravel(),
                            ),
                            copy=False,
                        ).set_index(["x", "y"])
                    )["val"].unstack("y")

                    xg, yg = np.meshgrid(df.index.values, df.columns.values)

                    if args["array"] is not None:
                        args["array"] = df.values.T

                    coll = self.shape.get_coll(xg, yg, "out", **args)
        else:
            # convert to 1D for further processing
            if args["array"] is not None:
                args["array"] = args["array"].ravel()

            coll = self.shape.get_coll(
                props["x0"].ravel(), props["y0"].ravel(), "out", **args
            )
        return coll

    def _shade_map(
        self,
        verbose=0,
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
        assert _register_datashader(), (
            "EOmaps: Missing dependency: 'datashader' \n ... please install"
            + " (conda install -c conda-forge datashader) to use the plot-shapes "
            + "'shade_points' and 'shade_raster'"
        )

        cmap = kwargs.pop("cmap", "viridis")
        vmin = kwargs.pop("vmin", None)
        vmax = kwargs.pop("vmin", None)

        # remove previously fetched backgrounds for the used layer
        if dynamic is False:
            self.BM._refetch_layer(layer)
            # del self.BM._bg_layers[layer]
            # self.BM._refetch_bg = True

        # get the name of the used aggretation reduction
        aggname = self.shape.aggregator.__class__.__name__
        if aggname in ["first", "last", "max", "min", "mean", "mode"]:
            # set vmin/vmax in case the aggregation still represents data-values
            if vmin is None:
                vmin = np.nanmin(self._data_manager.z_data)
            if vmax is None:
                vmax = np.nanmax(self._data_manager.z_data)
        else:
            # set vmin/vmax for aggregations that do NOT represent data values

            # allow vmin/vmax = None (e.g. autoscaling)
            if "count" in aggname:
                # if the reduction represents a count, don't count empty pixels
                if vmin and vmin <= 0:
                    print("EOmaps: setting vmin=1 to avoid counting empty pixels...")
                    vmin = 1

        if verbose > 0:
            print("EOmaps: Classifying...")

        # ---------------------- classify the data
        cbcmap, norm, bins, classified = self._classify_data(
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            classify_specs=self.classify_specs,
        )

        self.classify_specs._cbcmap = cbcmap
        self.classify_specs._norm = norm
        self.classify_specs._bins = bins
        self.classify_specs._classified = classified

        # in case the aggregation does not represent data-values
        # (e.g. count, std, var ... ) use an automatic "linear" normalization
        if aggname in ["first", "last", "max", "min", "mean", "mode"]:
            kwargs.setdefault("norm", self.classify_specs._norm)
            kwargs.setdefault("vmin", vmin)
            kwargs.setdefault("vmax", vmax)

            # clip the data to properly account for vmin and vmax
            # (do this only if we don't intend to use the full dataset!)
            # if vmin or vmax:
            #     props["z_data"] = props["z_data"].clip(vmin, vmax)
        else:
            kwargs.setdefault("norm", "linear")
            kwargs.setdefault("vmin", vmin)
            kwargs.setdefault("vmax", vmax)

        if verbose > 0:
            print("EOmaps: Plotting...")

        zdata = self._data_manager.z_data
        if len(zdata) == 0:
            print("EOmaps: there was no data to plot")
            return

        plot_width, plot_height = int(self.ax.bbox.width), int(self.ax.bbox.height)

        # get rid of unnecessary dimensions in the numpy arrays
        zdata = zdata.squeeze()
        x0 = self._data_manager.x0.squeeze()
        y0 = self._data_manager.y0.squeeze()

        # the shape is always set after _prepare data!
        if self.shape.name == "shade_points" and self._data_manager.x0_1D is None:
            assert (
                _register_pandas()
            ), f"EOmaps: missing dependency 'pandas' for {self.shape.name}"

            df = pd.DataFrame(
                dict(
                    x=x0.ravel(),
                    y=y0.ravel(),
                    val=zdata.ravel(),
                ),
                copy=False,
            )

        else:
            assert (
                _register_xarray()
            ), "EOmaps: missing dependency `xarray` for 'shade_raster'"
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
                # first convert 1D inputs to 2D, then reproject the grid and use
                # a curvilinear QuadMesh to display the data
                assert _register_pandas(), (
                    "EOmaps: missing dependency 'pandas' to convert 1D"
                    + "datasets to 2D as required for 'shade_raster'"
                )

                # use pandas to convert to 2D
                df = (
                    pd.DataFrame(
                        dict(
                            x=x0.ravel(),
                            y=y0.ravel(),
                            val=zdata.ravel(),
                        ),
                        copy=False,
                    )
                    .set_index(["x", "y"])
                    .to_xarray()
                )
                xg, yg = np.meshgrid(df.x, df.y)

                # transform the grid from input-coordinates to the plot-coordinates
                crs1 = CRS.from_user_input(self.data_specs.crs)
                crs2 = CRS.from_user_input(self._crs_plot)
                if crs1 != crs2:
                    transformer = Transformer.from_crs(
                        crs1,
                        crs2,
                        always_xy=True,
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
            x0, x1, y0, y1 = self.ax.get_extent()
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
            cmap=cbcmap,
            ax=self.ax,
            plot_width=plot_width,
            plot_height=plot_height,
            # x_range=(x0, x1),
            # y_range=(y0, y1),
            # x_range=(df.x.min(), df.x.max()),
            # y_range=(df.y.min(), df.y.max()),
            x_range=x_range,
            y_range=y_range,
            **kwargs,
        )

        self._coll = coll
        if verbose > 0:
            print("EOmaps: Indexing for pick-callbacks...")

        # This is now done lazily (only if a pick-callback is attached)
        # self.tree = searchtree(m=self._proxy(self))
        # self.cb.pick._set_artist(coll)
        # self.cb.pick._init_cbs()
        # self.cb._methods.add("pick")

        if dynamic is True:
            self.BM.add_artist(coll, layer)
        else:
            self.BM.add_bg_artist(coll, layer)

        if dynamic is True:
            self.BM.update(clear=False)

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
        if encoding is not None:
            try:
                scale_factor = encoding.get("scale_factor", None)
                add_offset = encoding.get("add_offset", None)

                if add_offset:
                    val = val - add_offset
                if scale_factor:
                    val = val / scale_factor

                return val
            except:
                print("EOmaps: There was an error while trying to encode the data.")
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
            except:
                print("EOmaps: There was an error while trying to decode the data.")
                return val
        else:
            return val

    def _get_layers(self, exclude=None, exclude_private=True):
        # return a list of all (empty and non-empty) layer-names
        layers = set((m.layer for m in (self.parent, *self.parent._children)))
        # add layers that are not yet activated (but have an activation
        # method defined...)
        layers = layers.union(set(self.BM._on_layer_activation[True]))
        layers = layers.union(set(self.BM._on_layer_activation[False]))

        # add all (possibly still invisible) layers with artists defined
        # (ONLY do this for unique layers... skip multi-layers )
        layers = layers.union({i for i in self.BM._bg_artists if "|" not in i})

        # exclude private layers
        if exclude_private:
            layers = {l for l in layers if not l.startswith("__")}

        if exclude:
            for l in exclude:
                if l in layers:
                    layers.remove(l)

        # sort the layers
        layers = sorted(layers, key=lambda x: str(x))

        return layers

    @lru_cache()
    def _get_nominatim_response(self, q, user_agent=None):
        import requests

        print(f"Querying {q}")
        if user_agent is None:
            user_agent = f"EOMaps v{Maps.__version__}"

        headers = {
            "User-Agent": user_agent,
        }

        resp = requests.get(
            rf"https://nominatim.openstreetmap.org/search/{q}?format=json&addressdetails=1&limit=1",
            headers=headers,
        ).json()

        if len(resp) == 0:
            raise TypeError(f"Unable to resolve the location: {q}")

        return resp[0]

    def _get_snapshot(self, layer=None):
        if layer is None:
            buf = self.f.canvas.print_to_buffer()
            x = np.frombuffer(buf[0], dtype=np.uint8).reshape(buf[1][1], buf[1][0], 4)
        else:
            x = self.BM._get_array(layer)[::-1, ...]
        return x

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

    def _open_companion_widget_cb(self, event):
        if event.key != self._companion_widget_key:
            return

        if event.inaxes != self.ax:
            return

        # hide all other companion-widgets
        for m in (self.parent, *self.parent._children):
            if m == self:
                continue
            if m._companion_widget is not None and m._companion_widget.isVisible():
                m._companion_widget.hide()
                m._indicate_companion_map(False)

        if self._companion_widget is None:
            self._init_companion_widget()

        if self._companion_widget is not None:
            if self._companion_widget.isVisible():
                self._companion_widget.hide()
                self._indicate_companion_map(False)
            else:
                self._companion_widget.show()
                self._indicate_companion_map(True)

                # execute all actions that should trigger before opening the widget
                # (e.g. update tabs to show visible layers etc.)
                for f in self._on_show_companion_widget:
                    f()

                # Do NOT activate the companion widget in here!!
                # Activating the window during the callback steals focus and
                # as a consequence the key-released-event is never triggered
                # on the figure and "w" would remain activated permanently.
                self.f.canvas.key_release_event("w")
                self._companion_widget.activateWindow()

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
            if plt.get_backend() not in ["QtAgg", "Qt5Agg"]:
                print(
                    "EOmaps: Using m.open_widget() is only possible if you use matplotlibs"
                    + f" 'Qt5Agg' backend! (active backend: '{plt.get_backend()}')"
                )
                return

            from .qtcompanion.app import MenuWindow

            if self._companion_widget is not None:
                print(
                    "EOmaps: There is already an existing companinon widget for this"
                    " Maps-object!"
                )
                return

            self._companion_widget = MenuWindow(m=self, parent=self.f.canvas)
            # make sure that we clear the colormap-pixmap cache on startup
            self._companion_widget.cmapsChanged.emit()

        except Exception as ex:
            print("EOmaps: Unable to initialize companion widget.", ex)

    @staticmethod
    def _proxy(obj):
        # None cannot be weak-referenced!
        if obj is None:
            return None

        # create a proxy if the object is not yet a proxy
        if type(obj) is not weakref.ProxyType:
            return weakref.proxy(obj)
        else:
            return obj

    @staticmethod
    def _get_cartopy_crs(crs):
        if isinstance(crs, Maps.CRS.CRS):  # already a cartopy CRS
            cartopy_proj = crs
        elif crs == 4326:
            cartopy_proj = ccrs.PlateCarree()
        elif isinstance(crs, (int, np.integer)):
            cartopy_proj = ccrs.epsg(crs)
        elif isinstance(crs, CRS):  # pyproj CRS
            for (
                subgrid,
                equi7crs,
            ) in Maps.CRS.Equi7Grid_projection._pyproj_crs_generator():
                if equi7crs == crs:
                    cartopy_proj = Maps.CRS.Equi7Grid_projection(subgrid)
                    break
        else:
            raise AssertionError(f"EOmaps: cannot identify the CRS for: {crs}")
        return cartopy_proj

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
        assert _register_geopandas(), (
            "EOmaps: Missing dependency `geopandas`!\n"
            + "please install '(conda install -c conda-forge geopandas)'"
        )

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


class _InsetMaps(Maps):
    # a subclass of Maps that includes some special functions for inset maps

    def __init__(
        self,
        parent,
        crs=4326,
        layer=None,
        xy=(45, 45),
        xy_crs=4326,
        radius=5,
        radius_crs=None,
        plot_position=(0.5, 0.5),
        plot_size=0.5,
        shape="ellipses",
        indicate_extent=True,
        boundary=True,
        **kwargs,
    ):

        # inherit the layer from the parent Maps-object if not explicitly
        # provided
        if layer is None:
            layer = parent.layer

        # put all inset-map artists on dedicated layers
        # NOTE: all artists of inset-map axes are put on a dedicated layer
        # with a "__inset_" prefix to ensure they appear on top of other artists
        # (AND on top of spines of normal maps)!
        # layer = "__inset_" + str(layer)

        possible_shapes = ["ellipses", "rectangles", "geod_circles"]
        assert (
            shape in possible_shapes
        ), f"EOmaps: the inset shape can only be one of {possible_shapes}"

        if shape == "geod_circles":
            assert radius_crs is None, (
                "EOmaps: Using 'radius_crs' is not possible if 'geod_circles' is "
                + "used as shape! (the radius for `geod_circles` is always in meters!)"
            )

        if radius_crs is None:
            radius_crs = xy_crs

        extent_kwargs = dict(ec="r", lw=1, fc="none")
        boundary_kwargs = dict(ec="r", lw=2)

        if isinstance(boundary, dict):
            assert (
                len(set(boundary.keys()).difference({"ec", "lw"})) == 0
            ), "EOmaps: only 'ec' and 'lw' keys are allowed for the 'boundary' dict!"

            boundary_kwargs.update(boundary)
            # use same edgecolor for boundary and indicator by default
            extent_kwargs["ec"] = boundary["ec"]

        if isinstance(indicate_extent, dict):
            extent_kwargs.update(indicate_extent)

        x, y = xy
        plot_x, plot_y = plot_position
        left = plot_x - plot_size / 2
        bottom = plot_y - plot_size / 2

        # initialize a new maps-object with a new axis
        super().__init__(
            crs=crs,
            f=parent.f,
            ax=(left, bottom, plot_size, plot_size),
            layer=layer,
            **kwargs,
        )

        # get the boundary of a ellipse in the inset_crs
        bnd, bnd_verts = self._get_inset_boundary(
            x, y, xy_crs, radius, radius_crs, shape
        )

        # set the map boundary
        self.ax.set_boundary(bnd)
        # set the plot-extent to the envelope of the shape
        (x0, y0), (x1, y1) = bnd_verts.min(axis=0), bnd_verts.max(axis=0)
        self.ax.set_extent((x0, x1, y0, y1), crs=self.ax.projection)

        # TODO turn off navigation until the matpltolib pull-request on
        # zoom-events in overlapping axes is resolved
        # https://github.com/matplotlib/matplotlib/pull/22347
        self.ax.set_navigate(False)

        if boundary is not False:
            spine = self.ax.spines["geo"]
            spine.set_edgecolor(boundary_kwargs["ec"])
            spine.set_lw(boundary_kwargs["lw"])

        self._inset_props = dict(
            xy=xy, xy_crs=xy_crs, radius=radius, radius_crs=radius_crs, shape=shape
        )

        if indicate_extent is not False:
            self.indicate_inset_extent(
                parent, layer=parent.layer, permanent=True, **extent_kwargs
            )

    def _handle_spines(self):
        spine = self.ax.spines["geo"]
        if spine not in self.BM._bg_artists.get("__inset___SPINES__", []):
            self.BM.add_bg_artist(spine, layer="__inset___SPINES__")

    def _get_ax_label(self):
        return "inset_map"

    def plot_map(self, *args, **kwargs):
        set_extent = kwargs.pop("set_extent", False)
        super().plot_map(*args, **kwargs, set_extent=set_extent)

    # a convenience-method to add a boundary-polygon to a map
    def indicate_inset_extent(self, m, n=100, **kwargs):
        """
        Add a polygon to a  map that indicates the extent of the inset-map.

        Parameters
        ----------
        m : eomaps.Maps
            The Maps-object that will be used to draw the marker.
            (e.g. the map on which the extent of the inset should be indicated)
        n : int
            The number of points used to represent the polygon.
            The default is 100.
        kwargs :
            additional keyword-arguments passed to `m.add_marker`
            (e.g. "facecolor", "edgecolor" etc.)

        """
        if not any((i in kwargs for i in ["fc", "facecolor"])):
            kwargs["fc"] = "none"
        if not any((i in kwargs for i in ["ec", "edgecolor"])):
            kwargs["ec"] = "r"
        if not any((i in kwargs for i in ["lw", "linewidth"])):
            kwargs["lw"] = 1

        m.add_marker(
            shape=self._inset_props["shape"],
            xy=self._inset_props["xy"],
            xy_crs=self._inset_props["xy_crs"],
            radius=self._inset_props["radius"],
            radius_crs=self._inset_props["radius_crs"],
            n=n,
            **kwargs,
        )

    # a convenience-method to set the position based on the center of the axis
    def set_inset_position(self, x=None, y=None, size=None):
        """
        Set the (center) position and size of the inset-map.

        Parameters
        ----------
        x, y : int or float, optional
            The center position in relative units (0-1) with respect to the figure.
            If None, the existing position is used.
            The default is None.
        size : float, optional
            The relative radius (0-1) of the inset in relation to the figure width.
            If None, the existing size is used.
            The default is None.

        """
        x0, y1, x1, y0 = self.ax.get_position().bounds

        if size is None:
            size = abs(x1 - x0)

        if x is None:
            x = (x0 + x1) / 2
        if y is None:
            y = (y0 + y1) / 2

        self.ax.set_position((x - size / 2, y - size / 2, size, size))
        self.redraw("__inset_" + self.layer, "__inset___SPINES__")

    # a convenience-method to get the position based on the center of the axis
    def get_inset_position(self, precision=3):
        """
        Get the current inset position (and size).

        Parameters
        ----------
        precision : int, optional
            The precision of the returned position and size.
            The default is 3.

        Returns
        -------
        (x, y, size) : (float, float, float)
            The position and size of the inset-map.

        """
        bbox = self.ax.get_position()
        size = round(max(bbox.width, bbox.height), precision)
        x = round((bbox.x0 + bbox.width / 2), precision)
        y = round((bbox.y0 + bbox.height / 2), precision)

        return x, y, size

    def _get_inset_boundary(self, x, y, xy_crs, radius, radius_crs, shape, n=100):
        # get the inset-shape boundary

        shp = self.set_shape._get(shape)

        if shape == "ellipses":
            shp_pts = shp._get_ellipse_points(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = np.stack(shp_pts[:2], axis=2)[0]

        elif shape == "rectangles":
            shp_pts = shp._get_rectangle_verts(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = shp_pts[0][0]

        elif shape == "geod_circles":
            shp_pts = shp._get_geod_circle_points(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                # radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = np.stack(shp_pts[:2], axis=2).squeeze()
        boundary = mpl.path.Path(bnd_verts)

        return boundary, bnd_verts

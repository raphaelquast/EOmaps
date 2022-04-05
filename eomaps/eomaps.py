"""A collection of helper-functions to generate map-plots."""

from functools import lru_cache, wraps
from itertools import repeat
from collections import defaultdict
import warnings
import copy
from types import SimpleNamespace
from pathlib import Path
import weakref
from tempfile import TemporaryDirectory, TemporaryFile
import gc

import numpy as np

try:
    import pandas as pd

    _pd_OK = True
except ImportError:
    _pd_OK = False

try:
    import geopandas as gpd

    _gpd_OK = True
except ImportError:
    _gpd_OK = False

try:
    import xarray as xar

    _xar_OK = True
except ImportError:
    _xar_OK = False


from scipy.spatial import cKDTree
from pyproj import CRS, Transformer

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec, SubplotSpec


from cartopy import crs as ccrs

from .helpers import (
    pairwise,
    cmap_alpha,
    BlitManager,
    draggable_axes,
    progressbar,
    searchtree,
)
from ._shapes import shapes

from ._containers import (
    data_specs,
    plot_specs,
    map_objects,
    classify_specs,
    # cb_container,
    wms_container,
    NaturalEarth_features,
)

from ._cb_container import cb_container
from .scalebar import ScaleBar, Compass
from .projections import Equi7Grid_projection
from .reader import read_file, from_file, new_layer_from_file

from .utilities import utilities

try:
    import mapclassify
except ImportError:
    print("No module named 'mapclassify'... classification will not work!")


class Maps(object):
    """
    The base-class for generating plots with EOmaps.

    See Also
    --------
    - MapsGrid : Initialize a grid of Maps objects
    - m.new_layer : get a Maps-object that represents a new layer of a map
    - m.copy : copy an existing Maps object

    Parameters
    ----------
    crs : int or a cartopy-projection, optional
        The projection of the map.
        If int, it is identified as an epsg-code
        Otherwise you can specify any projection supported by `cartopy.crs`
        A list for easy-accses is available as `Maps.CRS`

        The default is 4326.
    layer : int or str, optional
        The name of the plot-layer assigned to this Maps-object.
        The default is 0.

    Other Parameters:
    -----------------
    parent : eomaps.Maps
        The parent Maps-object to use.
        Any maps-objects that share the same figure must be connected
        to allow shared interactivity!

        By default, also the axis used for plotting is shared between connected
        Maps-objects, but this can be overridden if you explicitly specify
        either a GridSpec or an Axis via `gs_ax`.

        >>> m1 = Maps()
        >>> m2 = Maps(parent=m1)

        Note: Instead of specifying explicit axes, you might want to have a
        look at `eomaps.MapsGrid` objects!
    f : matplotlib.Figure, optional
        Explicitly specify the matplotlib figure instance to use.
        (ONLY useful if you want to add a map to an already existing figure!)

          - If None, a new figure will be created (accessible via m.figure.f)
          - Connected maps-objects will always share the same figure! You do
            NOT need to specify it (just provide the parent and you're fine)!

        The default is None
    gs_ax : matplotlib.axes or matplotlib.gridspec.SubplotSpec, optional
        Explicitly specify the axes (or GridSpec) for plotting.

        Possible values are:

        * None:
            Initialize a new axes (the default)
        * `matplotilb.gridspec.SubplotSpec`:
            Use the SubplotSpec for initializing the axes.
            The SubplotSpec will be divided accordingly in case a colorbar
            is plotted.

                >>> import matplotlib.pyplot as plt
                >>> from matplotlib.gridspec import GridSpec
                >>> f = plt.figure()
                >>> gs = GridSpec(2,2)
                >>> m = Maps()
                >>> ...
                >>> m.plot_map(f_gs=gs[0,0])
        * `matplotilb.Axes`:
            Directly use the provided figure and axes instances for plotting.
            The axes MUST be a geo-axes with `m.plot_specs.crs_plot`
            projection. NO colorbar and NO histogram will be plotted.

                >>> import matplotlib.pyplot as plt
                >>> f = plt.figure()
                >>> m = Maps()
                >>> ...
                >>> ax = f.add_subplot(projection=m.crs_plot)
                >>> m.plot_map(ax_gs=ax)
    preferred_wms_service : str, optional
        Set the preferred way for accessing WebMap services if both WMS and WMTS
        capabilities are possible.
        The default is "wms"

    kwargs :
        additional kwargs are passed to matplotlib.pyplot.figure()
        - e.g. figsize=(10,5)
    """

    CRS = ccrs
    CRS.Equi7Grid_projection = Equi7Grid_projection

    # mapclassify.CLASSIFIERS
    _classifiers = (
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

    CLASSIFIERS = SimpleNamespace(**dict(zip(_classifiers, _classifiers)))

    def __init__(
        self,
        crs=None,
        parent=None,
        layer=0,
        f=None,
        gs_ax=None,
        preferred_wms_service="wms",
        **kwargs,
    ):
        # share the axes with the parent if no explicit axes is provided
        if parent is not None:
            assert (
                f is None
            ), "You cannot specify the figure for connected Maps-objects!"

        self._f = f
        self._ax = gs_ax
        self._parent = None

        self._BM = None
        self._children = set()  # weakref.WeakSet()
        self._layer = layer

        self.parent = parent  # invoke the setter!

        # preferred way of accessing WMS services (used in the WMS container)
        assert preferred_wms_service in [
            "wms",
            "wmts",
        ], "preferred_wms_service must be either 'wms' or 'wmts' !"
        self._preferred_wms_service = preferred_wms_service

        # default plot specs
        self.plot_specs = plot_specs(
            weakref.proxy(self),
            label=None,
            cmap=plt.cm.viridis.copy(),
            histbins=256,
            tick_precision=2,
            vmin=None,
            vmax=None,
            cpos="c",
            cpos_radius=None,
            alpha=1,
            density=False,
        )

        if isinstance(gs_ax, plt.Axes):
            # set the plot_crs only if no explicit axes is provided
            if crs is not None:
                raise AssertionError(
                    "You cannot set the crs if you already provide an explicit axes!"
                )
            if gs_ax.projection == Maps.CRS.PlateCarree():
                self._crs_plot = 4326
            else:
                self._crs_plot = gs_ax.projection
        else:
            if crs is None or crs == Maps.CRS.PlateCarree():
                crs = 4326

            self._crs_plot = crs

        self._crs_plot_cartopy = self._get_cartopy_crs(self._crs_plot)

        # default classify specs
        self.classify_specs = classify_specs(weakref.proxy(self))

        self.data_specs = data_specs(
            weakref.proxy(self),
            xcoord="lon",
            ycoord="lat",
            crs=4326,
        )

        self._axpicker = None

        self._figure = map_objects(weakref.proxy(self))
        self._cb = cb_container(weakref.proxy(self))  # accessor for the callbacks
        self._init_figure(gs_ax=gs_ax, plot_crs=crs, **kwargs)
        self._utilities = utilities(weakref.proxy(self))
        self._wms_container = wms_container(weakref.proxy(self))
        self._new_layer_from_file = new_layer_from_file(weakref.proxy(self))

        self._shapes = shapes(weakref.proxy(self))
        self.set_shape.ellipses()

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

        # a set holding the callback ID's from added logos
        self._logo_cids = set()

        # keep track of all decorated functions that need to be "undecorated" so that
        # Maps-objects can be garbage-collected
        self._cleanup_functions = set()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.cleanup()
        gc.collect()

    @staticmethod
    def _proxy(obj):
        # create a proxy if the object is not yet a proxy
        if type(obj) is not weakref.ProxyType:
            return weakref.proxy(obj)
        else:
            return obj

    def cleanup(self):
        """
        Cleanup all references to the object so that it can be savely deleted.
        (primarily used internally to clear objects if the figure is closed)

        Note
        ----
        Executing this function will remove ALL attached callbacks
        and delete all assigned datasets & pre-computed values.

        ONLY execute this if you do not need to do anything with the layer
        (except for looking at it)
        """
        # remove the xlim-callback since it contains a reference to self
        if hasattr(self, "_cid_xlim"):
            self.ax.callbacks.disconnect(self._cid_xlim)
            del self._cid_xlim

        # disconnect all callbacks from attached logos
        for cid in self._logo_cids:
            self.figure.f.canvas.mpl_disconnect(cid)
        self._logo_cids.clear()

        # disconnect all click, pick and keypress callbacks
        self.cb._reset_cids()

        # call all additional cleanup functions
        for f in self._cleanup_functions:
            f()
        self._cleanup_functions.clear()

        # remove the children from the parent Maps object
        if self in self.parent._children:
            self.parent._children.remove(self)

    def _check_gpd(self):
        # raise an error if geopandas is not found
        # (execute this in any function that requires geopandas!)
        if not _gpd_OK:
            raise ImportError(
                "EOmaps: You need to install geopandas first!\n"
                + "... with conda, simply use:  "
                + "'conda install -c conda-forge geopandas'"
            )

    from_file = from_file
    read_file = read_file

    @property
    def layer(self):
        """
        The layer-name associated with this Maps-object.
        """
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

    def show(self):
        """
        Make the layer of this `Maps`-object visible.
        (just a shortcut for `m.show_layer(m.layer)`)
        """

        self.show_layer(self.layer)

    @property
    def ax(self):
        return self._ax

    @property
    @wraps(new_layer_from_file)
    def new_layer_from_file(self):
        return self._new_layer_from_file

    def new_layer(
        self,
        layer=None,
        copy_data_specs=False,
        copy_plot_specs=False,
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
        copy_data_specs, copy_shape, copy_plot_specs, copy_classify_specs : bool
            Indicator if the corresponding properties should be copied to
            the new layer. By default no settings are copied.

        Returns
        -------
        eomaps.Maps
            A connected copy of the Maps-object that shares the same plot-axes.

        See Also
        --------
        copy : general way for copying Maps objects
        """

        if layer is None:
            layer = copy.deepcopy(self.layer)

        m = self.copy(
            data_specs=copy_data_specs,
            plot_specs=copy_plot_specs,
            classify_specs=copy_classify_specs,
            shape=copy_shape,
            parent=self.parent,
            gs_ax=self.figure.ax,
            layer=layer,
        )

        return m

    @property
    @wraps(cb_container)
    def cb(self):
        return self._cb

    @property
    @wraps(utilities)
    def util(self):
        return self._utilities

    @property
    @wraps(map_objects)
    def figure(self):
        return self._figure

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

    def _init_figure(self, gs_ax=None, plot_crs=None, **kwargs):
        if self.parent.figure.f is None:
            self._f = plt.figure(**kwargs)
            newfig = True
        else:
            newfig = False

        if isinstance(gs_ax, plt.Axes):
            # in case an axis is provided, attempt to use it
            ax = gs_ax
            gs = gs_ax.get_gridspec()
            newax = False
        else:
            newax = True
            # create a new axis
            if gs_ax is None:
                gs = GridSpec(
                    nrows=1, ncols=1, left=0.01, right=0.99, bottom=0.05, top=0.95
                )
                gsspec = gs[:]
            elif isinstance(gs_ax, SubplotSpec):
                gsspec = gs_ax
                gs = gsspec.get_gridspec()

            if plot_crs is None:
                plot_crs = self.plot_specs["plot_crs"]

            projection = self._get_cartopy_crs(plot_crs)

            ax = self.figure.f.add_subplot(
                gsspec, projection=projection, aspect="equal", adjustable="box"
            )

        self._ax = ax

        self._gridspec = gs

        # initialize the callbacks
        self.cb._init_cbs()

        # set the _ignore_cb_events property on the parent
        # (used to temporarily disconnect all callbacks)
        self.parent._ignore_cb_events = False

        if newax:  # only if a new axis has been created
            self._ax_xlims = (0, 0)
            self._ax_ylims = (0, 0)

            def xlims_change(*args, **kwargs):
                if self._ax_xlims != args[0].get_xlim():
                    self.BM._refetch_bg = True
                    # self.figure.f.stale = True
                    self._ax_xlims = args[0].get_xlim()

            # def ylims_change(*args, **kwargs):
            #     if self._ax_ylims != args[0].get_ylim():
            #         print("y limchange", self.BM._refetch_bg)
            #         self.BM._refetch_bg = True
            #         self._ax_ylims = args[0].get_ylim()

            # do this only on xlims and NOT on ylims to avoid recursion
            # (plot aspect ensures that y changes if x changes)
            self._cid_xlim = self.figure.ax.callbacks.connect(
                "xlim_changed", xlims_change
            )
            # self.figure.ax.callbacks.connect("ylim_changed", ylims_change)

        if newfig:  # only if a new figure has been initialized
            _ = self._draggable_axes
            if plt.isinteractive():
                if plt.get_backend() == "module://ipympl.backend_nbagg":
                    warnings.warn(
                        "EOmaps disables matplotlib's interactive mode (e.g. 'plt.ioff()') "
                        + "when using the 'ipympl' backend to avoid recursions during callbacks!"
                    )
                    plt.ioff()
                else:
                    plt.ion()

            # attach a callback that is executed when the figure is closed
            self._cid_onclose = self.figure.f.canvas.mpl_connect(
                "close_event", self._on_close
            )
            # attach a callback that is executed if the figure canvas is resized
            self._cid_resize = self.figure.f.canvas.mpl_connect(
                "resize_event", self._on_resize
            )

        if newfig:
            # we only need to call show if a new figure has been created!
            if plt.isinteractive():
                # make sure to call show only if we use an interactive backend...
                # (otherwise it will block subsequent code!)
                plt.show()

    def _on_resize(self, event):
        # make sure the background is re-fetched if the canvas has been resized
        # (required for peeking layers after the canvas has been resized
        #  and for webagg and nbagg backends to correctly re-draw the layer)
        self.BM._refetch_bg = True

    def _on_close(self, event):
        # reset attributes that might use up a lot of memory when the figure is closed
        for m in [self.parent, *self.parent._children]:

            if hasattr(m, "_props"):
                m._props.clear()
                del m._props

            if hasattr(m, "tree"):
                del m.tree

            if hasattr(m.figure, "coll"):
                del m.figure.coll

            m.data_specs.delete()
            m.cleanup()

        # delete the tempfolder containing the memmaps
        if hasattr(self.parent, "_tmpfolder"):
            self.parent._tmpfolder.cleanup()

        # run garbage-collection to immediately free memory
        gc.collect

    @property
    def _ignore_cb_events(self):
        return self.parent._persistent_ignore_cb_events

    @_ignore_cb_events.setter
    def _ignore_cb_events(self, val):
        self.parent._persistent_ignore_cb_events = val

    @property
    def BM(self):
        """The Blit-Manager used to dynamically update the plots"""
        m = weakref.proxy(self)
        if self.parent._BM is None:
            self.parent._BM = BlitManager(m)
            self.parent._BM._bg_layer = m.parent.layer
        return self.parent._BM

    @property
    def _draggable_axes(self):
        if self.parent._axpicker is None:
            # make the axes draggable
            self.parent._axpicker = draggable_axes(self.parent, modifier="alt+d")
            return self.parent._axpicker

        return self.parent._axpicker

    def _add_child(self, m):
        self.parent._children.add(m)

    @property
    def parent(self):
        """
        The parent-object to which this Maps-object is connected to.
        If None, `self` is returned!
        """
        if self._parent is None:
            return weakref.proxy(self)
        else:
            return self._parent

    @parent.setter
    def parent(self, parent):
        assert parent is not self, "EOmaps: A Maps-object cannot be its own parent!"
        assert self._parent is None, "EOmaps: There is already a parent Maps object!"

        if parent is not None:
            self._parent = self._proxy(parent)
        else:
            # None cannot be weak-referenced!
            self._parent = None

        if parent not in [self, None]:
            # add the child to the topmost parent-object
            self.parent._add_child(self)

    def join_limits(self, *args):
        """
        Join the x- and y- limits of the axes (e.g. on zoom)

        Parameters
        ----------
        *args :
            the axes to join.
        """
        for m in args:
            if m is not self:
                self._join_axis_limits(weakref.proxy(m))

    def _join_axis_limits(self, m):
        if self.figure.ax.projection != m.figure.ax.projection:
            warnings.warn(
                "EOmaps: joining axis-limits is only possible for "
                + "axes with the same projection!"
            )
            return

        self.figure.ax._EOmaps_joined_action = False
        m.figure.ax._EOmaps_joined_action = False

        # Declare and register callbacks
        def child_xlims_change(event_ax):
            if event_ax._EOmaps_joined_action is not m.figure.ax:
                m.figure.ax._EOmaps_joined_action = event_ax
                m.figure.ax.set_xlim(event_ax.get_xlim())
            event_ax._EOmaps_joined_action = False

        def child_ylims_change(event_ax):
            if event_ax._EOmaps_joined_action is not m.figure.ax:
                m.figure.ax._EOmaps_joined_action = event_ax
                m.figure.ax.set_ylim(event_ax.get_ylim())
            event_ax._EOmaps_joined_action = False

        def parent_xlims_change(event_ax):
            if event_ax._EOmaps_joined_action is not self.figure.ax:
                self.figure.ax._EOmaps_joined_action = event_ax
                self.figure.ax.set_xlim(event_ax.get_xlim())
            event_ax._EOmaps_joined_action = False

        def parent_ylims_change(event_ax):
            if event_ax._EOmaps_joined_action is not self.figure.ax:
                self.figure.ax._EOmaps_joined_action = event_ax
                self.figure.ax.set_ylim(event_ax.get_ylim())

            event_ax._EOmaps_joined_action = False

        self.figure.ax.callbacks.connect("xlim_changed", child_xlims_change)
        self.figure.ax.callbacks.connect("ylim_changed", child_ylims_change)

        m.figure.ax.callbacks.connect("xlim_changed", parent_xlims_change)
        m.figure.ax.callbacks.connect("ylim_changed", parent_ylims_change)

    def copy(
        self,
        data_specs=False,
        plot_specs=True,
        classify_specs=True,
        shape=True,
        **kwargs,
    ):
        """
        Create a (deep)copy of the Maps object that shares selected specifications.

        -> useful to quickly create plots with similar configurations

        Parameters
        ----------
        data_specs, plot_specs, classify_specs, shape : bool or "shared", optional
            Indicator if the corresponding properties should be copied.

            - if True: ALL corresponding properties are copied

            By default, "plot_specs", "classify_specs" and the "shape" are copied.

        kwargs :
            Additional kwargs passed to `m = Maps(**kwargs)`
            (e.g. crs, f, gs_ax, orientation, layer)
        Returns
        -------
        copy_cls : eomaps.Maps object
            a new Maps class.
        """

        copy_cls = Maps(**kwargs)
        if plot_specs is True:
            copy_cls.set_plot_specs(
                **{key: copy.deepcopy(val) for key, val in self.plot_specs}
            )

        if data_specs is True:
            data_specs = list(self.data_specs.keys())
            copy_cls.set_data_specs(
                **{key: copy.deepcopy(val) for key, val in self.data_specs}
            )

        if shape is True:
            getattr(copy_cls.set_shape, self.shape.name)(**self.shape._initargs)

        if classify_specs is True:
            classify_specs = list(self.classify_specs.keys())
            copy_cls.set_classify_specs(
                scheme=self.classify_specs.scheme, **self.classify_specs
            )

        return copy_cls

    @property
    def data(self):
        return self.data_specs.data

    @data.setter
    def data(self, val):
        # for downward-compatibility
        self.data_specs.data = val

    @property
    @wraps(shapes)
    def set_shape(self):
        return self._shapes

    def set_data_specs(self, data=None, xcoord=None, ycoord=None, crs=None, **kwargs):
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

        xcoord, ycoord : str, optional
            Specify the coordinates associated with the provided data.
            Accepted inputs are:

            - a string (corresponding to the column-names of the `pandas.DataFrame`)
            - a pandas.Series
            - a 1D or 2D numpy-array
            - a 1D list

            The names of columns that contain the coordinates in the specified crs.
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
            ONLY relevant if a pandas.DataFrame that specifyes both the coordinates
            and the data-values is provided as `data`!

            The name of the column that should be used as parameter.

            If None, the first column (despite of xcoord and ycoord) will be used.
            The default is None.

        Examples
        --------

        - using a single `pandas.DataFrame`

          >>> data = pd.DataFrame(dict(lon=[...], lat=[...], a=[...], b=[...]))
          >>> m.set_data(data, xcoord="lon", ycoord="lat", parameter="a", crs=4326)

        - using individual `pandas.Series`

          >>> lon, lat, vals = pd.Series([...]), pd.Series([...]), pd.Series([...])
          >>> m.set_data(vals, xcoord=x, ycoord=y, crs=4326)

        - using 1D lists

          >>> lon, lat, vals = [...], [...], [...]
          >>> m.set_data(vals, xcoord=lon, ycoord=lat, crs=4326)

        - using 1D or 2D numpy.arrays

          >>> lon, lat, vals = np.array([[...]]), np.array([[...]]), np.array([[...]])
          >>> m.set_data(vals, xcoord=lon, ycoord=lat, crs=4326)

        """

        if data is not None:
            self.data_specs.data = data

        if xcoord is not None:
            self.data_specs.xcoord = xcoord

        if ycoord is not None:
            self.data_specs.ycoord = ycoord

        if crs is not None:
            self.data_specs.crs = crs

        for key, val in kwargs.items():
            self.data_specs[key] = val

    set_data = set_data_specs

    def set_plot_specs(self, **kwargs):
        """
        Set the plot-specifications (label, colormap, crs, etc.)

        Use this function to update multiple data-specs in one go
        Alternatively you can set the data-specifications via

            >>> m.data_specs.< property > = ...`

        Parameters
        ----------
        label : str, optional
            The colorbar-label.
            If None, the name of the parameter will be used.
            The default is None.
        cmap : str or matplotlib.colormap, optional
            The colormap to use. The default is "viridis".
        plot_crs : int or cartopy-projection, optional
            The projection to use for plotting.
            If int, it is identified as an epsg-code
            Otherwise you can specify any projection supported by cartopy.
            A list for easy-accses is available as `Maps.CRS`

            The default is 4326.
        histbins : int, list, tuple, array or "bins", optional
            If int: The number of histogram-bins to use for the colorbar.
            If list, tuple or numpy-array: the bins to use
            If "bins": use the bins obtained from the classification
            (ONLY possible if a classification scheme is used!)

            The default is 256.
        tick_precision : int, optional
            The precision of the tick-labels in the colorbar. The default is 2.
        vmin, vmax : float, optional
            Min- and max. values assigned to the colorbar. The default is None.
        cpos : str, optional
            Indicator if the provided x-y coordinates correspond to the center ("c"),
            upper-left ("ul"), lower-left ("ll") etc.  of the pixel.
            If any value other than "c" is provided, a "cpos_radius" must be set!
            The default is "c".
        cpos_radius : int or tuple, optional
            The pixel-radius (in the input-crs) that will be used to set the
            center-position of the provided data.
            If a number is provided, the pixels are treated as squares.
            If a tuple (rx, ry) is provided, the pixels are treated as rectangles.
        alpha : int, optional
            Set the transparency of the plot (0-1)
            The default is 1.
        density : bool, optional
            Indicator if the y-axis of the histogram should represent the
            probability-density (True) or the number of counts per bin (False)
            The default is False.
        """

        for key, val in kwargs.items():
            self.plot_specs[key] = val

    def set_classify_specs(self, scheme=None, **kwargs):
        """
        Set classification specifications for the data.
        (classification is performed by the `mapclassify` module)

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
        self.classify_specs._set_scheme_and_args(scheme, **kwargs)

    def _set_cpos(self, x, y, radiusx, radiusy, cpos):
        # use x = x + ...   instead of x +=  to allow casting from int to float
        if cpos == "c":
            pass
        elif cpos == "ll":
            x = x + radiusx
            y = y + radiusy
        elif cpos == "ul":
            x = x + radiusx
            y = y - radiusy
        elif cpos == "lr":
            x = x - radiusx
            y = y + radiusy
        elif cpos == "ur":
            x = x - radiusx
            y = y - radiusx

        return x, y

    @property
    def crs_plot(self):
        """
        The crs used for plotting.
        """
        return self._crs_plot_cartopy

    def get_crs(self, crs):
        """
        get the pyproj CRS instance of a given crs specification

        Parameters
        ----------
        crs : "in", "out" or a crs definition
            the crs to return
            if "in" : the crs defined in m.data_specs.crs
            if "out" or "plot" : the crs defined in m.plot_specs.plot_crs

        Returns
        -------
        crs : pyproj.CRS
            the pyproj CRS instance

        """
        if crs == "in":
            crs = self.data_specs.crs
        elif crs == "out" or crs == "plot":
            crs = self.crs_plot

        if not isinstance(crs, CRS):
            crs = CRS.from_user_input(crs)

        return crs

    def _identify_data(self, data=None, xcoord=None, ycoord=None, parameter=None):
        """
        Identify the way how the data has been provided and convert to the
        internal structure.
        """

        if data is None:
            data = self.data_specs.data
        if xcoord is None:
            xcoord = self.data_specs.xcoord
        if ycoord is None:
            ycoord = self.data_specs.ycoord
        if parameter is None:
            parameter = self.data_specs.parameter
        if data is not None:
            if _pd_OK and isinstance(data, pd.DataFrame):
                # get the data-values
                z_data = data[parameter].values
                # get the index-values
                ids = data.index.values

                if isinstance(xcoord, str) and isinstance(ycoord, str):
                    # get the data-coordinates
                    xorig = data[xcoord].values
                    yorig = data[ycoord].values
                else:
                    assert isinstance(xcoord, (list, np.ndarray, pd.Series)), (
                        "xcoord must be either a column-name, or explicit values "
                        " specified as a list, a numpy-array or a pandas"
                        + f" Series object if you provide the data as '{type(data)}'"
                    )
                    assert isinstance(ycoord, (list, np.ndarray, pd.Series)), (
                        "ycoord must be either a column-name, or explicit values "
                        " specified as a list, a numpy-array or a pandas"
                        + f" Series object if you provide the data as '{type(data)}'"
                    )

                    xorig = np.asanyarray(xcoord)
                    yorig = np.asanyarray(ycoord)

                return z_data, xorig, yorig, ids, parameter

            # check for explicit 1D value lists
            types = (list, np.ndarray)
            if _pd_OK:
                types += (pd.Series,)

            if isinstance(data, types):
                # get the data-values
                z_data = np.asanyarray(data)
                # get the index-values
                ids = np.arange(z_data.size)

                assert isinstance(xcoord, types), (
                    "xcoord must be either a list, a numpy-array or a pandas"
                    + f" Series object if you provide the data as '{type(data)}'"
                )
                assert isinstance(ycoord, types), (
                    "ycoord must be either a list, a numpy-array or a pandas"
                    + f" Series object if you provide the data as '{type(data)}'"
                )

                # get the data-coordinates
                xorig = np.asanyarray(xcoord)
                yorig = np.asanyarray(ycoord)

            return z_data, xorig, yorig, ids, parameter

    def _prepare_data(
        self,
        data=None,
        in_crs=None,
        plot_crs=None,
        radius=None,
        radius_crs=None,
        cpos=None,
        cpos_radius=None,
        parameter=None,
        xcoord=None,
        ycoord=None,
        buffer=None,
    ):
        if in_crs is None:
            in_crs = self.data_specs.crs
        if cpos is None:
            cpos = self.plot_specs.cpos
        if cpos_radius is None:
            cpos_radius = self.plot_specs.cpos_radius

        props = dict()
        # get coordinate transformation from in_crs to plot_crs
        # make sure to re-identify the CRS with pyproj to correctly skip re-projection
        # in case we use in_crs == plot_crs

        crs1 = CRS.from_user_input(in_crs)
        crs2 = CRS.from_user_input(self._crs_plot)

        # identify the provided data and get it in the internal format
        z_data, xorig, yorig, ids, parameter = self._identify_data(
            data=data, xcoord=xcoord, ycoord=ycoord, parameter=parameter
        )
        if cpos is not None and cpos != "c":
            # fix position of pixel-center in the input-crs
            assert (
                cpos_radius is not None
            ), "you must specify a 'cpos_radius if 'cpos' is not 'c'"
            if isinstance(cpos_radius, (list, tuple)):
                rx, ry = cpos_radius
            else:
                rx = ry = cpos_radius

            xorig, yorig = self._set_cpos(xorig, yorig, rx, ry, cpos)

        # transform center-points to the plot_crs

        if len(xorig.shape) == len(z_data.shape):
            assert xorig.shape == z_data.shape and yorig.shape == z_data.shape, (
                f"EOmaps: The data-shape {z_data.shape} and coordinate-shape "
                + f"x={xorig.shape}, y={yorig.shape} do not match!"
            )

        if crs1 == crs2:
            x0, y0 = xorig, yorig
        else:
            transformer = Transformer.from_crs(
                crs1,
                crs2,
                always_xy=True,
            )
            # convert 1D data to 2D to make sure re-projection is correct
            if len(xorig.shape) == 1 and len(z_data.shape) == 2:
                xorig, yorig = np.meshgrid(xorig, yorig, copy=False)
                z_data = z_data.T

            x0, y0 = transformer.transform(xorig, yorig)

        props["xorig"] = xorig
        props["yorig"] = yorig
        props["ids"] = ids
        props["z_data"] = z_data
        props["x0"] = x0
        props["y0"] = y0

        # convert the data to 1D for shapes that accept unstructured data
        if self.shape.name != "shade_raster":
            self._1Dprops(props)

        return props

    def _classify_data(
        self,
        z_data=None,
        cmap=None,
        histbins=None,
        vmin=None,
        vmax=None,
        classify_specs=None,
    ):

        if z_data is None:
            z_data = self._props["z_data"]
        if cmap is None:
            cmap = self.plot_specs["cmap"]
        if self.plot_specs["alpha"] < 1:
            cmap = cmap_alpha(
                cmap,
                self.plot_specs["alpha"],
            )

        if histbins is None:
            histbins = self.plot_specs["histbins"]
        if vmin is None:
            vmin = self.plot_specs["vmin"]
        if vmax is None:
            vmax = self.plot_specs["vmax"]

        if isinstance(cmap, str):
            cmap = plt.get_cmap(cmap)

        # evaluate classification
        if classify_specs is not None and classify_specs.scheme is not None:
            classified = True

            if classify_specs.scheme == "UserDefined" and hasattr(
                classify_specs, "bins"
            ):
                classifybins = np.array(classify_specs.bins)
                binmask = (classifybins > np.nanmin(z_data)) & (
                    classifybins < np.nanmax(z_data)
                )
                if np.any(binmask):
                    classifybins = classifybins[binmask]
                    warnings.warn(
                        "EOmaps: classification bins outside of value-range..."
                        + " bins have been updated!"
                    )

                    classify_specs.bins = classifybins

            mapc = getattr(mapclassify, classify_specs.scheme)(
                z_data[~np.isnan(z_data)], **classify_specs
            )
            bins = np.unique([mapc.y.min(), *mapc.bins])
            nbins = len(bins)
            norm = mpl.colors.BoundaryNorm(bins, nbins)
            colors = cmap(np.linspace(0, 1, nbins))
        else:
            classified = False
            if isinstance(histbins, int):
                nbins = histbins
                bins = None
            elif isinstance(histbins, (list, tuple, np.ndarray)):
                nbins = len(histbins)
                bins = histbins
            else:
                if isinstance(histbins, str) and histbins == "bins":
                    raise TypeError(
                        "using histbins='bins' is only valid"
                        + "if you classify the data!"
                    )
                else:
                    raise TypeError(
                        "you can only provide integers, lists "
                        + "tuples or numpy-arrays as histbins!"
                    )
            colors = cmap(np.linspace(0, 1, nbins))
            norm = mpl.colors.Normalize(vmin, vmax)

        # initialize a colormap
        cbcmap = LinearSegmentedColormap.from_list(
            "cmapname", colors=colors, N=len(colors)
        )
        if cmap._rgba_bad:
            cbcmap.set_bad(cmap._rgba_bad)
        if cmap._rgba_over:
            cbcmap.set_over(cmap._rgba_over)
        if cmap._rgba_under:
            cbcmap.set_under(cmap._rgba_under)

        return cbcmap, norm, bins, classified

    def _add_colorbar(
        self,
        ax_cb=None,
        ax_cb_plot=None,
        z_data=None,
        label=None,
        bins=None,
        histbins=None,
        cmap="viridis",
        norm=None,
        classified=False,
        vmin=None,
        vmax=None,
        tick_precision=3,
        density=False,
        orientation="vertical",
        log=False,
    ):

        if ax_cb is None:
            ax_cb = self.figure.ax_cb
        if ax_cb_plot is None:
            ax_cb_plot = self.figure.ax_cb_plot

        if z_data is None:
            z_data = self._props["z_data"]
        z_data = z_data.ravel()

        if label is None:
            label = self.plot_specs["label"]
            if label is None:
                label = self.data_specs["parameter"]
        if histbins is None:
            histbins = self.plot_specs["histbins"]
        if cmap is None:
            cmap = self.plot_specs["cmap"]
        if vmin is None:
            vmin = self.plot_specs["vmin"]
            if vmin is None:
                vmin = np.nanmin(self._props["z_data"])
        if vmax is None:
            vmax = self.plot_specs["vmax"]
            if vmax is None:
                vmax = np.nanmax(self._props["z_data"])
        if tick_precision is None:
            tick_precision = self.plot_specs["tick_precision"]
        if density is None:
            density = self.plot_specs["density"]

        if orientation == "horizontal":
            cb_orientation = "vertical"

            if log:
                ax_cb_plot.set_xscale("log")

        elif orientation == "vertical":
            cb_orientation = "horizontal"

            if log:
                ax_cb_plot.set_yscale("log")

        if histbins == "bins":
            assert (
                classified
            ), "EOmaps: using histbins='bins' is only possible for classified data!"

        n_cmap = cm.ScalarMappable(cmap=cmap, norm=norm)
        n_cmap.set_array(np.ma.masked_invalid(z_data))
        cb = plt.colorbar(
            n_cmap,
            cax=ax_cb,
            label=label,
            extend="neither",
            spacing="proportional",
            orientation=cb_orientation,
        )
        # plot the histogram
        hist_vals, hist_bins, init_hist = ax_cb_plot.hist(
            z_data,
            orientation=orientation,
            bins=bins if (classified and histbins == "bins") else histbins,
            color="k",
            align="mid",
            # range=(norm.vmin, norm.vmax),
            density=density,
        )

        # color the histogram
        for patch in list(ax_cb_plot.patches):
            # the list is important!! since otherwise we change ax.patches
            # as we iterate over it... which is not a good idea...
            if orientation == "horizontal":
                minval = np.atleast_1d(patch.get_y())[0]
                width = patch.get_width()
                height = patch.get_height()
                maxval = minval + height
            elif orientation == "vertical":
                minval = np.atleast_1d(patch.get_x())[0]
                width = patch.get_width()
                height = patch.get_height()
                maxval = minval + width

            patch.set_facecolor(cmap(norm((minval + maxval) / 2)))

            # take care of histogram-bins that have splitted colors
            if bins is not None:
                splitbins = bins[np.where((minval < bins) & (maxval > bins))]

                if len(splitbins) > 0:

                    patch.remove()
                    # add first and last patch
                    # (note b0 = b1 if only 1 split is performed!)
                    b0 = splitbins[0]
                    if orientation == "horizontal":
                        p0 = mpl.patches.Rectangle(
                            (0, minval),
                            width,
                            (b0 - minval),
                            facecolor=cmap(norm(minval)),
                        )
                    elif orientation == "vertical":
                        p0 = mpl.patches.Rectangle(
                            (minval, 0),
                            (b0 - minval),
                            height,
                            facecolor=cmap(norm(minval)),
                        )

                    b1 = splitbins[-1]
                    if orientation == "horizontal":
                        p1 = mpl.patches.Rectangle(
                            (0, b1), width, (maxval - b1), facecolor=cmap(norm(maxval))
                        )
                    elif orientation == "vertical":
                        p1 = mpl.patches.Rectangle(
                            (b1, 0), (maxval - b1), height, facecolor=cmap(norm(maxval))
                        )

                    ax_cb_plot.add_patch(p0)
                    ax_cb_plot.add_patch(p1)

                    # add in-between patches
                    if len(splitbins > 1):
                        for b0, b1 in pairwise(splitbins):
                            pi = mpl.patches.Rectangle(
                                (0, b0), width, (b1 - b0), facecolor=cmap(norm(b0))
                            )

                            if orientation == "horizontal":
                                pi = mpl.patches.Rectangle(
                                    (0, b0), width, (b1 - b0), facecolor=cmap(norm(b0))
                                )
                            elif orientation == "vertical":
                                pi = mpl.patches.Rectangle(
                                    (b0, 0), (b1 - b0), height, facecolor=cmap(norm(b0))
                                )

                            ax_cb_plot.add_patch(pi)
                else:
                    patch.set_facecolor(cmap(norm((minval + maxval) / 2)))

        # setup appearance of histogram
        if orientation == "horizontal":
            ax_cb_plot.invert_xaxis()

            ax_cb_plot.tick_params(
                left=False,
                labelleft=False,
                bottom=False,
                top=False,
                labelbottom=True,
                labeltop=False,
            )
            ax_cb_plot.grid(axis="x", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            ax_cb_plot.plot(
                [1, 1], [0, 1], "k--", alpha=0.5, transform=ax_cb_plot.transAxes
            )
            # make sure lower x-limit is 0
            if log is False:
                ax_cb_plot.xaxis.set_major_locator(plt.MaxNLocator(5))
                ax_cb_plot.set_xlim(None, 0)

        elif orientation == "vertical":
            ax_cb_plot.tick_params(
                left=False,
                labelleft=True,
                bottom=False,
                top=False,
                labelbottom=False,
                labeltop=False,
            )
            ax_cb_plot.grid(axis="y", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            ax_cb_plot.plot(
                [0, 1], [0, 0], "k--", alpha=0.5, transform=ax_cb_plot.transAxes
            )
            # make sure lower y-limit is 0
            if log is False:
                ax_cb_plot.yaxis.set_major_locator(plt.MaxNLocator(5))
                ax_cb_plot.set_ylim(0)

        cb.outline.set_visible(False)

        # ensure that ticklabels are correct if a classification is used
        if classified:
            cb.set_ticks([i for i in bins if i >= vmin and i <= vmax])

            if orientation == "vertical":
                labelsetfunc = "set_xticklabels"
            elif orientation == "horizontal":
                labelsetfunc = "set_yticklabels"

            getattr(cb.ax, labelsetfunc)(
                [
                    np.format_float_positional(i, precision=tick_precision, trim="-")
                    for i in bins
                    if i >= vmin and i <= vmax
                ]
            )
        else:
            cb.set_ticks(cb.get_ticks())

        # format position of scientific exponent for colorbar ticks
        if cb_orientation == "vertical":
            ot = ax_cb.yaxis.get_offset_text()
            ot.set_horizontalalignment("center")
            ot.set_position((1, 0))

        ax_cb.autoscale()

        return cb

    @property
    @wraps(NaturalEarth_features)
    def add_feature(self):
        return NaturalEarth_features(weakref.proxy(self))

    if _gpd_OK:

        def _clip_gdf(self, gdf, how="crs"):
            """
            Clip the shapes of a GeoDataFrame with respect to the boundaries
            of the crs (or the plot-extent).

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

            clipgdf = gdf.clip(clip_shp)

            if how.endswith("_invert"):
                clipgdf = clipgdf.symmetric_difference(clip_shp)

            return clipgdf

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
            **kwargs,
        ):
            """
            Plot a `geopandas.GeoDataFrame` on the map.

            Parameters
            ----------
            gdf : geopandas.GeoDataFrame
                A GeoDataFrame that should be added to the plot.
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
                The default is None.
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

                - if "gpd": geopandas is used to re-project the geometries
                - if "cartopy": cartopy is used to re-project the geometries
                  (slower but generally more robust than "gpd")

                >>> mg = MapsGrid(2, 1, crs=Maps.CRS.Stereographic())
                >>> mg.m_0_0.add_feature.preset.ocean(reproject="gpd")
                >>> mg.m_1_0.add_feature.preset.ocean(reproject="cartopy")

                The default is "gpd"
            verbose : bool, optional
                Indicator if a progressbar should be printed when re-projecting
                geometries with "use_gpd=False".
                The default is False.
            kwargs :
                all remaining kwargs are passed to `geopandas.GeoDataFrame.plot(**kwargs)`

            Returns
            -------
            new_artists : matplotlib.Artist
                The matplotlib-artists added to the plot

            """
            assert pick_method in ["centroids", "contains"], (
                f"EOmaps: '{pick_method}' is not a valid GeoDataFrame pick-method! "
                + "... use one of ['contains', 'centroids']"
            )

            self._check_gpd()

            try:
                # explode the GeoDataFrame to avoid picking multi-part geometries
                gdf = gdf.explode(index_parts=False)
            except Exception:
                # geopandas sometimes has problems exploding geometries...
                # if it does not work, just continue with the Multi-geometries!
                pass

            if clip:
                gdf = self._clip_gdf(gdf, clip)
            if reproject == "gpd":
                gdf = gdf.to_crs(self.crs_plot)
            elif reproject == "cartopy":
                # optionally use cartopy's re-projection routines to re-project
                # geometries
                if self.ax.projection != self._get_cartopy_crs(gdf.crs):
                    # select only polygons that actually intersect with the CRS-boundary
                    mask = gdf.intersects(
                        gpd.GeoDataFrame(
                            geometry=[self.ax.projection.domain], crs=self.ax.projection
                        )
                        .to_crs(gdf.crs)
                        .to_crs(gdf.crs)
                        .geometry[0]
                    )
                    gdf = gdf.copy()[mask]

                    geoms = gdf.geometry
                    if len(geoms) > 0:
                        proj_geoms = []

                        if verbose:
                            for g in progressbar(
                                geoms, "EOmaps: re-projecting... ", 20
                            ):
                                proj_geoms.append(
                                    self.ax.projection.project_geometry(
                                        g, ccrs.CRS(gdf.crs)
                                    )
                                )
                        else:
                            for g in geoms:
                                proj_geoms.append(
                                    self.ax.projection.project_geometry(
                                        g, ccrs.CRS(gdf.crs)
                                    )
                                )

                        gdf.geometry = proj_geoms
                        gdf.set_crs(self.ax.projection, allow_override=True)
            else:
                raise AssertionError(
                    f"EOmaps: '{reproject}' is not a valid reproject-argument."
                )
            # plot gdf and identify newly added collections
            # (geopandas always uses collections)
            colls = [id(i) for i in self.ax.collections]
            artists, prefixes = [], []
            for geomtype, geoms in gdf.groupby(gdf.geom_type):
                gdf.plot(ax=self.ax, aspect=self.ax.get_aspect(), **kwargs)
                artists = [i for i in self.ax.collections if id(i) not in colls]
                for i in artists:
                    prefixes.append(
                        f"_{i.__class__.__name__.replace('Collection', '')}"
                    )

            if picker_name is not None:
                if pick_method is not None:
                    if isinstance(pick_method, str):
                        if pick_method == "contains":

                            def picker(artist, mouseevent):
                                try:
                                    query = getattr(gdf, pick_method)(
                                        gpd.points_from_xy(
                                            [mouseevent.xdata], [mouseevent.ydata]
                                        )[0]
                                    )
                                    if query.any():
                                        return True, dict(
                                            ID=gdf.index[query][0],
                                            ind=query.values.nonzero()[0][0],
                                            val=(
                                                gdf[query][val_key].iloc[0]
                                                if val_key
                                                else None
                                            ),
                                        )
                                    else:
                                        return False, dict()
                                except:
                                    return False, dict()

                        elif pick_method == "centroids":
                            tree = cKDTree(
                                list(map(lambda x: (x.x, x.y), gdf.geometry.centroid))
                            )

                            def picker(artist, mouseevent):
                                try:
                                    dist, ind = tree.query(
                                        (mouseevent.xdata, mouseevent.ydata), 1
                                    )

                                    ID = gdf.index[ind]
                                    val = gdf.iloc[ind][val_key] if val_key else None
                                    pos = tree.data[ind].tolist()
                                except:
                                    return False, dict()

                                return True, dict(ID=ID, pos=pos, val=val, ind=ind)

                    elif callable(pick_method):
                        picker = pick_method
                    else:
                        print(
                            "EOmaps: I don't know what to do with the provided pick_method"
                        )

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
        shape="ellipses",
        buffer=1,
        **kwargs,
    ):
        """
        add a marker to the plot

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
        kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)

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

        # add marker
        marker = self.cb.click._cb.mark(
            ID=ID, pos=xy, radius=radius, ind=None, shape=shape, buffer=buffer, **kwargs
        )
        self.BM.update(clear=False)

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
        add an annotation to the plot

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

        """

        if ID is not None:
            assert xy is None, "You can only provide 'ID' or 'pos' not both!"
            mask = np.isin(self._props["ids"], ID)
            xy = (self._props["xorig"][mask], self._props["yorig"][mask])
            val = self._props["z_data"][mask]
            ind = self._props["ids"][mask]
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

        defaultargs = dict(permanent=True)
        defaultargs.update(kwargs)

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
                **defaultargs,
            )
        self.BM.update(clear=False)

    def add_compass(
        self, pos=None, scale=10, style="compass", patch="w", txt="N", pickable=True
    ):
        """
        Add a "compass" or "north-arrow" to the map.

        Note
        ----
        You can use the mouse to pick the compass and move it anywhere on the map.
        (the directions are dynamically updated if you pan/zoom or pick the compass)

        - If you press the "delete" key while clicking on the compass, it is removed.
          (same as calling `compass.remove()`)
        - If you press the "d" key while clicking on the compass, it will be
          disconnected from pick-events (same as calling `compass.set_pickable(False)`)


        Parameters
        ----------
        pos : tuple or None, optional
            The relative position of the compass with respect to the axis.
            (0,0) - lower left corner, (1,1) - upper right corner
            Note that you can also move the compass with the mouse!
        scale : float, optional
            A scale-factor for the size of the compass. The default is 10.
        style : str, optional

            - "north arrow" : draw only a north-arrow
            - "compass": draw a compass with arrows in all 4 directions

            The default is "compass".
        patch : False, str or tuple, optional
            The color of the background-patch.
            (can be any color specification supported by matplotlib)
            The default is "w".
        txt : str, optional
            Indicator which directions should be indicated.
            - "NESW" : add letters for all 4 directions
            - "NE" : add only letters for North and East (same for other combinations)
            - None : don't add any letters
            The default is "N".
        pickable : bool, optional
            Indicator if the compass should be static (False) or if it can be dragged
            with the mouse (True). The default is True

        Returns
        -------
        compass : eomaps.Compass
            A compass-object that can be used to manually adjust the style and position
            of the compass or remove it from the map.

        """

        c = Compass(weakref.proxy(self))
        c(pos=pos, scale=scale, style=style, patch=patch, txt=txt, pickable=pickable)
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
    ):

        s = ScaleBar(
            m=self,
            preset=preset,
            scale=scale,
            autoscale_fraction=autoscale_fraction,
            auto_position=auto_position,
            scale_props=scale_props,
            patch_props=patch_props,
            label_props=label_props,
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
            return self._wms_container

    @wraps(plt.savefig)
    def savefig(self, *args, **kwargs):
        # clear all cached background layers before saving to make sure they
        # are re-drawn with the correct dpi-settings
        self.BM._bg_layers = dict()
        self.figure.f.savefig(*args, **kwargs)
        # redraw after the save to ensure that backgrounds are correctly cached
        self.redraw()

    def _shade_map(
        self,
        pick_distance=100,
        verbose=0,
        layer=None,
        dynamic=False,
        set_extent=True,
        **kwargs,
    ):
        """
        Plot the dataset using the (very fast) "datashader" library.
        (requires `datashader`... use `conda install -c conda-forge datashader`)

        - This method is intended for extremely large datasets
          (up to millions of datapoints)!

        A dynamically updated "shaded" map will be generated.
        Note that the datapoints in this case are NOT represented by the shapes
        defined as `m.set_shape`!

        - By default, the shading is performed using a "mean"-value aggregation hook

        kwargs :
            kwargs passed to `datashader.mpl_ext.dsshow`

        """
        try:
            from datashader.mpl_ext import dsshow
        except ImportError:
            raise ImportError(
                "EOmaps: Missing dependency: 'datashader' \n ... please install"
                + " (conda install -c conda-forge datashader) to use the plot-shapes"
                + "'shade_points' and 'shade_raster'"
            )
        # remove previously fetched backgrounds for the used layer
        if layer in self.BM._bg_layers and dynamic is False:
            del self.BM._bg_layers[layer]
            # self.BM._refetch_bg = True

        if verbose:
            print("EOmaps: Preparing the data")
        # ---------------------- prepare the data
        props = self._prepare_data()
        if len(props["z_data"]) == 0:
            print("EOmaps: there was no data to plot")
            return

        # remember props for later use
        self._props = props

        z_finite = np.isfinite(props["z_data"])

        vmin = self.plot_specs["vmin"]
        if self.plot_specs["vmin"] is None:
            vmin = np.nanmin(props["z_data"])
        vmax = self.plot_specs["vmax"]
        if self.plot_specs["vmax"] is None:
            vmax = np.nanmax(props["z_data"])

        # clip the data to properly account for vmin and vmax
        # (do this only if we don't intend to use the full dataset!)
        if self.plot_specs["vmin"] or self.plot_specs["vmax"]:
            props["z_data"] = props["z_data"].clip(vmin, vmax)

        if verbose:
            print("EOmaps: Classifying...")

        # ---------------------- classify the data
        cbcmap, norm, bins, classified = self._classify_data(
            vmin=vmin,
            vmax=vmax,
            classify_specs=self.classify_specs,
        )

        self.classify_specs._cbcmap = cbcmap
        self.classify_specs._norm = norm
        self.classify_specs._bins = bins
        self.classify_specs._classified = classified

        if verbose:
            print("EOmaps: Plotting...")

        # convert to float to pass masked values to datashader as np.nan
        zdata = self.classify_specs._norm(props["z_data"]).astype(float)
        if len(zdata) == 0:
            print("EOmaps: there was no data to plot")
            return

        # re-evaluate vmin and vmax after normalization
        vmin, vmax = self.classify_specs._norm([vmin, vmax]).astype(float)
        # re-instate masked values
        zdata[~z_finite] = np.nan

        # df = df[
        #     np.logical_and(
        #         np.logical_and(df.x > x0, df.x < x1),
        #         np.logical_and(df.y > y0, df.y < y1),
        #     )
        # ]

        plot_width, plot_height = int(self.ax.bbox.width), int(self.ax.bbox.height)

        # get rid of unnecessary dimensions in the numpy arrays
        zdata = zdata.squeeze()
        props["x0"] = props["x0"].squeeze()
        props["y0"] = props["y0"].squeeze()

        if self.shape.name == "shade_raster":
            from datashader import glyphs

            assert _xar_OK, "EOmaps: missing dependency `xarray` for 'shade_raster'"
            if len(zdata.shape) == 2:
                if (zdata.shape == props["x0"].shape) and (
                    zdata.shape == props["y0"].shape
                ):
                    # use a curvilinear QuadMesh
                    self.shape.glyph = glyphs.QuadMeshCurvilinear("x", "y", "val")

                    # 2D coordinates and 2D raster
                    df = xar.Dataset(
                        data_vars=dict(val=(["xx", "yy"], zdata)),
                        # dims=["x", "y"],
                        coords=dict(
                            x=(["xx", "yy"], props["x0"]), y=(["xx", "yy"], props["y0"])
                        ),
                    )
                elif (
                    ((zdata.shape[1],) == props["x0"].shape)
                    and ((zdata.shape[0],) == props["y0"].shape)
                    and (props["x0"].shape != props["y0"].shape)
                ):
                    raise AssertionError(
                        "EOmaps: it seems like you need to transpose your data! \n"
                        + f"the dataset has a shape of {zdata.shape}, but the "
                        + f"coordinates suggest ({props['x0'].shape}, {props['x0'].shape})"
                    )
                elif (zdata.T.shape == props["x0"].shape) and (
                    zdata.T.shape == props["y0"].shape
                ):
                    raise AssertionError(
                        "EOmaps: it seems like you need to transpose your data! \n"
                        + f"the dataset has a shape of {zdata.shape}, but the "
                        + f"coordinates suggest {props['x0'].shape}"
                    )

                elif ((zdata.shape[0],) == props["x0"].shape) and (
                    (zdata.shape[1],) == props["y0"].shape
                ):
                    # use a rectangular QuadMesh
                    self.shape.glyph = glyphs.QuadMeshRectilinear("x", "y", "val")
                    # 1D coordinates and 2D data
                    df = xar.DataArray(
                        data=zdata,
                        dims=["x", "y"],
                        coords=dict(x=props["x0"], y=props["y0"]),
                    )
                    df = xar.Dataset(dict(val=df))
            else:
                # first convert 1D inputs to 2D, then reproject the grid and use
                # a curvilinear QuadMesh to display the data

                # use pandas to convert to 2D
                df = (
                    pd.DataFrame(
                        dict(
                            x=props["xorig"].ravel(),
                            y=props["yorig"].ravel(),
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
                self.shape.glyph = glyphs.QuadMeshCurvilinear("x", "y", "val")

                df = xar.Dataset(
                    data_vars=dict(val=(["xx", "yy"], df.val.values.T)),
                    coords=dict(x=(["xx", "yy"], xg), y=(["xx", "yy"], yg)),
                )

            # once the data is shaded, convert to 1D for further processing
            self._1Dprops(props)

        else:
            df = pd.DataFrame(
                dict(x=props["x0"].ravel(), y=props["y0"].ravel(), val=zdata.ravel()),
                copy=False,
            )

        if set_extent is True:
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

        coll = dsshow(
            df,
            glyph=self.shape.glyph,
            aggregator=self.shape.aggregator,
            shade_hook=self.shape.shade_hook,
            agg_hook=self.shape.agg_hook,
            # norm="eq_hist",
            norm=plt.Normalize(vmin, vmax),
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

        self.figure.coll = coll
        if verbose:
            print("EOmaps: Indexing for pick-callbacks...")

        if pick_distance is not None:
            # self.tree = cKDTree(np.stack([props["x0"], props["y0"]], axis=1))
            self.tree = searchtree(m=self._proxy(self), pick_distance=pick_distance)

            self.cb.pick._set_artist(coll)
            self.cb.pick._init_cbs()
            self.cb.pick._pick_distance = pick_distance
            self.cb._methods.append("pick")

        if dynamic is True:
            self.BM.add_artist(coll)
        else:
            self.BM.add_bg_artist(coll, layer)

        if dynamic is True:
            self.BM.update(clear=False)

    @staticmethod
    def _1Dprops(props):

        # convert all arrays in props to a proper 1D representation that will be used
        # to index and identify points

        # Note: _prepare_data already converts datasets to 1D if
        #       a shape that accepts non-rectangular datasets is used!

        # Note: both ravel and meshgrid return views!
        n_coord_shape = len(props["xorig"].shape)

        props["x0"], props["y0"] = (
            props["x0"].ravel(),
            props["y0"].ravel(),
        )
        props["xorig"], props["yorig"] = (
            props["xorig"].ravel(),
            props["yorig"].ravel(),
        )

        # in case 2D data and 1D coordinate arrays are provided, use a meshgrid
        # to identify the coordinates
        if n_coord_shape == 1 and len(props["z_data"].shape) == 2:

            props["x0"], props["y0"] = [
                i
                for i in np.broadcast_arrays(
                    *np.meshgrid(props["x0"], props["y0"], copy=False, sparse=True)
                )
            ]

            props["xorig"], props["yorig"] = [
                i
                for i in np.broadcast_arrays(
                    *np.meshgrid(
                        props["xorig"], props["yorig"], copy=False, sparse=True
                    )
                )
            ]

            # props["x0"], props["y0"] = [
            #     np.ravel(i) for i in np.meshgrid(props["x0"], props["y0"], copy=False)
            # ]
            # props["xorig"], props["yorig"] = [
            #     np.ravel(i)
            #     for i in np.meshgrid(props["xorig"], props["yorig"], copy=False)
            # ]

            # transpose since 1D coordinates are expected to be provided as (y, x)
            # and NOT as (x, y)
            props["z_data"] = props["z_data"].T.ravel()

        else:
            props["z_data"] = props["z_data"].ravel()

    def _memmap_props(self, dir=None):
        # memory-map all datasets in the self._props dict to free memory while
        # keeping all callbacks etc. responsive.
        if not hasattr(self.parent, "_tmpfolder"):
            if isinstance(dir, (str, Path)):
                self.parent._tmpfolder = TemporaryDirectory(dir=dir)
            else:
                self.parent._tmpfolder = TemporaryDirectory()

        memmaps = dict()

        for key, data in self._props.items():
            # don't memmap x0 and y0 since they are needed to identify points
            # (e.g. they would be loaded to memory as soon as a point is clicked)
            if key in ["x0", "y0"]:
                continue
            file = TemporaryFile(
                prefix=key + "__", suffix=".dat", dir=self.parent._tmpfolder.name
            )

            # filename = path.join(tmpfolder.name, f'{key}.dat')
            args = dict(filename=file, dtype="float32", shape=data.shape)

            fp = np.memmap(**args, mode="w+")

            fp[:] = data[:]  # write the data to the memmap object
            fp.flush()  # flush the data to disk

            # replace the file in memory with the memmap
            memmaps[key] = np.memmap(**args, mode="r")

        for key, val in memmaps.items():
            self._props[key] = val

    def _plot_map(
        self,
        pick_distance=100,
        layer=None,
        dynamic=False,
        set_extent=True,
        **kwargs,
    ):

        if "coastlines" in kwargs:
            kwargs.pop("coastlines")
            warnings.warn(
                "EOmaps: the 'coastlines' kwarg for 'plot_map' is depreciated!"
                + "Instead use "
                + "\n    m.add_feature.preset.ocean()"
                + "\n    m.add_feature.preset.coastline()"
                + " instead!"
            )

        ax = self.figure.ax

        cmap = kwargs.pop("cmap", None)
        if cmap is not None:
            self.plot_specs.cmap = cmap

        for key in ("array", "norm"):
            assert (
                key not in kwargs
            ), f"The key '{key}' is assigned internally by EOmaps!"

        try:
            # remove previously fetched backgrounds for the used layer
            if layer in self.BM._bg_layers and dynamic is False:
                del self.BM._bg_layers[layer]
                # self.BM._refetch_bg = True

            if self.data is None:
                return

            # ---------------------- prepare the data
            props = self._prepare_data()

            # remember props for later use
            self._props = props

            vmin = self.plot_specs["vmin"]
            if self.plot_specs["vmin"] is None:
                vmin = np.nanmin(props["z_data"])
            vmax = self.plot_specs["vmax"]
            if self.plot_specs["vmax"] is None:
                vmax = np.nanmax(props["z_data"])

            # clip the data to properly account for vmin and vmax
            # (do this only if we don't intend to use the full dataset!)
            if self.plot_specs["vmin"] or self.plot_specs["vmax"]:
                props["z_data"] = props["z_data"].clip(vmin, vmax)

            # ---------------------- classify the data
            cbcmap, norm, bins, classified = self._classify_data(
                vmin=vmin,
                vmax=vmax,
                classify_specs=self.classify_specs,
            )

            self.classify_specs._cbcmap = cbcmap
            self.classify_specs._norm = norm
            self.classify_specs._bins = bins
            self.classify_specs._classified = classified

            # ------------- plot the data

            # don't pass the array if explicit facecolors are set
            if (
                ("color" in kwargs and kwargs["color"] is not None)
                or ("facecolor" in kwargs and kwargs["facecolor"] is not None)
                or ("fc" in kwargs and kwargs["fc"] is not None)
            ):
                args = dict(array=None, cmap=None, norm=None, **kwargs)
            else:
                args = dict(array=props["z_data"], cmap=cbcmap, norm=norm, **kwargs)

            coll = self.shape.get_coll(
                props["xorig"].ravel(), props["yorig"].ravel(), "in", **args
            )

            coll.set_clim(vmin, vmax)
            ax.add_collection(coll)

            self.figure.coll = coll

            if pick_distance is not None:
                self.tree = searchtree(m=self._proxy(self), pick_distance=pick_distance)

                self.cb.pick._set_artist(coll)
                self.cb.pick._init_cbs()
                self.cb.pick._pick_distance = pick_distance
                self.cb._methods.append("pick")

            if dynamic is True:
                self.BM.add_artist(coll)
            else:
                self.BM.add_bg_artist(coll, layer)

            if set_extent:
                # set the image extent
                # get the extent of the added collection
                b = self.figure.coll.get_datalim(ax.transData)
                ymin, ymax = ax.projection.y_limits
                xmin, xmax = ax.projection.x_limits
                # set the axis-extent
                ax.set_xlim(max(b.xmin, xmin), min(b.xmax, xmax))
                ax.set_ylim(max(b.ymin, ymin), min(b.ymax, ymax))

            self.figure.f.canvas.draw_idle()

        except Exception as ex:
            raise ex

    def plot_map(
        self,
        pick_distance=100,
        layer=None,
        dynamic=False,
        set_extent=True,
        memmap=False,
        **kwargs,
    ):
        """
        Actually generate the map-plot based on the data provided as `m.data` and the
        specifications defined in "data_specs", "plot_specs" and "classify_specs".

        NOTE
        ----
        Each call to plot_map will replace the collection used for picking!
        (only the last collection remains interactive on multiple calls to `m.plot_map()`)

        If you need multiple responsive datasets, use a new layer for each dataset!
        (e.g. via `m2 = m.new_layer()`)

        Parameters
        ----------
        pick_distance : int or None
            If None, NO pick-callbacks will be assigned (e.g. 'm.cb.pick' will not work)
            (useful for very large datasets to speed up plotting and save memory)

            If int, it will be used to determine the search-area used to identify
            clicked pixels (e.g. a rectangle with a edge-size of
            `pick_distance * estimated radius`).

            The default is 100.
        layer : int, str or None
            The layer at which the dataset will be plotted.
            ONLY relevant if dynamic = False!

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
        memmap : bool, str or pathlib.Path
            Use memory-mapping to save some memory by storing intermediate datasets
            (e.g. projected coordinates, indexes & the data) in a temporary folder on
            disc rather than keeping everything in memory.
            This causes a slight performance penalty when identifying clicked points but
            it can provide a reduction in memory-usage for very large datasets
            (or for a very large number of interactive layers).

            - If None: memory-mapping is only used if "shade_raster" or "shade_points"
              is used as plot-shape.
            - if False: memory-mapping is disabled
            - if True: memory-mapping is used with an automatically located tempfolder
            - if str or pathlib.Path: memory-mapping is used and the provided folder
              is used as location for the temporary files (stored in a temp-subfolder).

            NOTE: The tempfolder and all files will be deleted if the figure is closed,
            the Maps-object is deleted or the kernel is interrupted!

            The location of the tempfolder is accessible via `m._tempfolder`

            The default is False.

        kwargs
            kwargs passed to the initialization of the matpltolib collection
            (dependent on the plot-shape) [linewidth, edgecolor, facecolor, ...]

            For "shade_points" or "shade_raster" shapes, kwargs are passed to
            `datashader.mpl_ext.dsshow`
        """
        if layer is None:
            layer = self.layer

        if self.shape.name.startswith("shade"):
            self._shade_map(
                pick_distance=pick_distance,
                layer=layer,
                dynamic=dynamic,
                set_extent=set_extent,
                **kwargs,
            )
        else:
            self._plot_map(
                pick_distance=pick_distance,
                layer=layer,
                dynamic=dynamic,
                set_extent=set_extent,
                **kwargs,
            )

        # after plotting, use memory-mapping to store datasets required by
        # callbacks etc. so that we don't need to keep them in memory.
        if memmap:
            self._memmap_props(dir=memmap)

    def add_colorbar(
        self,
        gs=0.2,
        orientation="horizontal",
        label=None,
        density=None,
        histbins=None,
        tick_precision=None,
        top=0.05,
        bottom=0.1,
        left=0.1,
        right=0.05,
        layer=None,
        log=False,
    ):
        """
        Add a colorbar to an existing figure.

        The colorbar always represents the data of the associated Maps-object
        that was assigned in the last call to `m.plot_map()`.

        By default, the colorbar will only be visible on the layer of the associated
        Maps-object (you can override this by providing an explicit "layer"-name).

        To change the position of the colorbar, use:

            >>> cb = m.add_colorbar(gs)
            >>> m.figure.set_colorbar_position(pos, cb=cb)

        Parameters
        ----------
        gs : float or matpltolib.gridspec.SubplotSpec
            - if float: The fraction of the the parent axes to use for the colorbar.
              (The colorbar will "steal" some space from the parent axes.)
            - if SubplotSpec : A SubplotSpec instance that will be used to initialize
              the colorbar.

            The default is 0.2.
        orientation : str
            The orientation of the colorbar ("horizontal" or "vertical")
            The default is "horizontal"
        label : str or None
            The label of the colorbar.
            If None, the parameter-name (e.g. `m.data_specs.parameter`) is used.
            The default is None.
        density : bool or None
            Indicator if the y-axis of the histogram should represent the
            probability-density (True) or the number of counts per bin (False)
            If None, the value assigned in `m.plot_specs.density` is used.
            The default is None.
        histbins : int, list, tuple, array or "bins", optional
            - If int: The number of histogram-bins to use for the colorbar.
            - If list, tuple or numpy-array: the bins to use
            - If "bins": use the bins obtained from the classification
              (ONLY possible if a classification scheme is used!)

            The default is 256.
        tick_precision : int or None
            The precision of the tick-labels in the colorbar. The default is 2.
            If None, the value assigned in `m.plot_specs.tick_precision` is used.
            The default is None.
        top, bottom, left, right : float
            The padding between the colorbar and the parent axes (as fraction of the
            plot-height (if "horizontal") or plot-width (if "vertical")
            The default is (0.05, 0.1, 0.1, 0.05)
        layer : int, str or None, optional
            The layer to put the colorbar on.
            To make the colorbar visible on all layers, use `layer="all"`
            If None, the layer of the associated Maps-object is used.
            The default is None.
        log : bool, optional
            Indicator if the y-axis of the plot should be logarithmic or not.
            The default is False

        Notes
        -----
        Here's how the padding looks like as a scetch:

        >>> _________________________________________________________
        >>> |[ - - - - - - - - - - - - - - - - - - - - - - - - - - ]|
        >>> |[ - - - - - - - - - - - - MAP - - - - - - - - - - - - ]|
        >>> |[ - - - - - - - - - - - - - - - - - - - - - - - - - - ]|
        >>> |                                                       |
        >>> |                         (top)                         |
        >>> |                                                       |
        >>> |      (left)       [ - COLORBAR  - ]      (right)      |
        >>> |                                                       |
        >>> |                       (bottom)                        |
        >>> |_______________________________________________________|

        """

        if hasattr(self, "_colorbar"):
            print(
                "EOmaps: A colorbar already exists for this Maps-object!\n"
                + "...use a new layer if you want multiple colorbars!"
            )
            return

        if layer is None:
            layer = self.layer

        assert hasattr(
            self.classify_specs, "_bins"
        ), "EOmaps: you need to call `m.plot_map()` before adding a colorbar!"

        # check if there is already an existing colorbar in another axis
        # and if we find one, use its specs instead of creating a new one
        parent_m_for_cb = None
        if hasattr(self, "_ax_cb"):
            parent_m_for_cb = self
        else:
            # check if self is actually just another layer of an existing Maps object
            # that already has a colorbar assigned
            for m in [self.parent, *self.parent._children]:
                if m is not self and m.ax is self.ax:
                    if hasattr(m, "_ax_cb"):
                        parent_m_for_cb = m
                        break

        if parent_m_for_cb:
            try:
                if (
                    parent_m_for_cb._cb_gridspec.nrows == 2
                    and parent_m_for_cb._cb_gridspec.ncols == 1
                ):
                    cb_orientation = "vertical"
                else:
                    cb_orientation = "horizontal"
            except AttributeError:
                print(
                    "EOmaps: could not add colorbar... maybe a colorbar for the"
                    f"layer {layer} already exists?"
                )
                return

        if parent_m_for_cb is None:
            # initialize colorbar axes
            if isinstance(gs, float):
                frac = gs
                gs = self.figure.ax.get_subplotspec()
                # get the original subplot-spec of the axes, and divide it based on
                # the fraction that is intended for the colorbar
                if orientation == "horizontal":
                    gs = GridSpecFromSubplotSpec(
                        4,
                        3,
                        gs,
                        height_ratios=(1, top, frac, bottom),
                        width_ratios=(left, 1, right),
                        wspace=0,
                        hspace=0,
                    )
                    self.figure.ax.set_subplotspec(gs[0, :])
                    gsspec = gs[2, 1]

                elif orientation == "vertical":
                    gs = GridSpecFromSubplotSpec(
                        3,
                        4,
                        gs,
                        width_ratios=(1, top, frac, bottom),
                        height_ratios=(left, 1, right),
                        hspace=0,
                        wspace=0,
                    )
                    self.figure.ax.set_subplotspec(gs[:, 0])
                    gsspec = gs[1, 2]

                else:
                    raise AssertionError("'{orientation}' is not a valid orientation")
            else:
                gsspec = gs

            if orientation == "horizontal":
                # sub-gridspec for the colorbar
                cbgs = GridSpecFromSubplotSpec(
                    nrows=2,
                    ncols=1,
                    subplot_spec=gsspec,
                    hspace=0,
                    wspace=0,
                    height_ratios=[0.9, 0.1],
                )

                # "_add_colorbar" orientation is opposite to the colorbar-orientation!
                cb_orientation = "vertical"

            elif orientation == "vertical":
                # sub-gridspec for the colorbar
                cbgs = GridSpecFromSubplotSpec(
                    nrows=1,
                    ncols=2,
                    subplot_spec=gsspec,
                    hspace=0,
                    wspace=0,
                    width_ratios=[0.9, 0.1],
                )

                # "_add_colorbar" orientation is opposite to the colorbar-orientation!
                cb_orientation = "horizontal"
        else:
            cbgs = parent_m_for_cb._cb_gridspec
            # cbgs = [
            #     parent_m_for_cb.figure.ax_cb.get_gridspec()[0],
            #     parent_m_for_cb.figure.ax_cb_plot.get_gridspec()[1],
            # ]

        ax_cb = self.figure.f.add_subplot(
            cbgs[1],
            frameon=False,
            label="ax_cb",
        )
        ax_cb_plot = self.figure.f.add_subplot(
            cbgs[0],
            frameon=False,
            label="ax_cb_plot",
        )

        # join colorbar and histogram axes
        if cb_orientation == "horizontal":
            ax_cb_plot.get_shared_y_axes().join(ax_cb_plot, ax_cb)
        elif cb_orientation == "vertical":
            ax_cb_plot.get_shared_x_axes().join(ax_cb_plot, ax_cb)

        cb = self._add_colorbar(
            ax_cb=ax_cb,
            ax_cb_plot=ax_cb_plot,
            bins=self.classify_specs._bins,
            cmap=self.classify_specs._cbcmap,
            norm=self.classify_specs._norm,
            classified=self.classify_specs._classified,
            orientation=cb_orientation,
            label=label,
            density=density,
            tick_precision=tick_precision,
            histbins=histbins,
            log=log,
        )

        # hide the colorbar if it is not added to the currently visible layer
        if layer not in [self.BM._bg_layer, "all"]:
            ax_cb.set_visible(False)
            ax_cb_plot.set_visible(False)
            m.BM._hidden_axes.add(ax_cb)
            m.BM._hidden_axes.add(ax_cb_plot)

        self._ax_cb = ax_cb
        self._ax_cb_plot = ax_cb_plot
        self._cb_gridspec = cbgs

        self.BM.add_bg_artist(self._ax_cb, layer)
        self.BM.add_bg_artist(self._ax_cb_plot, layer)

        # remember colorbar for later (so that we can update its position etc.)
        self._colorbar = [layer, cbgs, ax_cb, ax_cb_plot, orientation, cb]

        return [layer, cbgs, ax_cb, ax_cb_plot, orientation, cb]

    def indicate_masked_points(self, radius=1.0, **kwargs):
        """
        Add circles to the map that indicate masked points.
        (e.g. points resulting in very distorted shapes etc.)

        Parameters
        ----------
        radius : float, optional
            The readius to use for plotting the indicators for the masked
            points. The unit of the radius is map-pixels! The default is 1.
        **kwargs :
            additional kwargs passed to `m.plot_map(**kwargs)`.

        Returns
        -------
        m : eomaps.Maps
            A (connected) copy of the maps-object with the data set to the masked pixels.
        **kwargs
            additional kwargs passed to `m.plot_map(**kwargs)`
        """
        if not hasattr(self, "_data_mask"):
            print("EOmaps: There are no masked points to indicate!")
            return
        data = self.data[~self._data_mask]

        if len(data) == 0:
            print("EOmaps: There are no masked points to indicate!")
            return

        m = self.new_layer(copy_data_specs=True)
        m.data = data

        t = self.figure.ax.transData.inverted()
        r = (t.transform((100 + radius, 100 + radius)) - t.transform((100, 100))).mean()
        m.set_shape.ellipses(radius_crs="out", radius=r)
        m.plot_map(**kwargs)
        return m

    if _gpd_OK:

        @staticmethod
        def _make_rect_poly(x0, y0, x1, y1, crs=None, npts=100):
            """
            return a geopandas.GeoDataFrame with a rectangle in the given crs

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
            from shapely.geometry import Polygon

            xs, ys = np.linspace([x0, y0], [x1, y1], npts).T
            x0, y0, x1, y1, xs, ys = np.broadcast_arrays(x0, y0, x1, y1, xs, ys)
            verts = np.column_stack(
                ((x0, ys), (xs, y1), (x1, ys[::-1]), (xs[::-1], y0))
            ).T

            gdf = gpd.GeoDataFrame(geometry=[Polygon(verts)])
            gdf.set_crs(crs, inplace=True)

            return gdf

        def indicate_extent(self, x0, y0, x1, y1, crs=4326, npts=100, **kwargs):
            """
            Indicate a rectangular extent in a given crs on the map.
            (the rectangle is drawn as a polygon where each line is divided by "npts"
            points to ensure correct re-projection of the shape to other crs)

            Parameters
            ----------
            x0, y0, y1, y1 : float
                the boundaries of the shape
            npts : int, optional
                The number of points used to draw the polygon-lines.
                (e.g. to correctly display curvature in projected coordinate-systems)
                The default is 100.
            crs : any, optional
                a coordinate-system identifier.
                The default is 4326 (e.g. lon/lat).
            kwargs :
                additional keyword-arguments passed to `m.add_gdf()`.

            """

            gdf = self._make_rect_poly(x0, y0, x1, y1, self.get_crs(crs), npts)
            self.add_gdf(gdf, **kwargs)

    def add_logo(self, filepath=None, position="lr", size=0.12, pad=0.1):
        """
        Add a small image (png, jpeg etc.) to the map whose position is dynamically
        updated if the plot is resized or zoomed.

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
        """

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

        figax = self.figure.f.add_axes(**getpos(self.ax.get_position()))
        figax.set_navigate(False)
        figax.set_axis_off()
        art = figax.imshow(im, aspect="equal", zorder=999)
        self.BM.add_artist(art)

        def setlim(*args, **kwargs):
            figax.set_position(getpos(self.ax.get_position())["rect"])

        def update_decorator(f):
            # use this so that we can "undecorate" the function with the
            # __wrapped__ property
            @wraps(f)
            def newf(*args, **kwargs):
                ret = f(*args, **kwargs)
                setlim()
                return ret

            return newf

        toolbar = self.figure.f.canvas.toolbar
        if toolbar is not None:
            toolbar._update_view = update_decorator(toolbar._update_view)
            toolbar.release_zoom = update_decorator(toolbar.release_zoom)
            toolbar.release_pan = update_decorator(toolbar.release_pan)

        def cleanup():
            toolbar._update_view = toolbar._update_view.__wrapped__
            toolbar.release_zoom = toolbar.release_zoom.__wrapped__
            toolbar.release_pan = toolbar.release_pan.__wrapped__

        self._cleanup_functions.add(cleanup)

        self._logo_cids.add(self.figure.f.canvas.mpl_connect("resize_event", setlim))

    def show_layer(self, name):
        """
        Display the selected layer on the map.

        See Also
        --------
        - Maps.util.layer_selector
        - Maps.util.layer_slider

        Parameters
        ----------
        name : str or int, optional
            The name of the layer to activate.
            The default is None.
        """
        layers = self._get_layers()

        if name not in layers:
            lstr = " - " + "\n - ".join(map(str, layers))

            raise AssertionError(
                f"EOmaps: The layer '{name}' does not exist...\n"
                + f"Use one of: \n{lstr}"
            )

        # invoke the bg_layer setter of the blit-manager
        self.BM.bg_layer = name
        # self.BM.canvas.draw_idle()
        self.BM.update()

    def redraw(self):
        """
        Force a re-draw of all cached background layers.
        This will make sure that actions not managed by EOmaps are also properly drawn.

        - Use this at the very end of your code to trigger a final re-draw!

        Note
        ----
        Don't use this in an interactive context since it will trigger a re-draw
        of all background-layers!

        To make an artist dynamically updated if you interact with the map, use:

        >>> m.BM.add_artist(artist)
        """

        self.BM._refetch_bg = True
        self.BM.canvas.draw()

    @wraps(GridSpec.update)
    def subplots_adjust(self, **kwargs):
        self.parent.figure.gridspec.update(**kwargs)
        # after changing margins etc. a redraw is required
        # to fetch the updated background!
        self.redraw()

    def _get_layers(self, exclude=None):
        # return a list of all (empty and non-empty) layer-names
        layers = set((m.layer for m in self.parent._children))
        # add layers that are not yet activated (but have an activation
        # method defined...)
        layers = layers.union(set(self.BM._on_layer_activation))
        # add all (possibly still invisible) layers with artists defined
        layers = layers.union(set(self.BM._bg_artists))

        if exclude:
            for l in exclude:
                if l in layers:
                    layers.remove(l)

        # sort the layers
        layers = sorted(layers, key=lambda x: str(x))

        return layers


class MapsGrid:
    """
    Initialize a grid of Maps objects

    Parameters
    ----------
    r : int, optional
        The number of rows. The default is 2.
    c : int, optional
        The number of columns. The default is 2.
    crs : int or a cartopy-projection, optional
        The projection that will be assigned to all Maps objects.
        (you can still change the projection of individual Maps objects later!)
        See the doc of "Maps" for details.
        The default is 4326.
    m_inits : dict, optional
        A dictionary that is used to customize the initialization the Maps-objects.

        The keys of the dictionaries are used as names for the Maps-objects,
        (accessible via `mgrid.m_<name>` or `mgrid[m_<name>]`) and the values are used to
        identify the position of the axes in the grid.

        Possible values are:
        - a tuple of (row, col)
        - an integer representing (row + col)

        Note: If either `m_inits` or `ax_inits` is provided, ONLY objects with the
        specified properties are initialized!

        The default is None in which case a unique Maps-object will be created
        for each grid-cell (accessible via `mgrid.m_<row>_<col>`)
    ax_inits : dict, optional
        Completely similar to `m_inits` but instead of `Maps` objects, ordinary
        matplotlib axes will be initialized. They are accessible via `mg.ax_<name>`.

        Note: If you iterate over the MapsGrid object, ONLY the initialized Maps
        objects will be returned!
    figsize : (float, float)
        The width and height of the figure.
    layer : int or str
        The default layer to assign to all Maps-objects of the grid.
        The default is 0.
    kwargs
        Additional keyword-arguments passed to the `matplotlib.gridspec.GridSpec()`
        function that is used to initialize the grid.

    Attributes
    ----------
    f : matplotlib.figure
        The matplotlib figure object
    gridspec : matplotlib.GridSpec
        The matplotlib GridSpec instance used to initialize the axes.
    m_<identifier> : eomaps.Maps objects
        The individual Maps-objects can be accessed via `mgrid.m_<identifier>`
        The identifiers are hereby `<row>_<col>` or the keys of the `m_inits`
        dictionary (if provided)
    ax_<identifier> : matplotlib.axes
        The individual (ordinary) matplotlib axes can be accessed via
        `mgrid.ax_<identifier>`. The identifiers are hereby the keys of the
        `ax_inits` dictionary (if provided).
        Note: if `ax_inits` is not specified, NO ordinary axes will be created!


    Methods
    -------
    join_limits :
        join the axis-limits of maps that share the same projection
    share_click_events :
        share click-callback events between the Maps-objects
    share_pick_events :
        share pick-callback events between the Maps-objects
    create_axes :
        create a new (ordinary) matplotlib axes
    add_<...> :
        call the underlying `add_<...>` method on all Maps-objects of the grid
    set_<...> :
        set the corresponding property on all Maps-objects of the grid
    subplots_adjust :
        Dynamically adjust the layout of the subplots, e.g:

        >>> mg.subplots_adjust(left=0.1, right=0.9,
        >>>                    top=0.8, bottom=0.1,
        >>>                    wspace=0.05, hspace=0.25)

    Examples
    --------
    To initialize a 2 by 2 grid with a large map on top, a small map
    on the bottom-left and an ordinary matplotlib plot on the bottom-right, use:

    >>> m_inits = dict(top = (0, slice(0, 2)),
    >>>                bottom_left=(1, 0))
    >>> ax_inits = dict(bottom_right=(1, 1))

    >>> mg = MapsGrid(2, 2, m_inits=m_inits, ax_inits=ax_inits)
    >>> mg.m_top.plot_map()
    >>> mg.m_bottom_left.plot_map()
    >>> mg.ax_bottom_right.plot([1,2,3])

    Returns
    -------
    eomaps.MapsGrid
        Accessor to the Maps objects "m_{row}_{column}".

    Notes
    -----

    - To perform actions on all Maps-objects of the grid, simply iterate over
      the MapsGrid object!
    """

    def __init__(
        self,
        r=2,
        c=2,
        crs=None,
        m_inits=None,
        ax_inits=None,
        figsize=None,
        layer=0,
        **kwargs,
    ):

        self._Maps = []
        self._names = defaultdict(list)

        self._wms_container = wms_container(self)

        gskwargs = dict(bottom=0.01, top=0.99, left=0.01, right=0.99)
        gskwargs.update(kwargs)
        self.gridspec = GridSpec(nrows=r, ncols=c, **gskwargs)

        if m_inits is None and ax_inits is None:
            if isinstance(crs, list):
                crs = np.array(crs).reshape((r, c))
            else:
                crs = np.broadcast_to(crs, (r, c))

            self._custom_init = False
            for i in range(r):
                for j in range(c):
                    crsij = crs[i, j]
                    if isinstance(crsij, np.generic):
                        crsij = crsij.item()

                    if i == 0 and j == 0:
                        # use crs[i, j].item() to convert to native python-types
                        # (instead of numpy-dtypes)  ... check numpy.ndarray.item
                        mij = Maps(
                            crs=crsij,
                            gs_ax=self.gridspec[0, 0],
                            figsize=figsize,
                            layer=layer,
                        )
                        self.parent = mij
                    else:
                        mij = Maps(
                            crs=crsij,
                            parent=self.parent,
                            gs_ax=self.gridspec[i, j],
                            layer=layer,
                        )

                    self._Maps.append(mij)
                    name = f"{i}_{j}"
                    self._names["Maps"].append(name)
                    setattr(self, "m_" + name, mij)
        else:
            self._custom_init = True
            if m_inits is not None:
                if not isinstance(crs, dict):
                    if isinstance(crs, np.generic):
                        crs = crs.item()

                    crs = {key: crs for key in m_inits}

                assert self._test_unique_str_keys(
                    m_inits
                ), "EOmaps: there are duplicated keys in m_inits!"

                for i, [key, val] in enumerate(m_inits.items()):
                    if ax_inits is not None:
                        q = set(m_inits).intersection(set(ax_inits))
                        assert (
                            len(q) == 0
                        ), f"You cannot provide duplicate keys! Check: {q}"

                    if i == 0:
                        mi = Maps(
                            crs=crs[key],
                            gs_ax=self.gridspec[val],
                            figsize=figsize,
                            layer=layer,
                        )
                        self.parent = mi
                    else:
                        mi = Maps(
                            crs=crs[key],
                            parent=self.parent,
                            gs_ax=self.gridspec[val],
                            layer=layer,
                        )

                    name = str(key)
                    self._names["Maps"].append(name)

                    self._Maps.append(mi)
                    setattr(self, f"m_{name}", mi)

            if ax_inits is not None:
                assert self._test_unique_str_keys(
                    ax_inits
                ), "EOmaps: there are duplicated keys in ax_inits!"
                for key, val in ax_inits.items():
                    self.create_axes(val, name=key)

    def cleanup(self):
        for m in self:
            m.cleanup()

    @staticmethod
    def _test_unique_str_keys(x):
        # check if all keys are unique (as strings)
        seen = set()
        return not any(str(i) in seen or seen.add(str(i)) for i in x)

    def __iter__(self):
        return iter(self._Maps)

    def __getitem__(self, key):
        try:
            if self._custom_init is False:
                if isinstance(key, str):
                    r, c = map(int, key.split("_"))
                elif isinstance(key, (list, tuple)):
                    r, c = key
                else:
                    raise IndexError(f"{key} is not a valid indexer for MapsGrid")

                return getattr(self, f"m_{r}_{c}")
            else:
                if str(key) in self._names["Maps"]:
                    return getattr(self, "m_" + str(key))
                elif str(key) in self._names["Axes"]:
                    return getattr(self, "ax_" + str(key))
                else:
                    raise IndexError(f"{key} is not a valid indexer for MapsGrid")
        except:
            raise IndexError(f"{key} is not a valid indexer for MapsGrid")

    @property
    def _preferred_wms_service(self):
        return self.parent._preferred_wms_service

    def create_axes(self, ax_init, name=None):
        """
        Create (and return) an ordinary matplotlib axes.

        Note: If you intend to use both ordinary axes and Maps-objects, it is
        recommended to use explicit "m_inits" and "ax_inits" dicts in the
        initialization of the MapsGrid to avoid the creation of overlapping axes!

        Parameters
        ----------
        ax_init : set
            The GridSpec speciffications for the axis.
            use `ax_inits = (<row>, <col>)` to get an axis in a given grid-cell
            use `slice(<start>, <stop>)` for `<row>` or `<col>` to get an axis
            that spans over multiple rows/columns.

        Returns
        -------
        ax : matplotlib.axist
            The matplotlib axis instance

        Examples
        --------

        >>> ax_inits = dict(top = (0, slice(0, 2)),
        >>>                 bottom_left=(1, 0))

        >>> mg = MapsGrid(2, 2, ax_inits=ax_inits)
        >>> mg.m_top.plot_map()
        >>> mg.m_bottom_left.plot_map()

        >>> mg.create_axes((1, 1), name="bottom_right")
        >>> mg.ax_bottom_right.plot([1,2,3], [1,2,3])

        """

        if name is None:
            # get all existing axes
            axes = [key for key in self.__dict__ if key.startswith("ax_")]
            name = str(len(axes))
        else:
            assert (
                name.isidentifier()
            ), f"the provided name {name} is not a valid identifier"

        ax = self.f.add_subplot(self.gridspec[ax_init])

        self._names["Axes"].append(name)
        setattr(self, f"ax_{name}", ax)
        return ax

    _doc_prefix = (
        "This will execute the corresponding action on ALL Maps "
        + "objects of the MapsGrid!\n"
    )

    @property
    def children(self):
        return [i for i in self if i is not self.parent]

    @property
    def f(self):
        return self.parent.figure.f

    @wraps(Maps.plot_map)
    def plot_map(self, **kwargs):
        for m in self:
            m.plot_map(**kwargs)

    plot_map.__doc__ = _doc_prefix + plot_map.__doc__

    @property
    @lru_cache()
    @wraps(shapes)
    def set_shape(self):
        s = shapes(self)
        s.__doc__ = self._doc_prefix + s.__doc__

        return s

    @wraps(Maps.set_plot_specs)
    def set_plot_specs(self, **kwargs):
        for m in self:
            m.set_plot_specs(**kwargs)

    set_plot_specs.__doc__ = _doc_prefix + set_plot_specs.__doc__

    @wraps(Maps.set_data_specs)
    def set_data_specs(self, *args, **kwargs):
        for m in self:
            m.set_data_specs(*args, **kwargs)

    set_data_specs.__doc__ = _doc_prefix + set_data_specs.__doc__

    set_data = set_data_specs

    @wraps(Maps.set_classify_specs)
    def set_classify_specs(self, scheme=None, **kwargs):
        for m in self:
            m.set_classify_specs(scheme=scheme, **kwargs)

    set_classify_specs.__doc__ = _doc_prefix + set_classify_specs.__doc__

    @wraps(Maps.add_annotation)
    def add_annotation(self, *args, **kwargs):
        for m in self:
            m.add_annotation(*args, **kwargs)

    add_annotation.__doc__ = _doc_prefix + add_annotation.__doc__

    @wraps(Maps.add_marker)
    def add_marker(self, *args, **kwargs):
        for m in self:
            m.add_marker(*args, **kwargs)

    add_marker.__doc__ = _doc_prefix + add_marker.__doc__

    if wms_container is not None:

        @property
        @wraps(Maps.add_wms)
        def add_wms(self):
            return self._wms_container

    @property
    @wraps(Maps.add_feature)
    def add_feature(self):
        x = NaturalEarth_features(self)
        return x

    @wraps(Maps.add_gdf)
    def add_gdf(self, *args, **kwargs):
        for m in self:
            m.add_gdf(*args, **kwargs)

    add_gdf.__doc__ = _doc_prefix + add_gdf.__doc__

    @wraps(ScaleBar.__init__)
    def add_scalebar(self, *args, **kwargs):
        for m in self:
            m.add_scalebar(*args, **kwargs)

    add_scalebar.__doc__ = _doc_prefix + add_scalebar.__doc__

    @wraps(Maps.add_colorbar)
    def add_colorbar(self, *args, **kwargs):
        for m in self:
            m.add_colorbar(*args, **kwargs)

    add_colorbar.__doc__ = _doc_prefix + add_colorbar.__doc__

    @wraps(Maps.add_logo)
    def add_logo(self, *args, **kwargs):
        for m in self:
            m.add_logo(*args, **kwargs)

    add_colorbar.__doc__ = _doc_prefix + add_logo.__doc__

    def share_click_events(self):
        """
        Share click events between all Maps objects of the grid
        """
        self.parent.cb.click.share_events(*self.children)

    def share_pick_events(self, name="default"):
        """
        Share pick events between all Maps objects of the grid
        """
        if name == "default":
            self.parent.cb.pick.share_events(*self.children)
        else:
            self.parent.cb.pick[name].share_events(*self.children)

    def join_limits(self):
        """
        Join axis limits between all Maps objects of the grid
        (only possible if all maps share the same crs!)
        """
        self.parent.join_limits(*self.children)

    @wraps(Maps.redraw)
    def redraw(self):
        self.parent.redraw()

    @wraps(plt.savefig)
    def savefig(self, *args, **kwargs):

        # clear all cached background layers before saving to make sure they
        # are re-drawn with the correct dpi-settings
        self.parent.BM._bg_layers = dict()

        self.f.savefig(*args, **kwargs)

    @property
    @wraps(Maps.util)
    def util(self):
        return self.parent.util

    @wraps(Maps.subplots_adjust)
    def subplots_adjust(self, **kwargs):
        return self.parent.subplots_adjust(**kwargs)

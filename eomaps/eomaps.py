"""A collection of helper-functions to generate map-plots."""

from functools import partial, lru_cache, wraps
from collections import defaultdict
import warnings
import copy
from types import SimpleNamespace

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
from .scalebar import ScaleBar

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

    orientation : str, optional
        Indicator if the colorbar should be plotted right of the map
        ("horizontal") or below the map ("vertical"). The default is "vertical"

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
    """

    CRS = ccrs

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
        orientation="vertical",
        f=None,
        gs_ax=None,
        preferred_wms_service="wms",
    ):

        # share the axes with the parent if no explicit axes is provided
        if parent is not None:
            assert (
                f is None
            ), "You cannot specify the figure for connected Maps-objects!"

        self._f = None
        self._orientation = orientation
        self._ax = gs_ax
        self._init_ax = gs_ax

        self._BM = None
        self._parent = None
        self._children = []

        self.parent = parent  # invoke the setter!
        self._orientation = "vertical"
        self.layer = layer

        # preferred way of accessing WMS services (used in the WMS container)
        assert preferred_wms_service in [
            "wms",
            "wmts",
        ], "preferred_wms_service must be either 'wms' or 'wmts' !"
        self._preferred_wms_service = preferred_wms_service

        # default plot specs
        self.plot_specs = plot_specs(
            self,
            label=None,
            title=None,
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
        else:
            if crs is None:
                crs = 4326

            self.plot_specs.crs = crs

        # default classify specs
        self.classify_specs = classify_specs(self)

        self.set_shape.ellipses()

        self.data_specs = data_specs(
            self,
            xcoord="lon",
            ycoord="lat",
            crs=4326,
        )

        self._axpicker = None

    def _check_gpd(self):
        # raise an error if geopandas is not found
        # (execute this in any function that requires geopandas!)
        if not _gpd_OK:
            raise ImportError(
                "EOmaps: You need to install geopandas first!\n"
                + "... with conda, simply use:  "
                + "'conda install -c conda-forge geopandas'"
            )

    @property
    @lru_cache()
    @wraps(cb_container)
    def cb(self):
        return cb_container(self)

    @property
    @lru_cache()
    @wraps(shapes)
    def set_shape(self):
        return shapes(self)

    @property
    @lru_cache()
    @wraps(map_objects)
    def figure(self):
        return map_objects(self)

    def _set_axes(self):
        if self._ax is None or isinstance(self._ax, SubplotSpec):
            f, gs, cbgs, ax, ax_cb, ax_cb_plot = self._init_figure(
                gs_ax=self._ax,
                add_colorbar=getattr(self, "cbQ", False),
            )

            self._ax = ax
            self._ax_cb = ax_cb
            self._ax_cb_plot = ax_cb_plot
            self._gridspec = gs
            self._cb_gridspec = cbgs

            # initialize the callbacks
            self.cb._init_cbs()

            def lims_change(*args, **kwargs):
                self.BM._refetch_bg = True

            self.figure.ax.callbacks.connect("xlim_changed", lims_change)
            self.figure.ax.callbacks.connect("ylim_changed", lims_change)

            if self.parent is self:
                _ = self._draggable_axes

                if plt.get_backend() == "module://ipympl.backend_nbagg":
                    warnings.warn(
                        "EOmaps disables matplotlib's interactive mode (e.g. 'plt.ioff()') "
                        + "when using the 'ipympl' backend to avoid recursions during callbacks!"
                    )
                    plt.ioff()
                else:
                    plt.ion()
            else:
                # make sure the parent Maps-object is initialized as well!
                self.parent._set_axes()
            plt.show()

    def _reset_axes(self):
        # reset all objects connected to the figure (in case it is closed)
        for m in [self.parent, *self.parent._children]:
            m._f = None
            m._ax = m._init_ax
            m._ax_cb = None
            m._ax_cb_plot = None
            m._gridspec = None
            m._cb_gridspec = None

            # reset all callbacks attached to the figure
            m.cb._reset_cids()

        # reset the Blit-Manager
        self.parent._BM = None

        # reset the draggable-axes class on next call
        self.parent._axpicker = None

    @property
    def BM(self):
        """The Blit-Manager used to dynamically update the plots"""
        if self.parent._BM is None:
            self.parent._BM = BlitManager(self)
        return self.parent._BM

    @property
    def _draggable_axes(self):
        if self.parent._axpicker is None:
            # make the axes draggable
            self.parent._axpicker = draggable_axes(self.parent, modifier="alt+d")
            return self.parent._axpicker

        return self.parent._axpicker

    if wms_container is not None:

        @property
        @wraps(wms_container)
        @lru_cache()
        def add_wms(self):
            return wms_container(self)

    def _add_child(self, m):
        self.parent._children.append(m)

    @property
    def parent(self):
        """
        The parent-object to which this Maps-object is connected to.
        If None, `self` is returned!
        """
        if self._parent is None:
            return self
        else:
            return self._parent

    @parent.setter
    def parent(self, parent):
        assert parent is not self, "EOmaps: A Maps-object cannot be its own parent!"
        assert self._parent is None, "EOmaps: There is already a parent Maps object!"
        self._parent = parent
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
        self._set_axes()
        for m in args:
            m._set_axes()
            if m is not self:
                self._join_axis_limits(m)

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

    def new_layer(
        self,
        copy_data_specs=False,
        copy_plot_specs=True,
        copy_classify_specs=False,
        copy_shape=True,
        layer=None,
    ):
        """
        Create a new Maps-object that shares the same plot-axes.

        Parameters
        ----------
        copy_data_specs, copy_shape, copy_plot_specs, copy_classify_specs : bool
            Indicator if the corresponding properties should be copied to
            the new layer. By default, only "plot_specs" and the "shape" are copied.
        layer : int
            The layer index at which map-features are plotted by default.
            The default is None in which case the layer of the parent object is used.

        Returns
        -------
        eomaps.Maps
            A connected copy of the Maps-object that shares the same plot-axes.

        See Also
        --------
        copy : general way for copying Maps objects
        """

        if layer is None:
            layer = self.layer

        return self.copy(
            data_specs=copy_data_specs,
            plot_specs=copy_plot_specs,
            classify_specs=copy_classify_specs,
            shape=copy_shape,
            parent=self,
            gs_ax=self.figure.ax,
            layer=layer,
        )

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
            Indicator if the corresponding properties should be copied or shared

            - if True: ALL corresponding properties are copied
            - if "shared": the property-containers are shared between the objects
              (e.g. changing a property will change the property on the copied
              object as well)

            By default, "plot_specs", "classify_specs" and the "shape" are copied.

        kwargs :
            Additional kwargs passed to `m = Maps(**kwargs)`
            (e.g. parent, f, gs_ax, orientation, layer)
        Returns
        -------
        copy_cls : eomaps.Maps object
            a new Maps class.
        """

        # create a new class
        copy_cls = Maps(**kwargs)

        if data_specs is True:
            data_specs = list(self.data_specs.keys())
            copy_cls.set_data_specs(
                **{key: copy.deepcopy(val) for key, val in self.data_specs}
            )
        elif data_specs == "share":
            copy_cls.data_specs = self.data_specs

        if plot_specs is True:
            plot_specs = list(self.plot_specs.keys())
            if copy_cls.figure.ax is not None:
                # don't copy the plot_crs if there's already an axes defined!
                # (cartopy-projections can't be deep-copied)
                plot_specs.pop(plot_specs.index("plot_crs"))

            copy_cls.set_plot_specs(
                **{key: copy.deepcopy(self.plot_specs[key]) for key in plot_specs}
            )

        elif plot_specs == "share":
            copy_cls.plot_specs = self.plot_specs

        if shape is True:
            getattr(copy_cls.set_shape, self.shape.name)(**self.shape._initargs)
        elif shape == "share":
            copy_cls.shape = self.shape

        if classify_specs is True:
            classify_specs = list(self.classify_specs.keys())
            copy_cls.set_classify_specs(
                scheme=self.classify_specs.scheme, **self.classify_specs
            )
        elif classify_specs == "share":
            copy_cls.classify_specs = self.classify_specs

        return copy_cls

    @property
    def data(self):
        return self.data_specs.data

    @data.setter
    def data(self, val):
        # for downward-compatibility
        self.data_specs.data = val

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
        Set the plot-specifications (title, label, colormap, crs, etc.)

        Use this function to update multiple data-specs in one go
        Alternatively you can set the data-specifications via

            >>> m.data_specs.< property > = ...`

        Parameters
        ----------
        label : str, optional
            The colorbar-label.
            If None, the name of the parameter will be used.
            The default is None.
        title : str, optional
            The plot-title.
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

    @property
    @lru_cache()
    def _bounds(self):
        # get the extent of the added collection
        b = self.figure.coll.get_datalim(self.figure.ax.transData)
        # set the axis-extent
        return (b.xmin, b.ymin, b.xmax, b.ymax)

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
        The crs used for plotting. (A shortcut for `m.get_crs("plot")`)
        """
        return self.get_crs("plot")

    @property
    @lru_cache()
    def _transf_plot_to_lonlat(self):
        # get coordinate transformation from in_crs to plot_crs
        transformer = Transformer.from_crs(
            self.crs_plot,
            self.get_crs(4326),
            always_xy=True,
        )
        return transformer

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
            crs = self.plot_specs.plot_crs

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
                z_data = data[parameter].values.ravel()
                # get the index-values
                ids = data.index.values.ravel()

                if isinstance(xcoord, str) and isinstance(ycoord, str):
                    # get the data-coordinates
                    xorig = data[xcoord].values.ravel()
                    yorig = data[ycoord].values.ravel()
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

                    xorig = np.asanyarray(xcoord).ravel()
                    yorig = np.asanyarray(ycoord).ravel()

            # check for explicit 1D value lists
            types = (list, np.ndarray)
            if _pd_OK:
                types += (pd.Series,)

            if isinstance(data, types):
                # get the data-values
                z_data = np.asanyarray(data).ravel()
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
                xorig = np.asanyarray(xcoord).ravel()
                yorig = np.asanyarray(ycoord).ravel()

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
        transformer = Transformer.from_crs(
            self.get_crs(in_crs),
            self.crs_plot,
            always_xy=True,
        )

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

        props["xorig"] = xorig
        props["yorig"] = yorig
        props["ids"] = ids
        props["z_data"] = z_data

        # transform center-points to the plot_crs
        props["x0"], props["y0"] = transformer.transform(xorig, yorig)

        props["mask"] = np.isfinite(props["x0"]) & np.isfinite(props["y0"])

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

    def _init_fig_grid(self, gs_ax=None):

        if gs_ax is None:
            gs_main = None
            gs_func = GridSpec
        else:
            gs_main = gs_ax
            gs_func = partial(GridSpecFromSubplotSpec, subplot_spec=gs_main)

        if self._orientation == "horizontal":
            # gridspec for the plot
            if gs_main:
                gs = gs_func(
                    nrows=1,
                    ncols=2,
                    width_ratios=[0.75, 0.15],
                    wspace=0.02,
                )
            else:
                gs = gs_func(
                    nrows=1,
                    ncols=2,
                    width_ratios=[0.75, 0.15],
                    left=0.01,
                    right=0.91,
                    bottom=0.02,
                    top=0.92,
                    wspace=0.02,
                )
            # sub-gridspec
            cbgs = GridSpecFromSubplotSpec(
                nrows=1,
                ncols=2,
                subplot_spec=gs[0, 1],
                hspace=0,
                wspace=0,
                width_ratios=[0.9, 0.1],
            )
        elif self._orientation == "vertical":
            if gs_main:
                # gridspec for the plot
                gs = gs_func(
                    nrows=2,
                    ncols=1,
                    height_ratios=[0.75, 0.15],
                    hspace=0.02,
                )
            else:
                # gridspec for the plot
                gs = gs_func(
                    nrows=2,
                    ncols=1,
                    height_ratios=[0.75, 0.15],
                    left=0.05,
                    right=0.95,
                    bottom=0.07,
                    top=0.92,
                    hspace=0.02,
                )
            # sub-gridspec
            cbgs = GridSpecFromSubplotSpec(
                nrows=2,
                ncols=1,
                subplot_spec=gs[1, 0],
                hspace=0,
                wspace=0,
                height_ratios=[0.9, 0.1],
            )

        return gs, cbgs

    def _init_figure(self, gs_ax=None, plot_crs=None, add_colorbar=True):
        f = self.figure.f
        if plot_crs is None:
            plot_crs = self.plot_specs["plot_crs"]

        if gs_ax is None or isinstance(gs_ax, SubplotSpec):
            gs, cbgs = self._init_fig_grid(gs_ax=gs_ax)

            if plot_crs == 4326:
                cartopy_proj = ccrs.PlateCarree()
            elif isinstance(plot_crs, int):
                cartopy_proj = ccrs.epsg(plot_crs)
            else:
                cartopy_proj = plot_crs

            if add_colorbar:
                ax = f.add_subplot(
                    gs[0], projection=cartopy_proj, aspect="equal", adjustable="box"
                )
                # axes for histogram
                ax_cb_plot = f.add_subplot(cbgs[0], frameon=False, label="ax_cb_plot")
                # axes for colorbar
                ax_cb = f.add_subplot(cbgs[1], label="ax_cb")
                # join colorbar and histogram axes
                if self._orientation == "horizontal":
                    ax_cb_plot.get_shared_y_axes().join(ax_cb_plot, ax_cb)
                    ax_cb_plot.tick_params(rotation=90, axis="x")

                elif self._orientation == "vertical":
                    ax_cb_plot.get_shared_x_axes().join(ax_cb_plot, ax_cb)
            else:
                ax = f.add_subplot(
                    gs[:], projection=cartopy_proj, aspect="equal", adjustable="box"
                )
                if hasattr(gs, "update"):
                    gs.update(left=0.01, right=0.99, bottom=0.01, top=0.95)
                ax_cb, ax_cb_plot = None, None

        else:
            ax = gs_ax
            gs, cbgs = None, None
            ax_cb, ax_cb_plot = None, None

        return f, gs, cbgs, ax, ax_cb, ax_cb_plot

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
        orientation=None,
    ):

        if ax_cb is None:
            ax_cb = self.figure.ax_cb
        if ax_cb_plot is None:
            ax_cb_plot = self.figure.ax_cb_plot

        if z_data is None:
            z_data = self._props["z_data"]

        if label is None:
            label = self.plot_specs["label"]
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

        if orientation is None:
            orientation = self._orientation

        if orientation == "horizontal":
            cb_orientation = "vertical"
        elif orientation == "vertical":
            cb_orientation = "horizontal"

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
            ax_cb_plot.xaxis.set_major_locator(plt.MaxNLocator(5))
            ax_cb_plot.grid(axis="x", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            ax_cb_plot.plot(
                [1, 1], [0, 1], "k--", alpha=0.5, transform=ax_cb_plot.transAxes
            )
            # make sure lower x-limit is 0
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
            ax_cb_plot.yaxis.set_major_locator(plt.MaxNLocator(5))
            ax_cb_plot.grid(axis="y", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            ax_cb_plot.plot(
                [0, 1], [0, 0], "k--", alpha=0.5, transform=ax_cb_plot.transAxes
            )
            # make sure lower y-limit is 0
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

        return cb

    @property
    def add_feature(self):
        return NaturalEarth_features(self)

    def add_gdf(
        self,
        gdf,
        picker_name=None,
        pick_method="centroids",
        val_key=None,
        layer=None,
        **kwargs,
    ):
        """
        Overplot a `geopandas.GeoDataFrame` over the generated plot.
        (`plot_map()` must be called!)

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
        layer : int
            The layer-index at which the dataset will be plotted.

        kwargs :
            all remaining kwargs are passed to `gdf.plot(**kwargs)`
        """
        self._check_gpd()

        self._set_axes()
        ax = self.figure.ax
        defaultargs = dict(facecolor="none", edgecolor="k", lw=1.5)
        defaultargs.update(kwargs)

        # transform data to the plot crs
        usegdf = gdf.to_crs(self.crs_plot)
        # explode the GeoDataFrame to avoid picking multi-part geometries
        try:
            usegdf = usegdf.explode(index_parts=False)
        except Exception:
            # geopandas sometimes has problems exploding geometries...
            # if it does not work, just continue with the Multi-geometries!
            pass

        # plot gdf and identify newly added collections
        # (geopandas always uses collections)
        colls = [id(i) for i in self.figure.ax.collections]
        usegdf.plot(ax=ax, aspect=ax.get_aspect(), **defaultargs)
        newcolls = [i for i in self.figure.ax.collections if id(i) not in colls]
        if len(newcolls) > 1:
            prefixes = [
                f"_{i.__class__.__name__.replace('Collection', '')}" for i in newcolls
            ]
            warnings.warn(
                "EOmaps: Multiple geometry types encountered in `m.add_gdf`. "
                + "The pick containers are re-named to"
                + f"{[picker_name + prefix for prefix in prefixes]}"
            )
        else:
            prefixes = [""]

        if picker_name is not None:
            if pick_method is not None:
                if isinstance(pick_method, str):
                    if pick_method in ["contains"]:

                        def picker(artist, mouseevent):
                            try:
                                query = getattr(usegdf, pick_method)(
                                    gpd.points_from_xy(
                                        [mouseevent.xdata], [mouseevent.ydata]
                                    )[0]
                                )
                                if query.any():
                                    return True, dict(
                                        ID=usegdf.index[query][0],
                                        ind=query.values.nonzero()[0][0],
                                        val=(
                                            usegdf[query][val_key].iloc[0]
                                            if val_key
                                            else None
                                        ),
                                    )
                                else:
                                    return False, dict()
                            except:
                                return False, dict()

                    if pick_method == "centroids":
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

                for art, prefix in zip(newcolls, prefixes):
                    # make the newly added collection pickable
                    self.cb.add_picker(picker_name + prefix, art, picker=picker)

                    # attach the re-projected GeoDataFrame to the pick-container
                    self.cb.pick[picker_name + prefix].data = usegdf

        for art, prefix in zip(newcolls, prefixes):
            if layer is not None:
                self.BM.add_bg_artist(art, layer)

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
            If float: The radius of the marker.
            If "pixel": It will represent the dimensions of the selected pixel.
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
        **kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)

        Examples
        --------

            >>> m.add_marker(ID=1, buffer=5)
            >>> m.add_marker(ID=1, radius=2, radius_crs=4326, shape="rectangles")
            >>> m.add_marker(xy=(45, 35), xy_crs=4326, radius=20000, shape="geod_circles")
        """
        self._set_axes()

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
        ID : any
            The index-value of the pixel in m.data.
        xy : tuple
            A tuple of the position of the pixel provided in "xy_crs".
            If None, xy must be provided in the coordinate-system of the plot!
            The default is None
        xy_crs : any
            the identifier of the coordinate-system for the xy-coordinates
        text : callable or str, optional
            if str: the string to print
            if callable: A function that returns the string that should be
            printed in the annotation with the following call-signature:

                >>> def text(m, ID, val, pos):
                >>>     # m   ... the Maps object
                >>>     # ID  ... the ID
                >>>     # pos ... the position
                >>>     # val ... the value
                >>>
                >>>     return "the string to print"

            The default is None.

        **kwargs
            kwargs passed to m.cb.annotate

        Examples
        --------

            >>> m.add_annotation(ID=1)
            >>> m.add_annotation(xy=(45, 35), xy_crs=4326)
            >>> m.add_annotation(ID=1, text="some text")

            >>> def addtxt(m, ID, val, pos):
            >>>     return f"The ID {ID} at position {pos} has a value of {val}"
            >>> m.add_annotation(ID=1, text=addtxt)

        """
        self._set_axes()

        if ID is not None:
            assert xy is None, "You can only provide 'ID' or 'pos' not both!"

            # get the index of the first occurance of the ID in the provided ids
            ind = np.nonzero(self._props["ids"] == ID)[0][0]
            xy = (self._props["xorig"][ind], self._props["yorig"][ind])
            val = self._props["z_data"][ind]

            xy_crs = self.data_specs.crs
        else:
            val = None

        if xy is not None:

            if xy_crs is not None:
                # get coordinate transformation
                transformer = Transformer.from_crs(
                    CRS.from_user_input(xy_crs),
                    self.crs_plot,
                    always_xy=True,
                )
                # transform coordinates
                xy = transformer.transform(*xy)

        # add marker
        self.cb.click._cb.annotate(
            ID=ID,
            pos=xy,
            val=val,
            ind=None if ID is None else self.data.index.get_loc(ID),
            permanent=True,
            text=text,
            **kwargs,
        )
        self.BM.update(clear=False)

    @wraps(ScaleBar.__init__)
    def add_scalebar(
        self,
        lon=None,
        lat=None,
        azim=91.0,
        scale=10000,
        scale_props=None,
        patch_props=None,
        label_props=None,
    ):

        self._set_axes()

        if lon is None and lat is None:
            extent = self.figure.ax.get_extent()
            lon, lat = self._transf_plot_to_lonlat.transform(
                np.mean(extent[:2]),
                np.mean(extent[2:]),
            )

        s = ScaleBar(
            m=self,
            scale=scale,
            scale_props=scale_props,
            patch_props=patch_props,
            label_props=label_props,
        )
        s._add_scalebar(lon, lat, azim)
        s._make_pickable()

        return s

    @wraps(plt.savefig)
    def savefig(self, *args, **kwargs):

        # clear all cached background layers before saving to make sure they
        # are re-drawn with the correct dpi-settings
        self.BM._bg_layers = dict()

        self.figure.f.savefig(*args, **kwargs)

    def plot_map(
        self,
        colorbar=True,
        pick_distance=100,
        layer=None,
        dynamic=False,
        **kwargs,
    ):
        """
        Actually generate the map-plot based on the data provided as `m.data` and the
        specifications defined in "data_specs", "plot_specs" and "classify_specs".

        NOTE
        ----
        Each call to plot_map will replace the collection used for picking!
        (only the last collection remains interactive on multiple calls to `m.plot_map()`)

        If you need multiple responsive datasets, use connected maps-objects instead!
        (e.g. `m2 = Maps(parent=m)` or have a look at `MapsGrid`)

        Parameters
        ----------
        colorbar : bool
            Indicator if a colorbar should be added or not.
            (ONLY relevant for the first time a dataset is plotted!)
            The default is True
        pick_distance : int
            The maximum distance (in pixels) to trigger callbacks on the added collection.
            (The distance is evaluated between the clicked pixel and the center of the
            closest data-point)
            The default is 10.
        layer : int
            The layer-index at which the dataset will be plotted.
            The default is None.
        dynamic : bool
            If True, the collection will be dynamically updated

        kwargs
            kwargs passed to the initialization of the matpltolib collection
            (dependent on the plot-shape) [linewidth, edgecolor, facecolor, ...]
        """

        if "coastlines" in kwargs:
            kwargs.pop("coastlines")
            warnings.warn(
                "EOmaps: the 'coastlines' kwarg for 'plot_map' is depreciated!"
                + "Instead use "
                + "\n    m.add_feature.preset.ocean()"
                + "\n    m.add_feature.preset.coastline()"
                + " instead!"
            )

        if self.data is None and colorbar is True:
            print("EOmaps: ...cannot add a colormap if no data is provided!")
            colorbar = False
        self.cbQ = colorbar

        self._set_axes()
        ax = self.figure.ax

        for key in ("cmap", "array", "norm"):
            assert (
                key not in kwargs
            ), f"The key '{key}' is assigned internally by EOmaps!"

        try:
            if layer is None:
                layer = self.layer

            # remove previously fetched backgrounds for the used layer
            if layer in self.BM._bg_layers:
                del self.BM._bg_layers[layer]
            self.BM._refetch_bg = True

            title = self.plot_specs["title"]
            if title is not None:
                ax.set_title(title)

            if self.data is None:
                return

            # ---------------------- prepare the data
            props = self._prepare_data()

            # use a cKDTree based picking to speed up picks for large collections
            self.tree = cKDTree(np.stack([props["x0"], props["y0"]], axis=1))

            # remember props for later use
            self._props = props

            vmin = self.plot_specs["vmin"]
            if self.plot_specs["vmin"] is None:
                vmin = np.nanmin(props["z_data"])
            vmax = self.plot_specs["vmax"]
            if self.plot_specs["vmax"] is None:
                vmax = np.nanmax(props["z_data"])

            # clip the data to properly account for vmin and vmax
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

            coll = self.shape.get_coll(props["xorig"], props["yorig"], "in", **args)

            coll.set_clim(vmin, vmax)

            ax.add_collection(coll)

            self.figure.coll = coll

            # attach the pick-callback that executes the callbacks
            # self.attach_picker("default", self.figure.coll, None)

            # self.cb.add_picker("default", coll, None)
            self.cb.pick._set_artist(coll)
            self.cb.pick._init_cbs()
            self.cb.pick._pick_distance = pick_distance
            self.cb._methods.append("pick")

            if colorbar:
                if hasattr(self.figure, "cb"):
                    warnings.warn(
                        "EOmaps: There is already a colorbar present on the map!"
                    )
                elif self.figure.ax is not None and (
                    self.figure.ax_cb is None or self.figure.ax_cb_plot is None
                ):
                    warnings.warn(
                        "EOmaps: Colorbars can only be added on the base-layer!"
                    )

                elif (self.figure.ax_cb is not None) and (
                    self.figure.ax_cb_plot is not None
                ):

                    # ------------- add a colorbar with a histogram
                    cb = self._add_colorbar(
                        bins=bins,
                        cmap=cbcmap,
                        norm=norm,
                        classified=classified,
                    )
                    self.figure.cb = cb
                else:
                    warnings.warn(
                        "EOmaps: Colorbar could not be created... did "
                        + "you call 'm.plot_map()' before adding other features?"
                    )

            if dynamic is True:
                self.BM.add_artist(coll, layer)
            else:
                self.BM.add_bg_artist(coll, layer)

            # set the image extent
            # get the extent of the added collection
            b = self.figure.coll.get_datalim(ax.transData)
            ymin, ymax = ax.projection.y_limits
            xmin, xmax = ax.projection.x_limits
            # set the axis-extent
            ax.set_xlim(max(b.xmin, xmin), min(b.xmax, xmax))
            ax.set_ylim(max(b.ymin, ymin), min(b.ymax, ymax))

            # self.figure.f.canvas.draw()
            if dynamic is True:
                self.BM.update(clear=False)

        except Exception as ex:
            raise ex

    def add_colorbar(
        self,
        gs,
        orientation="horizontal",
        label=None,
        density=None,
        tick_precision=None,
    ):
        """
        Manually add a colorbar to an existing figure.
        (NOTE: the preferred way is to use `plot_map(colorbar=True)` instead!)

        To change the position of the colorbar, use:

            >>> cb = m.add_colorbar(gs)
            >>> m.figure.set_colorbar_position(pos, cb=cb)

        Parameters
        ----------
        gs : matpltolib.gridspec.GridSpec
            the gridspec to derive the colorbar-axes from.
        orientation : str
            The orientation of the colorbar ("horizontal" or "vertical")
            The default is "horizontal"
        """

        # "_add_colorbar" orientation is opposite to the colorbar-orientation
        if orientation == "horizontal":
            cb_orientation = "vertical"
        elif orientation == "vertical":
            cb_orientation = "horizontal"

        if cb_orientation == "horizontal":
            # sub-gridspec
            cbgs = GridSpecFromSubplotSpec(
                nrows=1,
                ncols=2,
                subplot_spec=gs,
                hspace=0,
                wspace=0,
                width_ratios=[0.9, 0.1],
            )
        elif cb_orientation == "vertical":
            # sub-gridspec
            cbgs = GridSpecFromSubplotSpec(
                nrows=2,
                ncols=1,
                subplot_spec=gs,
                hspace=0,
                wspace=0,
                height_ratios=[0.9, 0.1],
            )

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
        )

        # join colorbar and histogram axes
        if cb_orientation == "horizontal":
            ax_cb_plot.get_shared_y_axes().join(ax_cb_plot, ax_cb)
        elif cb_orientation == "vertical":
            ax_cb_plot.get_shared_x_axes().join(ax_cb_plot, ax_cb)

        return [cbgs, ax_cb, ax_cb_plot, orientation, cb]

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

        data = self.data[~self._data_mask]

        if len(data) == 0:
            print("EOmaps: There are no masked points to indicate!")
            return

        m = self.new_layer(copy_data_specs=True)
        m.data = data

        t = self.figure.ax.transData.inverted()
        r = t.transform((100 + radius, 100 + radius)) - t.transform((100, 100))
        m.set_shape.ellipses(radius_crs="out", radius=r)
        m.plot_map(**kwargs)
        return m


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


        Note: If either `m_inits` or `ax_inits` is provided, ONLY objects with the
        specified properties are initialized!

        The default is None in which case a unique Maps-object will be created
        for each grid-cell (accessible via `mgrid.m_<row>_<col>`)
    ax_inits : dict, optional
        Completely similar to `m_inits` but instead of `Maps` objects, ordinary
        matplotlib axes will be initialized. They are accessible via `mg.ax_<name>`.

        Note: If you iterate over the MapsGrid object, ONLY the initialized Maps
        objects will be returned!
    kwargs
        Additional keyword-arguments passed to the `matplotlib.gridspec.GridSpec()`
        function that is used to initialize the grid.

    Attributes
    ----------
    f : matplotlib.figure
        The matplotlib figure object
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

    def __init__(self, r=2, c=2, crs=None, m_inits=None, ax_inits=None, **kwargs):
        self._Maps = []
        self._names = defaultdict(list)
        self._gs = GridSpec(nrows=r, ncols=c, **kwargs)

        if m_inits is None and ax_inits is None:
            self._custom_init = False
            for i in range(r):
                for j in range(c):
                    if i == 0 and j == 0:
                        mij = Maps(crs=crs, gs_ax=self._gs[0, 0])
                        self.parent = mij
                    else:
                        mij = Maps(crs=crs, parent=self.parent, gs_ax=self._gs[i, j])

                    self._Maps.append(mij)
                    name = f"{i}_{j}"
                    self._names["Maps"].append(name)
                    setattr(self, "m_" + name, mij)
        else:
            self._custom_init = True
            if m_inits is not None:
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
                        mi = Maps(crs=crs, gs_ax=self._gs[val])
                        self.parent = mi
                    else:
                        mi = Maps(crs=crs, parent=self.parent, gs_ax=self._gs[val])

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

        ax = self.f.add_subplot(self._gs[ax_init])

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

    @wraps(Maps.set_plot_specs)
    def set_plot_specs(self, **kwargs):
        for m in self:
            m.set_plot_specs(**kwargs)

    set_plot_specs.__doc__ = _doc_prefix + set_plot_specs.__doc__

    @wraps(Maps.set_data_specs)
    def set_data_specs(self, **kwargs):
        for m in self:
            m.set_data_specs(**kwargs)

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

    @property
    @wraps(Maps.add_wms)
    @lru_cache()
    def add_wms(self):
        x = wms_container(self)
        x.__doc__ = self._doc_prefix + x.__doc__
        return x

    @property
    @wraps(Maps.add_feature)
    def add_feature(self):
        x = NaturalEarth_features(self)
        x.__doc__ = self._doc_prefix + x.__doc__
        return x

    @wraps(Maps.add_gdf)
    def add_gdf(self, *args, **kwargs):
        for m in self:
            m.add_gdf(*args, **kwargs)

    add_gdf.__doc__ = _doc_prefix + add_gdf.__doc__

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

    @wraps(plt.savefig)
    def savefig(self, *args, **kwargs):

        # clear all cached background layers before saving to make sure they
        # are re-drawn with the correct dpi-settings
        self.parent.BM._bg_layers = dict()

        self.f.savefig(*args, **kwargs)

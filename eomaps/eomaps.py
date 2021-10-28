"""a collection of helper-functions to generate map-plots"""

from functools import partial, lru_cache, wraps, update_wrapper
from collections import defaultdict
import warnings
import copy
from types import SimpleNamespace

import numpy as np
import pandas as pd

try:
    import geopandas as gpd
except:
    print("geopandas could not be imported... 'add_overlay' not working!")
    pass
from scipy.spatial import cKDTree
from pyproj import CRS, Transformer

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import cm, collections
from matplotlib.tri import Triangulation, TriMesh
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec, SubplotSpec
from matplotlib.patches import Patch


from cartopy import crs as ccrs
from cartopy import feature as cfeature
from cartopy.io import shapereader

from .helpers import pairwise, cmap_alpha, BlitManager
from .callbacks import callbacks
from ._shapes import shapes
from ._containers import (
    data_specs,
    plot_specs,
    map_objects,
    classify_specs,
    cb_container,
)

try:
    import mapclassify
except ImportError:
    print("No module named 'mapclassify'... classification will not work!")


class Maps(object):
    """
    A class to perform reading an plotting of spatial maps

    Parameters
    ----------
    orientation : str, optional
        Indicator if the colorbar should be plotted right of the map ("horizontal")
        or below the map ("vertical"). The default is "vertical"
    """

    _shapes = [
        "ellipses",
        "rectangles",
        "trimesh_rectangles",
        "delauney_triangulation",
        "delauney_triangulation_flat",
        "delauney_triangulation_masked",
        "delauney_triangulation_flat_masked",
        "voroni",
    ]

    crs_list = ccrs

    def __init__(self):

        self._orientation = "vertical"

        # default plot specs
        self.plot_specs = plot_specs(
            self,
            label=None,
            title=None,
            cmap=plt.cm.viridis.copy(),
            plot_crs=4326,
            radius_crs="in",
            radius="estimate",
            histbins=256,
            tick_precision=2,
            vmin=None,
            vmax=None,
            cpos="c",
            cpos_radius=None,
            alpha=1,
            add_colorbar=True,
            coastlines=True,
            density=False,
            shape="ellipses",
        )

        # default classify specs
        self.classify_specs = classify_specs(self)

        self._shapes = shapes(self)

        self._data_mask = slice(None)
        self.data_specs = data_specs(
            self,
            xcoord="lon",
            ycoord="lat",
            crs=4326,
        )

        self.figure = map_objects()

        self.cb = cb_container(self)

    def copy(
        self,
        data_specs=None,
        plot_specs=None,
        classify_specs=None,
        copy_data=False,
    ):
        """
        create a (deep)copy of the class that inherits all specifications
        from the parent class.
        Already loaded data is only copied if `copy_data=True`!

        -> useful to quickly create plots with similar configurations

        Parameters
        ----------
        data_specs, plot_specs, classify_specs : dict, optional
            Dictionaries that can be used to directly override the specifications of the
            parent class. The default is None.

        Returns
        -------
        copy_cls : eomaps.Maps object
            a new Maps class.
        """
        initdict = dict()
        initdict["data_specs"] = {
            key: copy.deepcopy(val) for key, val in self.data_specs
        }
        initdict["plot_specs"] = {
            key: copy.deepcopy(val) for key, val in self.plot_specs
        }
        initdict["classify_specs"] = {
            key: copy.deepcopy(val) for key, val in self.classify_specs
        }

        if data_specs:
            assert isinstance(data_specs, dict), "'data_specs' must be a dict"
            initdict["data_specs"].update(data_specs)

        if plot_specs:
            assert isinstance(plot_specs, dict), "'plot_specs' must be a dict"
            initdict["plot_specs"].update(plot_specs)

        if classify_specs:
            assert isinstance(classify_specs, dict), "'classify_specs' must be a dict"
            initdict["classify_specs"].update(classify_specs)

        # create a new class
        copy_cls = Maps()

        copy_cls.set_data_specs(**initdict["data_specs"])
        copy_cls.set_plot_specs(**initdict["plot_specs"])
        copy_cls.set_classify_specs(
            self.classify_specs.scheme, **initdict["classify_specs"]
        )

        if copy_data:
            copy_cls.data = self.data.copy(deep=True)

        return copy_cls

    @property
    def data(self):
        return self.data_specs.data

    @data.setter
    def data(self, val):
        # for downward-compatibility
        self.data_specs.data = val

    def set_data_specs(self, **kwargs):
        """
        Use this function to update multiple data-specs in one go
        Alternatively you can set the data-specifications via

            >>> m.data_specs.<...> = <...>`

        Parameters
        ----------
        parameter : str, optional
            The name of the parameter to use. If None, the first variable in the
            provided dataframe will be used.
            The default is None.
        xcoord, ycoord : str, optional
            The name of the x- and y-coordinate as provided in the dataframe.
            The default is "lon" and "lat".
        in_crs : int, dict or str
            The coordinate-system identifier.
            Can be any input usable with `pyproj.CRS.from_user_input`:

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

            The default is 4326 (e.g. lon/lat projection)
        """

        for key, val in kwargs.items():
            self.data_specs[key] = val

    set_data = set_data_specs

    def set_plot_specs(self, **kwargs):
        """
        Use this function to update multiple plot-specs in one go
        (alternatively you can set data-properties via `m.plot_specs.<...> = <...>`)

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
            A list for easy-accses is available as `m.crs_list`

            The default is 4326.
        radius_crs : str, optional
            The coordinate-system in which the radius is provided.
                - "in" : the crs of the input-dataframe (e.g. "in_crs")
                - "out" : the crs used for plotting (e.g. "plot_crs")
                - a crs specification (e.g. epsg-code, wkt string etc.) that
                  should be used to estimate the pixel-dimensions
            The default is "in".
        radius : str, float or tuple, optional
            The radius of the patches in the crs defined via "radius_crs".
            If "estimate", the radius will be automatically determined from the
            x-y coordinate separation of the data. The default is "estimate".
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
            The default is "c".
        alpha : int, optional
            Set the transparency of the plot (0-1)
            The default is 1.
        add_colorbar : bool, optional
            Indicator if a colorbar with a histogram should be added to the plot or not.
            The default is True.
        coastlines : bool, optional
            Indicator if simple coastlines and ocean-colorings should be added
            The default is True.
        density : bool, optional
            Indicator if the y-axis of the histogram should represent the
            probability-density (True) or the number of counts per bin (False)
            The default is False.
        shape : str, optional
            Indicator how the data-points should be plotted
                - "ellipses": plot projected ellipses
                - "rectangles": plot projected rectangles
                  Useful if pixel-boundaries should be visible.
                  (Note: polygons will have a visible boundary even if the
                   linewidth is set to 0!)
                - "trimesh_rectangles": rectangles but drawn with a
                  TriMesh collection so that there are no boundaries between
                  the pixels. (e.g. useful for contourplots)
                  NOTE: setting edge- and facecolors afterwards is not possible!
                - "delauney_triangulation": plot a delauney-triangulation
                  for the given set of data. (e.g. a dense triangulation of
                  irregularly spaced points)
                  NOTE: setting edge- and facecolors afterwards is not possible!
                - "delauney_triangulation_flat": same as the normal delauney-
                  triangulation, but plotted as a polygon-collection so that
                  edgecolors etc. can be set.
                - "delauney_triangulation_masked" (or "_flat_masked"):
                  same as "delauney_triangulation" but all triangles that
                  exhibit side-lengths longer than (2 x radius) are masked

                  This is particularly useful to triangulate concave areas
                  that are densely sampled.
                  -> you can use the radius as a parameter for the max.
                     interpolation-distance!

            The default is "trimesh_rectangles".
        """

        for key, val in kwargs.items():
            self.plot_specs[key] = val

    def set_classify_specs(self, scheme=None, **kwargs):
        """
        Set classification specifications for the data
        (classification is performed by the `mapclassify` module)

        Parameters
        ----------
        scheme : str
            The classification scheme to use.
            (the list is accessible via m.classify_specs.SCHEMES)

            E.g. one of:
            [ "scheme" (**kwargs)  ]

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

        **kwargs :
            kwargs passed to the call to the respective mapclassify classifier
        """
        self.classify_specs._set_scheme_and_args(scheme, **kwargs)

    def _attach_picker(self, coll=None, maxdist=None):
        if coll is None:
            coll = self.figure.coll
        if maxdist is None:
            maxdist = np.inf

        def picker(artist, event):
            if event.dblclick:
                double_click = True
            else:
                double_click = False

            if event.inaxes != self.figure.ax:
                return True, dict(
                    ind=None, double_click=double_click, mouse_button=event.button
                )

            # use a cKDTree based picking to speed up picks for large collections
            dist, index = self.tree.query((event.xdata, event.ydata))

            # always set the point as invalid if it is outside of the bounds
            # (for plots like delauney-triangulations that do not require a radius)
            bounds = self._bounds
            if not (
                (bounds[0] < event.xdata < bounds[2])
                and (bounds[1] < event.ydata < bounds[3])
            ):
                dist = np.inf

            if dist < maxdist:
                return True, dict(
                    ind=index, double_click=double_click, mouse_button=event.button
                )
            else:
                return True, dict(
                    ind=None, double_click=double_click, mouse_button=event.button
                )

            return False, None

        coll.set_picker(picker)

    @property
    @lru_cache()
    def _bounds(self):
        return (
            self._props["x0"].min(),
            self._props["y0"].min(),
            self._props["x0"].max(),
            self._props["y0"].max(),
        )

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
        return self.get_crs("plot")

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
        shape=None,
        buffer=None,
    ):

        # get specifications
        if data is None:
            data = self.data_specs.data
        if xcoord is None:
            xcoord = self.data_specs.xcoord
        if ycoord is None:
            ycoord = self.data_specs.ycoord
        if parameter is None:
            parameter = self.data_specs.parameter
        if in_crs is None:
            in_crs = self.data_specs.crs
        if radius is None:
            radius = self.plot_specs.radius
        if radius_crs is None:
            radius_crs = self.plot_specs.radius_crs
        if cpos is None:
            cpos = self.plot_specs.cpos
        if cpos_radius is None:
            cpos_radius = self.plot_specs.cpos_radius

        if shape is None:
            shape = self.plot_specs.shape

        props = dict()

        # get coordinate transformation from in_crs to plot_crs
        transformer = Transformer.from_crs(
            self.get_crs(in_crs),
            self.crs_plot,
            always_xy=True,
        )

        # get the data-coordinates
        xorig = data[xcoord].values
        yorig = data[ycoord].values
        # get the data-values
        z_data = data[parameter].values
        # get the index-values
        ids = data.index.values

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

        # get the radius for plotting
        if radius == "estimate":
            if radius_crs == "in":
                radiusx = np.median(np.abs(np.diff(np.unique(xorig)))) / 2.0
                radiusy = np.median(np.abs(np.diff(np.unique(yorig)))) / 2.0
            elif radius_crs == "out":
                radiusx = np.median(np.abs(np.diff(np.unique(props["x0"])))) / 2.0
                radiusy = np.median(np.abs(np.diff(np.unique(props["y0"])))) / 2.0
            else:
                raise AssertionError(
                    "radius can only be estimated if radius_crs is 'in' or 'out'!"
                )
        else:
            # get manually specified radius (e.g. if radius != "estimate")
            if isinstance(radius, (list, tuple)):
                radiusx, radiusy = radius
            elif isinstance(radius, (int, float)):
                radiusx = radius
                radiusy = radius

        if buffer is not None:
            radiusx = radiusx * buffer
            radiusy = radiusy * buffer

        props["radius"] = (radiusx, radiusy)

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

    def _init_fig_grid(self, f_gridspec=None):

        if f_gridspec is None:
            f = plt.figure(figsize=(12, 8))
            gs_main = None
            gs_func = GridSpec
        else:
            f, gs_main = f_gridspec
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

        return f, gs, cbgs

    def _init_figure(self, f_gridspec=None, plot_crs=None, add_colorbar=True):

        if plot_crs is None:
            plot_crs = self.plot_specs["plot_crs"]

        if f_gridspec is None or isinstance(f_gridspec[1], SubplotSpec):
            f, gs, cbgs = self._init_fig_grid(f_gridspec=f_gridspec)

            if plot_crs == 4326:
                cartopy_proj = ccrs.PlateCarree()
            elif isinstance(plot_crs, int):
                cartopy_proj = ccrs.epsg(plot_crs)
            else:
                cartopy_proj = plot_crs

            if add_colorbar:
                ax = f.add_subplot(
                    gs[0], projection=cartopy_proj, aspect="equal", adjustable="datalim"
                )
                # axes for histogram
                ax_cb_plot = f.add_subplot(cbgs[0], frameon=False, label="ax_cb_plot")
                ax_cb_plot.tick_params(rotation=90, axis="x")
                # axes for colorbar
                ax_cb = f.add_subplot(cbgs[1], label="ax_cb")
                # join colorbar and histogram axes
                if self._orientation == "horizontal":
                    ax_cb_plot.get_shared_y_axes().join(ax_cb_plot, ax_cb)
                elif self._orientation == "vertical":
                    ax_cb_plot.get_shared_x_axes().join(ax_cb_plot, ax_cb)
            else:
                ax = f.add_subplot(
                    gs[:], projection=cartopy_proj, aspect="equal", adjustable="datalim"
                )
                if hasattr(gs, "update"):
                    gs.update(left=0.01, right=0.99, bottom=0.01, top=0.95)
                ax_cb, ax_cb_plot = None, None

        else:
            f = f_gridspec[0]
            ax = f_gridspec[1]
            gs, cbgs = None, None
            ax_cb, ax_cb_plot = None, None

        return f, gs, cbgs, ax, ax_cb, ax_cb_plot

    def _add_colorbar(
        self,
        ax_cb=None,
        ax_cb_plot=None,
        z_data=None,
        label="",
        bins=None,
        histbins=None,
        cmap="viridis",
        norm=None,
        classified=False,
        vmin=None,
        vmax=None,
        tick_precision=3,
        density=False,
    ):

        if ax_cb is None:
            ax_cb = self.figure.ax_cb
        if ax_cb_plot is None:
            ax_cb_plot = self.figure.ax_cb_plot

        if z_data is None:
            z_data = self._props["z_data"]

        if label is None:
            label = self.plot_specs["parameter"]
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

        if self._orientation == "horizontal":
            cb_orientation = "vertical"
        elif self._orientation == "vertical":
            cb_orientation = "horizontal"

        n_cmap = cm.ScalarMappable(cmap=cmap, norm=norm)
        n_cmap.set_array(np.ma.masked_invalid(z_data))
        cb = plt.colorbar(
            n_cmap,
            cax=ax_cb,
            label=label,
            extend="both",
            spacing="proportional",
            orientation=cb_orientation,
        )

        # plot the histogram
        hist_vals, hist_bins, init_hist = ax_cb_plot.hist(
            z_data,
            orientation=self._orientation,
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
            if self._orientation == "horizontal":
                minval = np.atleast_1d(patch.get_y())[0]
                width = patch.get_width()
                height = patch.get_height()
                maxval = minval + height
            elif self._orientation == "vertical":
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
                    if self._orientation == "horizontal":
                        p0 = mpl.patches.Rectangle(
                            (0, minval),
                            width,
                            (b0 - minval),
                            facecolor=cmap(norm(minval)),
                        )
                    elif self._orientation == "vertical":
                        p0 = mpl.patches.Rectangle(
                            (minval, 0),
                            (b0 - minval),
                            height,
                            facecolor=cmap(norm(minval)),
                        )

                    b1 = splitbins[-1]
                    if self._orientation == "horizontal":
                        p1 = mpl.patches.Rectangle(
                            (0, b1), width, (maxval - b1), facecolor=cmap(norm(maxval))
                        )
                    elif self._orientation == "vertical":
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

                            if self._orientation == "horizontal":
                                pi = mpl.patches.Rectangle(
                                    (0, b0), width, (b1 - b0), facecolor=cmap(norm(b0))
                                )
                            elif self._orientation == "vertical":
                                pi = mpl.patches.Rectangle(
                                    (b0, 0), (b1 - b0), height, facecolor=cmap(norm(b0))
                                )

                            ax_cb_plot.add_patch(pi)
                else:
                    patch.set_facecolor(cmap(norm((minval + maxval) / 2)))

        # setup appearance of histogram
        if self._orientation == "horizontal":
            ax_cb_plot.invert_xaxis()

            ax_cb_plot.tick_params(
                left=False,
                labelleft=False,
                bottom=False,
                top=False,
                labelbottom=False,
                labeltop=True,
            )
            ax_cb_plot.xaxis.set_major_locator(plt.MaxNLocator(5))
            ax_cb_plot.grid(axis="x", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            ax_cb_plot.plot(
                [1, 1], [0, 1], "k--", alpha=0.5, transform=ax_cb_plot.transAxes
            )
            # make sure lower x-limit is 0
            ax_cb_plot.set_xlim(None, 0)

        elif self._orientation == "vertical":
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

            if self._orientation == "vertical":
                labelsetfunc = "set_xticklabels"
            elif self._orientation == "horizontal":
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

        return cb

    def add_gdf(self, gdf, **kwargs):
        """
        Overplot a `geopandas.GeoDataFrame` over the generated plot.
        (`plot_map()` must be called!)

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame
            A GeoDataFrame that should be added to the plot.
        **kwargs :
            all kwargs are passed to `gdf.plot(**kwargs)`
        """
        assert hasattr(self, "figure"), "you must call .plot_map() first!"

        ax = self.figure.ax

        defaultargs = dict(facecolor="none", edgecolor="k", lw=1.5)
        defaultargs.update(kwargs)

        gdf.to_crs(epsg=self.plot_specs["plot_crs"]).plot(
            ax=ax, aspect=ax.get_aspect(), **defaultargs
        )

    def add_overlay(
        self,
        dataspec,
        styledict=None,
        legend=True,
        legend_kwargs=None,
        maskshp=None,
    ):
        """
        A convenience function to add layers from NaturalEarth to an already generated
        map. (you must call `plot_map()`first!)
        Check `cartopy.shapereader.natural_earth` for details on how to specify
        layer properties.

        to change the appearance and position of the map (or to add it to the
        plot at a later stage) use

            >>> m.add_overlay_legend()

        Parameters
        ----------
        dataspec : dict
            the data-specification used to load the data via
            cartopy.shapereader.natural_earth(**dataspec)

            - (resolution='10m', category='cultural', name='urban_areas')
            - (resolution='10m', category='cultural', name='admin_0_countries')
            - (resolution='10m', category='physical', name='rivers_lake_centerlines')
            - (resolution='10m', category='physical', name='lakes')
            - etc.

        styledict : dict, optional
            a dict with style-kwargs used for plotting.
            The default is None in which case the following setting will be used:
            (facecolor='none', edgecolor='k', alpha=.5, lw=0.25)
        legend : bool, optional
            indicator if a legend should be added or not.
            The default is True.
        legend_kwargs : dict, optional
            kwargs passed to matplotlib.pyplot.legend()
            (ONLY if legend = True!).
        maskshp : gpd.GeoDataFrame
            a geopandas.GeoDataFrame that will be used as a mask for overlay
            (does not work with line-geometries!)
        """
        label = dataspec.get("name", "overlay")

        assert hasattr(self, "figure"), "you must call .plot_map() first!"

        ax = self.figure.ax

        if not all([i in dataspec for i in ["resolution", "category", "name"]]):
            assert False, (
                "the keys 'resolution', 'category' and 'name' must "
                + "be provided in dataspec!"
            )

        if styledict is None:
            styledict = dict(facecolor="none", edgecolor="k", alpha=0.5, lw=0.25)

        shp_fn = shapereader.natural_earth(**dataspec)

        overlay_df = gpd.read_file(shp_fn)
        overlay_df.crs = CRS.from_epsg(4326)
        overlay_df.to_crs(self.crs_plot, inplace=True)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            # ignore the UserWarning that area is proabably inexact when using
            # projected coordinate-systems (we only care about > 0)
            overlay_df = overlay_df[~np.isnan(overlay_df.area)]

        if maskshp is not None:
            overlay_df = gpd.overlay(overlay_df[["geometry"]], maskshp)

        _ = overlay_df.plot(ax=ax, aspect=ax.get_aspect(), label=label, **styledict)

        # save legend patches in case a legend should be created
        if not hasattr(self, "_overlay_legend"):
            self._overlay_legend = defaultdict(list)

        self._overlay_legend["handles"].append(mpl.patches.Patch(**styledict))
        self._overlay_legend["labels"].append(label)

        if legend is True:
            if legend_kwargs is None:
                legend_kwargs = dict(loc="upper center")
            self.add_overlay_legend(**legend_kwargs)

    def add_overlay_legend(self, update_hl=None, sort_order=None, **kwargs):
        """
        Add a legend for the attached overlays to the map
        (existing legend will be replaced if you call this function!)

        Parameters
        ----------
        update_hl : dict, optional
            a dict that can be used to replace the existing handles and labels
            of the legend. The signature is:

            >>> update_hl = {overlay-name : [handle, label]}

            If "handle" or "label" is None, the pre-defined values are used

            >>> m.add_overlay(dataspec={"name" : "some_overlay"})
            >>> m.add_overlay_legend(loc="upper left",
            >>>    update_hl={"some_overlay" : [plt.Line2D([], [], c="b")
            >>>                                 "A much nicer Label"]})

            >>> # use the following if you want to keep the existing handle:
            >>> m.add_overlay_legend(
            >>>    update_hl={"some_overlay" : [None, "A much nicer Label"]})
        sort_order : list, optional
            a list of integers (starting from 0) or strings (the overlay-names)
            that will be used to determine the order of the legend-entries.
            The default is None.

            >>> sort_order = [2, 1, 0, ...]
            >>> sort_order = ["overlay-name1", "overlay-name2", ...]

        **kwargs :
            kwargs passed to matplotlib.pyplot.legend().
        """
        handles = [*self._overlay_legend["handles"]]
        labels = [*self._overlay_legend["labels"]]

        if update_hl is not None:
            for key, val in update_hl.items():
                h, l = val
                if key in labels:
                    idx = labels.index(key)
                    if h is not None:
                        handles[idx] = h
                    if l is not None:
                        labels[idx] = l
                else:
                    warnings.warn(
                        f"there is no overlay with the name {key}"
                        + "... legend-handle can't be replaced..."
                    )

        if sort_order is not None:
            if all(isinstance(i, str) for i in sort_order):
                sort_order = [
                    self._overlay_legend["labels"].index(i) for i in sort_order
                ]
            elif all(isinstance(i, int) for i in sort_order):
                pass
            else:
                TypeError("sort-order must be a list of overlay-names or integers!")

        _ = self.figure.ax.legend(
            handles=handles if sort_order is None else [handles[i] for i in sort_order],
            labels=labels if sort_order is None else [labels[i] for i in sort_order],
            **kwargs,
        )

    def add_discrete_layer(
        self,
        data,
        parameter=None,
        xcoord=None,
        ycoord=None,
        label_dict=None,
        cmap=None,
        norm=None,
        vmin=None,
        vmax=None,
        color=None,
        radius=None,
        radius_crs=None,
        in_crs=None,
        cpos=None,
        legend_kwargs=True,
        shape="ellipses",
        dynamic_layer_idx=None,
        **kwargs,
    ):
        """
        add another layer of pixels

        Parameters
        ----------
        data : pandas.DataFrame
            a pandas DataFrame with column-names as specified via the parameters
            "parameter", "xcoord" and "ycoord".
        parameter : str, optional
            The name of the parameter-column to use.
            The default is None in which case the first column that is not
            one of the values specified in "xcoord" or "ycoord" is used.
        xcoord, ycoord : str, optional
            The name of the coordinate-columns. The default is 'x' and 'y'.
        label_dict : dict, optional
            a dict that contains label-entries for each unique value encountered
            in the data. The default is None.
        cmap : str or a matplotlib.Colormap, optional
            a matplotlib colormap name or instance. The default is 'viridis'.
        norm : matplotlib.colors norm, optional
            a matplotlib Norm instance to be used alongside the colormap.
            The default is None.
        color : matplotlib color, optional
            alternative to specifying cmap & norm, use a uniform color for
            all points.
        radius : str, float, list or tuple
            the radius (if list or tuple the ellipse-half-widths) of the points
            in units of the "in_crs". If "estimate", the mean difference of the
            provided coordinates will be used
        radius_crs : str or crs
            the crs in which the radius is defined
            if 'in': "in_crs" will be used
            if 'out': "plot_crs" will be used
            else the input is interpreted via pyproj.CRS.from_user_input()
        in_crs : int, dict or str, optional
            CRS descriptor ( interpreted by pyproj.CRS.from_user_input() )
            that is used to identify the CRS of the input-coordinates
            (e.g. "xcoord", "ycoord"). The default is 4326.
        cpos : str
            the position of the coordinate
            (one of 'c', 'll', 'lr', 'ul', 'ur')
        legend_kwargs : dict or bool, optional
            if False, no legend will be added.
            If a dict is provided, it will be used as kwargs for plt.legend()
            The default is True.
        shape : str
            the shapes to plot (either "ellipses" or "rectangles")
        dynamic_layer_idx : int or None

            If a "dynamic_layer_idx" is specified, the collection will only
            be drawn if `m.BM.update()` is called!
            This can be used to speed up drawing in case the collection is
            changed via a callback-function.

            The layer-index can be any number... the default values are:
                0: background
                1: overlays
                10 : annotations

            The default is None in which case the layer is added as a
            "static-background" layer
        **kwargs
            kwargs passed to the initialization of the maptlotlib collection
            (dependent on the used plot-shape!)
        """
        assert self.figure.f is not None, "you must call .plot_map() first!"

        for key in ("cmap", "array", "norm"):
            assert (
                key not in kwargs
            ), f"The key '{key}' is assigned internally by EOmaps!"

        if parameter is None:
            parameter = next(i for i in data.keys() if i not in [xcoord, ycoord])

        # ---------------------- prepare the data
        props = self._prepare_data(
            data=data,
            in_crs=in_crs,
            plot_crs=self.plot_specs["plot_crs"],
            radius=radius,
            radius_crs=radius_crs,
            cpos=cpos,
            parameter=parameter,
            xcoord=xcoord,
            ycoord=ycoord,
            shape=shape,
        )

        # ------------- plot the data
        if color:
            args = dict(array=None, cmap=None, norm=None, color=color, **kwargs)
        else:
            args = dict(
                array=props["z_data"], cmap=cmap, norm=norm, color=None, **kwargs
            )

        if shape.startswith("delauney_triangulation"):
            shape = "delauney_triangulation"
            args["masked"] = True if "masked" in shape else False
            args["flat"] = True if "flat" in shape else False

        coll = self._get_coll(shape, props, args, in_crs=in_crs, radius_crs=radius_crs)

        coll.set_clim(vmin, vmax)
        self.figure.ax.add_collection(coll)

        if dynamic_layer_idx is not None:
            # make this collection a "temporary layer"
            self.BM.add_artist(coll, layer=dynamic_layer_idx)

        if isinstance(cmap, str):
            cmap = coll.cmap
        if norm is None:
            norm = coll.norm

        if legend_kwargs is True or isinstance(legend_kwargs, dict):
            legkwargs = dict(loc="upper right")
            try:
                legkwargs.update(legend_kwargs)
            except TypeError:
                pass

            uniquevals = pd.unique(props["z_data"])
            if len(uniquevals) > 20:
                print("warnings, more than 20 entries... skipping legend generation")
            else:
                if color:
                    proxies = [Patch(color=color)]
                    labels = [
                        label_dict.get("label", "overlay") if label_dict else "overlay"
                    ]
                else:
                    proxies = [Patch(color=cmap(norm(val))) for val in uniquevals]
                    if label_dict:
                        labels = [label_dict[val] for val in uniquevals]
                    else:
                        labels = [str(val) for val in uniquevals]
                _ = self.figure.ax.legend(proxies, labels, **legkwargs)

        return coll

    def add_marker(
        self,
        ID=None,
        xy=None,
        xy_crs=None,
        radius="pixel",
        shape="ellipse",
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
            The radius of the marker.
            If "pixel", it will represent the dimensions of the selected pixel.
            The default is "pixel"

        shape : str, optional
            Indicator which shape to draw. Currently supported shapes are:
                - circle
                - ellipse
                - rectangle

            The default is "circle".
        buffer : float, optional
            A factor to scale the size of the shape. The default is 1.
        **kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)

        Returns
        -------
        None.

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
        self.cb._cb.mark(
            ID=ID, pos=xy, radius=radius, ind=None, shape=shape, buffer=buffer, **kwargs
        )

        self.BM.update()

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
        Returns
        -------
        None.

        """
        if ID is not None:
            assert xy is None, "You can only provide 'ID' or 'pos' not both!"

            xy = self.data.loc[ID][
                [self.data_specs.xcoord, self.data_specs.ycoord]
            ].values
            xy_crs = self.data_specs.crs

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
        self.cb._cb.annotate(
            ID=ID,
            pos=xy,
            val=None if ID is None else self.data.loc[ID][self.data_specs.parameter],
            ind=None if ID is None else self.data.index.get_loc(ID),
            permanent=True,
            text=text,
            **kwargs,
        )

        self.BM.update()

    @wraps(plt.savefig)
    def savefig(self, *args, **kwargs):
        self.figure.f.savefig(*args, **kwargs)

    def _get_coll(self, shape, props, args, in_crs=None, radius_crs=None):
        if in_crs is None:
            in_crs = self.data_specs.crs
        if radius_crs is None:
            radius_crs = self.plot_specs.radius_crs

        if shape.startswith("delauney_triangulation"):
            args["masked"] = True if "masked" in shape else False
            args["flat"] = True if "flat" in shape else False
            shape = "delauney_triangulation"

        if shape == "geod_circles":
            coll = self._shapes.geod_circles(
                props["xorig"],
                props["yorig"],
                in_crs,
                np.mean(props["radius"]),
                n=20,
                **args,
            )
        elif shape == "ellipses":
            coll = self._shapes.ellipses(
                props["xorig"],
                props["yorig"],
                in_crs,
                props["radius"],
                radius_crs,
                n=20,
                **args,
            )
        elif shape == "rectangles":
            coll = self._shapes.rectangles(
                props["xorig"],
                props["yorig"],
                in_crs,
                props["radius"],
                radius_crs,
                **args,
            )
        elif shape == "voroni":
            coll = self._shapes.voroni(
                props["xorig"],
                props["yorig"],
                in_crs,
                props["radius"],
                **args,
            )
        elif shape == "trimesh_rectangles":
            coll = self._shapes.trimesh_rectangles(
                props["xorig"],
                props["yorig"],
                in_crs,
                props["radius"],
                radius_crs,
                **args,
            )
        elif shape == "delauney_triangulation":
            coll = self._shapes.delauney_triangulation(
                props["xorig"],
                props["yorig"],
                in_crs,
                props["radius"],
                radius_crs,
                **args,
            )

        return coll

    def plot_map(
        self,
        f_gridspec=None,
        colorbar=True,
        coastlines=True,
        orientation="vertical",
        **kwargs,
    ):
        """
        Actually generate the map-plot based on the data provided as `m.data` and the
        specifications defined in "data_specs", "plot_specs" and "classify_specs".

        Parameters
        ----------
        f_gridspec : list, optional
            If provided, the figure and gridspec instances will be used to initialize
            the plot as a sub-plot to an already existing plot.
            The instances must be provided as:
                [matplotlib.figure, matplotlib.GridSpec]
            The default is None in which case a new figure is created.
        colorbar : bool
            Indicator if a colorbar should be added or not.
            The default is True
        coastlines : bool
            Indicator if coastlines should be added or not.
            The default is True
        **kwargs
            kwargs passed to the initialization of the matpltolib collection
            (dependent on the plot-shape)
        """

        if self.figure.ax is not None:
            warnings.warn(
                "There is already an open figure! "
                + "Either close it before creating a new one or call "
                + "`m2 = m.copy()` to copy the Maps object and then use `m2.plot_map()"
            )

        for key in ("cmap", "array", "norm"):
            assert (
                key not in kwargs
            ), f"The key '{key}' is assigned internally by EOmaps!"

        try:
            self._orientation = orientation

            if not hasattr(self, "data"):
                print("you must set the data first!")

            # ---------------------- prepare the data
            props = self._prepare_data()

            # use a cKDTree based picking to speed up picks for large collections
            self.tree = cKDTree(np.stack([props["x0"], props["y0"]], axis=1))

            # remember props for later use
            self._props = props

            title = self.plot_specs["title"]
            if title is None:
                title = self.data_specs.parameter
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

            # ------------- initialize figure
            f, gs, cbgs, ax, ax_cb, ax_cb_plot = self._init_figure(
                f_gridspec=f_gridspec,
                add_colorbar=colorbar,
            )

            self.figure.set_items(
                f=f,
                gridspec=gs,
                ax=ax,
                ax_cb=ax_cb,
                ax_cb_plot=ax_cb_plot,
                cb_gridspec=cbgs,
            )

            ax.set_title(title)

            shape = self.plot_specs["shape"]

            if "color" in kwargs and kwargs["color"] is not None:
                args = dict(array=None, cmap=None, norm=None, **kwargs)
            else:
                args = dict(array=props["z_data"], cmap=cbcmap, norm=norm, **kwargs)

            coll = self._get_coll(shape, props, args)

            coll.set_clim(vmin, vmax)
            ax.add_collection(coll)

            self.figure.coll = coll

            # add coastlines and ocean-coloring
            if coastlines is True:
                ax.coastlines()
                ax.add_feature(cfeature.OCEAN)

            if colorbar:
                # ------------- add a colorbar with a histogram
                cb = self._add_colorbar(
                    bins=bins,
                    cmap=cbcmap,
                    norm=norm,
                    classified=classified,
                )
                self.figure.cb = cb

            # ------------- add a picker that will be used by the callbacks
            self._attach_picker(maxdist=np.inf)

            # attach the pick-callback that executes the callbacks
            self.cb._add_pick_callback()

            # attach a cleanup function if the figure is closed
            # to ensure callbacks are removed and the container is reinitialized
            def on_close(event):
                for key in self.cb.get.attached_callbacks:
                    self.cb.remove(key)

                # remove all figure properties
                self.figure = self.figure.reinit()

            self.figure.f.canvas.mpl_connect("close_event", on_close)

            # set the blit-manager
            self.BM = BlitManager(self.figure.f.canvas)

            # get the extent of the added collection
            b = self.figure.coll.get_datalim(ax.transData)
            # set the axis-extent
            ax.set_extent((b.xmin, b.xmax, b.ymin, b.ymax), crs=ax.projection)

            # draw the figure
            self.figure.f.canvas.draw()

        except Exception as ex:
            self.figure = self.figure.reinit()
            raise ex

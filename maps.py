"""a collection of helper-functions to generate map-plots"""

from functools import partial, lru_cache

import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree
from pyproj import CRS, Transformer

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import cm, collections
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec, SubplotSpec
from matplotlib.patches import Patch

from cartopy import crs as ccrs
from cartopy import feature as cfeature
from cartopy.io import shapereader

from .helpers import pairwise
from .callbacks import callbacks


try:
    import mapclassify
except ImportError:
    print("No module named 'mapclassify'... classification will not work!")


def cmap_alpha(cmap, alpha, interpolate=False):
    """
    add transparency to an existing colormap

    Parameters
    ----------
    cmap : matplotlib.colormap
        the colormap to use
    alpha : float
        the transparency
    interpolate : bool
        indicator if a listed colormap (False) or a interpolated colormap (True)
        should be generated. The default is False

    Returns
    -------
    new_cmap : matplotlib.colormap
        a new colormap with the desired transparency
    """

    new_cmap = cmap(np.arange(cmap.N))
    new_cmap[:, -1] = alpha
    if interpolate:
        new_cmap = LinearSegmentedColormap("new_cmap", new_cmap)
    else:
        new_cmap = ListedColormap(new_cmap)
    return new_cmap


class _Maps_plot(object):
    def __init__(self, **kwargs):
        """
        a container for accessing the figure objects
        """
        for key, val in kwargs.items():
            setattr(self, key, val)

    # def update(self, **kwargs):
    #     for key, val in update:
    #         setattr(self, key, val)


class Maps(object):
    """
    A class to perform reading an plotting of spatial maps

    Parameters
    ----------
    respath : str, optional
        The parent path to a folder containing results
        The default is None
    dumpfolder : str, optional
        The name of the actual sub-folder containing the results.
        (with a sub-folder structure of 'cfg', 'dumps', 'results'])
        The default is None
    ncfile_name : str, optional
        The name of the NetCDF file to use (located in the 'results' subfolder)
        If only 1 NetCDF file is available, it will be used automatically.
        The default is None
    plot_specs : dict, optional
        A dict of keyword-arguments specifying the appearance of the plot
        See `set_plot_specs()` for details.
        The default is None
    classify_specs : dict, optional
        A dict of keyword-arguments that specify the classification of the data
        See `set_classify_specs()` for details.
        The default is None
    """

    def __init__(
        self,
        respath=None,
        dumpfolder=None,
        ncfile_name=None,
        plot_specs=None,
        classify_specs=None,
        orientation="horizontal",
    ):

        self.respath = respath
        self.dumpfolder = dumpfolder
        self.ncfile_name = ncfile_name

        self.orientation = orientation

        # initialize default plot specs
        self.data_specs = dict(
            parameter=None,
            xcoord="lon",
            ycoord="lat",
            in_crs=4326,
        )

        self.plot_specs = dict(
            label=None,
            title=None,
            cmap=plt.cm.viridis.copy(),
            plot_epsg=4326,
            radius_crs="in",
            radius=None,
            histbins=256,
            tick_precision=2,
            vmin=None,
            vmax=None,
            callback=None,
            cpos="c",
            alpha=1,
            add_colorbar=True,
            coastlines=True,
            density=False,
            shape="ellipses",
        )

        self.classify_specs = dict()

        if plot_specs is not None:
            self.plot_specs.update(plot_specs)
        if classify_specs is not None:
            self.classify_specs.update(classify_specs)

        self.cb = callbacks(self)
        self._attached_cbs = dict()

    def copy(self, **kwargs):
        """
        create a copy of the class that inherits all specifications
        from the parent class (already loaded data is not copied!)

        -> useful to quickly create plots with similar configuration but different data

        Parameters
        ----------
        **kwargs :
            kwargs passed to the initialization of the new class
            (e.g. overriding the specifications of the parent class).

        Returns
        -------
        copy_cls : maps.Maps object
            a new Maps class.
        """

        initdict = dict()
        for key in ["respath", "dumpfolder", "ncfile_name"]:
            if key in kwargs:
                initdict[key] = kwargs[key]
            else:
                initdict[key] = self.__dict__.get(key, None)

        initdict["data_specs"] = self.data_specs
        initdict["plot_specs"] = {
            key: val for key, val in self.plot_specs.items() if key != "callback"
        }
        initdict["classify_specs"] = {**self.classify_specs}

        # create a new class
        cls = self.__class__
        copy_cls = cls.__new__(cls)

        # re-bind the callback methods to the newly created copy-class
        cb = self.plot_specs["callback"]
        if cb is not None:
            new_cb = []
            for f in cb:
                if hasattr(f, "__func__"):
                    new_cb.append(f.__func__.__get__(copy_cls))
            initdict["plot_specs"]["callback"] = new_cb
        else:
            initdict["plot_specs"]["callback"] = None

        copy_cls.__dict__.update(initdict)
        return copy_cls

    def set_data_specs(self, **kwargs):
        """
        Use this function to update the data-specs

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
            if key in self.data_specs:
                self.data_specs[key] = val
            else:
                print(f'"{key}" is not a valid data_specs parameter!')

    def set_plot_specs(self, **kwargs):
        """
        Use this function to update the plot-specs

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
        plot_epsg : in, optional
            The epsg-code of the projection to use for plotting. The default is 4326.
        radius_crs : str, optional
            Indicator if the radius is specified in data-crs units (e.g. "in")-
            or in plot-crs units (e.g. "out"). The default is "in".
        radius : float, optional
            The radius of the patches in the crs defined via "radius_crs".
            If None, the radius will be automatically determined from the x-y coordinate
            separation of the data. The default is None.
        histbins : int, optional
            The number of histogram-bins to use for the colorbar. The default is 256.
        tick_precision : int, optional
            The precision of the tick-labels in the colorbar. The default is 2.
        vmin, vmax : float, optional
            Min- and max. values assigned to the colorbar. The default is None.
        callback : list of callables, optional
            List of callback-functions that are triggered if a patch is double-clicked.
            There are some useful builtin-callbacks:

            >>> m = Maps(...)
            >>> m.set_plot_specs(
            >>>     callback=[
            >>>         m.cb_annotate  # annotate properties of selected patch
            >>>         m.cb_load      # load the associated fit-object (if available)
            >>>         m.cb_print     # print info to the console on click
            >>>     ])

            You can also define custom functions that are automatically connected to
            the Maps-class instance:

            >>> m = Maps()
            >>>
            >>> def some_callback(self, **kwargs)
            >>>     ID = kwargs["ID"]    # index of the selected pixel in the dataframe
            >>>     ID = kwargs["pos"]   # (x, y) position of the selected pixel
            >>>     ...
            >>>     ... add any functionality you want ...
            >>>     ...
            >>>
            >>> m.set_plot_specs(callback=[some_callback])

            The default is None.
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
            Indicator if "rectangles" or "ellipses" should be potted
            The default is "ellipses".
        """

        for key, val in kwargs.items():
            if key in self.plot_specs:
                if key == "cmap":
                    self.plot_specs[key] = plt.get_cmap(val)
                else:
                    self.plot_specs[key] = val
            else:
                print(f'"{key}" is not a valid plot_specs parameter!')

    def set_classify_specs(self, **kwargs):
        """
        Set classification specifications for the data
        (classification is performed by the `mapclassify` module)

        Parameters
        ----------
        scheme : str, optional
            The classification scheme to use.
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
        for key, val in kwargs.items():
            self.classify_specs[key] = val

    def set_orientation(self, orientation="horizontal"):
        """
        set the orientation of the plot

        Parameters
        ----------
        orientation : str
            the orientation to use (either "horizontal" or "vertical").
            The default is "horizontal".
        """
        self.orientation = orientation

    def plot_map(self, f_gridspec=None):
        """
        Actually generate the map-plot
        (you must set the data first!)

        Parameters
        ----------
        f_gridspec : list, optional
            If provided, the figure and gridspec instances will be used to initialize
            the plot as a sub-plot to an already existing plot.
            The instances must be provided as:  [matplotlib.figure, matplotlib.GridSpec]
            The default is None in which case a new figure is created.
        """
        if not hasattr(self, "data"):
            print("you must set the data first!")

        self._spatial_plot(
            data=self.data, **self.plot_specs, **self.data_specs, f_gridspec=f_gridspec
        )

    def _spatial_plot(
        self,
        data,
        parameter=None,
        xcoord="x",
        ycoord="y",
        label=None,
        title="",
        cmap="viridis",
        radius=None,
        radius_crs="in",
        in_crs=4326,
        plot_epsg=4326,
        histbins=256,
        tick_precision=2,
        vmin=None,
        vmax=None,
        callback=None,
        cpos="c",
        f_gridspec=None,
        alpha=1,
        add_colorbar=True,
        coastlines=True,
        density=False,
        shape="ellipses",
    ):
        """
        A fast way to genereate a plot of "projected circles" of datapoints.

        Parameters
        ----------
        data : pandas.DataFrame
            a pandas DataFrame with column-names as specified via the parameters
            "parameter", "xcoord" and "ycoord".
        parameter : str, optional
            The name of the parameter-column to use.
            The default is None in which case the first column that is not
            one of the values specified in "xcoord" or "ycoord" is used.
        label : str, optional
            A label for the colorbar. The default is 'data'.
        title : str, optional
            A title for the plot. The default is ''.
        cmap : str or a matplotlib.Colormap, optional
            a matplotlib colormap name or instance. The default is 'viridis'.
        radius : float, list or tuple
            the radius (if list or tuple the ellipse-half-widths) of the points
            in units of the "in_crs". If None, the mean difference of the
            provided coordinates will be used
        radius_crs : str or crs
            the crs in which the radius is defined
            if 'in': "in_crs" will be used
            if 'out': "plot_epsg" will be used
            else the input is interpreted via pyproj.CRS.from_user_input()
        in_crs : int, dict or str, optional
            CRS descriptor ( interpreted by pyproj.CRS.from_user_input() )
            that is used to identify the CRS of the input-coordinates
            (e.g. "xcoord", "ycoord"). The default is 4326.
        plot_epsg : int, optional
            The epsg-code of the projection that is used to generate the plot.
            The default is 4326.
        histbins : int, optional
            The number of histogram bins. The default is 256.
        xcoord, ycoord : str, optional
            The name of the coordinate-columns. The default is 'x' and 'y'.
        tick_precision : int,
            The number of digits (after the comma) to print as colorbar tick-labels
            The default is 2.
        vmin, vmax : float, optional
            min- and max- values of the colorbar.
            The default is None in which case the whole data-range will be used.
        scheme : str, optional
            The name of a classification scheme of the "mapclassify" module.
            The default is None.
        callback: callable, optional
            a function that will be called when a pixel is clicked.
            call-signature:  callback(ID)
            The default is None.
        cpos : str
            the position of the coordinate
            (one of 'c', 'll', 'lr', 'ul', 'ur')
        f_gridspec : [matplotlib.figure, matplotlib.Gridspec]
            if provided, the gridspec is used instead of generating a new
            figure. provide as: [figure, gridspec]
        alpha : float
            global transparency value
        add_colorbar : bool
            indicator if a colorbar (with histogram) should be plotted or not
            The default is True.
        density : bool
            indicator if the colorbar-histogram should show the value-count (False)
            or the probability density (True)
            The default is False.
        shape : str
            the shapes to plot (either "ellipses" or "rectangles")
        Returns
        -------
        dict :
            a dict containing all objects required to update the plot
        """

        if alpha < 1:
            cmap = cmap_alpha(cmap, alpha)

        # ---------------------- prepare the data
        parameter, ids, z_data, x0, y0, w, h, theta = self._prepare_data(
            data=data,
            in_crs=in_crs,
            plot_epsg=plot_epsg,
            radius=radius,
            radius_crs=radius_crs,
            cpos="c",
            parameter=parameter,
            xcoord=xcoord,
            ycoord=ycoord,
        )

        if label is None:
            label = parameter
        if title is None:
            if self.dumpfolder is not None and self.ncfile_name is not None:
                title = self.dumpfolder + "  ||  " + self.ncfile_name + ".nc"
            else:
                title = parameter
        if vmin is None:
            vmin = np.nanmin(z_data)
        if vmax is None:
            vmax = np.nanmax(z_data)

        # ---------------------- classify the data
        cbcmap, norm, bins, classified = self._classify_data(
            z_data=z_data,
            cmap=cmap,
            histbins=histbins,
            vmin=vmin,
            vmax=vmax,
            classify_specs=self.classify_specs,
        )

        # ------------- initialize figure
        f, gs, cbgs, ax, cb_ax, cb_plot_ax = self._init_figure(
            f_gridspec=f_gridspec,
            plot_epsg=plot_epsg,
            add_colorbar=add_colorbar,
        )

        ax.set_xlim(x0.min(), x0.max())
        ax.set_ylim(y0.min(), y0.max())
        ax.set_title(title)

        # ax.set_extent((x0.min(), x0.max(), y0.min(), y0.max()))
        # -------------------------------

        # ------------- plot the data
        coll = self._add_collection(
            ax=ax,
            z_data=z_data,
            x0=x0,
            y0=y0,
            w=w,
            h=h,
            theta=theta,
            cmap=cbcmap,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
            ids=ids,
            shape=shape,
        )

        # add coastlines and ocean-coloring
        if coastlines is True:
            ax.coastlines()
            ax.add_feature(cfeature.OCEAN)

        if add_colorbar:
            # ------------- add a colorbar with a histogram
            cb = self._add_colorbar(
                cb_ax=cb_ax,
                cb_plot_ax=cb_plot_ax,
                z_data=z_data,
                label=label,
                bins=bins,
                histbins=histbins,
                cmap=cbcmap,
                norm=norm,
                classified=classified,
                vmin=vmin,
                vmax=vmax,
                tick_precision=tick_precision,
                density=density,
            )

            # save colorbar instance for later use
            f._rt1_used_colorbar = cb
        else:
            cb = None

        f.canvas.draw_idle()

        # ------------- add a callback

        # use a cKDTree based picking to speed up picks for large collections
        tree = cKDTree(np.stack([x0, y0], axis=1))
        maxdist = np.max([w.max(), h.max()])

        def picker(artist, event):
            if event.dblclick:
                dist, index = tree.query((event.xdata, event.ydata))
                if dist < maxdist:
                    return True, dict(ind=index)
                else:
                    return True, dict(ind=None)
            return False, None

        coll.set_picker(picker)

        if callback is not None:

            def onpick(event):
                if isinstance(event.artist, collections.EllipseCollection):
                    ind = event.ind

                    clickdict = dict(
                        pos=coll.get_offsets()[ind],
                        ID=coll.get_urls()[ind],
                        val=coll.get_array()[ind],
                        f=f,
                    )

                    if callback is not None:
                        for cb_i in np.atleast_1d(callback):
                            cb_i(**clickdict)
                elif isinstance(event.artist, collections.PolyCollection):
                    ind = event.ind

                    clickdict = dict(
                        pos=coll._Maps_positions[ind],
                        ID=coll.get_urls()[ind],
                        val=coll.get_array()[ind],
                        f=f,
                    )

                    if callback is not None:
                        for cb_i in np.atleast_1d(callback):
                            cb_i(**clickdict)

            f.canvas.mpl_connect("pick_event", onpick)

        self.updatedict = dict(
            f=f,
            gridspec=gs,
            colorbar_gs=cbgs,
            ax=ax,
            ax_cb=cb_ax,
            ax_cb_plot=cb_plot_ax,
            cb=cb,
            coll=coll,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            histbins=histbins,
            title=title,
            label=label,
            tick_precision=tick_precision,
        )

        self.figure = _Maps_plot(**self.updatedict)

    def _prepare_data(
        self,
        data,
        in_crs,
        plot_epsg,
        radius=None,
        radius_crs="in",
        cpos="c",
        parameter=None,
        xcoord=None,
        ycoord=None,
    ):

        if parameter is None:
            parameter = next(i for i in data.keys() if i not in [xcoord, ycoord])
            self.set_data_specs(parameter=parameter)

        assert isinstance(parameter, str), (
            "you must proivide a single string" + "as parameter name!"
        )

        z_data = data[parameter].ravel()
        ids = data.index.values.ravel()

        # ------ project circles
        transformer = Transformer.from_crs(
            CRS.from_user_input(in_crs), CRS.from_user_input(plot_epsg), always_xy=True
        )
        xorig, yorig = (data[xcoord].ravel(), data[ycoord].ravel())

        # transform center-points
        x0, y0 = transformer.transform(xorig, yorig)

        if radius is None:
            if radius_crs == "in":
                radiusx = np.abs(np.diff(np.unique(xorig)).mean()) / 2.0
                radiusy = np.abs(np.diff(np.unique(yorig)).mean()) / 2.0
            elif radius_crs == "out":
                radiusx = np.abs(np.diff(np.unique(x0)).mean()) / 2.0
                radiusy = np.abs(np.diff(np.unique(y0)).mean()) / 2.0
        elif isinstance(radius, (list, tuple)):
            radiusx, radiusy = radius
        else:
            radiusx = radius
            radiusy = radius

        if radius_crs == "in":
            # fix position of pixel-center
            if cpos == "c":
                pass
            elif cpos == "ll":
                xorig += radiusx
                yorig += radiusy
            elif cpos == "ul":
                xorig += radiusx
                yorig -= radiusy
            elif cpos == "lr":
                xorig += radiusx
                yorig -= radiusy
            elif cpos == "ur":
                xorig -= radiusx
                yorig -= radiusx

        # transform corner-points
        if radius_crs == "in":
            x3, y3 = transformer.transform(xorig + radiusx, yorig)
            x4, y4 = transformer.transform(xorig, yorig + radiusy)
        elif radius_crs == "out":
            x3, y3 = x0 + radiusx, y0
            x4, y4 = x0, y0 + radiusy
        else:
            radius_t = Transformer.from_crs(
                CRS.from_user_input(in_crs),
                CRS.from_user_input(radius_crs),
                always_xy=True,
            )
            radius_t_p = Transformer.from_crs(
                CRS.from_user_input(radius_crs),
                CRS.from_user_input(plot_epsg),
                always_xy=True,
            )

            x0r, y0r = radius_t.transform(xorig, yorig)
            x3, y3 = radius_t_p.transform(x0r + radiusx, y0r)
            x4, y4 = radius_t_p.transform(x0r, y0r + radiusy)

        w = np.abs(x3 - x0)
        h = np.abs(y4 - y0)
        theta = np.rad2deg(np.arcsin(np.abs(y3 - y0) / w))

        if radius_crs == "out":
            # fix position of pixel-center
            if cpos == "c":
                pass
            elif cpos == "ll":
                x0 += radiusx
                y0 += radiusy
            elif cpos == "ul":
                x0 += radiusx
                y0 -= radiusy
            elif cpos == "lr":
                x0 += radiusx
                y0 -= radiusy
            elif cpos == "ur":
                x0 -= radiusx
                y0 -= radiusx

        return parameter, ids, z_data, x0, y0, w, h, theta

    def _classify_data(self, z_data, cmap, histbins, vmin, vmax, classify_specs=None):
        if isinstance(cmap, str):
            cmap = plt.get_cmap(cmap)

        # evaluate classification
        if classify_specs is not None and len(classify_specs) > 0:
            scheme = classify_specs["scheme"]
            args = {key: val for key, val in classify_specs.items() if key != "scheme"}

            classified = True
            mapc = getattr(mapclassify, scheme)(z_data[~np.isnan(z_data)], **args)
            bins = np.unique([mapc.y.min(), *mapc.bins])
            nbins = len(bins)
            norm = mpl.colors.BoundaryNorm(bins, nbins)
            colors = cmap(np.linspace(0, 1, nbins))
        else:
            classified = False
            if isinstance(histbins, int):
                nbins = histbins
                bins = None
            else:
                nbins = len(histbins)
                bins = histbins
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
            gs_func = GridSpec
        else:
            f = f_gridspec[0]
            gs_func = partial(GridSpecFromSubplotSpec, subplot_spec=f_gridspec[1])

        if self.orientation == "horizontal":
            # gridspec for the plot
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
        elif self.orientation == "vertical":
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

    def _init_figure(self, f_gridspec=None, plot_epsg=4326, add_colorbar=True):
        if f_gridspec is None or isinstance(f_gridspec[1], SubplotSpec):
            f, gs, cbgs = self._init_fig_grid(f_gridspec=f_gridspec)

            if plot_epsg == 4326:
                cartopy_proj = ccrs.PlateCarree()
            else:
                cartopy_proj = ccrs.epsg(plot_epsg)

            if add_colorbar:
                ax = f.add_subplot(
                    gs[0], projection=cartopy_proj, aspect="equal", adjustable="datalim"
                )
                # axes for histogram
                cb_plot_ax = f.add_subplot(cbgs[0], frameon=False, label="cb_plot_ax")
                cb_plot_ax.tick_params(rotation=90, axis="x")
                # axes for colorbar
                cb_ax = f.add_subplot(cbgs[1], label="cb_ax")
                # join colorbar and histogram axes
                if self.orientation == "horizontal":
                    cb_plot_ax.get_shared_y_axes().join(cb_plot_ax, cb_ax)
                elif self.orientation == "vertical":
                    cb_plot_ax.get_shared_x_axes().join(cb_plot_ax, cb_ax)
            else:
                ax = f.add_subplot(
                    gs[:], projection=cartopy_proj, aspect="equal", adjustable="datalim"
                )
                cb_ax, cb_plot_ax = None, None

        else:
            f = f_gridspec[0]
            ax = f_gridspec[1]
            gs, cbgs = None, None
            cb_ax, cb_plot_ax = None, None

        return f, gs, cbgs, ax, cb_ax, cb_plot_ax

    def _add_collection(
        self,
        ax,
        z_data,
        x0,
        y0,
        w,
        h,
        theta,
        cmap,
        vmin,
        vmax,
        norm,
        ids,
        color=None,
        shape="ellipses",
    ):

        if shape == "ellipses":
            coll = collections.EllipseCollection(
                2 * w,
                2 * h,
                theta,
                offsets=list(zip(x0, y0)),
                units="x",
                transOffset=ax.transData,
            )

        if shape == "rectangles":
            # see https://stackoverflow.com/a/61664630/9703451

            theta = -np.deg2rad(theta)

            # top right
            p0 = np.array(
                [
                    x0 + w * np.cos(theta) - h * np.sin(theta),
                    y0 + w * np.sin(theta) + h * np.cos(theta),
                ]
            ).T
            # top left
            p1 = np.array(
                [
                    x0 - w * np.cos(theta) - h * np.sin(theta),
                    y0 - w * np.sin(theta) + h * np.cos(theta),
                ]
            ).T
            # bottom left
            p2 = np.array(
                [
                    x0 - w * np.cos(theta) + h * np.sin(theta),
                    y0 - w * np.sin(theta) - h * np.cos(theta),
                ]
            ).T
            # bottom right
            p3 = np.array(
                [
                    x0 + w * np.cos(theta) + h * np.sin(theta),
                    y0 + w * np.sin(theta) - h * np.cos(theta),
                ]
            ).T

            verts = np.array(list(zip(p0, p1, p2, p3)))

            coll = collections.PolyCollection(
                verts=verts,
                transOffset=ax.transData,
            )

            # add centroid positions (used by the picker in self._spatial_plot)
            coll._Maps_positions = list(zip(x0, y0))

        if color is not None:
            coll.set_color(color)
        else:
            coll.set_array(np.ma.masked_invalid(z_data))
            coll.set_cmap(cmap)
            coll.set_clim(vmin, vmax)
            coll.set_norm(norm)
        coll.set_urls(ids)

        # coll.set_facecolor(cbcmap(z_data))    # do this to properly treat nan-values
        # coll.set_edgecolor('none')
        ax.add_collection(coll)

        return coll

    def _add_colorbar(
        self,
        cb_ax,
        cb_plot_ax,
        z_data,
        label="",
        bins=None,
        histbins=256,
        cmap="viridis",
        norm=None,
        classified=False,
        vmin=None,
        vmax=None,
        tick_precision=3,
        density=False,
    ):

        if self.orientation == "horizontal":
            cb_orientation = "vertical"
        elif self.orientation == "vertical":
            cb_orientation = "horizontal"

        n_cmap = cm.ScalarMappable(cmap=cmap, norm=norm)
        n_cmap.set_array(np.ma.masked_invalid(z_data))
        cb = plt.colorbar(
            n_cmap,
            cax=cb_ax,
            label=label,
            extend="both",
            spacing="proportional",
            orientation=cb_orientation,
        )

        # plot the histogram
        hist_vals, hist_bins, init_hist = cb_plot_ax.hist(
            z_data,
            orientation=self.orientation,
            bins=histbins,
            color="k",
            align="mid",
            # range=(norm.vmin, norm.vmax),
            density=density,
        )

        # color the histogram
        for patch in list(cb_plot_ax.patches):
            # the list is important!! since otherwise we change ax.patches
            # as we iterate over it... which is not a good idea...
            if self.orientation == "horizontal":
                minval = np.atleast_1d(patch.get_y())[0]
                width = patch.get_width()
                height = patch.get_height()
                maxval = minval + height
            elif self.orientation == "vertical":
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
                    if self.orientation == "horizontal":
                        p0 = mpl.patches.Rectangle(
                            (0, minval),
                            width,
                            (b0 - minval),
                            facecolor=cmap(norm(minval)),
                        )
                    elif self.orientation == "vertical":
                        p0 = mpl.patches.Rectangle(
                            (minval, 0),
                            (b0 - minval),
                            height,
                            facecolor=cmap(norm(minval)),
                        )

                    b1 = splitbins[-1]
                    if self.orientation == "horizontal":
                        p1 = mpl.patches.Rectangle(
                            (0, b1), width, (maxval - b1), facecolor=cmap(norm(maxval))
                        )
                    elif self.orientation == "vertical":
                        p1 = mpl.patches.Rectangle(
                            (b1, 0), (maxval - b1), height, facecolor=cmap(norm(maxval))
                        )

                    cb_plot_ax.add_patch(p0)
                    cb_plot_ax.add_patch(p1)

                    # add in-between patches
                    if len(splitbins > 1):
                        for b0, b1 in pairwise(splitbins):
                            pi = mpl.patches.Rectangle(
                                (0, b0), width, (b1 - b0), facecolor=cmap(norm(b0))
                            )

                            if self.orientation == "horizontal":
                                pi = mpl.patches.Rectangle(
                                    (0, b0), width, (b1 - b0), facecolor=cmap(norm(b0))
                                )
                            elif self.orientation == "vertical":
                                pi = mpl.patches.Rectangle(
                                    (b0, 0), (b1 - b0), height, facecolor=cmap(norm(b0))
                                )

                            cb_plot_ax.add_patch(pi)
                else:
                    patch.set_facecolor(cmap(norm((minval + maxval) / 2)))

        # setup appearance of histogram
        if self.orientation == "horizontal":
            cb_plot_ax.invert_xaxis()

            cb_plot_ax.tick_params(
                left=False,
                labelleft=False,
                bottom=False,
                top=False,
                labelbottom=False,
                labeltop=True,
            )
            cb_plot_ax.xaxis.set_major_locator(plt.MaxNLocator(5))
            cb_plot_ax.grid(axis="x", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            cb_plot_ax.plot(
                [1, 1], [0, 1], "k--", alpha=0.5, transform=cb_plot_ax.transAxes
            )
        elif self.orientation == "vertical":
            cb_plot_ax.tick_params(
                left=False,
                labelleft=True,
                bottom=False,
                top=False,
                labelbottom=False,
                labeltop=False,
            )
            cb_plot_ax.yaxis.set_major_locator(plt.MaxNLocator(5))
            cb_plot_ax.grid(axis="y", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            cb_plot_ax.plot(
                [0, 1], [0, 0], "k--", alpha=0.5, transform=cb_plot_ax.transAxes
            )

        cb.outline.set_visible(False)

        # ensure that ticklabels are correct if a classification is used
        if classified:
            cb.set_ticks([i for i in bins if i >= vmin and i <= vmax])

            if self.orientation == "vertical":
                labelsetfunc = "set_xticklabels"
            elif self.orientation == "horizontal":
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
        ax = self.updatedict["ax"]

        defaultargs = dict(facecolor="none", edgecolor="k", lw=1.5)
        defaultargs.update(kwargs)

        gdf.plot(ax=ax, aspect=ax.get_aspect(), **defaultargs)

    def add_overlay(
        self,
        dataspec,
        styledict=None,
        legend=True,
        legendlabel=None,
        legend_loc="upper right",
        maskshp=None,
    ):
        """
        A convenience function to add layers from NaturalEarth to an already generated
        map. (you must call `plot_map()`first!)
        Check `cartopy.shapereader.natural_earth` for details on how to specify
        layer properties.

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
            indicator if a legend should be added or not. The default is True.
        legendlabel : str, optional
            The label of the legend. If None, the name specified in dataspec is used.
            The default is None.
        legend_loc : str, optional
            the position of the legend. The default is 'upper right'.
        maskshp : gpd.GeoDataFrame
            a geopandas.GeoDataFrame that will be used as a mask for overlay
            (does not work with line-geometries!)
        """
        if legendlabel is None:
            legendlabel = dataspec.get("name", "overlay")

        assert hasattr(self, "updatedict"), "you must call .plot_map() first!"

        ax = self.updatedict["ax"]

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
        overlay_df.to_crs(self.plot_specs["plot_epsg"], inplace=True)

        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            # ignore the UserWarning that area is proabably inexact when using
            # projected coordinate-systems (we only care about > 0)
            overlay_df = overlay_df[~np.isnan(overlay_df.area)]

        if maskshp is not None:
            overlay_df = gpd.overlay(overlay_df[["geometry"]], maskshp)

        _ = overlay_df.plot(ax=ax, aspect=ax.get_aspect(), **styledict)

        if legend is True:
            ax.legend(
                handles=[mpl.patches.Patch(**styledict)],
                labels=[legendlabel],
                loc=legend_loc,
            )

    def add_discrete_layer(
        self,
        data,
        parameter=None,
        xcoord="x",
        ycoord="y",
        label_dict=None,
        cmap="viridis",
        norm=None,
        vmin=None,
        vmax=None,
        color=None,
        radius=None,
        radius_crs="in",
        in_crs=4326,
        cpos="c",
        legend_kwargs=True,
        shape="ellipses",
    ):
        """
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
        radius : float, list or tuple
            the radius (if list or tuple the ellipse-half-widths) of the points
            in units of the "in_crs". If None, the mean difference of the
            provided coordinates will be used
        radius_crs : str or crs
            the crs in which the radius is defined
            if 'in': "in_crs" will be used
            if 'out': "plot_epsg" will be used
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
        """

        ax = self.updatedict["ax"]

        # ---------------------- prepare the data
        parameter, ids, z_data, x0, y0, w, h, theta = self._prepare_data(
            data=data,
            in_crs=in_crs,
            plot_epsg=self.plot_specs["plot_epsg"],
            radius=radius,
            radius_crs=radius_crs,
            cpos=cpos,
            parameter=parameter,
            xcoord=xcoord,
            ycoord=ycoord,
        )

        # ------------- plot the data
        coll = self._add_collection(
            ax=ax,
            z_data=z_data,
            x0=x0,
            y0=y0,
            w=w,
            h=h,
            theta=theta,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
            ids=ids,
            color=color,
            shape=shape,
        )

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

            uniquevals = pd.unique(z_data)
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
                _ = ax.legend(proxies, labels, **legkwargs)

        return coll

    def attach_callback(self, callback):
        """
        attach a callback to the plot that will be executed if a pixel is double-clicked

        A list of pre-defined callbacks is available at `m.cb...`

            >>> m.attach_callback(m.cb.annotate)
            >>> m.attach_callback(m.cb.scatter)
            >>> # to remove the callback again, call:
            >>> m.remove_callback(m.cb.scatter)

        """

        if callback is None:
            return

        # re-bind the callback methods to the Maps object
        # in case custom functions are used
        if hasattr(callback, "__func__"):
            callback = callback.__func__.__get__(self)
        else:
            newcb = partial(callback, self=self)
            newcb.__name__ = callback.__name__
            callback = newcb

        # ------------- add a callback
        def onpick(event):
            ind = event.ind
            if ind is not None:
                if isinstance(event.artist, collections.EllipseCollection):
                    clickdict = dict(
                        pos=self.figure.coll.get_offsets()[ind],
                        ID=self.figure.coll.get_urls()[ind],
                        val=self.figure.coll.get_array()[ind],
                    )

                    callback(**clickdict)
                elif isinstance(event.artist, collections.PolyCollection):
                    clickdict = dict(
                        pos=self.figure.coll._Maps_positions[ind],
                        ID=self.figure.coll.get_urls()[ind],
                        val=self.figure.coll.get_array()[ind],
                    )

                    callback(**clickdict)
            else:
                if "cb_annotate" in self._attached_cbs:
                    self._cb_hide_annotate()

        self._attached_cbs[callback.__name__] = self.figure.f.canvas.mpl_connect(
            "pick_event", onpick
        )

    def remove_callback(self, callback):
        name = callback.__name__

        self.figure.f.canvas.mpl_disconnect(self._attached_cbs[name])

        # call cleanup methods on removal
        if hasattr(self.cb, f"_{name}_cleanup"):
            getattr(self.cb, f"_{name}_cleanup")(self)

    @lru_cache()
    def _get_crs(self, crs):
        return CRS.from_user_input(crs)

    def _cb_hide_annotate(self):
        # a function to hide the annotation of an empty area is clicked
        if hasattr(self, "annotation"):
            self.annotation.set_visible(False)
            self.updatedict["f"].canvas.draw_idle()

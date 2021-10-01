"""a collection of helper-functions to generate map-plots"""

from functools import partial, lru_cache
import warnings

import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree
from pyproj import CRS, Transformer

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import cm, collections
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec, SubplotSpec
from matplotlib.patches import Patch

from cartopy import crs as ccrs
from cartopy import feature as cfeature
from cartopy.io import shapereader

from .helpers import pairwise, cmap_alpha
from .callbacks import callbacks


try:
    import mapclassify
except ImportError:
    print("No module named 'mapclassify'... classification will not work!")


class _Maps_plot(object):
    def __init__(self, **kwargs):
        """
        a container for accessing the figure objects
        """
        for key, val in kwargs.items():
            setattr(self, key, val)


class Maps(object):
    """
    A class to perform reading an plotting of spatial maps

    Parameters
    ----------
    orientation : str, optional
        Indicator if the colorbar should be plotted right of the map ("horizontal")
        or below the map ("vertical"). The default is "vertical"
    """

    def __init__(
        self,
        orientation="vertical",
    ):

        self.orientation = orientation

        # default data specs
        self._data_specs = dict(
            parameter=None,
            xcoord="lon",
            ycoord="lat",
            in_crs=4326,
        )

        # default plot specs
        self._plot_specs = dict(
            label=None,
            title=None,
            cmap=plt.cm.viridis.copy(),
            plot_epsg=4326,
            radius_crs="in",
            radius="estimate",
            histbins=256,
            tick_precision=2,
            vmin=None,
            vmax=None,
            cpos="c",
            alpha=1,
            add_colorbar=True,
            coastlines=True,
            density=False,
            shape="ellipses",
        )

        # default classify specs
        self._classify_specs = dict()

        self._attached_cbs = dict()  # dict to memorize attached callbacks

        self._cb = callbacks(self)

    def copy(
        self,
        data_specs=None,
        plot_specs=None,
        classify_specs=None,
    ):
        """
        create a copy of the class that inherits all specifications
        from the parent class (already loaded data is not copied!)

        -> useful to quickly create plots with similar configuration but different data

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
        initdict["data_specs"] = {**self.data_specs}
        initdict["plot_specs"] = {**self.plot_specs}
        initdict["classify_specs"] = {**self.classify_specs}

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
        copy_cls.set_classify_specs(**initdict["classify_specs"])

        return copy_cls

    @property
    def cb(self):
        """
        accessor to pre-defined callback functions
        """
        return self._cb

    @property
    def data_specs(self):
        return self._data_specs

    @data_specs.setter
    def data_specs(self, val):
        raise AttributeError("use 'm.set_data_specs' to set data-specifications!")

    @property
    def plot_specs(self):
        return self._plot_specs

    @plot_specs.setter
    def plot_specs(self, val):
        raise AttributeError("use 'm.set_plot_specs' to set plot-specifications!")

    @property
    def classify_specs(self):
        return self._classify_specs

    @classify_specs.setter
    def classify_specs(self, val):
        raise AttributeError(
            "use 'm.set_classify_specs' to set classification-specifications!"
        )

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
            if key in self._data_specs:
                self._data_specs[key] = val
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
        radius : str, float or tuple, optional
            The radius of the patches in the crs defined via "radius_crs".
            If "estimate", the radius will be automatically determined from the
            x-y coordinate separation of the data. The default is "estimate".
        histbins : int, optional
            The number of histogram-bins to use for the colorbar. The default is 256.
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
            Indicator if "rectangles" or "ellipses" should be potted
            The default is "ellipses".
        """

        for key, val in kwargs.items():
            if key in self.plot_specs:
                if key == "cmap":
                    self._plot_specs[key] = plt.get_cmap(val)
                else:
                    self._plot_specs[key] = val
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
            self._classify_specs[key] = val

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
        Actually generate the map-plot based on the data provided as `m.data` and the
        specifications defined in "data_specs", "plot_specs" and "classify_specs".

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
        radius="estimate",
        radius_crs="in",
        in_crs=4326,
        plot_epsg=4326,
        histbins=256,
        tick_precision=2,
        vmin=None,
        vmax=None,
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
        radius : str, float, list or tuple
            the radius (if list or tuple the ellipse-half-widths) of the points
            in units of the "in_crs". If "estimate", the mean difference of the
            provided coordinates will be used.
            The default is "estimate"
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

        if parameter is None:
            parameter = next(i for i in data.keys() if i not in [xcoord, ycoord])
            self.set_data_specs(parameter=parameter)

        if alpha < 1:
            cmap = cmap_alpha(cmap, alpha)

        # ---------------------- prepare the data
        props = self._prepare_data(
            data=data,
            in_crs=in_crs,
            plot_epsg=plot_epsg,
            radius=radius,
            radius_crs=radius_crs,
            cpos=cpos,
            parameter=parameter,
            xcoord=xcoord,
            ycoord=ycoord,
        )

        if label is None:
            label = parameter
        if title is None:
            title = parameter

        if vmin is None:
            vmin = np.nanmin(props["z_data"])
        if vmax is None:
            vmax = np.nanmax(props["z_data"])

        # ---------------------- classify the data
        cbcmap, norm, bins, classified = self._classify_data(
            z_data=props["z_data"],
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

        ax.set_xlim(props["x0"].min(), props["x0"].max())
        ax.set_ylim(props["y0"].min(), props["y0"].max())
        ax.set_title(title)

        # ax.set_extent((x0.min(), x0.max(), y0.min(), y0.max()))
        # -------------------------------

        # ------------- plot the data
        coll = self._add_collection(
            ax=ax,
            props=props,
            cmap=cbcmap,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
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
                z_data=props["z_data"],
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

        # ------------- add a picker that will be used by the callbacks
        # use a cKDTree based picking to speed up picks for large collections
        tree = cKDTree(np.stack([props["x0"], props["y0"]], axis=1))
        maxdist = np.max([np.max(props["w"]), np.max(props["h"])])

        def picker(artist, event):
            if event.dblclick:
                double_click = True
            else:
                double_click = False

            dist, index = tree.query((event.xdata, event.ydata))
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

        # trigger drawing the figure
        f.canvas.draw()

        self.figure = _Maps_plot(
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

    def _prepare_data(
        self,
        data=None,
        in_crs=None,
        plot_epsg=None,
        radius="estimate",
        radius_crs=None,
        cpos=None,
        parameter=None,
        xcoord=None,
        ycoord=None,
        shape=None,
    ):

        # get specifications

        if data is None:
            data = self.data
        if xcoord is None:
            xcoord = self.data_specs["xcoord"]
        if ycoord is None:
            ycoord = self.data_specs["ycoord"]

        if in_crs is None:
            in_crs = self.data_specs["in_crs"]
        if plot_epsg is None:
            plot_epsg = self.plot_specs["plot_epsg"]

        if radius is None:
            radius = self.plot_specs["radius"]
        if radius_crs is None:
            radius_crs = self.plot_specs["radius_crs"]
        if cpos is None:
            cpos = cpos
        if shape is None:
            shape = self.plot_specs["shape"]

        xorig = data[xcoord].values
        yorig = data[ycoord].values

        z_data = data[parameter].values
        ids = data.index.values

        # get coordinate transformation
        transformer = Transformer.from_crs(
            CRS.from_user_input(in_crs), CRS.from_user_input(plot_epsg), always_xy=True
        )

        if shape == "ellipses":
            # transform center-points
            x0, y0 = transformer.transform(xorig, yorig)

            if radius == "estimate":
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

            props = dict(x0=x0, y0=y0, w=w, h=h, theta=theta, ids=ids, z_data=z_data)
        elif shape == "rectangles":
            # transform center-points
            x0, y0 = transformer.transform(xorig, yorig)

            if radius == "estimate":
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
                # top right
                p0 = transformer.transform(xorig + radiusx, yorig + radiusy)
                # top left
                p1 = transformer.transform(xorig - radiusx, yorig + radiusy)
                # bottom left
                p2 = transformer.transform(xorig - radiusx, yorig - radiusy)
                # bottom right
                p3 = transformer.transform(xorig + radiusx, yorig - radiusy)

            elif radius_crs == "out":
                p0 = xorig + radiusx, yorig + radiusy
                p1 = xorig - radiusx, yorig + radiusy
                p2 = xorig - radiusx, yorig - radiusy
                p3 = xorig + radiusx, yorig - radiusy
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

                # top right
                p0 = radius_t_p.transform(x0r + radiusx, y0r + radiusy)
                # top left
                p1 = radius_t_p.transform(x0r - radiusx, y0r + radiusy)
                # bottom left
                p2 = radius_t_p.transform(x0r - radiusx, y0r - radiusy)
                # bottom right
                p3 = radius_t_p.transform(x0r + radiusx, y0r - radiusy)

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

            # also attach max w & h (used for the kd-tree)
            props = dict(
                verts=np.array(list(zip(*[np.array(i).T for i in (p0, p1, p2, p3)]))),
                x0=x0,
                y0=y0,
                ids=ids,
                z_data=z_data,
                w=(p0[0] - p1[0]).max(),
                h=(p0[1] - p3[1]).max(),
            )

        self._props = props

        return props

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
        props,
        cmap,
        vmin,
        vmax,
        norm,
        color=None,
        shape="ellipses",
    ):
        z_data = props["z_data"]
        ids = props["ids"]

        if shape == "ellipses":
            coll = collections.EllipseCollection(
                2 * props["w"],
                2 * props["h"],
                props["theta"],
                offsets=list(zip(props["x0"], props["y0"])),
                units="x",
                transOffset=ax.transData,
            )

        if shape == "rectangles":
            coll = collections.PolyCollection(
                verts=props["verts"],
                transOffset=ax.transData,
            )
            # add centroid positions (used by the picker in self._spatial_plot)
            coll._Maps_positions = list(zip(props["x0"], props["y0"]))

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
        assert hasattr(self, "figure"), "you must call .plot_map() first!"

        ax = self.figure.ax

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
        overlay_df.to_crs(self.plot_specs["plot_epsg"], inplace=True)

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
        radius="estimate",
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
        radius : str, float, list or tuple
            the radius (if list or tuple the ellipse-half-widths) of the points
            in units of the "in_crs". If "estimate", the mean difference of the
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
        shape : str
            the shapes to plot (either "ellipses" or "rectangles")
        """
        assert hasattr(self, "figure"), "you must call .plot_map() first!"

        if parameter is None:
            parameter = next(i for i in data.keys() if i not in [xcoord, ycoord])

        # ---------------------- prepare the data
        props = self._prepare_data(
            data=data,
            in_crs=in_crs,
            plot_epsg=self.plot_specs["plot_epsg"],
            radius=radius,
            radius_crs=radius_crs,
            cpos=cpos,
            parameter=parameter,
            xcoord=xcoord,
            ycoord=ycoord,
            shape=shape,
        )

        # ------------- plot the data
        coll = self._add_collection(
            ax=self.figure.ax,
            props=props,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            norm=norm,
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

    def add_callback(self, callback, double_click=True, mouse_button=1, **kwargs):
        """
        Attach a callback to the plot that will be executed if a pixel is double-clicked

        A list of pre-defined callbacks (accessible via `m.cb`) or customly defined
        functions can be used.

            >>> m.add_callback(m.cb.annotate)
            >>> m.add_callback("scatter")
            >>> # to remove the callback again, call:
            >>> m.remove_callback("scatter")

        Parameters
        ----------
        double_click : bool
            Indicator if the callback should be executed on double-click (True)
            or on single-click events (False)
        mouse_button : int
            The mouse-button to use for executing the callback:

                - LEFT = 1
                - MIDDLE = 2
                - RIGHT = 3
                - BACK = 8
                - FORWARD = 9

        callback : callable or str
            The callback-function to attach. Use either a function of the `m.cb`
            collection or a custom function with the following call-signature:

                >>> def some_callback(self, **kwargs):
                >>>     print("hello world")
                >>>     print("the position of the clicked pixel", kwargs["pos"])
                >>>     print("the data-index of the clicked pixel", kwargs["ID"])
                >>>     print("data-value of the clicked pixel", kwargs["val"])
                >>>     print("the plot-crs is:", self.plot_specs["plot_epsg"])
                >>>
                >>> m.add_callback(some_callback)

            If a string is provided, it will be used to assign the associated function
            from the `m.cb` collection.
        **kwargs :
            kwargs passed to the callback-function
        """

        assert not all(
            i in kwargs for i in ["pos", "ID", "val", "double_click", "mouse_button"]
        ), 'the names "pos", "ID", "val" cannot be used as keyword-arguments!'

        if isinstance(callback, str):
            assert hasattr(self.cb, callback), (
                f"The function '{callback}' does not exist as a pre-defined callback."
                + " Use one of:\n    - "
                + "\n    - ".join(self.cb.cb_list)
            )
            callback = getattr(self.cb, callback)
        elif callable(callback):
            # re-bind the callback methods to the eomaps.Maps.cb object
            # in case custom functions are used
            if hasattr(callback, "__func__"):
                callback = callback.__func__.__get__(self.cb)
            else:
                callback = callback.__get__(self.cb)

        # add mouse-button assignment as suffix to the name (with __ separator)
        # TODO document this!
        cbname = callback.__name__ + f"__{double_click}_{mouse_button}"

        assert (
            cbname not in self._attached_cbs
        ), f"the callback '{cbname}' is already attached to the plot!"

        # TODO support multiple assignments for callbacks
        # make sure multiple callbacks of the same funciton are only assigned
        # if multiple assignments are properly handled
        multi_cb_functions = ["mark"]

        no_multi_cb = [*self.cb.cb_list]
        for i in multi_cb_functions:
            no_multi_cb.pop(no_multi_cb.index(i))

        if callback.__name__ in no_multi_cb:
            assert callback.__name__ not in [
                i.split("__")[0] for i in self._attached_cbs
            ], (
                "Multiple assignments of the callback"
                + f" '{callback.__name__}' are not (yet) supported..."
            )

        # ------------- add a callback
        def onpick(event):
            if (event.double_click == double_click) and (
                event.mouse_button == mouse_button
            ):
                ind = event.ind
                if ind is not None:
                    if isinstance(event.artist, collections.EllipseCollection):
                        clickdict = dict(
                            pos=self.figure.coll.get_offsets()[ind],
                            ID=self.figure.coll.get_urls()[ind],
                            val=self.figure.coll.get_array()[ind],
                        )

                        callback(**clickdict, **kwargs)
                    elif isinstance(event.artist, collections.PolyCollection):
                        clickdict = dict(
                            pos=self.figure.coll._Maps_positions[ind],
                            ID=self.figure.coll.get_urls()[ind],
                            val=self.figure.coll.get_array()[ind],
                        )

                        callback(**clickdict, **kwargs)
                else:
                    if "annotate" in [i.split("__")[0] for i in self._attached_cbs]:
                        self._cb_hide_annotate()

        cid = self.figure.f.canvas.mpl_connect("pick_event", onpick)
        self._attached_cbs[cbname] = cid

        return cid

    def remove_callback(self, callback):
        """
        remove an attached callback from the figure

        Parameters
        ----------
        callback : int, str or callable
            if int: the identification-number of the callback to remove
                    (the number is returned by `cid = m.add_callback()`)
            if str: the name of the callback to remove
                    (format: `<function_name>__<double_click>_<mouse_button>`)
            if callable: the `__name__` property of the callback is used to
                         remove ANY callback that references the corresponding
                         function

            either the callback-function that should be removed from the figure
            (or the name of the function)
        """

        if isinstance(callback, int):
            self.figure.f.canvas.mpl_disconnect(callback)
            name = dict(zip(self._attached_cbs.values(), self._attached_cbs.keys()))[
                callback
            ]
            del self._attached_cbs[name]

            # call cleanup methods on removal
            fname = name.split("__")[0]
            if hasattr(self.cb, f"_{fname}_cleanup"):
                getattr(self.cb, f"_{fname}_cleanup")(self)

            print(f"Removed the callback: '{name}'.")

        else:

            if isinstance(callback, str):
                names = [callback]
                if names[0] not in self._attached_cbs:
                    warnings.warn(
                        f"The callback '{name}' is not attached and can not"
                        + " be removed. Attached callbacks are:\n    - "
                        + "    - \n".join(list(self._attached_cbs))
                    )
                    return

            elif callable(callback):
                # identify all callbacks that relate to the provided function
                names = [
                    key
                    for key in self._attached_cbs
                    if key.split("__")[0] == callback.__name__
                ]
                if len(names) == 0:
                    warnings.warn(
                        f"The callback '{callback.__name__}' is not attached"
                        + "and can not be removed. Attached callbacks are:"
                        + "\n    - "
                        + "    - \n".join(list(self._attached_cbs))
                    )

            for name in names:
                self.figure.f.canvas.mpl_disconnect(self._attached_cbs[name])
                del self._attached_cbs[name]

                # call cleanup methods on removal
                fname = name.split("__")[0]
                if hasattr(self.cb, f"_{fname}_cleanup"):
                    getattr(self.cb, f"_{fname}_cleanup")(self)

                print(f"Removed the callback: '{name}'.")

    @lru_cache()
    def _get_crs(self, crs):
        return CRS.from_user_input(crs)

    def _cb_hide_annotate(self):
        # a function to hide the annotation of an empty area is clicked
        if hasattr(self.cb, "annotation"):
            self.cb.annotation.set_visible(False)
            self._blit(self.cb.annotation)

    # implement blitting (see https://stackoverflow.com/a/29284318/9703451)
    def _safe_draw(self):
        """Temporarily disconnect the draw_event callback to avoid recursion"""
        canvas = self.figure.f.canvas
        if hasattr(self, "draw_cid"):
            canvas.mpl_disconnect(self.draw_cid)

            canvas.draw()
            self.draw_cid = canvas.mpl_connect("draw_event", self._grab_background)
        else:
            canvas.draw()

    def _grab_background(self, event=None, redraw=True):
        """
        When the figure is resized, draw everything, and update the background.
        """
        # hide annotations from the background
        annotation_visible = False
        if hasattr(self.cb, "annotation"):
            if self.cb.annotation.get_visible():
                annotation_visible = True
                self.cb.annotation.set_visible(False)

        if redraw:
            self._safe_draw()

        # With most backends (e.g. TkAgg), we could grab (and refresh, in
        # self.blit) self.ax.bbox instead of self.fig.bbox, but Qt4Agg, and
        # some others, requires us to update the _full_ canvas, instead.
        self.background = self.figure.f.canvas.copy_from_bbox(self.figure.f.bbox)

        # re-draw annotations
        if annotation_visible:
            self.cb.annotation.set_visible(True)
            self._blit(self.cb.annotation)
        else:
            self._blit()

    def _blit(self, artist=None):
        """
        Efficiently update the figure, without needing to redraw the
        "background" artists.

        Parameters
        ----------
        artist : the matplotlib artist to draw on top of the background
        """
        self.figure.f.canvas.restore_region(self.background)
        if artist is not None:
            self.figure.ax.draw_artist(artist)
        self.figure.f.canvas.blit(self.figure.f.bbox)

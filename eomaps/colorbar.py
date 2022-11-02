from matplotlib.gridspec import GridSpecFromSubplotSpec, SubplotSpec

import matplotlib.transforms as mtransforms
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

import numpy as np
import copy

from functools import partial

from .helpers import pairwise


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


# class copied from matplotlib.axes
class _TransformedBoundsLocator:
    """
    Axes locator for `.Axes.inset_axes` and similarly positioned Axes.
    The locator is a callable object used in `.Axes.set_aspect` to compute the
    Axes location depending on the renderer.
    """

    def __init__(self, bounds, transform):
        """
        *bounds* (a ``[l, b, w, h]`` rectangle) and *transform* together
        specify the position of the inset Axes.
        """
        self._bounds = bounds
        self._transform = transform

    def __call__(self, ax, renderer):
        # Subtracting transSubfigure will typically rely on inverted(),
        # freezing the transform; thus, this needs to be delayed until draw
        # time as transSubfigure may otherwise change after this is evaluated.
        return mtransforms.TransformedBbox(
            mtransforms.Bbox.from_bounds(*self._bounds),
            self._transform - ax.figure.transSubfigure,
        )


class ColorBar:
    def __init__(
        self,
        m,
        pos=0.4,
        inherit_position=None,
        margin=None,
        hist_size=0.8,
        hist_bins=256,
        extend_frac=0.025,
        orientation="horizontal",
        dynamic_shade_indicator=False,
        show_outline=False,
        tick_precision=2,
        tick_formatter=None,
        log=False,
        out_of_range_vals="clip",
        hist_kwargs=None,
        **kwargs,
    ):
        """
        Add a colorbar to the map.

        The colorbar always represents the data of the associated Maps-object
        that was assigned in the last call to `m.plot_map()`.

        By default, the colorbar will only be visible on the layer of the associated
        Maps-object.

        After the colorbar has been created, it can be accessed via:

            >>> cb = m.colorbar

        Parameters
        ----------
        pos : float or 4-tuple, optional

            - float: fraction of the axis size that is used to create the colorbar.
              The axes of the Maps-object will be shrinked accordingly to make space
              for the colorbar.
            - 4-tuple (x0, y0, width, height):
              Absolute position at which the colorbar should be placed in units.
              In this case, existing axes are NOT automatically re-positioned!

            Note: By default, multiple colorbars on different layers share their
            position! To force placement of a colorbar, use "inherit_position=False".

            The default is 0.4.
        inherit_position : bool or None optional
            Indicator if the colorbar should share its position with other colorbars
            that represent datasets on the same plot-axis.

            - If True, and there is already another colorbar for the given plot-axis,
              the value of "pos" will be ignored and the new colorbar will share its
              position with the parent-colorbar. (e.g. all colorbars for a given axis will
              overlap and moving a colorbar in one layer will move all other relevant
              colorbars accordingly).
            - If None: If the colorbar is added on a different layer than the parent
              colorbar, use "inherit_position=True", else use "inherit_position=False".

            The default is None
        hist_size : float or None
            The fraction of the colorbar occupied by the histogram.

            - None: no histogram will be drawn
            - 0:
            - 0.9: 90% histogram, 10% colorbar
            - 1: only histogram
        hist_bins : int, list, tuple, array or "bins", optional
            - If int: The number of histogram-bins to use for the colorbar.
            - If list, tuple or numpy-array: the bins to use
            - If "bins": use the bins obtained from the classification
              (ONLY possible if a classification scheme is used!)
            The default is 256.
        extend_frac : float, optional
            The fraction of the colorbar-size to use for extension-arrows.
            (Extension-arrows are added if out-of-range values are found!)
            The default is 0.025.
        orientation : str, optional
            The orientation of the colorbar ("horizontal" or "vertical").
            The default is "horizontal".
        dynamic_shade_indicator : bool, optional
            ONLY relevant if data-shading is used! ("shade_raster" or "shade_points")
            - False: The colorbar represents the actual (full) dataset
            - True: The colorbar is dynamically updated and represents the density of
              the shaded pixel values within the current field of view.
            The default is False.
        show_outline : bool or dict
            Indicator if an outline should be added to the histogram.
            (e.g. a line encompassing the histogram)
            If a dict is provided, it is passed to `plt.step()` to style the line.
            (e.g. with ordinary matplotlib parameters such as color, lw, ls etc.)
            If True, the following properties are used:
            - {"color": "k", "lw": 1}
            The default is False.
        tick_precision : int or None
            The precision of the tick-labels in the colorbar.
            The default is 3.
        tick_formatter : callable
            A function that will be used to format the ticks of the colorbar.
            The function will be used with matpltlibs `set_major_formatter`...
            For details, see:
            https://matplotlib.org/stable/api/_as_gen/matplotlib.axis.Axis.set_major_formatter.html

            Call-signagure:

            >>> def tick_formatter(x, pos):
            >>>     # x ... the tick-value
            >>>     # pos ... the tick-position
            >>>     return f"{x} m"

            The default is None.
        log : bool, optional
            Indicator if the y-axis of the plot should be logarithmic or not.
            The default is False
        out_of_range_vals : str or None


            - if "mask": out-of range values will be masked.
              (e.g. values outside the colorbar limits are not represented in the
               histogram and NO extend-arrows are added)
            - if "clip": out-of-range values will be clipped.
              (e.g. values outside the colorbar limits will be represented in the
               min/max bins of the histogram)

            The default is "clip"
        hist_kwargs : dict
            A dictionary with keyword-arguments passed to the creation of the histogram
            (e.g. passed to `plt.hist()` )
        kwargs :
            All additional kwargs are passed to the creation of the colorbar
            (e.g. `plt.colorbar()`)

        Examples
        --------

        >>> x = y = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        >>> data = [1, 2, 6, 6, 6, 8, 7, 3, 9, 10]
        >>> m = Maps()
        >>> m.set_data(data, x, y)
        >>> m.plot_map()
        >>> m.add_colorbar(label="some data")

        >>> x = y = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        >>> data = [1, 2, 6, 6, 6, 8, 7, 3, 9, 10]
        >>> m = Maps()
        >>> m.set_data(data, x, y)
        >>> m.set_classify.Quantiles(k=6)
        >>> m.plot_map()
        >>> m.add_colorbar(hist_bins="bins", label="some data")

        """
        self.m = m
        self.pos = pos
        self.margin = margin

        self._parent_cb = self._identify_parent_cb()

        if inherit_position is None:
            if not self.m.colorbar:
                inherit_position = True
            else:
                inherit_position = False

        self._inherit_position = inherit_position

        self.hist_size = hist_size
        self.hist_bins = hist_bins

        if hist_kwargs is None:
            self.hist_kwargs = dict()
        else:
            self.hist_kwargs = copy.deepcopy(hist_kwargs)

        self._depreciate_kwargs(kwargs)

        self.extend_frac = extend_frac
        self.orientation = orientation
        self.dynamic_shade_indicator = dynamic_shade_indicator
        self.show_outline = show_outline
        self.tick_precision = tick_precision
        self.tick_formatter = tick_formatter
        self.log = log
        self.out_of_range_vals = out_of_range_vals

        self.kwargs = copy.deepcopy(kwargs)

        self.coll = self.m.figure.coll
        self.vmin = self.coll.norm.vmin
        self.vmax = self.coll.norm.vmax

        self.classified = self.m.classify_specs._classified

        self._redraw = False
        self.ax = None
        self.ax_cb = None
        self.ax_cb_plot = None

        self._cid_redraw = None

        self._refetch_bg = False

        self._set_data()
        self._setup_axes()

    def set_visible(self, vis):
        """
        Set the visibility of the colorbar

        Parameters
        ----------
        vis : bool
            - True: colorbar visible
            - False: colorbar not visible
        """
        for ax in self._axes:
            ax.set_visible(vis)

    def _depreciate_kwargs(self, kwargs):
        if "histbins" in kwargs:
            self.hist_bins = kwargs.pop("histbins")
            print(
                "EOmaps: Colorbar argument 'histbins' is depreciated in EOmaps v5.0."
                "Please use 'hist_bins' instead!"
            )
        if "density" in kwargs:
            self.hist_kwargs["density"] = kwargs.pop("density")
            print(
                "EOmaps: Colorbar argument 'density' is depreciated in EOmaps v5.0."
                "Please use `hist_kwargs=dict(density=...)` instead!"
            )
        if "histogram_size" in kwargs:
            self.hist_size = kwargs.pop("histogram_size")
            print(
                "EOmaps: Colorbar argument 'histogram_size' is depreciated in EOmaps v5.0."
                "Please use `hist_size` instead!"
            )
        if "add_extend_arrows" in kwargs:
            kwargs.pop("add_extend_arrows")
            print(
                "EOmaps: Colorbar argument 'add_extend_arrows' is depreciated in EOmaps v5.0."
                "Extend-arrows are added automatically if data out-of-range is found."
            )

        for key in ["top", "bottom", "left", "right"]:

            margin = kwargs.pop("margin", None)
            if margin is None:
                margin = dict()

            if key in kwargs:
                margin[key] = kwargs.pop(key)
                print(
                    f"EOmaps: Colorbar argument '{key}' is depreciated in EOmaps v5.0."
                    "Please use 'margin=dict({key}=...)' instead!"
                )

            if len(margin) > 0:
                self.margin = margin

    def _default_cb_tick_formatter(self, x, pos, precision=None):
        """
        A formatter to format the tick-labels of the colorbar for encoded datasets.
        (used in xaxis.set_major_formatter() )
        """
        # if precision=None the shortest representation of the number is used
        return np.format_float_positional(self.m._decode_values(x), precision)

    def set_hist_size(self, size=None):
        """
        Set the size of the histogram (relative to the total colorbar size)

        Parameters
        ----------
        size : float, optional
            The fraction of the colorbar occupied by the histogram.

            - 0 = no histogram
            - 0.5 = 50% colorbar, 50% histogram
            - 1 = no colorbar, only histogram).

            The default is None.
        """
        if size is not None:
            self.hist_size = size

        # # evaluate axis padding due to extension-arrows
        # if self.extend == "both":
        #     d = self.extend_frac / (1 + 2 * self.extend_frac)
        #     ex_min, ex_max = d, d
        # elif self.extend == "min":
        #     d = self.extend_frac / (1 + self.extend_frac)
        #     ex_min, ex_max = d, 0.0
        # elif self.extend == "max":
        #     d = self.extend_frac / (1 + self.extend_frac)
        #     ex_min, ex_max = 0.0, d
        # else:
        #     ex_min, ex_max = 0.0, 0.0

        # no need to explicitly specify padding of extension arrows if axis-size
        # is determined AFTER the colorbar is plotted!
        ex_min, ex_max = 0.0, 0.0

        if self.orientation == "horizontal":
            s = 1 - self.hist_size
            cbpos = mtransforms.Bbox(((0, 0), (1, s)))
            histpos = mtransforms.Bbox(((ex_min, s), (1 - ex_max, 1)))
        else:
            s = 1 - self.hist_size
            cbpos = mtransforms.Bbox(((1 - s, 0), (1, 1)))
            histpos = mtransforms.Bbox(((0, ex_min), (1 - s, 1 - ex_max)))

        # colorbar axes
        # NOTE: labels are used to hide those axes from the layout-manager!
        if histpos.width > 1e-4 and histpos.height > 1e-4:
            self.ax_cb_plot.set_visible(True)
        else:
            self.ax_cb_plot.set_visible(False)

        self.ax_cb_plot.set_axes_locator(
            _TransformedBoundsLocator(histpos.bounds, self.ax.transAxes)
        )

        if cbpos.width > 1e-4 and cbpos.height > 1e-4:
            self.ax_cb.set_visible(True)
            [i.set_visible(True) for i in self.ax_cb.patches]
            [i.set_visible(True) for i in self.ax_cb.collections]
        else:
            [i.set_visible(False) for i in self.ax_cb.patches]
            [i.set_visible(False) for i in self.ax_cb.collections]

        self.ax_cb.set_axes_locator(
            _TransformedBoundsLocator(cbpos.bounds, self.ax.transAxes)
        )

        self.m.BM._refetch_layer(self.m.layer)
        self.m.BM.update(artists=self._axes)

    def _identify_parent_cb(self):
        parent_cb = None
        # check if there is already an existing colorbar for a Maps-object that shares
        # the same plot-axis.
        # If yes, use the position of this colorbar to creat a new one

        if self.m.colorbar is not None:
            parent_cb = None  # self.m.colorbar
        else:
            # check if self is actually just another layer of an existing Maps object
            # that already has a colorbar assigned
            for m in [self.m.parent, *self.m.parent._children]:
                if m is not self.m and m.ax is self.m.ax:
                    if m.colorbar is not None:
                        parent_cb = m.colorbar
                        break

        return parent_cb

    def _get_parent_cb(self):
        if self._parent_cb is None:
            return self
        else:
            parent = self
            while parent._parent_cb is not None:
                parent = parent._parent_cb

            return parent

    def _setup_axes(self):
        horizontal = self.orientation == "horizontal"
        add_hist = self.hist_size > 0
        add_margins = False

        # check if one of the parent colorbars has a colorbar, and if so,
        # use it to set the position of the colorbar.
        if self._inherit_position:
            if self._parent_cb is not None:

                try:
                    self.ax = self.m.figure.f.add_subplot(
                        self._parent_cb.ax.get_subplotspec(),
                        label="cb",
                        zorder=9999,
                    )
                except AttributeError:
                    self.ax = self.m.figure.f.add_axes(
                        self._parent_cb.ax.get_position(),
                        label="cb",
                        zorder=9999,
                    )

                # inherit axis-position from the parent axis position
                # (e.g. it can no longer be freely moved... its position is determined
                # by the position of the parent-colorbar axis)
                self.ax.set_axes_locator(
                    _TransformedBoundsLocator(
                        (0, 0, 1, 1), self._parent_cb.ax.transAxes
                    )
                )

            else:
                self._inherit_position = False

        if not self._inherit_position:
            if isinstance(self.pos, float):
                add_margins = True
                if horizontal:
                    gs = GridSpecFromSubplotSpec(
                        2,
                        1,
                        self.m.ax.get_subplotspec(),
                        height_ratios=(1, self.pos),
                    )

                    self.m.figure.ax.set_subplotspec(gs[0, 0])
                    self.ax = self.m.figure.f.add_subplot(
                        gs[1, 0],
                        label="cb",
                        zorder=9999,
                    )
                else:
                    gs = GridSpecFromSubplotSpec(
                        1,
                        2,
                        self.m.ax.get_subplotspec(),
                        width_ratios=(1, self.pos),
                    )

                    self.m.figure.ax.set_subplotspec(gs[0, 0])
                    self.ax = self.m.figure.f.add_subplot(
                        gs[0, 1],
                        label="cb",
                        zorder=9999,
                    )
            elif isinstance(self.pos, SubplotSpec):
                add_margins = True
                self.ax = self.m.figure.f.add_subplot(
                    self.pos,
                    label="cb",
                    zorder=9999,
                )
            elif isinstance(self.pos, (list, tuple)):
                x0, y0, w, h = self.pos
                x1 = x0 + w
                y1 = y0 + h
                bbox = mtransforms.Bbox(((x0, y0), (x1, y1)))

                # the parent axes holding the 2 child-axes
                self.ax = plt.Axes(self.m.figure.f, bbox, label="cb", zorder=9999)
                self.m.figure.f.add_axes(self.ax)

        # make all spines, labels etc. invisible for the base-axis
        self.ax.set_axis_off()

        # NOTE: labels are used to hide those axes from the layout-manager!
        # colorbar axes
        self.ax_cb = self.ax.figure.add_axes(
            self.ax.get_position(True),
            label="EOmaps_cb",
            zorder=9998,
        )
        # histogram axes
        self.ax_cb_plot = self.ax.figure.add_axes(
            self.ax.get_position(True),
            label="EOmaps_cb_hist",
            zorder=9998,
        )

        # join colorbar and histogram axes
        if horizontal:
            self.ax_cb_plot.get_shared_x_axes().join(self.ax_cb_plot, self.ax_cb)
        else:
            self.ax_cb_plot.get_shared_y_axes().join(self.ax_cb_plot, self.ax_cb)

        # keep the background of the plot-axis but remove the outer frame
        self.ax_cb_plot.spines["top"].set_visible(False)
        self.ax_cb_plot.spines["right"].set_visible(False)
        self.ax_cb_plot.spines["bottom"].set_visible(False)
        self.ax_cb_plot.spines["left"].set_visible(False)

        # set axis scale
        if horizontal:
            if self.log is True:
                self.ax_cb_plot.set_yscale("log")
            else:
                self.ax_cb_plot.set_yscale("linear")
        else:
            if self.log is True:
                self.ax_cb_plot.set_xscale("log")
            else:
                self.ax_cb_plot.set_xscale("linear")

        # hide histogram axis if no histogram should be drawn
        if not add_hist:
            self.ax_cb_plot.set_visible(False)

        # add margins
        if add_margins or self.margin is not None:
            if self.margin is None:
                if self.orientation == "horizontal":
                    self.margin = dict(left=0.1, right=0.1, bottom=0.3, top=0.0)
                else:
                    self.margin = dict(left=0.0, right=0.3, bottom=0.1, top=0.1)

            axpos = self.ax.get_position()
            w, h = axpos.width, axpos.height
            l, r = (self.margin.get(k, 0) * w for k in ["left", "right"])
            b, t = (self.margin.get(k, 0) * h for k in ["bottom", "top"])

            self.ax.set_position(
                [
                    axpos.x0 + l,
                    axpos.y0 + b,
                    axpos.width - l - r,
                    axpos.height - b - t,
                ]
            )

        # add all axes as background-artists
        for a in self._axes:
            a.set_navigate(False)
            if a is not None:
                self.m.BM.add_bg_artist(a, self.m.layer)

        # we need to re-draw since the background axis size has changed!
        self._refetch_bg = True

    @property
    def _axes(self):
        return (self.ax, self.ax_cb, self.ax_cb_plot)

    def _set_extend(self, z_data):
        extend = "neither"
        if (z_data > self.vmax).any():
            extend = "max"
        if (z_data < self.vmin).any():
            if extend == "max":
                extend = "both"
            else:
                extend = "min"

        self.extend = extend

    def _set_data(self):
        renorm = False

        dynamic_shade = False
        if self.dynamic_shade_indicator:
            if _register_datashader() and isinstance(self.coll, mpl_ext.ScalarDSArtist):
                dynamic_shade = True
            else:
                print(
                    "EOmaps: using 'dynamic_shade_indicator=True' is only possible "
                    "with 'shade' shapes (e.g. 'shade_raster' or 'shade_points'.\n"
                    "... creating a normal colorbar instead."
                )
                self.dynamic_shade_indicator = False

        if dynamic_shade:
            aggname = self.m.shape.aggregator.__class__.__name__
            if aggname in ["first", "last", "max", "min", "mean", "mode"]:
                pass
            else:
                renorm = True
                # TODO check this without requiring import of datashader!
                # print(
                #     "EOmaps: Only dynamic colorbars are possible when using"
                #     + f" '{aggname}' as datashader-aggregation reduction method "
                #     + "...creating a 'dynamic_shade_indicator' colorbar instead."
                # )
                # self.dynamic_shade_indicator = True

            try:
                z_data = self.coll.get_ds_data().values
            except:
                self.m.redraw()
                z_data = self.coll.get_ds_data().values

            if "count" in aggname:
                # make sure we don't count empty pixels
                z_data = z_data[~(z_data == 0)]

            # datashader sets None to 0 by default!
            # z_data = z_data[z_data > 0]

            bins = self.m.classify_specs._bins
            cmap = self.m.classify_specs._cbcmap

            if renorm:
                z_data = z_data[~np.isnan(z_data)]
                norm = self.coll.norm
                # make sure the norm clips with respect to vmin/vmax
                # (only clip if either vmin or vmax is not None)
                # if vmin or vmax:
                #     z_data = z_data.clip(vmin, vmax)
                cmap = self.coll.get_cmap()
            else:
                norm = self.m.classify_specs._norm

            # TODO remove cid on figure close
            if self._cid_redraw is None:
                self._cid_redraw = self.coll.add_callback(self._redraw_colorbar)
                # TODO colorbar not properly updated on layer change after zoom?
                self.m.BM.on_layer(
                    self._redraw_colorbar,
                    layer=self.m.layer,
                    persistent=True,
                    m=self.m,
                )
        else:

            z_data = self.m._props["z_data"]
            bins = self.m.classify_specs._bins
            cmap = self.m.classify_specs._cbcmap
            norm = self.m.classify_specs._norm

        if isinstance(z_data, np.ma.masked_array):
            z_data = z_data.compressed()
        else:
            z_data = z_data.ravel()

        # make sure we only consider valid values in the histogram
        z_data = z_data[np.isfinite(z_data)]

        self._set_extend(z_data)

        if self.out_of_range_vals == "mask":
            z_data = z_data[(z_data >= self.vmin) & (z_data <= self.vmax)]

        # make sure the norm clips with respect to vmin/vmax
        # (only clip if either vmin or vmax is not None)
        if self.out_of_range_vals == "clip":
            if self.vmin or self.vmax:
                z_data = z_data.clip(self.vmin, self.vmax)

        self.z_data = z_data
        self.bins = bins
        self.cmap = cmap
        # TODO check if copy is really necessary
        # (especially for dynamic datashader colorbars!)
        self.norm = copy.deepcopy(norm)
        # make sure boundaries are clipped with respect to vmin and vmax
        # to avoid issues with vmin/vmax in-between colorbar-boundaries

        if hasattr(self.norm, "boundaries"):
            self.norm.boundaries = np.clip(self.norm.boundaries, self.vmin, self.vmax)

        if self.dynamic_shade_indicator:
            if not hasattr(self, "_ds_data"):
                self._ds_data = self.z_data
                self._redraw = True
                return
            if self._ds_data.shape == self.z_data.shape:
                if np.allclose(self._ds_data, self.z_data, equal_nan=True):
                    self._redraw = False
                    return
            self._ds_data = self.z_data
            self._redraw = True

    def _plot_colorbar(self):

        # plot the colorbar
        horizontal = self.orientation == "horizontal"
        n_cmap = plt.cm.ScalarMappable(cmap=self.cmap, norm=self.norm)

        cb = plt.colorbar(
            n_cmap,
            cax=self.ax_cb,
            extend=self.extend,
            extendfrac=self.extend_frac,
            spacing="proportional",
            orientation=self.orientation,
            **self.kwargs,
        )

        cb.outline.set_visible(False)

        # ensure that ticklabels are correct if a classification is used
        if self.classified:
            cb.set_ticks([i for i in self.bins if i >= self.vmin and i <= self.vmax])

            if horizontal:
                labelsetfunc = "set_xticklabels"
            else:
                labelsetfunc = "set_yticklabels"

            getattr(cb.ax, labelsetfunc)(
                [
                    np.format_float_positional(
                        i, precision=self.tick_precision, trim="-"
                    )
                    for i in self.bins
                    if i >= self.vmin and i <= self.vmax
                ]
            )
        else:
            cb.set_ticks(cb.get_ticks())

        if self.tick_formatter is None:
            tick_formatter = partial(
                self._default_cb_tick_formatter, precision=self.tick_precision
            )
        else:
            tick_formatter = self.tick_formatter

        if horizontal:
            cb.ax.yaxis.set_major_formatter(tick_formatter)
        else:
            cb.ax.xaxis.set_major_formatter(tick_formatter)

        # format position of scientific exponent for colorbar ticks
        if horizontal:
            ot = self.ax_cb.yaxis.get_offset_text()
            ot.set_horizontalalignment("center")
            ot.set_position((1, 0))

        # make sure axis limits are correct
        if horizontal:
            limsetfunc = self.ax_cb.set_xlim
        else:
            limsetfunc = self.ax_cb.set_ylim

        if self.vmin != self.vmax:
            limsetfunc(self.vmin, self.vmax)
        else:
            print(
                "EOMaps-Warning: Attempting to set identical upper and "
                + "lower limits for the colorbar... limits will be ignored!"
            )

        # set the axis_locator to set relative axis positions
        # TODO check why colorbar axis size changes after plot!
        # (e.g. this needs to be called AFTER plotting the colorbar to make sure
        # the extension-arrows are properly aligned)
        self.set_hist_size()

    def _plot_histogram(self):
        horizontal = self.orientation == "horizontal"
        n_cmap = plt.cm.ScalarMappable(cmap=self.cmap, norm=self.norm)

        if self.hist_size <= 0:
            return

        # plot the histogram
        h = self.ax_cb_plot.hist(
            self.z_data,
            orientation="vertical" if horizontal else "horizontal",
            bins=self.bins
            if (self.classified and self.hist_bins == "bins")
            else self.hist_bins,
            color="k",
            align="mid",
            range=(self.vmin, self.vmax) if (self.vmin and self.vmax) else None,
            **self.hist_kwargs,
        )

        if self.show_outline:
            if self.show_outline is True:
                outline_props = dict(color="k", lw=1)
            else:
                outline_props = self.show_outline

            if horizontal:
                self.ax_cb_plot.step(h[1], [h[0][0], *h[0]], **outline_props)
            else:
                self.ax_cb_plot.step([h[0][0], *h[0]], h[1], **outline_props)

        if self.bins is None:
            # identify position of color-splits in the colorbar
            if isinstance(n_cmap.cmap, LinearSegmentedColormap):
                # for LinearSegmentedcolormap N is the number of quantizations!
                splitpos = np.linspace(self.vmin, self.vmax, n_cmap.cmap.N)
            else:
                # for ListedColormap N is the number of colors
                splitpos = np.linspace(self.vmin, self.vmax, n_cmap.cmap.N + 1)
        else:
            splitpos = self.bins

        # color the histogram patches
        for patch in list(self.ax_cb_plot.patches):
            # the list is important!! since otherwise we change ax.patches
            # as we iterate over it... which is not a good idea...
            if horizontal:
                minval = np.atleast_1d(patch.get_x())[0]
                width = patch.get_width()
                height = patch.get_height()
                maxval = minval + width
            else:
                minval = np.atleast_1d(patch.get_y())[0]
                width = patch.get_width()
                height = patch.get_height()
                maxval = minval + height
            # ----------- take care of histogram-bins that have split colors
            # identify bins that extend beyond a color-change
            splitbins = [
                minval,
                *splitpos[(splitpos > minval) & (maxval > splitpos)],
                maxval,
            ]

            if len(splitbins) > 2:
                patch.remove()
                # add in-between patches
                for b0, b1 in pairwise(splitbins):
                    if horizontal:
                        pi = mpl.patches.Rectangle(
                            (b0, 0),
                            (b1 - b0),
                            height,
                            facecolor=self.cmap(self.norm((b0 + b1) / 2)),
                        )
                    else:
                        pi = mpl.patches.Rectangle(
                            (0, b0),
                            width,
                            (b1 - b0),
                            facecolor=self.cmap(self.norm((b0 + b1) / 2)),
                        )

                    self.ax_cb_plot.add_patch(pi)
            else:
                patch.set_facecolor(self.cmap(self.norm((minval + maxval) / 2)))

        # setup appearance of histogram
        if horizontal:
            self.ax_cb_plot.tick_params(
                left=False,
                labelleft=True,
                bottom=False,
                top=False,
                labelbottom=False,
                labeltop=False,
            )
            self.ax_cb_plot.grid(axis="y", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            self.ax_cb_plot.plot(
                [0, 1],
                [0, 0],
                "k--",
                alpha=0.5,
                transform=self.ax_cb_plot.transAxes,
            )
            # make sure lower y-limit is 0
            if self.log is False:
                # self.ax_cb_plot.yaxis.set_major_locator(plt.MaxNLocator(5))
                self.ax_cb_plot.set_ylim(0)
        else:
            self.ax_cb_plot.invert_xaxis()

            self.ax_cb_plot.tick_params(
                left=False,
                labelleft=False,
                bottom=False,
                top=False,
                labelbottom=True,
                labeltop=False,
                rotation=90,
            )
            self.ax_cb_plot.grid(axis="x", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            self.ax_cb_plot.plot(
                [1, 1],
                [0, 1],
                "k--",
                alpha=0.5,
                transform=self.ax_cb_plot.transAxes,
            )
            # make sure lower x-limit is 0
            if self.log is False:
                # self.ax_cb_plot.xaxis.set_major_locator(plt.MaxNLocator(5))
                self.ax_cb_plot.set_xlim(None, 0)

        if self._refetch_bg:
            self.m.BM._refetch_layer(self.m.layer)

    def _redraw_colorbar(self, *args, **kwargs):
        self._set_data()
        if not self._redraw:
            return
        self.ax_cb_plot.clear()
        self._plot_histogram()

    def remove(self):
        """
        Remove the colorbar from the map.
        """
        for ax in (self.ax, self.ax_cb, self.ax_cb_plot):
            ax.clear()
            ax.remove()
            if self.dynamic_shade_indicator:
                self.m.BM.remove_artist(ax)
            else:
                self.m.BM.remove_bg_artist(ax)
        if self in self.m._colorbars:
            self.m._colorbars.pop(self.m._colorbars.index(self))

    def set_position(self, pos):
        """
        Set the position of the colorbar
        (and all colorbars that share the same location)

        Parameters
        ----------
        pos : [left, bottom, width, height] or ~matplotlib.transforms.Bbox
            The new position of the in .Figure coordinates.
        """
        self._get_parent_cb().ax.set_position(pos)

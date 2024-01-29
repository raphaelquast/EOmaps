from itertools import cycle
from functools import partial
from textwrap import dedent

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpecFromSubplotSpec, SubplotSpec
import matplotlib.transforms as mtransforms
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

import numpy as np

from eomaps.helpers import _TransformedBoundsLocator, pairwise


def get_named_bins_formatter(bins, names, show_values=False):
    """
    A formatter to format the tick-labels of the colorbar with respect to
    labels for a given set of bins.

    Parameters
    ----------
    bins : list of float
        The (upper) bin-boundaries to use.
    names : list of string
        The names for ticks that are inside the bins.
        Must be 1 longer than the provided bin-boundaries!

    Examples
    --------

    bins = [10, 20, 30, 40, 50]
    names =["below 10", "10-20", "20-30", "30-40", "40-50", "above 50"]


    """

    def formatter(x, pos):
        if len(names) != len(bins) + 1:
            raise AssertionError(
                f"EOmaps: the provided number of names ({len(names)}) "
                f"does not match! Expected {len(bins) + 1} names."
            )

        b = np.digitize(x, bins, right=True)

        if show_values:
            return f"{x}\n{names[b]}"
        else:
            return names[b]

    return formatter


class ColorBarBase:
    def __init__(
        self,
        orientation="horizontal",
        extend_frac=0.025,
        hist_kwargs=None,
        tick_precision=2,
        margin=None,
    ):

        self._hist_size = 0.9
        if hist_kwargs is not None:
            self._hist_kwargs = hist_kwargs
        else:
            self._hist_kwargs = {}

        self._extend_frac = extend_frac

        self.orientation = orientation

        self._tick_precision = tick_precision
        self._margin = margin

        self._vmin = None
        self._vmax = None
        self._norm = None
        self._cmap = None
        self._data = None

    @property
    def _scm(self):
        return plt.cm.ScalarMappable(cmap=self._cmap, norm=self._norm)

    @property
    def _hist_orientation(self):
        return "vertical" if self.orientation == "horizontal" else "horizontal"

    def _get_data(self):
        # TODO
        return self._data

    def _set_axes_locators(self, cb_bounds=None, hist_bounds=None):
        if cb_bounds is not None:
            self.ax_cb.set_axes_locator(
                _TransformedBoundsLocator(cb_bounds, self._ax.transAxes)
            )
        if hist_bounds is not None:
            self.ax_cb_plot.set_axes_locator(
                _TransformedBoundsLocator(hist_bounds, self._ax.transAxes)
            )

    def _setup_axes(self, pos, parent_ax=None, f=None, zorder=9999):
        if f is None and parent_ax is not None:
            f = parent_ax.figure

        self._parent_cb = self._identify_parent_cb()
        if self._parent_cb:
            # inherit axis-position from the parent axis position
            # (e.g. it can no longer be freely moved... its position is determined
            # by the position of the parent-colorbar axis)
            self._ax = self._parent_cb._ax
        else:
            if isinstance(pos, (int, float)):
                if self.orientation == "horizontal":
                    gs = GridSpecFromSubplotSpec(
                        2,
                        1,
                        parent_ax.get_subplotspec(),
                        height_ratios=(1, pos),
                    )
                    parent_ax.set_subplotspec(gs[0, :])
                    self._ax = f.add_subplot(
                        gs[1, :],
                        label="cb",
                        zorder=zorder,
                    )
                else:
                    gs = GridSpecFromSubplotSpec(
                        1,
                        2,
                        parent_ax.get_subplotspec(),
                        width_ratios=(1, pos),
                    )

                    parent_ax.set_subplotspec(gs[:, 0])
                    self._ax = f.add_subplot(
                        gs[:, 1],
                        label="cb",
                        zorder=zorder,
                    )
            elif isinstance(pos, SubplotSpec):
                self._ax = f.add_subplot(
                    pos,
                    label="cb",
                    zorder=zorder,
                )
            elif isinstance(pos, (list, tuple)):
                x0, y0, w, h = pos
                x1 = x0 + w
                y1 = y0 + h
                bbox = mtransforms.Bbox(((x0, y0), (x1, y1)))

                # the parent axes holding the 2 child-axes
                self._ax = plt.Axes(f, bbox, label="cb", zorder=zorder)
                f.add_axes(self._ax)

            # make all spines, labels etc. invisible for the base-axis
            self._ax.set_axis_off()

        # colorbar axes
        self.ax_cb = f.add_axes(
            self._ax.get_position(),
            label="EOmaps_cb",
            zorder=zorder - 1,  # make zorder 1 lower than container axes for picking
        )

        # histogram axes
        self.ax_cb_plot = f.add_axes(
            self._ax.get_position(),
            label="EOmaps_cb_hist",
            zorder=zorder - 1,  # make zorder 1 lower than container axes for picking
        )

        # add axes as child-axes
        self._ax.add_child_axes(self.ax_cb)
        self._ax.add_child_axes(self.ax_cb_plot)

        # join colorbar and histogram axes
        if self.orientation == "horizontal":
            self.ax_cb_plot.sharex(self.ax_cb)
        else:
            self.ax_cb_plot.sharey(self.ax_cb)

            # # for vertical colorbars, histogram-axis must be inverted!
            self.ax_cb_plot.xaxis.set_inverted(True)

        # keep the background of the plot-axis but remove the outer frame
        self.ax_cb_plot.spines["top"].set_visible(False)
        self.ax_cb_plot.spines["right"].set_visible(False)
        self.ax_cb_plot.spines["bottom"].set_visible(False)
        self.ax_cb_plot.spines["left"].set_visible(False)

        self._set_hist_size()

        self._attach_lim_cbs()

        return self._ax, self.ax_cb, self.ax_cb_plot

    def _attach_lim_cbs(self):
        # force lower limits of histogram axis to 0

        def ychanged(event):
            if self.orientation == "horizontal":
                with self.ax_cb_plot.callbacks.blocked(signal="ylim_changed"):
                    self.ax_cb_plot.set_ylim(0, None, emit=False)

        def xchanged(event):
            if self.orientation == "vertical":
                with self.ax_cb_plot.callbacks.blocked(signal="xlim_changed"):
                    self.ax_cb_plot.xaxis.set_inverted(True)
                    self.ax_cb_plot.set_xlim(left=None, right=0, emit=False)

        self.ax_cb_plot.callbacks.connect("xlim_changed", xchanged)
        self.ax_cb_plot.callbacks.connect("ylim_changed", ychanged)

    def _hide_singular_axes(self):
        sing_hist = self.ax_cb_plot.bbox.width <= 2 or self.ax_cb_plot.bbox.height <= 2
        sing_cb = self.ax_cb.bbox.width <= 2 or self.ax_cb.bbox.height <= 2

        if sing_hist:
            self.ax_cb_plot.set_visible(False)
        else:
            self.ax_cb_plot.set_visible(True)

        if sing_cb:
            self.ax_cb.set_visible(False)
        else:
            self.ax_cb.set_visible(True)

    def _set_hist_size(self, size=None, update_all=False):
        if size is None:
            size = self._hist_size
        else:
            self._hist_size = size

        assert 0 <= size <= 1, "Histogram size must be between 0 and 1"

        self._hide_singular_axes()

        if self._margin is None:
            if self.orientation == "horizontal":
                self._margin = dict(left=0.1, right=0.1, bottom=0.3, top=0.0)
            else:
                self._margin = dict(left=0.0, right=0.3, bottom=0.1, top=0.1)

        l, r = (self._margin.get(k, 0) for k in ["left", "right"])
        b, t = (self._margin.get(k, 0) for k in ["bottom", "top"])
        w, h = 1 - l - r, 1 - t - b

        if self.orientation == "horizontal":
            s = (1 - self._hist_size) * h
            l_cb_bounds = (l, b, w, s)
            l_hist_bounds = (l, b + s, w, h - s)
        else:
            s = (1 - self._hist_size) * w
            l_cb_bounds = (l + w - s, b, s, h)
            l_hist_bounds = (l, b, w - s, h)

        self._set_axes_locators(l_cb_bounds, l_hist_bounds)
        self._style_hist_ticks()

    def get_extend_fracs(self):
        # if no colorbar is found, use the full axis
        if not hasattr(self, "cb"):
            return 0, 1

        return 0, 1

        extend = self.cb.extend

        # extend fraction is defined as % of the interior colorbar length!
        getfrac = lambda n: self._extend_frac / (1 + n * self._extend_frac)

        if extend == "both":
            frac = getfrac(2)
            return frac, 1 - 2 * frac
        elif extend == "min":
            frac = getfrac(1)
            return frac, 1 - frac
        elif extend == "max":
            return 0, 1 - getfrac(1)
        else:
            return 0, 1

    def set_scale(self, log=False):
        if self.orientation == "horizontal":
            # set axis scale
            if log is True:
                self.ax_cb_plot.set_yscale("log")
            else:
                self.ax_cb_plot.set_yscale("linear")
        else:
            # set axis scale
            if log is True:
                self.ax_cb_plot.set_xscale("log")
            else:
                self.ax_cb_plot.set_xscale("linear")

    def _preprocess_data(self, out_of_range_vals="keep"):
        data = self._get_data()

        if isinstance(data, np.ma.masked_array):
            data = data.compressed()
        else:
            data = data.ravel()

        # make sure we only consider valid values in the histogram
        data = data[np.isfinite(data)]

        if out_of_range_vals == "mask":
            data_range_mask = (data >= self._vmin) & (data <= self._vmax)
            data = data[data_range_mask]

            # make sure that histogram weights are masked accordingly if provided
            if "weights" in self._hist_kwargs:
                self._hist_kwargs["weights"] = self._hist_kwargs["weights"][
                    data_range_mask
                ]

        # make sure the norm clips with respect to vmin/vmax
        # (only clip if either vmin or vmax is not None)
        elif out_of_range_vals == "clip":
            if self._vmin or self._vmax:
                data = data.clip(self._vmin, self._vmax)

        return data

    def _plot_colorbar(self, **kwargs):

        kwargs.setdefault("extendfrac", self._extend_frac)
        kwargs.setdefault("spacing", "proportional")
        kwargs.setdefault("extend", "both")

        self.cb = self.ax_cb.figure.colorbar(
            self._scm,
            cax=self.ax_cb,
            orientation=self.orientation,
            **kwargs,
        )

        self.cb.outline.set_visible(False)

        # after plotting the colorbar we must adjust the hist-size to ensure the
        # padding of the histogram axes confirms to the size of the colorbar arrows
        self._set_hist_size()

    def _plot_histogram(
        self, bins=None, out_of_range_vals="keep", show_outline=False, **kwargs
    ):

        self._hist_bins = bins
        self._out_of_range_vals = out_of_range_vals
        self._show_outline = show_outline

        # plot the histogram
        h = self.ax_cb_plot.hist(
            self._preprocess_data(out_of_range_vals=self._out_of_range_vals),
            orientation=self._hist_orientation,
            bins=self._hist_bins,
            align="mid",
            **kwargs,
        )

        if self._show_outline:
            if self._show_outline is True:
                outline_props = dict(color="k", lw=1)
            else:
                outline_props = self._show_outline

            if self.orientation == "horizontal":
                self.ax_cb_plot.step(
                    [h[1][0], *h[1], h[1][-1]], [0, h[0][0], *h[0], 0], **outline_props
                )
            else:
                self.ax_cb_plot.step([0, *h[0], 0], [h[1][0], *h[1]], **outline_props)

        bins = getattr(self._norm, "boundaries", None)

        if bins is None:
            # identify position of color-splits in the colorbar
            if isinstance(self._scm.cmap, LinearSegmentedColormap):
                # for LinearSegmentedcolormap N is the number of quantizations!
                splitpos = np.linspace(self._vmin, self._vmax, self._scm.cmap.N)
            else:
                # for ListedColormap N is the number of colors
                splitpos = np.linspace(self._vmin, self._vmax, self._scm.cmap.N + 1)
        else:
            splitpos = np.asanyarray(bins)

        # color the histogram patches
        for patch in list(self.ax_cb_plot.patches):
            # the list is important!! since otherwise we change ax.patches
            # as we iterate over it... which is not a good idea...
            if self.orientation == "horizontal":
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

            args = dict(
                edgecolor=kwargs.get("edgecolor", kwargs.get("ec", None)),
                linewidth=kwargs.get("linewidth", kwargs.get("lw", 0)),
                linestyle=kwargs.get("linestyle", kwargs.get("ls", None)),
                alpha=kwargs.get("alpha", None),
                hatch=kwargs.get("hatch", None),
            )
            # drop all unset values to avoi overriding defaults
            args = {key: val for key, val in args.items() if val is not None}
            # handle facecolors explicitly
            facecolor = kwargs.get("facecolor", kwargs.get("fc", None))

            if len(splitbins) > 2:
                patch.remove()
                # add in-between patches
                for b0, b1 in pairwise(splitbins):
                    if self.orientation == "horizontal":
                        pi = Rectangle(
                            (b0, 0),
                            (b1 - b0),
                            height,
                            facecolor=(
                                facecolor
                                if facecolor
                                else self._cmap(self._norm((b0 + b1) / 2))
                            ),
                            **args,
                        )
                    else:
                        pi = Rectangle(
                            (0, b0),
                            width,
                            (b1 - b0),
                            facecolor=(
                                facecolor
                                if facecolor
                                else self._cmap(self._norm((b0 + b1) / 2))
                            ),
                            **args,
                        )

                    self.ax_cb_plot.add_patch(pi)
            else:
                patch.set_facecolor(
                    facecolor
                    if facecolor
                    else self._cmap(self._norm((minval + maxval) / 2))
                )
                for key, val in args.items():
                    getattr(patch, f"set_{key}")(val)

        # add gridlines
        if self.orientation == "horizontal":
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
            if self.ax_cb_plot.get_yscale() == "log":
                self.ax_cb_plot.set_ylim(0)
        else:
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
            if self.ax_cb_plot.get_xscale() is False:
                self.ax_cb_plot.set_xlim(None, 0)

    def _style_hist_ticks(self):
        # setup appearance of histogram
        if self.orientation == "horizontal":
            if self._hist_size < 1:
                self.ax_cb_plot.tick_params(
                    left=False,
                    labelleft=True,
                    bottom=False,
                    top=False,
                    labelbottom=False,
                    labeltop=False,
                )
            else:
                self.ax_cb_plot.tick_params(
                    left=False,
                    labelleft=True,
                    bottom=True,
                    top=False,
                    labelbottom=True,
                    labeltop=False,
                )

        else:
            if self._hist_size < 1:
                self.ax_cb_plot.tick_params(
                    left=False,
                    labelleft=False,
                    bottom=False,
                    top=False,
                    labelbottom=True,
                    labeltop=False,
                    rotation=90,
                )
            else:
                self.ax_cb_plot.tick_params(
                    left=False,
                    labelleft=False,
                    right=True,
                    labelright=True,
                    bottom=False,
                    top=False,
                    labelbottom=True,
                    labeltop=False,
                    rotation=90,
                )

    def _redraw(self, *args, **kwargs):
        # only re-draw if the corresponding layer is visible
        if not self._m.BM._layer_visible(self.layer):
            return

        self.ax_cb.clear()
        self.ax_cb_plot.clear()

        self._attach_lim_cbs()  # re-attach ylim callbacks

        self._set_hist_size()

        self._plot_colorbar()

        self._plot_histogram(
            bins=self._hist_bins,
            out_of_range_vals=self._out_of_range_vals,
            show_outline=self._show_outline,
        )

    def _set_labels(self, cb_label=None, hist_label=None, **kwargs):
        if self._dynamic_shade_indicator and hist_label is not None:
            # remember kwargs to re-draw the histogram
            self._hist_label_kwargs = {
                "cb_label": None,
                "hist_label": hist_label,
                **kwargs,
            }

        if self.orientation == "horizontal":
            if cb_label:
                if self._hist_size < 0.001:
                    # label colorbar
                    self.ax_cb_plot.set_xlabel("")
                    self.ax_cb.set_xlabel(cb_label, **kwargs)
                elif self._hist_size > 0.999:
                    # label plot
                    self.ax_cb_plot.set_xlabel(cb_label, **kwargs)
                    self.ax_cb.set_xlabel("")
                else:
                    # label colorbar
                    self.ax_cb_plot.set_xlabel("")
                    self.ax_cb.set_xlabel(cb_label, **kwargs)
            if hist_label:
                self._hist_label = self.ax_cb_plot.set_ylabel(hist_label, **kwargs)
        else:
            if cb_label:
                if self._hist_size < 0.001:
                    # label colorbar
                    self.ax_cb_plot.set_ylabel("")
                    self.ax_cb.set_ylabel(cb_label, **kwargs)
                elif self._hist_size > 0.999:
                    # label plot
                    self.ax_cb_plot.set_ylabel(cb_label, **kwargs)
                    self.ax_cb.set_xlabel("")
                else:
                    # label colorbar
                    self.ax_cb_plot.set_ylabel("")
                    self.ax_cb.set_ylabel(cb_label, **kwargs)

            if hist_label:
                self._hist_label = self.ax_cb_plot.set_xlabel(hist_label, **kwargs)

    def set_labels(self, cb_label=None, hist_label=None, **kwargs):
        """
        Set the labels (and the styling) for the colorbar (and the histogram).

        For more details, see `ColorBar.ax_cb.set_xlabel(..)` and matplotlib's `.Text`
        properties.

        Parameters
        ----------
        cb_label : str or None
            The label of the colorbar. If None, the existing label is maintained.
            The default is None.
        hist_label : str or None
            The label of the histogram. If None, the existing label is maintained.
            The default is None.

        Other Parameters
        ----------------
        kwargs :
           Additional kwargs passed to `Axes.set_xlabel` to control the appearance of
           the label (e.g. color, fontsize, labelpad etc.).

        Examples
        --------
        Set both colorbar and histogram label in one go

        >>> cb.set_labels("The parameter", "histogram count", fontsize=10, color="r")

        Use different styles for the colorbar and histogram labels

        >>> cb.set_labels(cb_label="The parameter", color="r", labelpad=10)
        >>> cb.set_labels(hist_label="histogram count", fontsize=6, color="k")

        """

        self._label_kwargs = {"cb_label": cb_label, "hist_label": hist_label, **kwargs}

        self._set_labels(cb_label=cb_label, hist_label=hist_label, **kwargs)

        if not self._dynamic_shade_indicator:
            # no need to redraw the background for dynamically updated artists
            self._m.redraw(self.layer)
        else:
            self._m.BM.update()

    def tick_params(self, what="colorbar", **kwargs):
        """Set the appearance of the colorbar (or histogram) ticks."""
        if what == "colorbar":
            self.ax_cb.tick_params(**kwargs)
        elif what == "histogram":
            self.ax_cb_plot.tick_params(**kwargs)

        self._m.redraw(self.layer)

    tick_params.__doc__ = (
        "Set the appearance of the colorbar (or histogram) ticks.\n\n"
        "NOTE\n"
        "----\n"
        "This is a wrapper for `m.colorbar.ax_cb.tick_params` or "
        "`m.colorbar.ax_cb_plot.tick_params` to set the appearance of the ticks for "
        "the colorbar or the histogram."
        "You can select what you want to edit with the additional parameter:"
        "\n\n"
        "what: {'colorbar', 'histogram'}, default: 'colorbar'\n"
        "    - 'colorbar' : colorbar ticks (same as `m.colorbar.ax_cb.tick_params`)\n"
        "    - 'histogram' : histogram ticks (same as `m.colorbar.ax_cb_plot.tick_params`)\n"
        "\n\n----------------\n\n" + dedent(plt.Axes.tick_params.__doc__)
    )


class ColorBar(ColorBarBase):
    def __init__(self, *args, inherit_position=True, **kwargs):
        super().__init__(*args, **kwargs)

        self._inherit_position = inherit_position
        self._dynamic_shade_indicator = False

    @property
    def layer(self):
        return self._m.layer

    def _default_cb_tick_formatter(self, x, pos, precision=None):
        """
        A formatter to format the tick-labels of the colorbar for encoded datasets.
        (used in xaxis.set_major_formatter() )
        """
        # if precision=None the shortest representation of the number is used
        return np.format_float_positional(
            self._m._decode_values(x), precision=self._tick_precision
        )

    def _classified_cb_tick_formatter(self, x, pos, precision=None):
        """
        A formatter to format the tick-labels of the colorbar for classified datasets.
        (used in xaxis.set_major_formatter() )
        """
        # if precision=None the shortest representation of the number is used
        if x >= self._vmin and x <= self._vmax:
            return np.format_float_positional(
                self._m._decode_values(x), precision=self._tick_precision, trim="-"
            )
        else:
            return ""

    def _hide_singular_axes(self):
        # make sure that the mechanism for hiding singular axes does not show
        # colorbars that are not on the visible layer

        super()._hide_singular_axes()
        if not self._m.BM._layer_visible(self.layer):
            self.ax_cb.set_visible(False)
            self.ax_cb_plot.set_visible(False)

    def _get_data(self):
        if self._dynamic_shade_indicator is True:
            data = self._m.coll.get_ds_data().values
        else:
            data = self._m._data_manager.z_data

        return data

    def _identify_parent_cb(self):
        parent_cb = None
        # check if there is already an existing colorbar for a Maps-object that shares
        # the same plot-axis. If yes, inherit the position of this colorbar!

        if self._m.colorbar is not None and not self._inherit_position:
            parent_cb = None  # self._m.colorbar
        else:
            # check if self is actually just another layer of an existing Maps object
            # that already has a colorbar assigned
            for m in [self._m.parent, *self._m.parent._children]:
                if m is not self._m and m.ax is self._m.ax:
                    if m.colorbar is not None:
                        if m.colorbar._parent_cb is None:
                            parent_cb = m.colorbar
                            break
        if parent_cb and parent_cb.orientation == self.orientation:
            return parent_cb
        else:
            return None

    def _set_map(self, m):
        self._m = m

        if isinstance(self._inherit_position, ColorBarBase):
            self._parent_cb = self._inherit_position
        else:
            self._parent_cb = self._identify_parent_cb()

        self._vmin = self._m.coll.norm.vmin
        self._vmax = self._m.coll.norm.vmax
        self._norm = self._m.coll.norm
        self._cmap = self._m.coll.cmap

    def _add_axes_to_layer(self, dynamic):
        BM = self._m.BM

        self._layer = self._m.layer

        # add all axes as artists
        self.ax_cb.set_navigate(False)

        for a in (self._ax, self.ax_cb, self.ax_cb_plot):
            if a is not None:
                if dynamic is True:
                    BM.add_artist(a, self._layer)
                else:
                    BM.add_bg_artist(a, self._layer)

        # we need to re-draw since the background axis size has changed!
        BM._refetch_layer(self._layer)
        BM._refetch_layer("__SPINES__")
        self._m.redraw("__SPINES__")

    def _set_hist_size(self, *args, **kwargs):
        super()._set_hist_size(*args, **kwargs)
        self._m.BM._refetch_layer(self.layer)

    def set_hist_size(self, size=None):
        """
        Set the size of the histogram (relative to the total colorbar size)

        Parameters
        ----------
        size : float
            The fraction of the colorbar occupied by the histogram.

            - 0 = no histogram
            - 0.5 = 50% colorbar, 50% histogram
            - 1 = no colorbar, only histogram).

            The default is None.
        """
        self._set_hist_size(size, update_all=True)
        self._m.BM.update()

    def make_dynamic(self):
        self._dynamic_shade_indicator = True

        if not hasattr(self._m.coll, "get_ds_data"):
            print("dynamic colorbars are only possible for shade-shapes!")
            return

        if not hasattr(self, "_cid_redraw"):
            self._cid_redraw = False

        if self._cid_redraw is False:

            def check_data_updated(*args, **kwargs):
                # make sure the artist is updated before checking for new data
                # TODO check if this is really enough to ensure that the coll
                # is fully updated (calling coll.draw() is not an option since it
                # would result make the collection appear on any layer!)
                self._m.coll.changed()
                dsdata = self._m.coll.get_ds_data()
                if getattr(self, "_last_ds_data", None) is not None:
                    if not self._last_ds_data.equals(dsdata):
                        # if the data has changed, redraw the colorbar
                        self._redraw()

                self._last_ds_data = dsdata

            self._m.BM._before_fetch_bg_actions.append(check_data_updated)

            self._m.BM.on_layer(
                lambda *args, **kwargs: self._redraw,
                layer=self.layer,
                persistent=True,
            )

            self._cid_redraw = True

    def indicate_contours(
        self,
        contour_map=None,
        add_labels="top",
        use_levels=None,
        exclude_levels=None,
        colors=None,
        linewidths=None,
        linestyles=None,
        label_names=None,
        label_precision=4,
        label_kwargs=None,
    ):
        """
        Indicate contour locations in the colorbar.

        Note: Before using this function you must draw a dataset with the ``"contour"``
        shape! (you can also indicate contours from other Maps-objects by using
        the optional ``contour_map`` argument.)

        Parameters
        ----------
        contour_map : eomaps.Maps, optional
            The maps object whose contours should be indicated.
            If None, the Maps-object associated with this colorbar is used.
            The default is None.
        add_labels : str, float or None, optional

            - "bottom": add labels at the bottom of the colorbar
            - "top": add labels to the top of the colorbar histogram
            - If float: The relative position of the label in axis-coordinates (0-1)
            - None: don't add labels

            The default is "bottom".
        rotation : float, optional
            The rotation of the labels (in degrees). The default is 90.
        use_levels : list of int, optional
            A list of integers that specify levels that should be used.
            (negative values count from right)

            If None, all values are used.

            For example, to draw the first and 3rd level and name them "A" and "B", use:

                >>> cb.indicate_contours(use_levels = [-1, 2], label_names=["A", "B"])


            The default is None.

        exclude_levels : list of int, optional
            Only relevant if "use_levels" is None!
            A list of integers that specify levels that should be ignored.
            (negative values count from right)

            By default, the last level are ignored, e.g.:

            >>> exclude_levels = [-1]

        colors : str or list, optional
            Custom colors that will be used for the lines.
            NOTE: If less values than levels are specified, values are cycled!

            If None, the contour-colors are used.
            The default is None.
        linewidths : float or list, optional
            Custom linewidths that will be used for the lines.
            NOTE: If less values than levels are specified, values are cycled!

            If None, the contour-linewidths are used.
            The default is None.
        linestyles : float, tuple or list, optional
            Custom linestyles that will be used for the lines.
            NOTE: If less values than levels are specified, values are cycled!

            If None, the contour-linestyles are used.
            The default is None.
        label_kwargs : dict
            Additional kwargs passed to the creation of the labels.

            - Font-properties like "fontsize", "fontweight", "rotation", etc..
            - To offset the text (in points) from the xy value, use "xytext".
            - To add an arrow, use "arrowprops".

            For more details, see ``plt.annotate``.


            The default is:

            >>> {fontsize: "x-small",
            >>>  textcoords: "offset points"
            >>>  xytext: (0, 0)}


        """
        if label_kwargs is None:
            label_kwargs = dict()

        label_kwargs.setdefault("fontsize", "x-small")
        label_kwargs.setdefault("textcoords", "offset points")
        label_kwargs.setdefault("xytext", (0, 0))

        if exclude_levels is None:
            exclude_levels = [-1]

        if contour_map is None:
            coll = self._m.coll
        else:
            coll = contour_map.coll

        if not coll.__class__.__name__ == "_CollectionAccessor":
            raise TypeError(
                "EOmaps: Contour-lines can only be added to the colorbar if a contour "
                "was plotted first! If you want to indicate contours plotted on a "
                "different Maps-object, provide it via the 'contour_map' argument!"
            )

        levels = coll.levels

        # add support for using -1 to exclude the last level
        for i, val in enumerate(exclude_levels):
            if val < 0:
                exclude_levels[i] = len(levels) + val

        if colors is None:
            if coll._filled is False:
                colors = (
                    np.array(coll.get_edgecolors(), dtype=object).squeeze().tolist()
                )
            else:
                colors = (
                    np.array(coll.get_facecolors(), dtype=object).squeeze().tolist()
                )
        else:
            colors = cycle(colors)

        if linewidths is None:
            linewidths = (
                np.array(coll.get_linewidths(), dtype=object).squeeze().tolist()
            )
        else:
            linewidths = cycle(linewidths)

        if linestyles is None:
            linestyles = (
                np.array(coll.get_linestyles(), dtype=object).squeeze().tolist()
            )
        else:
            linestyles = cycle(linestyles)

        used_levels = []
        for i, (level, c, ls, lw) in enumerate(
            zip(
                levels,
                colors,
                linestyles,
                linewidths,
            )
        ):
            if use_levels is None and i in exclude_levels:
                continue

            if use_levels is not None and i not in use_levels:
                continue

            (a,) = self.ax_cb_plot.plot(
                [level, level],
                [self.ax_cb_plot.dataLim.y0, self.ax_cb_plot.dataLim.y1],
                c=c,
                ls=tuple(ls),  # linestyles must be provided as tuples!
                lw=lw,
                zorder=99999,
            )

            used_levels.append(level)

        if label_names is None:
            label_names = [
                np.format_float_positional(i, precision=label_precision)
                for i in used_levels
            ]
        else:
            label_names = label_names

        if add_labels == "top":
            label_kwargs.setdefault("horizontalalignment", "center")
            label_kwargs.setdefault("verticalalignment", "bottom")
            label_kwargs.setdefault("y", self.ax_cb_plot.dataLim.y1)

        elif add_labels == "bottom":
            label_kwargs.setdefault("horizontalalignment", "center")
            label_kwargs.setdefault("verticalalignment", "top")
            label_kwargs.setdefault("y", self.ax_cb_plot.dataLim.y0)
        elif isinstance(add_labels, float):
            label_kwargs.setdefault("horizontalalignment", "left")
            label_kwargs.setdefault("verticalalignment", "center")
            t = self.ax_cb_plot.transAxes + self.ax_cb_plot.transData.inverted()
            pos = t.transform((0, add_labels))

            label_kwargs.setdefault("y", pos[1])

        y = label_kwargs.pop("y")
        for level, label in zip(used_levels, label_names):
            self.ax_cb_plot.annotate(xy=(level, y), text=label, **label_kwargs)

        self._m.redraw(self.layer)

    def set_bin_labels(self, bins, names, tick_lines="center", show_values=False):
        """
        Set the tick-labels of the colorbar to custom names with respect to a given
        set of bins.

        The labels will be placed at the center of each bin.

        This is most useful when using `m.set_classify.UserDefined(bins=[...])`
        to classify the data with respect to custom bins.

        Parameters
        ----------
        bins : list
            A list of (right) bin-boundaries used to set the label-positions.
            (e.g. `bins=[1, 2, 6]` will result in labels located at [1.5 and 4])
        names : list
            A list of names that should be used as labels.

            - The first name is assigned to the values smaller than bins[0]
            - Names 1 to "len(bins)" are assigned to the intermediate bins
            - The "len(bins) + 1" label is assigned to the values larger than bins[-1]
              (if not available a "?" label will be used)

        tick_lines : str
            Set appearance of the tick-lines

            - "boundary": show only (minor) tick lines at the bin-boundaries
            - "center": show only (major) tick lines at the center of the bins
            - "both": show both major and minor tick lines
            - None: don't show any tick lines

            The default is "center"
        show_values : bool
            If True, numerical values of the bin-boundaries will be shown as
            minor-tick labels. The default is False
        Examples
        --------

        >>> bins = [1, 2, 3]
        >>> names = ["smaller than 1",
        >>>          "between 1 and 2",
        >>>          "between 2 and 3",
        >>>          "larger than 3"]
        >>>
        >>> m.add_colorbar()
        >>> m.label_bin_centers(bins, names)

        """
        nnames, nbins = len(names), len(bins)

        assert nnames in [nbins, nbins + 1], (
            "The number of provided names is incorrect! "
            f"Expected {nbins} (or {nbins + 1}) names but got {nnames}"
        )

        if nnames == nbins:
            names = [*names, "?"]

        horizontal = self.orientation == "horizontal"

        cbticks = np.array(sorted({self._vmin, *bins, self._vmax}))
        centerticks = cbticks[:-1] + (cbticks[1:] - cbticks[:-1]) / 2

        tick_formatter = get_named_bins_formatter(bins, names)

        self.cb.set_ticks(centerticks)
        self.cb.set_ticks(cbticks, minor=True)

        if horizontal:
            # set the histogram ticks to be the same as the colorbar-ticks
            # (just in case somebody wants to show ticks on the top of the histogram)
            self.ax_cb_plot.set_xticks(centerticks)
            self.ax_cb_plot.set_xticks(cbticks, minor=True)

            # set the tick-label formatter for the colorbar-ticks
            self.ax_cb.xaxis.set_major_formatter(tick_formatter)
            self.ax_cb_plot.xaxis.set_major_formatter(tick_formatter)

            if tick_lines == "boundary":
                self.ax_cb.tick_params(bottom=False)
                self.ax_cb.tick_params(bottom=True, which="minor")
            elif tick_lines == "center":
                self.ax_cb.tick_params(bottom=True)
                self.ax_cb.tick_params(bottom=False, which="minor")
            elif tick_lines == "both":
                self.ax_cb.tick_params(bottom=True)
                self.ax_cb.tick_params(bottom=True, which="minor")
            else:
                self.ax_cb.tick_params(bottom=False)
                self.ax_cb.tick_params(bottom=False, which="minor")

        else:
            self.ax_cb_plot.set_yticks(centerticks)
            self.ax_cb_plot.set_yticks(cbticks, minor=True)
            self.ax_cb.yaxis.set_major_formatter(tick_formatter)
            self.ax_cb_plot.yaxis.set_major_formatter(tick_formatter)

            if tick_lines == "boundary":
                self.ax_cb.tick_params(right=False)
                self.ax_cb.tick_params(right=True, which="minor")
            elif tick_lines == "center":
                self.ax_cb.tick_params(right=True)
                self.ax_cb.tick_params(right=False, which="minor")
            elif tick_lines == "both":
                self.ax_cb.tick_params(right=True)
                self.ax_cb.tick_params(right=True, which="minor")
            else:
                self.ax_cb.tick_params(right=False)
                self.ax_cb.tick_params(right=False, which="minor")

        if show_values:
            minor_tick_formatter = partial(
                self._default_cb_tick_formatter, precision=self._tick_precision
            )

            if horizontal:
                self.ax_cb.xaxis.set_minor_formatter(minor_tick_formatter)
                self.ax_cb_plot.xaxis.set_minor_formatter(minor_tick_formatter)
                self.ax_cb.tick_params(
                    labelbottom=True, which="minor", labelsize="xx-small"
                )

            else:
                self.ax_cb.yaxis.set_minor_formatter(minor_tick_formatter)
                self.ax_cb_plot.xaxis.set_minor_formatter(minor_tick_formatter)
                self.ax_cb.tick_params(
                    labelright=True, which="minor", labelsize="xx-small"
                )

        else:
            if horizontal:
                self.ax_cb.tick_params(
                    labelbottom=False,
                    which="minor",
                )

            else:
                self.ax_cb.tick_params(
                    labelright=False,
                    which="minor",
                )

        if horizontal:
            self.ax_cb_plot.tick_params(
                right=False,
                bottom=False,
                labelright=False,
                labelbottom=False,
                which="both",
            )
        else:
            self.ax_cb_plot.tick_params(
                left=False, top=False, labelleft=False, labeltop=False, which="both"
            )

        self._m.BM._refetch_layer(self.layer)

    def _set_tick_formatter(self):
        if self._m._classified:
            self.cb.set_ticks(
                np.unique(np.clip(self._m.classify_specs._bins, self._vmin, self._vmax))
            )

        if self.orientation == "horizontal":
            if self._m._classified:
                self.ax_cb.xaxis.set_major_formatter(self._classified_cb_tick_formatter)
            else:
                self.ax_cb.xaxis.set_major_formatter(self._default_cb_tick_formatter)
        else:
            if self._m._classified:
                self.ax_cb.yaxis.set_major_formatter(self._classified_cb_tick_formatter)
            else:
                self.ax_cb.yaxis.set_major_formatter(self._default_cb_tick_formatter)

    def _redraw(self, *args, **kwargs):
        super()._redraw(*args, **kwargs)
        self._set_tick_formatter()

    @classmethod
    def add_colorbar(
        cls,
        m,
        pos=0.4,
        inherit_position=None,
        orientation="horizontal",
        hist_bins=256,
        hist_size=0.8,
        out_of_range_vals="clip",
        tick_precision=2,
        dynamic_shade_indicator=False,
        extend=None,
        extend_frac=0.025,
        log=False,
        label=None,
        ylabel=None,
        show_outline=False,
        hist_kwargs=None,
        margin=None,
        **kwargs,
    ):

        cb = cls(
            orientation=orientation,
            hist_kwargs=hist_kwargs,
            tick_precision=tick_precision,
            inherit_position=inherit_position,
            extend_frac=extend_frac,
            margin=margin,
        )
        cb._set_map(m)
        cb._setup_axes(pos, m.ax)
        cb._add_axes_to_layer(dynamic=dynamic_shade_indicator)

        cb._set_hist_size(hist_size)
        cb.set_scale(log)
        cb._plot_colorbar(extend=extend)

        bins = (
            m.classify_specs._bins
            if (m._classified and hist_bins == "bins")
            else hist_bins
        )

        cb._plot_histogram(
            bins=bins,
            out_of_range_vals=out_of_range_vals,
            show_outline=show_outline,
        )

        cb._set_tick_formatter()

        cb.set_labels(cb_label=label, hist_label=ylabel)

        if dynamic_shade_indicator:
            cb.make_dynamic()

        return cb

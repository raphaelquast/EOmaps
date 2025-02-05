from itertools import cycle
from functools import partial
from textwrap import dedent

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpecFromSubplotSpec, SubplotSpec
import matplotlib.transforms as mtransforms
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

import numpy as np

from .helpers import _TransformedBoundsLocator, pairwise, version, mpl_version

import logging

_log = logging.getLogger(__name__)


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
        tick_precision=2,
        margin=None,
        divider_linestyle=None,
        hist_size=0.9,
    ):
        self._parent_cb = None

        if hist_size is None:
            self._hist_size_ = 0
        else:
            self._hist_size_ = hist_size

        self._extend_frac = extend_frac

        self.orientation = orientation

        self._tick_precision = tick_precision
        self._margin = margin

        self._vmin = None
        self._vmax = None
        self._norm = None
        self._cmap = None
        self._data = None

        if divider_linestyle is None:
            self._divider_linestyle = dict(color="k", linestyle="--", alpha=0.5)
        else:
            self._divider_linestyle = divider_linestyle

    @property
    def _scm(self):
        return plt.cm.ScalarMappable(cmap=self._cmap, norm=self._norm)

    @property
    def _hist_orientation(self):
        return "vertical" if self.orientation == "horizontal" else "horizontal"

    @property
    def _hist_size(self):
        if self._parent_cb is None:
            return self._hist_size_
        else:
            return self._parent_cb._hist_size_

    @_hist_size.setter
    def _hist_size(self, size):
        if size is None:
            size = 0

        if self._parent_cb is None:
            self._hist_size_ = size
        else:
            self._hist_size_ = size
            self._parent_cb._hist_size_ = size

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
                        navigate=False,
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
                        navigate=False,
                    )
            elif isinstance(pos, SubplotSpec):
                self._ax = f.add_subplot(
                    pos,
                    label="cb",
                    zorder=zorder,
                    navigate=False,
                )
            elif isinstance(pos, (list, tuple)):
                x0, y0, w, h = pos
                x1 = x0 + w
                y1 = y0 + h
                bbox = mtransforms.Bbox(((x0, y0), (x1, y1)))

                # the parent axes holding the 2 child-axes
                self._ax = plt.Axes(f, bbox, label="cb", zorder=zorder)
                f.add_axes(self._ax, navigate=False)

            # make all spines, labels etc. invisible for the base-axis
            self._ax.set_axis_off()
            self._ax._eomaps_cb_axes = []

        # colorbar axes
        self.ax_cb = f.add_axes(
            self._ax.get_position(),
            label="EOmaps_cb",
            zorder=zorder - 1,  # make zorder 1 lower than container axes for picking
            navigate=False,
        )

        # histogram axes
        self.ax_cb_plot = f.add_axes(
            self._ax.get_position(),
            label="EOmaps_cb_hist",
            zorder=zorder - 1,  # make zorder 1 lower than container axes for picking
            navigate=False,
        )

        # remember child axes
        self._ax._eomaps_cb_axes.extend([self.ax_cb, self.ax_cb_plot])

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
        self._style_hist_ticks()

        self._attach_lim_cbs()

        return self._ax, self.ax_cb, self.ax_cb_plot

    def _attach_lim_cbs(self):
        # force lower limits of histogram axis to 0

        def ychanged(event):
            if self.orientation == "horizontal":
                with self.ax_cb_plot.callbacks.blocked(signal="ylim_changed"):
                    if self.ax_cb_plot.get_yscale() == "log":
                        pass
                    else:
                        self.ax_cb_plot.set_ylim(0, None, emit=False)

        def xchanged(event):
            if self.orientation == "vertical":
                with self.ax_cb_plot.callbacks.blocked(signal="xlim_changed"):
                    self.ax_cb_plot.xaxis.set_inverted(True)
                    if self.ax_cb_plot.get_xscale() == "log":
                        pass
                    else:
                        self.ax_cb_plot.set_xlim(left=None, right=0, emit=False)

        self.ax_cb_plot.callbacks.connect("xlim_changed", xchanged)
        self.ax_cb_plot.callbacks.connect("ylim_changed", ychanged)

    def _hide_singular_axes(self):
        sing_hist = (self.ax_cb_plot.bbox.width <= 2) or (
            self.ax_cb_plot.bbox.height <= 2
        )
        sing_cb = (self.ax_cb.bbox.width <= 2) or (self.ax_cb.bbox.height <= 2)

        sing_hist = (self.ax_cb_plot.bbox.width <= 2) or (
            self.ax_cb_plot.bbox.height <= 2
        )
        sing_cb = (self.ax_cb.bbox.width <= 2) or (self.ax_cb.bbox.height <= 2)

        # use additional constraint < 0.1 to re-show axes after they have been hidden
        # (positions of hidden axes are not updated so we don't know the new position
        # before re-drawing... and a re-draw is not wanted because it would fetch
        # a new unnecessary background
        if sing_hist and self._hist_size < 0.01:
            self.ax_cb_plot.set_visible(False)
        else:
            self.ax_cb_plot.set_visible(True)

        if sing_cb and self._hist_size > 0.99:
            self.ax_cb.set_visible(False)
        else:
            self.ax_cb.set_visible(True)

    def _set_hist_size(self, size=None, update_all=False):
        if size is not None:
            self._hist_size = size

        assert 0 <= self._hist_size <= 1, "Histogram size must be between 0 and 1"

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

    def _preprocess_data(self, out_of_range_vals="keep"):
        data = self._get_data()

        if isinstance(data, np.ma.masked_array):
            data = data.compressed()
        else:
            data = data.ravel()

        # make sure we only consider valid values in the histogram
        finitemask = np.isfinite(data)
        data = data[finitemask]

        # make sure that histogram weights are masked accordingly if provided
        if "weights" in self._hist_kwargs:
            self._hist_kwargs["weights"] = self._hist_kwargs["weights"][finitemask]

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

        self._cb_kwargs = kwargs

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
        self, bins=None, out_of_range_vals="keep", outline=False, **kwargs
    ):

        self._hist_kwargs = kwargs
        self._hist_bins = bins
        self._out_of_range_vals = out_of_range_vals
        self._outline = outline

        if "range" not in self._hist_kwargs:
            self._hist_kwargs["range"] = (
                (self._vmin, self._vmax) if (self._vmin and self._vmax) else None
            )

        # plot the histogram
        h = self.ax_cb_plot.hist(
            self._preprocess_data(out_of_range_vals=self._out_of_range_vals),
            orientation=self._hist_orientation,
            bins=self._hist_bins,
            align="mid",
            **self._hist_kwargs,
        )

        if self._outline:
            if self._outline is True:
                outline_props = dict(color="k", lw=1)
            else:
                outline_props = self._outline

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
                transform=self.ax_cb_plot.transAxes,
                **self._divider_linestyle,
            )
            # make sure lower y-limit is 0
            if self.ax_cb_plot.get_yscale() != "log":
                self.ax_cb_plot.set_ylim(0)
        else:
            self.ax_cb_plot.grid(axis="x", dashes=[5, 5], c="k", alpha=0.5)
            # add a line that indicates 0 histogram level
            self.ax_cb_plot.plot(
                [1, 1],
                [0, 1],
                transform=self.ax_cb_plot.transAxes,
                **self._divider_linestyle,
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

        self._plot_colorbar(**self._cb_kwargs)

        self._plot_histogram(
            bins=self._hist_bins,
            out_of_range_vals=self._out_of_range_vals,
            outline=self._outline,
            **self._hist_kwargs,
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


class ColorBar(ColorBarBase):
    """
    Base class for EOmaps colorbars with a histogram on top.

    Note
    ----
    To add a colorbar to a map, use
    :py:meth:`Maps.add_colorbar <eomaps.eomaps.Maps.add_colorbar>`.

    """

    max_n_classify_bins_to_label = 30

    def __init__(self, *args, inherit_position=True, layer=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._layer = layer

        self._inherit_position = inherit_position
        self._dynamic_shade_indicator = False

    @property
    def layer(self):
        """The layer associated with the colorbar."""
        if self._layer is None:
            return self._m.layer
        else:
            return self._layer

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
        if self._inherit_position is False:
            parent_cb = None
        elif self._m.colorbar is not None and self.layer == self._m.colorbar.layer:
            # in case a colorbar is already present on the same layer, don't
            # inherit the position (since they would overlap)
            parent_cb = None
        elif isinstance(self._inherit_position, ColorBar):
            # if a colorbar instance is provided, use it to inherit its position
            parent_cb = self._inherit_position
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

    def remove(self):
        """Remove the colorbar from the map."""
        if self._dynamic_shade_indicator:
            try:
                self._m.BM._before_fetch_bg_actions.remove(self._check_data_updated)
            except Exception:
                _log.debug("Problem while removing dynamic-colorbar callback")

            self._m.BM.remove_artist(self.ax_cb, self.layer)
            self._m.BM.remove_artist(self.ax_cb_plot, self.layer)

        else:
            self._m.BM.remove_bg_artist(self.ax_cb, self.layer, draw=False)
            self._m.BM.remove_bg_artist(self.ax_cb_plot, self.layer, draw=False)

        if self.ax_cb in self._ax._eomaps_cb_axes:
            self._ax._eomaps_cb_axes.remove(self.ax_cb)
        if self.ax_cb_plot in self._ax._eomaps_cb_axes:
            self._ax._eomaps_cb_axes.remove(self.ax_cb_plot)

        self.ax_cb.remove()
        self.ax_cb_plot.remove()

    def _set_map(self, m):
        self._m = m

        if self._layer is None:
            self._layer = self._m.layer

        self._parent_cb = self._identify_parent_cb()

        self._vmin = self._m.coll.norm.vmin
        self._vmax = self._m.coll.norm.vmax
        self._norm = self._m.coll.norm
        self._cmap = self._m.coll.cmap

    def _add_axes_to_layer(self, dynamic):
        BM = self._m.BM

        # add all axes as artists
        self.ax_cb.set_navigate(False)

        for a in (self.ax_cb, self.ax_cb_plot):
            if a is not None:
                if dynamic is True:
                    BM.add_artist(a, self._layer)
                else:
                    BM.add_bg_artist(a, self._layer)

        # we need to re-draw all layers since the axis size has changed!
        self._m.redraw()

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

    def _check_data_updated(self, *args, **kwargs):
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

    def _make_dynamic(self):
        if "weights" in self._hist_kwargs:
            _log.warn(
                "EOmaps: Weighted histograms for 'dynamic-shade indicator' colorbars "
                "are not supported! Histogram weights will be ignored!"
            )
            self._hist_kwargs.pop("weights")

        self._dynamic_shade_indicator = True

        if not hasattr(self._m.coll, "get_ds_data"):
            print("dynamic colorbars are only possible for shade-shapes!")
            return

        if not hasattr(self, "_cid_redraw"):
            self._cid_redraw = False

        if self._cid_redraw is False:
            self._m.BM._before_fetch_bg_actions.append(self._check_data_updated)

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

        Note: Before using this function you must draw a dataset with the
        :py:class:`contour <eomaps.eomaps.Maps.set_shape.contour>` shape!
        (you can also indicate contours from other Maps-objects by using
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

        # TODO remove this once mpl >=3.10 is required
        if mpl_version < version.Version("3.10"):
            expected_collections = ["_CollectionAccessor"]
        else:
            expected_collections = ["ContourSet", "TriContourSet", "GeoContourSet"]

        if not coll.__class__.__name__ in expected_collections:
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
            # _filled is required for mpl <3.10 (e.g. _CollectionAccessor)
            # TODO use only "coll.filled" once mpl >=3.10 is required
            filled = coll._filled if hasattr(coll, "_filled") else coll.filled

            if filled is False:
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

        This is most useful when using
        :py:meth:`Maps.set_classify.UserDefined(bins=[...]) <eomaps.eomaps.Maps.set_classify>`
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
        if "format" in self._cb_kwargs:
            self.cb.set_ticks(self.cb.get_ticks())
            return

        if self._m._classified:
            unique_bins = np.unique(
                np.clip(self._m.classify_specs._bins, self._vmin, self._vmax)
            )
            if len(unique_bins) <= self.max_n_classify_bins_to_label:
                self.cb.set_ticks(unique_bins)

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

    def set_position(self, pos):
        """
        Set the position of the colorbar
        (and all colorbars that share the same location)

        Parameters
        ----------
        pos : [left, bottom, width, height] or ~matplotlib.transforms.Bbox
            The new position of the in .Figure coordinates.
        """
        self._ax.set_position(pos)
        if self._dynamic_shade_indicator is False:
            self._m.redraw(self.layer)

    def set_visible(self, vis):
        """
        Set the visibility of the colorbar.

        Parameters
        ----------
        vis : bool
            - True: colorbar visible
            - False: colorbar not visible
        """
        for ax in (self.ax_cb, self.ax_cb_plot):
            ax.set_visible(vis)

        if vis is True:
            self._hide_singular_axes()

        if self._dynamic_shade_indicator is False:
            self._m.redraw(self.layer)

    def set_labels(self, cb_label=None, hist_label=None, **kwargs):
        """
        Set the labels (and the label-style) for the colorbar (and the histogram).

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

    def set_scale(self, log=False):
        """
        Set the scale of the colorbar histogram. (e.g. logarithmic or linear)

        Parameters
        ----------
        log : bool, optional
            If True, use a logarithmic scale for the histogram.
            The default is False.

        """
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

        self._m.redraw(self.layer)

    @classmethod
    def _new_colorbar(
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
        outline=False,
        hist_kwargs=None,
        hist_label=None,
        margin=None,
        divider_linestyle=None,
        layer=None,
        **kwargs,
    ):
        """
        Add a colorbar to the map.

        The colorbar always represents the data of the associated Maps-object
        that was assigned in the last call to
        :py:meth:`Maps.plot_map() <eomaps.eomaps.Maps.plot_map>`.

        By default, the colorbar will only be visible on the layer of the associated
        Maps-object.

        After the colorbar has been created, it can be accessed via:

            >>> cb = m.colorbar

        For more details, see :py:class:`ColorBar <eomaps.colorbar.ColorBar>`.

        Parameters
        ----------
        pos : float or 4-tuple, optional

            - float: fraction of the axis size that is used to create the colorbar.
              The axes of the Maps-object will be shrunk accordingly to make space
              for the colorbar.
            - 4-tuple (x0, y0, width, height):
              Absolute position of the colorbar in relative figure-units (0-1).
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
        extend : str or None, optional
            Set how extension-arrows should be added.

            - None: extension-arrow behavior is determined by the provided dataset
              in conjunction with the limits (e.g. vmin and vmax).
            - "neither": extension arrows are never added
            - "min" or "max": only min / max extension arrows are added
            - "both": both min and max extension arrows are added

            Note: If the colorbar inherits its position from a colorbar on a different
            layer, the extend-behavior is inherited as well!

            The default is None.
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
        outline : bool or dict
            Indicator if an outline should be added to the histogram.
            (e.g. a line encompassing the histogram)
            If a dict is provided, it is passed to `plt.step()` to style the line.
            (e.g. with ordinary matplotlib parameters such as color, lw, ls etc.)
            If True, the following properties are used:

            - {"color": "k", "lw": 1}

            The default is False.
        tick_precision : int or None
            The precision of the tick-labels in the colorbar.
            (e.g. a precision of 2 means that 0.12345 will be shown as 0.12)
            The default is 2.
        log : bool, optional
            Indicator if the y-axis of the plot should be logarithmic or not.
            The default is False.
        out_of_range_vals : str or None
            Set how to treat histogram values outside the visible range of values.

            - if "mask": out-of range values will be masked.
              (e.g. values outside the colorbar limits are not represented in the
              histogram and NO extend-arrows are added)
            - if "clip": out-of-range values will be clipped.
              (e.g. values outside the colorbar limits will be represented in the
              min/max bins of the histogram)

            The default is "clip"
        label : str, optional
            The label used for the colorbar.
            Use `ColorBar.set_labels()` to set the labels (and styling) for the
            colorbar and the histogram.
            The default is None.
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
        hist_label : str, optional
            The label used for the y-axis of the colorbar. The default is None
        hist_kwargs : dict
            A dictionary with keyword-arguments passed to the creation of the histogram
            (e.g. passed to `plt.hist()` )
        layer : str
            The layer at which the colorbar will be drawn.
            NOTE: In most cases you should NOT need to adjust the layer!
            The layer is automatically assigned to the layer at which the
            data was plotted and Colorbars are only visible on the assigned layer!
        divider_linestyle : dict or None
            A dictionary that specifies the style of the line between the histogram and
            the colorbar. If None a black dashed line is drawn
            (e.g. `{"color": "k", "linestyle":"--"}`). The default is None.
        kwargs :
            All additional kwargs are passed to the creation of the colorbar
            (e.g. `plt.colorbar()`)

        See Also
        --------
        ColorBar.set_bin_labels:  Use custom names for classified colorbar bins.

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
        if "show_outline" in kwargs:
            import warnings

            warnings.simplefilter("default", DeprecationWarning)
            warnings.warn(
                "EOmaps: The colorbar argument 'show_outline' is deprecated and will "
                "be removed in EOmaps v8.1. Use 'outline' instead!",
                category=DeprecationWarning,
                stacklevel=2,
            )

            outline = kwargs.pop("show_outline")

        if "ylabel" in kwargs:
            import warnings

            warnings.simplefilter("default", DeprecationWarning)
            warnings.warn(
                "EOmaps: The colorbar argument 'ylabel' is deprecated and will "
                "be removed in EOmaps v8.1. Use 'hist_label' instead!",
                category=DeprecationWarning,
                stacklevel=2,
            )

            if hist_label is None:
                hist_label = kwargs.pop("ylabel")

        if hist_kwargs is None:
            hist_kwargs = dict()

        cb = cls(
            orientation=orientation,
            tick_precision=tick_precision,
            inherit_position=inherit_position,
            extend_frac=extend_frac,
            margin=margin,
            divider_linestyle=divider_linestyle,
            hist_size=hist_size,
            layer=layer,
        )
        cb._set_map(m)
        cb._setup_axes(pos, m.ax)
        cb._add_axes_to_layer(dynamic=dynamic_shade_indicator)

        cb.set_scale(log)
        cb._plot_colorbar(extend=extend, **kwargs)

        bins = (
            m.classify_specs._bins
            if (m._classified and hist_bins == "bins")
            else hist_bins
        )

        cb._plot_histogram(
            bins=bins,
            out_of_range_vals=out_of_range_vals,
            outline=outline,
            **hist_kwargs,
        )

        cb._set_tick_formatter()

        if label is None:
            label = m.data_specs.parameter

        cb.set_labels(cb_label=label, hist_label=hist_label)

        if dynamic_shade_indicator:
            cb._make_dynamic()

        return cb

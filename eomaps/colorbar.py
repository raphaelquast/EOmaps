"""Interactive Colorbar."""

import logging
from functools import partial, lru_cache
from itertools import cycle
from textwrap import dedent
import copy


import numpy as np

from matplotlib.gridspec import GridSpecFromSubplotSpec, SubplotSpec
import matplotlib.transforms as mtransforms
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from .helpers import pairwise, _TransformedBoundsLocator, register_modules

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


class ColorBar:
    """Class to draw colorbars with a histogram on top."""

    def __init__(
        self,
        m,
        pos=0.4,
        inherit_position=None,
        margin=None,
        hist_size=0.8,
        hist_bins=256,
        extend=None,
        extend_frac=0.025,
        orientation="horizontal",
        dynamic_shade_indicator=False,
        show_outline=False,
        tick_precision=2,
        tick_formatter=None,
        log=False,
        out_of_range_vals="clip",
        hist_kwargs=None,
        label=None,
        ylabel=None,
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
            (e.g. a precision of 2 means that 0.12345 will be shown as 0.12)
            The default is 2.
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
        label : str, optional
            The label used for the colorbar.
            Use `ColorBar.set_labels()` to set the labels (and styling) for the
            colorbar and the histogram.
            The default is None.
        ylabel : str, optional
            The label used for the y-axis of the colorbar. The default is None
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
        self._m = m
        self._pos = pos
        self._margin = margin
        self._orientation = orientation

        self._init_extend = extend
        self._extend_frac = extend_frac

        self._parent_cb = self._identify_parent_cb()

        if inherit_position is None:
            if not self._m.colorbar:
                inherit_position = True
            else:
                inherit_position = False

        self._inherit_position = inherit_position

        if hist_size is None:
            self._hist_size = 0
        else:
            self._hist_size = hist_size

        self._hist_bins = hist_bins

        if hist_kwargs is None:
            self._hist_kwargs = dict()
        else:
            self._hist_kwargs = copy.deepcopy(hist_kwargs)

        self._histogram_plotted = False  # indicator if histogram has been plotted

        self._dynamic_shade_indicator = dynamic_shade_indicator
        self._hist_label_kwargs = None

        self._show_outline = show_outline
        self._tick_precision = tick_precision
        self._tick_formatter = tick_formatter
        self._log = log
        self._out_of_range_vals = out_of_range_vals

        # kwargs["label"] = label

        self._kwargs = copy.deepcopy(kwargs)

        self._coll = self._m.coll
        self._vmin = self._coll.norm.vmin
        self._vmax = self._coll.norm.vmax

        self._classified = self._m.classify_specs._classified

        if self._hist_bins == "bins" and not self._classified:
            raise AssertionError(
                "EOmaps: Using hist_bins='bins' is only possible "
                "for classified datasets!"
            )

        self._ax = None
        self.ax_cb = None
        self.ax_cb_plot = None

        self._cid_redraw = False

        self._set_data()
        self._setup_axes()
        self.set_labels(label)
        if ylabel is not None:
            self.ax_cb_plot.set_ylabel(ylabel)

    def set_visible(self, vis):
        """
        Set the visibility of the colorbar.

        Parameters
        ----------
        vis : bool
            - True: colorbar visible
            - False: colorbar not visible
        """
        for ax in self._axes:
            if ax is self.ax_cb_plot:
                pass
            ax.set_visible(vis)

        if self._hist_size <= 0.0001:
            self.ax_cb_plot.set_visible(False)
        else:
            self.ax_cb_plot.set_visible(vis)

    def _set_labels(self, cb_label=None, hist_label=None, **kwargs):
        if self._dynamic_shade_indicator and hist_label is not None:
            # remember kwargs to re-draw the histogram
            self._hist_label_kwargs = {
                "cb_label": None,
                "hist_label": hist_label,
                **kwargs,
            }

        if self._orientation == "horizontal":
            if cb_label:
                if self._hist_size < 0.001:
                    # label colorbar
                    self.ax_cb_plot.set_xlabel("")
                    label = self.ax_cb.set_xlabel(cb_label, **kwargs)
                elif self._hist_size > 0.999:
                    # label plot
                    self.ax_cb_plot.set_xlabel(cb_label, **kwargs)
                    self.ax_cb.set_xlabel("")
                else:
                    # label colorbar
                    self.ax_cb_plot.set_xlabel("")
                    label = self.ax_cb.set_xlabel(cb_label, **kwargs)
            if hist_label:
                self._hist_label = self.ax_cb_plot.set_ylabel(hist_label, **kwargs)
        else:
            if cb_label:
                if self._hist_size < 0.001:
                    # label colorbar
                    self.ax_cb_plot.set_ylabel("")
                    label = self.ax_cb.set_ylabel(cb_label, **kwargs)
                elif self._hist_size > 0.999:
                    # label plot
                    self.ax_cb_plot.set_ylabel(cb_label, **kwargs)
                    self.ax_cb.set_xlabel("")
                else:
                    # label colorbar
                    self.ax_cb_plot.set_ylabel("")
                    label = self.ax_cb.set_ylabel(cb_label, **kwargs)

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
            self._m.redraw(self._m.layer)
        else:
            self._m.BM.update()

    @lru_cache()
    def _default_cb_tick_formatter(self, x, pos, precision=None):
        """
        A formatter to format the tick-labels of the colorbar for encoded datasets.
        (used in xaxis.set_major_formatter() )
        """
        # if precision=None the shortest representation of the number is used
        return np.format_float_positional(self._m._decode_values(x), precision)

    @lru_cache()
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
            self._hist_size = size

        if self._inherit_position:
            parent = self._get_parent_cb()
            parent.set_hist_size(size)
        else:
            # if the position is not inherited from a parent-axes, add margins
            if self._margin is None:
                if self._orientation == "horizontal":
                    self._margin = dict(left=0.1, right=0.1, bottom=0.3, top=0.0)
                else:
                    self._margin = dict(left=0.0, right=0.3, bottom=0.1, top=0.1)

            l, r = (self._margin.get(k, 0) for k in ["left", "right"])
            b, t = (self._margin.get(k, 0) for k in ["bottom", "top"])
            w, h = 1 - l - r, 1 - t - b

            if self._orientation == "horizontal":
                s = (1 - self._hist_size) * h
                cbpos = (l, b, w, s)
                histpos = (l, b + s, w, h - s)
            else:
                s = (1 - self._hist_size) * w
                cbpos = (l + w - s, b, s, h)
                histpos = (l, b, w - s, h)

            self.ax_cb_plot.set_axes_locator(
                _TransformedBoundsLocator(histpos, self._ax.transAxes)
            )
            self.ax_cb.set_axes_locator(
                _TransformedBoundsLocator(cbpos, self._ax.transAxes)
            )

        if self._hist_size > 0.0001:
            self.ax_cb_plot.set_visible(True)

            # in case the histogram has not yet been plotted, plot it!
            if not self._histogram_plotted:
                self._plot_histogram()
        else:
            self.ax_cb_plot.set_visible(False)  # to avoid singular matrix errors

        # avoid singular matrix errors caused by visible axes with 0 size
        # when activating the layout editor
        if self._hist_size > 0.999:
            self.ax_cb.set_visible(False)  # to avoid singular matrix errors
            self.ax_cb_plot.set_visible(True)
            [i.set_visible(False) for i in self.ax_cb.patches]
            [i.set_visible(False) for i in self.ax_cb.collections]
            self.ax_cb_plot.tick_params(bottom=True, labelbottom=True)
        elif self._hist_size < 0.001:
            self.ax_cb.set_visible(True)
            self.ax_cb_plot.set_visible(False)  # to avoid singular matrix errors
            [i.set_visible(True) for i in self.ax_cb.patches]
            [i.set_visible(True) for i in self.ax_cb.collections]
        else:
            self.ax_cb.set_visible(True)
            self.ax_cb_plot.set_visible(True)
            self.ax_cb_plot.tick_params(bottom=False, labelbottom=False)
            [i.set_visible(True) for i in self.ax_cb.patches]
            [i.set_visible(True) for i in self.ax_cb.collections]

        self.set_labels(**self._label_kwargs)
        # tag layer for refetch
        self._m.redraw(self._m.layer)

    def _identify_parent_cb(self):
        parent_cb = None
        # check if there is already an existing colorbar for a Maps-object that shares
        # the same plot-axis.
        # If yes, use the position of this colorbar to creat a new one

        if self._m.colorbar is not None:
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
        if parent_cb and parent_cb._orientation == self._orientation:
            return parent_cb
        else:
            return None

    def _get_parent_cb(self):
        if self._parent_cb is None:
            return self
        else:
            parent = self
            while parent._parent_cb is not None:
                parent = parent._parent_cb

            return parent

    def _setup_axes(self):
        zorder = 9999

        horizontal = self._orientation == "horizontal"
        hide_hist = self._hist_size < 0.0001
        hide_axes = self._hist_size > 0.999
        # check if one of the parent colorbars has a colorbar, and if so,
        # use it to set the position of the colorbar.
        if self._inherit_position:
            if self._parent_cb is not None:

                try:
                    parent_subplotspec = self._parent_cb._ax.get_subplotspec()
                except AttributeError:
                    parent_subplotspec = None

                if parent_subplotspec is not None:
                    self._ax = self._m.f.add_subplot(
                        parent_subplotspec,
                        label="cb",
                        zorder=zorder,
                    )
                else:
                    self._ax = self._m.f.add_axes(
                        self._parent_cb._ax.get_position(),
                        label="cb",
                        zorder=zorder,
                    )

                parent_extend = getattr(
                    self._parent_cb, "_extend", self._parent_cb._init_extend
                )

                if parent_extend is None:
                    try:
                        self._parent_cb._set_extend()
                        parent_extend = getattr(
                            self._parent_cb, "_extend", self._parent_cb._init_extend
                        )

                    except Exception:
                        _log.exception(
                            "EOmaps: unable to determine automatic extension arrow"
                            "size of parent colorbar."
                        )

                # inherit axis-position from the parent axis position
                # (e.g. it can no longer be freely moved... its position is determined
                # by the position of the parent-colorbar axis)
                self._ax.set_axes_locator(
                    _TransformedBoundsLocator(
                        (0, 0, 1, 1), self._parent_cb._ax.transAxes
                    )
                )

            else:
                self._inherit_position = False

        if not self._inherit_position:
            if isinstance(self._pos, float):
                if horizontal:
                    gs = GridSpecFromSubplotSpec(
                        2,
                        1,
                        self._m.ax.get_subplotspec(),
                        height_ratios=(1, self._pos),
                    )

                    self._m.ax.set_subplotspec(gs[0, 0])
                    self._ax = self._m.f.add_subplot(
                        gs[1, 0],
                        label="cb",
                        zorder=zorder,
                    )
                else:
                    gs = GridSpecFromSubplotSpec(
                        1,
                        2,
                        self._m.ax.get_subplotspec(),
                        width_ratios=(1, self._pos),
                    )

                    self._m.ax.set_subplotspec(gs[0, 0])
                    self._ax = self._m.f.add_subplot(
                        gs[0, 1],
                        label="cb",
                        zorder=zorder,
                    )
            elif isinstance(self._pos, SubplotSpec):
                self._ax = self._m.f.add_subplot(
                    self._pos,
                    label="cb",
                    zorder=zorder,
                )
            elif isinstance(self._pos, (list, tuple)):
                x0, y0, w, h = self._pos
                x1 = x0 + w
                y1 = y0 + h
                bbox = mtransforms.Bbox(((x0, y0), (x1, y1)))

                # the parent axes holding the 2 child-axes
                self._ax = plt.Axes(self._m.f, bbox, label="cb", zorder=zorder)
                self._m.f.add_axes(self._ax)

        # make all spines, labels etc. invisible for the base-axis
        self._ax.set_axis_off()

        # colorbar axes
        self.ax_cb = self._ax.figure.add_axes(
            self._ax.get_position(),
            label="EOmaps_cb",
            zorder=zorder - 1,  # make zorder 1 lower than container axes for picking
        )

        # histogram axes
        self.ax_cb_plot = self._ax.figure.add_axes(
            self._ax.get_position(),
            label="EOmaps_cb_hist",
            zorder=zorder - 1,  # make zorder 1 lower than container axes for picking
        )
        # hide histogram and coorbar axes if they are 0 size
        if hide_axes:
            self.ax_cb.set_visible(False)
        if hide_hist:
            self.ax_cb_plot.set_visible(False)

        if self._inherit_position:
            # handle axis size in case parent colorbar has extension arrows
            if parent_extend in ["min", "both", None]:
                padx = -self._parent_cb._extend_frac
            else:
                padx = 0
            if parent_extend in ["max", "both", None]:
                pady = -self._parent_cb._extend_frac
            else:
                pady = 0

            if self._orientation == "horizontal":
                size = (padx, 0, 1 - padx - pady, 1)
            else:
                size = (0, padx, 1, 1 - padx - pady)

            # in case the position is inherited, copy the locators from the parent!
            self.ax_cb_plot.set_axes_locator(
                _TransformedBoundsLocator(
                    (0, 0, 1, 1), self._parent_cb.ax_cb_plot.transAxes
                )
            )
            self.ax_cb.set_axes_locator(
                _TransformedBoundsLocator(size, self._parent_cb.ax_cb.transAxes)
            )

        # join colorbar and histogram axes
        if horizontal:
            self.ax_cb_plot.sharex(self.ax_cb)
        else:
            self.ax_cb_plot.sharey(self.ax_cb)

        # keep the background of the plot-axis but remove the outer frame
        self.ax_cb_plot.spines["top"].set_visible(False)
        self.ax_cb_plot.spines["right"].set_visible(False)
        self.ax_cb_plot.spines["bottom"].set_visible(False)
        self.ax_cb_plot.spines["left"].set_visible(False)

        # set axis scale
        if horizontal:
            if self._log is True:
                self.ax_cb_plot.set_yscale("log")
            else:
                self.ax_cb_plot.set_yscale("linear")
        else:
            if self._log is True:
                self.ax_cb_plot.set_xscale("log")
            else:
                self.ax_cb_plot.set_xscale("linear")

        # add all axes as artists
        for a in self._axes:
            a.set_navigate(False)
            if a is not None:
                if self._dynamic_shade_indicator is True:
                    self._m.BM.add_artist(a, self._m.layer)
                else:
                    self._m.BM.add_bg_artist(a, self._m.layer)

        # we need to re-draw since the background axis size has changed!
        self._m.BM._refetch_layer(self._m.layer)
        self._m.BM._refetch_layer("__SPINES__")
        self._m.redraw("__SPINES__")

    @property
    def _axes(self):
        return (self._ax, self.ax_cb, self.ax_cb_plot)

    def _set_extend(self, z_data):
        if self._inherit_position and self._parent_cb is not None:
            self._extend = self._parent_cb._extend
            # warn if provided extend behavior differs from the inherited behavior
            if self._extend != self._init_extend:
                _log.warning(
                    f"EOmaps Warning: m.add_colorbar(extend='{self._extend}') is "
                    "inherited from the parent colorbar! Explicitly set the 'extend' "
                    "behavior to silence this warning."
                )
            if self._extend is not None:
                return

        if self._init_extend is not None:
            self._extend = self._init_extend
        else:
            extend = "neither"
            if (z_data > self._vmax).any():
                extend = "max"
            if (z_data < self._vmin).any():
                if extend == "max":
                    extend = "both"
                else:
                    extend = "min"

            self._extend = extend

    def _set_data(self):
        renorm = False

        dynamic_shade = False
        if self._dynamic_shade_indicator:
            ds, mpl_ext = register_modules("datashader", "datashader.mpl_ext")

            if all((ds, mpl_ext)) and isinstance(self._coll, mpl_ext.ScalarDSArtist):
                dynamic_shade = True
            else:
                _log.error(
                    "EOmaps: Using 'dynamic_shade_indicator=True' is only possible "
                    "with 'shade' shapes (e.g. 'shade_raster' or 'shade_points'.\n"
                    "... creating a normal colorbar instead."
                )
                self._dynamic_shade_indicator = False

        if dynamic_shade:
            aggname = self._m.shape.aggregator.__class__.__name__
            if aggname in ["first", "last", "max", "min", "mean", "mode"]:
                pass
            else:
                renorm = True
                # TODO check this without requiring import of datashader!
                # _log.error(
                #     "EOmaps: Only dynamic colorbars are possible when using"
                #     + f" '{aggname}' as datashader-aggregation reduction method "
                #     + "...creating a 'dynamic_shade_indicator' colorbar instead."
                # )
                # self._dynamic_shade_indicator = True

            try:
                z_data = self._coll.get_ds_data().values
            except:
                self._m.redraw(self._m.layer)
                z_data = self._coll.get_ds_data().values

            if "count" in aggname:
                # make sure we don't count empty pixels
                z_data = z_data[~(z_data == 0)]

            # datashader sets None to 0 by default!
            # z_data = z_data[z_data > 0]

            bins = self._m.classify_specs._bins
            cmap = self._m.classify_specs._cbcmap

            if renorm:
                z_data = z_data[~np.isnan(z_data)]
                norm = self._coll.norm
                # make sure the norm clips with respect to vmin/vmax
                # (only clip if either vmin or vmax is not None)
                # if vmin or vmax:
                #     z_data = z_data.clip(vmin, vmax)
                cmap = self._coll.get_cmap()
            else:
                norm = self._m.classify_specs._norm

            if self._cid_redraw is False:
                # TODO check why this no longer triggers on data-updates...
                # self._m.coll.add_callback(self._redraw_colorbar)

                def check_data_updated(*args, **kwargs):
                    # make sure the artist is drawn before checking for new data
                    self._m.f.draw_artist(self._m.coll)
                    dsdata = self._m.coll.get_ds_data()
                    if getattr(self, "_last_ds_data", None) is not None:
                        if not self._last_ds_data.equals(dsdata):
                            # if the data has changed, redraw the colorbar
                            self._redraw_colorbar()
                    self._last_ds_data = dsdata

                self._m.BM._before_fetch_bg_actions.append(check_data_updated)

                self._m.BM.on_layer(
                    lambda *args, **kwargs: self._redraw_colorbar,
                    layer=self._m.layer,
                    persistent=True,
                )

                self._cid_redraw = True

                # TODO colorbar not properly updated on layer change after zoom?
                self._m.BM.on_layer(
                    self._redraw_colorbar,
                    layer=self._m.layer,
                    persistent=True,
                    m=self._m,
                )
        else:

            z_data = self._m._data_manager.z_data
            bins = self._m.classify_specs._bins
            cmap = self._m.classify_specs._cbcmap
            norm = self._m.classify_specs._norm

        if isinstance(z_data, np.ma.masked_array):
            z_data = z_data.compressed()
        else:
            z_data = z_data.ravel()

        # make sure we only consider valid values in the histogram
        z_data = z_data[np.isfinite(z_data)]

        self._set_extend(z_data)

        if self._out_of_range_vals == "mask":
            z_data = z_data[(z_data >= self._vmin) & (z_data <= self._vmax)]

        # make sure the norm clips with respect to vmin/vmax
        # (only clip if either vmin or vmax is not None)
        if self._out_of_range_vals == "clip":
            if self._vmin or self._vmax:
                z_data = z_data.clip(self._vmin, self._vmax)

        self._z_data = z_data
        self._bins = bins
        self._cmap = cmap
        # TODO check if copy is really necessary
        # (especially for dynamic datashader colorbars!)
        self._norm = copy.deepcopy(norm)
        # make sure boundaries are clipped with respect to vmin and vmax
        # to avoid issues with vmin/vmax in-between colorbar-boundaries

        if hasattr(self._norm, "boundaries"):
            self._norm.boundaries = np.clip(
                self._norm.boundaries, self._vmin, self._vmax
            )

    def _plot_colorbar(self):
        # plot the colorbar
        horizontal = self._orientation == "horizontal"
        n_cmap = plt.cm.ScalarMappable(cmap=self._cmap, norm=self._norm)

        # avoid using "plt.colorbar" since it might not properly recognize
        # the associated figure (e.g. plt.gcf() might point somewhere else)!
        self.cb = self._m.f.colorbar(
            n_cmap,
            cax=self.ax_cb,
            extend=self._extend,
            extendfrac=self._extend_frac,
            spacing="proportional",
            orientation=self._orientation,
            **self._kwargs,
        )

        self.cb.outline.set_visible(False)

        # ensure that ticklabels are correct if a classification is used
        if self._classified and "ticks" not in self._kwargs:
            self.cb.set_ticks(np.unique(np.clip(self._bins, self._vmin, self._vmax)))

            if self._tick_formatter is None:
                self._tick_formatter = self._classified_cb_tick_formatter
        else:
            self.cb.set_ticks(self.cb.get_ticks())

        if self._tick_formatter is None:
            tick_formatter = partial(
                self._default_cb_tick_formatter, precision=self._tick_precision
            )
        else:
            tick_formatter = self._tick_formatter

        if horizontal:
            self.ax_cb.xaxis.set_major_formatter(tick_formatter)
        else:
            self.ax_cb.yaxis.set_major_formatter(tick_formatter)

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

        if self._vmin != self._vmax:
            limsetfunc(self._vmin, self._vmax)
        else:
            _log.error(
                "EOMaps-Warning: Attempting to set identical upper and "
                + "lower limits for the colorbar... limits will be ignored!"
            )

        # set the axis_locator to set relative axis positions
        # TODO check why colorbar axis size changes after plot!
        # (e.g. this needs to be called AFTER plotting the colorbar to make sure
        # the extension-arrows are properly aligned)
        self.set_hist_size()

    def _plot_histogram(self):
        if self._hist_size <= 0.0001:
            return

        horizontal = self._orientation == "horizontal"
        n_cmap = plt.cm.ScalarMappable(cmap=self._cmap, norm=self._norm)

        # plot the histogram
        h = self.ax_cb_plot.hist(
            self._z_data,
            orientation="vertical" if horizontal else "horizontal",
            bins=self._bins
            if (self._classified and self._hist_bins == "bins")
            else self._hist_bins,
            color="k",
            align="mid",
            range=(self._vmin, self._vmax) if (self._vmin and self._vmax) else None,
            **self._hist_kwargs,
        )

        if self._show_outline:
            if self._show_outline is True:
                outline_props = dict(color="k", lw=1)
            else:
                outline_props = self._show_outline

            if horizontal:
                self.ax_cb_plot.step(h[1], [h[0][0], *h[0]], **outline_props)
            else:
                self.ax_cb_plot.step([h[0][0], *h[0]], h[1], **outline_props)

        if self._bins is None:
            # identify position of color-splits in the colorbar
            if isinstance(n_cmap.cmap, LinearSegmentedColormap):
                # for LinearSegmentedcolormap N is the number of quantizations!
                splitpos = np.linspace(self._vmin, self._vmax, n_cmap.cmap.N)
            else:
                # for ListedColormap N is the number of colors
                splitpos = np.linspace(self._vmin, self._vmax, n_cmap.cmap.N + 1)
        else:
            splitpos = np.asanyarray(self._bins)

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
                            facecolor=self._cmap(self._norm((b0 + b1) / 2)),
                        )
                    else:
                        pi = mpl.patches.Rectangle(
                            (0, b0),
                            width,
                            (b1 - b0),
                            facecolor=self._cmap(self._norm((b0 + b1) / 2)),
                        )

                    self.ax_cb_plot.add_patch(pi)
            else:
                patch.set_facecolor(self._cmap(self._norm((minval + maxval) / 2)))

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
            if self._log is False:
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
            if self._log is False:
                # self.ax_cb_plot.xaxis.set_major_locator(plt.MaxNLocator(5))
                self.ax_cb_plot.set_xlim(None, 0)

        self._histogram_plotted = True

    def _redraw_colorbar(self, *args, **kwargs):
        # only re-draw if the corresponding layer is visible
        if self._m.layer not in self._m.BM.bg_layer.split("|"):
            return

        self._set_data()
        self.ax_cb_plot.clear()
        self._plot_histogram()

        # if self._hist_label_kwargs:
        #     self._set_labels(**self._hist_label_kwargs)

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

        horizontal = self._orientation == "horizontal"

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

        self._m.BM._refetch_layer(self._m.layer)

    def remove(self):
        """
        Remove the colorbar from the map.
        """
        for ax in (self._ax, self.ax_cb, self.ax_cb_plot):
            ax.clear()
            ax.remove()
            if self._dynamic_shade_indicator:
                self._m.BM.remove_artist(ax)
            else:
                self._m.BM.remove_bg_artist(ax)
        if self in self._m._colorbars:
            self._m._colorbars.pop(self._m._colorbars.index(self))

    def set_position(self, pos):
        """
        Set the position of the colorbar
        (and all colorbars that share the same location)

        Parameters
        ----------
        pos : [left, bottom, width, height] or ~matplotlib.transforms.Bbox
            The new position of the in .Figure coordinates.
        """
        self._get_parent_cb()._ax.set_position(pos)

    # @wraps(plt.Axes.tick_params)
    def tick_params(self, what="colorbar", **kwargs):
        """Set the appearance of the colorbar (or histogram) ticks."""
        if what == "colorbar":
            self.ax_cb.tick_params(**kwargs)
        elif what == "histogram":
            self.ax_cb_plot.tick_params(**kwargs)

        self._m.redraw(self._m.layer)

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

        self._m.redraw(self._m.layer)

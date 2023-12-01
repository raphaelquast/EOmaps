"""a collection of useful helper-functions."""

import logging
from itertools import tee
import re
import sys
from itertools import chain
from contextlib import contextmanager, ExitStack
from importlib import import_module
from textwrap import indent, dedent
from functools import wraps, lru_cache
from pathlib import Path
import json
import warnings
from weakref import WeakSet

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.transforms import Bbox, TransformedBbox
from matplotlib.axis import XAxis, YAxis
from matplotlib.spines import Spine

_log = logging.getLogger(__name__)


from matplotlib.backend_bases import KeyEvent


def _key_release_event(canvas, key, guiEvent=None):
    # copy of depreciated matplotlib functions for internal use
    s = "key_release_event"
    event = KeyEvent(s, canvas, key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)
    canvas._key = None


def _deprecated(message):
    def deprecated_decorator(func):
        def deprecated_func(*args, **kwargs):
            warnings.warn(
                f"EOmaps: '{func.__name__}' is deprecated and will be removed "
                f"in upcoming releases. {message}",
                category=DeprecationWarning,
                stacklevel=2,
            )
            warnings.simplefilter("default", DeprecationWarning)

            return func(*args, **kwargs)

        return deprecated_func

    return deprecated_decorator


@lru_cache()
def _do_import_module(name):
    return import_module(name)


def register_modules(*names, raise_exception=True):
    """Lazy-loading for optional dependencies."""
    modules = []
    for name in names:
        try:
            modules.append(_do_import_module(name))
        except ImportError as ex:
            if raise_exception:
                raise ImportError(
                    f"EOmaps: Missing required dependency: {name} \n {ex}"
                )
            else:
                modules.append(None)
    return modules


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
        return TransformedBbox(
            Bbox.from_bounds(*self._bounds),
            self._transform - ax.figure.transSubfigure,
        )


def pairwise(iterable, pairs=2):
    """
    a generator to return n consecutive values from an iterable.

        pairs = 2
        s -> (s0,s1), (s1,s2), (s2, s3), ...

        pairs = 3
        s -> (s0, s1, s2), (s1, s2, s3), (s2, s3, s4), ...

    adapted from https://docs.python.org/3.7/library/itertools.html
    """
    x = tee(iterable, pairs)
    for n, n_iter in enumerate(x[1:]):
        [next(n_iter, None) for i in range(n + 1)]
    return zip(*x)


def _sanitize(s, prefix="layer_"):
    # taken from https://stackoverflow.com/a/3303361/9703451
    s = str(s)
    # Remove leading characters until we find a letter or underscore
    s2 = re.sub("^[^a-zA-Z_]+", "", s)
    if len(s2) == 0:
        s2 = _sanitize(prefix + str(s))
    # replace invalid characters with an underscore
    s = re.sub("[^0-9a-zA-Z_]", "_", s2)
    return s


def cmap_alpha(cmap, alpha, interpolate=False, name="new_cmap"):
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
    name : str
        the name of the new colormap
        The default is "new_cmap"
    Returns
    -------
    new_cmap : matplotlib.colormap
        a new colormap with the desired transparency
    """
    cmap = plt.get_cmap(cmap)
    new_cmap = cmap(np.arange(cmap.N))
    new_cmap[:, -1] = alpha

    if interpolate:
        new_cmap = LinearSegmentedColormap(name, new_cmap)
    else:
        new_cmap = ListedColormap(new_cmap, name=name)

    return new_cmap


# a simple progressbar
# taken from https://stackoverflow.com/a/34482761/9703451
def progressbar(it, prefix="", size=60, file=sys.stdout):
    """
    A (very) simple progressbar generator.

    Parameters
    ----------
    it : iter
        The iterator for which a progressbr should be shown.
    prefix : str, optional
        Prefix for the output. The default is "".
    size : int, optional
        The size of the progressbar (in characters). The default is 60.
    file : filehandle, optional
        The file-handle to write to. The default is sys.stdout.

    Yields
    ------
    item :
        Consecutive items from the iterator.

    """
    count = len(it)

    def show(j):
        x = int(size * j / count)
        file.write("\r%s[%s%s] %i/%i\r" % (prefix, "#" * x, "." * (size - x), j, count))
        file.flush()

    show(0)
    for i, item in enumerate(it):
        yield item
        show(i + 1)
    file.write("\n")
    file.flush()


def _add_to_docstring(prefix=None, suffix=None, insert=None):
    """
    Add text to an existing docstring

    Parameters
    ----------
    prefix : str, optional
        A string appended as prefix to the existing docstring.
        The default is None.
    suffix : str, optional
        A string appended as suffix to the existing docstring.
        The default is None.
    insert : dict, optional
        Search for the provided keys and insert the values at the next line.

        If values are tuples, they are interpreted as:
        (string, line-offset) where `line-offset` represents an offset added
        to the line at which key was found.

        The default is None.
    """

    def decorator(f):
        doc = f.__doc__

        try:

            @wraps(f)
            def inner(*args, **kwargs):
                return f(*args, **kwargs)

            if insert is not None:
                for searchstr, val in insert.items():
                    if isinstance(val, str):
                        offset = 0
                    else:
                        val, offset = val

                    try:
                        docsplit = dedent(f.__doc__).split("\n")
                        paramline = docsplit.index(searchstr) + 1
                        docsplit = f.__doc__.split("\n")

                        # count number of leading spaces
                        nspaces = len(docsplit[paramline]) - len(
                            docsplit[paramline].lstrip(" ")
                        )

                        docsplit = (
                            docsplit[: (paramline + offset)]
                            + indent(val, " " * nspaces).split("\n")
                            + docsplit[(paramline + offset) :]
                        )
                        doc = "\n".join(docsplit)
                    except ValueError:
                        _log.debug(
                            f"EOmaps: Unable to update docstring for {f.__name__}"
                        )

            if prefix is not None:
                doc = prefix + "\n" + doc
            if suffix is not None:
                doc = doc + "\n" + suffix

            inner.__doc__ = doc
            return inner
        except Exception:
            _log.debug(f"EOmaps: Unable to update docstring for {f.__name__}")
            return f

    return decorator


class SearchTree:
    """Class to perform fast nearest-neighbour queries."""

    def __init__(self, m):
        """
        Class to perform fast nearest-neighbour queries.

        Parameters
        ----------
        m : eomaps.Maps
            The maps-object that provides the data.
        """
        self._m = m
        # set starting pick-distance to 50 times the radius
        self.set_search_radius(self._m.cb.pick._search_radius)

    @property
    def d(self):
        """Side-length of the search-rectangle (in units of the plot-crs)."""
        return self._d

    def set_search_radius(self, r):
        """
        Set the rectangle side-length that is used to limit the query.

        (e.g. only points that are within a rectangle of the specified size
         centered at the clicked point are considered!)

        Parameters
        ----------
        r : int, float or str, optional
            Set the radius of the (circular) area that is used to limit the
            number of pixels when searching for nearest-neighbours.

            - if `int` or `float`:
              The radius of the circle in units of the plot_crs
            - if `str`:
              A multiplication-factor for the estimated pixel-radius.
              (e.g. a circle with (`r=search_radius * m.shape.radius`) is
              used if possible and else np.inf is used.

            The default is "50" (e.g. 50 times the pixel-radius).

        """
        self._search_radius = r
        if isinstance(r, str):
            # evaluate an appropriate pick-distance
            if getattr(self._m.shape, "radius_crs", None) == "out":
                radius = self._m.shape.radius
            else:
                try:
                    if self._m.get_crs("in") == self._m.get_crs(self._m._crs_plot):
                        radius = self._m.shape.radius
                    else:
                        radius = self._m.set_shape._estimate_radius(
                            self._m, "out", np.max
                        )
                except AssertionError:
                    _log.error(
                        "EOmaps: Unable to estimate search-radius based on data."
                        "Defaulting to `np.inf`. "
                        "See `m.cb.pick.set_props(search_radius=...)` for more details!"
                    )
                    radius = [np.inf]

            self._d = np.max(radius) * float(self._search_radius)
        elif isinstance(r, (int, float, np.number)):
            self._d = float(r)
        else:
            raise TypeError(
                f"EOmaps: {r} is not a valid search-radius. "
                "The search-radius must be provided as "
                "int, float or as string that can be identified "
                "as float!"
            )

    def _identify_search_subset(self, x, d):
        # select a rectangle around the pick-coordinates
        # (provides tremendous speedups for very large datasets)

        if self._m._data_manager.x0_1D is not None:
            # TODO check this!
            # get a rectangular boolean mask
            mx = np.logical_and(
                self._m._data_manager.x0_1D > (x[0] - d),
                self._m._data_manager.x0_1D < (x[0] + d),
            )
            my = np.logical_and(
                self._m._data_manager.y0_1D > (x[1] - d),
                self._m._data_manager.y0_1D < (x[1] + d),
            )

            mx_id, my_id = np.where(mx)[0], np.where(my)[0]
            m_rect_x, m_rect_y = np.meshgrid(mx_id, my_id)

            x_rect = self._m._data_manager.x0[m_rect_x].ravel()
            y_rect = self._m._data_manager.y0[m_rect_y].ravel()

            # get the unravelled indexes of the boolean mask
            idx = np.ravel_multi_index((m_rect_x, m_rect_y), self._m._zshape).ravel()
        else:
            # get a rectangular boolean mask
            mx = np.logical_and(
                self._m._data_manager.x0 > (x[0] - d),
                self._m._data_manager.x0 < (x[0] + d),
            )
            my = np.logical_and(
                self._m._data_manager.y0 > (x[1] - d),
                self._m._data_manager.y0 < (x[1] + d),
            )

            m = np.logical_and(mx, my)
            # get the indexes of the search-rectangle
            idx = np.where(m.ravel())[0]

            if len(idx) > 0:
                x_rect = self._m._data_manager.x0[m].ravel()
                y_rect = self._m._data_manager.y0[m].ravel()
            else:
                x_rect, y_rect = [], []

        if len(x_rect) > 0 and len(y_rect) > 0:
            mcircle = (x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2 < d**2
            return x_rect[mcircle], y_rect[mcircle], idx[mcircle]
        else:
            return [], [], []

    def query(self, x, k=1, d=None, pick_relative_to_closest=True):
        """
        Find the (k) closest points.

        Parameters
        ----------
        x : list, tuple or np.array of length 2
            The x- and y- coordinates to search.
        k : int, optional
            The number of points to identify.
            The default is 1.
        d : float, optional
            The max. distance (in plot-crs) to consider when identifying points.
            If None, the currently assigned distance (e.g. `m.tree.d`) is used.
            (see `m.tree.set_search_radius` on how to set the default distance!)
            The default is None.
        pick_relative_to_closest : bool, optional
            ONLY relevant if `k > 1`.

            - If True: pick (k) nearest neighbours based on the center of the
              closest point
            - If False: pick (k) nearest neighbours based on the click-position

            The default is True.

        Returns
        -------
        i : list
            The indexes of the selected datapoints with respect to the
            flattened array.
        """
        if d is None:
            d = self.d
        i = None
        # take care of 1D coordinates and 2D data
        if self._m._data_manager.x0_1D is not None:
            if k > 1 and pick_relative_to_closest is True:
                ix = np.argmin(np.abs(self._m._data_manager.x0_1D - x[0]))
                iy = np.argmin(np.abs(self._m._data_manager.y0_1D - x[1]))
                # query again (starting from the closest point)
                return self.query(
                    (self._m._data_manager.x0_1D[ix], self._m._data_manager.y0_1D[iy]),
                    k=k,
                    d=d,
                    pick_relative_to_closest=False,
                )
            else:

                # perform a brute-force search for 1D coords
                ix = np.argpartition(
                    np.abs(self._m._data_manager.x0_1D - x[0]), range(k)
                )[:k]
                iy = np.argpartition(
                    np.abs(self._m._data_manager.y0_1D - x[1]), range(k)
                )[:k]

                if k > 1:
                    # select a circle within the kxk rectangle
                    ix, iy = np.meshgrid(ix, iy)

                    idx = np.ravel_multi_index(
                        (iy, ix),
                        (
                            self._m._data_manager.y0_1D.size,
                            self._m._data_manager.x0_1D.size,
                        ),
                    ).ravel()

                    x_rect, y_rect = (
                        i.ravel()
                        for i in (
                            self._m._data_manager.x0_1D[ix],
                            self._m._data_manager.y0_1D[iy],
                        )
                    )

                    i = idx[
                        ((x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2).argpartition(
                            range(int(min(k, x_rect.size)))
                        )[:k]
                    ]

                else:
                    ix = np.argmin(np.abs(self._m._data_manager.x0_1D - x[0]))
                    iy = np.argmin(np.abs(self._m._data_manager.y0_1D - x[1]))

                    # TODO check treatment of transposed data in here!
                    i = np.ravel_multi_index(
                        (iy, ix),
                        (
                            self._m._data_manager.y0_1D.size,
                            self._m._data_manager.x0_1D.size,
                        ),
                    )

                return i

        x_rect, y_rect, idx = self._identify_search_subset(x, d)
        if len(idx) > 0:

            if k == 1:
                i = idx[((x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2).argmin()]
            else:
                if pick_relative_to_closest is True:
                    i0 = ((x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2).argmin()

                    return self.query(
                        (x_rect[i0], y_rect[i0]),
                        k=k,
                        d=d,
                        pick_relative_to_closest=False,
                    )
                i = idx[
                    ((x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2).argpartition(
                        range(min(k, x_rect.size))
                    )[:k]
                ]
        else:
            i = None

        return i


class LayoutEditor:
    """Class to handle interactive re-positioning of figure-objects."""

    def __init__(self, m, modifier="alt+d", cb_modifier="control"):
        self.modifier = modifier
        self.cb_modifier = cb_modifier

        self.m = m
        self.f = self.m.parent.f

        self._ax_picked = []
        self._m_picked = []
        self._cb_picked = []

        self._modifier_pressed = False

        self.cids = []

        # indicator if the pick-callback should be re-attached or not
        self._reattach_pick_cb = False

        self.f.canvas.mpl_connect("key_press_event", self.cb_key_press)
        self.f.canvas.mpl_connect("resize_event", self._on_resize)

        # the snap-to-grid interval (0 means no snapping)
        self._snap_id = 5

        # an optional filepath that will be used to store the layout once the
        # editor exits
        self._filepath = None

        # indicator if scaling should be in horizontal or vertical direction
        self._scale_direction = "both"

        # indicator if multiple-axis select key is pressed or not (e.g. "shift")
        self._shift_pressed = False

        self._max_hist_steps = 1000
        self._history = list()
        self._history_undone = list()

        self._current_bg = None

        self._info_text = None
        self._info_text_hidden = False

    def add_info_text(self):
        self._info_text_hidden = False

        a = self.m.f.text(
            0.72,
            0.98,
            (
                "LayoutEditor Controls:\n\n"
                "0 - 9:  Snap-grid spacing\n"
                "SHIFT:  Multi-select\n"
                "P:      Print to console\n"
                "ESCAPE (or ALT + L): Exit\n"
                "\n"
                "ARROW-KEYS:   Move\n"
                "SCROLL (+/-): Resize\n"
                "  H:    horizontal\n"
                "  V:    vertical\n"
                "  ctrl: histogram"
                "\n\n(right-click to hide info)"
            ),
            transform=self.m.f.transFigure,
            ha="left",
            va="top",
            fontsize=min(self.m.f.bbox.width * 72 / self.m.f.dpi / 60, 12),
            bbox=dict(
                boxstyle="round", facecolor=".8", edgecolor="k", lw=0.5, alpha=0.9
            ),
            zorder=1e6,
            fontfamily="monospace",
        )
        return a

    def _update_info_text(self):
        if getattr(self, "_info_text", None) is not None:
            self._info_text.set_fontsize(
                min(self.m.f.bbox.width * 72 / self.m.f.dpi / 60, 15)
            )

    def _on_resize(self, *args, **kwargs):
        # update snap-grid on resize
        if self.modifier_pressed:
            self._add_snap_grid()
            self._update_info_text()

    @property
    def modifier_pressed(self):
        return self._modifier_pressed

    @modifier_pressed.setter
    def modifier_pressed(self, val):
        self._modifier_pressed = val
        self.m.cb.execute_callbacks(not val)

        if self._modifier_pressed:
            self.m.BM._disable_draw = True
            self.m.BM._disable_update = True
        else:
            self.m.BM._disable_draw = False
            self.m.BM._disable_update = False

    @property
    def ms(self):
        return [self.m.parent, *self.m.parent._children]

    @property
    def maxes(self):
        return [m.ax for m in self.ms]

    @property
    def cbaxes(self):
        axes = list()
        for m in self.ms:
            axes.extend((i._ax for i in m._colorbars))
        return axes

    @property
    def axes(self):
        return self.f.axes

    @property
    def cbs(self):
        # get all colorbars
        cbs = list()
        for m in self.ms:
            cbs.extend(m._colorbars)
        return cbs

    @staticmethod
    def roundto(x, base=10):
        if base == 0:
            return x
        if x % base <= base / 2:
            return x - x % base
        else:
            return x + (base - x % base)

    def _get_move_with_key_bbox(self, ax, key):
        snapx, snapy = self._snap
        intervalx, intervaly = (
            max(0.25, snapx),
            max(0.25, snapy),
        )

        if key == "left":
            bbox = Bbox.from_bounds(
                self.roundto(ax.bbox.x0 - intervalx, snapx),
                ax.bbox.y0,
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "right":
            bbox = Bbox.from_bounds(
                self.roundto(ax.bbox.x0 + intervalx, snapx),
                ax.bbox.y0,
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "up":
            bbox = Bbox.from_bounds(
                ax.bbox.x0,
                self.roundto(ax.bbox.y0 + intervaly, snapy),
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "down":
            bbox = Bbox.from_bounds(
                ax.bbox.x0,
                self.roundto(ax.bbox.y0 - intervaly, snapy),
                ax.bbox.width,
                ax.bbox.height,
            )

        bbox = bbox.transformed(self.f.transFigure.inverted())
        return bbox

    def _get_move_bbox(self, ax, x, y):
        w, h = ax.bbox.width, ax.bbox.height
        x0, y0 = (
            self._start_ax_position[ax][0] + (x - self._start_position[0]),
            self._start_ax_position[ax][1] + (y - self._start_position[1]),
        )

        if self._snap_id > 0:
            sx, sy = self._snap
            x0 = self.roundto(x0, sx)
            y0 = self.roundto(y0, sy)

        bbox = Bbox.from_bounds(x0, y0, w, h).transformed(self.f.transFigure.inverted())

        return bbox

    def _get_resize_bbox(self, ax, step):
        origw, origh = ax.bbox.width, ax.bbox.height
        x0, y0 = ax.bbox.x0, ax.bbox.y0

        sx, sy = self._snap

        h, w = origh, origw

        if self._scale_direction == "horizontal":
            w += max(0.25, sx) * step
            w = self.roundto(w, sx)
        elif self._scale_direction == "vertical":
            h += max(0.25, sy) * step
            h = self.roundto(h, sy)
        else:
            w += max(0.25, sx) * step
            w = self.roundto(w, sx)

            h += max(0.25, sy) * step
            h = self.roundto(h, sy)

        if h <= 0 or w <= 0:
            return

        # x0 = self.roundto(x0, sx)
        # y0 = self.roundto(y0, sy)

        # keep the center-position of the scaled axis
        x0 = x0 + (origw - w) / 2
        y0 = y0 + (origh - h) / 2

        bbox = Bbox.from_bounds(x0, y0, w, h).transformed(self.f.transFigure.inverted())

        if bbox.width <= 0 or bbox.height <= 0:
            return

        return bbox

    def _color_unpicked(self, ax):
        for spine in ax.spines.values():
            spine.set_edgecolor("b")
            spine._EOmaps_linestyle = spine.get_linestyle()
            spine.set_linestyle("-")
            spine.set_linewidth(1)

    def _color_picked(self, ax):
        for spine in ax.spines.values():
            spine.set_edgecolor("r")
            spine.set_linestyle("-")
            spine.set_linewidth(2)

    def _color_axes(self):
        for ax in self.axes:
            self._color_unpicked(ax)

        for cb in self.cbs:
            for ax in (cb.ax_cb, cb.ax_cb_plot):
                self._color_unpicked(ax)

        for ax in self._ax_picked:
            if ax is not None:
                self._color_picked(ax)

        for cb in self._cb_picked:
            for ax in (cb.ax_cb, cb.ax_cb_plot):
                self._color_picked(ax)

    def _set_startpos(self, event):
        self._start_position = (event.x, event.y)
        self._start_ax_position = {
            i: (i.bbox.x0, i.bbox.y0)
            for i in (*self._ax_picked, *(cb._ax for cb in self._cb_picked))
        }

    def _add_to_history(self):
        self._history_undone.clear()
        self._history = self._history[: self._max_hist_steps]
        self._history.append(self.get_layout())

    def _undo(self):
        if len(self._history) > 0:
            l = self._history.pop(-1)
            self._history_undone.append(l)
            self.m.apply_layout(l)
            self.m.redraw()

    def _redo(self):
        if len(self._history_undone) > 0:
            l = self._history_undone.pop(-1)
            self._history.append(l)
            self.m.apply_layout(l)
            self.m.redraw()

    def cb_release(self, event):
        self._set_startpos(event)

    def cb_pick(self, event):
        if not self.modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        # toggle info-text visibility on left-click
        if event.button == 3:
            if getattr(self, "_info_text", None) is not None:
                vis = not self._info_text.get_visible()
                self._info_text.set_visible(vis)
                self._info_text_hidden = not vis

        eventax = event.inaxes

        if eventax not in self.axes:
            # if no axes is clicked "unpick" previously picked axes
            if len(self._ax_picked) + len(self._cb_picked) == 0:
                # if there was nothing picked there's nothing to do
                # except updating the info-text visibility

                if getattr(self, "_info_text", None) is not None:
                    self.blit_artists()

                return

            self._ax_picked = []
            self._cb_picked = []
            self._m_picked = []
            self._color_axes()
            self._remove_snap_grid()
            self.fetch_current_background()
            self.blit_artists()
            return

        if self._shift_pressed:
            if eventax in self.maxes:
                m = self.ms[self.maxes.index(eventax)]
                if eventax in self._ax_picked:
                    self._ax_picked.remove(eventax)
                else:
                    self._ax_picked.append(eventax)

                if m in self._m_picked:
                    self._m_picked.remove(m)
                else:
                    self._m_picked.append(m)
            elif eventax in self.cbaxes:
                cb = self.cbs[self.cbaxes.index(eventax)]
                if cb in self._cb_picked:
                    self._cb_picked.remove(cb)
                else:
                    self._cb_picked.append(cb)
            else:
                if eventax in self._ax_picked:
                    self._ax_picked.remove(eventax)
                else:
                    self._ax_picked.append(eventax)
        else:
            selected = eventax in self._ax_picked
            if eventax in self.cbaxes:
                selected = (
                    selected or self.cbs[self.cbaxes.index(eventax)] in self._cb_picked
                )

            if not selected:
                self._m_picked = []
                self._cb_picked = []
                self._ax_picked = []

                if eventax in self.axes:
                    if eventax in self.maxes:
                        self._ax_picked.append(eventax)
                        self._m_picked.append(self.ms[self.maxes.index(eventax)])
                    elif eventax in self.cbaxes:
                        self._cb_picked.append(self.cbs[self.cbaxes.index(eventax)])
                    else:
                        self._m_picked = []
                        self._cb_picked = []
                        self._ax_picked.append(eventax)

                    self._add_snap_grid()

            else:
                self._add_snap_grid()

        self._set_startpos(event)
        self._color_axes()
        self.fetch_current_background()
        self.blit_artists()

    def fetch_current_background(self):
        # clear the renderer to avoid drawing on existing backgrounds
        renderer = self.m.BM.canvas.get_renderer()
        renderer.clear()

        with ExitStack() as stack:
            for ax in self._ax_picked:
                stack.enter_context(ax._cm_set(visible=False))

            for cb in self._cb_picked:
                stack.enter_context(cb.ax_cb._cm_set(visible=False))
                stack.enter_context(cb.ax_cb_plot._cm_set(visible=False))

            self.m.BM.blit_artists(self.axes, None, False)

            grid = getattr(self, "_snap_grid_artist", None)
            if grid is not None:
                self.m.BM.blit_artists([grid], None, False)

            self.m.BM.canvas.blit()
            self._current_bg = self.m.BM.canvas.copy_from_bbox(self.m.f.bbox)

    def cb_move_with_key(self, event):
        if not self.modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        if event.key not in ["left", "right", "up", "down"]:
            return

        for ax in self._ax_picked:
            bbox = self._get_move_with_key_bbox(ax, event.key)
            ax.set_position(bbox)

        for cb in self._cb_picked:
            bbox = self._get_move_with_key_bbox(cb._ax, event.key)
            cb.set_position(bbox)

        self._add_to_history()
        self._color_axes()
        self.blit_artists()

    def cb_move(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self.modifier is not None:
            if not self.modifier_pressed:
                return False

        if event.button != 1:
            return

        for ax in self._ax_picked:
            if ax is None:
                return

            bbox = self._get_move_bbox(ax, event.x, event.y)
            ax.set_position(bbox)

        for cb in self._cb_picked:
            if cb is None:
                return

            bbox = self._get_move_bbox(cb._ax, event.x, event.y)
            cb.set_position(bbox)

        self._add_to_history()
        self._color_axes()
        self.blit_artists()

    def blit_artists(self):
        # TODO the current colorbar implementation requires the parent colorbar
        # to be drawn in order to change the inherited position.
        # a full redraw takes care of that but it is slower than blitting...
        if len(self._cb_picked) > 0:
            self.m.redraw()
            return

        artists = [*self._ax_picked]
        for cb in self._cb_picked:
            artists.append(cb.ax_cb)
            artists.append(cb.ax_cb_plot)

        if getattr(self, "_info_text", None) is not None:
            artists.append(self._info_text)

        self.m.BM.blit_artists(artists, self._current_bg)

    def cb_scroll(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self.modifier is not None:
            if not self.modifier_pressed:
                return False

        # ordinary axes picked
        if self._scale_direction not in ["set_hist_size"]:
            for ax in self._ax_picked:
                if ax is None:
                    continue
                resize_bbox = self._get_resize_bbox(ax, event.step)
                if resize_bbox is not None:
                    ax.set_position(resize_bbox)

        for cb in self._cb_picked:
            if cb is None:
                continue

            if self._scale_direction == "set_hist_size":
                start_size = cb._hist_size

                new_size = np.clip(start_size + event.step * 0.02, 0.0, 1.0)
                cb.set_hist_size(new_size)
            else:
                resize_bbox = self._get_resize_bbox(cb._ax, event.step)
                if resize_bbox is not None:
                    cb.set_position(resize_bbox)

        self._add_to_history()
        # self._color_axes()
        self.blit_artists()

    def cb_key_press(self, event):
        # release shift key on every keypress
        self._shift_pressed = False

        if (event.key == self.modifier) and (not self.modifier_pressed):
            self._make_draggable()
            return
        elif (event.key == self.modifier or event.key == "escape") and (
            self.modifier_pressed
        ):
            self._undo_draggable()
            return
        elif (event.key.lower() == "p") and (self.modifier_pressed):
            s = "\nlayout = {\n    "
            s += "\n    ".join(
                f'"{key}": {val},' for key, val in self.get_layout().items()
            )
            s += "\n}\n"
            print(s)
        elif (event.key.lower() == "q") and (self.modifier_pressed):
            print(
                "\n##########################\n\n"
                "EOmaps Layout Editor controls:\n\n"
                "Click on axes to select them for editing.\n"
                "(Hold 'shift' while clicking on axes to select multiple axes.)\n\n"
                "Drag selected axes with the mouse or use the 'arrow-keys' to "
                "change their position.\n\n"
                "Use the 'scroll-wheel' or the '+' and '-' keys to change the size "
                "of selected axes.\n"
                "For normal matplotlib axes: Hold down 'h' or 'v' to adjust only "
                "the horizontal or vertical size of the axes.\n"
                "For EOmaps colorbars: Hold down 'control' to adjust the relative "
                "size of the histogram.\n\n"
                "Use the keys 1-9 to adjust the spacing of the 'snap grid' (Note that "
                "the grid-spacing also determines the step-size for size- and "
                "position-changes!) Press 0 to disable grid-snapping.\n\n"
                f"To exit, press 'escape' or '{self.modifier}'\n"
                "\n##########################\n\n"
            )
            return

        else:
            if not self.modifier_pressed:
                # only continue if  modifier is pressed!
                return

        if event.key in ("ctrl+z", "control+z"):
            self._undo()
            return
        elif event.key in ("ctrl+y", "control+y"):
            self._redo()
            return
        elif event.key == "h":
            self._scale_direction = "horizontal"
        elif event.key == "v":
            self._scale_direction = "vertical"
        elif event.key in ("control", "ctrl", "ctrl++", "ctrl+-"):
            self._scale_direction = "set_hist_size"

        elif event.key == "shift":
            self._shift_pressed = True

        # assign snaps with keys 0-9
        if event.key in map(str, range(10)):
            self._snap_id = int(event.key)
            self._add_snap_grid()
            self.fetch_current_background()
            self.blit_artists()

        # assign snaps with keys 0-9
        if event.key in ["+", "-", "ctrl++", "ctrl+-"]:

            class dummyevent:
                pass

            d = dummyevent()
            d.key = event.key
            d.step = 1 * {"+": 1, "ctrl++": 1, "ctrl+-": -1, "-": -1}[event.key]

            self.cb_scroll(d)

    def cb_key_release(self, event):
        # reset scale direction on every key release event
        if event.key in ("h", "v", "control", "ctrl", "ctrl++", "ctrl+-"):
            self._scale_direction = "both"
        if event.key in ("shift"):
            self._shift_pressed = False

    @property
    def _snap(self):
        # grid-separation distance
        if self._snap_id == 0:
            snap = (0, 0)
        else:
            n = (self.f.bbox.width / 400) * (self._snap_id)

            snap = (n, n)

        return snap

    def _make_draggable(self, filepath=None):
        # Uncheck avtive pan/zoom actions of the matplotlib toolbar.
        # use a try-except block to avoid issues with ipympl in jupyter notebooks
        # (see https://github.com/matplotlib/ipympl/issues/530#issue-1780919042)
        try:
            toolbar = getattr(self.m.BM.canvas, "toolbar", None)
            if toolbar is not None:
                for key in ["pan", "zoom"]:
                    val = toolbar._actions.get(key, None)
                    if val is not None and val.isCheckable() and val.isChecked():
                        val.trigger()
        except AttributeError:
            pass

        self._filepath = filepath
        self.modifier_pressed = True
        _log.info(
            "EOmaps: Layout Editor activated! (press 'esc' to exit " "and 'q' for info)"
        )

        self._history.clear()
        self._history_undone.clear()
        self._add_to_history()

        self._revert_props = []
        for ax in self.f.axes:
            # only handle axes that have a finite size (in pixels) to avoid
            # singular matrix errors for initially hidden zero-size axes
            # (can happen for colorbar/colorbar histogram axes)
            singularax = False
            if ax.bbox.width <= 1 or ax.bbox.height <= 1:
                singularax = True

            # check if the axis is the container-axes of a colorbar
            cbaxQ = ax.get_label() == "cb"

            self._revert_props.append((ax.set_visible, ax.get_visible()))
            self._revert_props.append((ax.set_frame_on, ax.get_frame_on()))
            self._revert_props.append((ax.set_animated, ax.get_animated()))

            if not ax.axison:
                showXY = False
                self._revert_props.append(ax.set_axis_off)
                ax.set_axis_on()
            else:
                showXY = True

            # keep singular axes hidden
            if not singularax:
                ax.set_visible(True)
            else:
                ax.set_visible(False)

            ax.set_animated(False)
            ax.set_frame_on(True)

            for child in ax.get_children():
                revert_props = [
                    "edgecolor",
                    "linewidth",
                    "alpha",
                    "animated",
                    "visible",
                ]
                self._add_revert_props(child, *revert_props)

                if isinstance(child, Spine) and not cbaxQ:
                    # make sure spines are visible (and re-drawn on draw)
                    child.set_animated(False)
                    child.set_visible(True)
                    if hasattr(child, "_EOmaps_linestyle"):
                        child.set_linestyle(getattr(child, "_EOmaps_linestyle", "-"))
                        del child._EOmaps_linestyle
                elif (
                    ax not in self.maxes
                    and showXY
                    and isinstance(child, (XAxis, YAxis))
                ):
                    # keep all tick labels etc. of normal axes and colorbars visible
                    child.set_animated(False)
                    child.set_visible(True)

                elif child is ax.patch and not cbaxQ:
                    # only reset facecolors for axes-patches to avoid issues with
                    # black spines (TODO check why this happens!)
                    self._add_revert_props(child, "facecolor")

                    # make sure patches are visible (and re-drawn on draw)
                    child.set_visible(True)
                    child.set_facecolor("w")
                    child.set_alpha(0.75)  # for overlapping axes

                else:
                    # make all other childs invisible (to avoid drawing them)
                    child.set_visible(False)
                    child.set_animated(True)

        # hide all colorbars that are not on the visible layer
        for cb in self.cbs:
            if cb._m.layer != self.m.BM.bg_layer:
                cb.set_visible(False)

        # only re-draw if info-text is None
        if getattr(self, "_info_text", None) is None:
            self._info_text = self.add_info_text()

        self._color_axes()
        self._attach_callbacks()

        self.m._emit_signal("layoutEditorActivated")

        self.m.redraw()

    def _add_revert_props(self, child, *args):
        for prop in args:
            if hasattr(child, f"set_{prop}") and hasattr(child, f"get_{prop}"):
                self._revert_props.append(
                    (
                        getattr(child, f"set_{prop}"),
                        getattr(child, f"get_{prop}")(),
                    )
                )

    def _undo_draggable(self):
        if getattr(self, "_info_text", None) not in (None, False):
            self._info_text.remove()
            # set to None to avoid crating the info-text again
            self._info_text = None

        self._history.clear()
        self._history_undone.clear()

        toolbar = getattr(self.m.f, "toolbar", None)
        if toolbar is not None:
            # Reset the axes stack to make sure the "home" "back" and "forward" buttons
            # of the toolbar do not reset axis positions
            # see "matplotlib.backend_bases.NavigationToolbar2.update"
            if hasattr(toolbar, "update"):
                try:
                    toolbar.update()
                except Exception:
                    _log.exception(
                        "EOmaps: Error while trying to reset the axes stack!"
                    )

        # clear all picks on exit
        self._ax_picked = []
        self._cb_picked = []
        self._m_picked = []

        _log.info("EOmaps: Exiting layout-editor mode...")

        # in case a filepath was provided, save the new layout
        if self._filepath:
            try:
                self.m.get_layout(filepath=self._filepath, override=True)
            except Exception:
                _log.exception(
                    "EOmaps: Layout could not be saved to the provided "
                    + f"filepath: '{self._filepath}'."
                )

        self._reset_callbacks()
        # revert all changes to artists
        for p in self._revert_props:
            if isinstance(p, tuple):
                p[0](p[1])
            else:
                p()

        self.modifier_pressed = False

        # show all colorbars that are on the visible layer
        active_layers = self.m.BM._get_layers_alphas()[0]
        for cb in self.cbs:
            if cb._m.layer in active_layers:
                cb.set_visible(True)

        # reset the histogram-size of all colorbars to make sure previously hidden
        # axes (e.g. size=0) become visible if the size is now > 0.
        for m in self.ms:
            for cb in m._colorbars:
                cb.set_hist_size()

        # remove snap-grid (if it's still visible)
        self._remove_snap_grid()

        self.m._emit_signal("layoutEditorDeactivated")

        self.m.redraw()

    def _reset_callbacks(self):
        # disconnect all callbacks of the layout-editor
        while len(self.cids) > 0:
            cid = self.cids.pop(-1)
            self.f.canvas.mpl_disconnect(cid)

    def _attach_callbacks(self):
        # make sure all previously set callbacks are reset
        self._reset_callbacks()

        events = (
            ("scroll_event", self.cb_scroll),
            ("button_press_event", self.cb_pick),
            ("button_release_event", self.cb_release),
            ("motion_notify_event", self.cb_move),
            ("key_press_event", self.cb_move_with_key),
            ("key_release_event", self.cb_key_release),
        )

        for event, cb in events:
            self.cids.append(self.f.canvas.mpl_connect(event, cb))

    def _add_snap_grid(self, snap=None):
        # snap = (snapx, snapy)

        if snap is None:
            if self._snap_id == 0:
                self._remove_snap_grid()
                return
            else:
                snapx, snapy = self._snap
        else:
            snapx, snapy = snap

        self._remove_snap_grid()

        bbox = self.m.f.bbox
        t = self.m.f.transFigure.inverted()

        gx, gy = np.mgrid[
            0 : int(bbox.width) + int(snapx) : snapx,
            0 : int(bbox.height) + int(snapy) : snapy,
        ]
        g = t.transform(np.column_stack((gx.flat, gy.flat)))

        l = Line2D(
            *g.T,
            lw=0,
            marker=".",
            markerfacecolor="steelblue",
            markeredgecolor="none",
            ms=(snapx + snapy) / 6,
        )
        self._snap_grid_artist = self.m.f.add_artist(l)

    def _remove_snap_grid(self):
        if hasattr(self, "_snap_grid_artist"):
            self._snap_grid_artist.remove()
            del self._snap_grid_artist

    def get_layout(self, filepath=None, override=False, precision=5):
        """
        Get the positions of all axes within the current plot.

        To re-apply a layout, use:

            >>> l = m.get_layout()
            >>> m.set_layout(l)

        Note
        ----
        The returned list is only a snapshot of the current layout.
        It can only be re-applied to a given figure if the order at which the axes are
        created remains the same!

        Parameters
        ----------
        filepath : str or pathlib.Path, optional
            If provided, a json-file will be created at the specified destination that
            can be used in conjunction with `m.set_layout(...)` to apply the layout:

            >>> m.get_layout(filepath=<FILEPATH>, override=True)
            >>> m.apply_layout_layout(<FILEPATH>)

            You can also manually read-in the layout-dict via:
            >>> import json
            >>> layout = json.load(<FILEPATH>)
        override: bool
            Indicator if the file specified as 'filepath' should be overwritten if it
            already exists.
            The default is False.
        precision : int or None
            The precision of the returned floating-point numbers.
            If None, all available digits are returned
            The default is 5
        Returns
        -------
        layout : dict or None
            A dict of the positons of all axes, e.g.: {1:(x0, y0, width height), ...}
        """
        figsize = [*self.f.get_size_inches()]

        axes = [
            a for a in self.axes if a.get_label() not in ["EOmaps_cb", "EOmaps_cb_hist"]
        ]

        # identify relevant colorbars
        colorbars = [getattr(m, "colorbar", None) for m in self.ms]
        cbaxes = [getattr(cb, "_ax", None) for cb in colorbars]
        cbs = [(colorbars[cbaxes.index(a)] if a in cbaxes else None) for a in axes]
        # -----------

        layout = dict()
        layout["figsize"] = figsize

        for i, ax in enumerate(axes):
            if cbs[i] is not None:
                if cbs[i]._ax.get_axes_locator() is not None:
                    continue

            label = ax.get_label()
            name = f"{i}_{label}"
            if precision is not None:
                layout[name] = np.round(ax.get_position().bounds, precision).tolist()
            else:
                layout[name] = ax.get_position().bounds

            if cbs[i] is not None:
                layout[f"{name}_histogram_size"] = cbs[i]._hist_size

        if filepath is not None:
            filepath = Path(filepath)
            assert (
                not filepath.exists() or override
            ), f"The file {filepath} already exists! Use override=True to relace it."
            with open(filepath, "w") as file:
                json.dump(layout, file)
            _log.info(f"EOmaps: Layout saved to:\n       {filepath}")

        return layout

    def apply_layout(self, layout):
        """
        Set the positions of all axes within the current plot based on a previously
        defined layout.

        To apply a layout, use:

            >>> l = m.get_layout()
            >>> m.set_layout(l)

        To save a layout to disc and apply it at a later stage, use
            >>> m.get_layout(filepath=<FILEPATH>)
            >>> m.set_layout(<FILEPATH>)

        Note
        ----
        The returned list is only a snapshot of the current layout.
        It can only be re-applied to a given figure if the order at which the axes are
        created remains the same!

        Parameters
        ----------
        layout : dict, str or pathlib.Path
            If a dict is provided, it is directly used to define the layout.

            If a string or a pathlib.Path object is provided, it will be used to
            read a previously dumped layout (e.g. with `m.get_layout(filepath)`)

        """
        if isinstance(layout, (str, Path)):
            with open(layout, "r") as file:
                layout = json.load(file)

        # check if all relevant axes are specified in the layout
        valid_keys = set(self.get_layout())
        if valid_keys != set(layout):
            _log.warning(
                "EOmaps: The the layout does not match the expected structure! "
                "Layout might not be properly restored. "
                "Invalid or missing keys:\n"
                f"{sorted(valid_keys.symmetric_difference(set(layout)))}\n"
            )

        # set the figsize
        figsize = layout.get("figsize", None)
        if figsize is not None:
            self.f.set_size_inches(*figsize)

        axes = [
            a for a in self.axes if a.get_label() not in ["EOmaps_cb", "EOmaps_cb_hist"]
        ]

        # identify relevant colorbars
        colorbars = [getattr(m, "colorbar", None) for m in self.ms]
        cbaxes = [getattr(cb, "_ax", None) for cb in colorbars]
        cbs = [(colorbars[cbaxes.index(a)] if a in cbaxes else None) for a in axes]

        for key in valid_keys.intersection(set(layout)):
            if key == "figsize":
                continue
            val = layout[key]

            i = int(key[: key.find("_")])
            if key.endswith("_histogram_size"):
                cbs[i].set_hist_size(val)
            else:
                axes[i].set_position(val)

        self.m.redraw()


# taken from https://matplotlib.org/stable/tutorials/advanced/blitting.html#class-based-example
class BlitManager:
    """Manager used to schedule draw events, cache backgrounds, etc."""

    _snapshot_on_update = None

    def __init__(self, m):
        """
        Manager used to schedule draw events, cache backgrounds, etc.

        Parameters
        ----------
        canvas : FigureCanvasAgg
            The canvas to work with, this only works for sub-classes of the Agg
            canvas which have the `~FigureCanvasAgg.copy_from_bbox` and
            `~FigureCanvasAgg.restore_region` methods.

        animated_artists : Iterable[Artist]
            List of the artists to manage

        """
        self._disable_draw = False
        self._disable_update = False

        self._m = m

        self._artists = dict()

        self._bg_artists = dict()
        self._bg_layers = dict()

        self._pending_webmaps = dict()

        # the name of the layer at which all "unmanaged" artists are drawn
        self._unmanaged_artists_layer = "base"

        # grab the background on every draw
        self.cid = self.canvas.mpl_connect("draw_event", self.on_draw)

        self._after_update_actions = []
        self._after_restore_actions = []
        self._bg_layer = "base"

        self._artists_to_clear = dict()

        self._hidden_artists = set()

        self._refetch_bg = True
        self._layers_to_refetch = set()

        # TODO these activate some crude fixes for jupyter notebook and webagg
        # backends... proper fixes would be nice
        self._mpl_backend_blit_fix = any(
            i in plt.get_backend().lower() for i in ["webagg", "nbagg"]
        )

        # self._mpl_backend_force_full = any(
        #     i in plt.get_backend().lower() for i in ["nbagg"]
        # )
        # recent fixes seem to take care of this nbagg issue...
        self._mpl_backend_force_full = False
        self._mpl_backend_blit_fix = False

        # True = persistant, False = execute only once
        self._on_layer_change = {True: list(), False: list()}
        self._on_layer_activation = {True: dict(), False: dict()}

        self._on_add_bg_artist = list()
        self._on_remove_bg_artist = list()

        self._before_fetch_bg_actions = list()
        self._before_update_actions = list()

        self._refetch_blank = True
        self._blank_bg = None

        self._managed_axes = set()

        self._clear_on_layer_change = False

        self._on_layer_change_running = False

        # a weak set containing artists that should NOT be identified as
        # unmanaged artists
        self._ignored_unmanaged_artists = WeakSet()

    def _get_renderer(self):
        # don't return the renderer if the figure is saved.
        # in this case the normal draw-routines are used (see m.savefig) so there is
        # no need to trigger updates (also `canvas.get_renderer` is undefined for
        # pdf/svg exports since those canvas do not expose the renderer)
        # ... this is required to support vektor format outputs!
        if self.canvas.is_saving():
            return None

        try:
            return self.canvas.get_renderer()
        except Exception:
            return None

    def _get_all_map_axes(self):
        maxes = {
            m.ax for m in (self._m.parent, *self._m.parent._children) if m._new_axis_map
        }
        return maxes

    def _get_managed_axes(self):
        return (*self._get_all_map_axes(), *self._managed_axes)

    def _get_unmanaged_axes(self):
        # return a list of all axes that are not managed by the blit-manager
        # (to ensure that "unmanaged" axes are drawn as well)

        # EOmaps axes
        managed_axes = self._get_managed_axes()
        allaxes = set(self._m.f.axes)

        unmanaged_axes = allaxes.difference(managed_axes)
        return unmanaged_axes

    @property
    def figure(self):
        """The matplotlib figure instance."""
        return self._m.f

    @property
    def canvas(self):
        """The figure canvas instance."""
        return self.figure.canvas

    @contextmanager
    def _cx_on_layer_change_running(self):
        # a context-manager to avoid recursive on_layer_change calls
        try:
            self._on_layer_change_running = True
            yield
        finally:
            self._on_layer_change_running = False

    def _do_on_layer_change(self, layer, new=False):
        # avoid recursive calls to "_do_on_layer_change"
        # This is required in case the executed functions trigger actions that would
        # trigger "_do_on_layer_change" again which can result in a mixed-up order of
        # the scheduled functions.
        if self._on_layer_change_running is True:
            return

        # do not execute layer-change callbacks on private layer activation!
        if layer.startswith("__"):
            return

        with self._cx_on_layer_change_running():
            # only execute persistent layer-change callbacks if the layer changed!
            if new:
                # general callbacks executed on any layer change
                # persistent callbacks
                for f in reversed(self._on_layer_change[True]):
                    f(layer=layer)

            # single-shot callbacks
            # (execute also if the layer is already active)
            while len(self._on_layer_change[False]) > 0:
                try:
                    f = self._on_layer_change[False].pop(0)
                    f(layer=layer)
                except Exception as ex:
                    _log.error(
                        "EOmaps: Issue while executing a layer-change action",
                        exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                    )

            if new:
                for l in layer.split("|"):
                    # individual callables executed if a specific layer is activate
                    # persistent callbacks
                    for f in reversed(self._on_layer_activation[True].get(layer, [])):
                        f(layer=l)

            for l in layer.split("|"):
                # single-shot callbacks
                single_shot_funcs = self._on_layer_activation[False].get(l, [])
                while len(single_shot_funcs) > 0:
                    try:
                        f = single_shot_funcs.pop(0)
                        f(layer=l)
                    except Exception as ex:
                        _log.error(
                            "EOmaps: Issue while executing a layer-change action",
                            exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                        )

            # clear the list of pending webmaps once the layer has been activated
            if layer in self._pending_webmaps:
                self._pending_webmaps.pop(layer)

    @contextmanager
    def _without_artists(self, artists=None, layer=None):
        try:
            removed_artists = {layer: set(), "all": set()}
            if artists is None:
                yield
            else:
                for a in artists:
                    if a in self._artists.get(layer, []):
                        self.remove_artist(a, layer=layer)
                        removed_artists[layer].add(a)
                    elif a in self._artists.get("all", []):
                        self.remove_artist(a, layer="all")
                        removed_artists["all"].add(a)

                yield
        finally:
            for layer, artists in removed_artists.items():
                for a in artists:
                    self.add_artist(a, layer=layer)

    def _get_active_bg(self, exclude_artists=None):
        with self._without_artists(artists=exclude_artists, layer=self.bg_layer):
            # fetch the current background (incl. dynamic artists)
            self.update()

            with ExitStack() as stack:
                # get rid of the figure background patch
                # (done by putting the patch on the __BG__ layer!)

                # get rid of the axes background patch
                for ax_i in self._get_all_map_axes():
                    stack.enter_context(
                        ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                    )
                bg = self.canvas.copy_from_bbox(self.figure.bbox)

        return bg

    @property
    def bg_layer(self):
        """The currently visible layer-name."""
        return self._bg_layer

    @bg_layer.setter
    def bg_layer(self, val):
        if val == self._bg_layer:
            # in case the layer did not change, do nothing
            return

        # check if a new layer is activated (or added to a multi-layer)
        old_layers = self._bg_layer.split("|")
        new = val != self._bg_layer or any(l not in old_layers for l in val.split("|"))

        # make sure we use a "full" update for webagg and ipympl backends
        # (e.g. force full redraw of canvas instead of a diff)
        self.canvas._force_full = True
        self._bg_layer = val

        # a general callable to be called on every layer change

        self._do_on_layer_change(layer=val, new=new)

        layer_names = val.split("|")

        # hide all colorbars that are not on the visible layer
        for m in [self._m.parent, *self._m.parent._children]:
            layer_visible = m.layer in layer_names

            for cb in m._colorbars:
                if layer_visible:
                    if cb in self._hidden_artists:
                        self._hidden_artists.remove(cb)
                else:
                    if cb not in self._hidden_artists:
                        self._hidden_artists.add(cb)

        # hide all wms_legends that are not on the visible layer
        if hasattr(self._m.parent, "_wms_legend"):
            for layer, legends in self._m.parent._wms_legend.items():
                if layer in layer_names:
                    for i in legends:
                        i.set_visible(True)
                else:
                    for i in legends:
                        i.set_visible(False)

        if self._clear_on_layer_change:
            self._clear_temp_artists("on_layer_change")

    @contextmanager
    def _cx_dont_clear_on_layer_change(self):
        # a context-manager to avoid clearing artists on layer-changes
        # (used in savefig to avoid clearing artists when re-fetching
        # layers with backgrounds)
        init_val = self._clear_on_layer_change
        try:
            self._clear_on_layer_change = False
            yield
        finally:
            self._clear_on_layer_change = init_val

    def on_layer(self, func, layer=None, persistent=False, m=None):
        """
        Add callables that are executed whenever the visible layer changes.

        NOTE: if m is None this function always falls back to the parent Maps-object!!

        Parameters
        ----------
        func : callable
            The callable to use.
            The call-signature is:

            >>> def func(m, layer):
            >>>    # m     ... the Maps-object
            >>>    # layer ... the name of the layer


        layer : str or None, optional
            - If str: The function will only be called if the specified layer is
              activated.
            - If None: The function will be called on any layer-change.

            The default is None.
        persistent : bool, optional
            Indicator if the function should be called only once (False) or if it
            should be called whenever a layer is activated.
            The default is False.
        m : eomaps.Maps
            The Maps-object to pass as argument to the function execution.
            If None, the parent Maps-object is used.

        """
        if m is None:
            m = self._m

        def cb(*args, **kwargs):
            func(m=m, *args, **kwargs)

        if _log.getEffectiveLevel() <= 10:
            logmsg = (
                f"Adding {'persistent' if persistent else 'single-shot'} "
                f"layer change action for: '{layer}'"
            )
            _log.debug(logmsg)

        if layer is None:
            self._on_layer_change[persistent].append(cb)
        else:
            # treat inset-map layers like normal layers
            if layer.startswith("__inset_"):
                layer = layer[8:]
            self._on_layer_activation[persistent].setdefault(layer, list()).append(cb)

    def _refetch_layer(self, layer):
        if layer == "all":
            # if the all layer changed, all backgrounds need a refetch
            self._refetch_bg = True
        else:
            # set any background that contains the layer for refetch
            self._layers_to_refetch.add(layer)
            for l in self._bg_layers:
                if layer in l.split("|"):
                    self._layers_to_refetch.add(l)

    def _bg_artists_sort(self, art):
        sortp = []

        # ensure that inset-map artists are always drawn after all other artists
        if art.axes is not None:
            if art.axes.get_label() == "inset_map":
                sortp.append(1)
            else:
                sortp.append(0)

        sortp.append(getattr(art, "zorder", -1))
        return sortp

    def get_bg_artists(self, layer):
        """
        Get all (sorted) background artists assigned to a given layer-name.

        Parameters
        ----------
        layer : str
            The layer name for which artists should be fetched.

        Returns
        -------
        artists : list
            A list of artists on the specified layer, sorted with respect to the
            vertical stacking (layer-order / zorder).

        """
        artists = list()
        for l in np.atleast_1d(layer):
            # get all relevant artists for combined background layers
            l = str(l)  # w make sure we convert non-string layer names to string!

            # get artists defined on the layer itself
            # Note: it's possible to create explicit multi-layers and attach
            # artists that are only visible if both layers are visible! (e.g. "l1|l2")
            artists.extend(self._bg_artists.get(l, []))

            if l == self._unmanaged_artists_layer:
                artists.extend(self._get_unmanaged_artists())

        # make the list unique but maintain order (dicts keep order for python>3.7)
        artists = dict.fromkeys(artists)
        # sort artists by zorder (respecting inset-map priority)
        artists = sorted(artists, key=self._bg_artists_sort)

        return artists

    def get_artists(self, layer):
        """
        Get all (sorted) dynamically updated artists assigned to a given layer-name.

        Parameters
        ----------
        layer : str
            The layer name for which artists should be fetched.

        Returns
        -------
        artists : list
            A list of artists on the specified layer, sorted with respect to the
            vertical stacking (layer-order / zorder).

        """

        artists = list()
        for l in np.atleast_1d(layer):
            # get all relevant artists for combined background layers
            l = str(l)  # w make sure we convert non-string layer names to string!

            # get artists defined on the layer itself
            # Note: it's possible to create explicit multi-layers and attach
            # artists that are only visible if both layers are visible! (e.g. "l1|l2")
            artists.extend(self._artists.get(l, []))

        # make the list unique but maintain order (dicts keep order for python>3.7)
        artists = dict.fromkeys(artists)
        # sort artists by zorder (respecting inset-map priority)
        artists = sorted(artists, key=self._bg_artists_sort)

        return artists

    def _get_layers_alphas(self, layer=None):
        if layer is None:
            layer = self.bg_layer

        layers, alphas = [], []
        for l in layer.split("|"):
            if l.endswith("}") and "{" in l:
                try:
                    name, a = l.split("{", maxsplit=1)
                    a = float(a.replace("}", ""))

                    layers.append(name)
                    alphas.append(a)
                except Exception:
                    raise TypeError(
                        "EOmaps: unable to parse multilayer-transparency " f"for '{l}'"
                    )
            else:
                layers.append(l)
                alphas.append(1)
        return layers, alphas

    # cache the last 10 combined backgrounds to avoid re-combining backgrounds
    # on updates of interactive artists
    # cache is automatically cleared on draw if any layer is tagged for re-fetch!
    @lru_cache(10)
    def _combine_bgs(self, layer):
        layers, alphas = self._get_layers_alphas(layer)

        # make sure all layers are already fetched
        for l in layers:
            if l not in self._bg_layers:
                # execute actions on layer-changes
                # (to make sure all lazy WMS services are properly added)
                self._do_on_layer_change(layer=l, new=False)
                self.fetch_bg(l)

        renderer = self._get_renderer()
        # clear the renderer to avoid drawing on existing backgrounds
        renderer.clear()
        if renderer:
            gc = renderer.new_gc()
            gc.set_clip_rectangle(self.canvas.figure.bbox)

            x0, y0, w, h = self.figure.bbox.bounds
            for l, a in zip(layers, alphas):
                rgba = self._get_array(l, a=a)
                if rgba is None:
                    # to handle completely empty layers
                    continue
                renderer.draw_image(
                    gc,
                    int(x0),
                    int(y0),
                    rgba[int(y0) : int(y0 + h), int(x0) : int(x0 + w), :],
                )
            bg = renderer.copy_from_bbox(self._m.f.bbox)
            gc.restore()
            return bg

    def _get_array(self, l, a=1):
        if l not in self._bg_layers:
            return None
        rgba = np.array(self._bg_layers[l])[::-1, :, :]
        if a != 1:
            rgba = rgba.copy()
            rgba[..., -1] = (rgba[..., -1] * a).astype(rgba.dtype)
        return rgba

    def _get_background(self, layer, bbox=None, cache=False):
        if layer not in self._bg_layers:
            if "|" in layer:
                bg = self._combine_bgs(layer)
            else:
                self.fetch_bg(layer, bbox=bbox)
                bg = self._bg_layers[layer]
        else:
            bg = self._bg_layers[layer]

        if cache is True:
            # explicitly cache the layer
            # (for peek-layer callbacks to avoid re-fetching the layers all the time)
            self._bg_layers[layer] = bg

        return bg

    def _do_fetch_bg(self, layer, bbox=None):
        cv = self.canvas
        renderer = self._get_renderer()
        renderer.clear()

        if bbox is None:
            bbox = self.figure.bbox

        if "|" in layer:
            if layer not in self._bg_layers:
                self._combine_bgs(layer)
            return

        # update axes spines and patches since they are used to clip artists!
        for ax in self._get_all_map_axes():
            ax.spines["geo"]._adjust_location()
            ax.patch._adjust_location()

        # use contextmanagers to make sure the background patches are not stored
        # in the buffer regions!
        with ExitStack() as stack:
            if layer not in ["__BG__"]:
                # get rid of the axes background patches for all layers except
                # the __BG__ layer
                # (the figure background patch is on the "__BG__" layer)
                for ax_i in self._get_all_map_axes():
                    stack.enter_context(
                        ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                    )

            # execute actions before fetching new artists
            # (e.g. update data based on extent etc.)
            for action in self._before_fetch_bg_actions:
                action(layer=layer, bbox=bbox)

            # get all relevant artists to plot and remember zorders
            # self.get_bg_artists() already returns artists sorted by zorder!
            if layer in ["__SPINES__", "__BG__", "__inset___SPINES__"]:
                # avoid fetching artists from the "all" layer for private layers
                allartists = self.get_bg_artists(layer)
            else:
                if layer.startswith("__inset"):
                    allartists = self.get_bg_artists(["__inset_all", layer])
                else:
                    allartists = self.get_bg_artists(["all", layer])

            # check if all artists are not stale
            no_stale_artists = all(not art.stale for art in allartists)

            # don't re-fetch the background if it is not necessary
            if no_stale_artists and (self._bg_layers.get(layer, None) is not None):
                return

            if renderer:
                for art in allartists:
                    if art not in self._hidden_artists:
                        art.draw(renderer)
                        art.stale = False
                self._bg_layers[layer] = renderer.copy_from_bbox(bbox)

    def fetch_bg(self, layer=None, bbox=None):
        """
        Trigger fetching (and caching) the background for a given layer-name.

        Parameters
        ----------
        layer : str, optional
            The layer for which the background should be fetched.
            If None, the currently visible layer is fetched.
            The default is None.
        bbox : bbox, optional
            The region-boundaries (in figure coordinates) for which the background
            should be fetched (x0, y0, w, h). If None, the whole figure is fetched.
            The default is None.

        """

        if layer is None:
            layer = self.bg_layer

        if layer in self._bg_layers:
            # don't re-fetch existing layers
            # (layers get cleared automatically if re-draw is necessary)
            return

        with self._disconnect_draw():
            self._do_fetch_bg(layer, bbox)

    @contextmanager
    def _disconnect_draw(self):
        try:
            # temporarily disconnect draw-event callback to avoid recursion
            if self.cid is not None:
                self.canvas.mpl_disconnect(self.cid)
                self.cid = None
            yield
        finally:
            # reconnect draw event
            if self.cid is None:
                self.cid = self.canvas.mpl_connect("draw_event", self.on_draw)

    def on_draw(self, event):
        """Callback to register with 'draw_event'."""

        if self._disable_draw:
            return

        cv = self.canvas
        loglevel = _log.getEffectiveLevel()

        if hasattr(cv, "get_renderer") and not cv.is_saving():

            renderer = cv.get_renderer()
            if renderer is None:
                # don't run on_draw if no renderer is available
                return
        else:
            # don't run on_draw if no renderer is available
            # (this is true for svg export where mpl export routines
            # are used to avoid issues)
            if loglevel <= 5:
                _log.log(5, " not drawing")

            return

        if loglevel <= 5:
            _log.log(5, "draw")

        if event is not None:
            if event.canvas != cv:
                raise RuntimeError
        try:
            # reset all background-layers and re-fetch the default one
            if self._refetch_bg:
                self._bg_layers.clear()
                self._layers_to_refetch.clear()
                self._refetch_bg = False
                type(self)._combine_bgs.cache_clear()  # clear combined_bg cache

            else:
                # in case there is a stale (unmanaged) artists and the
                # stale-artist layer is attempted to be drawn, re-draw the
                # cached background for the unmanaged-artists layer
                if self._unmanaged_artists_layer in self._bg_layer.split("|") and any(
                    a.stale for a in self._get_unmanaged_artists()
                ):
                    self._refetch_layer(self._unmanaged_artists_layer)
                    type(self)._combine_bgs.cache_clear()  # clear combined_bg cache

                # remove all cached backgrounds that were tagged for refetch
                while len(self._layers_to_refetch) > 0:
                    self._bg_layers.pop(self._layers_to_refetch.pop(), None)
                    type(self)._combine_bgs.cache_clear()  # clear combined_bg cache

            # workaround for nbagg backend to avoid glitches
            # it's slow but at least it works...
            # check progress of the following issuse
            # https://github.com/matplotlib/matplotlib/issues/19116
            if self._mpl_backend_blit_fix:
                self.update()
            else:
                self.update(blit=False)

            # re-draw indicator-shapes of active drawer
            # (to show indicators during zoom-events)
            active_drawer = getattr(self._m.parent, "_active_drawer", None)
            if active_drawer is not None:
                active_drawer.redraw(blit=False)

        except Exception:
            # we need to catch exceptions since QT does not like them...
            if loglevel <= 5:
                _log.log(5, "There was an error during draw!", exc_info=True)

    def add_artist(self, art, layer=None):
        """
        Add a dynamic-artist to be managed.
        (Dynamic artists are re-drawn on every update!)

        Parameters
        ----------
        art : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        layer : str or None, optional
            The layer name at which the artist should be drawn.

            - If "all": the corresponding feature will be added to ALL layers

            The default is None in which case the layer of the base-Maps object is used.
        """

        if art.figure != self.figure:
            raise RuntimeError(
                "EOmaps: The artist does not belong to the figure"
                "of this Maps-object!"
            )

        if layer is None:
            layer = self._m.layer

        # make sure all layers are converted to string
        layer = str(layer)

        self._artists.setdefault(layer, list())

        if art in self._artists[layer]:
            return
        else:
            art.set_animated(True)
            self._artists[layer].append(art)

            if isinstance(art, plt.Axes):
                self._managed_axes.add(art)

    def add_bg_artist(self, art, layer=None, draw=True):
        """
        Add a background-artist to be managed.
        (Background artists are only updated on zoom-events... they are NOT animated!)

        Parameters
        ----------
        art : Artist
            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        layer : str or None, optional
            The layer name at which the artist should be drawn.

            - If "all": the corresponding feature will be added to ALL layers

            The default is None in which case the layer of the base-Maps object is used.
        draw : bool, optional
            If True, `figure.draw_idle()` is called after adding the artist.
            The default is True.
        """

        if layer is None:
            layer = self._m.layer

        # make sure all layer names are converted to string
        layer = str(layer)

        if art.figure != self.figure:
            raise RuntimeError

        # put all artist of inset-maps on dedicated layers
        if (
            getattr(art, "axes", None) is not None
            and art.axes.get_label() == "inset_map"
            and not layer.startswith("__inset_")
        ):
            layer = "__inset_" + str(layer)
        if layer in self._bg_artists and art in self._bg_artists[layer]:
            _log.info(f"EOmaps: Background-artist '{art}' already added")
            return

        art.set_animated(True)
        self._bg_artists.setdefault(layer, []).append(art)

        if isinstance(art, plt.Axes):
            self._managed_axes.add(art)

        # tag all relevant layers for refetch
        self._refetch_layer(layer)

        for f in self._on_add_bg_artist:
            f()

        if draw:
            self.canvas.draw_idle()

    def remove_bg_artist(self, art, layer=None, draw=True):
        """
        Remove a (background) artist from the map.

        Parameters
        ----------
        art : Artist
            The artist that should be removed.
        layer : str or None, optional
            If provided, the artist is only searched on the provided layer, otherwise
            all map layers are searched. The default is None.
        draw : bool, optional
            If True, `figure.draw_idle()` is called after removing the artist.
            The default is True.

        Note
        ----
        This only removes the artist from the blit-manager and does not call its
        remove method!

        """
        # handle the "__inset_" prefix of inset-map artists
        if (
            layer is not None
            and getattr(art, "axes", None) is not None
            and art.axes.get_label() == "inset_map"
            and not layer.startswith("__inset_")
        ):
            layer = "__inset_" + str(layer)

        removed = False
        if layer is None:
            layers = []
            for key, val in self._bg_artists.items():
                if art in val:
                    art.set_animated(False)
                    val.remove(art)

                    # remove axes from the managed_axes set as well!
                    if art in self._managed_axes:
                        self._managed_axes.remove(art)

                    removed = True
                    layers.append(key)
                layer = "|".join(layers)
        else:
            if layer not in self._bg_artists:
                return
            if art in self._bg_artists[layer]:
                art.set_animated(False)
                self._bg_artists[layer].remove(art)

                # remove axes from the managed_axes set as well!
                if art in self._managed_axes:
                    self._managed_axes.remove(art)

                removed = True

        if removed:
            for f in self._on_remove_bg_artist:
                f()

            # tag all relevant layers for refetch
            self._refetch_layer(layer)

        if draw:
            self.canvas.draw_idle()

    def remove_artist(self, art, layer=None):
        """
        Remove a (dynamically updated) artist from the blit-manager.

        Parameters
        ----------
        art : matpltolib.Artist
            The artist to remove.
        layer : str, optional
            The layer to search for the artist. If None, all layers are searched.
            The default is None.

        Note
        ----
        This only removes the artist from the blit-manager and does not call its
        remove method!

        """
        if layer is None:
            for key, layerartists in self._artists.items():
                if art in layerartists:
                    art.set_animated(False)
                    layerartists.remove(art)

                    # remove axes from the managed_axes set as well!
                    if art in self._managed_axes:
                        self._managed_axes.remove(art)

        else:
            if art in self._artists.get(layer, []):
                art.set_animated(False)
                self._artists[layer].remove(art)

                # remove axes from the managed_axes set as well!
                if art in self._managed_axes:
                    self._managed_axes.remove(art)
            else:
                _log.debug(f"The artist {art} is not on the layer '{layer}'")

    def _get_artist_zorder(self, a):
        try:
            return a.get_zorder()
        except Exception:
            _log.error(f"EOmaps: unalble to identify zorder of {a}... using 99")
            return 99

    def _draw_animated(self, layers=None, artists=None):
        """
        Draw animated artists

        - if layers is None and artists is None: active layer artists will be re-drawn
        - if layers is not None: all artists from the selected layers will be re-drawn
        - if artists is not None: all provided artists will be redrawn

        """
        fig = self.canvas.figure
        renderer = self._get_renderer()
        if renderer is None:
            return

        # make sure to strip-off transparency-assignments (e.g. "layer1{0.5}")
        if layers is None:
            layers = [self.bg_layer]
            layers.extend(
                (l.split("{", maxsplit=1)[0] for l in self.bg_layer.split("|"))
            )
        else:
            layers = list(chain(*(i.split("|") for i in layers)))
            for l in layers:
                layers.append(l.split("{", maxsplit=1)[0])

        if artists is None:
            artists = []

        # always redraw artists from the "all" layer
        layers.append("all")

        # make the list unique but maintain order (dicts keep order for python>3.7)
        layers = list(dict.fromkeys(layers))

        # draw all "unmanaged" axes (e.g. axes that are found in the figure but
        # not in the blit-manager)
        # TODO would be nice to find a better way to handle this!
        # - NOTE: this must be done before drawing managed artists to properly support
        #   temporary artists on unmanaged axes!
        for ax in self._get_unmanaged_axes():
            ax.draw(renderer)

        # redraw artists from the selected layers and explicitly provided artists
        # (sorted by zorder for each layer)
        layer_artists = list(
            sorted(self._artists.get(layer, []), key=self._get_artist_zorder)
            for layer in layers
        )

        with ExitStack() as stack:
            # avoid drawing the background-patches of managed (dynamic) axes
            # since they might interfere with consecutive draws issued by callbacks
            for ax_i in self._managed_axes:
                stack.enter_context(
                    ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                )

            for a in chain(*layer_artists, artists):
                fig.draw_artist(a)

    def _get_unmanaged_artists(self):
        # return all artists not explicitly managed by the blit-manager
        # (e.g. any artist added via cartopy or matplotlib functions)
        managed_artists = set(
            chain(
                *self._bg_artists.values(),
                *self._artists.values(),
                self._ignored_unmanaged_artists,
            )
        )

        axes = {m.ax for m in (self._m, *self._m._children) if m.ax is not None}

        allartists = set()
        for ax in axes:
            # only include axes titles if they are actually set
            # (otherwise empty artists appear in the widget)
            titles = [
                i
                for i in (ax.title, ax._left_title, ax._right_title)
                if len(i.get_text()) > 0
            ]

            axartists = {
                *ax._children,
                *titles,
                *([ax.legend_] if ax.legend_ is not None else []),
            }

            allartists.update(axartists)

        return allartists.difference(managed_artists)

    def _clear_all_temp_artists(self):
        for method in self._m.cb._methods:
            container = getattr(self._m.cb, method, None)
            if container:
                container._clear_temporary_artists()
            self._clear_temp_artists(method)

    def _clear_temp_artists(self, method, forward=True):
        # clear artists from connected methods
        if method == "_click_move" and forward:
            self._clear_temp_artists("click", False)
        elif method == "click" and forward:
            self._clear_temp_artists("_click_move", False)
        elif method == "pick" and forward:
            self._clear_temp_artists("click", True)
        elif method == "on_layer_change" and forward:
            self._clear_temp_artists("pick", False)
            self._clear_temp_artists("click", True)
            self._clear_temp_artists("move", False)

        if method == "on_layer_change":
            # clear all artists from "on_layer_change" list irrespective of the method
            artists = self._artists_to_clear.pop("on_layer_change", [])
            for art in artists:
                for met, met_artists in self._artists_to_clear.items():
                    if art in met_artists:
                        art.set_visible(False)
                        self.remove_artist(art)
                        try:
                            art.remove()
                        except ValueError:
                            # ignore errors if the artist no longer exists
                            pass
                        met_artists.remove(art)
        else:
            artists = self._artists_to_clear.pop(method, [])
            while len(artists) > 0:
                art = artists.pop(-1)
                art.set_visible(False)
                self.remove_artist(art)
                try:
                    art.remove()
                except ValueError:
                    # ignore errors if the artist no longer exists
                    pass

                try:
                    self._artists_to_clear.get("on_layer_change", []).remove(art)
                except ValueError:
                    # ignore errors if the artist is not present in the list
                    pass

    def _get_showlayer_name(self, layer=None, transparent=False):
        # combine all layers that should be shown
        # (e.g. to add spines, backgrounds and inset-maps)

        if layer is None:
            layer = self.bg_layer

        # pass private layers through
        if layer.startswith("__"):
            return layer

        if transparent is True:
            show_layers = [layer, "__SPINES__"]
        else:
            show_layers = ["__BG__", layer, "__SPINES__"]

        # show inset map layers and spines only if they contain at least 1 artist
        inset_Q = False
        for l in layer.split("|"):
            narts = len(self._bg_artists.get("__inset_" + l, []))

            if narts > 0:
                show_layers.append(f"__inset_{l}")
                inset_Q = True

        if inset_Q:
            show_layers.append("__inset___SPINES__")

        return self._m._get_combined_layer_name(*show_layers)

    def update(
        self,
        layers=None,
        bbox_bounds=None,
        bg_layer=None,
        artists=None,
        clear=False,
        blit=True,
        clear_snapshot=True,
    ):
        """
        Update the screen with animated artists.

        Parameters
        ----------
        layers : list, optional
            The layers to redraw (if None and artists is None, all layers will be redrawn).
            The default is None.
        bbox_bounds : tuple, optional
            the blit-region bounds to update. The default is None.
        bg_layer : int, optional
            the background-layer name to restore. The default is None.
        artists : list, optional
            A list of artists to update.
            If provided NO layer will be automatically updated!
            The default is None.
        clear : bool, optional
            If True, all temporary artists tagged for removal will be cleared.
            The default is False.
        blit : bool, optional
            If True, figure.cavas.blit() will be called to update the figure.
            If False, changes will only be visible on the next blit-event!
            The default is True.
        clear_snapshot : bool, optional
            Only relevant if the `inline` backend is used in a jupyter-notebook
            or an Ipython console.

            If True, clear the active cell before plotting a snapshot of the figure.
            The default is True.
        """
        if self._disable_update:
            # don't update during layout-editing
            return

        cv = self.canvas

        if bg_layer is None:
            bg_layer = self.bg_layer

        for action in self._before_update_actions:
            action()

        if clear:
            self._clear_temp_artists(clear)

        # restore the background
        # add additional layers (background, spines etc.)
        show_layer = self._get_showlayer_name()

        if show_layer not in self._bg_layers:
            # make sure the background is properly fetched
            self.fetch_bg(show_layer)

        cv.restore_region(self._get_background(show_layer))

        # execute after restore actions (e.g. peek layer callbacks)
        while len(self._after_restore_actions) > 0:
            action = self._after_restore_actions.pop(0)
            action()

        # draw all of the animated artists
        self._draw_animated(layers=layers, artists=artists)
        if blit:
            # workaround for nbagg backend to avoid glitches
            # it's slow but at least it works...
            # check progress of the following issuse
            # https://github.com/matplotlib/matplotlib/issues/19116
            if self._mpl_backend_force_full:
                cv._force_full = True

            if bbox_bounds is not None:

                class bbox:
                    bounds = bbox_bounds

                cv.blit(bbox)
            else:
                # update the GUI state
                cv.blit(self.figure.bbox)

        # execute all actions registered to be called after blitting
        while len(self._after_update_actions) > 0:
            action = self._after_update_actions.pop(0)
            action()

        # let the GUI event loop process anything it has to do
        # don't do this! it is causing infinite loops
        # cv.flush_events()

        if (
            blit
            and not getattr(self._m, "_snapshotting", False)
            and BlitManager._snapshot_on_update is True
        ):
            self._m.snapshot(clear=clear_snapshot)

    def blit_artists(self, artists, bg="active", blit=True):
        """
        Blit artists (optionally on top of a given background)

        Parameters
        ----------
        artists : iterable
            the artists to draw
        bg : matpltolib.BufferRegion, None or "active", optional
            A fetched background that is restored before drawing the artists.
            The default is "active".
        blit : bool
            Indicator if canvas.blit() should be called or not.
            The default is True
        """
        cv = self.canvas
        renderer = self._get_renderer()
        if renderer is None:
            _log.error("EOmaps: encountered a problem while trying to blit artists...")
            return

        # restore the background
        if bg is not None:
            if bg == "active":
                bg = self._get_active_bg()
            cv.restore_region(bg)

        for a in artists:
            self.figure.draw_artist(a)

        if blit:
            cv.blit()

    def _get_restore_bg_action(
        self,
        layer,
        bbox_bounds=None,
        alpha=1,
        clip_path=None,
        set_clip_path=False,
    ):
        """
        Update a part of the screen with a different background
        (intended as after-restore action)

        bbox_bounds = (x, y, width, height)
        """
        if bbox_bounds is None:
            bbox = self.figure.bbox
        else:
            bbox = Bbox.from_bounds(*bbox_bounds)

        def action():
            renderer = self._get_renderer()
            if renderer is None:
                return

            if self.bg_layer == layer:
                return

            # TODO properly check if this is necessary...
            # update to make sure spines etc. are properly displayed
            # self.update()

            x0, y0, w, h = bbox.bounds

            # make sure to restore the initial background
            init_bg = renderer.copy_from_bbox(self._m.f.bbox)
            # convert the buffer to rgba so that we can add transparency
            buffer = self._get_background(layer, cache=True)
            self.canvas.restore_region(init_bg)

            x = buffer.get_extents()
            ncols, nrows = x[2] - x[0], x[3] - x[1]

            argb = (
                np.frombuffer(buffer, dtype=np.uint8).reshape((nrows, ncols, 4)).copy()
            )
            argb = argb[::-1, :, :]

            argb[:, :, -1] = (argb[:, :, -1] * alpha).astype(np.int8)

            gc = renderer.new_gc()

            gc.set_clip_rectangle(bbox)
            if set_clip_path is True:
                gc.set_clip_path(clip_path)

            renderer.draw_image(
                gc,
                int(x0),
                int(y0),
                argb[int(y0) : int(y0 + h), int(x0) : int(x0 + w), :],
            )
            gc.restore()

        return action

    def cleanup_layer(self, layer):
        """Trigger cleanup methods for a given layer."""
        self._cleanup_bg_artists(layer)
        self._cleanup_artists(layer)
        self._cleanup_bg_layers(layer)
        self._cleanup_on_layer_activation(layer)

    def _cleanup_bg_artists(self, layer):
        if layer not in self._bg_artists:
            return

        artists = self._bg_artists[layer]
        while len(artists) > 0:
            a = artists.pop()
            try:
                self.remove_bg_artist(a, layer)
                # no need to remove spines (to avoid NotImplementedErrors)!
                if not isinstance(a, Spine):
                    a.remove()
            except Exception:
                _log.debug(f"EOmaps-cleanup: Problem while clearing bg artist:\n {a}")

        del self._bg_artists[layer]

    def _cleanup_artists(self, layer):
        if layer not in self._artists:
            return

        artists = self._artists[layer]
        while len(artists) > 0:
            a = artists.pop()
            try:
                self.remove_artist(a)
                # no need to remove spines (to avoid NotImplementedErrors)!
                if not isinstance(a, Spine):
                    a.remove()
            except Exception:
                _log.debug(
                    f"EOmaps-cleanup: Problem while clearing dynamic artist:\n {a}"
                )

        del self._artists[layer]

    def _cleanup_bg_layers(self, layer):
        try:
            # remove cached background-layers
            if layer in self._bg_layers:
                del self._bg_layers[layer]
        except Exception:
            _log.debug(
                "EOmaps-cleanup: Problem while clearing cached background layers"
            )

    def _cleanup_on_layer_activation(self, layer):

        try:
            # remove not yet executed lazy-activation methods
            # (e.g. not yet fetched WMS services)
            if layer in self._on_layer_activation:
                del self._on_layer_activation[layer]
        except Exception:
            _log.debug(
                "EOmaps-cleanup: Problem while clearing layer activation methods"
            )

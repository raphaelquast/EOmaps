# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""A collection of useful helper-functions."""

import logging
from itertools import tee
import re
import sys
from importlib import import_module
from textwrap import indent, dedent
from functools import wraps, lru_cache
import warnings

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.transforms import Bbox, TransformedBbox
from matplotlib.backend_bases import KeyEvent

import importlib.metadata
from packaging import version

mpl_version = version.parse(importlib.metadata.version("matplotlib"))

_log = logging.getLogger(__name__)


def _parse_log_level(level):
    """
    Get the numerical log-level from string (or number).

    Parameters
    ----------
    level : str or number
        The log level

    Returns
    -------
    int_level : float
        The numerical value of the log level.

    """

    levels = logging.getLevelNamesMapping()

    if isinstance(level, str) and level.upper() in levels:
        use_level = levels[level.upper()]
    else:
        use_level = float(level)

    return use_level


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
        if ax.figure is None:
            return TransformedBbox(
                Bbox.from_bounds(*self._bounds),
                self._transform,
            )

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

            dx = np.abs(self._m._data_manager.x0_1D - x[0])
            dy = np.abs(self._m._data_manager.y0_1D - x[1])

            if k > 1 and pick_relative_to_closest is True:
                # mask datapoints outside the "search_radius"
                dx, dy = dx[dx < d], dy[dy < d]
                if len(dx) == 0 or len(dy) == 0:
                    return None

                ix = np.argmin(dx)
                iy = np.argmin(dy)
                # query again (starting from the closest point)
                return self.query(
                    (self._m._data_manager.x0_1D[ix], self._m._data_manager.y0_1D[iy]),
                    k=k,
                    d=d,
                    pick_relative_to_closest=False,
                )
            else:
                # perform a brute-force search for 1D coords
                ix = np.argpartition(dx, range(k))[:k]
                iy = np.argpartition(dy, range(k))[:k]

                # mask datapoints outside the "search_radius"
                ix, iy = ix[dx[ix] < d], iy[dy[iy] < d]
                if len(ix) == 0 or len(iy) == 0:
                    return None

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

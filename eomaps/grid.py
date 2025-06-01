# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Grid lines and grid labels."""

import logging
from itertools import chain
from functools import lru_cache

import numpy as np

from matplotlib.collections import LineCollection

_log = logging.getLogger(__name__)


def _ccw(A, B, C):
    # determine if 3 points are listed in a counter-clockwise order
    return (C[..., 1] - A[..., 1]) * (B[..., 0] - A[..., 0]) > (
        B[..., 1] - A[..., 1]
    ) * (C[..., 0] - A[..., 0])


def _intersect(A, B, C, D):
    # determine if 2 line-segments intersect with each other
    # see https://stackoverflow.com/a/9997374/9703451
    # see https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/

    A, B, C, D = map(np.atleast_2d, (A, B, C, D))
    return np.logical_and(
        _ccw(A, C, D) != _ccw(B, C, D),
        _ccw(A, B, C) != _ccw(A, B, D),
    )


def _get_intersect(a1, a2, b1, b2):
    # get the intersection-point between 2 lines defined by points
    # taken from https://stackoverflow.com/a/42727584/9703451

    s = np.vstack([a1, a2, b1, b2])  # s for stacked
    h = np.hstack((s, np.ones((4, 1))))  # h for homogeneous
    l1 = np.cross(h[0], h[1])  # get first line
    l2 = np.cross(h[2], h[3])  # get second line
    x, y, z = np.cross(l1, l2)  # point of intersection
    if z == 0:  # lines are parallel
        return (float("inf"), float("inf"))
    return (x / z, y / z)


class GridLines:
    """
    Base class for EOmaps grid-lines (and associated grid-labels).

    Note
    ----
    To add new grid-lines to a map, see
    :py:meth:`Maps.add_gridlines <eomaps.eomaps.Maps.add_gridlines>`.

    """

    def __init__(
        self, m, d=None, auto_n=10, layer=None, bounds=None, n=100, dynamic=False
    ):
        self.m = m._proxy(m)

        self._d = d
        self._auto_n = auto_n
        self._bounds = bounds
        self._n = n

        self._kwargs = dict()
        self._coll = None

        self._layer = layer
        self._grid_labels = []

        self._dynamic = dynamic

    @property
    def d(self):
        """The fixed grid-spacing distance (if specified)."""
        return self._d

    @property
    def layer(self):
        """The layer assigned to the grid"""
        if self._layer is None:
            return self.m.layer
        else:
            return self._layer

    @property
    def auto_n(self):
        """Number of automatic grid-lines to evaluate (if d=None)"""
        return self._auto_n

    @property
    def n(self):
        """Number of intermediate points to draw for each gridline"""
        return self._n

    @property
    def bounds(self):
        """The boundaries of the grid"""
        if self._bounds is None:
            return (-180, 180, -90, 90)
        return self._bounds

    def set_bounds(self, bounds):
        """
        Set the extent of the area in which gridlines are drawn.

        Parameters
        ----------
        bounds : tuple or None
            A tuple of boundaries in the form:  (lon_min, lon_max, lat_min, lat_max).
            If None, global boundaries are used (e.g. (-180, 180, -90, 90))

        """
        self._bounds = bounds
        self._redraw()
        self.m.redraw(self.layer)

    def set_d(self, d):
        """
        Set a fixed gridline distance (in degrees).

        Parameters
        ----------
        d : int, float, tuple, list, numpy.array or None
            Set the properties (separation or specific coordinates) for a fixed grid.

            - If `int` or `float`, the provided number is used as grid-spacing.
            - If a `list` or `numpy.array` is provided, it is used to draw gridlines
              at the provided coordinates.
            - If a `2-tuple` is provided, it represents separate assignments of
              the aforementioned types for longitude/latitude , e.g.: `(d_lon, d_lat)`.
            - If `None`, gridlines are automatically determined based on the "auto_n"
              parameter.

        The default is None
        """
        self._d = d
        self._redraw()
        self.m.redraw(self.layer)

    def set_auto_n(self, auto_n):
        """
        Set the number of (auto) gridlines to draw in the currently visible extent.

        Note: this is an approximate value!

        Parameters
        ----------
        auto_n : int or tuple of int
            The (rough) number of gridlines to use when evaluating the automatic
            grid-spacing. To use different numbers of gridlines in each direction,
            provide a tuple of ints, e.g.: `(n_lon, n_lat)`.

        """
        self._auto_n = auto_n
        self._redraw()
        self.m.redraw(self.layer)

    def set_n(self, n):
        """
        Set the number of intermediate points to calculate for each gridline.

        Parameters
        ----------
        n : int
            Number of intermedate points.

        """
        self._n = n
        self._redraw()
        self.m.redraw(self.layer)

    def _update_line_props(self, **kwargs):
        color = None
        if "c" in kwargs:
            color = kwargs.pop("c", None)
        if "color" in kwargs:
            color = kwargs.pop("color", None)

        if color is not None:
            kwargs["edgecolor"] = color

        self._kwargs.update(kwargs)

    def update_line_props(self, **kwargs):
        """
        Set/update the properties of the drawn lines (e.g. color, linewidth etc.).

        Any kwargs accepted by `matplotlib.collections.LineCollection` are supported.

        Commonly used parameters are:

        - "edgecolor" (or "ec" or "color" or "c"): the color of the lines
        - "linewidth" (or "lw"): the linewidth
        - "linestyle" (or "ls"): the linestyle to use

        Parameters
        ----------
        kwargs :
            keyword-arguments used to update the properties of the lines.

        """
        self._update_line_props(**kwargs)
        self._redraw()
        self.m.redraw(self.layer)

    @staticmethod
    def _calc_lines(d, bounds, n=100):
        lons, lats, dlon, dlat = None, None, None, None

        if isinstance(d, tuple):
            # tuples are used to
            if len(d) == 2:
                if isinstance(d[0], (list, tuple, np.ndarray)):
                    lons = np.asanyarray(d[0])
                else:
                    dlon = d[0]

                if isinstance(d[1], (list, tuple, np.ndarray)):
                    lats = np.asanyarray(d[1])
                else:
                    dlat = d[1]
            else:
                raise TypeError(
                    "EOmaps: If you provide a tuple as grid-spacing "
                    "'d=(dlon, dlat)' it must contain 2 items!"
                )
        elif isinstance(d, (int, float, np.number)):
            dlon = dlat = d
        elif isinstance(d, (list, np.ndarray)):
            if len(d) == 2:
                lons, lats = np.asanyarray(d[0]), np.asanyarray(d[1])
            else:
                lons = lats = np.asanyarray(d)
        else:
            raise TypeError(f"EOmaps: d={d} is not a valid grid-spacing.")

        # evaluate line positions if no explicit positions are provided
        if lons is None:
            if dlon is not None:
                lons = np.arange(bounds[0], bounds[1] + dlon, dlon)
                lons = lons[lons <= bounds[1]]
                lons = lons[lons >= bounds[0]]
            else:
                lons = np.array([])

        if lats is None:
            if dlat is not None:
                lats = np.arange(bounds[2], bounds[3] + dlat, dlat)
                lats = lats[lats <= bounds[3]]
                lats = lats[lats >= bounds[2]]
            else:
                lats = np.array([])

        lines = [
            np.linspace([x, bounds[2]], [x, bounds[3]], n, endpoint=True)
            for x in np.unique(lons.clip(*bounds[:2]))
        ]

        linesy = [
            np.linspace([bounds[0], y], [bounds[1], y], n, endpoint=True)
            for y in np.unique(lats.clip(*bounds[2:]))
        ]

        return lines, linesy

    @lru_cache()
    def _get_lines(self):
        if self.d is not None:
            return self._calc_lines(self.d, self.bounds, self.n)
        else:
            return self._get_auto_grid_lines()

    def _round_up(self, a, precision=0):
        return np.true_divide(np.ceil(a * 10**precision), 10**precision)

    def _get_auto_grid_lines(self):
        if isinstance(self.auto_n, tuple):
            nlon, nlat = self.auto_n
        else:
            nlon = nlat = self.auto_n

        extent = self.m.get_extent(self.m.CRS.PlateCarree(globe=self.m.crs_plot.globe))

        x0, _, y0, _ = np.max((self.bounds, extent), axis=0)
        _, x1, _, y1 = np.min((self.bounds, extent), axis=0)

        bounds = np.array([x0, x1, y0, y1])

        b_lon = bounds[1] - bounds[0]
        b_lat = bounds[3] - bounds[2]

        # get the magnitudes
        glon = 10 ** np.floor(np.log10(b_lon))
        glat = 10 ** np.floor(np.log10(b_lat))

        bounds[0] = max(-180, bounds[0] - bounds[0] % glon)
        bounds[1] = min(180, bounds[1] - bounds[1] % glon + glon)
        bounds[2] = max(-90, bounds[2] - bounds[2] % glat)
        bounds[3] = min(90, bounds[3] - bounds[3] % glat + glat)

        dlon, dlat = (bounds[1] - bounds[0]) / nlon, (bounds[3] - bounds[2]) / nlat
        # round auto-separation distances to 2 significant digits
        dlon = self._round_up(dlon, -int(np.log10(dlon)) + 2)
        dlat = self._round_up(dlat, -int(np.log10(dlat)) + 2)

        if nlon == nlat:
            dlon = dlat = min(dlon, dlat)

        lons = np.arange(bounds[0], min(180 + dlon, bounds[1] + 10 * dlon), dlon)
        lats = np.arange(bounds[2], min(90 + dlat, bounds[3] + 10 * dlat), dlat)

        lines = [
            np.linspace(
                [x, max(lats[0], self.bounds[2])],
                [x, min(lats[-1], self.bounds[3])],
                self.n,
                endpoint=True,
            )
            for x in np.unique(lons.clip(*self.bounds[:2]))
        ]
        linesy = [
            np.linspace(
                [max(lons[0], self.bounds[0]), y],
                [min(lons[-1], self.bounds[1]), y],
                self.n,
                endpoint=True,
            )
            for y in np.unique(lats.clip(*self.bounds[2:]))
        ]

        # lines.extend(linesy)

        # return np.array(lines)
        return lines, linesy

    def _get_coll(self, **kwargs):
        lines = np.array(list(chain(*self._get_lines())))
        if len(lines) == 0:
            return

        l0, l1 = lines[..., 0], lines[..., 1]

        l0, l1 = self.m._transf_lonlat_to_plot.transform(l0, l1)

        coll = LineCollection(np.dstack((l0, l1)), **kwargs)
        return coll

    def _add_grid(self, **kwargs):
        self._update_line_props(**kwargs)

        self._coll = self._get_coll(**self._kwargs)
        if self._coll is not None:
            # exclude artist in companion widget editor
            self._coll.set_label("__EOmaps_exclude")

            self.m.ax.add_collection(self._coll)
            # don't trigger draw since this would result in a recursion!
            # (_redraw is called on each fetch-bg event)
            if self._dynamic:
                self.m.BM.add_artist(self._coll, layer=self.layer)
            else:
                self.m.BM.add_bg_artist(self._coll, layer=self.layer, draw=False)

    def _redraw(self):
        self._get_lines.cache_clear()
        try:
            self._remove()
        except Exception as ex:
            # catch exceptions to avoid issues with dynamic re-drawing of
            # invisible grids
            pass

        self._add_grid()

        for l in self._grid_labels:
            l._redraw()

    def _remove(self):
        if self._coll is None:
            return

        # don't trigger draw since this would result in a recursion!
        # (_redraw is called on each fetch-bg event)
        if self._dynamic:
            self.m.BM.remove_artist(self._coll, layer=self.layer)
        else:
            self.m.BM.remove_bg_artist(self._coll, layer=self.layer, draw=False)

        try:
            self._coll.remove()
        except ValueError:
            pass

        self._coll = None

    def remove(self):
        """Remove the grid from the map."""
        self._remove()

        factory = self.m.parent._grid
        if self in factory._gridlines:
            factory._gridlines.remove(self)

        for gl in self._grid_labels:
            gl.remove()

        if self._dynamic is False:
            self.m.redraw(self.layer)

    def add_labels(
        self,
        where="tblr",
        offset=10,
        precision=2,
        every=None,
        exclude="corners",
        labels=None,
        rotation=0,
        rotation_relative=True,
        **kwargs,
    ):
        """
        Add labels to the gridlines.

        Parameters
        ----------
        where : str or int, optional
            Specify where labels should be added to the gridlines.

            In general, the position of labels is determined by the intersection-points
            of the gridlines with the axis-boundary.

            To select specific labels, use one of the following options:

            - Use a combination of the letters `"tblr"` (top, bottom, left, right) to
              draw labels only at the selected sides of the plot.
              (NOTE: With this option, latitude-lines are labeled only on "l" and "r",
              and longitude-lines are labeled only on "t" and "b"!)
            - Use `"all"` to add all labels without any restrictions
            - Use an integer to add labels only to the nth found intersection point
              (e.g. 0 for the first intersection-point, 1 for the second etc.)

            The default is "tblr".
        offset : number or tuple of numbers, optional
            The offset of the labels relative to the intersection point of the
            gridline with the axes-boundary.

            - number (d): the offset in the direction of of the rotation of the label.
            - 2-tuple (x, y): the offset in x- and y- direction.
            - 3-tuple (d, x, y): all of the above

            The default is 10.
        precision : int, optional
            The floating point precision of the labels.
            The default is 2.
        every : int, slice, tuple or None, optional
            Specify if all labels (None) or only every nth label should be drawn.

            - if int: draw every nth label
            - if 3-tuple: draw every nth label according to `(start, stop, step)`
              (use stop=-1 if you want to draw all labels)

            The default is None.
        exclude : str, list, tuple or None, optional
            Exclude one (or more) labels.

            - A list of grid values to exclude as lon/lat labels. (e.g. `[10, -45]`)
            - Provide a tuple of lists to exclude lon/lat values separately
              (e.g. `([-120, 60], [-40, 40])`).
            - If `"corners"`, the corner-points of the boundaries are excluded (this
              is the default to avoid overlapping lon/lat labels at the corners).
            - If `None`, no points are excluded.

            The default is "corners".
        labels : list or None, optional
            A list of strings to use as custom labels.
            If None, the grid-values are used.
            The default is None.
        rotation : float, optional
            The rotation of the label. The default is 0.
        rotation_relative : bool, optional
            Indicator if the rotation is performed relative to the current
            label-rotation (True) or the rotation is set to the provided value (False).
            The default is True.
        kwargs :
            Additional kwargs passed to matplotlib's `plt.text(...)` for additional
            styling of the labels.
            (e.g. fontsize, fontweight, color, ...)

        Returns
        -------
        gl : GridLabels
            The class that handles the drawing of the grid-labels.

        """
        gl = GridLabels(
            self,
            where=where,
            offset=offset,
            precision=precision,
            every=every,
            exclude=exclude,
            labels=labels,
            rotation=rotation,
            rotation_relative=rotation_relative,
            **kwargs,
        )
        gl.add_labels()

        # remember attached labels
        self._grid_labels.append(gl)

        if self._dynamic is False:
            self.m.redraw(self.layer)

        return gl


class GridLabels:
    """Class to draw grid-labels."""

    def __init__(
        self,
        g,
        where="tblr",
        offset=10,
        precision=2,
        every=None,
        exclude="corners",
        labels=None,
        rotation=0,
        rotation_relative=True,
        **kwargs,
    ):
        self._g = g
        self._texts = []

        self._last_extent = None
        self._last_ax_pos = None
        self._last_dpi = None  # to avoid wrong label positions on dpi changes
        self._default_dpi = 100

        if isinstance(where, int):
            self._where = "all"
            # draw only the nth found point
            self._n_pts = slice(where, where + 1)
        else:
            self._where = where
            # label max. 2 points (to avoid issues with corner points etc.)
            self._n_pts = slice(0, 2, 1)

        self._labels = labels
        self._rotation_relative = rotation_relative
        self._precision = precision
        self._every = every
        self._kwargs = kwargs

        self._set_offset(offset)
        self._set_rotation(rotation)
        self._set_exclude(exclude)

        # in case a custom boundary is used for gridlines,
        # draw the labels only inside the axes
        if self._g._bounds is not None:
            self._kwargs.setdefault("clip_on", True)
            self._kwargs.setdefault("clip_box", self._g.m.ax.bbox)
        self._g.m.BM._before_fetch_bg_actions.append(self._redraw)

    def _set_exclude(self, exclude):
        # a list of tick values to exclude
        if exclude is None:
            self._exclude = ([], [])
        elif isinstance(exclude, str) and exclude == "corners":
            # if grid-labels are added to a grid that uses a custom boundary,
            # exclude corner-values by default to avoid overlaps
            bnds = self._g._bounds
            if bnds is not None:
                self._exclude = (bnds[:2], bnds[2:])
            else:
                self._exclude = ([-180, 180], [-90, 90])

        elif isinstance(exclude, (list, np.ndarray)):
            self._exclude = (exclude, exclude)
        elif isinstance(exclude, tuple):
            self._exclude = exclude
        else:
            raise TypeError(f"EOmaps: {exclude} is not a valid value for exclude.")

    def _set_offset(self, offset):
        # float                 : offset in text-rotation direction (r)
        # (float, float)        : offsets in x-y direction (x, y)
        # (float, float, float) : both (r, x, y)

        if isinstance(offset, (int, float, np.number)):
            self._offset = (0, 0)
            self._relative_offset = offset
        elif len(offset) == 2:
            self._offset = offset
            self._relative_offset = 0
        elif len(offset) == 3:
            self._offset = (offset[1], offset[2])
            self._relative_offset = offset[0]

    def _set_rotation(self, rotation):
        self._rotation = np.deg2rad(rotation)

    def _remove(self):
        while len(self._texts) > 0:
            try:
                t = self._texts.pop(-1)
                try:
                    t.remove()
                except ValueError:
                    pass

                if self._g._dynamic:
                    self._g.m.BM.remove_artist(t)
                else:
                    self._g.m.BM.remove_bg_artist(t, draw=False)
            except Exception:
                _log.exception("EOmaps: Problem while trying to remove a grid-label:")
                pass

    def remove(self):
        """Remove the grid-labels from the map."""
        if self._redraw in self._g.m.BM._before_fetch_bg_actions:
            self._g.m.BM._before_fetch_bg_actions.remove(self._redraw)

        self._remove()

    def _redraw(self, **kwargs):
        try:
            m = self._g.m
            extent = m.get_extent(self._g.m.crs_plot)
            pos = m.ax.get_position()
            dpi = m.f.dpi

            if (
                self._last_ax_pos is not None
                and self._last_extent is not None
                and self._last_dpi is not None
                and self._last_dpi == dpi
                and self._last_extent == extent
                and self._last_ax_pos.bounds == pos.bounds
            ):
                return

            self._last_extent = extent
            self._last_ax_pos = pos

            self._remove()

            self.add_labels()
        except Exception:
            _log.exception(
                "EOmaps: Encountered a problem while re-drawing grid-labels:"
            )
            pass

    def _get_bound_verts(self, n=300):
        # get vertices of the grid-boundaries with n intermediate points
        m = self._g.m
        if self._g._bounds is not None:
            x0, x1, y0, y1 = self._g.bounds

            xs, ys = np.linspace([x0, y0], [x1, y1], n).T
            x0, y0, x1, y1, xs, ys = np.broadcast_arrays(x0, y0, x1, y1, xs, ys)
            verts = np.column_stack(
                ((x0, ys), (xs, y1), (x1, ys[::-1]), (xs[::-1], y0))
            ).T

            verts = m._transf_lonlat_to_plot.transform(*verts.T)
            verts = m.ax.transData.transform(np.column_stack(verts))
        else:
            m.ax.spines["geo"]._adjust_location()
            verts = m.ax.spines["geo"].get_verts()
        return verts

    def _get_spine_intersections(self, lines, axis=None):

        m = self._g.m

        # get boundary vertices of current axis spine (in figure coordinates)
        bl = self._get_bound_verts()
        bndmin, bndmax = bl.min(axis=0), bl.max(axis=0)

        # get gridlines
        uselines = np.array(lines[axis])

        if len(uselines) == 0:
            return

        # get the tick-label values
        tick_label_values = [*uselines[:, 0, axis]]

        # elongate the gridlines to make sure they reach outside the spine or boundary
        # (elongate in lon/lat for grids defined inside the axes (e.g. with bounds))
        if self._g._bounds is not None:
            uselines[:, 0, 0 if axis == 1 else 1] -= 0.1
            uselines[:, -1, 0 if axis == 1 else 1] += 0.1

        # get gridline vertices in plot-coordinates
        lines_plot = np.stack(
            m._transf_lonlat_to_plot.transform(uselines[..., 0], uselines[..., 1]),
            axis=-1,
        )

        # transform grid-lines to figure coordinates
        lines_fig = m.ax.transData.transform(lines_plot.reshape(-1, 2)).reshape(
            uselines.shape
        )

        # elongate the gridlines to make sure they reach outside the spine or boundary
        # (do this in figure coordinates for gridlines outside the axes since otherwise
        # the transformations would result in infinite values!)
        if self._g._bounds is None:
            lines_fig[:, 0, 0 if axis == 1 else 1] -= 0.01
            lines_fig[:, -1, 0 if axis == 1 else 1] += 0.01

        tr = m.ax.transData.inverted()
        tr_ax = m.ax.transAxes.inverted()

        # TODO would be nice to vectorize over gridlines as well
        intersection_points = dict()
        for l, label in zip(lines_fig, tick_label_values):
            if axis == 0 and label == -180:
                label = 180.0
            if axis == 1 and label == -90:
                label = 90.0

            if label in self._exclude[axis]:
                continue

            label = np.format_float_positional(
                label, precision=self._precision, trim="-", fractional=True
            ) + ("°E" if axis == 0 else "°N")

            l0x, l0y, l1x, l1y, b0x, b0y, b1x, b1y = np.broadcast_arrays(
                l[:-1, 0],
                l[:-1, 1],
                l[1:, 0],
                l[1:, 1],
                bl[:-1, 0][:, np.newaxis],
                bl[:-1, 1][:, np.newaxis],
                bl[1:, 0][:, np.newaxis],
                bl[1:, 1][:, np.newaxis],
            )

            l0 = np.stack((l0x, l0y), axis=2)
            l1 = np.stack((l1x, l1y), axis=2)
            b0 = np.stack((b0x, b0y), axis=2)
            b1 = np.stack((b1x, b1y), axis=2)

            q = _intersect(l0, l1, b0, b1)

            for la, lb, ba, bb in zip(l0[q], l1[q], b0[q], b1[q]):
                x, y = _get_intersect(la, lb, ba, bb)

                xt, yt = tr_ax.transform((x, y))

                # TODO find a better way to identify position of label
                # select which lines to draw (e.g. tblr)
                if self._where != "all":
                    if axis == 0:
                        if xt > 0.99 or xt < 0.01:
                            continue

                        line_in_bnds = l[:, 1].clip(bndmin[1], bndmax[1])
                        line_center = (
                            np.nanmin(line_in_bnds) + np.nanmax(line_in_bnds)
                        ) / 2
                        top = y > line_center
                        if top:
                            if not ("t" in self._where):
                                continue
                        else:
                            if not ("b" in self._where):
                                continue
                    else:
                        if yt > 0.99 or yt < 0.01:
                            continue

                        line_in_bnds = l[:, 0].clip(bndmin[0], bndmax[0])
                        line_center = (
                            np.nanmin(line_in_bnds) + np.nanmax(line_in_bnds)
                        ) / 2
                        right = x > line_center
                        if right:
                            if not ("r" in self._where):
                                continue
                        else:
                            if not ("l" in self._where):
                                continue

                # calculate rotation angle of boundary segment
                r = np.pi + np.arctan2(
                    (ba[1] - bb[1]),
                    (ba[0] - bb[0]),
                )

                r = (r + self._rotation) if self._rotation_relative else self._rotation

                # add offset to label positions
                x = (
                    x
                    - self._relative_offset * np.sin(r) * m.f.dpi / self._default_dpi
                    + self._offset[0]
                )
                y = (
                    y
                    + self._relative_offset * np.cos(r) * m.f.dpi / self._default_dpi
                    + self._offset[1]
                )

                # round to avoid "jumpy" labels
                x, y = np.round((x, y))

                intersection_points.setdefault(label, list()).append([x, y, r])

        return intersection_points

    def _get_grid_line_intersections(self, lines, axis=0):
        # calculate intersection point of a grid witih a set of lines

        if self._every:
            if isinstance(self._every, int):
                every = slice(0, -1, self._every)
            elif isinstance(self._every, (list, tuple)) and len(self._every) <= 3:
                every = slice(*self._every)
            elif isinstance(self._every, slice):
                every = self._every
            else:
                raise TypeError(
                    f"EOmaps: {self._every} is not a valid input for 'every'"
                )
            uselines = [i[every] for i in lines]
        else:
            uselines = lines

        intersection_points = self._get_spine_intersections(uselines, axis=axis)

        return intersection_points

    def _add_axis_labels(self, lines, axis):
        m = self._g.m

        if self._kwargs is None:
            txt_kwargs = dict()
        else:
            txt_kwargs = self._kwargs

        intersection_points = self._get_grid_line_intersections(lines, axis)

        if intersection_points is None:
            return

        transf = m.f.transFigure
        transf_inv = transf.inverted()

        if len(intersection_points) > 0:
            # make sure only unique pairs of coordinates are used
            # pts = np.unique(np.rec.fromarrays(pts)).view((pts.dtype, 2)).T
            for i, (label, pts) in enumerate(intersection_points.items()):
                # TODO currently we take only the first 2 points
                # to avoid issues with 180° lines etc.
                for (x, y, r) in pts[self._n_pts]:
                    if self._rotation_relative:
                        r = np.rad2deg(r)
                        # make sure that labels on straight axes are oriented the same
                        if r == 180:
                            r = 0
                        if r == 270:
                            r = 90

                        r = r + self._rotation
                    else:
                        r = self._rotation

                    if self._labels is None:
                        uselabel = label
                    else:
                        # use the provided labels (keep existing if None)
                        uselabel = self._labels[i]
                        if uselabel is None:
                            uselabel = label

                    # route positions through dpi_scale_trans to avoid wrong positioning
                    # on figure export with different dpi since (x, y) are in
                    # display-coordinates!
                    x, y = transf_inv.transform((x, y))
                    t = m.ax.text(
                        x,
                        y,
                        uselabel,
                        transform=transf,  # None,
                        animated=True,
                        rotation=r,
                        ha="center",
                        va="center",
                        **txt_kwargs,
                    )
                    # exclude artist in companion widget editor
                    t.set_label("__EOmaps_exclude")

                    if self._g._dynamic:
                        m.BM.add_artist(t, layer=self._g.layer)
                    else:
                        m.BM.add_bg_artist(t, layer=self._g.layer, draw=False)
                    self._texts.append(t)

    def add_labels(self):
        """
        Add labels to the grid.
        """
        m = self._g.m
        lines = self._g._get_lines()
        aspect = m.ax.bbox.height / m.ax.bbox.width

        if self._where == "all":
            use_axes = (0, 1)
        else:
            use_axes = []
            if "t" in self._where or "b" in self._where:
                use_axes.append(0)
            if "l" in self._where or "r" in self._where:
                use_axes.append(1)

        for axis in use_axes:
            self._add_axis_labels(lines=lines, axis=axis)


class GridFactory:
    """Class to handle grids on a map."""

    def __init__(self, m):
        self.m = m
        self._gridlines = []
        self.m.BM._before_fetch_bg_actions.append(self._update_autogrid)

    def add_grid(
        self,
        d=None,
        auto_n=10,
        n=100,
        bounds=None,
        layer=None,
        *,
        m=None,
        labels=False,
        dynamic=False,
        **kwargs,
    ):
        """
        Add gridlines to the map.

        By default, an appropriate grid-spacing is determined via the "auto_n" kwarg.

        An explicit grid-spacing can be used by providing the grid-separation
        via the "d" kwarg.

        Parameters
        ----------
        d : int, float, 2-tuple, list, numpy.array or None
            Set the location of the gridlines (for a fixed grid).

            - For a regular grid with a fixed spacing, provide a number or a `tuple`
              of numbers to set the lon/lat distance between the grid-lines.

              >>> d = 10       # a regular 10 degree grid
              >>> d = (5, 10)  # a regular grid with d_lon=5 and d_lat=10

            - To draw only specific gridlines, provide a `tuple` of lists or
              numpy-arrays of (lon, lat) values.

              >>> d = ([lon0, lon1, lon2, ...], [lat0, lat1, ...])

            - If `d = None`, gridlines are automatically determined based on
              the "auto_n" parameter.

            The default is None
        auto_n : int or 2-tuple
            Only relevant if "d" is None!
            The (rough) number of gridlines to use when evaluating the automatic
            grid-spacing. To use different numbers of gridlines in each direction,
            provide a tuple of ints, e.g.: `(n_lon, n_lat)`.
            The default is 10.
        layer : str
            The name of the layer on which the gridlines should be visible.
        bounds : 4-tuple
            A tuple of boundaries to limit the gridlines to a given extent.
            (lon_min, lon_max, lat_min, lat_max)
            The default is None in which case (-180, 180, -90, 90) is used.
        n : int
            The number of intermediate points to draw for each line.
            (e.g. to nicely draw curved grid lines)
            The default is 100
        labels : bool or dict, optional
            If True, add grid-labels to the map.
            If a dict is provided, it is passed to :py:meth:`GridLines.add_labels`.

            This is a shortcut for using:

            >>> g = m.add_gridlines()
            >>> g.add_labels(fontsize=7, color="b", ...)

            The default is False.
        kwargs :
            Additional kwargs passed to matplotlib.collections.LineCollection.

            The default is: (ec="0.2", lw=0.5, zorder=100)

        Other Parameters
        ----------------
        clip_on: bool, optional
            If True, clip the gridlines at the map-boundary.
            If False, clip the gridliens at the figure-boundary.
            This is useful if you want gridlines to extend beyond custom map-boundaries
            set with :py:meth:`Maps.set_frame`.
            Note: This has to be set for the grid-labels as well!

        Returns
        -------
        g : GridLines
            The GridLines-object.

        Note
        ----
        To add labels to the grid, use:

        >>> g = m.add_gridlines(...)
        >>> g.add_labels(...)

        Examples
        --------
        >>> m = Maps(Maps.CRS.InterruptedGoodeHomolosine())
        >>> m.add_feature.preset.ocean()
        >>> g0 = m.add_gridlines(d=10, ec=".5", lw=0.25, zorder=1, layer="g")
        >>> g1 = m.add_gridlines(d=(10, 20), ec="k", lw=0.5, zorder=2, layer="g")
        >>> g2 = m.add_gridlines(d=5, ec="darkred", lw=0.25, zorder=0,
        >>>                      bounds=(-20, 40, -20, 60), layer="g")
        >>> m.show_layer(m.layer, "g")

        """
        fc = kwargs.pop("facecolor", "none")
        ec = kwargs.pop("edgecolor", ".2")
        lw = kwargs.pop("linewidth", 0.5)

        kwargs.setdefault("fc", fc)
        kwargs.setdefault("ec", ec)
        kwargs.setdefault("lw", lw)
        kwargs.setdefault("zorder", 100)

        g = GridLines(
            m=m, d=d, auto_n=auto_n, n=n, bounds=bounds, layer=layer, dynamic=dynamic
        )
        g._add_grid(**kwargs)
        self._gridlines.append(g)

        if labels:
            if labels is True:
                g.add_labels()
            elif isinstance(labels, dict):
                g.add_labels(**labels)
            else:
                raise TypeError(f"{labels} is not a valid input for labels")

        self.m.f.canvas.draw_idle()
        return g

    def _update_autogrid(self, *args, **kwargs):
        for g in self._gridlines:
            if g.d is None:
                try:
                    g._redraw()
                except Exception as ex:
                    # catch exceptions to avoid issues with dynamic re-drawing of
                    # invisible grids
                    continue

from matplotlib.collections import LineCollection
import numpy as np


class GridLines:
    def __init__(
        self, m, d=None, auto_n=10, layer=None, bounds=(-180, 180, -90, 90), n=100
    ):
        self.m = m._proxy(m)

        self._d = d
        self._auto_n = auto_n
        self._bounds = bounds
        self._n = n

        self._kwargs = dict()
        self._coll = None

        self._layer = layer

    @property
    def d(self):
        return self._d

    @property
    def layer(self):
        return self._layer

    @property
    def auto_n(self):
        return self._auto_n

    @property
    def n(self):
        return self._n

    @property
    def bounds(self):
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
        if bounds is None:
            bounds = (-180, 180, -90, 90)
        self._bounds = bounds
        self._redraw()

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
            - If a `tuple` of lengh 2 is provided, it represents separate assignments of
              the aforementioned types for longitude/latitude , e.g.: `(d_lon, d_lat)`.
            - If `None`, gridlines are automatically determined based on the "auto_n"
              parameter.

        The default is None
        """
        self._d = d
        self._redraw()

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

    def _get_lines(self):
        lons, lats = None, None

        if self.d is not None:
            if isinstance(self.d, tuple):
                # tuples are used to
                if len(self.d) == 2:
                    if all(isinstance(i, (int, float, np.number)) for i in self.d):
                        dlon, dlat = self.d
                    elif all(isinstance(i, (list, np.ndarray)) for i in self.d):
                        dlon = dlat = "manual"
                        lons, lats = map(np.asanyarray, self.d)
                else:
                    raise TypeError(
                        f"EOmaps: If you provide a tuple as grid-spacing "
                        "'d=(dlon, dlat)' it must contain 2 items!"
                    )
            elif isinstance(self.d, (int, float, np.number)):
                dlon = dlat = self.d
            elif isinstance(self.d, (list, np.ndarray)):
                dlon = dlat = "manual"
                lons = lats = np.asanyarray(self.d)
            else:
                raise TypeError(f"EOmaps: d={self.d} is not a valid grid-spacing.")

            # evaluate line positions if no explicit positions are provided
            if lons is None and lats is None:
                if all(isinstance(i, (int, float, np.number)) for i in (dlon, dlat)):
                    lons = np.arange(self.bounds[0], self.bounds[1] + dlon, dlon)
                    lats = np.arange(self.bounds[2], self.bounds[3] + dlat, dlat)
                else:
                    raise TypeError("EOmaps: dlon and dlat must be numbers!")

            lines = [
                np.linspace(
                    [x, self.bounds[2]], [x, self.bounds[3]], self.n, endpoint=True
                )
                for x in np.unique(lons.clip(*self.bounds[:2]))
            ]
            linesy = [
                np.linspace(
                    [self.bounds[0], y], [self.bounds[1], y], self.n, endpoint=True
                )
                for y in np.unique(lats.clip(*self.bounds[2:]))
            ]
            lines.extend(linesy)

            return np.array(lines)

        else:
            return self._get_auto_grid_lines()

    def _round_up(self, a, precision=0):
        return np.true_divide(np.ceil(a * 10**precision), 10**precision)

    def _get_auto_grid_lines(self):
        if isinstance(self.auto_n, tuple):
            nlon, nlat = self.auto_n
        else:
            nlon = nlat = self.auto_n

        extent = self.m.ax.get_extent(self.m.CRS.PlateCarree())

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

        lines.extend(linesy)

        return np.array(lines)

    def _get_coll(self, **kwargs):
        lines = self._get_lines()

        l0, l1 = lines[..., 0], lines[..., 1]

        l0, l1 = self.m._transf_lonlat_to_plot.transform(l0, l1)

        coll = LineCollection(np.dstack((l0, l1)), **kwargs)
        return coll

    def _add_grid(self, **kwargs):
        self._update_line_props(**kwargs)

        self._coll = self._get_coll(**self._kwargs)

        self.m.ax.add_collection(self._coll)
        self.m.BM.add_bg_artist(self._coll, layer=self.layer)

    def _redraw(self):
        try:
            self._remove()
        except Exception as ex:
            # catch exceptions to avoid issues with dynamic re-drawing of
            # invisible grids
            pass
        self._add_grid()

    def _remove(self):
        if self._coll is None:
            return

        self.m.BM.remove_bg_artist(self._coll, layer=self.layer)
        try:
            self._coll.remove()
        except ValueError:
            pass

        self._coll = None

    def remove(self):
        """Remove the grid from the map."""
        self._remove()

        if self in self.m._grid._gridlines:
            self.m._grid._gridlines.remove(self)


class GridFactory:
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
            Set the properties (separation or specific coordinates) for a fixed grid.

            - If `int` or `float`, the provided number is used as grid-spacing.
            - If a `list` or `numpy.array` is provided, it is used to draw gridlines
              at the provided coordinates.
            - If a `tuple` of lengh 2 is provided, it represents separate assignments of
              the aforementioned types for longitude/latitude , e.g.: `(d_lon, d_lat)`.
            - If `None`, gridlines are automatically determined based on the "auto_n"
              parameter.

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
        kwargs :
            Additional kwargs passed to matplotlib.collections.LineCollection.

            The default is: (ec="0.2", lw=0.5, zorder=100)

        Returns
        -------
        m_grid : EOmaps.Maps
            The Maps-object used to draw the gridlines.

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

        if bounds is None:
            bounds = (-180, 180, -90, 90)

        g = GridLines(m=m, d=d, auto_n=auto_n, n=n, bounds=bounds, layer=layer)
        g._add_grid(**kwargs)
        self._gridlines.append(g)

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

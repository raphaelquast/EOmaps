# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Plot shape classes (for data visualization)."""

import logging
from functools import partial, wraps
from contextlib import contextmanager, ExitStack

from matplotlib.collections import PolyCollection, QuadMesh, TriMesh
from matplotlib.tri import Triangulation
from matplotlib.collections import Collection

from pyproj import CRS
import numpy as np

from .helpers import register_modules, version, mpl_version


_log = logging.getLogger(__name__)


# a base class for shapes that support setting the number of intermediate points
class _ShapeBase:
    name = "none"

    def __init__(self, m):
        self._m = m
        self._n = None

        self._select_radius = True

    def _get_auto_n(self):
        s = self._m._data_manager._get_current_datasize()

        if self.name == "rectangles":
            # mesh currently only supports n=1
            if self.mesh is True:
                return 1

            # if plot crs is same as input-crs there is no need for
            # intermediate points since the rectangles are not curved!
            if self._m._crs_plot == self._m.data_specs.crs:
                return 1

        if s < 10:
            n = 100
        elif s < 100:
            n = 75
        elif s < 1000:
            n = 50
        elif s < 10000:
            n = 20
        else:
            n = 12

        return n

    @property
    def n(self):
        if self._n is None:
            return self._get_auto_n()
        else:
            return self._n

    @n.setter
    def n(self, val):
        if self.name == "rectangles" and self.mesh is True:
            if val is not None and val != 1:
                _log.info("EOmaps: rectangles with 'mesh=True' only support n=1")
            self._n = 1
        else:
            self._n = val

    @property
    def _selected_radius(self):
        # option to override radius-selection in case the shape is used
        # to create markers (e.g. call is independent of plot-extent)
        if self._select_radius is False:
            return self.radius

        # if radius was provided as a array (for individual shape radius)
        # select values according to the dat-manager query to get values
        # of visible points

        # if no data is assigned, just return the radius
        if not self._m._data_manager._current_data:
            return self.radius

        # check if multiple individual x-y radius was provided
        q1 = isinstance(self.radius, tuple) and isinstance(self.radius[0], np.ndarray)
        # chedk if multiple radius values were provided
        q2 = isinstance(self.radius, np.ndarray)

        if q1 or q2:
            mask = self._m._data_manager._get_q()[0]

            # quick exit if full data is in extent
            if mask is True:
                return self.radius

        if q1:
            radius = (self.radius[0][mask], self.radius[1][mask])
        elif q2:
            radius = self.radius[mask]
        else:
            radius = self.radius

        return radius

    def _wraparound(self, x, y, xs, ys, crs):
        # ------------------------- implement some kind of "wraparound"
        if self._m._crs_plot in (
            self._m.CRS.Orthographic(),
            self._m.CRS.Geostationary(),
            self._m.CRS.NearsidePerspective(),
        ):
            # avoid masking in those crs
            mask = np.full(xs.shape[0], True)
        else:

            # check if any points are in different halfspaces with respect to x
            # and if so, mask the ones in the wrong halfspace
            # (required for proper longitude wrapping)
            # TODO this might be a lot easier (and faster) to implement!

            xc = 0  # the center-point (e.g. (-180 + 180)/2 = 0 )

            def getQ(x, xc):
                quadrants = np.full_like(x, -1)

                quadrant = x < xc
                quadrants[quadrant] = 0
                quadrant = x > xc
                quadrants[quadrant] = 1

                return quadrants

            t_in_lonlat = self._m._get_transformer(crs, 4326)
            t_plot_lonlat = self._m._get_transformer(self._m.crs_plot, 4326)

            # transform the coordinates to lon/lat
            xp, _ = t_in_lonlat.transform(x, y)
            xsp, _ = t_plot_lonlat.transform(xs, ys)

            quadrants, pts_quadrants = getQ(xp, xc), getQ(xsp, xc)

            # mask any point that is in a different quadrant than the center point
            maskx = pts_quadrants != quadrants[:, np.newaxis]
            # take care of points that are on the center line (e.g. don't mask them)
            # (use a +- 25 degree around 0 as threshold)
            cpoints = np.broadcast_to(
                np.isclose(xp, xc, atol=25)[:, np.newaxis], xs.shape
            )

            maskx[cpoints] = False
            xs.mask[maskx] = True
            ys.mask = xs.mask

            # mask any datapoint that has less than 3 of the ellipse-points unmasked
            mask = np.count_nonzero(~xs.mask, axis=1) >= 3

        return xs, ys, mask


class _CircularShapeBase(_ShapeBase):
    name = "circular_shape_base"
    radius_crs = None

    def __init__(self, m):
        super().__init__(m=m)

    def __call__(self, radius=None, n=None, radius_crs=None):
        if radius is None:
            raise TypeError(
                f"EOmaps: If 'm.set_shape.{self.name}(...)' is used, "
                "you must provide a radius!"
            )

        from . import MapsGrid  # do this here to avoid circular imports!

        for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
            shape = self.__class__(m)
            shape.radius = radius
            shape.radius_crs = radius_crs
            shape.n = n

            m._shape = shape

    @property
    def _initargs(self):
        return dict(radius=self._radius, radius_crs=self.radius_crs, n=self._n)

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, val):
        # string is required to accept "estimate" as radius
        # tuple is required to provide (rx, ry) explicitly
        if isinstance(val, (int, float, str, tuple, np.number)):
            self._radius = val
        else:
            self._radius = np.asanyarray(np.atleast_1d(val)).ravel()

    def __repr__(self):
        try:
            s = f"{self.name}(radius={self.radius}, n={self.n})"
        except AttributeError:
            s = f"{self.name}(radius, n)"
        except Exception:
            s = object.__repr__(self)

        return s

    def _get_points(self, x, y, crs, radius, n=20):
        raise NotImplementedError("get_points is not implemented")
        xs, ys, mask = [], [], []
        return xs, ys, mask

    def get_coll(self, x, y, crs, **kwargs):
        xs, ys, mask = self._get_points(
            x=x,
            y=y,
            crs=crs,
            radius=self._selected_radius,
            radius_crs=self.radius_crs,
            n=self.n,
        )
        # compress the coordinates (masked arrays produce artefacts on the boundary
        # in case intermediate points are masked)
        verts = (
            np.column_stack((x.compressed(), y.compressed()))
            for i, (x, y) in enumerate(zip(xs, ys))
            if mask[i]
        )
        # remember masked points
        self._m._data_mask = mask

        color_and_array = Shapes._get_colors_and_array(kwargs, mask)

        coll = PolyCollection(
            verts,
            # transOffset=self._m.ax.transData,
            **color_and_array,
            **kwargs,
        )

        return coll


class _CollectionAccessor:
    """
    Accessor class to handle contours drawn by plt.contour.

    The main purpose of this class is to serve as a single Artist-like container
    that executes relevant functions on ALL collections returned by plt.contour.

    The `ContourSet` returned by plt.contour is accessible via `.contour_set`

    To add labels to the contours on the map, use:

    >>> m = Maps()
    >>> m.set_data(...)
    >>> m.set_shape.contour()
    >>> m.plot_map()
    >>>
    >>> labels = m3_1.ax.clabel(m.coll.contour_set)
    >>> for i in labels:
    >>>     m.BM.add_bg_artist(i, layer=m.layer)

    """

    def __init__(self, cont, filled):
        self.contour_set = cont
        self._filled = filled

        self._label = ""
        self.collections = self.contour_set.collections

        # TODO check why cmap and norm are not properly set on the collections
        # of the contourplot ("over", "under" colors etc. get lost)
        for c in self.collections:
            c.set_cmap(self.cmap)
            c.set_norm(self.norm)

        methods = [
            f
            for f in dir(Collection)
            if (callable(getattr(Collection, f)) and not f.startswith("__"))
        ]

        custom_funcs = [i for i in dir(self) if not i.startswith("__")]
        for name in methods:
            if name not in custom_funcs:
                setattr(self, name, self._get_func_for_all_colls(name))

    def __getattr__(self, name):
        return getattr(self.collections[0], name)

    def _get_func_for_all_colls(self, name):
        @wraps(getattr(self.collections[0], name))
        def cb(*args, **kwargs):
            returns = []
            for c in self.collections:
                returns.append(getattr(c, name)(*args, **kwargs))
            return returns

        return cb

    def get_zorder(self):
        return self.collections[0].get_zorder()

    @property
    def levels(self):
        return self.contour_set.levels

    @property
    def norm(self):
        return self.contour_set.norm

    @property
    def cmap(self):
        return self.contour_set.cmap

    def get_label(self):
        return self._label

    def set_label(self, s):
        self._label = s
        for i, c in enumerate(self.collections):
            c.set_label(f"__EOmaps_exclude {s} (level {i})")

    @contextmanager
    def _cm_set(self, **kwargs):
        with ExitStack() as stack:
            try:
                for c in self.collections:
                    stack.enter_context(c._cm_set(**kwargs))
                yield
            finally:
                pass


class Shapes(object):
    """
    Set the plot-shape to represent the data-points.

    By default, "ellipses" is used for datasets smaller than 500k pixels and shading
    with "shade_raster" is used for larger datasets (if datashader is installed).

    Possible shapes are:
    (check the individual docs for details!)

        - Projected ellipses

        >>> m.set_shape.ellipses(radius, radius_crs)

        - Projected rectangles

        >>> m.set_shape.rectangles(radius, radius_crs, mesh)

        - Projected geodetic circles

        >>> m.set_shape.geod_circles(radius)

        - Voronoi diagram

        >>> m.set_shape.voronoi_diagram(masked, mask_radius)

        - Delaunay triangulation

        >>> m.set_shape.delaunay_triangulation(masked, mask_radius, mask_radius_crs, flat)

        - Point-based shading

        >>> m.set_shape.shade_points(aggregator, shade_hook, agg_hook)

        - Raster-based shading

        >>> m.set_shape.delaunay_triangulation(aggregator, shade_hook, agg_hook)

    Attributes
    ----------
    _radius_estimation_range : int
        The number of datapoints to use for estimating the radius of a shape.
        (only relevant if the radius is not specified explicitly.)
        The default is 100000

    """

    _shp_list = [
        "geod_circles",
        "ellipses",
        "rectangles",
        "raster",
        "voronoi_diagram",
        "delaunay_triangulation",
        "shade_points",
        "shade_raster",
    ]

    def __init__(self, m):
        self._m = m
        self._radius_estimation_range = 100000

    def _get(self, shape, **kwargs):
        # get the name of the class for a given shape
        # (CamelCase without underscores)
        shapeclass_name = "_" + "".join(i.capitalize() for i in shape.split("_"))

        shp = getattr(self, shapeclass_name)(self._m)
        shp._select_radius = False  # disable radius selection based on dataset

        for key, val in kwargs.items():
            setattr(shp, key, val)
        return shp

    @staticmethod
    def _get_radius(m, radius, radius_crs):
        if (isinstance(radius, str) and radius == "estimate") or radius is None:
            if m._estimated_radius is None:
                # make sure props are defined otherwise we can't estimate the radius!
                if m._data_manager.x0 is None:
                    m._data_manager.set_props(None)

                # check if the first element of x0 is nonzero...
                # (to avoid slow performance of np.any for large arrays)
                if not np.any(m._data_manager.x0.take(0)):
                    return None

                _log.info("EOmaps: Estimating shape radius...")
                radiusx, radiusy = Shapes._estimate_radius(m, radius_crs)

                if radiusx == radiusy:
                    _log.info(
                        "EOmaps: radius = "
                        f"{np.format_float_scientific(radiusx, precision=4)}"
                    )
                else:
                    _log.info(
                        "EOmaps: radius = "
                        f"({np.format_float_scientific(radiusx, precision=4)}, "
                        f"{np.format_float_scientific(radiusy, precision=4)})"
                    )
                radius = (radiusx, radiusy)
                # remember estimated radius to avoid re-calculating it all the time
                m._estimated_radius = (radiusx, radiusy)
            else:
                radius = m._estimated_radius
        else:
            # get manually specified radius (e.g. if radius != "estimate")
            if isinstance(radius, (list, np.ndarray)):
                radiusx = radiusy = np.asanyarray(radius).ravel()
            elif isinstance(radius, tuple):
                radiusx, radiusy = radius
            elif isinstance(radius, (int, float, np.number)):
                radiusx = radiusy = radius
            else:
                radiusx = radiusy = radius

            radius = (radiusx, radiusy)
        return radius

    @staticmethod
    def _estimate_radius(m, radius_crs, method=np.nanmedian):
        assert radius_crs in [
            "in",
            "out",
        ], "radius can only be estimated if radius_crs is 'in' or 'out'!"

        if m._data_manager.x0_1D is not None:
            x, y = m._data_manager.x0_1D, m._data_manager.y0_1D
        else:
            if radius_crs == "in":
                x, y = m._data_manager.xorig, m._data_manager.yorig
            elif radius_crs == "out":
                x, y = m._data_manager.x0, m._data_manager.y0

        radius = None
        # try to estimate radius for 2D datasets
        if len(x.shape) == 2 and len(y.shape) == 2:
            userange = int(np.sqrt(m.set_shape._radius_estimation_range))

            radiusx = method(np.diff(x[:userange, :userange], axis=1)) / 2
            if radiusx == 0:
                radiusx = method(np.diff(x[:userange, :userange].T, axis=1)) / 2

            radiusy = method(np.diff(y[:userange, :userange], axis=0)) / 2
            if radiusy == 0:
                radiusy = method(np.diff(y[:userange, :userange].T, axis=0)) / 2

            radius = (radiusx, radiusy)

            if not np.isfinite(radius).all() or not all(i > 0 for i in radius):
                radius = None

        # for 1D datasets (or if 2D radius-estimation fails), use the median distance
        # of 3 neighbours of the first N datapoints (N=shape._radius_estimation_range)
        if radius is None:
            from scipy.spatial import cKDTree

            # take care of 2D data with 1D coordinates
            if m._data_manager.x0_1D is not None:
                userange = int(np.sqrt(m.set_shape._radius_estimation_range))
                x, y = np.meshgrid(x[:userange], y[:userange])
                x, y = x.flat, y.flat
            else:
                x = x.flat[: m.set_shape._radius_estimation_range]
                x = x[np.isfinite(x)]
                y = y.flat[: m.set_shape._radius_estimation_range]
                y = y[np.isfinite(y)]

            in_tree = cKDTree(
                np.stack(
                    [
                        x,
                        y,
                    ],
                    axis=1,
                ),
                compact_nodes=False,
                balanced_tree=False,
            )

            dists, pts = in_tree.query(in_tree.data, min(len(in_tree.data), 3))
            # consider only neighbors
            # (the first entry is the search-point again!)
            pts = pts[:, 1:]
            # get the average distance between points having a distance > 0
            d = np.abs(in_tree.data[:, np.newaxis] - in_tree.data[pts]).reshape(-1, 2)

            use_dx = d[:, 0] > 0
            use_dy = d[:, 1] > 0
            if any(use_dx):
                radiusx = method(d[:, 0][use_dx]) / 2
            else:
                radiusx = np.nan

            if any(use_dy):
                radiusy = method(d[:, 1][use_dy]) / 2
            else:
                radiusy = np.nan

            rxOK = np.isfinite(radiusx) and (radiusx > 0)
            ryOK = np.isfinite(radiusy) and (radiusy > 0)
            if rxOK and ryOK:
                radius = (radiusx, radiusy)
            elif rxOK:
                radius = (radiusx, radiusx)
            elif ryOK:
                radius = (radiusy, radiusy)
            else:
                radius = None

        assert radius is not None, (
            "EOmaps: Radius estimation failed... maybe there's something wrong with "
            "the provided coordinates? "
            "You can manually specify a radius with 'm.set_shape.<SHAPE>(radius=...)' "
            "or you can increase the number of datapoints used to estimate the radius "
            "by increasing `m.set_shape._radius_estimation_range`."
        )

        return radius

    @staticmethod
    def _get_colors_and_array(kwargs, mask):
        # identify colors and the array
        # special treatment of array input to properly mask values
        array = kwargs.pop("array", None)
        if array is not None:
            if mask is not None:
                array = array[mask]
        else:
            array = None

        color_vals = dict()
        for c_key in ["fc", "facecolor", "color"]:
            color = kwargs.pop(c_key, None)

            if color is not None:
                # explicit treatment for recarrays (to avoid performance issues)
                # with matplotlib.colors.to_rgba_array()
                # (recarrays are used to convert 3/4 arrays into an rgb(a) array
                # in m._data_manager._handle_explicit_colors() )
                if isinstance(color, np.recarray):
                    color_vals[c_key] = color[mask.reshape(color.shape)].view(
                        (float, len(color.dtype.names))
                    )  # .ravel()
                elif isinstance(color, np.ndarray):
                    color_vals[c_key] = color[mask.reshape(color.shape)]
                else:
                    color_vals[c_key] = color

        if len(color_vals) == 0:
            return {"array": array}
        else:
            color_vals["array"] = None
            return color_vals

    class _GeodCircles(_CircularShapeBase):
        name = "geod_circles"

        def __init__(self, m):
            super().__init__(m=m)

        def __call__(self, radius=None, n=None):
            """
            Draw geodesic circles with a radius defined in meters.

            Parameters
            ----------
            radius : float or array-like
                The radius of the circles in meters.

                If you provide an array of sizes, each datapoint will be drawn with
                the respective size!
            n : int or None
                The number of intermediate points to calculate on the geodesic circle.
                If None, 100 is used for < 10k pixels and 20 otherwise.
                The default is None.

            Returns
            -------
            self
                The class representing the plot-shape.

            """
            super().__call__(radius=radius, n=n, radius_crs="geod")

        def _calc_geod_circle_points(self, lon, lat, radius, n=20, start_angle=0):
            """
            Calculate points on a geodetic circle with a given radius.

            Parameters
            ----------
            lon : array-like
                the longitudes
            lat : array-like
                the latitudes
            radius : float
                the radius in meters
            n : int, optional
                the number of points to calculate.
                The default is 10.
            start_angle : int, optional
                the starting angle for the points in radians

            Returns
            -------
            lons : array-like
                the longitudes of the geodetic circle points.
            lats : array-like
                the latitudes of the geodetic circle points.

            """
            size = lon.size

            if isinstance(radius, (int, float)):
                radius = np.full((size, n), radius)
            else:
                if radius.size != lon.size:
                    radius = np.broadcast_to(radius[:, None], (size, n))
                else:
                    radius = np.broadcast_to(radius.ravel()[:, None], (size, n))

            geod = self._m.crs_plot.get_geod()
            lons, lats, back_azim = geod.fwd(
                lons=np.broadcast_to(lon[:, None], (size, n)),
                lats=np.broadcast_to(lat[:, None], (size, n)),
                az=np.linspace(
                    [start_angle] * size, [360 - start_angle] * size, n, axis=1
                ),
                dist=radius,
                radians=False,
            )

            return lons, lats

        def _get_points(self, x, y, crs, radius, radius_crs="geod", n=20):
            crs = self._m.get_crs(crs)
            x, y = np.asarray(x), np.asarray(y)

            # transform from in-crs to lon/lat
            radius_t = self._m._get_transformer(
                crs,
                self._m.CRS.PlateCarree(globe=self._m.crs_plot.globe),
            )
            # transform from lon/lat to the plot_crs
            plot_t = self._m._get_transformer(
                self._m.CRS.PlateCarree(globe=self._m.crs_plot.globe),
                CRS.from_user_input(self._m.crs_plot),
            )

            lon, lat = radius_t.transform(x, y)
            # calculate some points on the geodesic circle
            lons, lats = self._calc_geod_circle_points(lon, lat, radius, n=n)

            xs, ys = np.ma.masked_invalid(plot_t.transform(lons, lats), copy=False)

            xs, ys, mask = self._wraparound(x, y, xs, ys, crs)

            return xs, ys, mask

    class _Ellipses(_CircularShapeBase):
        name = "ellipses"

        def __init__(self, m):
            super().__init__(m=m)

        def __call__(self, radius="estimate", radius_crs="in", n=None):
            """
            Draw projected ellipses with dimensions defined in units of a given crs.

            Parameters
            ----------
            radius : int, float, array-like or str, optional
                The radius in x- and y- direction.
                The default is "estimate" in which case the radius is attempted
                to be estimated from the input-coordinates.

                If you provide an array of sizes, each datapoint will be drawn with
                the respective size!
            radius_crs : crs-specification, optional
                The crs in which the dimensions are defined.
                The default is "in".
            n : int or None
                The number of intermediate points to calculate on the circle.
                If None, 100 is used for < 10k pixels and 20 otherwise.
                The default is None.
            """
            super().__call__(radius=radius, n=n, radius_crs=radius_crs)

        @_CircularShapeBase.radius.getter
        def radius(self):
            radius = Shapes._get_radius(self._m, self._radius, self.radius_crs)
            return radius

        def _calc_ellipse_points(self, x0, y0, a, b, theta, n, start_angle=0):
            """
            Calculate points on a rotated ellipse.

            Parameters
            ----------
            x0, y0 : array-like
                the center-position of the ellipse.
            a, b : array-like
                the ellipse half-axes.
            theta : array-like
                the rotation-angle of the ellipse.
            n : int
                the number of points to calculate on the ellipse.
            start_angle : float, optional
                the angle at which the ellipse-point calculation starts.
                The default is 0.

            Returns
            -------
            xs, ys : array-like
                the coordinates of the ellipse points.
            """

            a = np.broadcast_to(a[:, None], (x0.size, n))
            b = np.broadcast_to(b[:, None], (x0.size, n))

            theta = np.broadcast_to(theta[:, None], a.shape)

            angs = np.linspace(start_angle, 2 * np.pi + start_angle, n)

            angs = np.broadcast_to(angs, (x0.size, n))

            x0 = np.broadcast_to(x0[:, None], a.shape)
            y0 = np.broadcast_to(y0[:, None], a.shape)
            xs = (
                x0 + a * np.cos(angs) * np.cos(theta) - b * np.sin(angs) * np.sin(theta)
            )
            ys = (
                y0 + a * np.cos(angs) * np.sin(theta) + b * np.sin(angs) * np.cos(theta)
            )
            return (xs, ys)

        def _get_points(self, x, y, crs, radius, radius_crs="in", n=20):
            crs = self._m.get_crs(crs)
            radius_crs = self._m.get_crs(radius_crs)
            # transform from crs to the plot_crs
            t_in_plot = self._m._get_transformer(crs, self._m.crs_plot)
            # transform from crs to the radius_crs
            t_in_radius = self._m._get_transformer(crs, radius_crs)
            # transform from crs to the radius_crs
            t_radius_plot = self._m._get_transformer(radius_crs, self._m.crs_plot)

            if isinstance(radius, (int, float, np.number)):
                rx, ry = radius, radius
            else:
                rx, ry = radius

            # transform corner-points
            if radius_crs == crs:
                p = (x, y)
                xs, ys = self._calc_ellipse_points(
                    p[0],
                    p[1],
                    np.broadcast_to(rx, x.shape).astype(float),
                    np.broadcast_to(ry, y.shape).astype(float),
                    np.full_like(x, 0),
                    n=n,
                )
                xs, ys = np.ma.masked_invalid((xs, ys), copy=False)
                xs, ys = np.ma.masked_invalid(t_in_plot.transform(xs, ys), copy=False)
            else:
                p = t_in_radius.transform(x, y)
                xs, ys = self._calc_ellipse_points(
                    p[0],
                    p[1],
                    np.broadcast_to(rx, x.shape).astype(float),
                    np.broadcast_to(ry, y.shape).astype(float),
                    np.full_like(x, 0),
                    n=n,
                )

                xs, ys = np.ma.masked_invalid((xs, ys), copy=False)
                xs, ys = np.ma.masked_invalid(
                    t_radius_plot.transform(xs, ys), copy=False
                )

            xs, ys, mask = self._wraparound(x, y, xs, ys, crs)

            return xs, ys, mask

    class _Rectangles(_ShapeBase):
        name = "rectangles"

        def __init__(self, m):
            super().__init__(m=m)

        def __call__(self, radius="estimate", radius_crs="in", mesh=False, n=None):
            """
            Draw projected rectangles with fixed dimensions (and possibly curved edges).

            Parameters
            ----------
            radius : int, float, tuple or str, optional
                The radius in x- and y- direction.
                The default is "estimate" in which case the radius is attempted
                to be estimated from the input-coordinates.

                If you provide an array of sizes, each datapoint will be drawn with
                the respective size!
            radius_crs : crs-specification, optional
                The crs in which the dimensions are defined.
                The default is "in".
            mesh : bool
                Indicator if polygons (False) or a triangular mesh (True)
                should be plotted.

                Using polygons allows setting edgecolors, using a triangular mesh
                does NOT allow setting edgecolors but it has the advantage that
                boundaries between neighbouring rectangles are not visible.
                Only n=1 is currently supported!
            n : int or None
                The number of intermediate points to calculate on the rectangle edges
                (e.g. to properly plot "curved" rectangles in projected crs)
                Use n=1 to force rectangles!
                If None, 40 is used for <10k datapoints and 10 is used otherwise.
                The default is None
            """
            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)

                shape._radius = radius
                shape.radius_crs = radius_crs
                shape.mesh = mesh
                shape.n = n

                m._shape = shape

        @property
        def _initargs(self):
            return dict(
                radius=self._radius,
                radius_crs=self.radius_crs,
                n=self._n,
                mesh=self.mesh,
            )

        @property
        def radius(self):
            radius = Shapes._get_radius(self._m, self._radius, self.radius_crs)
            return radius

        @radius.setter
        def radius(self, val):
            if isinstance(val, (list, np.ndarray)):
                self._radius = np.asanyarray(val).ravel()
            else:
                self._radius = val

        def __repr__(self):
            try:
                s = f"rectangles(radius={self.radius}, radius_crs={self.radius_crs})"
            except AttributeError:
                s = "rectangles(radius, radius_crs)"

            return s

        def _get_rectangle_verts(self, x, y, crs, radius, radius_crs="in", n=4):
            in_crs = self._m.get_crs(crs)

            if isinstance(radius, (int, float, np.number)):
                rx, ry = radius, radius
            else:
                rx, ry = radius

            # transform corner-points
            if radius_crs == crs:
                in_crs = self._m.get_crs(crs)
                # transform from crs to the plot_crs
                t = self._m._get_transformer(
                    CRS.from_user_input(in_crs), self._m.crs_plot
                )

                # make sure we do not transform out of bounds (if possible)
                if in_crs.area_of_use is not None:
                    transformer = self._m._get_transformer(in_crs.geodetic_crs, in_crs)

                    xmin, ymin, xmax, ymax = transformer.transform_bounds(
                        *in_crs.area_of_use.bounds
                    )

                    clipx = partial(np.clip, a_min=xmin, a_max=xmax)
                    clipy = partial(np.clip, a_min=ymin, a_max=ymax)
                else:
                    clipx, clipy = lambda x: x, lambda y: y
                p = x, y

            else:
                r_crs = self._m.get_crs(radius_crs)

                # transform from crs to the radius_crs
                t_in_radius = self._m._get_transformer(in_crs, r_crs)
                # transform from radius_crs to the plot_crs
                t = self._m._get_transformer(r_crs, self._m.crs_plot)

                # make sure we do not transform out of bounds (if possible)
                if r_crs.area_of_use is not None:
                    transformer = self._m._get_transformer(r_crs.geodetic_crs, r_crs)

                    xmin, ymin, xmax, ymax = transformer.transform_bounds(
                        *r_crs.area_of_use.bounds
                    )

                    clipx = partial(np.clip, a_min=xmin, a_max=xmax)
                    clipy = partial(np.clip, a_min=ymin, a_max=ymax)
                else:
                    clipx, clipy = lambda x: x, lambda y: y

                p = t_in_radius.transform(x, y)

            px = np.column_stack(
                (
                    clipx(np.linspace(p[0] - rx, p[0] + rx, n)).T.flat,
                    clipx(np.repeat([p[0] + rx], n, axis=0)).T.flat,
                    clipx(np.linspace(p[0] + rx, p[0] - rx, n)).T.flat,
                    clipx(np.repeat([p[0] - rx], n)).T.flat,
                )
            )
            py = np.column_stack(
                (
                    clipy(np.repeat([p[1] + ry], n, axis=0)).T.flat,
                    clipy(np.linspace(p[1] + ry, p[1] - ry, n)).T.flat,
                    clipy(np.repeat([p[1] - ry], n, axis=0)).T.flat,
                    clipy(np.linspace(p[1] - ry, p[1] + ry, n)).T.flat,
                )
            )

            px, py = t.transform(px, py)

            px = (
                np.ma.masked_invalid(np.split(px, len(x)))
                .swapaxes(1, 2)
                .reshape(len(x), -1)
            )
            py = (
                np.ma.masked_invalid(np.split(py, len(x)))
                .swapaxes(1, 2)
                .reshape(len(x), -1)
            )

            verts = np.ma.stack((px.T, py.T), axis=0).T
            mask = np.count_nonzero(~verts.mask.any(axis=2), axis=1) >= 4

            verts = [i[~i.mask.any(axis=1)] for i in verts[mask]]

            return verts, mask

        def _get_polygon_coll(self, x, y, crs, **kwargs):
            verts, mask = self._get_rectangle_verts(
                x, y, crs, self._selected_radius, self.radius_crs, self.n
            )

            # remember masked points
            self._m._data_mask = mask
            color_and_array = Shapes._get_colors_and_array(kwargs, mask)

            coll = PolyCollection(
                verts=verts,
                # transOffset=self._m.ax.transData,
                **color_and_array,
                **kwargs,
            )

            return coll

        def _get_trimesh_rectangle_triangulation(
            self,
            x,
            y,
            crs,
            radius,
            radius_crs,
            n,
        ):

            verts, mask = self._get_rectangle_verts(x, y, crs, radius, radius_crs, n)
            verts = np.array(verts)

            x = np.vstack(
                [verts[:, 2][:, 0], verts[:, 3][:, 0], verts[:, 1][:, 0]]
            ).T.flat
            y = np.vstack(
                [verts[:, 2][:, 1], verts[:, 3][:, 1], verts[:, 1][:, 1]]
            ).T.flat

            x2 = np.vstack(
                [verts[:, 3][:, 0], verts[:, 0][:, 0], verts[:, 1][:, 0]]
            ).T.flat
            y2 = np.vstack(
                [verts[:, 3][:, 1], verts[:, 0][:, 1], verts[:, 1][:, 1]]
            ).T.flat

            x = np.append(x, x2)
            y = np.append(y, y2)

            tri = Triangulation(
                x, y, triangles=np.array(range(len(x))).reshape((len(x) // 3, 3))
            )
            return tri, mask

        def _get_trimesh_coll(self, x, y, crs, **kwargs):
            tri, mask = self._get_trimesh_rectangle_triangulation(
                x, y, crs, self._selected_radius, self.radius_crs, self.n
            )
            # remember masked points
            self._m._data_mask = mask

            color_and_array = Shapes._get_colors_and_array(kwargs, mask)

            def broadcast_colors_and_array(array):
                if array is None:
                    return
                # tri-contour meshes need 3 values for each triangle
                array = np.broadcast_to(array, (3, len(array))).T
                # we plot 2 triangles per rectangle
                array = np.broadcast_to(array, (2, *array.shape))

                return array.ravel()

            color_and_array = {
                key: broadcast_colors_and_array(val)
                for key, val in color_and_array.items()
            }

            coll = TriMesh(
                tri,
                # transOffset=self._m.ax.transData,
                **color_and_array,
                **kwargs,
            )

            return coll

        def get_coll(self, x, y, crs, **kwargs):
            if self.mesh is True:
                return self._get_trimesh_coll(x, y, crs, **kwargs)
            else:
                return self._get_polygon_coll(x, y, crs, **kwargs)

    class _Hexbin(object):
        name = "hexbin"

        def __init__(self, m):
            self._m = m

        def __call__(self, size=100, aggregator="mean"):
            """
            Draw a 2D hexagonal binning plot of the data.

            All arguments are forwarded to `matplotlib.pyplot.hexbin()`.

            Parameters
            ----------
            size : int, or (int, int), optional
                If int, the number of hexagons in x-direction.
                If a tuple of int is provided, the number of hexagons
                in x- and y-direction

                See matplotlib.pyplot.hexbin for more information about marker styles.
            aggregator: str or callable
                The function used to aggregate the data-values.
                If a string is provided, it is identified as the associated numpy
                function. The default is "mean".
            """
            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)
                shape._size = size
                shape._aggregator = aggregator
                m._shape = shape

        @property
        def _initargs(self):
            return dict(size=self._size, aggregator=self._aggregator)

        @property
        def radius(self):
            radius = Shapes._get_radius(self._m, "estimate", "in")
            return radius

        @property
        def radius_crs(self):
            return "in"

        def get_coll(self, x, y, crs, **kwargs):
            # hide edgecolors if they are not explicitly set (to avoid overlapping
            # hexagons due to large edge linewidths)
            # matplotlib's default is currently `ec="face", lw=1`
            if not any(i in kwargs for i in ("ec", "edgecolor")):
                special_kwargs = {"ec": "none"}
            else:
                special_kwargs = {}

            color_and_array = Shapes._get_colors_and_array(kwargs, None)

            if isinstance(self._aggregator, str):
                reduce_C_function = getattr(np, self._aggregator)
            else:
                reduce_C_function = self._aggregator

            color_and_array["C"] = color_and_array.pop("array", None)

            if "extent" not in kwargs:
                dm = self._m._data_manager

                extent = (dm._x0min, dm._x0max, dm._y0min, dm._y0max)

            coll = self._m.ax.hexbin(
                x,
                y,
                gridsize=self._size,
                reduce_C_function=reduce_C_function,
                extent=kwargs.get("extent", extent),
                **color_and_array,
                **kwargs,
                **special_kwargs,
            )
            return coll

    class _ScatterPoints(object):
        name = "scatter_points"

        def __init__(self, m):
            self._m = m

        def __call__(self, size=None, marker=None):
            """
            Draw each datapoint as a shape with a size defined in points**2.

            All arguments are forwarded to `m.ax.scatter()`.

            Parameters
            ----------
            size : int, float, array-like or str, optional
                The marker size in points**2.

                If you provide an array of sizes, each datapoint will be drawn with
                the respective size!
            marker : str
                The marker style. Can be either an instance of the class or the text
                shorthand for a particular marker. Some examples are:

                - `".", "o", "s", "<", ">", "^", "$A^2$"`

                See matplotlib.markers for more information about marker styles.
            """
            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)
                shape._size = np.asanyarray(size)  # always convert to numpy
                shape._marker = marker
                m._shape = shape

        @property
        def _initargs(self):
            return dict(size=self._size, marker=self._marker)

        @property
        def _selected_size(self):
            # chedck if multiple size values were provided
            if np.size(self._size) > 1:
                mask = self._m._data_manager._get_q()[0]

                # quick exit if full data is in extent
                if mask is True:
                    return self._size

                size = self._size[mask]
            else:
                size = self._size

            return size

        @property
        def radius(self):
            radius = Shapes._get_radius(self._m, "estimate", "in")
            return radius

        @property
        def radius_crs(self):
            return "in"

        def get_coll(self, x, y, crs, **kwargs):
            color_and_array = Shapes._get_colors_and_array(
                kwargs, np.full((x.size,), True)
            )
            color_and_array["c"] = color_and_array["array"]
            coll = self._m.ax.scatter(
                x,
                y,
                s=self._selected_size,
                marker=self._marker,
                **color_and_array,
                **kwargs,
            )
            return coll

    class _VoronoiDiagram(object):
        name = "voronoi_diagram"

        def __init__(self, m):
            self._m = m
            self._mask_radius = None

        def __call__(self, masked=True, mask_radius=None):
            """
            Draw a Voronoi-Diagram of the data.

            Parameters
            ----------
            masked : bool
                Indicator if the voronoi-diagram should be masked or not

            mask_radius : float, optional
                The radius used for masking the voronoi-diagram
                (in units of the plot-crs)
                The default is 4 times the estimated data-radius.
            """
            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)

                shape.mask_radius = mask_radius
                shape.masked = masked

                m._shape = shape

        @property
        def _initargs(self):
            return dict(mask_radius=self.mask_radius, masked=self.masked)

        def __repr__(self):
            try:
                s = f"voronoi_diagram(mask_radius={self.mask_radius}, masked={self.masked})"
            except AttributeError:
                s = "voronoi_diagram(mask_radius, masked)"

            return s

        @property
        def mask_radius(self):
            r = Shapes._get_radius(self._m, self._mask_radius, "out")
            if self._mask_radius is None:
                return [i * 4 for i in r]
            else:
                return r

        @mask_radius.setter
        def mask_radius(self, val):
            self._mask_radius = val

        def _get_voronoi_verts_and_mask(self, x, y, crs, radius, masked=True):
            try:
                from scipy.spatial import Voronoi
                from itertools import zip_longest
            except ImportError:
                raise ImportError("'scipy' is required for 'voronoi'!")

            # transform from crs to the plot_crs
            t_in_plot = self._m._get_transformer(self._m.get_crs(crs), self._m.crs_plot)

            x0, y0 = t_in_plot.transform(x, y)

            datamask = np.isfinite(x0) & np.isfinite(y0)
            [radiusx, radiusy] = radius

            maxdist = 2 * np.mean(np.sqrt(radiusx**2 + radiusy**2))

            xy = np.column_stack((x0[datamask], y0[datamask]))

            vor = Voronoi(xy)
            rect_regions = np.array(list(zip_longest(*vor.regions, fillvalue=-2))).T
            # (use -2 instead of None to make np.take work as expected)

            rect_regions = rect_regions[vor.point_region]
            # exclude all points at infinity
            mask = np.all(np.not_equal(rect_regions, -1), axis=1)
            # get the mask for the artificially added vertices
            rect_mask = rect_regions == -2

            x = np.ma.masked_array(
                np.take(vor.vertices[:, 0], rect_regions), mask=rect_mask
            )
            y = np.ma.masked_array(
                np.take(vor.vertices[:, 1], rect_regions), mask=rect_mask
            )
            rect_verts = np.ma.stack((x, y)).swapaxes(0, 1).swapaxes(1, 2)

            if masked:
                # exclude any polygon whose defining point is farther away than maxdist
                cdist = np.sqrt(np.sum((rect_verts - vor.points[:, None]) ** 2, axis=2))
                polymask = np.all(cdist < maxdist, axis=1)
                mask = np.logical_and(mask, polymask)

            verts = list(i.compressed().reshape(-1, 2) for i in rect_verts[mask])
            return verts, mask, datamask

        def get_coll(self, x, y, crs, **kwargs):

            verts, mask, datamask = self._get_voronoi_verts_and_mask(
                x, y, crs, self.mask_radius, masked=self.masked
            )

            # find the masked points that are not masked by the datamask
            mask2 = ~datamask.copy()
            mask2[np.where(datamask)[0][mask]] = True
            # remember the mask
            self._m._data_mask = mask2

            color_and_array = Shapes._get_colors_and_array(
                kwargs, np.logical_and(datamask, mask)
            )

            coll = PolyCollection(
                verts=verts,
                **color_and_array,
                # transOffset=self._m.ax.transData,
                **kwargs,
            )

            return coll

        @property
        def radius(self):
            radius = Shapes._get_radius(self._m, "estimate", "in")
            return radius

        @property
        def radius_crs(self):
            return "in"

    class _SphericalVoronoiDiagram(object):
        name = "spherical_voronoi_diagram"

        def __init__(self, m):
            self._m = m
            self._mask_radius = None

        def __call__(self, masked=True, mask_radius=None):
            """
            Draw a Spherical Voronoi-Diagram of the data.

            Parameters
            ----------
            masked : bool
                Indicator if the voronoi-diagram should be masked or not

            mask_radius : float, optional
                The radius used for masking the voronoi-diagram
                (in units of the plot-crs)
                The default is 4 times the estimated data-radius.
            """
            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)

                shape.mask_radius = mask_radius
                shape.masked = masked

                m._shape = shape

        @property
        def _initargs(self):
            return dict(mask_radius=self.mask_radius, masked=self.masked)

        def __repr__(self):
            try:
                s = f"voronoi_diagram(mask_radius={self.mask_radius}, masked={self.masked})"
            except AttributeError:
                s = "voronoi_diagram(mask_radius, masked)"

            return s

        @property
        def mask_radius(self):
            r = Shapes._get_radius(self._m, self._mask_radius, "out")
            if self._mask_radius is None:
                return [i * 4 for i in r]
            else:
                return r

        @mask_radius.setter
        def mask_radius(self, val):
            self._mask_radius = val

        def _get_voronoi_verts_and_mask(self, x, y, crs, radius, masked=True):
            try:
                from scipy.spatial import SphericalVoronoi
                from itertools import zip_longest
            except ImportError:
                raise ImportError("'scipy' is required for 'voronoi'!")

            # transform from crs to the lon/lat

            t_in_lonlat = self._m._get_transformer(
                self._m.get_crs(crs), self._m.get_crs(crs).geodetic_crs
            )

            t_lonlat_plot = self._m._get_transformer(
                self._m.get_crs(crs).geodetic_crs, self._m.crs_plot
            )

            xy_orig = np.column_stack((x, y))  # remember orig input coords

            x0, y0 = t_in_lonlat.transform(x, y)

            x0 = (x0 + 360) % 360
            y0 = (y0 + 180) % 180

            datamask = np.isfinite(x0) & np.isfinite(y0)
            [radiusx, radiusy] = radius

            maxdist = 2 * np.mean(np.sqrt(radiusx**2 + radiusy**2))

            xy = np.column_stack((x0[datamask], y0[datamask]))

            # plot the unit sphere for reference (optional)
            r = 1

            theta, phi = np.deg2rad(xy.T)
            x = r * np.cos(theta) * np.sin(phi)
            y = r * np.sin(theta) * np.sin(phi)
            z = r * np.cos(phi)

            vor = SphericalVoronoi(np.column_stack((x, y, z)), r, [0, 0, 0])
            vor.sort_vertices_of_regions()

            rect_regions = np.array(list(zip_longest(*vor.regions, fillvalue=-2))).T
            # (use -2 instead of None to make np.take work as expected)

            # rect_regions = rect_regions[vor.point_region]
            # exclude all points at infinity
            mask = np.all(np.not_equal(rect_regions, -1), axis=1)

            # get the mask for the artificially added vertices
            rect_mask = rect_regions == -2

            x_s = np.ma.masked_array(
                np.take(vor.vertices[:, 0], rect_regions), mask=rect_mask
            )
            y_s = np.ma.masked_array(
                np.take(vor.vertices[:, 1], rect_regions), mask=rect_mask
            )
            z_s = np.ma.masked_array(
                np.take(vor.vertices[:, 2], rect_regions), mask=rect_mask
            )

            # convert back to lon/lat
            x = np.rad2deg(np.arctan2(y_s, x_s))
            y = np.rad2deg(np.arccos(z_s / r))

            # convert back to the -180, 180 and -90, 90 range
            x = (x + 180) % 360 - 180
            y = (y + 90) % 180 - 90

            x, y = t_lonlat_plot.transform(x, y)

            rect_verts = np.ma.stack((x, y)).swapaxes(0, 1).swapaxes(1, 2)

            if masked:
                # exclude any polygon whose defining point is farther away than maxdist
                cdist = np.sqrt(np.sum((rect_verts - xy_orig[:, None]) ** 2, axis=2))
                polymask = np.all(cdist < maxdist, axis=1)
                mask = np.logical_and(mask, polymask)

            verts = list(i.compressed().reshape(-1, 2) for i in rect_verts[mask])
            return verts, mask, datamask

        def get_coll(self, x, y, crs, **kwargs):

            verts, mask, datamask = self._get_voronoi_verts_and_mask(
                x, y, crs, self.mask_radius, masked=self.masked
            )

            # find the masked points that are not masked by the datamask
            mask2 = ~datamask.copy()
            mask2[np.where(datamask)[0][mask]] = True
            # remember the mask
            self._m._data_mask = mask2

            color_and_array = Shapes._get_colors_and_array(
                kwargs, np.logical_and(datamask, mask)
            )

            coll = PolyCollection(
                verts=verts,
                **color_and_array,
                # transOffset=self._m.ax.transData,
                **kwargs,
            )

            return coll

        @property
        def radius(self):
            radius = Shapes._get_radius(self._m, "estimate", "in")
            return radius

        @property
        def radius_crs(self):
            return "in"

    class _DelaunayTriangulation(object):
        name = "delaunay_triangulation"

        def __init__(self, m):
            self._m = m
            self._mask_radius = None

        def __call__(
            self, masked=True, mask_radius=None, mask_radius_crs="in", flat=False
        ):
            """
            Draw a Delaunay-Triangulation of the data.

            Parameters
            ----------
            masked : bool
                Indicator if the delaunay-triangulation should be masked or not
            mask_radius : float, optional
                the radius used for masking the delaunay-triangulation
                (in units of the plot-crs)
                The default is 4 times the estimated data-radius.
            mask_radius_crs : str, optional
                The crs in which the radius is defined (either "in" or "out")
            flat : bool
                Indicator if a triangulation (flat=False) or polygons (flat=True)
                should be plotted. The default is False
            """
            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)

                shape.mask_radius = mask_radius
                shape.mask_radius_crs = mask_radius_crs
                shape.masked = masked
                shape.flat = flat

                m._shape = shape

        @property
        def _initargs(self):
            return dict(
                mask_radius=self.mask_radius,
                masked=self.masked,
                mask_radius_crs=self.mask_radius_crs,
                flat=self.flat,
            )

        def __repr__(self):
            try:
                s = (
                    f"delaunay_triangulation(mask_radius={self.mask_radius}, "
                    + f"mask_radius_crs={self.mask_radius_crs}, "
                    + f"masked={self.masked}, flat={self.flat})"
                )
            except AttributeError:
                s = "delaunay_triangulation(mask_radius, mask_radius_crs, masked, flat)"
            return s

        @property
        def mask_radius(self):
            if self.masked:
                r = Shapes._get_radius(self._m, self._mask_radius, self.mask_radius_crs)
                if self._mask_radius is None:
                    return [i * 4 for i in r]
                else:
                    return r
            else:
                return None

        @mask_radius.setter
        def mask_radius(self, val):
            self._mask_radius = val

        def _get_delaunay_triangulation(
            self, x, y, crs, radius, radius_crs="out", masked=True
        ):

            # prepare data
            try:
                from scipy.spatial import Delaunay
            except ImportError:
                raise ImportError("'scipy' is required for 'delaunay_triangulation'!")

            # transform from crs to the plot_crs
            t_in_plot = self._m._get_transformer(self._m.get_crs(crs), self._m.crs_plot)

            x0, y0 = t_in_plot.transform(x, y)
            datamask = np.isfinite(x0) & np.isfinite(y0)

            d = Delaunay(
                np.column_stack((x0[datamask], y0[datamask])), qhull_options="QJ"
            )

            tri = Triangulation(d.points[:, 0], d.points[:, 1], d.simplices)

            if masked:
                radiusx, radiusy = radius
                maxdist = 4 * np.mean(np.sqrt(radiusx**2 + radiusy**2))

                if radius_crs == "in":
                    # use input-coordinates for evaluating the mask
                    mx = self._m._data_manager._current_data["xorig"].ravel()
                    my = self._m._data_manager._current_data["yorig"].ravel()
                elif radius_crs == "out":
                    # use projected coordinates for evaluating the mask
                    mx = x
                    my = y
                else:
                    assert (
                        False
                    ), f"the radius_crs '{radius_crs}' is not supported for delaunay-masking"

                mx, my = mx[datamask][tri.triangles], my[datamask][tri.triangles]
                # get individual triangle side-lengths
                l = np.array(
                    [
                        np.sqrt(
                            ((mx[:, i] - mx[:, j]) ** 2) + ((my[:, i] - my[:, j]) ** 2)
                        )
                        for i, j in ((0, 1), (0, 2), (1, 2))
                    ]
                )

                # mask any triangle whose side-length exceeds maxdist
                mask = np.any(l > maxdist, axis=0)
                tri.set_mask(mask)

            return tri, datamask

        def get_coll(self, x, y, crs, **kwargs):

            tri, datamask = self._get_delaunay_triangulation(
                x, y, crs, self.mask_radius, self.mask_radius_crs, self.masked
            )
            maskedTris = tri.get_masked_triangles()

            # find the masked points that are not masked by the datamask
            mask = ~datamask.copy()
            if self.masked:
                mask[np.where(datamask)[0][list(set(maskedTris.flat))]] = True

            # remember the mask
            self._m._data_mask = mask

            color_and_array = Shapes._get_colors_and_array(kwargs, datamask)

            if self.flat == False:
                for key, val in color_and_array.items():
                    if val is None:
                        continue

                    if key == "array":
                        pass
                    else:
                        color_and_array[key] = np.tile(val, 6)
                coll = TriMesh(
                    tri,
                    # transOffset=self._m.ax.transData,
                    **color_and_array,
                    **kwargs,
                )
            else:
                for key, val in color_and_array.items():
                    if val is None:
                        continue

                    if key == "array":
                        color_and_array[key] = val[maskedTris].mean(axis=1)
                    else:
                        # explicitly handle single-color entries
                        # (e.g. int, float, str rgb-tuples etc.)
                        if isinstance(val, (int, float, str, tuple)):
                            pass
                        elif isinstance(val, np.ndarray):
                            # if arrays of colors have been provided, broadcast them
                            color_and_array[key] = val[maskedTris[:, 0]]

                # Vertices of triangles.
                verts = np.stack((tri.x[maskedTris], tri.y[maskedTris]), axis=-1)

                coll = PolyCollection(
                    verts=verts,
                    # transOffset=self._m.ax.transData,
                    **color_and_array,
                    **kwargs,
                )

            return coll

        @property
        def radius(self):
            radius = Shapes._get_radius(self._m, "estimate", "in")
            return radius

        @property
        def radius_crs(self):
            return "in"

    class _ShadePoints(object):
        name = "shade_points"

        def __init__(self, m):
            self._m = m

        def __repr__(self):
            return "Point-based shading with datashader"

        def __call__(self, aggregator=None, shade_hook=None, agg_hook=None):
            """
            Shade the data as infinitesimal points (>> usable for very large datasets!).

            This function is based on the functionalities of `datashader.mpl_ext.dsshow`
            provided by the matplotlib-extension for "datashader".

            Parameters
            ----------
            aggregator : Reduction, optional
                The reduction to compute per-pixel.
                The default is `ds.mean("val")` where "val" represents the data-values.
            shade_hook : callable, optional
                A callable that takes the image output of the shading pipeline,
                and returns another Image object.
                See dynspread() and spread() for examples.
                The default is `partial(ds.tf.dynspread, max_px=50)`.
            agg_hook : callable, optional
                A callable that takes the computed aggregate as an argument, and returns
                another aggregate. This can be used to do preprocessing before the
                aggregate is converted to an image.
                The default is None.
            """

            (ds,) = register_modules("datashader")

            if aggregator is None:
                aggregator = ds.mean("val")
            elif isinstance(aggregator, str):
                aggregator = getattr(ds, aggregator)("val")

            if shade_hook is None:
                shade_hook = partial(ds.tf.dynspread, max_px=50)

            if agg_hook is None:
                pass

            glyph = ds.Point("x", "y")

            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)

                shape.aggregator = aggregator
                shape.shade_hook = shade_hook
                shape.agg_hook = agg_hook
                shape.glyph = glyph

                m._shape = shape

        @property
        def _initargs(self):
            return dict(
                aggregator=self.aggregator,
                shade_hook=self.shade_hook,
                agg_hook=self.agg_hook,
            )

        @property
        def radius(self):
            radius = Shapes._get_radius(self._m, "estimate", "in")
            return radius

        @property
        def radius_crs(self):
            return "in"

    class _ShadeRaster(object):
        name = "shade_raster"

        def __init__(self, m):
            self._m = m

        def __repr__(self):
            return "Raster-shading with datashader"

        def __call__(self, aggregator="mean", shade_hook=None, agg_hook=None):
            """
            Shade the data as a rectangular raster (>> usable for very large datasets!).

            - Using a raster-based shading is only possible if:
                - the data can be converted to rectangular 2D arrays

            This function is based on the functionalities of `datashader.mpl_ext.dsshow`
            provided by the matplotlib-extension for datashader.

            Note
            ----
            The shade_raster-shape uses a QuadMesh to represent the datapoints.

            As a requirement for correct identification of the pixels, the
            **data must be sorted by coordinates**!
            (see `assume_sorted` argument of `m.plot_map()` for more details.)


            Parameters
            ----------
            aggregator : str or datashader.reductions, optional
                The reduction to compute per-pixel.
                (see https://datashader.org/api.html#reductions for details)

                If a string is provided, it is interpreted as `ds.<aggregator>("val")`
                where "val" represents the data-values.

                Possible string values are:
                - "mean", "min", "max", "first", "last", "std", "sum", "var", "count"

                The default is "mean", e.g. `datashader.mean("val")`
            shade_hook : callable, optional
                A callable that takes the image output of the shading pipeline,
                and returns another Image object.
                See dynspread() and spread() for examples.
                The default is None.
            agg_hook : callable, optional
                A callable that takes the computed aggregate as an argument, and returns
                another aggregate. This can be used to do preprocessing before the
                aggregate is converted to an image.
                The default is None.
            """

            (ds,) = register_modules("datashader")

            if aggregator is None:
                aggregator = ds.mean("val")
            if isinstance(aggregator, str):
                aggregator = getattr(ds, aggregator)("val")

            if shade_hook is None:
                shade_hook = None

            if agg_hook is None:
                pass

            # this might be changed by m._ShadeRaster depending on the dataset-shape
            glyph = None

            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)
                shape.aggregator = aggregator
                shape.shade_hook = shade_hook
                shape.agg_hook = agg_hook
                shape.glyph = glyph

                m._shape = shape

        @property
        def _initargs(self):
            return dict(
                aggregator=self.aggregator,
                shade_hook=self.shade_hook,
                agg_hook=self.agg_hook,
            )

        @property
        def radius(self):
            radius = Shapes._get_radius(self._m, "estimate", "in")
            return radius

        @property
        def radius_crs(self):
            return "in"

    class _Raster(object):
        name = "raster"

        def __init__(self, m):
            self._m = m
            self._radius = None
            self.radius_crs = "in"

        def __call__(
            self, maxsize=5e6, interp_order=0, aggregator="mean", valid_fraction=0
        ):
            """
            Draw the data as a rectangular raster  (>> usable for very large datasets!)

            (optionally aggregate data prior to plotting)

            By default, large datasets (>5 million datapoints) will be aggregated
            prior to plotting to considerably speed up initialization of the plot.
            (use `maxsize=None` to disable aggregation.)

            The aggregation will apply the selected `aggregator` to datapoints within
            regular data-blocks of the size (n, n) where `n` is selected such that the
            plotted dataset contains approximately `maxsize` datapoints.
            Lower values of `maxsize` will result in faster (but more coarse) plots.

            Note
            ----
            The raster-shape uses a QuadMesh to represent the datapoints.

            - As a requirement for correct identification of the pixels, the
              **data must be sorted by coordinates**!
              (see `assume_sorted` argument of `m.plot_map()` for more details.)

            This considerably speeds up plotting of large datasets but it has the
            disadvantage that only the vertices of the rectangles will be reprojected
            to the plot-crs while the curvature of the edges is NOT considered!
            (e.g. the effective shape is a distorted rectangle with straight edges)

            - use `m.set_shape.rectangles()` if you need "curved" edges!
            - use `m.set_shape.shade_raster()` to use datashader for aggregation

            Parameters
            ----------
            maxsize: int, None
                If provided, the dataset will be aggregated prior to plotting.

                Datasets larger than 'maxsize' will be resampled into a regular grid
                such that the final dataset contains approximately 'maxsize' datapoints.
                (aggregation is performed with respect to the selected 'method')

                Lower numbers for 'maxsize' will reduce the image resolution in favor
                of a (possibly huge) speedup for the initialization of the plot!

                The default is 5e6  (e.g. 5 million datapoints)
            aggregator : str
                The method used for aggregation.

                - "first", "last" : select first/last value of the aggregation blocks
                  (this is very fast but the resulting dataset might not always be a
                  reliable aggregated estimate of the actual data)
                - "min", "max", "mean", "median", "std", "sum": calculate the
                  corresponding metrics of the data inside the aggregation blocks.
                - "mode": evaluate the most commonly encountered value within each
                  aggregation bin (NOTE: this is computationally intense and can become
                  slow if `maxsize` is set too large!)
                - "fast_mean", "fast_sum": use a fast and memory-efficient method to
                  evaluate the corresponding metrics.
                  NOTE: this uses `numpy.einsum` for aggregation which does not check
                  for overflow errors and might cause problems if the  dataset was
                  provided in a dtype that cannot be used to store the resulting
                  aggregated sum of data-values (e.g. int8, int16 etc).

                  To avoid problems, cast the dataset to a larger dtype using
                  `data = np.array([...]).astype(<desired dtype>)` or use ordinary
                  aggregator metrics.

                - "spline": aggregate with spline interpolation via `scipy.ndimage.zoom`
                  (interpolation order can be set via the 'interp_order' kwarg)

                The default is "mean"
            valid_fraction : float
                (NOT used by the "scipy" method and only relevant for masked arrays!)

                Percentage (0-1) of the masked pixels within an aggregation box
                that will result in a masked value.
                (e.g. 0.1 -> if more than 10% of the data is masked in an aggregation
                box, the aggregated value will be masked). The default is 0
            interp_order: int
                (ONLY used if method = "scipy")
                The spline interpolation order for zooming.
                See `scipy.ndimage.zoom` for more details.
            """

            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)
                shape._maxsize = maxsize
                shape._interp_order = interp_order
                shape._aggregator = aggregator
                shape._valid_fraction = valid_fraction
                m._shape = shape

        @property
        def _initargs(self):
            return dict(
                maxsize=self._maxsize,
                interp_order=self._interp_order,
                aggregator=self._aggregator,
                valid_fraction=self._valid_fraction,
            )

        @property
        def radius(self):
            if self._radius is None:
                radius = Shapes._get_radius(self._m, self._radius, self.radius_crs)
                return radius

            return self._radius

        def __repr__(self):
            try:
                s = f"raster(radius={self.radius}, radius_crs={self.radius_crs})"
            except AttributeError:
                s = "raster(radius, radius_crs)"

            return s

        def _get_rectangle_verts(self, x, y, crs):
            # estimate distance between pixels
            dx = np.diff(x, axis=1, prepend=x[:, 1][:, np.newaxis]) / 2
            dy = np.diff(y, axis=0, prepend=y[1, :][np.newaxis, :]) / 2

            # since prepend will result in a inverted diff (val - prepended_val)
            # instead of (prepended_val - val) we need to invert the sign!
            dx[:, 0] = -dx[:, 0]
            dy[0, :] = -dy[0, :]

            x = x - dx
            y = y - dy

            # transform corner-points
            in_crs = self._m.get_crs(crs)
            # transform from crs to the plot_crs
            t = self._m._get_transformer(in_crs, self._m.crs_plot)

            # make sure we do not transform out of bounds (if possible)
            if in_crs.area_of_use is not None:
                transformer = self._m._get_transformer(in_crs.geodetic_crs, in_crs)

                xmin, ymin, xmax, ymax = transformer.transform_bounds(
                    *in_crs.area_of_use.bounds
                )

                clipx = partial(np.clip, a_min=xmin, a_max=xmax)
                clipy = partial(np.clip, a_min=ymin, a_max=ymax)
            else:
                clipx, clipy = lambda x: x, lambda y: y

            # distribute the values as rectangle vertices
            v = np.full((x.shape[0] + 1, x.shape[1] + 1, 2), None, dtype=float)

            v[:-1, :-1, 0] = x
            v[:-1, :-1, 1] = y

            # treat bottom vertices values
            v[-1, :-1] = v[-2, :-1] + [0, 2 * dy[-1, 0]]
            # treat right most vertices values
            v[:, -1] = v[:, -2] + [2 * dx[0, -1], 0]

            px, py = t.transform(clipx(v[:, :, 0]), clipy(v[:, :, 1]))
            verts = np.stack((px, py), axis=2)

            # TODO is there a proper way to implement a mask here?
            # (raster must always remain 2D...)
            # mask = np.logical_and(np.isfinite(px)[:-1, :-1], np.isfinite(py)[:-1, :-1])
            mask = np.full(px[:-1, :-1].shape, True, dtype=bool)
            return verts, mask

        def _get_polygon_coll(self, x, y, crs, **kwargs):

            verts, mask = self._get_rectangle_verts(
                x,
                y,
                crs,
            )

            # TODO masking is skipped for now...
            self._m._data_mask = None
            # don't use a mask here since we need the full 2D array
            color_and_array = Shapes._get_colors_and_array(
                kwargs, np.full_like(mask, True)
            )

            coll = QuadMesh(
                verts,
                **color_and_array,
                **kwargs,
            )

            # temporary fix for https://github.com/matplotlib/matplotlib/issues/22908
            # QuadMesh.get_cursor_data = lambda *args, **kwargs: None
            coll.get_cursor_data = lambda *args, **kwargs: None
            # temporary fix for https://github.com/matplotlib/matplotlib/issues/23164
            # (no need for .contains in EOmaps since pixels are identified internally)
            coll.contains = lambda *args, **kwargs: [False]

            return coll

        def get_coll(self, x, y, crs, **kwargs):

            x, y = np.asanyarray(x), np.asanyarray(y)
            # don't use antialiasing by default since it introduces unwanted
            # transparency for reprojected QuadMeshes!
            kwargs.setdefault("antialiased", False)

            return self._get_polygon_coll(x, y, crs, **kwargs)

    class _Contour(object):
        name = "contour"

        def __init__(self, m):
            self._m = m
            self._radius = None
            self.radius_crs = "in"

        def __call__(self, filled=True):
            """
            Draw a contour-plot of the data.

            Note
            ----
            This is a wrapper for matplotlibs contour-plot capabilities.

            - contours for 2D datasets are evaluated with `plt.contour`
            - contours for 1D datasets are evaluated with `plt.tricontour`

            """
            from . import MapsGrid  # do this here to avoid circular imports!

            for m in self._m if isinstance(self._m, MapsGrid) else [self._m]:
                shape = self.__class__(m)
                shape._filled = filled

                m._shape = shape

        @property
        def _initargs(self):
            return dict(filled=self._filled)

        @property
        def radius(self):
            if self._radius is None:
                radius = Shapes._get_radius(self._m, self._radius, self.radius_crs)
                return radius

            return self._radius

        def __repr__(self):
            try:
                s = f"{self.name}(radius={self.radius}, radius_crs={self.radius_crs})"
            except AttributeError:
                s = f"{self.name}(radius, radius_crs)"

            return s

        def _get_contourf_colls(self, x, y, crs, **kwargs):
            # make sure the array is not dropped from kwargs since we need it for
            # evaluating the contours
            z = kwargs.pop("array", None)

            # if manual levels were specified, use them, otherwise check for
            # classification values
            if "levels" not in kwargs:
                bins = getattr(self._m.classify_specs, "_bins", None)
                if bins is not None:
                    # in order to ensure that values above or below vmin/vmax are
                    # colored with the appropriate "under" and "over" colors,
                    # we need to extend the classification bins with the min/max values
                    # of the data (otherwise only intermediate levels would be drawn!)
                    kwargs["levels"] = np.unique([z.min(), *bins, z.max()])

            # transform from crs to the plot_crs
            in_crs = self._m.get_crs(crs)
            t_in_plot = self._m._get_transformer(in_crs, self._m.crs_plot)

            # don't use a mask here since we need the full 2D array
            mask = np.full(x.shape, True, dtype=bool)
            self._m._data_mask = None

            color_and_array = Shapes._get_colors_and_array(kwargs, mask)
            # since the "array" parameter is added by default (even if None),
            # remove it again to avoid warnings that the parameter is unused.
            # TODO implement better treatment for "array" kwarg
            color_and_array.pop("array")

            xs, ys = np.ma.masked_invalid(t_in_plot.transform(x, y), copy=False)

            # for 2D data use normal contour, for irregular data use tricontour
            if len(xs.shape) == 2 and len(ys.shape) == 2:
                use_tri = False
            else:
                use_tri = True

            # tricontours do not accept masked values -> drop all masked values!
            if use_tri and isinstance(z, np.ma.MaskedArray):
                xs = xs[~z.mask]
                ys = ys[~z.mask]
                z = z.compressed()

            data = dict(x=xs, y=ys, z=z)

            color_and_array.update(kwargs)

            # if manual colors are specified, cmap and norm must be set to None
            # otherwise contour complains about ambiguous arguments!
            if "colors" in kwargs:
                color_and_array.pop("cmap", None)
                color_and_array.pop("norm", None)
            if self._filled:
                if use_tri:
                    cont = self._m.ax.tricontourf(
                        *[i.ravel() for i in data.values()], **color_and_array
                    )
                else:
                    cont = self._m.ax.contourf(
                        "x", "y", "z", data=data, **color_and_array
                    )
            else:
                if use_tri:
                    cont = self._m.ax.tricontour(
                        *[i.ravel() for i in data.values()], **color_and_array
                    )
                else:
                    cont = self._m.ax.contour(
                        "x", "y", "z", data=data, **color_and_array
                    )

            # from matplotlib v3.10 on the .collection kwarg is removed and
            # since v3.8 ax.contour already returns a collection.
            # TODO remove this once mpl >=3.10 is required
            if mpl_version < version.Version("3.10"):
                return _CollectionAccessor(cont, self._filled)
            else:
                return cont

        def get_coll(self, x, y, crs, **kwargs):
            x, y = np.asanyarray(x), np.asanyarray(y)
            # don't use antialiasing by default since it introduces unwanted
            # transparency for reprojected QuadMeshes!
            # kwargs.setdefault("antialiased", False)

            coll = self._get_contourf_colls(x, y, crs, **kwargs)

            # TODO remove this once mpl >= 3.10 is required
            if isinstance(coll, _CollectionAccessor):
                for c in coll.collections:
                    self._m.BM._ignored_unmanaged_artists.add(c)

            return coll

    @wraps(_Contour.__call__)
    def contour(self, *args, **kwargs):
        shp = self._Contour(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_ScatterPoints.__call__)
    def scatter_points(self, *args, **kwargs):
        shp = self._ScatterPoints(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_Hexbin.__call__)
    def hexbin(self, *args, **kwargs):
        shp = self._Hexbin(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_GeodCircles.__call__)
    def geod_circles(self, *args, **kwargs):
        shp = self._GeodCircles(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_Ellipses.__call__)
    def ellipses(self, *args, **kwargs):
        shp = self._Ellipses(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_Rectangles.__call__)
    def rectangles(self, *args, **kwargs):
        shp = self._Rectangles(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_Raster.__call__)
    def raster(self, *args, **kwargs):
        shp = self._Raster(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_VoronoiDiagram.__call__)
    def voronoi_diagram(self, *args, **kwargs):
        shp = self._VoronoiDiagram(m=self._m)
        # increase radius margins for voronoi diagrams since
        # outer points are otherwise always masked!
        self._m._data_manager.set_margin_factors(20, 0.1)

        return shp.__call__(*args, **kwargs)

    @wraps(_SphericalVoronoiDiagram.__call__)
    def spherical_voronoi_diagram(self, *args, **kwargs):
        shp = self._SphericalVoronoiDiagram(m=self._m)
        # increase radius margins for voronoi diagrams since
        # outer points are otherwise always masked!
        self._m._data_manager.set_margin_factors(20, 0.1)

        return shp.__call__(*args, **kwargs)

    @wraps(_DelaunayTriangulation.__call__)
    def delaunay_triangulation(self, *args, **kwargs):
        shp = self._DelaunayTriangulation(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_ShadePoints.__call__)
    def shade_points(self, *args, **kwargs):
        shp = self._ShadePoints(m=self._m)
        return shp.__call__(*args, **kwargs)

    @wraps(_ShadeRaster.__call__)
    def shade_raster(self, *args, **kwargs):
        shp = self._ShadeRaster(m=self._m)
        return shp.__call__(*args, **kwargs)

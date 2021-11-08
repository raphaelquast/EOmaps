from matplotlib.collections import PolyCollection
from matplotlib.tri import TriMesh, Triangulation
import numpy as np

from pyproj import CRS, Transformer
from functools import update_wrapper, partial
import warnings


class shapes(object):
    """
    Set the plot-shape to represent the data-points.
    Possible shapes are:
    (check the individual docs for details!)

        - Projected ellipses

        >>> m.set_shape.ellipses(radius, radius_crs)

        - Projected rectangles

        >>> m.set_shape.rectangles(radius, radius_crs, mesh)

        - Projected geodetic circles

        >>> m.set_shape.geod_circles(radius)

        - Voroni diagram

        >>> m.set_shape.voroni_diagram(masked, mask_radius)

        - Delaunay triangulation

        >>> m.set_shape.delaunay_triangulation(masked, mask_radius, mask_radius_crs, flat)

    """

    _shp_list = [
        "geod_circles",
        "ellipses",
        "rectangles",
        "voroni_diagram",
        "delaunay_triangulation",
    ]

    def __init__(self, m):
        self._m = m

        for shp in self._shp_list:
            setattr(
                self,
                shp,
                update_wrapper(
                    getattr(self, f"_{shp}")(m=m), getattr(self, f"_{shp}").__call__
                ),
            )

    def _get(self, shape, **kwargs):
        shp = getattr(self, f"_{shape}")(self._m)
        for key, val in kwargs.items():
            setattr(shp, key, val)
        return shp

    @staticmethod
    def _get_radius(m, radius, radius_crs, buffer=None):
        # get the radius for plotting
        if (isinstance(radius, str) and radius == "estimate") or radius is None:
            if radius_crs == "in":
                radiusx = np.median(np.abs(np.diff(np.unique(m._props["xorig"])))) / 2.0
                radiusy = np.median(np.abs(np.diff(np.unique(m._props["yorig"])))) / 2.0
            elif radius_crs == "out":
                radiusx = np.median(np.abs(np.diff(np.unique(m._props["x0"])))) / 2.0
                radiusy = np.median(np.abs(np.diff(np.unique(m._props["y0"])))) / 2.0
            else:
                raise AssertionError(
                    "radius can only be estimated if radius_crs is 'in' or 'out'!"
                )
        else:
            # get manually specified radius (e.g. if radius != "estimate")
            if isinstance(radius, (list, tuple, np.ndarray)):
                radiusx, radiusy = radius
            elif isinstance(radius, (int, float)):
                radiusx = radius
                radiusy = radius

        if buffer is not None:
            radiusx = radiusx * buffer
            radiusy = radiusy * buffer

        return (radiusx, radiusy)

    class _geod_circles(object):
        name = "geod_circles"

        def __init__(self, m):
            self._m = m

        def __call__(self, radius, n=20):
            """
            Draw geodesic circles with a radius defined in meters.

            Parameters
            ----------
            radius : float
                The radius of the circles in meters.
            n : int
                The number of points to calculate on the circle.
                The default is 20.

            Returns
            -------
            self
                The class representing the plot-shape.

            """
            self.radius = radius

            self.n = n

            self._m.shape = self

        @property
        def _initargs(self):
            return dict(radius=self._radius, n=self.n)

        @property
        def radius(self):
            return self._radius

        @radius.setter
        def radius(self, val):
            if not isinstance(val, (int, float)):
                print("EOmaps: geod_circles only support a number as radius!")
                if isinstance(val[0], (int, float)):
                    print("EOmaps: ... using the mean")
                    val = np.mean(val)
                else:
                    raise TypeError(
                        f"EOmaps: '{val}' is not a valid radius for 'geod_circles'!"
                    )

            self._radius = val

        def __repr__(self):
            try:
                s = f"geod_circles(radius={self.radius}, n={self.n})"
            except AttributeError:
                s = "geod_circles(radius, n)"
            return s

        def _calc_geod_circle_points(self, lon, lat, radius, n=20, start_angle=0):
            """
            calculate points on a geodetic circle with a given radius

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
            lats : TYPE
                the latitudes of the geodetic circle points.

            """
            size = lon.size

            if isinstance(radius, (int, float)):
                radius = np.full((size, n), radius)
            else:
                radius = (np.broadcast_to(radius[:, None], (size, n)),)

            geod = self._m.crs_plot.get_geod()
            lons, lats, back_azim = geod.fwd(
                np.broadcast_to(lon[:, None], (size, n)),
                np.broadcast_to(lat[:, None], (size, n)),
                np.linspace(
                    [start_angle] * size, [360 - start_angle] * size, n, axis=1
                ),
                radius,
                radians=False,
            )

            return lons.T, lats.T

        def _get_geod_circle_points(self, x, y, crs, radius, n=20):
            x, y = np.asarray(x), np.asarray(y)

            # transform from in-crs to lon/lat
            radius_t = Transformer.from_crs(
                CRS.from_user_input(self._m.get_crs(crs)),
                CRS.from_epsg(4326),
                always_xy=True,
            )
            # transform from lon/lat to the plot_crs
            plot_t = Transformer.from_crs(
                CRS.from_epsg(4326),
                CRS.from_user_input(self._m.crs_plot),
                always_xy=True,
            )

            lon, lat = radius_t.transform(x, y)
            # calculate some points on the geodesic circle
            lons, lats = self._calc_geod_circle_points(lon, lat, radius, n=n)

            xs, ys = np.ma.masked_invalid(plot_t.transform(lons, lats), copy=False)

            # get the mask for invalid, very distorted or very large shapes
            dx = xs.max(axis=0) - xs.min(axis=0)
            dy = ys.max(axis=0) - ys.min(axis=0)
            mask = (
                ~xs.mask.any(axis=0)
                & ~ys.mask.any(axis=0)
                & ((dx / dy) < 10)
                & (dx < radius * 50)
                & (dy < radius * 50)
            )

            mask = np.broadcast_to(mask[:, None].T, lons.shape)

            return xs, ys, mask

        def get_coll(self, x, y, crs, **kwargs):

            xs, ys, mask = self._get_geod_circle_points(x, y, crs, self.radius, self.n)

            # special treatment of array input to properly mask values
            array = kwargs.pop("array", None)
            # xs, ys, mask = props["xs"], props["ys"], props["mask"]

            # only plot polygons if they contain 2 or more vertices
            vertmask = np.count_nonzero(mask, axis=0) > 2

            # remember masked points
            self._m._data_mask = vertmask

            verts = np.stack((xs, ys)).T
            verts = np.ma.masked_array(
                verts,
                np.broadcast_to(~mask[:, None].T.swapaxes(1, 2), verts.shape),
            )
            verts = list(
                i.compressed().reshape(-1, 2) for i, m in zip(verts, vertmask) if m
            )

            if array is not None:
                array = array[vertmask]

            coll = PolyCollection(
                verts, transOffset=self._m.figure.ax.transData, array=array, **kwargs
            )
            return coll

    class _ellipses(object):
        name = "ellipses"

        def __init__(self, m):
            self._m = m

        def __call__(self, radius="estimate", radius_crs="in", n=20):
            """
            Draw projected ellipses defined in distance-units of a given crs.

            Parameters
            ----------
            radius : tuple or str, optional
                a tuple representing the radius in x- and y- direction.
                The default is "estimate" in which case the radius is attempted
                to be estimated from the input-coordinates.
            radius_crs : crs-specification, optional
                The crs in which the dimensions are defined.
                The default is "in".
            n : int
                The number of points to calculate on the circle.
                The default is 20.

            Returns
            -------
            None.

            """

            self._radius = radius

            self.radius_crs = radius_crs
            self.n = n

            self._m.shape = self

        @property
        def _initargs(self):
            return dict(radius=self._radius, radius_crs=self.radius_crs, n=self.n)

        @property
        def radius(self):
            return shapes._get_radius(self._m, self._radius, self.radius_crs)

        @radius.setter
        def radius(self, val):
            self._radius = val

        def __repr__(self):
            try:
                s = f"ellipses(radius={self.radius}, radius_crs={self.radius_crs}, n={self.n})"
            except AttributeError:
                s = "ellipses(radius, radius_crs, n)"
            return s

        def _calc_ellipse_points(self, x0, y0, a, b, theta, n, start_angle=0):
            """
            calculate points on a rotated ellipse

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

        def _get_ellipse_points(self, x, y, crs, radius, radius_crs="in", n=20):
            # transform from crs to the plot_crs
            t_in_plot = Transformer.from_crs(
                self._m.get_crs(crs),
                self._m.crs_plot,
                always_xy=True,
            )
            # transform from crs to the radius_crs
            t_in_radius = Transformer.from_crs(
                self._m.get_crs(crs),
                self._m.get_crs(radius_crs),
                always_xy=True,
            )
            # transform from crs to the radius_crs
            t_radius_plot = Transformer.from_crs(
                self._m.get_crs(radius_crs),
                self._m.crs_plot,
                always_xy=True,
            )

            [rx, ry] = radius
            # transform corner-points
            if radius_crs == crs:
                pr = t_in_plot.transform(x, y + ry)
                pl = t_in_plot.transform(x, y - ry)
                d = np.ma.masked_invalid(pl) - np.ma.masked_invalid(pr)
                theta = np.arctan(d[1] / d[0]) - (np.pi / 2)

                xs, ys = self._calc_ellipse_points(
                    x,
                    y,
                    np.full_like(x, rx, dtype=float),
                    np.full_like(x, ry, dtype=float),
                    theta,
                    n=n,
                )
                xs, ys = np.ma.masked_invalid((xs, ys), copy=False)
                xs, ys = np.ma.masked_invalid(t_in_plot.transform(xs, ys), copy=False)
            else:
                p = t_in_radius.transform(x, y)
                pr = t_radius_plot.transform(p[0], p[1] + y)
                pl = t_radius_plot.transform(p[0], p[1] - y)

                d = np.ma.masked_invalid(pl) - np.ma.masked_invalid(pr)
                theta = np.arctan(d[1] / d[0]) - (np.pi / 2)
                xs, ys = self._calc_ellipse_points(
                    p[0],
                    p[1],
                    np.full_like(x, rx, dtype=float),
                    np.full_like(x, ry, dtype=float),
                    theta,
                    n=n,
                )

                xs, ys = np.ma.masked_invalid((xs, ys), copy=False)
                xs, ys = np.ma.masked_invalid(
                    t_radius_plot.transform(xs, ys), copy=False
                )

            # get the mask for invalid, very distorted or very large shapes
            dx = np.abs(xs.max(axis=1) - xs.min(axis=1))
            dy = np.abs(ys.max(axis=1) - ys.min(axis=1))
            mask = (
                ~xs.mask.any(axis=1)
                & ~ys.mask.any(axis=1)
                & (dx <= (np.ma.median(dx) * 10))
                & (dy <= (np.ma.median(dy) * 10))
                & np.isfinite(theta)
            )

            return xs, ys, mask

        def get_coll(self, x, y, crs, **kwargs):
            xs, ys, mask = self._get_ellipse_points(
                x, y, crs, self.radius, self.radius_crs, n=self.n
            )

            # remember masked points
            self._m._data_mask = mask

            # special treatment of array input to properly mask values
            array = kwargs.pop("array", None)
            if array is not None:
                array = array[mask]

            verts = np.stack((xs[mask], ys[mask])).T.swapaxes(0, 1)

            coll = PolyCollection(
                verts, transOffset=self._m.figure.ax.transData, array=array, **kwargs
            )
            return coll

    class _rectangles(object):
        name = "rectangles"

        def __init__(self, m):
            self._m = m

        def __call__(self, radius="estimate", radius_crs="in", mesh=False, n=10):
            """
            Draw projected rectangles with dimensions defined in units of a given crs.

            Parameters
            ----------
            radius : tuple or str, optional
                a tuple representing the radius in x- and y- direction.
                The default is "estimate" in which case the radius is attempted
                to be estimated from the input-coordinates.
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
            n : int
                The number of intermediate points to calculate on the rectangle
                edges (e.g. to plot "curved" rectangles in projected crs)
                Use n=1 to get actual rectangles!
                The default is 10
            Returns
            -------
            None.

            """
            self._radius = radius
            self.radius_crs = radius_crs
            self.mesh = mesh

            if mesh is True:
                if n > 1:
                    warnings.warn(
                        "EOmaps: rectangles with 'mesh=True' only supports n=1"
                    )
                self.n = 1
            else:
                self.n = n
            self._m.shape = self

        @property
        def _initargs(self):
            return dict(
                radius=self._radius,
                radius_crs=self.radius_crs,
                n=self.n,
                mesh=self.mesh,
            )

        @property
        def radius(self):
            return shapes._get_radius(self._m, self._radius, self.radius_crs)

        @radius.setter
        def radius(self, val):
            self._radius = val

        def __repr__(self):
            try:
                s = f"rectangles(radius={self.radius}, radius_crs={self.radius_crs})"
            except AttributeError:
                s = "rectangles(radius, radius_crs)"

            return s

        def _get_rectangle_verts(self, x, y, crs, radius, radius_crs="in", n=4):
            in_crs = self._m.get_crs(crs)

            [rx, ry] = radius
            # transform corner-points
            if radius_crs == crs:
                in_crs = self._m.get_crs(crs)
                # transform from crs to the plot_crs
                t = Transformer.from_crs(
                    in_crs,
                    self._m.crs_plot,
                    always_xy=True,
                )

                # make sure we do not transform out of bounds (if possible)
                if in_crs.area_of_use is not None:
                    transformer = Transformer.from_crs(
                        in_crs.geodetic_crs, in_crs, always_xy=True
                    )
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
                t_in_radius = Transformer.from_crs(
                    in_crs,
                    r_crs,
                    always_xy=True,
                )
                # transform from radius_crs to the plot_crs
                t = Transformer.from_crs(
                    r_crs,
                    self._m.crs_plot,
                    always_xy=True,
                )

                # make sure we do not transform out of bounds (if possible)
                if r_crs.area_of_use is not None:
                    transformer = Transformer.from_crs(
                        r_crs.geodetic_crs, r_crs, always_xy=True
                    )
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
                x, y, crs, self.radius, self.radius_crs, self.n
            )

            # remember masked points
            self._m._data_mask = mask

            # special treatment of array input to properly mask values
            array = kwargs.pop("array", None)
            if array is not None:
                array = array[mask]

            coll = PolyCollection(
                verts=verts,
                transOffset=self._m.figure.ax.transData,
                array=array,
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
            # special treatment of color and array inputs to distribute the values
            color = kwargs.pop("color", None)
            fc = kwargs.pop("fc", None)
            facecolor = kwargs.pop("facecolor", None)
            facecolors = kwargs.pop("facecolors", None)

            array = kwargs.pop("array", None)

            tri, mask = self._get_trimesh_rectangle_triangulation(
                x, y, crs, self.radius, self.radius_crs, self.n
            )

            # remember masked points
            self._m._data_mask = mask

            coll = TriMesh(
                tri,
                transOffset=self._m.figure.ax.transData,
                **kwargs,
            )

            # special treatment of color input to properly distribute values
            if color is not None:
                coll.set_facecolors([color] * (len(x)) * 6)
            elif facecolor is not None:
                coll.set_facecolors([facecolor] * (len(x)) * 6)
            elif facecolors is not None:
                coll.set_facecolors([facecolors] * (len(x)) * 6)
            elif fc is not None:
                coll.set_facecolors([fc] * (len(x)) * 6)
            else:
                # special treatment of array input to properly mask values
                if array is not None:
                    array = array[mask]

                    # tri-contour meshes need 3 values for each triangle
                    array = np.broadcast_to(array, (3, len(array))).T
                    # we plot 2 triangles per rectangle
                    array = np.broadcast_to(array, (2, *array.shape))
                    coll.set_array(array.ravel())

            return coll

        def get_coll(self, x, y, crs, **kwargs):
            if self.mesh is True:
                return self._get_trimesh_coll(x, y, crs, **kwargs)
            else:
                return self._get_polygon_coll(x, y, crs, **kwargs)

    class _voroni_diagram(object):
        name = "voroni_diagram"

        def __init__(self, m):
            self._m = m

        def __call__(self, masked=True, mask_radius=None):
            """
            Draw projected rectangles with dimensions defined in units of a given crs.

            Parameters
            ----------
            masked : bool
                Indicator if the voroni-diagram should be masked or not

            mask_radius : float, optional
                the radius used for masking the voroni-diagram (in units of the plot-crs)

            Returns
            -------
            None.

            """
            self.mask_radius = mask_radius
            self.masked = masked

            self._m.shape = self

        @property
        def _initargs(self):
            return dict(mask_radius=self.mask_radius, masked=self.masked)

        def __repr__(self):
            try:
                s = f"voroni_diagram(mask_radius={self.mask_radius}, masked={self.masked})"
            except AttributeError:
                s = "voroni_diagram(mask_radius, masked)"

            return s

        @property
        def mask_radius(self):
            return shapes._get_radius(self._m, self._mask_radius, "out")

        @mask_radius.setter
        def mask_radius(self, val):
            self._mask_radius = val

        def _get_voroni_verts_and_mask(self, x, y, crs, radius, masked=True):
            try:
                from scipy.spatial import Voronoi
                from itertools import zip_longest
            except ImportError:
                raise ImportError("'scipy' is required for 'Voroni'!")

            # transform from crs to the plot_crs
            t_in_plot = Transformer.from_crs(
                self._m.get_crs(crs),
                self._m.crs_plot,
                always_xy=True,
            )

            x0, y0 = t_in_plot.transform(x, y)

            datamask = np.isfinite(x0) & np.isfinite(y0)
            [radiusx, radiusy] = radius

            maxdist = 2 * np.mean(np.sqrt(radiusx ** 2 + radiusy ** 2))

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

            # special treatment of array input to properly mask values
            array = kwargs.pop("array", None)

            verts, mask, datamask = self._get_voroni_verts_and_mask(
                x, y, crs, self.mask_radius, masked=self.masked
            )

            # find the masked points that are not masked by the datamask
            mask2 = ~datamask.copy()
            mask2[np.where(datamask)[0][mask]] = True
            # remember the mask
            self._m._data_mask = mask2

            if array is not None:
                array = array[datamask][mask]

            coll = PolyCollection(
                verts=verts,
                array=array,
                transOffset=self._m.figure.ax.transData,
                **kwargs,
            )

            return coll

    # class _trimesh_rectangles(_rectangles):
    #     name = "trimesh_rectangles"
    #     def __init__(self, m):
    #         self._m = m

    #     def __call__(self, radius="estimate", radius_crs="in"):
    #         """
    #         Draw a triangular mesh of rectangles with dimensions defined in units of a given crs.
    #         (similar to rectangles but boundaries between neighbouring rectangles are not visible)

    #         Parameters
    #         ----------
    #         radius : tuple or str, optional
    #             a tuple representing the radius in x- and y- direction.
    #             The default is "estimate" in which case the radius is attempted
    #             to be estimated from the input-coordinates.
    #         radius_crs : crs-specification, optional
    #             The crs in which the dimensions are defined.
    #             The default is "in".

    #         Returns
    #         -------
    #         None.

    #         """

    #         self._radius = radius

    #         self.radius_crs = radius_crs

    #         self._m.shape = self

    #     @property
    #     def radius(self):
    #         return shapes._get_radius(self._m, self._radius, self.radius_crs)

    #     @radius.setter
    #     def radius(self, val):
    #         self._radius = val

    #     def __repr__(self):
    #         try:
    #             s = f"trimesh_rectangles(radius={self.radius}, radius_crs={self.radius_crs})"
    #         except AttributeError:
    #             s = "trimesh_rectangles(radius, radius_crs)"
    #         return s

    #     def _get_trimesh_rectangle_triangulation(
    #         self, x, y, crs, radius, radius_crs="in"
    #     ):

    #         verts, mask = self._get_rectangle_verts(x, y, crs, radius, radius_crs)

    #         x = np.vstack(
    #             [verts[:, 2][:, 0], verts[:, 3][:, 0], verts[:, 1][:, 0]]
    #         ).T.flat
    #         y = np.vstack(
    #             [verts[:, 2][:, 1], verts[:, 3][:, 1], verts[:, 1][:, 1]]
    #         ).T.flat

    #         x2 = np.vstack(
    #             [verts[:, 3][:, 0], verts[:, 0][:, 0], verts[:, 1][:, 0]]
    #         ).T.flat
    #         y2 = np.vstack(
    #             [verts[:, 3][:, 1], verts[:, 0][:, 1], verts[:, 1][:, 1]]
    #         ).T.flat

    #         x = np.append(x, x2)
    #         y = np.append(y, y2)

    #         tri = Triangulation(
    #             x, y, triangles=np.array(range(len(x))).reshape((len(x) // 3, 3))
    #         )
    #         return tri, mask

    #     def get_coll(self, x, y, crs, **kwargs):
    #         # special treatment of color and array inputs to distribute the values
    #         color = kwargs.pop("color", None)
    #         array = kwargs.pop("array", None)

    #         tri, mask = self._get_trimesh_rectangle_triangulation(
    #             x, y, crs, self.radius, self.radius_crs
    #         )

    #         coll = TriMesh(
    #             tri,
    #             transOffset=self._m.figure.ax.transData,
    #             **kwargs,
    #         )

    #         # special treatment of color input to properly distribute values
    #         if color is not None:
    #             coll.set_facecolors([color] * (len(x)) * 6)
    #         else:
    #             # special treatment of array input to properly mask values
    #             if array is not None:
    #                 array = array[mask]

    #                 # tri-contour meshes need 3 values for each triangle
    #                 array = np.broadcast_to(array, (3, len(array))).T
    #                 # we plot 2 triangles per rectangle
    #                 array = np.broadcast_to(array, (2, *array.shape))
    #                 coll.set_array(array.ravel())

    #         return coll

    class _delaunay_triangulation(object):
        name = "delaunay_triangulation"

        def __init__(self, m):
            self._m = m

        def __call__(
            self, masked=True, mask_radius=None, mask_radius_crs="in", flat=False
        ):
            """
            Draw projected rectangles with dimensions defined in units of a given crs.

            Parameters
            ----------
            masked : bool
                Indicator if the voroni-diagram should be masked or not
            mask_radius : float, optional
                the radius used for masking the voroni-diagram (in units of the plot-crs)
            mask_radius_crs : str, optional
                The crs in which the radius is defined (either "in" or "out")
            flat : bool
                Indicator if a triangulation (flat=False) or polygons (flat=True)
                should be plotted. The default is False
            """
            self.mask_radius = mask_radius
            self.mask_radius_crs = mask_radius_crs
            self.masked = masked
            self.flat = flat

            self._m.shape = self

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
                    + "mask_radius_crs={self.mask_radius_crs}, masked={masked}, flat={flat})"
                )
            except AttributeError:
                s = "delaunay_triangulation(mask_radius, mask_radius_crs, masked, flat)"
            return s

        @property
        def mask_radius(self):
            return shapes._get_radius(self._m, self._mask_radius, self.mask_radius_crs)

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
            t_in_plot = Transformer.from_crs(
                self._m.get_crs(crs),
                self._m.crs_plot,
                always_xy=True,
            )

            x0, y0 = t_in_plot.transform(x, y)
            datamask = np.isfinite(x0) & np.isfinite(y0)

            d = Delaunay(
                np.column_stack((x0[datamask], y0[datamask])), qhull_options="QJ"
            )

            tri = Triangulation(d.points[:, 0], d.points[:, 1], d.simplices)

            if masked:
                radiusx, radiusy = radius
                maxdist = 4 * np.mean(np.sqrt(radiusx ** 2 + radiusy ** 2))

                if radius_crs == "in":
                    x, y = x[datamask][tri.triangles], y[datamask][tri.triangles]
                    # get individual triangle side-lengths
                    l = np.array(
                        [
                            np.sqrt(
                                ((x[:, i] - x[:, j]) ** 2) + ((y[:, i] - y[:, j]) ** 2)
                            )
                            for i, j in ((0, 1), (0, 2), (1, 2))
                        ]
                    )
                elif radius_crs == "out":
                    x0, y0 = x0[datamask][tri.triangles], y0[datamask][tri.triangles]

                    # get individual triangle side-lengths
                    l = np.array(
                        [
                            np.sqrt(
                                ((x0[:, i] - x0[:, j]) ** 2)
                                + ((y0[:, i] - y0[:, j]) ** 2)
                            )
                            for i, j in ((0, 1), (0, 2), (1, 2))
                        ]
                    )
                else:
                    assert (
                        False
                    ), f"the radius_crs '{radius_crs}' is not supported for delaunay-masking"
                # mask any triangle whose side-length exceeds maxdist
                mask = np.any(l > maxdist, axis=0)
                tri.set_mask(mask)
            return tri, datamask

        def get_coll(self, x, y, crs, **kwargs):

            # special treatment of color and array inputs to distribute the values
            color = kwargs.pop("color", None)
            array = kwargs.pop("array", None)

            tri, datamask = self._get_delaunay_triangulation(
                x, y, crs, self.mask_radius, self.mask_radius_crs, self.masked
            )

            if self.flat == False:
                coll = TriMesh(
                    tri,
                    transOffset=self._m.figure.ax.transData,
                    **kwargs,
                )
            else:
                # Vertices of triangles.
                maskedTris = tri.get_masked_triangles()
                verts = np.stack((tri.x[maskedTris], tri.y[maskedTris]), axis=-1)

                coll = PolyCollection(
                    verts=verts,
                    transOffset=self._m.figure.ax.transData,
                    **kwargs,
                )

            maskedTris = tri.get_masked_triangles()

            # find the masked points that are not masked by the datamask
            mask = ~datamask.copy()
            mask[np.where(datamask)[0][list(set(maskedTris.flat))]] = True

            # remember the mask
            self._m._data_mask = mask

            # special treatment of color input to properly distribute values
            if color is not None:
                coll.set_facecolors([color] * (len(x)) * 6)
            else:
                if array is not None:
                    # tri-contour meshes need 3 values for each triangle

                    if self.flat:
                        array = array[datamask][maskedTris].mean(axis=1)
                        coll.set_array(array.ravel())
                    else:
                        coll.set_array(array[datamask])

            return coll

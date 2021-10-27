from matplotlib.collections import EllipseCollection, PolyCollection
from matplotlib.tri import TriMesh, Triangulation
import numpy as np

from pyproj import CRS, Transformer


class shapes(object):
    def __init__(self, m):
        self.m = m
        pass

    def calc_geod_circle_points(self, lon, lat, radius, n=20, start_angle=0):
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

        geod = self.m.crs_plot.get_geod()
        lons, lats, back_azim = geod.fwd(
            np.broadcast_to(lon[:, None], (size, n)),
            np.broadcast_to(lat[:, None], (size, n)),
            np.linspace([start_angle] * size, [360 - start_angle] * size, n, axis=1),
            radius,
            radians=False,
        )

        return lons.T, lats.T

    def calc_ellipse_points(self, x0, y0, a, b, theta, n, start_angle=0):
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
        xs = x0 + a * np.cos(angs) * np.cos(theta) - b * np.sin(angs) * np.sin(theta)
        ys = y0 + a * np.cos(angs) * np.sin(theta) + b * np.sin(angs) * np.cos(theta)

        return (xs, ys)

    def _get_geod_circle_points(self, x, y, crs, radius, n=20):
        x, y = np.asarray(x), np.asarray(y)

        # transform from in-crs to lon/lat
        radius_t = Transformer.from_crs(
            CRS.from_user_input(self.m.get_crs(crs)),
            CRS.from_epsg(4326),
            always_xy=True,
        )
        # transform from lon/lat to the plot_crs
        plot_t = Transformer.from_crs(
            CRS.from_epsg(4326),
            CRS.from_user_input(self.m.crs_plot),
            always_xy=True,
        )

        lon, lat = radius_t.transform(x, y)
        # calculate some points on the geodesic circle
        lons, lats = self.calc_geod_circle_points(lon, lat, radius, n=n)

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

    def geod_circles(self, x, y, crs, radius, n, **kwargs):

        xs, ys, mask = self._get_geod_circle_points(x, y, crs, radius, n)

        # special treatment of array input to properly mask values
        array = kwargs.pop("array", None)
        # xs, ys, mask = props["xs"], props["ys"], props["mask"]

        # only plot polygons if they contain 2 or more vertices
        vertmask = np.count_nonzero(mask, axis=0) > 2
        # remember masked points
        self.m._data_mask = vertmask

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
            verts, transOffset=self.m.figure.ax.transData, array=array, **kwargs
        )
        return coll

    def _get_ellipse_points(self, x, y, crs, radius, radius_crs="in", n=20):
        # transform from crs to the plot_crs
        t_in_plot = Transformer.from_crs(
            self.m.get_crs(crs),
            self.m.crs_plot,
            always_xy=True,
        )
        # transform from crs to the radius_crs
        t_in_radius = Transformer.from_crs(
            self.m.get_crs(crs),
            self.m.get_crs(radius_crs),
            always_xy=True,
        )
        # transform from crs to the radius_crs
        t_radius_plot = Transformer.from_crs(
            self.m.get_crs(radius_crs),
            self.m.crs_plot,
            always_xy=True,
        )

        [rx, ry] = radius
        # transform corner-points
        if radius_crs == crs:
            pr = t_in_plot.transform(x, y + ry)
            pl = t_in_plot.transform(x, y - ry)
            d = np.ma.masked_invalid(pl) - np.ma.masked_invalid(pr)
            theta = np.arctan(d[1] / d[0]) - (np.pi / 2)

            xs, ys = self.calc_ellipse_points(
                x, y, np.full_like(x, rx), np.full_like(x, ry), theta, n=n
            )
            xs, ys = np.ma.masked_invalid((xs, ys), copy=False)
            xs, ys = np.ma.masked_invalid(t_in_plot.transform(xs, ys), copy=False)
        else:
            p = t_in_radius.transform(x, y)
            pr = t_radius_plot.transform(p[0], p[1] + y)
            pl = t_radius_plot.transform(p[0], p[1] - y)

            d = np.ma.masked_invalid(pl) - np.ma.masked_invalid(pr)
            theta = np.arctan(d[1] / d[0]) - (np.pi / 2)
            xs, ys = self.calc_ellipse_points(
                p[0], p[1], np.full_like(x, rx), np.full_like(x, ry), theta, n=n
            )

            xs, ys = np.ma.masked_invalid((xs, ys), copy=False)
            xs, ys = np.ma.masked_invalid(t_radius_plot.transform(xs, ys), copy=False)

        # get the mask for invalid, very distorted or very large shapes
        dx = xs.max(axis=1) - xs.min(axis=1)
        dy = ys.max(axis=1) - ys.min(axis=1)
        mask = (
            ~xs.mask.any(axis=1)
            & ~ys.mask.any(axis=1)
            & (dx < (np.ma.median(dx) * 10))
            & (dy < (np.ma.median(dy) * 10))
            & np.isfinite(theta)
        )

        return xs, ys, mask

    def ellipses(self, x, y, crs, radius, radius_crs, n, **kwargs):
        xs, ys, mask = self._get_ellipse_points(x, y, crs, radius, radius_crs, n=n)
        # special treatment of array input to properly mask values
        array = kwargs.pop("array", None)
        if array is not None:
            array = array[mask]

        verts = np.stack((xs[mask], ys[mask])).T.swapaxes(0, 1)

        coll = PolyCollection(
            verts, transOffset=self.m.figure.ax.transData, array=array, **kwargs
        )
        return coll

    def _get_rectangle_verts(self, x, y, crs, radius, radius_crs="in"):
        # transform from crs to the plot_crs
        t_in_plot = Transformer.from_crs(
            self.m.get_crs(crs),
            self.m.crs_plot,
            always_xy=True,
        )
        # transform from crs to the radius_crs
        t_in_radius = Transformer.from_crs(
            self.m.get_crs(crs),
            self.m.get_crs(radius_crs),
            always_xy=True,
        )
        # transform from crs to the radius_crs
        t_radius_plot = Transformer.from_crs(
            self.m.get_crs(radius_crs),
            self.m.crs_plot,
            always_xy=True,
        )

        [rx, ry] = radius
        # transform corner-points
        if radius_crs == crs:
            # top right
            p0 = t_in_plot.transform(x + rx, y + ry)
            # top left
            p1 = t_in_plot.transform(x - rx, y + ry)
            # bottom left
            p2 = t_in_plot.transform(x - rx, y - ry)
            # bottom right
            p3 = t_in_plot.transform(x + rx, y - ry)

        else:
            p = t_in_radius.transform(x, y)

            # top right
            p0 = t_radius_plot.transform(p[0] + rx, p[1] + ry)
            # top left
            p1 = t_radius_plot.transform(p[0] - rx, p[1] + ry)
            # bottom left
            p2 = t_radius_plot.transform(p[0] - rx, p[1] - ry)
            # bottom right
            p3 = t_radius_plot.transform(p[0] + rx, p[1] - ry)

        mask = np.all([np.isfinite(i).all(axis=0) for i in [p0, p1, p2, p3]], axis=0)

        # get the mask for invalid, very distorted or very large shapes
        dx = p0[0][mask] - p1[0][mask]
        dy = p0[1][mask] - p3[1][mask]

        mask[mask] = (
            mask[mask] & (dx < (np.nanmedian(dx) * 50)) & (dy < (np.nanmedian(dy) * 50))
        )

        verts = np.array(
            list(
                zip(
                    *[
                        np.array(i).T
                        for i in (
                            [i[mask] for i in p0],
                            [i[mask] for i in p1],
                            [i[mask] for i in p2],
                            [i[mask] for i in p3],
                        )
                    ]
                )
            )
        )
        return verts, mask

    def rectangles(self, x, y, crs, radius, radius_crs, **kwargs):
        verts, mask = self._get_rectangle_verts(x, y, crs, radius, radius_crs)

        # special treatment of array input to properly mask values
        array = kwargs.pop("array", None)
        if array is not None:
            array = array[mask]

        coll = PolyCollection(
            verts=verts,
            transOffset=self.m.figure.ax.transData,
            array=array,
            **kwargs,
        )

        return coll

    def _get_voroni_verts_and_mask(self, x, y, crs, radius, masked=True):
        try:
            from scipy.spatial import Voronoi
            from itertools import zip_longest
        except ImportError:
            raise ImportError("'scipy' is required for 'Voroni'!")

        # transform from crs to the plot_crs
        t_in_plot = Transformer.from_crs(
            self.m.get_crs(crs),
            self.m.crs_plot,
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

    def voroni(self, x, y, crs, radius, masked=True, **kwargs):

        # special treatment of array input to properly mask values
        array = kwargs.pop("array", None)

        verts, mask, datamask = self._get_voroni_verts_and_mask(
            x, y, crs, radius, masked=True
        )

        # remember masked points
        self.m._data_mask = mask

        if array is not None:
            array = array[datamask][mask]

        coll = PolyCollection(
            verts=verts,
            array=array,
            transOffset=self.m.figure.ax.transData,
            **kwargs,
        )

        return coll

    def _get_trimesh_rectangle_triangulation(self, x, y, crs, radius, radius_crs="in"):

        verts, mask = self._get_rectangle_verts(x, y, crs, radius, radius_crs)

        x = np.vstack([verts[:, 2][:, 0], verts[:, 3][:, 0], verts[:, 1][:, 0]]).T.flat
        y = np.vstack([verts[:, 2][:, 1], verts[:, 3][:, 1], verts[:, 1][:, 1]]).T.flat

        x2 = np.vstack([verts[:, 3][:, 0], verts[:, 0][:, 0], verts[:, 1][:, 0]]).T.flat
        y2 = np.vstack([verts[:, 3][:, 1], verts[:, 0][:, 1], verts[:, 1][:, 1]]).T.flat

        x = np.append(x, x2)
        y = np.append(y, y2)

        tri = Triangulation(
            x, y, triangles=np.array(range(len(x))).reshape((len(x) // 3, 3))
        )
        return tri, mask

    def trimesh_rectangles(self, x, y, crs, radius, radius_crs, **kwargs):
        # special treatment of color and array inputs to distribute the values
        color = kwargs.pop("color", None)
        array = kwargs.pop("array", None)

        tri, mask = self._get_trimesh_rectangle_triangulation(
            x, y, crs, radius, radius_crs
        )

        coll = TriMesh(
            tri,
            transOffset=self.m.figure.ax.transData,
            **kwargs,
        )

        # special treatment of color input to properly distribute values
        if color is not None:
            coll.set_facecolors([color] * (len(x)) * 6)
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

    def _get_delauney_triangulation(
        self, x, y, crs, radius, radius_crs="out", masked=True
    ):
        # prepare data
        try:
            from scipy.spatial import Delaunay
        except ImportError:
            raise ImportError("'scipy' is required for 'delauney_triangulation'!")

        # transform from crs to the plot_crs
        t_in_plot = Transformer.from_crs(
            self.m.get_crs(crs),
            self.m.crs_plot,
            always_xy=True,
        )

        x0, y0 = t_in_plot.transform(x, y)
        datamask = np.isfinite(x0) & np.isfinite(y0)

        d = Delaunay(np.column_stack((x0[datamask], y0[datamask])), qhull_options="QJ")

        tri = Triangulation(d.points[:, 0], d.points[:, 1], d.simplices)

        if masked:
            radiusx, radiusy = radius
            maxdist = 4 * np.mean(np.sqrt(radiusx ** 2 + radiusy ** 2))

            if radius_crs == "in":
                x, y = x[datamask][tri.triangles], y[datamask][tri.triangles]
                # get individual triangle side-lengths
                l = np.array(
                    [
                        np.sqrt(((x[:, i] - x[:, j]) ** 2) + ((y[:, i] - y[:, j]) ** 2))
                        for i, j in ((0, 1), (0, 2), (1, 2))
                    ]
                )
            elif self.m.plot_specs.radius_crs == "out":
                x0, y0 = x0[datamask][tri.triangles], y0[datamask][tri.triangles]

                # get individual triangle side-lengths
                l = np.array(
                    [
                        np.sqrt(
                            ((x0[:, i] - x0[:, j]) ** 2) + ((y0[:, i] - y0[:, j]) ** 2)
                        )
                        for i, j in ((0, 1), (0, 2), (1, 2))
                    ]
                )
            else:
                assert (
                    False
                ), f"the radius_crs '{radius_crs}' is not supported for delauney-masking"
            # mask any triangle whose side-length exceeds maxdist
            mask = np.any(l > maxdist, axis=0)
            tri.set_mask(mask)

        return tri, datamask

    def delauney_triangulation(
        self, x, y, crs, radius, radius_crs="out", flat=False, masked=False, **kwargs
    ):

        radiusx, radiusy = radius

        # special treatment of color and array inputs to distribute the values
        color = kwargs.pop("color", None)
        array = kwargs.pop("array", None)

        tri, datamask = self._get_delauney_triangulation(
            x, y, crs, radius, radius_crs, masked
        )

        if flat == False:
            coll = TriMesh(
                tri,
                transOffset=self.m.figure.ax.transData,
                **kwargs,
            )
        else:
            # Vertices of triangles.
            maskedTris = tri.get_masked_triangles()
            verts = np.stack((tri.x[maskedTris], tri.y[maskedTris]), axis=-1)

            coll = PolyCollection(
                verts=verts,
                transOffset=self.m.figure.ax.transData,
                **kwargs,
            )

        maskedTris = tri.get_masked_triangles()

        # special treatment of color input to properly distribute values
        if color is not None:
            coll.set_facecolors([color] * (len(x)) * 6)
        else:
            if array is not None:
                # tri-contour meshes need 3 values for each triangle

                if flat:
                    array = array[datamask][maskedTris].mean(axis=1)
                    coll.set_array(array.ravel())
                else:
                    coll.set_array(array[datamask])

        return coll

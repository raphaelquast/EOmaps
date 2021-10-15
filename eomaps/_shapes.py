from matplotlib.collections import EllipseCollection, PolyCollection
from matplotlib.tri import TriMesh, Triangulation
import numpy as np


class shapes(object):
    def __init__(self, m):
        self.m = m
        pass

    def ellipses(self, props=None, **kwargs):
        if props is None:
            props = self.m._props

        coll = EllipseCollection(
            2 * props["w"],
            2 * props["h"],
            props["theta"],
            offsets=list(zip(props["x0"], props["y0"])),
            units="x",
            **kwargs
        )

        return coll

    @staticmethod
    def _get_rectangle_verts(props):
        verts = np.array(
            list(
                zip(
                    *[
                        np.array(i).T
                        for i in (props["p0"], props["p1"], props["p2"], props["p3"])
                    ]
                )
            )
        )
        return verts

    def rectangles(self, props=None, **kwargs):
        if props is None:
            props = self.m._props

        coll = PolyCollection(verts=self._get_rectangle_verts(props), **kwargs)

        return coll

    @staticmethod
    def _get_voroni_verts_and_mask(props, masked=False):
        radiusx, radiusy = props["radius"]

        try:
            from scipy.spatial import Voronoi
            from itertools import zip_longest
        except ImportError:
            raise ImportError("'scipy' is required for 'Voroni'!")

        maxdist = 2 * np.mean(np.sqrt(radiusx ** 2 + radiusy ** 2))

        xy = np.column_stack((props["x0"], props["y0"]))
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
        return verts, mask

    def voroni(self, props=None, masked=True, **kwargs):
        if props is None:
            props = self.m._props

        # special treatment of array input to properly mask values
        array = kwargs.pop("array", None)

        verts, mask = self._get_voroni_verts_and_mask(props, masked)

        # remember masked points
        self.m._data_mask = mask

        if array is not None:
            array = array[mask]

        coll = PolyCollection(verts=verts, array=array, **kwargs)

        return coll

    @staticmethod
    def _get_trimesh_rectangle_triangulation(props):
        # prepare data
        verts = np.array(
            list(
                zip(
                    *[
                        np.array(i).T
                        for i in (props["p0"], props["p1"], props["p2"], props["p3"])
                    ]
                )
            )
        )
        x = np.vstack([verts[:, 2][:, 0], verts[:, 3][:, 0], verts[:, 1][:, 0]]).T.flat
        y = np.vstack([verts[:, 2][:, 1], verts[:, 3][:, 1], verts[:, 1][:, 1]]).T.flat

        x2 = np.vstack([verts[:, 3][:, 0], verts[:, 0][:, 0], verts[:, 1][:, 0]]).T.flat
        y2 = np.vstack([verts[:, 3][:, 1], verts[:, 0][:, 1], verts[:, 1][:, 1]]).T.flat

        x = np.append(x, x2)
        y = np.append(y, y2)

        tri = Triangulation(
            x, y, triangles=np.array(range(len(x))).reshape((len(x) // 3, 3))
        )
        return tri

    def trimesh_rectangles(self, props=None, **kwargs):
        if props is None:
            props = self.m._props
        # special treatment of color and array inputs to distribute the values
        color = kwargs.pop("color", None)
        array = kwargs.pop("array", None)

        tri = self._get_trimesh_rectangle_triangulation(props)

        coll = TriMesh(tri, **kwargs)

        if color is not None:
            coll.set_facecolors([color] * (len(props["x0"])) * 6)
        else:
            if array is not None:
                z = np.ma.masked_invalid(array)
                # tri-contour meshes need 3 values for each triangle
                z = np.broadcast_to(z, (3, len(z))).T
                # we plot 2 triangles per rectangle
                z = np.broadcast_to(z, (2, *z.shape))
                coll.set_array(z.ravel())

        return coll

    @staticmethod
    def _get_delauney_triangulation(props, masked):
        # prepare data
        try:
            from scipy.spatial import Delaunay
        except ImportError:
            raise ImportError("'scipy' is required for 'delauney_triangulation'!")

        d = Delaunay(np.column_stack((props["x0"], props["y0"])), qhull_options="QJ")

        tri = Triangulation(d.points[:, 0], d.points[:, 1], d.simplices)

        if masked:
            if radius_crs == "in":
                x = xorig[tri.triangles]
                y = yorig[tri.triangles]
            elif radius_crs == "out":
                x = x0[tri.triangles]
                y = y0[tri.triangles]
            else:
                x = x0r[tri.triangles]
                y = y0r[tri.triangles]

            maxdist = 4 * np.mean(np.sqrt(radiusx ** 2 + radiusy ** 2))

            verts = np.stack((x, y), axis=2)
            cpos = verts.mean(axis=1)[:, None]
            cdist = np.sqrt(np.sum((verts - cpos) ** 2, axis=2))

            mask = np.logical_or(
                np.any(cdist > maxdist * 2, axis=1), cdist.mean(axis=1) > maxdist
            )

            tri.set_mask(mask)

        return tri

    def delauney_triangulation(self, props=None, flat=False, masked=False, **kwargs):
        if props is None:
            props = self.m._props

        radiusx, radiusy = props["radius"]
        radius_crs = self.m.plot_specs["radius_crs"]

        # special treatment of color and array inputs to distribute the values
        color = kwargs.pop("color", None)
        array = kwargs.pop("array", None)

        tri = self._get_delauney_triangulation(props, masked)

        if flat == False:
            coll = TriMesh(tri, **kwargs)
        else:
            # Vertices of triangles.
            maskedTris = tri.get_masked_triangles()
            verts = np.stack((tri.x[maskedTris], tri.y[maskedTris]), axis=-1)

            coll = PolyCollection(verts=verts, **kwargs)

        if color is not None:
            coll.set_facecolors([color] * (len(props["x0"])) * 6)
        else:
            z = np.ma.masked_invalid(array)
            # tri-contour meshes need 3 values for each triangle
            z = np.tile(z, 3)
            coll.set_array(z.ravel())

        return coll

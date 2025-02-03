# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Inset maps class definitions."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path

from . import Maps
from .grid import _intersect, _get_intersect


class InsetMaps(Maps):
    """
    Base class to create inset maps.

    Note
    ----
    To create a new inset-map, see
    :py:meth:`Maps.new_inset_map <eomaps.eomaps.Maps.new_inset_map>`.

    """

    # a subclass of Maps that includes some special functions for inset maps

    def __init__(
        self,
        parent,
        crs=4326,
        layer=None,
        xy=(45, 45),
        xy_crs=4326,
        radius=5,
        radius_crs=None,
        plot_position=(0.5, 0.5),
        plot_size=0.5,
        shape="ellipses",
        indicate_extent=True,
        indicator_line=False,
        boundary=True,
        background_color="w",
        **kwargs,
    ):

        self._parent_m = self._proxy(parent)
        self._indicators = []
        # inherit the layer from the parent Maps-object if not explicitly
        # provided
        if layer is None:
            layer = self._parent_m.layer

        # put all inset-map artists on dedicated layers
        # NOTE: all artists of inset-map axes are put on a dedicated layer
        # with a "__inset_" prefix to ensure they appear on top of other artists
        # (AND on top of spines of normal maps)!
        # layer = "__inset_" + str(layer)

        possible_shapes = ["ellipses", "rectangles", "geod_circles"]
        assert (
            shape in possible_shapes
        ), f"EOmaps: the inset shape can only be one of {possible_shapes}"

        if shape == "geod_circles":
            assert radius_crs is None, (
                "EOmaps: Using 'radius_crs' is not possible if 'geod_circles' is "
                + "used as shape! (the radius for `geod_circles` is always in meters!)"
            )

        if radius_crs is None:
            radius_crs = xy_crs

        self._extent_kwargs = dict(ec="r", lw=1, fc="none")
        self._line_kwargs = dict(c="r", lw=2)
        boundary_kwargs = dict(ec="r", lw=2)

        if isinstance(boundary, dict):
            assert (
                len(set(boundary.keys()).difference({"ec", "lw"})) == 0
            ), "EOmaps: only 'ec' and 'lw' keys are allowed for the 'boundary' dict!"

            boundary_kwargs.update(boundary)
            # use same edgecolor for boundary and indicator by default
            self._extent_kwargs["ec"] = boundary["ec"]
            self._line_kwargs["c"] = boundary["ec"]
        elif isinstance(boundary, (str, tuple)):
            boundary_kwargs.update({"ec": boundary})
            # use same edgecolor for boundary and indicator by default
            self._extent_kwargs["ec"] = boundary
            self._line_kwargs["c"] = boundary

        if isinstance(indicate_extent, dict):
            self._extent_kwargs.update(indicate_extent)

        if isinstance(indicator_line, dict):
            self._line_kwargs.update(indicator_line)

        x, y = xy
        plot_x, plot_y = plot_position
        left = plot_x - plot_size / 2
        bottom = plot_y - plot_size / 2

        # initialize a new maps-object with a new axis
        super().__init__(
            crs=crs,
            f=self._parent_m.f,
            ax=(left, bottom, plot_size, plot_size),
            layer=layer,
            **kwargs,
        )

        # make sure inset-map axes are on a very high zorder
        # (needed for ordinary draw-cycle in savefig)
        self.ax.set_zorder(99999)

        # get the boundary of a ellipse in the inset_crs
        bnd, bnd_verts = self._get_inset_boundary(
            x, y, xy_crs, radius, radius_crs, shape
        )

        # set the map boundary
        self.ax.set_boundary(bnd)
        # set the plot-extent to the envelope of the shape
        (x0, y0), (x1, y1) = bnd_verts.min(axis=0), bnd_verts.max(axis=0)
        self.ax.set_extent((x0, x1, y0, y1), crs=self.ax.projection)

        # TODO turn off navigation until the matplotlib pull-request on
        # zoom-events in overlapping axes is resolved
        # https://github.com/matplotlib/matplotlib/pull/22347
        # self.ax.set_navigate(False)

        if boundary is not False:
            spine = self.ax.spines["geo"]
            spine.set_edgecolor(boundary_kwargs["ec"])
            spine.set_lw(boundary_kwargs["lw"])

        self._inset_props = dict(
            xy=xy, xy_crs=xy_crs, radius=radius, radius_crs=radius_crs, shape=shape
        )

        if indicate_extent is not False:
            self.add_extent_indicator(
                self._parent_m,
                **self._extent_kwargs,
            )

        self._indicator_lines = []
        if indicator_line is not False:
            self.add_indicator_line(**self._line_kwargs)

        # add a background patch to the "all" layer
        if background_color is not None:
            self._bg_patch = self._add_background_patch(
                color=background_color, layer=self.layer
            )
        else:
            self._bg_patch = None

        # attach callback to update indicator patches
        self.BM._before_fetch_bg_actions.append(self._update_indicator)

    def _get_spine_verts(self):
        s = self.ax.spines["geo"]
        s._adjust_location()
        verts = s.get_verts()

        verts = self.ax.transData.inverted().transform(s.get_verts())
        verts = np.column_stack(self._transf_plot_to_lonlat.transform(*verts.T))

        return verts

    def _update_indicator(self, *args, **kwargs):
        from matplotlib.patches import Polygon

        if not hasattr(self, "_patches"):
            self._patches = set()

        while len(self._patches) > 0:
            patch = self._patches.pop()
            self.BM.remove_bg_artist(patch, draw=False)
            try:
                patch.remove()
            except ValueError:
                # ignore ValueErrors in here (they are caused by cleanup methods
                # that already removed the artist)
                pass

        verts = self._get_spine_verts()
        for m, kwargs in self._indicators:
            verts_t = np.column_stack(m._transf_lonlat_to_plot.transform(*verts.T))

            p = Polygon(verts_t, **kwargs)
            # TODO implement this as a proper artist that updates itself
            # indicate the artist in the companion widget editor but deactivate
            # all buttons since they will not work on dynamically re-created artists...
            p.set_label("__EOmaps_deactivated InsetMap indicator")
            art = m.ax.add_patch(p)
            self.BM.add_bg_artist(art, layer=m.layer, draw=False)
            self._patches.add(art)

    def _add_background_patch(self, color, layer="all"):
        (art,) = self.ax.fill(
            [0, 0, 1, 1],
            [0, 1, 1, 0],
            fc=color,
            ec="none",
            zorder=-9999,
            transform=self.ax.transAxes,
        )

        art.set_label("Inset map background patch")

        self.BM.add_bg_artist(art, layer=layer)
        return art

    def _handle_spines(self):
        spine = self.ax.spines["geo"]
        if spine not in self.BM._bg_artists.get("__inset___SPINES__", []):
            self.BM.add_bg_artist(spine, layer="__inset___SPINES__")

    def _get_ax_label(self):
        return "inset_map"

    def plot_map(self, *args, **kwargs):
        set_extent = kwargs.pop("set_extent", False)
        super().plot_map(*args, **kwargs, set_extent=set_extent)

    # a convenience-method to add a boundary-polygon to a map
    def add_extent_indicator(self, m=None, n=100, **kwargs):
        """
        Add a polygon to a map that indicates the current extent of this inset-map.

        Parameters
        ----------
        m : eomaps.Maps or None
            The Maps-object that will be used to draw the marker.
            (e.g. the map on which the extent of the inset should be indicated)
            If None, the parent Maps-object that was used to create the inset-map
            is used. The default is None.
        n : int
            The number of points used to represent the polygon.
            The default is 100.
        kwargs :
            additional keyword-arguments passed to `m.add_marker`
            (e.g. "facecolor", "edgecolor" etc.)

        """
        if m is None:
            m = self._parent_m

        defaultargs = {**self._extent_kwargs}
        defaultargs.setdefault("zorder", 9999)
        defaultargs.update(kwargs)

        if not any((i in defaultargs for i in ["fc", "facecolor"])):
            defaultargs["fc"] = "none"
        if not any((i in defaultargs for i in ["ec", "edgecolor"])):
            defaultargs["ec"] = "r"
        if not any((i in defaultargs for i in ["lw", "linewidth"])):
            defaultargs["lw"] = 1

        self._indicators.append((m, defaultargs))
        self._update_indicator()

    def add_indicator_line(self, m=None, **kwargs):
        """
        Add a line that connects the inset-map to the inset location on a given map.

        The line connects the current inset-map (center) position to the center of the
        inset extent on the provided Maps-object.

        It is possible to add multiple indicator-lines for different maps!

        The lines will be automatically updated if axes sizes or positions change.

        Parameters
        ----------
        m : eomaps.Maps or None
            The Maps object for which the inset-line should be added.
            If None, the parent Maps-object that was used to create the inset-map
            is used. The default is None.

        kwargs :
            Additional kwargs are passed to plt.Line2D to style the appearance of the
            line (e.g. "c", "ls", "lw", ...)


        Examples
        --------

        """
        if m is None:
            m = self._parent_m

        defaultargs = {**self._line_kwargs}
        defaultargs.setdefault("c", "r")
        defaultargs.setdefault("lw", 2)
        defaultargs.setdefault("zorder", 99999)
        defaultargs.update(kwargs)

        l = plt.Line2D([0, 0], [1, 1], transform=self.f.transFigure, **defaultargs)
        l = self._parent.ax.add_artist(l)
        l.set_clip_on(False)

        self.BM.add_bg_artist(l, self.layer, draw=False)
        self._indicator_lines.append((l, m))

        if isinstance(m, InsetMaps):
            # in order to make the line visible on top of another inset-map
            # but NOT on the inset-map whose extent is indicated, the line has to
            # be drawn on the inset-map explicitly.

            # This is because all artists on inset-map axes are always on top of other
            # (normal map) artists... (and so the line would be behind the background)
            from matplotlib.transforms import TransformedPath

            clip_path = TransformedPath(
                m.ax.patch.get_path(), m.ax.projection._as_mpl_transform(m.ax)
            )

            defaultargs["zorder"] = 99999
            l2 = plt.Line2D([0, 0], [1, 1], **defaultargs, transform=m.f.transFigure)
            l2.set_clip_path(clip_path)
            l2.set_clip_on(True)

            l2 = m.ax.add_artist(l2)
            self.BM.add_bg_artist(l2, self.layer)
            self._indicator_lines.append((l2, m))

        self._update_indicator_lines()
        self.BM._before_fetch_bg_actions.append(self._update_indicator_lines)

    def _update_indicator_lines(self, *args, **kwargs):
        spine_verts = self._get_spine_verts()

        # find center of the inset map in the figure (in figure coordinates)
        verts = np.column_stack(self._transf_lonlat_to_plot.transform(*spine_verts.T))
        verts = (self.ax.transData + self.f.transFigure.inverted()).transform(verts)

        for l, m in self._indicator_lines:
            # find center of inset-map indicator on the map (in figure coordinates)
            verts_t = np.column_stack(
                m._transf_lonlat_to_plot.transform(*spine_verts.T)
            )
            verts_t = (m.ax.transData + m.f.transFigure.inverted()).transform(verts_t)
            p_map = verts_t.mean(axis=0)

            p_inset = verts.mean(axis=0)
            # find the first intersection point of lines connecting the centers
            # 1) with the inset-map boundary
            q = np.nonzero(_intersect(p_map, p_inset, verts[:-1], verts[1:]))[0]

            if len(q) > 0:
                x0, y0 = _get_intersect(
                    p_map, p_inset, verts[:-1][q[0]], verts[1:][q[0]]
                )
            else:
                x0, y0 = p_inset

            # 2) with the inset-map indicator on the map
            q = np.nonzero(_intersect(p_map, p_inset, verts_t[:-1], verts_t[1:]))[0]
            if len(q) > 0:
                x1, y1 = _get_intersect(
                    p_map, p_inset, verts_t[:-1][q[0]], verts_t[1:][q[0]]
                )

                # update indicator line vertices
                l.set_xdata([x0, x1])
                l.set_ydata([y0, y1])
                continue

    # a convenience-method to set the position based on the center of the axis
    def set_inset_position(self, x=None, y=None, size=None):
        """
        Set the (center) position and size of the inset-map.

        Parameters
        ----------
        x, y : int or float, optional
            The center position in relative units (0-1) with respect to the figure.
            If None, the existing position is used.
            The default is None.
        size : float, optional
            The relative radius (0-1) of the inset in relation to the figure width.
            If None, the existing size is used.
            The default is None.

        """
        x0, y1, x1, y0 = self.ax.get_position().bounds

        if size is None:
            size = abs(x1 - x0)

        if x is None:
            x = (x0 + x1) / 2
        if y is None:
            y = (y0 + y1) / 2

        self.ax.set_position((x - size / 2, y - size / 2, size, size))
        self.redraw("__inset_" + self.layer, "__inset___SPINES__")

    # a convenience-method to get the position based on the center of the axis
    def get_inset_position(self, precision=3):
        """
        Get the current inset position (and size).

        Parameters
        ----------
        precision : int, optional
            The precision of the returned position and size.
            The default is 3.

        Returns
        -------
        (x, y, size) : (float, float, float)
            The position and size of the inset-map.

        """
        bbox = self.ax.get_position()
        size = round(max(bbox.width, bbox.height), precision)
        x = round((bbox.x0 + bbox.width / 2), precision)
        y = round((bbox.y0 + bbox.height / 2), precision)

        return x, y, size

    def _get_inset_boundary(self, x, y, xy_crs, radius, radius_crs, shape, n=100):
        # get the inset-shape boundary

        shp = self.set_shape._get(shape)

        if shape == "ellipses":
            shp_pts = shp._get_points(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = np.stack(shp_pts[:2], axis=2)[0]

            # make sure vertices are right-handed
            bnd_verts = bnd_verts[::-1]

        elif shape == "rectangles":
            shp_pts = shp._get_rectangle_verts(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = shp_pts[0][0]

        elif shape == "geod_circles":
            shp_pts = shp._get_points(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                n=n,
            )
            bnd_verts = np.stack(shp_pts[:2], axis=2).squeeze()
            # make sure vertices are right-handed
            bnd_verts = bnd_verts[::-1]

        boundary = Path(bnd_verts)

        return boundary, bnd_verts

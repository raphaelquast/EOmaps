from .helpers import pairwise

import numpy as np
from pyproj import Transformer, CRS

from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.textpath import TextPath
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D


class ScaleBar:
    def __init__(
        self,
        m,
        nscales=10,
        scale=10000,
        width=5,
        colors=("k", "w"),
        frame_offsets=(1, 1),
        fontscale=1,
        patch_props=None,
    ):
        """
        Add a scalebar to the map.
        The scalebar represents a ruler in units of meters whose direction
        follows geodesic lines.

        Note
        ----
        You can click on the scalebar to dynamically adjust the position,
        orientation and size!

            - left-click on the scalebar to make it interactive
            - right-click to make the scalebar static again
            - drag the scalebar by "picking" it with the left mouse-button
            - use "+" and "-" keys on your keyboard to rotate the scalebar


        Parameters
        ----------
        lon, lat : float
            The longitude and latitude of the starting point for the scalebar
            (If None, the center of the axis is used )
        azim : float
            The azimuth-direction (in degrees) in which the scalebar points.
            The default is 90.
        nscales : int
            The number of scales (e.g. line-segments) to draw.
        scale : float
            The length (in meters) of the line-segments
        width : float
            The width of the scalebar (in ordinary matpltolib linewidth-units)
        colors : list, tuple, optional
            A sequence of colors that will be repeated to color the individual
            line-fragments of the scalebar. (you can provide more than 2 colors!)
            The default is ("k", "w").
        frame_offsets : tuple, optional
            A tuple to adjust the top- and right offset of the frame-patch.
            The default is (1, 1).
        fontscale : float, optional
            A factor to scale the fontsize. The default is 1.
        patch_props : dict, optional
            A dictionary that can be used to adjust the properties of the
            frame-patch. The default is None which translates to:

                >>> dict(fc=".75", ec="k", lw=2)
        """

        self.m = m
        self.nscales = nscales
        self.scale = scale
        self.width = width
        self.colors = colors
        self.frame_offsets = frame_offsets
        self.geod = self.m.crs_plot.get_geod()
        self.fontscale = fontscale

        # the interval for the azimuth when using + and - keys
        self.azimuth_interval = 1

        if patch_props is None:
            self.patch_props = dict(fc=".75", ec="k", lw=2)
        else:
            self.patch_props = patch_props

        # transform from lon/lat to the plot_crs
        self.plot_t = Transformer.from_crs(
            CRS.from_epsg(4326),
            CRS.from_user_input(self.m.crs_plot),
            always_xy=True,
        )

        self._artists = dict()

    def _get_pts(self, lon, lat, azim):
        interm_pts = 50
        pts = self.geod.fwd_intermediate(
            lon1=lon,
            lat1=lat,
            azi1=azim,
            npts=(self.nscales + 1),
            del_s=self.scale,
            initial_idx=0,
            terminus_idx=0,
        )

        lons, lats = [], []
        for [lon1, lon2], [lat1, lat2] in zip(pairwise(pts.lons), pairwise(pts.lats)):
            if abs(lon1 - lon2) > 180:
                continue
            if abs(lat1 - lat2) > 90:
                continue

            # get intermediate points
            p = self.geod.inv_intermediate(
                lon1=lon1,
                lat1=lat1,
                lon2=lon2,
                lat2=lat2,
                npts=interm_pts,
                initial_idx=0,
                terminus_idx=0,
            )
            lons.append(p.lons)
            lats.append(p.lats)

        # transform points to plot-crs
        pts_t = self.plot_t.transform(np.array(lons), np.array(lats))
        pts_t = np.stack(pts_t, axis=2)

        return pts_t

    def _txt(self):
        units = {" cm": 0.01, " m": 1, " km": 1000, "k km": 1000000}

        for key, val in units.items():
            x = self.scale * self.nscales / val
            if self.scale * self.nscales / val < 1000:
                return np.format_float_positional(x, trim="-", precision=3) + key

        return f"{self.scale} m"

    def _add_scalebar(self, lon=45, lat=45, azim=90):
        assert len(self._artists) == 0, "EOmaps: there is already a scalebar present!"

        # do this to make sure that the ax-transformations work as expected
        self.m.BM.update(self._artists.values())

        self._lon = lon
        self._lat = lat
        self._azim = azim

        pts = self._get_pts(lon, lat, azim)

        # estimate the rotation-angle for the text and the patch
        try:
            dx0, dy0 = pts[0][1] - pts[0][0]
            ang = np.arctan2(dy0, dx0)
            if not np.isfinite(ang):
                ang = 0
        except:
            ang = 0

        # get the position in figure coordinates
        x, y = self.m.figure.ax.transData.transform(self.plot_t.transform(lon, lat))

        self.d_fig = self.m.figure.ax.bbox.width / 100
        # translate d_fig to data-coordinates
        xb, yb = self.m.figure.ax.transData.inverted().transform(
            ([x, y + self.d_fig], [x, y - self.d_fig])
        )
        self.d = np.abs(xb[1] - yb[1])

        verts = self._get_patch_verts(pts, lon, lat, ang)
        p = PolyCollection([verts], **self.patch_props)
        self._artists["patch"] = self.m.figure.ax.add_artist(p)

        # get the base point for the text
        xt, yt = self.plot_t.transform(lon, lat)
        xt = xt - self.d * self.frame_offsets[1] * np.sin(ang) / 2
        yt = yt + self.d * self.frame_offsets[1] * np.cos(ang) / 2

        tp = TextPath((0, 0), self._txt(), size=self.fontscale * self.d)
        self._artists["text"] = self.m.figure.ax.add_artist(
            PathPatch(tp, color="black")
        )

        self._artists["text"].set_transform(
            Affine2D().scale(self.fontscale)
            + Affine2D().rotate(ang)
            + Affine2D().translate(xt, yt)
            + self.m.figure.ax.transData
        )

        coll = LineCollection(pts)

        colors = np.tile(self.colors, int(np.ceil(len(pts) / len(self.colors))))[
            : len(pts)
        ]
        coll.set_colors(colors)
        coll.set_linewidth(self.width)
        self._artists["scale"] = self.m.figure.ax.add_collection(coll, autolim=False)

        self.m.BM.add_artist(self._artists["scale"], layer=1)
        self.m.BM.add_artist(self._artists["text"], layer=1)
        self.m.BM.add_artist(self._artists["patch"], layer=0)

        self.m.BM.update(artists=self._artists.values())

        self._decorate_zooms()

    def _get_patch_verts(self, pts, lon, lat, ang):
        ot = 1.5 * self.d * self.frame_offsets[1]  # top offset
        ob = 0.5 * self.d * self.frame_offsets[0]  # right offset
        o0 = 0.5 * self.d  # left & bottom offset

        dxy = np.gradient(pts.reshape((-1, 2)), axis=0)
        alpha = np.arctan2(dxy[:, 1], -dxy[:, 0])
        t = np.column_stack([np.sin(alpha), np.cos(alpha)])

        ptop = pts.reshape((-1, 2)) - ot * t
        pbottom = pts.reshape((-1, 2)) + o0 * t

        ptop[0] += (o0 * np.cos(alpha[0]), -o0 * np.sin(alpha[0]))
        pbottom[0] += (o0 * np.cos(alpha[0]), -o0 * np.sin(alpha[0]))

        ptop[-1] -= (ob * np.cos(alpha[-1]), -ob * np.sin(alpha[-1]))
        pbottom[-1] -= (ob * np.cos(alpha[-1]), -ob * np.sin(alpha[-1]))

        return np.vstack([ptop, pbottom[::-1]])

    def set_position(self, lon=None, lat=None, azim=None):
        """
        set the position of the colorbar

        Parameters
        ----------
        lon : float, optional
            the longitude of the starting-point. The default is None.
        lat : float, optional
            the latitude of the starting point. The default is None.
        azim : float, optional
            the azimuth-direction in which to calculate the intermediate
            points for the scalebar. The default is None.
        """
        if lon is None:
            lon = self._lon
        if lat is None:
            lat = self._lat
        if azim is None:
            azim = self._azim

        pts = self._get_pts(lon, lat, azim)

        # estimate the rotation-angle for the text
        try:
            dx0, dy0 = pts[0][1] - pts[0][0]
            ang = np.arctan2(dy0, dx0)
            if not np.isfinite(ang):
                ang = 0
        except:
            ang = 0

        # don't use first and last scale (they are just used as placeholders)
        self._artists["scale"].set_verts(pts)
        colors = np.tile(self.colors, int(np.ceil(len(pts) / len(self.colors))))[
            : len(pts)
        ]
        self._artists["scale"].set_colors(colors)

        # get the base point for the text
        xt, yt = self.plot_t.transform(lon, lat)
        xt = xt - self.d * self.frame_offsets[1] * np.sin(ang) / 2
        yt = yt + self.d * self.frame_offsets[1] * np.cos(ang) / 2

        self._artists["text"].set_transform(
            Affine2D().scale(self.fontscale)
            + Affine2D().rotate(ang)
            + Affine2D().translate(xt, yt)
            + self.m.figure.ax.transData
        )

        verts = self._get_patch_verts(pts, lon, lat, ang)
        self._artists["patch"].set_verts([verts])

        self._lon = lon
        self._lat = lat
        self._azim = azim

    def _make_pickable(self):
        """
        Add callbacks to adjust the scalebar position manually

            - LEFT-click on the scalebar with the mouse to pick it up
                - hold down <LEFT> to drag the scalebar
            - use "+" and "-" keys to rotate the colorbar
            - RIGHT-click on the scalebar to detach the callbacks again
              (e.g. make it non-interactive)

        """

        def cb(self, s, pos, **kwargs):
            # s._artists["patch"].set_pickradius(150)
            # if not s._artists["patch"].contains(self.cb.click._event)[0]:
            #     return

            # transform from in-crs to lon/lat
            radius_t = Transformer.from_crs(
                CRS.from_user_input(self.crs_plot),
                CRS.from_epsg(4326),
                always_xy=True,
            )
            lon, lat = radius_t.transform(*pos)

            s.set_position(lon, lat)

        def cb_remove(self, s, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s.remove()

        def cb_az_up(self, s, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s._azim += s.azimuth_interval
            s.set_position()
            s.m.BM.update(artists=s._artists.values())

        def cb_az_down(self, s, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s._azim -= s.azimuth_interval
            s.set_position()
            s.m.BM.update(artists=s._artists.values())

        # ------------ callbacks to change frame with arrow-keys
        def cb_patch_y_up(self, s, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s.frame_offsets = (s.frame_offsets[0], s.frame_offsets[1] + 0.1)
            s.set_position()
            s.m.BM.update(artists=s._artists.values())

        def cb_patch_y_down(self, s, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s.frame_offsets = (s.frame_offsets[0], s.frame_offsets[1] - 0.1)
            s.set_position()
            s.m.BM.update(artists=s._artists.values())

        def cb_patch_x_up(self, s, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s.frame_offsets = (s.frame_offsets[0] + 0.1, s.frame_offsets[1])
            s.set_position()
            s.m.BM.update(artists=s._artists.values())

        def cb_patch_x_down(self, s, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s.frame_offsets = (s.frame_offsets[0] - 0.1, s.frame_offsets[1])
            s.set_position()
            s.m.BM.update(artists=s._artists.values())

        def addcbs(self, s, **kwargs):
            self.cb.click._only.append(s._cid_remove_cbs.split("__", 1)[0])

            # make sure we pick always only one scalebar
            for i in s._existing_pickers:
                p = getattr(self.cb, i)
                if p.is_picked is True and p.scalebar is not s:
                    p.scalebar._remove_callbacks()

            self.cb.pick[s._picker_name].is_picked = True

            if not hasattr(s, "_cid_move"):
                s._cid_move = self.cb.click.attach(cb, s=s)
                self.cb.click._only.append(s._cid_move.split("__", 1)[0])

            if not hasattr(s, "_cid_up"):
                s._cid_up = self.cb.keypress.attach(cb_az_up, key="+", s=s)
            if not hasattr(s, "_cid_down"):
                s._cid_down = self.cb.keypress.attach(cb_az_down, key="-", s=s)

            if not hasattr(s, "_cid_patch_x_up"):
                s._cid_up = self.cb.keypress.attach(cb_patch_x_up, key="right", s=s)
            if not hasattr(s, "_cid_patch_y_up"):
                s._cid_down = self.cb.keypress.attach(cb_patch_x_down, key="left", s=s)
            if not hasattr(s, "_cid_patch_x_down"):
                s._cid_up = self.cb.keypress.attach(cb_patch_y_up, key="up", s=s)
            if not hasattr(s, "_cid_patch_y_down"):
                s._cid_down = self.cb.keypress.attach(cb_patch_y_down, key="down", s=s)

            if not hasattr(s, "_cid_remove"):
                s._cid_remove = self.cb.keypress.attach(cb_remove, key="delete", s=s)

            s._artists["patch"].set_edgecolor("r")
            s._artists["patch"].set_linewidth(2)

        def rmcbs(self, s, **kwargs):
            s._remove_callbacks()

        self._picker_name = f"_scalebar{len(self._existing_pickers)}"

        self.m.cb.add_picker(self._picker_name, self._artists["patch"], True)
        self._cid_pick = self.m.cb.pick[self._picker_name].attach(addcbs, s=self)
        # remove all callbacks (except the pick-callback) on right-click
        self._cid_remove_cbs = self.m.cb.click.attach(rmcbs, s=self, button=3)

        self.m.cb.pick[self._picker_name].scalebar = self
        self.m.cb.pick[self._picker_name].is_picked = False

    @property
    def _existing_pickers(self):
        return [i for i in self.m.cb.__dict__ if i.startswith("_pick__scalebar")]

    def _remove_callbacks(self, **kwargs):
        if hasattr(self, "_cid_move"):
            self.m.cb.click.remove(self._cid_move)
            del self._cid_move

        if hasattr(self, "_cid_up"):
            self.m.cb.keypress.remove(self._cid_up)
            del self._cid_up
        if hasattr(self, "_cid_down"):
            self.m.cb.keypress.remove(self._cid_down)
            del self._cid_down

        if hasattr(self, "_cid_txt_up"):
            self.m.cb.keypress.remove(self._cid_txt_up)
            del self._cid_down
        if hasattr(self, "_cid_txt_down"):
            self.m.cb.keypress.remove(self._cid_txt_down)
            del self._cid_down

        self.m.cb.pick[self._picker_name].is_picked = False

        self.m.cb.click._only.clear()

        # reset the edgecolor
        for prop in ["ec", "edgecolor"]:
            if prop in self.patch_props:
                self._artists["patch"].set_edgecolor(self.patch_props[prop])
                break
            else:
                self._artists["patch"].set_edgecolor("k")

        # reset the linewidth
        for prop in ["lw", "linewidth"]:
            if prop in self.patch_props:
                if self.patch_props[prop] == 0:
                    self._artists["patch"].set_linewidth(self.patch_props[prop])
                    break
                else:
                    self._artists["patch"].set_linewidth(2)

    def _decorate_zooms(self):
        toolbar = self.m.figure.f.canvas.toolbar

        if toolbar is not None:
            toolbar.release_zoom = self._zoom_decorator(toolbar.release_zoom)
            toolbar.release_pan = self._zoom_decorator(toolbar.release_pan)
            toolbar._update_view = self._update_decorator(toolbar._update_view)

    def _setsize(self):
        # get the position in figure coordinates
        x, y = self.m.figure.ax.transData.transform(
            self.plot_t.transform(self._lon, self._lat)
        )

        self.d_fig = self.m.figure.ax.bbox.width / 100
        # translate d_fig to data-coordinates
        xb, yb = self.m.figure.ax.transData.inverted().transform(
            ([x, y + self.d_fig], [x, y - self.d_fig])
        )
        self.d = np.abs(xb[1] - yb[1])

    def _zoom_decorator(self, f):
        def newzoom(event):
            ret = f(event)
            self._setsize()

            tp = PathPatch(TextPath((0, 0), self._txt(), size=self.fontscale * self.d))
            self._artists["text"].set_path(tp.get_path())

            self.set_position()
            return ret

        return newzoom

    def _update_decorator(self, f):
        def newupdate():
            ret = f()
            self._setsize()

            tp = PathPatch(TextPath((0, 0), self._txt(), size=self.fontscale * self.d))
            self._artists["text"].set_path(tp.get_path())

            self.set_position()
            return ret

        return newupdate

    def get_position(self):
        """
        return the current position (and orientation) of the scalebar
        (e.g. to obtain the position after manual re-positioning)

        Returns
        -------
        list
            a list corresponding to [longitude, latitude, azimuth].
        """
        return [self._lon, self._lat, self._azim]

    def remove(self):
        """
        remove the scalebar from the map
        """
        self._remove_callbacks()
        for a in self._artists.values():
            self.m.BM.remove_artist(a)
            a.remove()

        self.m.BM.update()

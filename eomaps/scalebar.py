from .helpers import pairwise

import numpy as np
from pyproj import Transformer, CRS

from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.textpath import TextPath
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D
from matplotlib.font_manager import FontProperties


class ScaleBar:
    def __init__(
        self,
        m,
        scale=10000,
        scale_props=None,
        patch_props=None,
        label_props=None,
    ):
        """
        Add a scalebar to the map.
        The scalebar represents a ruler in units of meters whose direction
        follows geodesic lines.

        Note
        ----
        You can click on the scalebar to dynamically adjust its position,
        orientation and size!

            - < LEFT-click> on the scalebar to make the scalebar interactive
            - drag the scalebar by "picking" it with the < LEFT > mouse-button
            - use < + > and < - > keys on your keyboard to rotate the scalebar
            - use <alt> + < + > and < - > keys to set the text-offset
            - use the < arrow-keys > to increase the size of the frame
            - use < alt > + < arrow-keys > to decrease the size of the frame
            - use the < DELETE-key > to remove the scalebar from the plot
            - < RIGHT-click> to make the scalebar fixed again

        Parameters
        ----------
        lon, lat : float
            The longitude and latitude of the starting point for the scalebar
            (If None, the center of the axis is used )
        azim : float
            The azimuth-direction (in degrees) in which the scalebar points.
            The default is 90.
        scale : float
            The length (in meters) of the line-segments
        scale_props : dict, optional
            A dictionary that is used to set the properties of the scale.

            - "n": (int) The number of scales (e.g. line-segments) to draw.
            - "width": (float) The width of the scalebar
            - "colors" (tuple): A sequence of colors that will be repeated to
              color the individual line-fragments of the scalebar.
              (you can provide more than 2 colors!)
              The default is ("k", "w").

            The default is:
                >>> dict(n=10, width=5, colors=("k", "w"))
        patch_props : dict, optional
            A dictionary that is used to set the properties of the frame-patch.

            - "offsets": A tuple that is used to adjust the offset of the
              frame-patch. Individual values represent `(top, bottom, left, right)`
              on a horizontally oriented scalebar.
              The default is (1, 1, 1, 1).
            - ... additional kwargs are passed to the PolygonPatch used to draw the
              frame. Possible values are:

             - "facecolor", "edgecolor", "linewidth", "linestyle", "alpha" ...

            The default is:
                >>> dict(fc=".75", ec="k", lw=1)
        label_props : dict, optional
            A dictionary that is used to set the properties of the labels.

            - "scale": A scaling factor for the fontsize
            - "offset" : A scaling factor to adjust the offset of the labels
              relative to the scalebar
            - "rotation" : the rotation angle of the labels (in degrees)
              relative to the curvature of the scalebar
            - "color" : The color of the text
            - ... additional kwargs are passed to `matplotlib.font_manager.FontProperties`
              to set the used font-properties. Possible values are:

              - "family", "style", "variant", "stretch", and "weight"

              for example: `{family="Helvetica", style="italic"}`

            The default is:
                >>> dict(scale=1, offset=1, rotation=0)
        """

        self._m = m

        # number of intermediate points for evaluating the curvature
        self._interm_pts = 20

        self._cb_offset_interval = 0.05
        self._cb_rotate_inverval = 1

        self._fontkeys = ("family", "style", "variant", "stretch", "weight")
        self._font_kwargs = dict()

        self._scale_props = dict(scale=scale, n=10, width=5, colors=("k", "w"))
        self._patch_props = dict(fc=".75", ec="k", lw=1, ls="-")
        self._patch_offsets = (1, 1, 1, 1)
        self._label_props = dict(scale=1, rotation=0, every=2, offset=1, color="k")

        self.set_scale_props(scale=scale, **(scale_props if scale_props else {}))
        # set the label properties
        self.set_label_props(**(label_props if label_props else {}))
        # set the patch properties
        self.set_patch_props(**(patch_props if patch_props else {}))

        # geod from plot_crs
        self._geod = self._m.crs_plot.get_geod()
        # Transformer from lon/lat to the plot_crs
        self._t_plot = Transformer.from_crs(
            CRS.from_epsg(4326),
            CRS.from_user_input(self._m.crs_plot),
            always_xy=True,
        )
        # Transformer from in-crs to lon/lat
        self._t_lonlat = Transformer.from_crs(
            CRS.from_user_input(self._m.crs_plot),
            CRS.from_epsg(4326),
            always_xy=True,
        )

        self._artists = dict()

    @property
    def cb_rotate_interval(self):
        """
        Get/set the interval for the rotation when using the <+> and <->
        keys on the keyboard to rotate the scalebar
        """
        return self._cb_rotate_inverval

    @cb_rotate_interval.setter
    def cb_rotate_interval(self, val):
        self._cb_rotate_inverval = val

    @property
    def cb_offset_interval(self):
        """
        Get/set the interval for the text-offset when using the <alt> + <+>/<->
        keyboard-shortcut to set the offset for the scalebar-labels.
        """
        return self._cb_offset_interval

    @cb_offset_interval.setter
    def cb_offset_interval(self, val):
        self._cb_offset_interval = val

    def set_scale_props(self, scale=None, n=None, width=None, colors=None):
        """
        Set the properties of the scalebar (and update the plot accordingly)

        Parameters
        ----------
        scale  : float, optional
            The length (in meters) of the individual line-segments.
            The default is 10000.
        n : int, optional
            The number of scales (e.g. line-segments) to draw.
            The default is 10.
        width : float, optional
            The width of the scalebar (in ordinary matplotlib linewidth units).
            The default is 5.
        colors : tuple, optional
            A sequence of colors that will be repeated to color the individual
            line-fragments of the scalebar. (you can provide more than 2 colors!)
            The default is ("k", "w").
        """
        if scale is not None:
            self._scale_props["scale"] = scale
        if n is not None:
            self._scale_props["n"] = n
            self._redraw_minitxt()
        if width is not None:
            self._scale_props["width"] = width
        if colors is not None:
            self._scale_props["colors"] = colors

        if hasattr(self, "_lon") and hasattr(self, "_lat"):
            self.set_position()
            self._m.BM.update()

    def set_patch_props(self, offsets=None, **kwargs):
        """
        Set the properties of the frame (and update the plot accordingly)

        Parameters
        ----------
        offsets : tuple, optional
            A tuple that is used to adjust the offset of the frame-patch.
            Individual values represent `(top, bottom, left, right)` on a
            horizontally oriented scalebar. The default is (1, 1, 1, 1).
        kwargs :
            Additional kwargs are passed to the `matpltlotlib.Patches.PolygonPatch`
            that is used to draw the frame.
            The default is `{"fc": ".75", "ec": "k", "lw": 1, "ls": "-"}`

            Possible values are:

            - "facecolor", "edgecolor", "linewidth", "linestyle", "alpha" ...
        """
        if offsets is not None:
            self._patch_offsets = offsets

        for key, synonym in [
            ["fc", "facecolor"],
            ["ec", "edgecolor"],
            ["lw", "linewidth"],
            ["ls", "linestyle"],
        ]:
            self._patch_props[key] = kwargs.pop(
                key, kwargs.pop(synonym, self._patch_props[key])
            )

        self._patch_props.update(kwargs)

        if hasattr(self, "_lon") and hasattr(self, "_lat"):
            self.set_position()
            self._m.BM.update()

    def set_label_props(
        self, scale=None, rotation=None, every=None, offset=None, color=None, **kwargs
    ):
        """
        Set the properties of the labels (and update the plot accordingly)

        Parameters
        ----------
        scale : int, optional
            A scaling factor for the fontsize of the labels. The default is 1.
        rotation : float, optional
            the rotation angle of the labels (in degrees) relative to the
            curvature of the scalebar. The default is 0.
        every : int, optional
            DESCRIPTION. The default is 2.
        offset : float, optional
            A scaling factor to adjust the offset of the labels relative to the
            scalebar. The default is 1.
        color : str or tuple
            The color of the text.
            The default is "k" (e.g. black)
        kwargs :
            Additional kwargs are passed to `matplotlib.font_manager.FontProperties`
            to set the font specifications of the labels. Possible values are:

              - "family", "style", "variant", "stretch", and "weight"

            For example:
                >>> dict(family="Helvetica", style="italic").

        """

        if scale is not None:
            self._label_props["scale"] = scale
        if rotation is not None:
            self._label_props["rotation"] = rotation
        if every is not None:
            self._label_props["every"] = every
            self._redraw_minitxt()
        if offset is not None:
            self._label_props["offset"] = offset
        if color is not None:
            self._label_props["color"] = color

        self._font_kwargs.update(
            **{key: kwargs.pop(key) for key in self._fontkeys if key in kwargs}
        )
        self._font_props = FontProperties(**self._font_kwargs)

        self._label_props.update(kwargs)

        if hasattr(self, "_lon") and hasattr(self, "_lat"):
            self.set_position()
            self._m.BM.update()

    def _get_base_pts(self, lon, lat, azim, npts=None):
        if npts is None:
            npts = self._scale_props["n"] + 1

        pts = self._geod.fwd_intermediate(
            lon1=lon,
            lat1=lat,
            azi1=azim,
            npts=npts,
            del_s=self._scale_props["scale"],
            initial_idx=0,
            terminus_idx=0,
        )
        return pts

    def _get_pts(self, lon, lat, azim):
        pts = self._get_base_pts(lon, lat, azim)

        lons, lats = [], []
        for [lon1, lon2], [lat1, lat2] in zip(pairwise(pts.lons), pairwise(pts.lats)):
            if abs(lon1 - lon2) > 180:
                continue
            if abs(lat1 - lat2) > 90:
                continue

            # get intermediate points
            p = self._geod.inv_intermediate(
                lon1=lon1,
                lat1=lat1,
                lon2=lon2,
                lat2=lat2,
                npts=self._interm_pts,
                initial_idx=0,
                terminus_idx=0,
            )
            lons.append(p.lons)
            lats.append(p.lats)

        # transform points to plot-crs
        pts_t = self._t_plot.transform(np.array(lons), np.array(lats))
        pts_t = np.stack(pts_t, axis=2)

        return pts_t

    def _get_txt(self, n):
        scale = self._scale_props["scale"]
        # the text displayed above the scalebar
        units = {" cm": 0.01, " m": 1, " km": 1000, "k km": 1000000}
        for key, val in units.items():
            x = scale * n / val
            if scale * n / val < 1000:
                return np.format_float_positional(x, trim="-", precision=3) + key

        return f"{scale} m"

    def _txt(self):
        return self._get_txt(self._scale_props["n"])

    def _get_d(self):
        # the base length used to define zhe size of the scalebar
        # get the position in figure coordinates
        x, y = self._m.figure.ax.transData.transform(
            self._t_plot.transform(self._lon, self._lat)
        )

        d_fig = max(self._m.figure.ax.bbox.height, self._m.figure.ax.bbox.width) / 100
        # translate d_fig to data-coordinates
        xb, yb = self._m.figure.ax.transData.inverted().transform(
            ([x, y + d_fig], [x, y - d_fig])
        )
        return np.abs(xb[1] - yb[1])

    def _get_patch_verts(self, pts, lon, lat, ang, d):
        ot = 0.5 * d * self._patch_offsets[0]  # top offset
        ob = 2.5 * d * self._patch_offsets[1]  # bottom offset

        o_l = 0.5 * d * self._patch_offsets[2]  # left offset
        o_r = 1.5 * d * self._patch_offsets[3]  # right offset

        dxy = np.gradient(pts.reshape((-1, 2)), axis=0)
        alpha = np.arctan2(dxy[:, 1], -dxy[:, 0])
        t = np.column_stack([np.sin(alpha), np.cos(alpha)])

        ptop = pts.reshape((-1, 2)) - ot * t
        pbottom = pts.reshape((-1, 2)) + ob * t

        ptop[0] += (o_l * np.cos(alpha[0]), -o_l * np.sin(alpha[0]))
        pbottom[0] += (o_l * np.cos(alpha[0]), -o_l * np.sin(alpha[0]))

        ptop[-1] -= (o_r * np.cos(alpha[-1]), -o_r * np.sin(alpha[-1]))
        pbottom[-1] -= (o_r * np.cos(alpha[-1]), -o_r * np.sin(alpha[-1]))

        return np.vstack([ptop, pbottom[::-1]])

    def _get_ang(self, p0, p1):
        # estimate the rotation-angle for the text
        try:
            dx0, dy0 = p1 - p0
            ang = np.arctan2(dy0, dx0)
            if not np.isfinite(ang):
                ang = 0
        except:
            ang = 0
        return ang

    def _get_txt_coords(self, lon, lat, d, ang):
        # get the base point for the text
        xt, yt = self._t_plot.transform(lon, lat)
        xt = xt - d * self._label_props["offset"] * np.sin(ang) / 2
        yt = yt + d * self._label_props["offset"] * np.cos(ang) / 2
        return xt, yt

    def _set_minitxt(self, d, pts):

        angs = np.arctan2(*np.array([p[0] - p[-1] for p in pts]).T[::-1])
        angs = [*angs, angs[-1]]
        pts = self._get_base_pts(
            self._lon, self._lat, self._azim, npts=self._scale_props["n"] + 2
        )

        for i, (lon, lat, ang) in enumerate(zip(pts.lons, pts.lats, angs)):
            if i % self._label_props["every"] != 0:
                continue
            if i == 0:
                txt = "0"
            else:
                txt = self._get_txt(i)

            xy = self._get_txt_coords(
                lon, lat, self._label_props["scale"] * d * 1.5, ang
            )
            tp = TextPath(
                xy, txt, size=self._label_props["scale"] * d / 2, prop=self._font_props
            )

            self._artists[f"text_{i}"] = self._m.figure.ax.add_artist(
                PathPatch(tp, color=self._label_props["color"], lw=0)
            )
            self._artists[f"text_{i}"].set_transform(
                Affine2D().rotate_around(
                    *xy, ang + np.pi / 2 + np.deg2rad(self._label_props["rotation"])
                )
                + self._m.figure.ax.transData
            )
            self._m.BM.add_artist(self._artists[f"text_{i}"], layer=1)

    def _redraw_minitxt(self):
        # don't redraw if we haven't drawn anything yet
        if not hasattr(self, "_artists"):
            return

        for key in list(self._artists):
            if key.startswith("text_"):
                self._artists[key].remove()
                self._m.BM.remove_artist(self._artists[key])
                del self._artists[key]

        pts = self._get_pts(self._lon, self._lat, self._azim)
        d = self._get_d()
        self._set_minitxt(d, pts)

    def _update_minitxt(self, d, pts):
        angs = np.arctan2(*np.array([p[0] - p[-1] for p in pts]).T[::-1])
        angs = [*angs, angs[-1]]
        pts = self._get_base_pts(
            self._lon, self._lat, self._azim, npts=self._scale_props["n"] + 2
        )

        for i, (lon, lat, ang) in enumerate(zip(pts.lons, pts.lats, angs)):
            if i % self._label_props["every"] != 0:
                continue

            if i == 0:
                txt = "0"
            else:
                txt = self._get_txt(i)

            xy = self._get_txt_coords(
                lon, lat, self._label_props["scale"] * d * 1.5, ang
            )

            tp = PathPatch(
                TextPath(
                    xy,
                    txt,
                    size=self._label_props["scale"] * d / 2,
                    prop=self._font_props,
                ),
                lw=0,
            )
            self._artists[f"text_{i}"].set_path(tp.get_path())
            self._artists[f"text_{i}"].set_transform(
                Affine2D().rotate_around(
                    *xy, ang + np.pi / 2 + np.deg2rad(self._label_props["rotation"])
                )
                + self._m.figure.ax.transData
            )

    def _add_scalebar(self, lon, lat, azim):
        assert len(self._artists) == 0, "EOmaps: there is already a scalebar present!"
        # do this to make sure that the ax-transformations work as expected
        self._m.BM.update()

        self._lon = lon
        self._lat = lat
        self._azim = azim

        pts = self._get_pts(lon, lat, azim)
        d = self._get_d()
        ang = self._get_ang(pts[0][0], pts[0][1])

        # -------------- add the patch
        verts = self._get_patch_verts(pts, lon, lat, ang, d)
        p = PolyCollection([verts], **self._patch_props)
        self._artists["patch"] = self._m.figure.ax.add_artist(p)

        # -------------- add the labels
        self._set_minitxt(d, pts)

        # -------------- add the scalebar
        coll = LineCollection(pts)
        colors = np.tile(
            self._scale_props["colors"],
            int(np.ceil(len(pts) / len(self._scale_props["colors"]))),
        )[: len(pts)]
        coll.set_colors(colors)
        coll.set_linewidth(self._scale_props["width"])
        self._artists["scale"] = self._m.figure.ax.add_collection(coll, autolim=False)

        # -------------- make all artists animated
        self._m.BM.add_artist(self._artists["scale"], layer=1)
        # self._m.BM.add_artist(self._artists["text"], layer=1)
        self._m.BM.add_artist(self._artists["patch"], layer=0)

        self._m.BM.update(artists=self._artists.values())

        # make sure to update the artists on zoom
        self._decorate_zooms()

    def set_position(self, lon=None, lat=None, azim=None, update=True):
        """
        Sset the position of the colorbar

        Parameters
        ----------
        lon : float, optional
            The longitude of the starting-point. The default is None.
        lat : float, optional
            The latitude of the starting point. The default is None.
        azim : float, optional
            The azimuth-direction in which to calculate the intermediate
            points for the scalebar. The default is None.
        update : bool
            Indicator if the plot should be updated or not
            The default is True.
        """
        if lon is None:
            lon = self._lon
        if lat is None:
            lat = self._lat
        if azim is None:
            azim = self._azim

        pts = self._get_pts(lon, lat, azim)
        d = self._get_d()
        ang = self._get_ang(pts[0][0], pts[0][1])

        # don't use first and last scale (they are just used as placeholders)
        self._artists["scale"].set_verts(pts)
        colors = np.tile(
            self._scale_props["colors"],
            int(np.ceil(len(pts) / len(self._scale_props["colors"]))),
        )[: len(pts)]
        self._artists["scale"].set_colors(colors)

        verts = self._get_patch_verts(pts, lon, lat, ang, d)
        self._artists["patch"].set_verts([verts])
        self._artists["patch"].update(self._patch_props)

        if self._m.cb.pick[self._picker_name].is_picked:
            self._artists["patch"].set_edgecolor("r")
            self._artists["patch"].set_linewidth(2)
            self._artists["patch"].set_linestyle("-")

        self._lon = lon
        self._lat = lat
        self._azim = azim

        # do this after setting _lon, _lat and _azim !
        self._update_minitxt(d, pts)

        if update:
            self._m.BM.update()

    def _make_pickable(self):
        """
        Add callbacks to adjust the scalebar position manually

            - <LEFT>-click on the scalebar with the mouse to pick it up
                - hold down <LEFT> to drag the scalebar
            - use "+" and "-" keys to rotate the colorbar
            - <RIGHT>-click on the scalebar to detach the callbacks again
              (e.g. make it non-interactive)
            - use <ARROW-keys> to set the size of the patch
        """

        def scb_move(self, s, pos, **kwargs):
            # s._artists["patch"].set_pickradius(150)
            # if not s._artists["patch"].contains(self.cb.click._event)[0]:
            #     return
            lon, lat = s._t_lonlat.transform(*pos)
            # don't update here... the click callback updates itself!
            s.set_position(lon, lat, update=False)

        def scb_remove(self, s, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s.remove()

        def scb_az_ud(self, s, up=True, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            s._azim += s.cb_rotate_interval if up else -s.cb_rotate_interval
            s.set_position(update=True)

        # ------------ callbacks to change frame with arrow-keys
        def scb_patch_dim(self, s, udlr, add=True, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return
            o = [*s._patch_offsets]
            o[udlr] += 0.1 if add else -0.1
            s.set_patch_props(offsets=o)

        # ------------ callbacks to change the text offset with alt +-
        def scb_txt_offset(self, s, add=True, **kwargs):
            if not self.cb.pick[s._picker_name].is_picked:
                return

            o = s._label_props["offset"]
            o += s._cb_offset_interval if add else -s._cb_offset_interval
            s.set_label_props(offset=o)

        def addcbs(self, s, **kwargs):
            self.cb.click._only.append(s._cid_remove_cbs.split("__", 1)[0])

            # make sure we pick always only one scalebar
            for i in s._existing_pickers:
                p = getattr(self.cb, i)
                if p.is_picked is True and p.scalebar is not s:
                    p.scalebar._remove_callbacks()

            self.cb.pick[s._picker_name].is_picked = True

            if not hasattr(s, "_cid_move"):
                s._cid_move = self.cb.click.attach(scb_move, s=s)
                self.cb.click._only.append(s._cid_move.split("__", 1)[0])

            if not hasattr(s, "_cid_up"):
                s._cid_up = self.cb.keypress.attach(scb_az_ud, key="+", up=True, s=s)
            if not hasattr(s, "_cid_down"):
                s._cid_down = self.cb.keypress.attach(scb_az_ud, key="-", up=False, s=s)

            if not hasattr(s, "_cid_txt_offset_up"):
                s._cid_txt_offset_up = self.cb.keypress.attach(
                    scb_txt_offset, key="alt++", add=True, s=s
                )
            if not hasattr(s, "_cid_txt_offset_down"):
                s._cid_txt_offset_down = self.cb.keypress.attach(
                    scb_txt_offset, key="alt+-", add=False, s=s
                )

            for key, udlr in zip(["up", "down", "left", "right"], range(4)):
                if not hasattr(s, f"_cid_patch_dim_{key}_0"):
                    setattr(
                        s,
                        f"_cid_patch_dim_{key}_0",
                        self.cb.keypress.attach(
                            scb_patch_dim, key=key, udlr=udlr, add=True, s=s
                        ),
                    )
                if not hasattr(s, f"_cid_patch_dim_{key}_1"):
                    setattr(
                        s,
                        f"_cid_patch_dim_{key}_1",
                        self.cb.keypress.attach(
                            scb_patch_dim, key="alt+" + key, udlr=udlr, add=False, s=s
                        ),
                    )

            if not hasattr(s, "_cid_remove"):
                s._cid_remove = self.cb.keypress.attach(scb_remove, key="delete", s=s)

        def scb_unpick(self, s, **kwargs):
            s._remove_callbacks()

        self._picker_name = f"_scalebar{len(self._existing_pickers)}"

        self._m.cb.add_picker(self._picker_name, self._artists["patch"], True)
        self._cid_pick = self._m.cb.pick[self._picker_name].attach(addcbs, s=self)
        # remove all callbacks (except the pick-callback) on right-click
        self._cid_remove_cbs = self._m.cb.click.attach(scb_unpick, s=self, button=3)

        self._m.cb.pick[self._picker_name].scalebar = self
        self._m.cb.pick[self._picker_name].is_picked = False

    @property
    def _existing_pickers(self):
        return [i for i in self._m.cb.__dict__ if i.startswith("_pick__scalebar")]

    def _remove_callbacks(self, **kwargs):
        if hasattr(self, "_cid_move"):
            self._m.cb.click.remove(self._cid_move)
            del self._cid_move

        if hasattr(self, "_cid_up"):
            self._m.cb.keypress.remove(self._cid_up)
            del self._cid_up
        if hasattr(self, "_cid_down"):
            self._m.cb.keypress.remove(self._cid_down)
            del self._cid_down

        if hasattr(self, "_cid_txt_up"):
            self._m.cb.keypress.remove(self._cid_txt_up)
            del self._cid_down
        if hasattr(self, "_cid_txt_down"):
            self._m.cb.keypress.remove(self._cid_txt_down)
            del self._cid_down

        self._m.cb.pick[self._picker_name].is_picked = False

        self._m.cb.click._only.clear()
        self.set_position()

    def _decorate_zooms(self):
        toolbar = self._m.figure.f.canvas.toolbar

        if toolbar is not None:
            toolbar.release_zoom = self._zoom_decorator(toolbar.release_zoom)
            toolbar.release_pan = self._zoom_decorator(toolbar.release_pan)
            toolbar._update_view = self._update_decorator(toolbar._update_view)

    def _zoom_decorator(self, f):
        def newzoom(event):
            ret = f(event)
            self.set_position()
            return ret

        return newzoom

    def _update_decorator(self, f):
        def newupdate():
            ret = f()
            self.set_position()
            return ret

        return newupdate

    def get_position(self):
        """
        Return the current position (and orientation) of the scalebar
        (e.g. to obtain the position after manual re-positioning)

        Returns
        -------
        list
            a list corresponding to [longitude, latitude, azimuth].
        """
        return [self._lon, self._lat, self._azim]

    def remove(self):
        """
        Remove the scalebar from the map
        """
        self._remove_callbacks()
        for a in self._artists.values():
            self._m.BM.remove_artist(a)
            a.remove()

        self._m.BM.update()

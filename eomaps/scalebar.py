from .helpers import pairwise
from collections import OrderedDict

import numpy as np
from pyproj import Transformer, CRS

from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.textpath import TextPath
from matplotlib.patches import PathPatch, CirclePolygon
from matplotlib.transforms import Affine2D
from matplotlib.font_manager import FontProperties
from matplotlib.offsetbox import AuxTransformBox
import matplotlib.transforms as transforms


class ScaleBar:
    """Base class for EOmaps scalebars."""

    def __init__(
        self,
        m,
        preset=None,
        scale=None,
        autoscale_fraction=0.25,
        auto_position=(0.75, 0.25),
        scale_props=None,
        patch_props=None,
        label_props=None,
        layer=None,
    ):
        """
        Add a scalebar to the map.

        The scalebar represents a ruler in units of meters whose direction
        follows geodesic lines.

        Note
        ----
        You can click on the scalebar to dynamically adjust its position,
        orientation and size! (hold down the left mouse-button to use the keys)

            - < LEFT-click> on the scalebar to make the scalebar interactive
            - you can move and interact with the scalebar as long as you hold down the
              < LEFT > mouse-button
            - use < + > and < - > keys on your keyboard to rotate the scalebar
            - use <alt> + < + > and < - > keys to set the text-offset
            - use the < arrow-keys > to increase the size of the frame
            - use < alt > + < arrow-keys > to decrease the size of the frame
            - use the < DELETE-key > to remove the scalebar from the plot

        Parameters
        ----------
        lon, lat : float
            The longitude and latitude of the starting point for the scalebar
            (If None, the center of the axis is used )
        azim : float
            The azimuth-direction (in degrees) in which the scalebar points.
            The default is 90.
        preset : str
            The name of the style preset to use.

            - "bw" : a simple black-and white ruler without a background patch

        scale : float or None, optional
            The distance of the individual segments of the scalebar.

            - If None: the scale is automatically updated based on the current
              zoom level and the provided "autoscale_fraction".
            - If float: A fixed length of the segments (in meters).
              (e.g. the total length of the scalebar will be `scale_props["n"] * scale`

            The default is None.
        autoscale_fraction : float, optional
            The (approximate) fraction of the axis width to use as size for the scalebar
            in the autoscale procedure. Note that this is number is not exact since
            (depending on the crs) the final scalebar might be curved.
            The default is 0.25.
        auto_position : tuple or False, optional
            Re-position the scalebar automatically on pan/zoom events.

            - If False: the position of the scalebar remains fixed.
            - If a tuple is provided, it is identified as relative (x, y) position
              on the axes (e.g. (0,0)=lower left, (1,1)=upper right )

            The default is (0.75, 0.25).
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
            - "every" : indicator which scales should be labelled (e.g. every nth)
            - ... additional kwargs are passed to `matplotlib.font_manager.FontProperties`
              to set the used font-properties. Possible values are:

              - "family", "style", "variant", "stretch", and "weight"

              for example: `{family="Helvetica", style="italic"}`

            The default is:
                >>> dict(scale=1, offset=1, rotation=0, every=2)
        layer : str, optional
            The layer at which the scalebar should be visible.
            If None, the layer of the Maps-object used to create the scalebar is used.
            The default is None.

        """
        self._m = m

        if layer is None:
            layer = self._m.layer
        self.layer = layer

        self._scale_props = dict(scale=None)
        self._label_props = dict()
        self._patch_props = dict()
        self._patch_offsets = (1, 1, 1, 1)

        self._font_kwargs = dict()
        self._fontkeys = ("family", "style", "variant", "stretch", "weight")

        # apply preset styling (so that any additional properties are applied on top
        # of the preset)
        self._apply_preset(preset)

        if scale is None:
            self._autoscale = autoscale_fraction
        else:
            self._autoscale = None

        self._auto_position = auto_position

        self.set_scale_props(scale=scale, **(scale_props if scale_props else {}))
        # set the label properties
        self.set_label_props(**(label_props if label_props else {}))
        # set the patch properties
        self.set_patch_props(**(patch_props if patch_props else {}))

        # number of intermediate points for evaluating the curvature
        self._interm_pts = 20

        self._cb_offset_interval = 0.05
        self._cb_rotate_inverval = 1

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

        self._artists = OrderedDict(patch=None, scale=None)
        self._picker_name = None

    def _get_preset_props(self, preset):
        scale_props = dict(n=10, width=5, colors=("k", "w"))
        patch_props = dict(fc=".75", ec="k", lw=1, ls="-")
        label_props = dict(scale=2, offset=1, every=2, rotation=0, color="k")

        if preset == "bw":
            scale_props.update(dict(n=10, width=4, colors=("k", "w")))
            patch_props.update(dict(fc="none", ec="none"))
            label_props.update(
                dict(
                    scale=1.5,
                    offset=0.5,
                    every=2,
                    weight="bold",
                    family="Courier New",
                )
            )
        return scale_props, patch_props, label_props

    def _apply_preset(self, preset):
        self.preset = preset

        scale_props, patch_props, label_props = self._get_preset_props(preset)
        self.set_scale_props(**scale_props)
        self.set_patch_props(**patch_props)
        self.set_label_props(**label_props)

    def apply_preset(self, preset):
        """
        Apply a style-preset to the Scalebar.

        Parameters
        ----------
        preset : str
            The name of the preset.

        """
        self._apply_preset(preset)
        self._estimate_scale()
        self.set_position()

    @staticmethod
    def _round_to_n(x, n=0):
        # round to n significant digits
        # 1234 -> 1000
        # 0.01234 -> 0.1
        res = round(x, n - int(np.floor(np.log10(abs(x)))))
        if res.is_integer():
            return int(res)
        else:
            return res

    def _estimate_scale(self):
        try:
            ax2data = self._m.ax.transAxes + self._m.ax.transData.inverted()
            ang = np.deg2rad(self._azim)

            x0, y0 = ax2data.inverted().transform((self._lon, self._lat))

            aspect = self._m.ax.bbox.height / self._m.ax.bbox.width
            d = self._autoscale * aspect

            dx = abs(d * np.cos(ang))
            dy = abs(d * np.sin(ang))

            p0 = ax2data.transform((x0, y0))
            p1 = ax2data.transform((x0 + dx, y0 + dy))

            l0 = self._m._transf_plot_to_lonlat.transform(*p0)
            l1 = self._m._transf_plot_to_lonlat.transform(*p1)

            geod = self._m.ax.projection.get_geod()

            faz, baz, dist = geod.inv(*l0, *l1)

            scale = dist / self._scale_props["n"]
            # round to 1 significant digit
            scale = self._round_to_n(scale)

            self._scale_props["scale"] = scale
            return scale

        except Exception:
            raise AssertionError(
                "EOmaps: Unable to determine a suitable 'scale' for the scalebar...\n"
                + "Please provide the scale explicitly via `m.add_scalebar(scale=10000)`"
            )

    def _get_autopos(self, pos):
        # try to position the colorbar at the lower right corner of the axis
        x0, y0 = (self._m.ax.transAxes + self._m.ax.transData.inverted()).transform(pos)
        lon, lat = self._m._transf_plot_to_lonlat.transform(x0, y0)

        if not all(np.isfinite([x0, y0])):
            # if it fails, try to position it at the center of the extent
            extent = self._m.ax.get_extent()
            lon, lat = self._m._transf_plot_to_lonlat.transform(
                np.mean(extent[:2]),
                np.mean(extent[2:]),
            )
        return lon, lat

    def auto_position(self, pos):
        """Move the scalebar to the desired position and apply auto-scaling."""
        lon, lat = self._get_autopos(pos)
        self.set_position(lon, lat, self._azim)

    @property
    def cb_rotate_interval(self):
        """Get/set the rotation interval when rotating the scalebar with +/- keys."""
        return self._cb_rotate_inverval

    @cb_rotate_interval.setter
    def cb_rotate_interval(self, val):
        self._cb_rotate_inverval = val

    @property
    def cb_offset_interval(self):
        """
        Get/set the interval for changing the text-offset with keyboard-shortcuts.

        e.g.: when using the <alt> + <+>/<-> keyboard-shortcut to set the offset for
        the scalebar-labels.
        """
        return self._cb_offset_interval

    @cb_offset_interval.setter
    def cb_offset_interval(self, val):
        self._cb_offset_interval = val

    def set_scale_props(self, scale=None, n=None, width=None, colors=None):
        """
        Set the properties of the scalebar (and update the plot accordingly).

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
            self._m.BM.update(artists=self._artists.values())

    def set_patch_props(self, offsets=None, **kwargs):
        """
        Set the properties of the frame (and update the plot accordingly).

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
            if key in self._patch_props:
                self._patch_props[key] = kwargs.pop(
                    key, kwargs.pop(synonym, self._patch_props[key])
                )

        self._patch_props.update(kwargs)

        if hasattr(self, "_lon") and hasattr(self, "_lat"):
            self.set_position()
            self._m.BM.update(artists=self._artists.values())

    def set_label_props(
        self, scale=None, rotation=None, every=None, offset=None, color=None, **kwargs
    ):
        """
        Set the properties of the labels (and update the plot accordingly).

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
            self._m.BM.update(artists=self._artists.values())

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
        units = {" mm": 0.001, " m": 1, " km": 1000, "k km": 1000000}
        for key, val in units.items():
            x = scale * n / val
            if scale * n / val < 1000:
                return np.format_float_positional(x, trim="-", precision=3) + key

        return f"{scale} m"

    def _txt(self):
        return self._get_txt(self._scale_props["n"])

    def _get_d(self):
        # the base length used to define the size of the scalebar

        # get the position in figure coordinates
        x, y = self._m.ax.transData.transform(
            self._t_plot.transform(self._lon, self._lat)
        )

        d_fig = max(self._m.ax.bbox.height, self._m.ax.bbox.width) / 100
        # translate d_fig to data-coordinates
        xb, yb = self._m.ax.transData.inverted().transform(
            ([x, y + d_fig], [x, y - d_fig])
        )
        return np.abs(xb[1] - yb[1])

    def _get_patch_verts(self, pts, lon, lat, ang, d):
        # top bottom left right referrs to a horizontally oriented colorbar!
        ot = d * self._patch_offsets[0]
        ob = self._maxw + d * (self._label_props["offset"] + self._patch_offsets[1])
        o_l = d * self._patch_offsets[2]
        o_r = d * self._patch_offsets[3]

        # in case the top scale has a label, add a margin to encompass the text!
        if len(pts) % self._label_props["every"] == 0:
            o_r += self._top_h * 1.5

        dxy = np.gradient(pts.reshape((-1, 2)), axis=0)
        alpha = np.arctan2(dxy[:, 1], -dxy[:, 0])
        t = np.column_stack([np.sin(alpha), np.cos(alpha)])

        ptop = pts.reshape((-1, 2)) - ot * t
        pbottom = pts.reshape((-1, 2)) + ob * t

        ptop[0] += (o_l * np.cos(alpha[0]), -o_l * np.sin(alpha[0]))
        pbottom[0] += (o_l * np.cos(alpha[0]), -o_l * np.sin(alpha[0]))

        ptop[-1] -= (o_r * np.cos(alpha[-1]), -o_r * np.sin(alpha[-1]))
        pbottom[-1] -= (o_r * np.cos(alpha[-1]), -o_r * np.sin(alpha[-1]))

        # TODO check how to deal with invalid vertices (e.g. self-intersections)

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
        xt = xt - d * self._label_props["offset"] * np.sin(ang)
        yt = yt + d * self._label_props["offset"] * np.cos(ang)
        return xt, yt

    from functools import lru_cache

    # cache this to avoid re-evaluating the text-size when dragging the scalebar
    @lru_cache(1)
    def _get_maxw(self, sscale, sn, lscale, lrotation, levery):
        # arguments are only used for caching!

        # update here to make sure axis-transformations etc. are properly set
        self._m.BM.update(blit=False)

        # the max. width of the texts
        _maxw = 0
        for key, val in self._artists.items():
            if not key.startswith("text_"):
                continue

            # use try-except here since the renderer can only estimate the size
            # if the object is within the canvas!
            try:
                # get the widths of the text patches in data-coordinates
                bbox = val.get_window_extent(self._m.f.canvas.get_renderer())
                bbox = bbox.transformed(self._m.ax.transData.inverted())
                # use the max to account for rotated text objects
                w = max(bbox.width, bbox.height)
                if w > _maxw:
                    _maxw = w
            except Exception:
                pass

        _top_h = 0
        try:
            _top_label = next(i for i in sorted(self._artists) if i.startswith("text_"))
            val = self._artists[_top_label]
            bbox = val.get_window_extent(self._m.f.canvas.get_renderer())
            bbox = bbox.transformed(self._m.ax.transData.inverted())
            _top_h = min(bbox.width, bbox.height)
        except Exception:
            pass

        self._maxw = _maxw
        self._top_h = _top_h

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

            xy = self._get_txt_coords(lon, lat, d, ang)
            tp = TextPath(
                xy, txt, size=self._label_props["scale"] * d / 2, prop=self._font_props
            )

            self._artists[f"text_{i}"] = self._m.ax.add_artist(
                PathPatch(tp, color=self._label_props["color"], lw=0)
            )
            self._artists[f"text_{i}"].set_transform(
                Affine2D().rotate_around(
                    *xy, ang + np.pi / 2 + np.deg2rad(self._label_props["rotation"])
                )
                + self._m.ax.transData
            )

            self._artists[f"text_{i}"].set_zorder(1)
            self._m.BM.add_artist(self._artists[f"text_{i}"], layer=self.layer)

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

            xy = self._get_txt_coords(lon, lat, d, ang)

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
                + self._m.ax.transData
            )
        self._get_maxw(
            self._scale_props["scale"],
            self._scale_props["n"],
            self._label_props["scale"],
            self._label_props["rotation"],
            self._label_props["every"],
        )

    def _add_scalebar(self, lon, lat, azim):

        assert (
            self._artists["scale"] is None
        ), "EOmaps: there is already a scalebar present!"

        # do this to make sure that the ax-transformations work as expected
        self._m.BM.update(blit=False)

        self._lon = lon
        self._lat = lat
        self._azim = azim

        if self._scale_props["scale"] is None:
            self._estimate_scale()

        pts = self._get_pts(lon, lat, azim)
        d = self._get_d()
        ang = self._get_ang(pts[0][0], pts[0][1])

        # -------------- add the labels
        self._set_minitxt(d, pts)

        # -------------- add the patch
        self._get_maxw(
            self._scale_props["scale"],
            self._scale_props["n"],
            self._label_props["scale"],
            self._label_props["rotation"],
            self._label_props["every"],
        )

        verts = self._get_patch_verts(pts, lon, lat, ang, d)
        p = PolyCollection([verts], **self._patch_props)
        self._artists["patch"] = self._m.ax.add_artist(p)

        # -------------- add the scalebar
        coll = LineCollection(pts)
        colors = np.tile(
            self._scale_props["colors"],
            int(np.ceil(len(pts) / len(self._scale_props["colors"]))),
        )[: len(pts)]
        coll.set_colors(colors)
        coll.set_linewidth(self._scale_props["width"])
        self._artists["scale"] = self._m.ax.add_collection(coll, autolim=False)

        # -------------- make all artists animated
        self._artists["scale"].set_zorder(1)
        self._artists["patch"].set_zorder(0)

        self._m.BM.add_artist(self._artists["scale"], layer=self.layer)
        # self._m.BM.add_artist(self._artists["text"])
        self._m.BM.add_artist(self._artists["patch"], layer=self.layer)

        self._m.BM.update(artists=self._artists.values())
        # make sure to update the artists on zoom
        self._decorate_zooms()

    def set_position(self, lon=None, lat=None, azim=None, update=False):
        """
        Set the position of the colorbar.

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
            Indicator if the plot should be immediately updated (True) or at the next
            event (False). The default is False.

        """
        if lon is None:
            lon = self._lon
        if lat is None:
            lat = self._lat
        if azim is None:
            azim = self._azim

        self._lon = lon
        self._lat = lat
        self._azim = azim
        pts = self._get_pts(lon, lat, azim)
        d = self._get_d()
        ang = self._get_ang(pts[0][0], pts[0][1])

        # do this after setting _lon, _lat and _azim !
        # and BEFORE all other changes since we need the size of the text-patches!
        self._update_minitxt(d, pts)

        # don't use first and last scale (they are just used as placeholders)
        self._artists["scale"].set_verts(pts)
        colors = np.tile(
            self._scale_props["colors"],
            int(np.ceil(len(pts) / len(self._scale_props["colors"]))),
        )[: len(pts)]
        self._artists["scale"].set_colors(colors)

        verts = self._get_patch_verts(pts, lon, lat, ang, d)

        # TODO check how to deal with invalid vertices!!
        # print(np.all(np.isfinite(self._m._transf_plot_to_lonlat.transform(*verts.T))))

        # verts = np.ma.masked_invalid(verts)

        self._artists["patch"].set_verts([verts])
        self._artists["patch"].update(self._patch_props)

        if self._picker_name:
            if self._m.cb.pick[self._picker_name].is_picked:
                self._artists["patch"].set_edgecolor("r")
                self._artists["patch"].set_linewidth(2)
                self._artists["patch"].set_linestyle("-")

        if update:
            self._m.BM.update()

    def _make_pickable(self):
        """
        Add callbacks to adjust the scalebar position manually.

            - <LEFT>-click on the scalebar with the mouse to pick it up
                - hold down <LEFT> to drag the scalebar
            - use "+" and "-" keys to rotate the colorbar
            - <RIGHT>-click on the scalebar to detach the callbacks again
              (e.g. make it non-interactive)
            - use <ARROW-keys> to set the size of the patch

        """

        def scb_move(s, pos, **kwargs):
            # scb_remove(self, s)
            # s._artists["patch"].set_pickradius(150)
            # if not s._artists["patch"].contains(self.cb.click._event)[0]:
            #     return
            lon, lat = s._t_lonlat.transform(*pos)
            # don't update here... the click callback updates itself!
            s.set_position(lon, lat, update=False)

        def scb_remove(s, **kwargs):
            if not s._m.cb.pick[s._picker_name].is_picked:
                return
            s.remove()

        def scb_az_ud(s, up=True, **kwargs):
            if not s._m.cb.pick[s._picker_name].is_picked:
                return
            s._azim += s.cb_rotate_interval if up else -s.cb_rotate_interval
            s.set_position(update=True)

        # ------------ callbacks to change frame with arrow-keys
        def scb_patch_dim(s, udlr, add=True, **kwargs):
            if not s._m.cb.pick[s._picker_name].is_picked:
                return
            o = [*s._patch_offsets]
            o[udlr] += 0.1 if add else -0.1
            s.set_patch_props(offsets=o)

        # ------------ callbacks to change the text offset with alt +-
        def scb_txt_offset(s, add=True, **kwargs):
            if not s._m.cb.pick[s._picker_name].is_picked:
                return

            o = s._label_props["offset"]
            o += s._cb_offset_interval if add else -s._cb_offset_interval
            s.set_label_props(offset=o)

        def addcbs(s, **kwargs):
            m = s._m
            # make sure we pick always only one scalebar
            for i in s._existing_pickers:
                p = getattr(m.cb, i)
                if p.is_picked is True and p.scalebar is not s:
                    p.scalebar._remove_callbacks()

            m.cb.pick[s._picker_name].is_picked = True

            if not hasattr(s, "_cid_move"):
                s._cid_move = m.cb.click.attach(scb_move, s=s)

            if not hasattr(s, "_cid_up"):
                s._cid_up = m.cb.keypress.attach(scb_az_ud, key="+", up=True, s=s)
            if not hasattr(s, "_cid_down"):
                s._cid_down = m.cb.keypress.attach(scb_az_ud, key="-", up=False, s=s)

            if not hasattr(s, "_cid_txt_offset_up"):
                s._cid_txt_offset_up = m.cb.keypress.attach(
                    scb_txt_offset, key="alt++", add=True, s=s
                )
            if not hasattr(s, "_cid_txt_offset_down"):
                s._cid_txt_offset_down = m.cb.keypress.attach(
                    scb_txt_offset, key="alt+-", add=False, s=s
                )

            for key, udlr in zip(["up", "down", "left", "right"], range(4)):
                if not hasattr(s, f"_cid_patch_dim_{key}_0"):
                    setattr(
                        s,
                        f"_cid_patch_dim_{key}_0",
                        m.cb.keypress.attach(
                            scb_patch_dim, key=key, udlr=udlr, add=True, s=s
                        ),
                    )
                if not hasattr(s, f"_cid_patch_dim_{key}_1"):
                    setattr(
                        s,
                        f"_cid_patch_dim_{key}_1",
                        m.cb.keypress.attach(
                            scb_patch_dim, key="alt+" + key, udlr=udlr, add=False, s=s
                        ),
                    )

            if not hasattr(s, "_cid_remove"):
                s._cid_remove = m.cb.keypress.attach(scb_remove, key="delete", s=s)

        def scb_unpick(s, **kwargs):
            s._remove_callbacks()

        self._picker_name = f"_scalebar{len(self._existing_pickers)}"

        self._m.cb.add_picker(self._picker_name, self._artists["patch"], True)
        self._cid_pick = self._m.cb.pick[self._picker_name].attach(addcbs, s=self)
        # remove all callbacks (except the pick-callback) on right-click
        self._cid_remove_cbs = self._m.cb.click.attach(
            scb_unpick, s=self, button=1, double_click="release"
        )

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

        self.set_position()

    def _decorate_zooms(self):
        toolbar = self._m.f.canvas.toolbar

        if toolbar is not None:
            toolbar.release_zoom = self._zoom_decorator(toolbar.release_zoom)
            toolbar.release_pan = self._zoom_decorator(toolbar.release_pan)
            toolbar._update_view = self._update_decorator(toolbar._update_view)

    def _zoom_decorator(self, f):
        def newzoom(event):
            ret = f(event)

            # clear the cache to re-evaluate the text-width
            self.__class__._get_maxw.cache_clear()
            if self._autoscale is not None:
                prev_scale = self._scale_props["scale"]
                try:
                    self._estimate_scale()
                except Exception:
                    self._scale_props["scale"] = prev_scale
            if self._auto_position:
                self.auto_position(self._auto_position)

            self.set_position()
            self._m.BM.update()
            return ret

        return newzoom

    def _update_decorator(self, f):
        def newupdate():
            # clear the cache to re-evaluate the text-width
            ret = f()
            self.__class__._get_maxw.cache_clear()
            if self._autoscale is not None:
                prev_scale = self._scale_props["scale"]
                try:
                    self._estimate_scale()
                except Exception:
                    self._scale_props["scale"] = prev_scale

            if self._auto_position:
                self.auto_position(self._auto_position)

            self.set_position()
            self._m.BM.update()

            return ret

        return newupdate

    def get_position(self):
        """
        Return the current position (and orientation) of the scalebar.

        Returns
        -------
        list
            a list corresponding to [longitude, latitude, azimuth].
        """
        return [self._lon, self._lat, self._azim]

    def remove(self):
        """Remove the scalebar from the map."""
        self._remove_callbacks()
        for a in self._artists.values():
            self._m.BM.remove_artist(a)
            a.remove()

        self._m.BM.update()


class Compass:
    """Base class for EOmaps compass objects."""

    def __init__(self, m):
        self._m = m

        self._scale = 10
        self._style = "north arrow"
        self._patch = False
        self._txt = "N"

    def __call__(
        self,
        pos=None,
        pos_transform="axes",
        scale=10,
        style="compass",
        patch=None,
        txt="N",
        pickable=True,
        layer=None,
        ignore_invalid_angles=False,
    ):
        """
        Add a "compass" or "north-arrow" to the map.

        Note
        ----
        You can use the mouse to pick the compass and move it anywhere on the map.
        (the directions are dynamically updated if you pan/zoom or pick the compass)

        - If you press the "delete" key while clicking on the compass, it is removed.
          (same as calling `compass.remove()`)
        - If you press the "d" key while clicking on the compass, it will be
          disconnected from pick-events (same as calling `compass.set_pickable(False)`)


        Parameters
        ----------
        pos : tuple or None, optional
            The initial position of the compass with respect to the transformation
            defined as "pos_transform".
            Note that you can also move the compass with the mouse!
        pos_transform : string, optional
            Indicator in what coordinate-system the initial position is provided.

            - "axes": relative axis-coordinates in the range (0-1)
            - "lonlat": coordinates provided as (longitude, latitude)
            - "plot_crs": coordinates provided in the crs used for plotting.

            The default is "axes".
        scale : float, optional
            A scale-factor for the size of the compass. The default is 10.
        style : str, optional

            - "north arrow" : draw only a north-arrow
            - "compass": draw a compass with arrows in all 4 directions

            The default is "compass".
        patch : False, str or tuple, optional
            The color of the background-patch.
            (can be any color specification supported by matplotlib)
            The default is "w".
        txt : str, optional
            Indicator which directions should be indicated.
            - "NESW" : add letters for all 4 directions
            - "NE" : add only letters for North and East (same for other combinations)
            - None : don't add any letters
            The default is "N".
        pickable : bool, optional
            Indicator if the compass should be static (False) or if it can be dragged
            with the mouse (True). The default is True
        layer : str, optional
            The layer to put the compass on. The default is "all".
        ignore_invalid_angles : bool, optional
            - If True the compass will always (silently) use the last valid rotation-angle
              in case the correct angle could not be determined.
            - If False, a warning will be issued in case the angle could
              not be determined, and a red border will be drawn around the compass to
              indicate that it might not point in the right direction.

            The default is False

        Returns
        -------
        compass : eomaps.Compass
            A compass-object that can be used to manually adjust the style and position
            of the compass or remove it from the map.

        """
        if layer is None:
            layer = self._m.layer
        self.layer = layer

        self._ignore_invalid_angles = ignore_invalid_angles
        # self._m.BM.update()

        ax2data = self._m.ax.transAxes + self._m.ax.transData.inverted()

        if pos is None:
            pos = ax2data.transform((0.5, 0.5))
        else:
            if pos_transform == "axes":
                pos = ax2data.transform(pos)
            elif pos_transform == "lonlat":
                pos = self._m._transf_lonlat_to_plot.transform(*pos)
            elif pos_transform == "plot_crs":
                pass
            else:
                raise TypeError(
                    f"EOmaps: {pos_transform} is not a valid 'pos_transform'."
                    "Use one of ('axes', 'lonlat', 'plot_crs')"
                )

        self._style = style
        self._patch = patch
        self._txt = txt
        self._scale = scale
        # remember the dpi at the time the compass was initialized
        self._init_dpi = self._m.f.dpi

        self._ang = 0
        # remember last used rotation angle for out-of-axes compass
        self._last_ang = 999

        self._artist = self._get_artist(pos)
        self._m.ax.add_artist(self._artist)
        self._m.BM.add_artist(self._artist, layer=self.layer)

        self._set_position(pos)

        if pickable:
            if not self._artist.pickable():
                self._artist.set_picker(True)

        self._got_artist = True
        self._canvas = self._artist.figure.canvas
        self._cids = [
            self._canvas.mpl_connect("pick_event", self._on_pick),
            self._canvas.mpl_connect("button_release_event", self._on_release),
            self._canvas.mpl_connect("scroll_event", self._on_scroll),
        ]

        if self._update_offset not in self._m.BM._before_fetch_bg_actions:
            self._m.BM._before_fetch_bg_actions.append(self._update_offset)

    def _get_artist(self, pos):
        if self._style == "north arrow":
            bg_patch = PolyCollection(
                [[[-1.5, -0.5], [-1.5, 5], [1.5, 5], [1.5, -0.5]]],
                facecolors=[self._patch] if self._patch else ["none"],
                edgecolors=["k"] if self._patch else ["none"],
            )

            verts = [
                [[1, 0], [0, 3], [0, 0.5]],  # N w
                [[-1, 0], [0, 3], [0, 0.5]],  # N b
            ]
            arrow = PolyCollection(
                verts,
                facecolors=["w", "k"],
                edgecolors=["k"],
            )
        elif self._style == "compass":
            c = CirclePolygon((0, 0)).get_path().vertices

            bg_patch = PolyCollection(
                [[[-3.5, -3.5], [-3.5, 5], [3.5, 5], [3.5, -3.5]]],
                facecolors=[self._patch] if self._patch else ["none"],
                edgecolors=["k"] if self._patch else ["none"],
            )

            verts = [
                [[-1, 0], [0, 3], [0, 1]],  # N b
                [[0, 1], [3, 0], [1, 0]],  # E b
                [[0, -3], [0, -1], [1, 0]],  # S b
                [[-3, 0], [-1, 0], [0, -1]],  # W b
                [[-3, 0], [0, 1], [-1, 0]],  # W w
                [[0, 1], [0, 3], [1, 0]],  # N w
                [[3, 0], [0, -1], [1, 0]],  # E w
                [[0, -3], [-1, 0], [0, -1]],  # S w
                c / 4,
                c / 8,
            ]

            arrow = PolyCollection(
                verts,
                facecolors=["k"] * 4 + ["w"] * 4 + [".5", "w"],
                edgecolors=["k"],
            )
        else:
            raise AssertionError("EOmaps: {style} is not a valid compass-style.")

        art = AuxTransformBox(self._get_transform(pos))
        art.add_artist(bg_patch)
        art.add_artist(arrow)

        for t in self._txt:
            if t == "N":
                txt = PathPatch(TextPath((-0.75, 3.2), "N", size=2), fc="k", ec="none")
                art.add_artist(txt)
            elif self._style == "compass":
                if t == "E":
                    txt = PathPatch(
                        TextPath((3.3, -0.75), "E", size=2), fc="k", ec="none"
                    )
                    art.add_artist(txt)
                elif t == "S":
                    txt = PathPatch(
                        TextPath((-0.75, -4.7), "S", size=2), fc="k", ec="none"
                    )
                    art.add_artist(txt)
                elif t == "W":
                    txt = PathPatch(
                        TextPath((-5.2, -0.75), "W", size=2), fc="k", ec="none"
                    )
                    art.add_artist(txt)

        return art

    def _update_offset(self, x=None, y=None, *args, **kwargs):
        # reset to the center of the axis if both are None
        try:
            if x is None or y is None:
                try:
                    self._set_position(self._pos)
                    return
                except Exception:
                    x, y = 0.9, 0.1
                    self._set_position((x, y), "axis")
                    return

            self._set_position((x, y), "data")
        except Exception:
            pass

    def _get_transform(self, pos):

        lon, lat = self._m._transf_plot_to_lonlat.transform(*pos)
        x, y = self._m._transf_lonlat_to_plot.transform([lon, lon], [lat, lat + 0.01])

        try:
            ang = -np.arctan2(x[1] - x[0], y[1] - y[0])
        except Exception:
            print("EOmaps: could not add scalebar at the desired location")
            return

        if np.isnan(ang):
            if not self._ignore_invalid_angles:
                if self._last_ang != self._ang:
                    print(
                        "EOmaps: Compass rotation-angle could not be determined! "
                        f"... using last found angle: {np.rad2deg(self._ang):.2f}"
                    )
                    patch = self._artist.get_children()[0]
                    self._patch_ec = patch.get_edgecolor()
                    patch.set_edgecolor("r")

                self._last_ang = self._ang
            else:
                if hasattr(self, "_patch_ec"):
                    self._artist.get_children()[0].set_edgecolor(self._patch_ec)
                    del self._patch_ec
                self._last_ang = 9999

            ang = self._ang
        else:
            if hasattr(self, "_patch_ec"):
                self._artist.get_children()[0].set_edgecolor(self._patch_ec)
                del self._patch_ec

            self._last_ang = 9999

        self._ang = ang
        r = transforms.Affine2D().rotate(ang)
        # apply the scale-factor with respect to the current figure dpi to keep the
        # relative size of the north-arrow on dpi-changes!
        s = transforms.Affine2D().scale(self._scale * self._m.f.dpi / self._init_dpi)
        t = transforms.Affine2D().translate(*self._m.ax.transData.transform(pos))
        trans = r + s + t
        return trans

    def _on_motion(self, evt):
        if not self._layer_visible:
            return

        if self._check_still_parented() and self._got_artist:
            x, y = evt.xdata, evt.ydata

            # transform values if axes is put outside the figure
            if evt.inaxes is None:
                x, y = self._m.ax.transData.inverted().transform((evt.x, evt.y))
            elif evt.inaxes != self._m.ax:
                # don't allow moving the compass on top of another axes
                # (somehow pick-events do not fire if compass is in another axes)
                # TODO check this!
                return

            # continue values outside of the crs-domain
            if x is None or y is None:
                x, y = self._m.ax.transData.inverted().transform((evt.x, evt.y))

            self._update_offset(x, y)
            self._m.BM.update(artists=[self._artist])

    def _on_scroll(self, event):
        if not self._layer_visible:
            return

        if self._check_still_parented() and self._got_artist:
            self.set_scale(max(1, self._scale + event.step))

    def _on_pick(self, evt):
        if not self._layer_visible:
            return

        if evt.mouseevent.button != 1:
            return

        if self._check_still_parented() and evt.artist == self._artist:
            self._got_artist = True
            self._c1 = self._canvas.mpl_connect("motion_notify_event", self._on_motion)
            self._c2 = self._canvas.mpl_connect("key_press_event", self._on_keypress)

    def _on_keypress(self, event):
        if not self._layer_visible:
            return

        if event.key == "delete":
            self.remove()
        if event.key == "d":
            self._on_release(None)
            self.set_pickable(False)

    def _on_release(self, event):
        if not self._layer_visible:
            return

        if self._check_still_parented() and self._got_artist:
            self._finalize_offset()
            self._got_artist = False
            try:
                c1 = self._c1
            except AttributeError:
                pass
            else:
                self._canvas.mpl_disconnect(c1)

            try:
                c2 = self._c2
            except AttributeError:
                pass
            else:
                self._canvas.mpl_disconnect(c2)
            self._m.BM.update()

    def _check_still_parented(self):
        if self._artist.figure is None:
            self._disconnect()
            return False
        else:
            return True

    @property
    def _layer_visible(self):
        return self.layer == "all" or (
            self.layer in (*self._m.BM.bg_layer.split("|"), self._m.BM.bg_layer)
        )

    def _disconnect(self):
        """Disconnect the callbacks."""
        for cid in self._cids:
            self._canvas.mpl_disconnect(cid)

        if self._update_offset in self._m.BM._before_fetch_bg_actions:
            self._m.BM._before_fetch_bg_actions.append(self._update_offset)

        try:
            c1 = self._c1
        except AttributeError:
            pass
        else:
            self._canvas.mpl_disconnect(c1)

        try:
            c2 = self._c2
        except AttributeError:
            pass
        else:
            self._canvas.mpl_disconnect(c2)

    def _finalize_offset(self):
        pass

    def remove(self):
        """
        Remove the compass from the map.

        Note
        ----
        You can also remove a compass by clicking on it and pressing the "delete"
        button on the keyboard (while holding down the mouse-button)

        """
        self._disconnect()
        self._m.BM.remove_artist(self._artist)
        self._artist.remove()
        self._m.BM.update()

    def set_patch(self, facecolor=None, edgecolor=None, linewidth=None):
        """
        Set the style of the background patch.

        Parameters
        ----------
        facecolor, edgecolor : str, tuple, None or False
            - str or tuple: Set the color of the background patch.
            - False or "none": Make the background-patch invisible.
        linewidth: float
            The linewidth of the patch.

        """
        if facecolor is False:
            facecolor = "none"
        if edgecolor is False:
            edgecolor = "none"

        if facecolor is not None:
            self._artist.get_children()[0].set_facecolor(facecolor)
        if edgecolor is not None:
            self._artist.get_children()[0].set_edgecolor(edgecolor)
        if linewidth is not None:
            assert isinstance(
                linewidth, (int, float, np.number)
            ), "EOmaps: linewidth must be int or float!"
            self._artist.get_children()[0].set_linewidth(linewidth)

    def set_scale(self, scale):
        """
        Set the size scale-factor of the compass. (The default is 10).

        Parameters
        ----------
        s : float
            The size of the compass.

        """
        self._scale = scale
        self._update_offset(*self._pos)

    def set_pickable(self, b):
        """
        Set if the compass can be picked with the mouse or not.

        Parameters
        ----------
        b : bool
            True : enable picking
            False : disable picking
        """
        if b is False:
            b = None
        self._artist.set_picker(b)

    def _set_position(self, pos, coords="data"):
        # Avoid calling BM.update() in here! It results in infinite
        # recursions on zoom events because the position of the scalebar is
        # dynamically updated on each re-fetch of the background!

        if coords == "axis":
            self._ax2data = self._m.ax.transAxes + self._m.ax.transData.inverted()
            pos = self._ax2data.transform(pos)

        trans = self._get_transform(pos)
        for c in self._artist.get_children():
            c.set_transform(trans)
        self._pos = pos

    def set_position(self, pos, coords="data"):
        """
        Set the position of the compass.

        Parameters
        ----------
        pos : tuple
            The (x, y) coordinates.
        coords : str, optional
            Indicator how the coordinates are provided

            - "data" : pos represents coordinates in the plot-crs
            - "axis" : pos represents relative [0-1] coordinates with respect to the
              axis (e.g. (0, 0) = lower left corner, (1, 1) = upper right corner).

            The default is "data".
        """
        self._set_position(pos, coords="data")
        self._m.BM.update(artists=[self._artist])

    def get_position(self, coords="data"):
        """
        Return the current position of the compass.

        Parameters
        ----------
        coords : str, optional
            Define what coordinates are returned

            - "data" : coordinates in the plot-crs
            - "axis": relative [0-1] coordinates with respect to the
              axis (e.g. (0, 0) = lower left corner, (1, 1) = upper right corner)

            The default is "data".

        Returns
        -------
        pos
            a tuple (x, y) representing the current location of the compass.

        """
        self._ax2data = self._m.ax.transAxes + self._m.ax.transData.inverted()

        if coords == "axis":
            return self._ax2data.inverted().transform(self._pos)
        elif coords == "data":
            return self._pos
        else:
            raise TypeError("EOmaps: 'coords' must be one of ['data', 'axis']!")

    def get_scale(self):
        """
        Return the current size scale-factor of the compass.

        Returns
        -------
        s : float
            The size of the compass.

        """
        return self._scale

    def set_ignore_invalid_angles(self, val):
        """
        Set how to deal with invalid rotation-angles.

        - If True the compass will always (silently) use the last valid rotation-angle
          in case the correct angle could not be determined.
        - If False (the default), a warning will be issued in case the angle could
          not be determined, and a red border will be drawn around the compass to
          indicate that it might not point in the right direction.

        Parameters
        ----------
        val : bool
            ignore invalid rotation angles.
        """
        self._ignore_invalid_angles = val
        self.set_position(self._pos)

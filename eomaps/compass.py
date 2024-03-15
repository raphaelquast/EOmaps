# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Interactive Compass (or North Arrow)."""

import logging

import numpy as np

from matplotlib.collections import PolyCollection
from matplotlib.textpath import TextPath
from matplotlib.patches import PathPatch, CirclePolygon
from matplotlib.offsetbox import AuxTransformBox
import matplotlib.transforms as transforms

_log = logging.getLogger(__name__)


class Compass:
    """
    Base class for EOmaps compass (or North-arrow) objects.

    Note
    ----
    To add a new compass (or north-arrow) to a map, see
    :py:meth:`Maps.add_compass <eomaps.eomaps.Maps.add_compass>`.

    """

    def __init__(self, m):
        self._m = m

        self._scale = 10
        self._style = "north arrow"
        self._patch = False
        self._txt = "N"

        self._last_patch_ec = None
        self._last_patch_lw = None

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
            A scale-factor for the size of the compass in relation to the size of the
            whole figure. The default is 10.
        style : str, optional

            - "north arrow" : draw only a north-arrow
            - "compass": draw a compass with arrows in all 4 directions

            The default is "compass".
        patch : False, str or tuple, optional
            The color of the background-patch (can be any color specification supported
            by matplotlib). See `Compass.set_patch(...)` for more styling options.
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

        self._m.BM.update()

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
            _log.error("EOmaps: Unable to add a compass at the desired location.")
            return

        if np.isnan(ang):
            if not self._ignore_invalid_angles:
                if self._last_ang != self._ang:
                    _log.error(
                        "EOmaps: Compass rotation-angle could not be determined! "
                        f"... using angle: {np.rad2deg(self._ang):.2f}"
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
        s = transforms.Affine2D().scale(
            self._scale
        )  # * self._m.f.dpi / self._init_dpi)
        t = transforms.Affine2D().translate(*self._m.ax.transData.transform(pos))
        trans = r + s + t

        # cycle position once through transFigure to ensure correct positioning
        # of the compass for agg exports (png, jpeg.. pixel-based) and
        # svg/pdf based exports (point-based)
        trans = trans + self._m.f.transFigure.inverted() + self._m.f.transFigure
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

            self._m.BM.update(artists=[self._artist])

    def _on_pick(self, evt):
        if not self._layer_visible:
            return

        if evt.mouseevent.button != 1:
            return

        if self._check_still_parented() and evt.artist == self._artist:
            self._got_artist = True
            self._c1 = self._canvas.mpl_connect("motion_notify_event", self._on_motion)
            self._c2 = self._canvas.mpl_connect("key_press_event", self._on_keypress)

            # make red 1pt edgecolor while compass is picked
            self._last_patch_ec = self._artist.get_children()[0].get_edgecolor()
            self._last_patch_lw = self._artist.get_children()[0].get_linewidth()[0]

            self.set_patch(edgecolor="r", linewidth=1)

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

            self.set_patch(
                edgecolor=self._last_patch_ec,
                linewidth=self._last_patch_lw,
            )

            self._m.BM.update()

    def _check_still_parented(self):
        if self._artist.figure is None:
            self._disconnect()
            return False
        else:
            return True

    @property
    def _layer_visible(self):
        return self._m.BM._layer_visible(self.layer)

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

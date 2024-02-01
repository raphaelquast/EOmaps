# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Definition of the LayoutEditor used to interactively re-position axes."""

import logging
from contextlib import ExitStack
from pathlib import Path
import json

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox
from matplotlib.axis import XAxis, YAxis
from matplotlib.spines import Spine

_log = logging.getLogger(__name__)


class LayoutEditor:
    """Class to handle interactive re-positioning of figure-objects."""

    def __init__(self, m, modifier="alt+d", cb_modifier="control"):
        self.modifier = modifier
        self.cb_modifier = cb_modifier

        self.m = m
        self.f = self.m.parent.f

        self._ax_picked = []
        self._m_picked = []

        self._modifier_pressed = False

        self.cids = []

        # indicator if the pick-callback should be re-attached or not
        self._reattach_pick_cb = False

        self.f.canvas.mpl_connect("key_press_event", self.cb_key_press)
        self.f.canvas.mpl_connect("resize_event", self._on_resize)

        # the snap-to-grid interval (0 means no snapping)
        self._snap_id = 5

        # an optional filepath that will be used to store the layout once the
        # editor exits
        self._filepath = None

        # indicator if scaling should be in horizontal or vertical direction
        self._scale_direction = "both"

        # indicator if multiple-axis select key is pressed or not (e.g. "shift")
        self._shift_pressed = False

        self._max_hist_steps = 1000
        self._history = list()
        self._history_undone = list()

        self._current_bg = None

        self._info_text = None
        self._info_text_hidden = False

    def add_info_text(self):
        self._info_text_hidden = False

        a = self.m.f.text(
            0.72,
            0.98,
            (
                "LayoutEditor Controls:\n\n"
                "0 - 9:  Snap-grid spacing\n"
                "SHIFT:  Multi-select\n"
                "P:      Print to console\n"
                "ESCAPE (or ALT + L): Exit\n"
                "\n"
                "ARROW-KEYS:   Move\n"
                "SCROLL (+/-): Resize\n"
                "  H:    horizontal\n"
                "  V:    vertical\n"
                "  ctrl: histogram"
                "\n\n(right-click to hide info)"
            ),
            transform=self.m.f.transFigure,
            ha="left",
            va="top",
            fontsize=min(self.m.f.bbox.width * 72 / self.m.f.dpi / 60, 12),
            bbox=dict(
                boxstyle="round", facecolor=".8", edgecolor="k", lw=0.5, alpha=0.9
            ),
            zorder=1e6,
            fontfamily="monospace",
        )
        return a

    def _update_info_text(self):
        if getattr(self, "_info_text", None) is not None:
            self._info_text.set_fontsize(
                min(self.m.f.bbox.width * 72 / self.m.f.dpi / 60, 15)
            )

    def _on_resize(self, *args, **kwargs):
        # update snap-grid on resize
        if self.modifier_pressed:
            self._add_snap_grid()
            self._update_info_text()

    @property
    def modifier_pressed(self):
        return self._modifier_pressed

    @modifier_pressed.setter
    def modifier_pressed(self, val):
        self._modifier_pressed = val
        self.m.cb.execute_callbacks(not val)

        if self._modifier_pressed:
            self.m.BM._disable_draw = True
            self.m.BM._disable_update = True
        else:
            self.m.BM._disable_draw = False
            self.m.BM._disable_update = False

    @property
    def ms(self):
        return [self.m.parent, *self.m.parent._children]

    @property
    def maxes(self):
        return [m.ax for m in self.ms]

    @property
    def axes(self):
        return self.f.axes

    @staticmethod
    def roundto(x, base=10):
        if base == 0:
            return x
        if x % base <= base / 2:
            return x - x % base
        else:
            return x + (base - x % base)

    def _get_move_with_key_bbox(self, ax, key):
        snapx, snapy = self._snap
        intervalx, intervaly = (
            max(0.25, snapx),
            max(0.25, snapy),
        )

        if key == "left":
            bbox = Bbox.from_bounds(
                self.roundto(ax.bbox.x0 - intervalx, snapx),
                ax.bbox.y0,
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "right":
            bbox = Bbox.from_bounds(
                self.roundto(ax.bbox.x0 + intervalx, snapx),
                ax.bbox.y0,
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "up":
            bbox = Bbox.from_bounds(
                ax.bbox.x0,
                self.roundto(ax.bbox.y0 + intervaly, snapy),
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "down":
            bbox = Bbox.from_bounds(
                ax.bbox.x0,
                self.roundto(ax.bbox.y0 - intervaly, snapy),
                ax.bbox.width,
                ax.bbox.height,
            )

        bbox = bbox.transformed(self.f.transFigure.inverted())
        return bbox

    def _get_move_bbox(self, ax, x, y):
        w, h = ax.bbox.width, ax.bbox.height
        x0, y0 = (
            self._start_ax_position[ax][0] + (x - self._start_position[0]),
            self._start_ax_position[ax][1] + (y - self._start_position[1]),
        )

        if self._snap_id > 0:
            sx, sy = self._snap
            x0 = self.roundto(x0, sx)
            y0 = self.roundto(y0, sy)

        bbox = Bbox.from_bounds(x0, y0, w, h).transformed(self.f.transFigure.inverted())

        return bbox

    def _get_resize_bbox(self, ax, step):
        origw, origh = ax.bbox.width, ax.bbox.height
        x0, y0 = ax.bbox.x0, ax.bbox.y0

        sx, sy = self._snap

        h, w = origh, origw

        if self._scale_direction == "horizontal":
            w += max(0.25, sx) * step
            w = self.roundto(w, sx)
        elif self._scale_direction == "vertical":
            h += max(0.25, sy) * step
            h = self.roundto(h, sy)
        else:
            w += max(0.25, sx) * step
            w = self.roundto(w, sx)

            h += max(0.25, sy) * step
            h = self.roundto(h, sy)

        if h <= 0 or w <= 0:
            return

        # x0 = self.roundto(x0, sx)
        # y0 = self.roundto(y0, sy)

        # keep the center-position of the scaled axis
        x0 = x0 + (origw - w) / 2
        y0 = y0 + (origh - h) / 2

        bbox = Bbox.from_bounds(x0, y0, w, h).transformed(self.f.transFigure.inverted())

        if bbox.width <= 0 or bbox.height <= 0:
            return

        return bbox

    def _color_unpicked(self, ax):
        for spine in ax.spines.values():
            spine.set_edgecolor("b")
            spine._EOmaps_linestyle = spine.get_linestyle()
            spine.set_linestyle("-")
            spine.set_linewidth(1)

    def _color_picked(self, ax):
        for spine in ax.spines.values():
            spine.set_edgecolor("r")
            spine.set_linestyle("-")
            spine.set_linewidth(2)

    def _color_axes(self):
        for ax in self.axes:
            self._color_unpicked(ax)

        for ax in self._ax_picked:
            if ax is not None:
                self._color_picked(ax)

    def _set_startpos(self, event):
        self._start_position = (event.x, event.y)
        self._start_ax_position = {i: (i.bbox.x0, i.bbox.y0) for i in self._ax_picked}

    def _add_to_history(self):
        self._history_undone.clear()
        self._history = self._history[: self._max_hist_steps]
        self._history.append(self.get_layout())

    def _undo(self):
        if len(self._history) > 0:
            l = self._history.pop(-1)
            self._history_undone.append(l)
            self.m.apply_layout(l)

    def _redo(self):
        if len(self._history_undone) > 0:
            l = self._history_undone.pop(-1)
            self._history.append(l)
            self.m.apply_layout(l)

    def cb_release(self, event):
        self._set_startpos(event)

    def cb_pick(self, event):
        if not self.modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        # toggle info-text visibility on left-click
        if event.button == 3:
            if getattr(self, "_info_text", None) is not None:
                vis = not self._info_text.get_visible()
                self._info_text.set_visible(vis)
                self._info_text_hidden = not vis

        eventax = event.inaxes

        if eventax not in self.axes:
            # if no axes is clicked "unpick" previously picked axes
            if len(self._ax_picked) == 0:
                # if there was nothing picked there's nothing to do
                # except updating the info-text visibility

                if getattr(self, "_info_text", None) is not None:
                    self.blit_artists()

                return

            self._ax_picked = []
            self._m_picked = []
            self._color_axes()
            self._remove_snap_grid()
            self.fetch_current_background()
            self.blit_artists()
            return

        if self._shift_pressed:
            if eventax in self.maxes:
                m = self.ms[self.maxes.index(eventax)]
                if eventax in self._ax_picked:
                    self._ax_picked.remove(eventax)
                else:
                    self._ax_picked.append(eventax)

                if m in self._m_picked:
                    self._m_picked.remove(m)
                else:
                    self._m_picked.append(m)
            else:
                if eventax in self._ax_picked:
                    self._ax_picked.remove(eventax)
                    # handle colorbar axes
                    if eventax.get_label() == "cb":
                        for cbax in getattr(eventax, "_eomaps_cb_axes", []):
                            self._ax_picked.remove(cbax)
                else:
                    self._ax_picked.append(eventax)
                    # handle colorbar axes
                    if eventax.get_label() == "cb":
                        for cbax in getattr(eventax, "_eomaps_cb_axes", []):
                            self._ax_picked.append(cbax)
        else:
            if eventax not in self._ax_picked:
                self._m_picked = []
                self._ax_picked = []

                if eventax in self.axes:
                    if eventax in self.maxes:
                        self._ax_picked.append(eventax)
                        self._m_picked.append(self.ms[self.maxes.index(eventax)])
                    else:
                        self._m_picked = []
                        self._ax_picked.append(eventax)
                        # handle colorbar axes
                        if eventax.get_label() == "cb":
                            for cbax in getattr(eventax, "_eomaps_cb_axes", []):
                                self._ax_picked.append(cbax)

                    self._add_snap_grid()
            else:
                self._add_snap_grid()

        self._set_startpos(event)
        self._color_axes()
        self.fetch_current_background()
        self.blit_artists()

    def fetch_current_background(self):
        # clear the renderer to avoid drawing on existing backgrounds
        renderer = self.m.BM.canvas.get_renderer()
        renderer.clear()

        with ExitStack() as stack:
            for ax in self._ax_picked:
                stack.enter_context(ax._cm_set(visible=False))

            self.m.BM.blit_artists(self.axes, None, False)

            grid = getattr(self, "_snap_grid_artist", None)
            if grid is not None:
                self.m.BM.blit_artists([grid], None, False)

            self.m.BM.canvas.blit()
            self._current_bg = self.m.BM.canvas.copy_from_bbox(self.m.f.bbox)

    def cb_move_with_key(self, event):
        if not self.modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        if event.key not in ["left", "right", "up", "down"]:
            return

        for ax in self._ax_picked:
            bbox = self._get_move_with_key_bbox(ax, event.key)
            ax.set_position(bbox)

        self._add_to_history()
        self._color_axes()
        self.blit_artists()

    def cb_move(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self.modifier is not None:
            if not self.modifier_pressed:
                return False

        if event.button != 1:
            return

        for ax in self._ax_picked:
            if ax is None:
                return

            bbox = self._get_move_bbox(ax, event.x, event.y)
            ax.set_position(bbox)

        self._add_to_history()
        self._color_axes()
        self.blit_artists()

    def blit_artists(self):
        artists = [*self._ax_picked]

        if getattr(self, "_info_text", None) is not None:
            artists.append(self._info_text)

        self.m.BM.blit_artists(artists, self._current_bg)

    def cb_scroll(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self.modifier is not None:
            if not self.modifier_pressed:
                return False

        if self._scale_direction == "set_hist_size":
            # resize colorbar histogram
            for ax in self._ax_picked:
                if not ax.get_label() == "cb":
                    continue

                # identify all relevant colorbars
                # (e.g. all colorbars that share the container-ax "cb._ax")
                cbs = []
                for m in self.ms:
                    for cb in m._colorbars:
                        if cb._ax is ax:
                            cbs.append(cb)

                if len(cbs) == 0:
                    return False

                # use the hist-size of the first colorbar as start (to avoid ambiguity)
                start_size = cbs[0]._hist_size
                for cb in cbs:
                    new_size = np.clip(start_size + event.step * 0.02, 0.0, 1.0)
                    cb._set_hist_size(new_size)

            self._add_to_history()
            self.blit_artists()
        else:
            # resize axes
            for ax in self._ax_picked:
                if ax is None:
                    continue
                resize_bbox = self._get_resize_bbox(ax, event.step)
                if resize_bbox is not None:
                    ax.set_position(resize_bbox)
            self._add_to_history()
            self.blit_artists()

    def cb_key_press(self, event):
        # release shift key on every keypress
        self._shift_pressed = False

        if (event.key == self.modifier) and (not self.modifier_pressed):
            self._make_draggable()
            return
        elif (event.key == self.modifier or event.key == "escape") and (
            self.modifier_pressed
        ):
            self._undo_draggable()
            return
        elif (event.key.lower() == "p") and (self.modifier_pressed):
            s = "\nlayout = {\n    "
            s += "\n    ".join(
                f'"{key}": {val},' for key, val in self.get_layout().items()
            )
            s += "\n}\n"
            print(s)
        elif (event.key.lower() == "q") and (self.modifier_pressed):
            print(
                "\n##########################\n\n"
                "EOmaps Layout Editor controls:\n\n"
                "Click on axes to select them for editing.\n"
                "(Hold 'shift' while clicking on axes to select multiple axes.)\n\n"
                "Drag selected axes with the mouse or use the 'arrow-keys' to "
                "change their position.\n\n"
                "Use the 'scroll-wheel' or the '+' and '-' keys to change the size "
                "of selected axes.\n"
                "For normal matplotlib axes: Hold down 'h' or 'v' to adjust only "
                "the horizontal or vertical size of the axes.\n"
                "For EOmaps colorbars: Hold down 'control' to adjust the relative "
                "size of the histogram.\n\n"
                "Use the keys 1-9 to adjust the spacing of the 'snap grid' (Note that "
                "the grid-spacing also determines the step-size for size- and "
                "position-changes!) Press 0 to disable grid-snapping.\n\n"
                f"To exit, press 'escape' or '{self.modifier}'\n"
                "\n##########################\n\n"
            )
            return

        else:
            if not self.modifier_pressed:
                # only continue if  modifier is pressed!
                return

        if event.key in ("ctrl+z", "control+z"):
            self._undo()
            return
        elif event.key in ("ctrl+y", "control+y"):
            self._redo()
            return
        elif event.key == "h":
            self._scale_direction = "horizontal"
        elif event.key == "v":
            self._scale_direction = "vertical"
        elif event.key in ("control", "ctrl", "ctrl++", "ctrl+-"):
            self._scale_direction = "set_hist_size"

        elif event.key == "shift":
            self._shift_pressed = True

        # assign snaps with keys 0-9
        if event.key in map(str, range(10)):
            self._snap_id = int(event.key)
            self._add_snap_grid()
            self.fetch_current_background()
            self.blit_artists()

        # assign snaps with keys 0-9
        if event.key in ["+", "-", "ctrl++", "ctrl+-"]:

            class dummyevent:
                pass

            d = dummyevent()
            d.key = event.key
            d.step = 1 * {"+": 1, "ctrl++": 1, "ctrl+-": -1, "-": -1}[event.key]

            self.cb_scroll(d)

    def cb_key_release(self, event):
        # reset scale direction on every key release event
        if event.key in ("h", "v", "control", "ctrl", "ctrl++", "ctrl+-"):
            self._scale_direction = "both"
        if event.key in ("shift"):
            self._shift_pressed = False

    @property
    def _snap(self):
        # grid-separation distance
        if self._snap_id == 0:
            snap = (0, 0)
        else:
            n = (self.f.bbox.width / 400) * (self._snap_id)

            snap = (n, n)

        return snap

    def ax_on_layer(self, ax):
        if ax in self.m.BM._get_unmanaged_axes():
            return True
        elif ax in self.maxes:
            return True
        else:
            for layer in (self.m.BM.bg_layer, "__SPINES__", "all"):
                # logos are put on the spines-layer to appear on top of spines!
                if ax in self.m.BM.get_bg_artists(layer):
                    return True
                elif ax in self.m.BM.get_artists(self.m.BM.bg_layer):
                    return True

        return False

    def _make_draggable(self, filepath=None):
        # Uncheck active pan/zoom actions of the matplotlib toolbar.
        # use a try-except block to avoid issues with ipympl in jupyter notebooks
        # (see https://github.com/matplotlib/ipympl/issues/530#issue-1780919042)
        try:
            toolbar = getattr(self.m.BM.canvas, "toolbar", None)
            if toolbar is not None:
                for key in ["pan", "zoom"]:
                    val = toolbar._actions.get(key, None)
                    if val is not None and val.isCheckable() and val.isChecked():
                        val.trigger()
        except AttributeError:
            pass

        self._filepath = filepath
        self.modifier_pressed = True
        _log.info(
            "EOmaps: Layout Editor activated! (press 'esc' to exit " "and 'q' for info)"
        )

        self._history.clear()
        self._history_undone.clear()
        self._add_to_history()

        self._revert_props = []
        for ax in self.f.axes:
            # only handle axes that have a finite size (in pixels) to avoid
            # singular matrix errors for initially hidden zero-size axes
            # (can happen for colorbar/colorbar histogram axes)
            singularax = False
            if ax.bbox.width <= 1 or ax.bbox.height <= 1:
                singularax = True

            # check if the axis is the container-axes of a colorbar
            cbaxQ = ax.get_label() == "cb"

            if not ax.axison:
                showXY = False
                self._revert_props.append(ax.set_axis_off)
                ax.set_axis_on()
            else:
                showXY = True

            # keep singular axes hidden
            self._revert_props.append((ax.set_visible, ax.get_visible()))
            if not singularax:
                if self.ax_on_layer(ax):
                    ax.set_visible(True)
                else:
                    ax.set_visible(False)
            else:
                ax.set_visible(False)

            self._revert_props.append((ax.set_animated, ax.get_animated()))
            ax.set_animated(False)

            self._revert_props.append((ax.set_frame_on, ax.get_frame_on()))
            ax.set_frame_on(True)

            for child in ax.get_children():
                # make sure we don't treat axes again (in case they are child-axes)
                if child in self.f.axes:
                    continue
                revert_props = [
                    "edgecolor",
                    "linewidth",
                    "alpha",
                    "animated",
                    "visible",
                ]
                self._add_revert_props(child, *revert_props)

                if isinstance(child, Spine) and not cbaxQ:
                    # make sure spines are visible (and re-drawn on draw)
                    child.set_animated(False)
                    child.set_visible(True)
                    if hasattr(child, "_EOmaps_linestyle"):
                        child.set_linestyle(getattr(child, "_EOmaps_linestyle", "-"))
                        del child._EOmaps_linestyle
                elif (
                    ax not in self.maxes
                    and showXY
                    and isinstance(child, (XAxis, YAxis))
                ):
                    # keep all tick labels etc. of normal axes and colorbars visible
                    child.set_animated(False)
                    child.set_visible(True)

                elif child is ax.patch and not cbaxQ:
                    # only reset facecolors for axes-patches to avoid issues with
                    # black spines (TODO check why this happens!)
                    self._add_revert_props(child, "facecolor")

                    # make sure patches are visible (and re-drawn on draw)
                    child.set_visible(True)
                    child.set_facecolor("w")
                    child.set_alpha(0.75)  # for overlapping axes

                else:
                    # make all other children invisible (to avoid drawing them)
                    child.set_visible(False)
                    child.set_animated(True)

        # only re-draw if info-text is None
        if getattr(self, "_info_text", None) is None:
            self._info_text = self.add_info_text()

        self._color_axes()
        self._attach_callbacks()

        self.m._emit_signal("layoutEditorActivated")

        self.m.redraw()

    def _add_revert_props(self, child, *args):
        for prop in args:
            if hasattr(child, f"set_{prop}") and hasattr(child, f"get_{prop}"):
                self._revert_props.append(
                    (
                        getattr(child, f"set_{prop}"),
                        getattr(child, f"get_{prop}")(),
                    )
                )

    def _undo_draggable(self):
        if getattr(self, "_info_text", None) not in (None, False):
            self._info_text.remove()
            # set to None to avoid crating the info-text again
            self._info_text = None

        self._history.clear()
        self._history_undone.clear()

        toolbar = getattr(self.m.f, "toolbar", None)
        if toolbar is not None:
            # Reset the axes stack to make sure the "home" "back" and "forward" buttons
            # of the toolbar do not reset axis positions
            # see "matplotlib.backend_bases.NavigationToolbar2.update"
            if hasattr(toolbar, "update"):
                try:
                    toolbar.update()
                except Exception:
                    _log.exception(
                        "EOmaps: Error while trying to reset the axes stack!"
                    )

        # clear all picks on exit
        self._ax_picked = []
        self._m_picked = []

        _log.info("EOmaps: Exiting layout-editor mode...")

        # in case a filepath was provided, save the new layout
        if self._filepath:
            try:
                self.m.get_layout(filepath=self._filepath, override=True)
            except Exception:
                _log.exception(
                    "EOmaps: Layout could not be saved to the provided "
                    + f"filepath: '{self._filepath}'."
                )

        self._reset_callbacks()
        # revert all changes to artists
        for p in self._revert_props:
            if isinstance(p, tuple):
                p[0](p[1])
            else:
                p()

        self.modifier_pressed = False

        # reset the histogram-size of all colorbars to make sure previously hidden
        # axes (e.g. size=0) become visible if the size is now > 0.
        for m in self.ms:
            for cb in m._colorbars:
                cb._set_hist_size(update_all=True)

        # remove snap-grid (if it's still visible)
        self._remove_snap_grid()

        self.m._emit_signal("layoutEditorDeactivated")

        self.m.redraw()
        # try to push the current view to the "home" toolbar button
        try:
            self.m.f.canvas.toolbar.push_current()
        except Exception:
            pass

    def _reset_callbacks(self):
        # disconnect all callbacks of the layout-editor
        while len(self.cids) > 0:
            cid = self.cids.pop(-1)
            self.f.canvas.mpl_disconnect(cid)

    def _attach_callbacks(self):
        # make sure all previously set callbacks are reset
        self._reset_callbacks()

        events = (
            ("scroll_event", self.cb_scroll),
            ("button_press_event", self.cb_pick),
            ("button_release_event", self.cb_release),
            ("motion_notify_event", self.cb_move),
            ("key_press_event", self.cb_move_with_key),
            ("key_release_event", self.cb_key_release),
        )

        for event, cb in events:
            self.cids.append(self.f.canvas.mpl_connect(event, cb))

    def _add_snap_grid(self, snap=None):
        # snap = (snapx, snapy)

        if snap is None:
            if self._snap_id == 0:
                self._remove_snap_grid()
                return
            else:
                snapx, snapy = self._snap
        else:
            snapx, snapy = snap

        self._remove_snap_grid()

        bbox = self.m.f.bbox
        t = self.m.f.transFigure.inverted()

        gx, gy = np.mgrid[
            0 : int(bbox.width) + int(snapx) : snapx,
            0 : int(bbox.height) + int(snapy) : snapy,
        ]
        g = t.transform(np.column_stack((gx.flat, gy.flat)))

        l = Line2D(
            *g.T,
            lw=0,
            marker=".",
            markerfacecolor="steelblue",
            markeredgecolor="none",
            ms=(snapx + snapy) / 6,
        )
        self._snap_grid_artist = self.m.f.add_artist(l)

    def _remove_snap_grid(self):
        if hasattr(self, "_snap_grid_artist"):
            self._snap_grid_artist.remove()
            del self._snap_grid_artist

    def get_layout(self, filepath=None, override=False, precision=5):
        """
        Get the positions of all axes within the current plot.

        To re-apply a layout, use:

            >>> l = m.get_layout()
            >>> m.set_layout(l)

        Note
        ----
        The returned list is only a snapshot of the current layout.
        It can only be re-applied to a given figure if the order at which the axes are
        created remains the same!

        Parameters
        ----------
        filepath : str or pathlib.Path, optional
            If provided, a json-file will be created at the specified destination that
            can be used in conjunction with `m.set_layout(...)` to apply the layout:

            >>> m.get_layout(filepath=<FILEPATH>, override=True)
            >>> m.apply_layout_layout(<FILEPATH>)

            You can also manually read-in the layout-dict via:
            >>> import json
            >>> layout = json.load(<FILEPATH>)
        override: bool
            Indicator if the file specified as 'filepath' should be overwritten if it
            already exists.
            The default is False.
        precision : int or None
            The precision of the returned floating-point numbers.
            If None, all available digits are returned
            The default is 5
        Returns
        -------
        layout : dict or None
            A dict of the positions of all axes, e.g.: {1:(x0, y0, width height), ...}
        """
        figsize = [*self.f.get_size_inches()]

        axes = [
            a for a in self.axes if a.get_label() not in ["EOmaps_cb", "EOmaps_cb_hist"]
        ]

        # identify relevant colorbars
        colorbars = [getattr(m, "colorbar", None) for m in self.ms]
        cbaxes = [getattr(cb, "_ax", None) for cb in colorbars]
        cbs = [(colorbars[cbaxes.index(a)] if a in cbaxes else None) for a in axes]
        # -----------

        layout = dict()
        layout["figsize"] = figsize

        for i, ax in enumerate(axes):
            if cbs[i] is not None:
                if cbs[i]._ax.get_axes_locator() is not None:
                    continue

            label = ax.get_label()
            name = f"{i}_{label}"
            if precision is not None:
                layout[name] = np.round(ax.get_position().bounds, precision).tolist()
            else:
                layout[name] = ax.get_position().bounds

            if cbs[i] is not None:
                layout[f"{name}_histogram_size"] = cbs[i]._hist_size

        if filepath is not None:
            filepath = Path(filepath)
            assert (
                not filepath.exists() or override
            ), f"The file {filepath} already exists! Use override=True to relace it."
            with open(filepath, "w") as file:
                json.dump(layout, file)
            _log.info(f"EOmaps: Layout saved to:\n       {filepath}")

        return layout

    def apply_layout(self, layout):
        """
        Set the positions of all axes within the current plot based on a previously
        defined layout.

        To apply a layout, use:

            >>> l = m.get_layout()
            >>> m.set_layout(l)

        To save a layout to disc and apply it at a later stage, use
            >>> m.get_layout(filepath=<FILEPATH>)
            >>> m.set_layout(<FILEPATH>)

        Note
        ----
        The returned list is only a snapshot of the current layout.
        It can only be re-applied to a given figure if the order at which the axes are
        created remains the same!

        Parameters
        ----------
        layout : dict, str or pathlib.Path
            If a dict is provided, it is directly used to define the layout.

            If a string or a pathlib.Path object is provided, it will be used to
            read a previously dumped layout (e.g. with `m.get_layout(filepath)`)

        """
        if isinstance(layout, (str, Path)):
            with open(layout, "r") as file:
                layout = json.load(file)

        # check if all relevant axes are specified in the layout
        valid_keys = set(self.get_layout())
        if valid_keys != set(layout):
            _log.warning(
                "EOmaps: The the layout does not match the expected structure! "
                "Layout might not be properly restored. "
                "Invalid or missing keys:\n"
                f"{sorted(valid_keys.symmetric_difference(set(layout)))}\n"
            )

        # set the figsize
        figsize = layout.get("figsize", None)
        if figsize is not None:
            self.f.set_size_inches(*figsize)

        axes = [
            a for a in self.axes if a.get_label() not in ["EOmaps_cb", "EOmaps_cb_hist"]
        ]

        # identify relevant colorbars
        colorbars = [getattr(m, "colorbar", None) for m in self.ms]
        cbaxes = [getattr(cb, "_ax", None) for cb in colorbars]
        cbs = [(colorbars[cbaxes.index(a)] if a in cbaxes else None) for a in axes]

        for key in valid_keys.intersection(set(layout)):
            if key == "figsize":
                continue
            val = layout[key]

            i = int(key[: key.find("_")])
            if key.endswith("_histogram_size"):
                cbs[i]._set_hist_size(val)
            else:
                axes[i].set_position(val)

        # force an immediate draw (rather than using draw_idle) to avoid issues with
        # stacking order for tkagg backend
        self.m.redraw()
        self.m.f.canvas.draw()

        # try to push the current view to the "home" toolbar button
        try:
            self.m.f.canvas.toolbar.push_current()
        except Exception:
            pass

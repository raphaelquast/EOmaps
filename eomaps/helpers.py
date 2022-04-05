"""a collection of useful helper-functions."""
from itertools import tee
import re
import sys

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from collections import defaultdict
from itertools import chain
from matplotlib.transforms import Bbox
import matplotlib.pyplot as plt


def pairwise(iterable, pairs=2):
    """
    a generator to return n consecutive values from an iterable.

        pairs = 2
        s -> (s0,s1), (s1,s2), (s2, s3), ...

        pairs = 3
        s -> (s0, s1, s2), (s1, s2, s3), (s2, s3, s4), ...

    adapted from https://docs.python.org/3.7/library/itertools.html
    """
    x = tee(iterable, pairs)
    for n, n_iter in enumerate(x[1:]):
        [next(n_iter, None) for i in range(n + 1)]
    return zip(*x)


def _sanitize(s, prefix="layer_"):
    # taken from https://stackoverflow.com/a/3303361/9703451
    s = str(s)
    # Remove leading characters until we find a letter or underscore
    s2 = re.sub("^[^a-zA-Z_]+", "", s)
    if len(s2) == 0:
        s2 = _sanitize(prefix + str(s))
    # replace invalid characters with an underscore
    s = re.sub("[^0-9a-zA-Z_]", "_", s2)
    return s


def cmap_alpha(cmap, alpha, interpolate=False):
    """
    add transparency to an existing colormap

    Parameters
    ----------
    cmap : matplotlib.colormap
        the colormap to use
    alpha : float
        the transparency
    interpolate : bool
        indicator if a listed colormap (False) or a interpolated colormap (True)
        should be generated. The default is False

    Returns
    -------
    new_cmap : matplotlib.colormap
        a new colormap with the desired transparency
    """

    new_cmap = cmap(np.arange(cmap.N))
    new_cmap[:, -1] = alpha
    if interpolate:
        new_cmap = LinearSegmentedColormap("new_cmap", new_cmap)
    else:
        new_cmap = ListedColormap(new_cmap)
    return new_cmap


# a simple progressbar
# taken from https://stackoverflow.com/a/34482761/9703451
def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)

    def show(j):
        x = int(size * j / count)
        file.write("\r%s[%s%s] %i/%i\r" % (prefix, "#" * x, "." * (size - x), j, count))
        file.flush()

    show(0)
    for i, item in enumerate(it):
        yield item
        show(i + 1)
    file.write("\n")
    file.flush()


class searchtree:
    def __init__(self, m=None, pick_distance=50):
        """
        search for coordinates

        Parameters
        ----------
        m : eomaps.Maps, optional
            the maps-object. The default is None.
        pick_distance : int, optional
            used to limit the number of pixels in the search to
            a rectangle of (pick_distance * estimated radius in plot_crs)
            The default is 50.
        """
        self._m = m
        self._pick_distance = pick_distance

        if self._m.shape.radius_crs != "out":
            radius = self._m.set_shape._estimate_radius(self._m, "out", np.max)
        else:
            radius = self._m.shape.radius
        self.d = max(radius) * self._pick_distance

        self._misses = 0

    def query(self, x, k=1, d=None):
        if d is None:
            d = self.d

        # select a rectangle around the pick-coordinates
        # (provides tremendous speedups for very large datasets)
        mx = np.logical_and(
            self._m._props["x0"] > (x[0] - d), self._m._props["x0"] < (x[0] + d)
        )
        my = np.logical_and(
            self._m._props["y0"] > (x[1] - d), self._m._props["y0"] < (x[1] + d)
        )
        m = np.logical_and(mx, my)
        # get the indexes of the search-rectangle
        idx = np.where(m.ravel())[0]
        # evaluate the clicked pixel as the one with the smallest
        # euclidean distance
        if len(idx) > 0:
            i = idx[
                (
                    (self._m._props["x0"][m].ravel() - x[0]) ** 2
                    + (self._m._props["y0"][m].ravel() - x[1]) ** 2
                ).argmin()
            ]

        else:
            # show some warning if no points are found within the pick_distance

            if self._misses < 3:
                self._misses += 1

                text = "Found no data here...\n Increase pick_distance?"

                self._m.cb.click._cb.annotate(
                    pos=x,
                    permanent=False,
                    text=text,
                    xytext=(0.98, 0.98),
                    textcoords=self._m.figure.f.transFigure,
                    horizontalalignment="right",
                    verticalalignment="top",
                    arrowprops=None,
                    fontsize=7,
                    bbox=dict(ec="r", fc=(1, 0.9, 0.9, 0.5), lw=0.25, boxstyle="round"),
                )

            i = None

        return None, i


class draggable_axes:
    def __init__(self, m, modifier="alt+d", cb_modifier="control"):
        self.modifier = modifier
        self.cb_modifier = cb_modifier

        self.m = m
        self.f = self.m.parent.figure.f

        self._ax_picked = None
        self._m_picked = None
        self._cb_picked = False

        self._modifier_pressed = False

        self.cids = []

        # indicator if the pick-callback should be re-attached or not
        self._reattach_pick_cb = False

        self.f.canvas.mpl_connect("key_press_event", self.cb_key_press)

        self._annotations = []
        self._hiddenax = []

        self._artists_visible = dict()

        self._ax_visible = dict()

    def clear_annotations(self):
        while len(self._annotations) > 0:
            a = self._annotations.pop(-1)
            a.remove()

        self._hiddenax = []

    def set_annotations(self):
        self.clear_annotations()

        for cb in self.cbs:
            for ax in cb:
                if ax is None:
                    continue
                if not ax.get_visible():
                    x = ax.bbox.x0 + ax.bbox.width / 2
                    y = ax.bbox.y0 + ax.bbox.height / 2

                    a = self.m.figure.ax.annotate(
                        r"$\bullet$",
                        xy=(x, y),
                        xycoords="figure pixels",
                        annotation_clip=False,
                        color="r",
                        fontsize=18,
                    )
                    self._annotations.append(a)
                    self._hiddenax.append(ax)

    @property
    def ms(self):
        return [self.m.parent, *self.m.parent._children]

    @property
    def maxes(self):
        return [m.figure.ax for m in self.ms]

    @property
    def axes(self):
        # get all axes (and child-axes)
        # return [i.figure.ax for i in self.ms if i.figure.ax is not None]
        cbaxes = [i for cb in self.cbs for i in cb]
        return [i for i in self.all_axes if i not in cbaxes]

    @property
    def all_axes(self):
        return self.f.axes
        # return self.axes + [ax for caxes in self.cbs for ax in caxes if ax is not None]

    def get_spines_visible(self):
        return [
            {key: val.get_visible() for key, val in ax.spines.items()}
            for ax in self.all_axes
        ]

    @property
    def cbs(self):
        # get all axes (and child-axes)
        cbs = list()
        for i in self.ms:
            cbis = list()
            if hasattr(i.figure, "ax_cb"):
                cbis.append(i.figure.ax_cb)
            if hasattr(i.figure, "ax_cb_plot"):
                cbis.append(i.figure.ax_cb_plot)

            if len(cbis) > 0:
                cbs.append(cbis)
            else:
                cbs.append((None, None))
        return cbs

    def cb_move_with_key(self, event):
        if not self._modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self._ax_picked is None:
            return

        key = event.key
        if key.startswith("alt+"):
            key = key[4:]
            interval = 10
            method = 0  # e.g. zoom
        elif key.startswith("ctrl+"):
            key = key[5:]
            interval = 1
            method = 1  # e.g. change rate
        else:
            interval = 1
            method = 0  # e.g. zoom

        if key not in ["left", "right", "up", "down"]:
            return

        if method == 0:  # e.g. key pressed
            for ax in self._ax_picked:
                if key == "left":
                    bbox = Bbox.from_bounds(
                        int(ax.bbox.x0 - interval),
                        ax.bbox.y0,
                        ax.bbox.width,
                        ax.bbox.height,
                    )
                elif key == "right":
                    bbox = Bbox.from_bounds(
                        int(ax.bbox.x0 + interval),
                        ax.bbox.y0,
                        ax.bbox.width,
                        ax.bbox.height,
                    )
                elif key == "up":
                    bbox = Bbox.from_bounds(
                        ax.bbox.x0,
                        int(ax.bbox.y0 + interval),
                        ax.bbox.width,
                        ax.bbox.height,
                    )
                elif key == "down":
                    bbox = Bbox.from_bounds(
                        ax.bbox.x0,
                        int(ax.bbox.y0 - interval),
                        ax.bbox.width,
                        ax.bbox.height,
                    )

                bbox = bbox.transformed(self.f.transFigure.inverted())

                ax.set_position(bbox)
        if method == 1:  # e.g. ctrl + key pressed
            if self._cb_picked:
                orientation = self._m_picked._colorbar[-2]
                if orientation == "horizontal":
                    ratio = (
                        self._m_picked.figure.ax_cb_plot.bbox.height
                        / self._m_picked.figure.ax_cb.bbox.height
                    )
                elif orientation == "vertical":
                    ratio = (
                        self._m_picked.figure.ax_cb_plot.bbox.width
                        / self._m_picked.figure.ax_cb.bbox.width
                    )

                ratio = np.round(ratio, 1)
                if key == "left":
                    ratio += 0.5
                    self._m_picked.figure.set_colorbar_position(
                        ratio=ratio if ratio < 15 else 1000
                    )
                elif key == "right":
                    if ratio > 900:
                        ratio = 15
                    self._m_picked.figure.set_colorbar_position(
                        ratio=max(ratio - 0.5, 0)
                    )
                elif key == "up":
                    # toggle ax_cb_plot and make the ticks visible
                    if self._m_picked.figure.ax_cb_plot in self._ax_visible:
                        vis = not self._ax_visible[self._m_picked.figure.ax_cb_plot]
                    else:
                        vis = not self._m_picked.figure.ax_cb_plot.get_visible()

                    # self._m_picked.figure.ax_cb_plot.set_visible(vis)
                    self._ax_visible[self._m_picked.figure.ax_cb_plot] = vis

                elif key == "down":
                    # toggle ax_cb and make the ticks visible
                    if self._m_picked.figure.ax_cb in self._ax_visible:
                        vis = not self._ax_visible[self._m_picked.figure.ax_cb]
                    else:
                        vis = not self._m_picked.figure.ax_cb.get_visible()
                    # self._m_picked.figure.ax_cb.set_visible(vis)
                    self._ax_visible[self._m_picked.figure.ax_cb] = vis

                # fix the visible ticks
                orientation = self._m_picked._colorbar[-2]
                if self._m_picked.figure.ax_cb.get_visible() is False:
                    if orientation == "vertical":
                        self._m_picked.figure.ax_cb_plot.tick_params(
                            right=True,
                            labelright=True,
                            bottom=True,
                            labelbottom=True,
                            left=False,
                            labelleft=False,
                            top=False,
                            labeltop=False,
                        )
                    elif orientation == "horizontal":
                        self._m_picked.figure.ax_cb_plot.tick_params(
                            bottom=True,
                            labelbottom=True,
                            left=True,
                            labelleft=True,
                            top=False,
                            labeltop=False,
                            right=False,
                            labelright=False,
                        )
                else:
                    if orientation == "vertical":
                        self._m_picked.figure.ax_cb_plot.tick_params(
                            right=False,
                            labelright=False,
                            bottom=True,
                            labelbottom=True,
                            left=False,
                            labelleft=False,
                            top=False,
                            labeltop=False,
                        )
                    elif orientation == "horizontal":
                        self._m_picked.figure.ax_cb_plot.tick_params(
                            bottom=False,
                            labelbottom=False,
                            left=True,
                            labelleft=True,
                            top=False,
                            labeltop=False,
                            right=False,
                            labelright=False,
                        )
            else:
                pass
        self.set_annotations()
        self._color_axes()
        self.m.BM._refetch_bg = True
        self.m.BM.canvas.draw()

    def cb_move(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self.modifier is not None:
            if not self._modifier_pressed:
                return False
        if self._ax_picked is None:
            return

        if event.button != 1:
            return

        b = [0, 0, 0, 0]
        for ax in self._ax_picked:
            if ax is None:
                return
            if not event.button:
                return
            w, h = ax.bbox.width, ax.bbox.height
            x0, y0 = event.x - w / 2, event.y - h / 2
            # make sure that we don't move the axis outside the figure
            # avoid this since cartopy axis can be bigger than the canvas!
            # fbbox = self.f.bbox
            # if x0 <= fbbox.x0:
            #     x0 = fbbox.x0
            # if x0 + w >= fbbox.x1:
            #     x0 = fbbox.x1 - w
            # if y0 <= fbbox.y0:
            #     y0 = fbbox.y0
            # if y0 + h >= fbbox.y1:
            #     y0 = fbbox.y1 - h

            bbox = Bbox.from_bounds(x0, y0, w, h).transformed(
                self.f.transFigure.inverted()
            )

            if not self._cb_picked:
                ax.set_position(bbox)
            else:
                orientation = self._m_picked._colorbar[-2]
                if orientation == "horizontal":
                    b = [bbox.x0, bbox.y0, bbox.width, b[3] + bbox.height]
                elif orientation == "vertical":
                    b = [bbox.x0, bbox.y0, b[2] + bbox.width, bbox.height]

        if (
            self._cb_picked
            and (self._m_picked is not None)
            and (self._ax_picked is not None)
        ):
            self._m_picked.figure.set_colorbar_position(b)

        self.set_annotations()

        self.m.BM._refetch_bg = True
        self.m.BM.canvas.draw()

    def _color_axes(self):
        for ax in self.all_axes:
            for spine in ax.spines.values():
                spine.set_edgecolor("red")

                if ax in self._ax_visible and self._ax_visible[ax]:
                    spine.set_linestyle("-")
                    spine.set_linewidth(2)
                else:
                    spine.set_linestyle(":")
                    spine.set_linewidth(1)

        if self._ax_picked is not None:
            for ax in self._ax_picked:
                if ax is None:
                    continue
                for spine in ax.spines.values():
                    spine.set_edgecolor("green")

                if ax in self._ax_visible and self._ax_visible[ax]:
                    spine.set_linestyle("-")
                    spine.set_linewidth(2)
                else:
                    spine.set_linestyle(":")
                    spine.set_linewidth(1)

    def cb_pick(self, event):

        if not self._modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        eventax = event.inaxes

        if eventax not in self.all_axes:
            # TODO this needs some update...
            # check if we clicked on a hidden ax, and if so make it visible again
            # hidden_ax, hidden_ann = None, None
            # for ax, ann in zip(self._hiddenax, self._annotations):
            #     bbox = ax.bbox
            #     if (
            #         (event.x > bbox.x0)
            #         & (event.x < bbox.x1)
            #         & (event.y > bbox.y0)
            #         & (event.y < bbox.y1)
            #     ):
            #         hidden_ax = ax
            #         hidden_ann = ann
            #         break
            # if hidden_ax is not None:
            #     hidden_ax.set_visible(True)
            #     hidden_ann.set_visible(False)
            #     self.m.BM.update(artists=[hidden_ax] + self._annotations)
            #     self.set_annotations()
            #     return

            # if no axes is clicked "unpick" previously picked axes
            prev_pick = self._ax_picked
            if prev_pick is None:
                # if there was no ax picked there's nothing to do...
                return

            self._ax_picked = None
            self._m_picked = None
            self._cb_picked = False
            self._color_axes()
            self.m.BM.canvas.draw()
            return

        _m_picked = False
        _cb_picked = False
        _ax_picked = [eventax]

        if eventax in self.axes:
            _ax_picked = [eventax]
            if eventax in self.maxes:
                _m_picked = self.ms[self.maxes.index(eventax)]
            else:
                _m_picked = None
            _cb_picked = False
        else:
            # check if we picked a colorbar
            for i, cbi in enumerate(self.cbs):
                if eventax in cbi:
                    if all(i is not None for i in cbi):
                        _cb_picked = True
                        _m_picked = self.ms[i]
                        _ax_picked = cbi
                    break

        if self._m_picked is not None:
            if self._m_picked is _m_picked and self._cb_picked == _cb_picked:
                return

        self._ax_picked = _ax_picked
        self._m_picked = _m_picked
        self._cb_picked = _cb_picked

        self._color_axes()

        self.set_annotations()
        self.m.BM.canvas.draw()

    def cb_scroll(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self.modifier is not None:
            if not self._modifier_pressed:
                return False

        steps = event.step

        if self._ax_picked is None:
            return

        b = [0, 0, 0, 0]

        for ax in self._ax_picked:
            if ax is None:
                return

            pos = ax.get_position()

            wstep = steps * pos.width * 0.025
            hstep = steps * pos.height * 0.025

            if not self._cb_picked:
                ax.set_position(
                    (
                        pos.x0 - wstep / 2,
                        pos.y0 - hstep / 2,
                        pos.width + wstep,
                        pos.height + hstep,
                    )
                )
            else:
                orientation = self._m_picked._colorbar[-2]
                if orientation == "horizontal":
                    b = [
                        pos.x0 - wstep / 2,
                        pos.y0 - hstep / 2,
                        pos.width + wstep,
                        b[3] + pos.height + hstep,
                    ]
                elif orientation == "vertical":
                    b = [
                        pos.x0 - wstep / 2,
                        pos.y0 - hstep / 2,
                        b[2] + pos.width + wstep,
                        pos.height + hstep,
                    ]

        if self._cb_picked and self._m_picked is not None:
            self._m_picked.figure.set_colorbar_position(b)

        self._color_axes()
        self.m.BM.canvas.draw()

    def cb_key_press(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        if event.key == self.modifier:
            if self._modifier_pressed:
                self._undo_draggable()
            else:
                self._make_draggable()

    def _undo_draggable(self):
        print("EOmaps: Making axes interactive again...")

        for ax, frameQ, spine_vis in zip(
            self.all_axes, self._frameon, self._spines_visible
        ):

            ax.set_frame_on(frameQ)
            for key, spine in ax.spines.items():
                spine.set_visible(spine_vis[key])
                spine.set_edgecolor("k")
                spine.set_linewidth(0.5)

            while len(self.cids) > 0:
                cid = self.cids.pop(-1)
                self.f.canvas.mpl_disconnect(cid)

        self.clear_annotations()

        for a, visQ in self._artists_visible.items():
            a.set_visible(visQ)
        self._artists_visible.clear()

        # apply changes to the visibility state of the axes
        # do this at the end since axes might also be artists!
        for ax, val in self._ax_visible.items():
            ax.set_visible(val)

            # remember any axes that are intentionally hidden
            if not val:
                if ax in self.m.BM._bg_artists[self.m.BM.bg_layer]:
                    self.m.BM._hidden_axes.add(ax)
            else:
                if ax in self.m.BM._hidden_axes:
                    self.m.BM._hidden_axes.remove(ax)

        self._ax_visible.clear()

        # do this at the end!
        self._modifier_pressed = False
        self.m._ignore_cb_events = False

        self.m.BM._refetch_bg = True
        self.f.canvas.draw()
        self.m.BM.update()

    def _make_draggable(self):
        # all ordinary callbacks will not execute if" self._modifier_pressed" is True!
        print("EOmaps: Making axis draggable...")

        # remember the visibility state of the axes
        # do this as the first thing since axes might be artists as well!
        for ax in self.all_axes:
            self._ax_visible[ax] = ax.get_visible()

        # make all artists invisible (and remember their visibility state for later)
        for l in self.m.BM._bg_artists.values():
            for a in l:
                self._artists_visible[a] = a.get_visible()
                a.set_visible(False)

        # remember which spines were visible before
        self._spines_visible = self.get_spines_visible()
        self._frameon = [i.get_frame_on() for i in self.all_axes]

        self._modifier_pressed = True
        self.m._ignore_cb_events = True

        for ax in self.all_axes:
            if ax not in self.m.BM._bg_artists[self.m.BM.bg_layer]:
                continue
            ax.set_visible(True)

            ax.set_frame_on(True)
            for spine in ax.spines.values():
                spine.set_visible(True)

        self._color_axes()

        if len(self.cids) == 0:
            self.cids.append(self.f.canvas.mpl_connect("scroll_event", self.cb_scroll))
            self.cids.append(
                self.f.canvas.mpl_connect("button_press_event", self.cb_pick)
            )
            self.cids.append(
                self.f.canvas.mpl_connect("motion_notify_event", self.cb_move)
            )

            self.cids.append(
                self.f.canvas.mpl_connect("key_press_event", self.cb_move_with_key)
            )

        self.m.BM.fetch_bg()
        self.set_annotations()
        self.f.canvas.draw()


# taken from https://matplotlib.org/stable/tutorials/advanced/blitting.html#class-based-example
class BlitManager:
    def __init__(self, m):
        """
        Parameters
        ----------
        canvas : FigureCanvasAgg
            The canvas to work with, this only works for sub-classes of the Agg
            canvas which have the `~FigureCanvasAgg.copy_from_bbox` and
            `~FigureCanvasAgg.restore_region` methods.

        animated_artists : Iterable[Artist]
            List of the artists to manage
        """

        self._m = m

        self._bg = None
        self._artists = defaultdict(list)

        self._bg_artists = defaultdict(list)
        self._bg_layers = dict()

        # grab the background on every draw
        self.cid = self.canvas.mpl_connect("draw_event", self.on_draw)

        self._after_update_actions = []
        self._after_restore_actions = []
        self._bg_layer = 0

        self._artists_to_clear = defaultdict(list)

        self._hidden_axes = set()

        self._refetch_bg = True

        # TODO these activate some crude fixes for jupyter notebook and webagg
        # backends... proper fixes would be nice
        self._mpl_backend_blit_fix = any(
            i in plt.get_backend().lower() for i in ["webagg", "nbagg"]
        )

        # self._mpl_backend_force_full = any(
        #     i in plt.get_backend().lower() for i in ["nbagg"]
        # )
        # recent fixes seem to take care of this nbagg issue...
        self._mpl_backend_force_full = False
        self._mpl_backend_blit_fix = False

        self._on_layer_change = dict()
        self._on_layer_activation = defaultdict(dict)

    @property
    def canvas(self):
        return self._m.figure.f.canvas

    def _do_on_layer_change(self, layer):
        # general callbacks executed on any layer change
        if len(self._on_layer_change) > 0:
            actions = list(self._on_layer_change)
            for action in actions:
                action(self._on_layer_change[action], layer)

        # individual callables executed if a specific layer is activated
        activate_action = self._on_layer_activation.get(layer, None)
        if activate_action is not None:
            actions = list(activate_action)
            for action in actions:
                action(activate_action[action], layer)

    @property
    def bg_layer(self):
        return self._bg_layer

    @bg_layer.setter
    def bg_layer(self, val):
        self._bg_layer = val

        # a general callable to be called on every layer change
        self._do_on_layer_change(layer=val)

        # hide all colorbars that are not no the visible layer
        for m in [self._m.parent, *self._m.parent._children]:
            if getattr(m, "_colorbar", None) is not None:
                [layer, cbgs, ax_cb, ax_cb_plot, orientation, cb] = m._colorbar

                if layer != val:
                    ax_cb.set_visible(False)
                    ax_cb_plot.set_visible(False)
                else:
                    ax_cb.set_visible(True)
                    ax_cb_plot.set_visible(True)

        # self.canvas.flush_events()
        self._clear_temp_artists("on_layer_change")
        # self.fetch_bg(self._bg_layer)

    def on_layer(self, func, layer=None, persistent=False, m=None):
        """
        Add callables that are executed whenever the visible layer changes.

        Parameters
        ----------
        func : callable
            The callable to use.
            The call-signature is:

            >>> def func(m, l):
            >>>    # m... the Maps-object
            >>>    # l... the name of the layer


        layer : str or None, optional
            - If str: The function will only be called if the specified layer is
              activated.
            - If None: The function will be called on any layer-change.

            The default is None.
        persistent : bool, optional
            Indicator if the function should be called only once (False) or if it
            should be called whenever a layer is activated.
            The default is False.


        """
        if m is None:
            m = self._m

        if layer is None:
            if not persistent:

                def remove_decorator(func):
                    def inner(*args, **kwargs):
                        try:
                            func(*args, **kwargs)
                            if inner in self._on_layer_change[layer]:
                                self._on_layer_change[layer].pop(inner)
                        except IndexError:
                            pass

                    return inner

                func = remove_decorator(func)

            self._on_layer_change[func] = m

        else:
            if not persistent:

                def remove_decorator(func):
                    def inner(*args, **kwargs):
                        try:
                            func(*args, **kwargs)
                            if inner in self._on_layer_activation[layer]:
                                self._on_layer_activation[layer].pop(inner)
                        except IndexError:
                            pass

                    return inner

                func = remove_decorator(func)

            self._on_layer_activation[layer][func] = m

    def _refetch_layer(self, layer):
        if layer == "all":
            self._refetch_bg = True
        else:
            if layer in self._bg_layers:
                del self._bg_layers[layer]

    def fetch_bg(self, layer=None, bbox=None, overlay=None):
        # add this to the zorder of the overlay-artists prior to plotting
        # to ensure that they appear on top of other artists

        overlay_zorder_bias = 1000

        cv = self.canvas
        if layer is None:
            layer = self.bg_layer

        if overlay is None:
            overlay_name, overlay_layers = "", []
        else:
            overlay_name, overlay_layers = overlay

        for l in overlay_layers:
            self._do_on_layer_change(l)

        allartists = list(chain(*(self._bg_artists[i] for i in [layer, "all"])))
        allartists.sort(key=lambda x: getattr(x, "zorder", -1))

        overlay_artists = list(chain(*(self._bg_artists[i] for i in overlay_layers)))
        overlay_artists.sort(key=lambda x: getattr(x, "zorder", -1))

        for a in overlay_artists:
            a.zorder += overlay_zorder_bias

        allartists = allartists + overlay_artists

        # check if all artists are stale, and if so skip re-fetching the background
        # (only if also the axis extent is the same!)
        newbg = any(art.stale for art in allartists)

        # don't re-fetch the background if it is not necessary
        if (
            (not newbg)
            and (self._bg_layers.get(layer, None) is not None)
            and (
                (overlay_name == "")
                or (self._bg_layers.get(overlay_name, None) is not None)
            )
        ):
            return

        if bbox is None:
            bbox = cv.figure.bbox

        # temporarily disconnect draw-event callback to avoid recursion
        # while we re-draw the artists

        cv.mpl_disconnect(self.cid)

        if not self._m._draggable_axes._modifier_pressed:
            # make all artists of the corresponding layer visible
            for l in self._bg_artists:
                if l not in [layer, "all", *overlay_layers]:
                    # artists on "all" are always visible!
                    # make all artists of other layers are invisible
                    for art in self._bg_artists[l]:
                        art.set_visible(False)

            for art in allartists:
                if art not in self._hidden_axes:
                    art.set_visible(True)

            cv._force_full = True
            cv.draw()

        if overlay_layers:
            self._bg_layers[overlay_name] = cv.copy_from_bbox(bbox)
        else:
            self._bg_layers[layer] = cv.copy_from_bbox(bbox)

        self.cid = cv.mpl_connect("draw_event", self.on_draw)

        for a in overlay_artists:
            a.zorder -= overlay_zorder_bias

        self._refetch_bg = False

    def on_draw(self, event):
        """Callback to register with 'draw_event'."""
        cv = self.canvas

        if event is not None:
            if event.canvas != cv:
                raise RuntimeError
        try:
            # reset all background-layers and re-fetch the default one
            if self._refetch_bg:
                self._bg_layers = dict()
            if self.bg_layer not in self._bg_layers:
                self.fetch_bg()

            # workaround for nbagg backend to avoid glitches
            # it's slow but at least it works...
            # check progress of the following issuse
            # https://github.com/matplotlib/matplotlib/issues/19116
            if self._mpl_backend_blit_fix:
                self.update()
            else:
                self.update(blit=False)

        except Exception:
            # we need to catch exceptions since QT does not like them...
            pass

    def add_artist(self, art):
        """
        Add an artist to be managed.

        Parameters
        ----------
        art : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        layer : bool
            The layer number
        """
        layer = art.get_zorder()

        if art.figure != self.canvas.figure:
            raise RuntimeError
        if art in self._artists[layer]:
            return
        else:
            art.set_animated(True)
            self._artists[layer].append(art)

    def add_bg_artist(self, art, layer=0):
        """
        Add a background-artist to be managed.
        (Background artists are only updated on zoom-events...
         they are NOT animated!!)

        Parameters
        ----------
        art : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        layer : int or str
            The layer name at which the artist should be drawn.

            - If "all": the corresponding feature will be added to ALL layers

            The default is 0.
        """

        if not any(m.layer == layer for m in (self._m, *self._m._children)):
            print(f"creating a new Maps-object for the layer {layer}")
            self._m.new_layer(layer)

        if art.figure != self.canvas.figure:
            raise RuntimeError

        if art in self._bg_artists[layer]:
            print(f"EOmaps: Background-artist {art} already added")
            return

        # art.set_animated(True)
        self._bg_artists[layer].append(art)
        self._m.BM._refetch_layer(layer)

    def remove_bg_artist(self, art, layer=None):
        if layer is None:
            for key, val in self._bg_artists.items():
                if art in val:
                    art.set_animated(False)
                    val.remove(art)
        else:
            if art in self._bg_artists[layer]:
                art.set_animated(False)
                self._bg_artists[layer].remove(art)

    def remove_artist(self, art, layer=None):
        if layer is None:
            for key, val in self._artists.items():
                if art in val:
                    art.set_animated(False)
                    val.remove(art)
        else:
            if art in self._artists[layer]:
                art.set_animated(False)
                self._artists[layer].remove(art)

    def _draw_animated(self, layers=None, artists=None):
        """
        Draw animated artists

        - if layers is None and artists is None: all layers will be re-drawn
        - if layers is not None: all artists from the selected layers will be re-drawn
        - if artists is not None: all provided artists will be redrawn

        """
        fig = self.canvas.figure

        if layers is None and artists is None:
            # redraw all layers
            for l in sorted(list(self._artists)):
                for a in self._artists[l]:
                    fig.draw_artist(a)
        else:
            if layers is not None:
                # redraw artists from the selected layers
                for l in layers:
                    for a in self._artists[l]:
                        fig.draw_artist(a)
            if artists is not None:
                # redraw provided artists
                for a in artists:
                    fig.draw_artist(a)

    def _clear_temp_artists(self, method):
        if method == "on_layer_change":
            # clear all artists from "on_layer_change" list irrespective of the method
            allmethods = [i for i in self._artists_to_clear if i != method]
            for art in self._artists_to_clear[method]:
                for met in allmethods:

                    if art in self._artists_to_clear[met]:
                        art.set_visible(False)
                        self.remove_artist(art)
                        art.remove()
                        self._artists_to_clear[met].remove(art)
            del self._artists_to_clear[method]

            # always clear all temporary "pick" artists on a layer-change
            for method in ["pick"]:
                while len(self._artists_to_clear[method]) > 0:
                    art = self._artists_to_clear[method].pop(-1)
                    art.set_visible(False)
                    self.remove_artist(art)
                    art.remove()
                    if art in self._artists_to_clear["on_layer_change"]:
                        self._artists_to_clear["on_layer_change"].remove(art)
                del self._artists_to_clear[method]

        else:
            while len(self._artists_to_clear[method]) > 0:
                art = self._artists_to_clear[method].pop(-1)
                art.set_visible(False)
                self.remove_artist(art)
                art.remove()
                if art in self._artists_to_clear["on_layer_change"]:
                    self._artists_to_clear["on_layer_change"].remove(art)
            del self._artists_to_clear[method]

    def update(
        self,
        layers=None,
        bbox_bounds=None,
        bg_layer=None,
        artists=None,
        clear=False,
        blit=True,
    ):
        """
        Update the screen with animated artists.

        Parameters
        ----------
        layers : list, optional
            The layers to redraw (if None and artists is None, all layers will be redrawn).
            The default is None.
        bbox_bounds : tuple, optional
            the blit-region bounds to update. The default is None.
        bg_layer : int, optional
            the background-layer number. The default is None.
        artists : list, optional
            A list of artists to update.
            If provided NO layer will be automatically updated!
            The default is None.
        """
        cv = self.canvas
        if (cv.toolbar is not None) and cv.toolbar.mode != "":
            # only re-draw artists during toolbar-actions (e.g. pan/zoom)
            # this avoids a glitch with animated artists during pan/zoom events
            self._draw_animated(layers=layers, artists=artists)
            if self._mpl_backend_blit_fix:
                cv.blit()
            return

        fig = cv.figure

        if bg_layer is None:
            bg_layer = self.bg_layer

        # paranoia in case we missed the draw event,
        if bg_layer not in self._bg_layers or self._bg_layers[bg_layer] is None:
            self.on_draw(None)
        else:
            if clear:
                self._clear_temp_artists(clear)

            # restore the background
            cv.restore_region(self._bg_layers[bg_layer])

            # draw all of the animated artists
            while len(self._after_restore_actions) > 0:
                action = self._after_restore_actions.pop(0)
                action()

            self._draw_animated(layers=layers, artists=artists)

            if blit:
                # workaround for nbagg backend to avoid glitches
                # it's slow but at least it works...
                # check progress of the following issuse
                # https://github.com/matplotlib/matplotlib/issues/19116
                if self._mpl_backend_force_full:
                    cv._force_full = True

                if bbox_bounds is not None:

                    class bbox:
                        bounds = bbox_bounds

                    cv.blit(bbox)
                else:
                    # update the GUI state
                    cv.blit(fig.bbox)

            # execute all actions registered to be called after blitting
            while len(self._after_update_actions) > 0:
                action = self._after_update_actions.pop(0)
                action()

        # let the GUI event loop process anything it has to do
        # don't do this! it is causing infinit loops
        # cv.flush_events()

    def _get_overlay_name(self, layer=None, bg_layer=None):
        if layer is None:
            layer = []
        if bg_layer is None:
            bg_layer = self.bg_layer

        return "__overlay_" + str(bg_layer) + "_" + "_".join(map(str, layer))

    def _get_restore_bg_action(self, layer, bbox_bounds=None):
        """
        Update a part of the screen with a different background
        (intended as after-restore action)

        bbox_bounds = (x, y, width, height)
        """

        if bbox_bounds is None:
            bbox_bounds = self.canvas.figure.bbox.bounds

        name = self._get_overlay_name(bg_layer=layer)

        def action():
            if self.bg_layer == layer:
                return

            x0, y0, w, h = bbox_bounds

            initial_layer = self.bg_layer
            if name not in self._bg_layers:
                # fetch the required background layer
                if not isinstance(layer, (list, tuple)):
                    layers = [layer]
                else:
                    layers = layer

                self.fetch_bg(self._bg_layer, overlay=(name, layers))

                self.fetch_bg(initial_layer)
                self._m.show_layer(initial_layer)

            # restore the region of interest
            self.canvas.restore_region(
                self._bg_layers[name],
                bbox=(
                    x0,
                    self.canvas.figure.bbox.height - y0 - h,
                    x0 + w,
                    self.canvas.figure.bbox.height - y0,
                ),
                xy=(0, 0),
            )

        return action

    def _get_overlay_bg_action(self, layer, bbox_bounds=None):
        """
        Overlay a part of the screen with a different background
        (intended as after-restore action)

        bbox_bounds = (x, y, width, height)
        """
        if not isinstance(layer, (list, tuple)):
            layer = [layer]

        if bbox_bounds is None:
            bbox_bounds = self.canvas.figure.bbox.bounds

        if not hasattr(self, "_last_overlay_layer"):
            self._last_overlay_layer = ""

        def action():
            name = self._get_overlay_name(layer, bg_layer=self.bg_layer)

            if self.bg_layer == layer:
                return

            x0, y0, w, h = bbox_bounds

            initial_layer = self.bg_layer
            if name not in self._bg_layers:
                # fetch the required background layer (assigned as <name>)
                self.fetch_bg(initial_layer, overlay=(name, layer))
                self._m.show_layer(initial_layer)

            # restore the region of interest
            if name in self._bg_layers:
                self.canvas.restore_region(
                    self._bg_layers[name],
                    bbox=(
                        x0,
                        self.canvas.figure.bbox.height - y0 - h,
                        x0 + w,
                        self.canvas.figure.bbox.height - y0,
                    ),
                    xy=(0, 0),
                )

        return action

""" a collection of useful helper-functions """
from itertools import tee

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from collections import defaultdict
from matplotlib.transforms import Bbox
import matplotlib.pyplot as plt


def pairwise(iterable, pairs=2):
    """
    a generator to return n consecutive values from an iterable, e.g.:

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

        if method == 0:
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
        if method == 1:
            if self._cb_picked:
                if self._m_picked._orientation == "vertical":
                    ratio = (
                        self._m_picked.figure.ax_cb_plot.bbox.height
                        / self._m_picked.figure.ax_cb.bbox.height
                    )
                elif self._m_picked._orientation == "horizontal":
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
                    vis = not self._m_picked.figure.ax_cb_plot.get_visible()
                    self._m_picked.figure.ax_cb_plot.set_visible(vis)
                elif key == "down":
                    # toggle ax_cb and make the ticks visible
                    vis = not self._m_picked.figure.ax_cb.get_visible()
                    self._m_picked.figure.ax_cb.set_visible(vis)

                # fix the visible ticks
                if self._m_picked.figure.ax_cb.get_visible() is False:
                    if self._m_picked._orientation == "horizontal":
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
                    elif self._m_picked._orientation == "vertical":
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
                    if self._m_picked._orientation == "horizontal":
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
                    elif self._m_picked._orientation == "vertical":
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
        self.m.BM.update(artists=self._ax_picked + self._annotations)

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
                if self._m_picked._orientation == "vertical":
                    b = [bbox.x0, bbox.y0, bbox.width, b[3] + bbox.height]
                elif self._m_picked._orientation == "horizontal":
                    b = [bbox.x0, bbox.y0, b[2] + bbox.width, bbox.height]

        if (
            self._cb_picked
            and (self._m_picked is not None)
            and (self._ax_picked is not None)
        ):
            self._m_picked.figure.set_colorbar_position(b)

        self.set_annotations()
        self.m.BM.update(artists=self._ax_picked + self._annotations)

    def _color_axes(self):
        for ax in self.all_axes:
            ax.set_frame_on(True)
            for spine in ax.spines.values():
                spine.set_edgecolor("red")
                spine.set_linewidth(2)

        if self._ax_picked is not None:
            for ax in self._ax_picked:
                if ax is None:
                    continue
                for spine in ax.spines.values():
                    spine.set_edgecolor("green")
                    spine.set_linewidth(2)

    def cb_pick(self, event):

        if not self._modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        eventax = event.inaxes

        if eventax not in self.all_axes:
            # TODO this needs some update...
            # check if we clicked on a hidden ax, and if so make it visible again
            hidden_ax, hidden_ann = None, None
            for ax, ann in zip(self._hiddenax, self._annotations):
                bbox = ax.bbox
                if (
                    (event.x > bbox.x0)
                    & (event.x < bbox.x1)
                    & (event.y > bbox.y0)
                    & (event.y < bbox.y1)
                ):
                    hidden_ax = ax
                    hidden_ann = ann
                    break
            if hidden_ax is not None:
                hidden_ax.set_visible(True)
                hidden_ann.set_visible(False)
                self.m.BM.update(artists=[hidden_ax] + self._annotations)
                self.set_annotations()
                return

            # if no axes is clicked "unpick" previously picked axes
            prev_pick = self._ax_picked
            if prev_pick is None:
                # if there was no ax picked there's nothing to do...
                return

            self._ax_picked = None
            self._m_picked = None
            self._cb_picked = False
            self._color_axes()
            # make previously picked axes visible again and fetch the background
            if prev_pick is not None:
                for ax in prev_pick:
                    if ax not in self._hiddenax:
                        ax.set_visible(True)

            self.m.BM.fetch_bg()
            self.m.BM.update(
                layers=[self.m.layer], artists=prev_pick + self._annotations
            )
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

        if self._m_picked is _m_picked and self._cb_picked == _cb_picked:
            return

        self._ax_picked = _ax_picked
        self._m_picked = _m_picked
        self._cb_picked = _cb_picked

        self._color_axes()

        for ax in self._ax_picked:
            ax.set_visible(False)
        self.m.BM.fetch_bg()
        for ax in self._ax_picked:
            if ax not in self._hiddenax:
                ax.set_visible(True)

        self.set_annotations()
        self.m.BM.update(
            layers=[self.m.layer], artists=self._ax_picked + self._annotations
        )

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
                if self._m_picked._orientation == "vertical":
                    b = [
                        pos.x0 - wstep / 2,
                        pos.y0 - hstep / 2,
                        pos.width + wstep,
                        b[3] + pos.height + hstep,
                    ]
                elif self._m_picked._orientation == "horizontal":
                    b = [
                        pos.x0 - wstep / 2,
                        pos.y0 - hstep / 2,
                        b[2] + pos.width + wstep,
                        pos.height + hstep,
                    ]

        if self._cb_picked and self._m_picked is not None:
            self._m_picked.figure.set_colorbar_position(b)

        self._color_axes()
        self.m.BM.update(artists=self._ax_picked + self._annotations)

    def cb_key_press(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        if event.key == self.modifier:
            if self._modifier_pressed:
                self._undo_draggable()
            else:
                self._make_draggable()

    def _undo_draggable(self):
        self._modifier_pressed = False

        print("EOmaps: Making axes interactive again")
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
        self.m.BM.fetch_bg()
        self.f.canvas.draw()

    def _make_draggable(self):
        # all ordinary callbacks will not execute if" self._modifier_pressed" is True!

        # remember which spines were visible before
        self._spines_visible = self.get_spines_visible()
        self._frameon = [i.get_frame_on() for i in self.all_axes]

        self._modifier_pressed = True
        print("EOmaps: Making axis draggable")

        for ax in self.all_axes:
            ax.set_frame_on(True)
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_edgecolor("red")
                spine.set_linewidth(2)

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
        self.m.BM.update(layers=[self.m.layer], artists=self._annotations)
        # self.f.canvas.draw()


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
        self._layers = defaultdict(list)

        self._bg_artists = defaultdict(list)
        self._bg_layers = dict()

        # grab the background on every draw
        self.cid = self.canvas.mpl_connect("draw_event", self.on_draw)

        self._after_update_actions = []
        self._after_restore_actions = []
        self._bg_layer = 0

        self._artists_to_clear = defaultdict(list)

        self._refetch_bg = True

    @property
    def canvas(self):
        return self._m.figure.f.canvas

    @property
    def bg_layer(self):
        return self._bg_layer

    @bg_layer.setter
    def bg_layer(self, val):
        self._bg_layer = val

    def fetch_bg(self, layer=None, bbox=None):
        cv = self.canvas

        if layer is None:
            layer = self.bg_layer
        if bbox is None:
            bbox = cv.figure.bbox

        # make all artists of the corresponding layer visible
        for art in self._bg_artists[layer]:
            art.set_visible(True)

        for l in self._bg_artists:
            if l != layer:
                # make all artists of the corresponding layer visible
                for art in self._bg_artists[l]:
                    art.set_visible(False)

        # temporarily disconnect draw-event callback to avoid recursion
        # while we re-draw the artists
        cv.mpl_disconnect(self.cid)
        cv.draw()
        self.cid = cv.mpl_connect("draw_event", self.on_draw)

        self._bg_layers[layer] = cv.copy_from_bbox(bbox)
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
                self.fetch_bg(self.bg_layer)
            else:
                self.fetch_bg(self.bg_layer)

            # do an update but don't clear temporary artists!
            # (they are cleared on clicks only)
            self.update(clear=False, blit=False)
        except Exception:
            pass

    def add_artist(self, art, layer=0):
        """
        Add an artist to be managed.

        Parameters
        ----------
        art : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        bottom : bool
            Indicator if the artist should be added on top(False) or bottom(True)
        """
        if art.figure != self.canvas.figure:
            raise RuntimeError
        if art in self._layers[layer]:
            return
        else:
            art.set_animated(True)
            self._layers[layer].append(art)

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
        bottom : bool
            Indicator if the artist should be added on top(False) or bottom(True)
        """
        if art.figure != self.canvas.figure:
            raise RuntimeError

        if art in self._bg_artists[layer]:
            print(f"EOmaps: Background-artist {art} already added")
        else:
            self._bg_artists[layer].append(art)

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
            for key, val in self._layers.items():
                if art in val:
                    art.set_animated(False)
                    val.remove(art)
        else:
            if art in self._layers[layer]:
                art.set_animated(False)
                self._layers[layer].remove(art)

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
            for l in sorted(list(self._layers)):
                for a in self._layers[l]:
                    fig.draw_artist(a)
        else:
            if layers is not None:
                # redraw artists from the selected layers
                for l in layers:
                    for a in self._layers[l]:
                        fig.draw_artist(a)
            if artists is not None:
                # redraw provided artists
                for a in artists:
                    fig.draw_artist(a)

    def _clear_temp_artists(self, method):
        while len(self._artists_to_clear[method]) > 0:
            art = self._artists_to_clear[method].pop(-1)
            art.set_visible(False)
            self.remove_artist(art)
            art.remove()
        del self._artists_to_clear[method]

    def update(
        self,
        layers=None,
        bbox_bounds=None,
        bg_layer=None,
        artists=None,
        clear="click",
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

    def _get_restore_bg_action(self, layer, bbox_bounds=None):
        """
        Update a part of the screen with a different background
        (intended as after-restore action)

        bbox_bounds = (x, y, width, height)
        """
        if bbox_bounds is None:
            bbox_bounds = self.canvas.figure.bbox.bounds

        def action():
            x0, y0, w, h = bbox_bounds

            if layer not in self._bg_layers:
                # fetch the required background layer
                self.fetch_bg(layer)
                self.canvas.restore_region(self._bg_layers[self.bg_layer])

            # restore the region of interest
            self.canvas.restore_region(
                self._bg_layers[layer],
                bbox=(
                    x0,
                    self.canvas.figure.bbox.height - y0 - h,
                    x0 + w,
                    self.canvas.figure.bbox.height - y0,
                ),
                xy=(0, 0),
            )

        return action

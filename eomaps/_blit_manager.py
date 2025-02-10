# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""The BlitManager used to handle drawing and caching of backgrounds."""

import logging
from contextlib import ExitStack, contextmanager
from functools import lru_cache
from itertools import chain
from weakref import WeakSet

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.spines import Spine
from matplotlib.transforms import Bbox

_log = logging.getLogger(__name__)


class LayerParser:
    @staticmethod
    def _parse_single_layer_str(layer):
        """
        Parse a single layer-string (with optional transparency assignment).

        Parameters
        ----------
        layer : str
            A layer-string (with transparency provided in curly brackets).

        Returns
        -------
        name: str
            The name of the layer.
        alpha:
            The transparency of the layer.

        """
        # split transparency
        t_split = layer.find("{")
        if t_split > 0:
            name = layer[:t_split]
            alpha = layer[t_split + 1 :]
            if not alpha.endswith("}"):
                raise TypeError(
                    f"EOmaps: unable to parse multilayer-transparency for '{layer}'"
                )
            return name, float(alpha[:-1])
        else:
            return layer, 1

    @classmethod
    def _parse_multi_layer_str(cls, layer=None):
        layers, alphas = zip(*map(cls._parse_single_layer_str, layer.split("|")))
        return list(layers), list(alphas)

    @classmethod
    def _layer_is_subset(cls, layer1, layer2):
        """
        Return True if combined layer-name 'layer2' is a subset of 'layer1'.

        - Transparency assignments are stripped off before comparison

        Parameters
        ----------
        layer1, layer2 : str
            The combined layer-names to check.

        Returns
        -------
        subset: bool
            True if layer2 is a subset of layer1, False otherwise

        """
        # get a list of the currently visible layers
        layers1, _ = cls._parse_multi_layer_str(layer1)
        layers2, _ = cls._parse_multi_layer_str(layer2)

        return set(layers1).issubset(layers2)

    @staticmethod
    def _get_combined_layer_name(*args):
        """
        Create a combine layer name from layer-names or tuples (name, transparency).

        Parameters
        ----------
        *args : str or tuple
            The layers to combine. (e.g. `"A"`, `"B"` or `("A", .5)`, `("B", .23)`, ...)

        Returns
        -------
        str
            The combined layer-name.

        """
        try:
            combnames = []
            for i in args:
                if isinstance(i, str):
                    combnames.append(i)
                elif isinstance(i, (list, tuple)):
                    assert (
                        len(i) == 2
                        and isinstance(i[0], str)
                        and i[1] >= 0
                        and i[1] <= 1
                    ), (
                        f"EOmaps: unable to identify the layer-assignment: {i} .\n"
                        "You can provide either a single layer-name as string, a list "
                        "of layer-names or a list of tuples of the form: "
                        "(< layer-name (str) >, < layer-transparency [0-1] > )"
                    )

                    if i[1] < 1:
                        combnames.append(i[0] + "{" + str(i[1]) + "}")
                    else:
                        combnames.append(i[0])
                else:
                    raise TypeError(
                        f"EOmaps: unable to identify the layer-assignment: {i} .\n"
                        "You can provide either a single layer-name as string, a list "
                        "of layer-names or a list of tuples of the form: "
                        "(< layer-name (str) >, < layer-transparency [0-1] > )"
                    )
            return "|".join(combnames)
        except Exception:
            raise TypeError(f"EOmaps: Unable to combine the layer-names {args}")

    @staticmethod
    def _check_layer_name(layer):
        if not isinstance(layer, str):
            _log.info("EOmaps: All layer-names are converted to strings!")
            layer = str(layer)

        if layer.startswith("__") and not layer.startswith("__inset_"):
            raise TypeError(
                "EOmaps: Layer-names starting with '__' are reserved "
                "for internal use and cannot be used as Maps-layer-names!"
            )

        reserved_symbs = {
            # "|": (
            #     "It is used as a separation-character to combine multiple "
            #     "layers (e.g. m.show_layer('A|B') will overlay the layer 'B' "
            #     "on top of 'A'."
            # ),
            "{": (
                "It is used to specify transparency when combining multiple "
                "layers (e.g. m.show_layer('A|B{0.5}') will overlay the layer "
                "'B' with 50% transparency on top of the layer 'A'."
            ),
        }

        reserved_symbs["}"] = reserved_symbs["{"]

        for symb, explanation in reserved_symbs.items():
            if symb in layer:
                raise TypeError(
                    f"EOmaps: The symbol '{symb}' is not allowed in layer-names!\n"
                    + explanation
                )

        return layer


# taken from https://matplotlib.org/stable/tutorials/advanced/blitting.html#class-based-example
class BlitManager(LayerParser):
    """Manager used to schedule draw events, cache backgrounds, etc."""

    _snapshot_on_update = False

    def __init__(self, m):
        """
        Manager used to schedule draw events, cache backgrounds, etc.

        Parameters
        ----------
        canvas : FigureCanvasAgg
            The canvas to work with, this only works for sub-classes of the Agg
            canvas which have the `~FigureCanvasAgg.copy_from_bbox` and
            `~FigureCanvasAgg.restore_region` methods.

        animated_artists : Iterable[Artist]
            List of the artists to manage

        """
        self._disable_draw = False
        self._disable_update = False

        self._m = m
        self._bg_layer = self._m.layer

        self._artists = dict()

        self._bg_artists = dict()
        self._bg_layers = dict()

        self._pending_webmaps = dict()

        # the name of the layer at which all "unmanaged" artists are drawn
        self._unmanaged_artists_layer = "base"

        # grab the background on every draw
        self._cid_draw = self.canvas.mpl_connect("draw_event", self._on_draw_cb)

        self._after_update_actions = []
        self._after_restore_actions = []

        self._artists_to_clear = dict()

        self._hidden_artists = set()

        self._refetch_bg = True
        self._layers_to_refetch = set()

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

        # True = persistent, False = execute only once
        self._on_layer_change = {True: list(), False: list()}
        self._on_layer_activation = {True: dict(), False: dict()}

        self._on_add_bg_artist = list()
        self._on_remove_bg_artist = list()

        self._before_fetch_bg_actions = list()
        self._before_update_actions = list()

        self._refetch_blank = True
        self._blank_bg = None

        self._managed_axes = set()

        self._clear_on_layer_change = False

        self._on_layer_change_running = False

        # a weak set containing artists that should NOT be identified as
        # unmanaged artists
        self._ignored_unmanaged_artists = WeakSet()

    def _get_renderer(self):
        # don't return the renderer if the figure is saved.
        # in this case the normal draw-routines are used (see m.savefig) so there is
        # no need to trigger updates (also `canvas.get_renderer` is undefined for
        # pdf/svg exports since those canvas do not expose the renderer)
        # ... this is required to support vector format outputs!
        if self.canvas.is_saving():
            return None

        try:
            return self.canvas.get_renderer()
        except Exception:
            return None

    def _get_all_map_axes(self):
        maxes = {
            m.ax
            for m in (self._m.parent, *self._m.parent._children)
            if getattr(m, "_new_axis_map", False)
        }
        return maxes

    def _get_managed_axes(self):
        return (*self._get_all_map_axes(), *self._managed_axes)

    def _get_unmanaged_axes(self):
        # return a list of all axes that are not managed by the blit-manager
        # (to ensure that "unmanaged" axes are drawn as well)

        # EOmaps axes
        managed_axes = self._get_managed_axes()
        allaxes = set(self._m.f.axes)

        unmanaged_axes = allaxes.difference(managed_axes)
        return unmanaged_axes

    @property
    def figure(self):
        """The matplotlib figure instance."""
        return self._m.f

    @property
    def canvas(self):
        """The figure canvas instance."""
        return self.figure.canvas

    @contextmanager
    def _cx_on_layer_change_running(self):
        # a context-manager to avoid recursive on_layer_change calls
        try:
            self._on_layer_change_running = True
            yield
        finally:
            self._on_layer_change_running = False

    def _do_on_layer_change(self, layer, new=False):
        # avoid recursive calls to "_do_on_layer_change"
        # This is required in case the executed functions trigger actions that would
        # trigger "_do_on_layer_change" again which can result in a mixed-up order of
        # the scheduled functions.
        if self._on_layer_change_running is True:
            return

        # do not execute layer-change callbacks on private layer activation!
        if layer.startswith("__"):
            return

        with self._cx_on_layer_change_running():
            # only execute persistent layer-change callbacks if the layer changed!
            if new:
                # general callbacks executed on any layer change
                # persistent callbacks
                for f in reversed(self._on_layer_change[True]):
                    f(layer=layer)

            # single-shot callbacks
            # (execute also if the layer is already active)
            while len(self._on_layer_change[False]) > 0:
                try:
                    f = self._on_layer_change[False].pop(0)
                    f(layer=layer)
                except Exception as ex:
                    _log.error(
                        f"EOmaps: Issue during layer-change action: {ex}",
                        exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                    )

            sublayers, _ = self._parse_multi_layer_str(layer)
            if new:
                for l in sublayers:
                    # individual callables executed if a specific layer is activated
                    # persistent callbacks
                    for f in reversed(self._on_layer_activation[True].get(layer, [])):
                        f(layer=l)

            for l in sublayers:
                # single-shot callbacks
                single_shot_funcs = self._on_layer_activation[False].get(l, [])
                while len(single_shot_funcs) > 0:
                    try:
                        f = single_shot_funcs.pop(0)
                        f(layer=l)
                    except Exception as ex:
                        _log.error(
                            f"EOmaps: Issue during layer-change action: {ex}",
                            exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                        )

            # clear the list of pending webmaps once the layer has been activated
            if layer in self._pending_webmaps:
                self._pending_webmaps.pop(layer)

    @contextmanager
    def _without_artists(self, artists=None, layer=None):
        try:
            removed_artists = {layer: set(), "all": set()}
            if artists is None:
                yield
            else:
                for a in artists:
                    if a in self._artists.get(layer, []):
                        self.remove_artist(a, layer=layer)
                        removed_artists[layer].add(a)
                    elif a in self._artists.get("all", []):
                        self.remove_artist(a, layer="all")
                        removed_artists["all"].add(a)

                yield
        finally:
            for layer, artists in removed_artists.items():
                for a in artists:
                    self.add_artist(a, layer=layer)

    def _get_active_bg(self, exclude_artists=None):
        with self._without_artists(artists=exclude_artists, layer=self.bg_layer):
            # fetch the current background (incl. dynamic artists)
            self.update()

            with ExitStack() as stack:
                # get rid of the figure background patch
                # (done by putting the patch on the __BG__ layer!)

                # get rid of the axes background patch
                for ax_i in self._get_all_map_axes():
                    stack.enter_context(
                        ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                    )
                bg = self.canvas.copy_from_bbox(self.figure.bbox)

        return bg

    @property
    def bg_layer(self):
        """The currently visible layer-name."""
        return self._bg_layer

    @bg_layer.setter
    def bg_layer(self, val):
        if val == self._bg_layer:
            # in case the layer did not change, do nothing
            return

        # check if a new layer is activated (or added to a multi-layer)
        old_layers = set(self._parse_multi_layer_str(self._bg_layer)[0])
        new_layers = set(self._parse_multi_layer_str(val)[0])

        new = old_layers != new_layers

        # make sure we use a "full" update for webagg and ipympl backends
        # (e.g. force full redraw of canvas instead of a diff)
        self.canvas._force_full = True
        self._bg_layer = val

        # a general callable to be called on every layer change
        self._do_on_layer_change(layer=val, new=new)

        # hide all colorbars that are not on the visible layer
        for m in [self._m.parent, *self._m.parent._children]:
            layer_visible = self._layer_is_subset(val, m.layer)

            for cb in getattr(m, "_colorbars", []):
                cb._hide_singular_axes()

                if layer_visible:
                    if cb in self._hidden_artists:
                        self._hidden_artists.remove(cb)
                else:
                    if cb not in self._hidden_artists:
                        self._hidden_artists.add(cb)

        # hide all wms_legends that are not on the visible layer
        if hasattr(self._m.parent, "_wms_legend"):
            for layer, legends in self._m.parent._wms_legend.items():
                layer_visible = self._layer_is_subset(val, layer)

                if layer_visible:
                    for i in legends:
                        i.set_visible(True)
                else:
                    for i in legends:
                        i.set_visible(False)

        if self._clear_on_layer_change:
            self._clear_temp_artists("on_layer_change")

    @contextmanager
    def _cx_dont_clear_on_layer_change(self):
        # a context-manager to avoid clearing artists on layer-changes
        # (used in savefig to avoid clearing artists when re-fetching
        # layers with backgrounds)
        init_val = self._clear_on_layer_change
        try:
            self._clear_on_layer_change = False
            yield
        finally:
            self._clear_on_layer_change = init_val

    def on_layer(self, func, layer=None, persistent=False, m=None):
        """
        Add callables that are executed whenever the visible layer changes.

        NOTE: if m is None this function always falls back to the parent Maps-object!!

        Parameters
        ----------
        func : callable
            The callable to use.
            The call-signature is:

            >>> def func(m, layer):
            >>>    # m     ... the Maps-object
            >>>    # layer ... the name of the layer


        layer : str or None, optional
            - If str: The function will only be called if the specified layer is
              activated.
            - If None: The function will be called on any layer-change.

            The default is None.
        persistent : bool, optional
            Indicator if the function should be called only once (False) or if it
            should be called whenever a layer is activated.
            The default is False.
        m : eomaps.Maps
            The Maps-object to pass as argument to the function execution.
            If None, the parent Maps-object is used.

        """
        if m is None:
            m = self._m

        def cb(*args, **kwargs):
            func(m=m, *args, **kwargs)

        if _log.getEffectiveLevel() <= 10:
            logmsg = (
                f"Adding {'persistent' if persistent else 'single-shot'} "
                f"layer change action for: '{layer}'"
            )
            _log.debug(logmsg)

        if layer is None:
            self._on_layer_change[persistent].append(cb)
        else:
            # treat inset-map layers like normal layers
            if layer.startswith("__inset_"):
                layer = layer[8:]
            self._on_layer_activation[persistent].setdefault(layer, list()).append(cb)

    def _refetch_layer(self, layer):
        if layer == "all":
            # if the all layer changed, all backgrounds need a refetch
            self._refetch_bg = True
        else:
            # set any background that contains the layer for refetch
            self._layers_to_refetch.add(layer)

            for l in self._bg_layers:
                sublayers, _ = self._parse_multi_layer_str(l)
                if layer in sublayers:
                    self._layers_to_refetch.add(l)

    def _bg_artists_sort(self, art):
        sortp = []

        # ensure that inset-map artists are always drawn after all other artists
        if art.axes is not None:
            if art.axes.get_label() == "inset_map":
                sortp.append(1)
            else:
                sortp.append(0)

        sortp.append(getattr(art, "zorder", -1))
        return sortp

    def get_bg_artists(self, layer):
        """
        Get all (sorted) background artists assigned to a given layer-name.

        Parameters
        ----------
        layer : str
            The layer name for which artists should be fetched.

        Returns
        -------
        artists : list
            A list of artists on the specified layer, sorted with respect to the
            vertical stacking (layer-order / zorder).

        """
        artists = list()
        for l in np.atleast_1d(layer):
            # get all relevant artists for combined background layers
            l = str(l)  # w make sure we convert non-string layer names to string!

            # get artists defined on the layer itself
            # Note: it's possible to create explicit multi-layers and attach
            # artists that are only visible if both layers are visible! (e.g. "l1|l2")
            artists.extend(self._bg_artists.get(l, []))

            # make sure to also trigger drawing unmanaged artists on inset-maps!
            if l in (
                self._unmanaged_artists_layer,
                f"__inset_{self._unmanaged_artists_layer}",
            ):
                artists.extend(self._get_unmanaged_artists())

        # make the list unique but maintain order (dicts keep order for python>3.7)
        artists = dict.fromkeys(artists)
        # sort artists by zorder (respecting inset-map priority)
        artists = sorted(artists, key=self._bg_artists_sort)

        return artists

    def get_artists(self, layer):
        """
        Get all (sorted) dynamically updated artists assigned to a given layer-name.

        Parameters
        ----------
        layer : str
            The layer name for which artists should be fetched.

        Returns
        -------
        artists : list
            A list of artists on the specified layer, sorted with respect to the
            vertical stacking (layer-order / zorder).

        """

        artists = list()
        for l in np.atleast_1d(layer):
            # get all relevant artists for combined background layers
            l = str(l)  # w make sure we convert non-string layer names to string!

            # get artists defined on the layer itself
            # Note: it's possible to create explicit multi-layers and attach
            # artists that are only visible if both layers are visible! (e.g. "l1|l2")
            artists.extend(self._artists.get(l, []))

        # make the list unique but maintain order (dicts keep order for python>3.7)
        artists = dict.fromkeys(artists)
        # sort artists by zorder (respecting inset-map priority)
        artists = sorted(artists, key=self._bg_artists_sort)

        return artists

    def _layer_visible(self, layer):
        """
        Return True if the layer is currently visible.

        - layer is considered visible if all sub-layers of a combined layer are visible
        - transparency assignments do not alter the layer visibility

        Parameters
        ----------
        layer : str
            The combined layer-name to check. (e.g. 'A|B{.4}|C{.3}')

        Returns
        -------
        visible: bool
            True if the layer is currently visible, False otherwise

        """
        return layer == "all" or self._layer_is_subset(layer, self.bg_layer)

    @property
    def _get_active_layers_alphas(self):
        """
        Return the currently visible layers (and their associated transparencies)

        Returns
        -------
        layers, alphas: list of str, list of float
            2 lists of layer-names and associated global transparencies.

        """
        return self._parse_multi_layer_str(self.bg_layer)

    # cache the last 10 combined backgrounds to avoid re-combining backgrounds
    # on updates of interactive artists
    # cache is automatically cleared on draw if any layer is tagged for re-fetch!
    @lru_cache(10)
    def _combine_bgs(self, layer):
        layers, alphas = self._parse_multi_layer_str(layer)

        # make sure all layers are already fetched
        for l in layers:
            if l not in self._bg_layers:
                # execute actions on layer-changes
                # (to make sure all lazy WMS services are properly added)
                self._do_on_layer_change(layer=l, new=False)
                self.fetch_bg(l)

        renderer = self._get_renderer()
        # clear the renderer to avoid drawing on existing backgrounds
        renderer.clear()
        if renderer:
            gc = renderer.new_gc()
            gc.set_clip_rectangle(self.canvas.figure.bbox)

            x0, y0, w, h = self.figure.bbox.bounds
            for l, a in zip(layers, alphas):
                rgba = self._get_array(l, a=a)
                if rgba is None:
                    # to handle completely empty layers
                    continue
                renderer.draw_image(
                    gc,
                    int(x0),
                    int(y0),
                    rgba[int(y0) : int(y0 + h), int(x0) : int(x0 + w), :],
                )
            bg = renderer.copy_from_bbox(self._m.f.bbox)
            gc.restore()
            return bg

    def _get_array(self, l, a=1):
        if l not in self._bg_layers:
            return None
        rgba = np.array(self._bg_layers[l])[::-1, :, :]
        if a != 1:
            rgba = rgba.copy()
            rgba[..., -1] = (rgba[..., -1] * a).astype(rgba.dtype)
        return rgba

    def _get_background(self, layer, bbox=None, cache=False):
        if layer not in self._bg_layers:
            if "|" in layer:
                bg = self._combine_bgs(layer)
            else:
                self.fetch_bg(layer, bbox=bbox)
                bg = self._bg_layers[layer]
        else:
            bg = self._bg_layers[layer]

        if cache is True:
            # explicitly cache the layer
            # (for peek-layer callbacks to avoid re-fetching the layers all the time)
            self._bg_layers[layer] = bg

        return bg

    def _do_fetch_bg(self, layer, bbox=None):
        renderer = self._get_renderer()
        renderer.clear()

        if bbox is None:
            bbox = self.figure.bbox

        if "|" in layer:
            if layer not in self._bg_layers:
                self._combine_bgs(layer)
            return

        # update axes spines and patches since they are used to clip artists!
        for ax in self._get_all_map_axes():
            if "geo" in ax.spines:
                ax.spines["geo"]._adjust_location()
                ax.patch._adjust_location()

        # use contextmanagers to make sure the background patches are not stored
        # in the buffer regions!
        with ExitStack() as stack:
            if layer not in ["__BG__"]:
                # get rid of the axes background patches for all layers except
                # the __BG__ layer
                # (the figure background patch is on the "__BG__" layer)
                for ax_i in self._get_all_map_axes():
                    stack.enter_context(
                        ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                    )

            # execute actions before fetching new artists
            # (e.g. update data based on extent etc.)
            for action in self._before_fetch_bg_actions:
                action(layer=layer, bbox=bbox)

            # get all relevant artists to plot and remember zorders
            # self.get_bg_artists() already returns artists sorted by zorder!
            if layer in ["__SPINES__", "__BG__", "__inset___SPINES__"]:
                # avoid fetching artists from the "all" layer for private layers
                allartists = self.get_bg_artists(layer)
            else:
                if layer.startswith("__inset"):
                    allartists = self.get_bg_artists(["__inset_all", layer])
                else:
                    allartists = self.get_bg_artists(["all", layer])

            # check if all artists are not stale
            no_stale_artists = all(not art.stale for art in allartists)

            # don't re-fetch the background if it is not necessary
            if no_stale_artists and (self._bg_layers.get(layer, None) is not None):
                return

            if renderer:
                for art in allartists:
                    if art not in self._hidden_artists:
                        try:
                            art.draw(renderer)
                            art.stale = False
                        except Exception:
                            if _log.getEffectiveLevel() <= logging.DEBUG:
                                _log.error(
                                    "Unable to draw artist:"
                                    f"{art} ("
                                    f"figure={getattr(art, 'figure', '??')}, "
                                    f"axes={getattr(art, 'axes', '??')})"
                                )

                self._bg_layers[layer] = renderer.copy_from_bbox(bbox)

    def fetch_bg(self, layer=None, bbox=None):
        """
        Trigger fetching (and caching) the background for a given layer-name.

        Parameters
        ----------
        layer : str, optional
            The layer for which the background should be fetched.
            If None, the currently visible layer is fetched.
            The default is None.
        bbox : bbox, optional
            The region-boundaries (in figure coordinates) for which the background
            should be fetched (x0, y0, w, h). If None, the whole figure is fetched.
            The default is None.

        """

        if layer is None:
            layer = self.bg_layer

        if layer in self._bg_layers:
            # don't re-fetch existing layers
            # (layers get cleared automatically if re-draw is necessary)
            return

        with self._disconnect_draw():
            self._do_fetch_bg(layer, bbox)

    @contextmanager
    def _disconnect_draw(self):
        try:
            # temporarily disconnect draw-event callback to avoid recursion
            if self._cid_draw is not None:
                self.canvas.mpl_disconnect(self._cid_draw)
                self._cid_draw = None
            yield
        finally:
            # reconnect draw event
            if self._cid_draw is None:
                self._cid_draw = self.canvas.mpl_connect("draw_event", self._on_draw_cb)

    def _on_draw_cb(self, event):
        """Callback to register with 'draw_event'."""

        if self._disable_draw:
            return

        cv = self.canvas
        loglevel = _log.getEffectiveLevel()

        if hasattr(cv, "get_renderer") and not cv.is_saving():
            renderer = cv.get_renderer()
            if renderer is None:
                # don't run if no renderer is available
                return
        else:
            # don't run if no renderer is available
            # (this is true for svg export where mpl export routines
            # are used to avoid issues)
            if loglevel <= 5:
                _log.log(5, " not drawing")

            return

        if loglevel <= 5:
            _log.log(5, "draw")

        if event is not None:
            if event.canvas != cv:
                raise RuntimeError
        try:
            # reset all background-layers and re-fetch the default one
            if self._refetch_bg:
                self._bg_layers.clear()
                self._layers_to_refetch.clear()
                self._refetch_bg = False
                type(self)._combine_bgs.cache_clear()  # clear combined_bg cache

            else:
                # in case there is a stale (unmanaged) artists and the
                # stale-artist layer is attempted to be drawn, re-draw the
                # cached background for the unmanaged-artists layer
                active_layers, _ = self._get_active_layers_alphas
                if self._unmanaged_artists_layer in active_layers and any(
                    a.stale for a in self._get_unmanaged_artists()
                ):
                    self._refetch_layer(self._unmanaged_artists_layer)
                    type(self)._combine_bgs.cache_clear()  # clear combined_bg cache

                # remove all cached backgrounds that were tagged for refetch
                while len(self._layers_to_refetch) > 0:
                    self._bg_layers.pop(self._layers_to_refetch.pop(), None)
                    type(self)._combine_bgs.cache_clear()  # clear combined_bg cache

            # workaround for nbagg backend to avoid glitches
            # it's slow but at least it works...
            # check progress of the following issues
            # https://github.com/matplotlib/matplotlib/issues/19116
            if self._mpl_backend_blit_fix:
                self.update()
            else:
                self.update(blit=False)

            # re-draw indicator-shapes of active drawer
            # (to show indicators during zoom-events)
            active_drawer = getattr(self._m.parent, "_active_drawer", None)
            if active_drawer is not None:
                active_drawer.redraw(blit=False)

        except Exception:
            # we need to catch exceptions since QT does not like them...
            if loglevel <= 5:
                _log.log(5, "There was an error during draw!", exc_info=True)

    def add_artist(self, art, layer=None):
        """
        Add a dynamic-artist to be managed.
        (Dynamic artists are re-drawn on every update!)

        Parameters
        ----------
        art : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        layer : str or None, optional
            The layer name at which the artist should be drawn.

            - If "all": the corresponding feature will be added to ALL layers

            The default is None in which case the layer of the base-Maps object is used.
        """

        if art.figure != self.figure:
            raise RuntimeError(
                "EOmaps: The artist does not belong to the figure"
                "of this Maps-object!"
            )

        if layer is None:
            layer = self._m.layer

        # make sure all layers are converted to string
        layer = str(layer)

        self._artists.setdefault(layer, list())

        if art in self._artists[layer]:
            return
        else:
            art.set_animated(True)
            self._artists[layer].append(art)

            if isinstance(art, plt.Axes):
                self._managed_axes.add(art)

    def add_bg_artist(self, art, layer=None, draw=True):
        """
        Add a background-artist to be managed.
        (Background artists are only updated on zoom-events... they are NOT animated!)

        Parameters
        ----------
        art : Artist
            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        layer : str or None, optional
            The layer name at which the artist should be drawn.

            - If "all": the corresponding feature will be added to ALL layers

            The default is None in which case the layer of the base-Maps object is used.
        draw : bool, optional
            If True, `figure.draw_idle()` is called after adding the artist.
            The default is True.
        """

        if layer is None:
            layer = self._m.layer

        # make sure all layer names are converted to string
        layer = str(layer)

        if art.figure != self.figure:
            raise RuntimeError

        # put all artist of inset-maps on dedicated layers
        if (
            getattr(art, "axes", None) is not None
            and art.axes.get_label() == "inset_map"
            and not layer.startswith("__inset_")
        ):
            layer = "__inset_" + str(layer)

        if layer in self._bg_artists and art in self._bg_artists[layer]:
            _log.info(
                f"EOmaps: Background-artist '{art}' already added on layer '{layer}'"
            )
            return

        art.set_animated(True)
        self._bg_artists.setdefault(layer, []).append(art)

        if isinstance(art, plt.Axes):
            self._managed_axes.add(art)

        # tag all relevant layers for refetch
        self._refetch_layer(layer)

        for f in self._on_add_bg_artist:
            f()

        if draw:
            self.canvas.draw_idle()

    def remove_bg_artist(self, art, layer=None, draw=True):
        """
        Remove a (background) artist from the map.

        Parameters
        ----------
        art : Artist
            The artist that should be removed.
        layer : str or None, optional
            If provided, the artist is only searched on the provided layer, otherwise
            all map layers are searched. The default is None.
        draw : bool, optional
            If True, `figure.draw_idle()` is called after removing the artist.
            The default is True.

        Note
        ----
        This only removes the artist from the blit-manager and does not call its
        remove method!

        """
        # handle the "__inset_" prefix of inset-map artists
        if (
            layer is not None
            and getattr(art, "axes", None) is not None
            and art.axes.get_label() == "inset_map"
            and not layer.startswith("__inset_")
        ):
            layer = "__inset_" + str(layer)

        removed = False
        if layer is None:
            layers = []
            for key, val in self._bg_artists.items():
                if art in val:
                    art.set_animated(False)
                    val.remove(art)

                    # remove axes from the managed_axes set as well!
                    if art in self._managed_axes:
                        self._managed_axes.remove(art)

                    removed = True
                    layers.append(key)
                layer = self._get_combined_layer_name(*layers)
        else:
            if layer not in self._bg_artists:
                return
            if art in self._bg_artists[layer]:
                art.set_animated(False)
                self._bg_artists[layer].remove(art)

                # remove axes from the managed_axes set as well!
                if art in self._managed_axes:
                    self._managed_axes.remove(art)

                removed = True

        if removed:
            for f in self._on_remove_bg_artist:
                f()

            # tag all relevant layers for refetch
            self._refetch_layer(layer)

        if draw:
            self.canvas.draw_idle()

    def remove_artist(self, art, layer=None):
        """
        Remove a (dynamically updated) artist from the blit-manager.

        Parameters
        ----------
        art : matplotlib.Artist
            The artist to remove.
        layer : str, optional
            The layer to search for the artist. If None, all layers are searched.
            The default is None.

        Note
        ----
        This only removes the artist from the blit-manager and does not call its
        remove method!

        """
        if layer is None:
            for key, layerartists in self._artists.items():
                if art in layerartists:
                    art.set_animated(False)
                    layerartists.remove(art)

                    # remove axes from the managed_axes set as well!
                    if art in self._managed_axes:
                        self._managed_axes.remove(art)

        else:
            if art in self._artists.get(layer, []):
                art.set_animated(False)
                self._artists[layer].remove(art)

                # remove axes from the managed_axes set as well!
                if art in self._managed_axes:
                    self._managed_axes.remove(art)
            else:
                _log.debug(f"The artist {art} is not on the layer '{layer}'")

    def _get_artist_zorder(self, a):
        try:
            return a.get_zorder()
        except Exception:
            _log.error(f"EOmaps: unalble to identify zorder of {a}... using 99")
            return 99

    def _draw_animated(self, layers=None, artists=None):
        """
        Draw animated artists

        - if layers is None and artists is None: active layer artists will be re-drawn
        - if layers is not None: all artists from the selected layers will be re-drawn
        - if artists is not None: all provided artists will be redrawn

        """
        fig = self.canvas.figure
        renderer = self._get_renderer()
        if renderer is None:
            return

        if layers is None:
            active_layers, _ = self._get_active_layers_alphas
            layers = [self.bg_layer, *active_layers]
        else:
            (layers,) = list(
                chain(*(self._parse_multi_layer_str(l)[0] for l in layers))
            )

        if artists is None:
            artists = []

        # always redraw artists from the "all" layer
        layers.append("all")

        # make the list unique but maintain order (dicts keep order for python>3.7)
        layers = list(dict.fromkeys(layers))

        # draw all "unmanaged" axes (e.g. axes that are found in the figure but
        # not in the blit-manager)
        # TODO would be nice to find a better way to handle this!
        # - NOTE: this must be done before drawing managed artists to properly support
        #   temporary artists on unmanaged axes!
        for ax in self._get_unmanaged_axes():
            ax.draw(renderer)

        # redraw artists from the selected layers and explicitly provided artists
        # (sorted by zorder for each layer)
        layer_artists = list(
            sorted(self._artists.get(layer, []), key=self._get_artist_zorder)
            for layer in layers
        )

        with ExitStack() as stack:
            # avoid drawing the background-patches of managed (dynamic) axes
            # since they might interfere with consecutive draws issued by callbacks
            for ax_i in self._managed_axes:
                stack.enter_context(
                    ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                )

            for a in chain(*layer_artists, artists):
                fig.draw_artist(a)

    def _get_unmanaged_artists(self):
        # return all artists not explicitly managed by the blit-manager
        # (e.g. any artist added via cartopy or matplotlib functions)
        managed_artists = set(
            chain(
                *self._bg_artists.values(),
                *self._artists.values(),
                self._ignored_unmanaged_artists,
            )
        )

        axes = {m.ax for m in (self._m, *self._m._children) if m.ax is not None}

        allartists = set()
        for ax in axes:
            # only include axes titles if they are actually set
            # (otherwise empty artists appear in the widget)
            titles = [
                i
                for i in (ax.title, ax._left_title, ax._right_title)
                if len(i.get_text()) > 0
            ]

            axartists = {
                *ax._children,
                *titles,
                *([ax.legend_] if ax.legend_ is not None else []),
            }

            allartists.update(axartists)

        return allartists.difference(managed_artists)

    def _clear_all_temp_artists(self):
        for method in self._m.cb._methods:
            container = getattr(self._m.cb, method, None)
            if container:
                container._clear_temporary_artists()
            self._clear_temp_artists(method)

    def _clear_temp_artists(self, method, forward=True):
        # clear artists from connected methods
        if method == "_click_move" and forward:
            self._clear_temp_artists("click", False)
        elif method == "click" and forward:
            self._clear_temp_artists("_click_move", False)
        elif method == "pick" and forward:
            self._clear_temp_artists("click", True)
        elif method == "on_layer_change" and forward:
            self._clear_temp_artists("pick", False)
            self._clear_temp_artists("click", True)
            self._clear_temp_artists("move", False)

        if method == "on_layer_change":
            # clear all artists from "on_layer_change" list irrespective of the method
            artists = self._artists_to_clear.pop("on_layer_change", [])
            for art in artists:
                for met, met_artists in self._artists_to_clear.items():
                    if art in met_artists:
                        art.set_visible(False)
                        self.remove_artist(art)
                        try:
                            art.remove()
                        except ValueError:
                            # ignore errors if the artist no longer exists
                            pass
                        met_artists.remove(art)
        else:
            artists = self._artists_to_clear.pop(method, [])
            while len(artists) > 0:
                art = artists.pop(-1)
                art.set_visible(False)
                self.remove_artist(art)
                try:
                    art.remove()
                except ValueError:
                    # ignore errors if the artist no longer exists
                    pass

                try:
                    self._artists_to_clear.get("on_layer_change", []).remove(art)
                except ValueError:
                    # ignore errors if the artist is not present in the list
                    pass

    def _get_showlayer_name(self, layer=None, transparent=False):
        # combine all layers that should be shown
        # (e.g. to add spines, backgrounds and inset-maps)

        if layer is None:
            layer = self.bg_layer

        # pass private layers through
        if layer.startswith("__"):
            return layer

        if transparent is True:
            show_layers = [layer, "__SPINES__"]
        else:
            show_layers = ["__BG__", layer, "__SPINES__"]

        # show inset map layers and spines only if they contain at least 1 artist
        inset_Q = False
        for l in self._parse_multi_layer_str(layer)[0]:
            narts = len(self._bg_artists.get("__inset_" + l, []))

            if narts > 0:
                show_layers.append(f"__inset_{l}")
                inset_Q = True

        if inset_Q:
            show_layers.append("__inset___SPINES__")

        return self._get_combined_layer_name(*show_layers)

    def update(
        self,
        layers=None,
        bbox_bounds=None,
        bg_layer=None,
        artists=None,
        clear=False,
        blit=True,
        clear_snapshot=True,
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
            the background-layer name to restore. The default is None.
        artists : list, optional
            A list of artists to update.
            If provided NO layer will be automatically updated!
            The default is None.
        clear : bool, optional
            If True, all temporary artists tagged for removal will be cleared.
            The default is False.
        blit : bool, optional
            If True, figure.cavas.blit() will be called to update the figure.
            If False, changes will only be visible on the next blit-event!
            The default is True.
        clear_snapshot : bool, optional
            Only relevant if the `inline` backend is used in a jupyter-notebook
            or an Ipython console.

            If True, clear the active cell before plotting a snapshot of the figure.
            The default is True.
        """
        if self._disable_update:
            # don't update during layout-editing
            return

        cv = self.canvas

        if bg_layer is None:
            bg_layer = self.bg_layer

        for action in self._before_update_actions:
            action()

        if clear:
            self._clear_temp_artists(clear)

        # restore the background
        # add additional layers (background, spines etc.)
        show_layer = self._get_showlayer_name()

        if show_layer not in self._bg_layers:
            # make sure the background is properly fetched
            self.fetch_bg(show_layer)

        cv.restore_region(self._get_background(show_layer))

        # execute after restore actions (e.g. peek layer callbacks)
        while len(self._after_restore_actions) > 0:
            action = self._after_restore_actions.pop(0)
            action()

        # draw all of the animated artists
        self._draw_animated(layers=layers, artists=artists)
        if blit:
            # workaround for nbagg backend to avoid glitches
            # it's slow but at least it works...
            # check progress of the following issues
            # https://github.com/matplotlib/matplotlib/issues/19116
            if self._mpl_backend_force_full:
                cv._force_full = True

            if bbox_bounds is not None:

                class bbox:
                    bounds = bbox_bounds

                cv.blit(bbox)
            else:
                # update the GUI state
                cv.blit(self.figure.bbox)

        # execute all actions registered to be called after blitting
        while len(self._after_update_actions) > 0:
            action = self._after_update_actions.pop(0)
            action()

        # let the GUI event loop process anything it has to do
        # don't do this! it is causing infinite loops
        # cv.flush_events()

        if blit and BlitManager._snapshot_on_update is True:
            self._m.snapshot(clear=clear_snapshot)

    def blit_artists(self, artists, bg="active", blit=True):
        """
        Blit artists (optionally on top of a given background)

        Parameters
        ----------
        artists : iterable
            the artists to draw
        bg : matplotlib.BufferRegion, None or "active", optional
            A fetched background that is restored before drawing the artists.
            The default is "active".
        blit : bool
            Indicator if canvas.blit() should be called or not.
            The default is True
        """
        cv = self.canvas
        renderer = self._get_renderer()
        if renderer is None:
            _log.error("EOmaps: encountered a problem while trying to blit artists...")
            return

        # restore the background
        if bg is not None:
            if bg == "active":
                bg = self._get_active_bg()
            cv.restore_region(bg)

        for a in artists:
            try:
                self.figure.draw_artist(a)
            except np.linalg.LinAlgError:
                # Explicitly catch numpy LinAlgErrors resulting from singular matrices
                # that can occur when colorbar histogram sizes are dynamically updated
                if _log.getEffectiveLevel() <= logging.DEBUG:
                    _log.debug(f"problem drawing artist {a}", exc_info=True)

        if blit:
            cv.blit()

    def _get_restore_bg_action(
        self,
        layer,
        bbox_bounds=None,
        alpha=1,
        clip_path=None,
        set_clip_path=False,
    ):
        """
        Update a part of the screen with a different background
        (intended as after-restore action)

        bbox_bounds = (x, y, width, height)
        """
        if bbox_bounds is None:
            bbox = self.figure.bbox
        else:
            bbox = Bbox.from_bounds(*bbox_bounds)

        def action():
            renderer = self._get_renderer()
            if renderer is None:
                return

            if self.bg_layer == layer:
                return

            x0, y0, w, h = bbox.bounds

            # make sure to restore the initial background
            init_bg = renderer.copy_from_bbox(self._m.f.bbox)
            # convert the buffer to rgba so that we can add transparency
            buffer = self._get_background(layer, cache=True)
            self.canvas.restore_region(init_bg)

            x = buffer.get_extents()
            ncols, nrows = x[2] - x[0], x[3] - x[1]

            argb = (
                np.frombuffer(buffer, dtype=np.uint8).reshape((nrows, ncols, 4)).copy()
            )
            argb = argb[::-1, :, :]

            argb[:, :, -1] = (argb[:, :, -1] * alpha).astype(np.int8)

            gc = renderer.new_gc()

            gc.set_clip_rectangle(bbox)
            if set_clip_path is True:
                gc.set_clip_path(clip_path)

            renderer.draw_image(
                gc,
                int(x0),
                int(y0),
                argb[int(y0) : int(y0 + h), int(x0) : int(x0 + w), :],
            )
            gc.restore()

        return action

    def _cleanup_layer(self, layer):
        """Trigger cleanup methods for a given layer."""
        self._cleanup_bg_artists(layer)
        self._cleanup_artists(layer)
        self._cleanup_bg_layers(layer)
        self._cleanup_on_layer_activation(layer)

    def _cleanup_bg_artists(self, layer):
        if layer not in self._bg_artists:
            return

        artists = self._bg_artists[layer]
        while len(artists) > 0:
            a = artists.pop()
            try:
                self.remove_bg_artist(a, layer, draw=False)
                # no need to remove spines (to avoid NotImplementedErrors)!
                if not isinstance(a, Spine):
                    a.remove()
            except Exception:
                _log.debug(f"EOmaps-cleanup: Problem while clearing bg artist:\n {a}")

        del self._bg_artists[layer]

    def _cleanup_artists(self, layer):
        if layer not in self._artists:
            return

        artists = self._artists[layer]
        while len(artists) > 0:
            a = artists.pop()
            try:
                self.remove_artist(a)
                # no need to remove spines (to avoid NotImplementedErrors)!
                if not isinstance(a, Spine):
                    a.remove()
            except Exception:
                _log.debug(
                    f"EOmaps-cleanup: Problem while clearing dynamic artist:\n {a}"
                )

        del self._artists[layer]

    def _cleanup_bg_layers(self, layer):
        try:
            # remove cached background-layers
            if layer in self._bg_layers:
                del self._bg_layers[layer]
        except Exception:
            _log.debug(
                "EOmaps-cleanup: Problem while clearing cached background layers"
            )

    def _cleanup_on_layer_activation(self, layer):
        try:
            # remove not yet executed lazy-activation methods
            # (e.g. not yet fetched WMS services)
            if layer in self._on_layer_activation:
                del self._on_layer_activation[layer]
        except Exception:
            _log.debug(
                "EOmaps-cleanup: Problem while clearing layer activation methods"
            )

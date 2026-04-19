# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""The BlitManager used to handle drawing and caching of backgrounds."""

import logging
from contextlib import ExitStack, contextmanager
from functools import lru_cache, wraps
from itertools import chain
import weakref

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.spines import Spine
from matplotlib.transforms import Bbox

from .helpers import _proxy, WeakOrderedCollection

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
            for arg in args:
                if isinstance(arg, str):
                    combnames.append(arg)
                elif isinstance(arg, (list, tuple)):
                    assert (
                        len(arg) == 2
                        and isinstance(arg[0], str)
                        and arg[1] >= 0
                        and arg[1] <= 1
                    ), (
                        f"EOmaps: unable to identify the layer-assignment: {arg} .\n"
                        "You can provide either a single layer-name as string, a list "
                        "of layer-names or a list of tuples of the form: "
                        "(< layer-name (str) >, < layer-transparency [0-1] > )"
                    )

                    layer, alpha = arg

                    if alpha < 1:
                        combnames.append(layer + "{" + str(alpha) + "}")
                    else:
                        combnames.append(layer)
                else:
                    raise TypeError(
                        f"EOmaps: unable to identify the layer-assignment: {layer} .\n"
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

        if layer.startswith("__") and not layer.startswith("**inset_"):
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


class ArtistAccessor:
    def __init__(self, ca, name="artists"):
        self._ca = ca
        self._name = name

        # used for private artists not obtained from Maps objects
        # (e.g. Spines, background patches etc.)
        # NOTE: sub-layer syntax is not supported for free artists
        # (e.g. keys should be layer-names not "<layer>__<sublayer id>")
        self._free_artists = {}

    def add(self, layer, *artists):
        "Add a 'free' artist to the blit-manager not connected to a Maps-object"
        self._free_artists.setdefault(layer, WeakOrderedCollection()).update(artists)

    def __getitem__(self, key):
        return [
            *getattr(self._ca, f"_get_{self._name}")(key),
            *self._free_artists.get(key, {}),
        ]

    def __setitem__(self, layer, artist):
        return getattr(self._ca.get_maps(layer), f"_{self._name}").add(artist)

    def __iter__(self):
        return chain(
            getattr(self._ca, f"_get_{self._name}")(), *self._free_artists.values()
        )


class ChildAccessor:
    def __init__(self):
        self._children = {}

        self.artists = ArtistAccessor(self, "artists")
        self.bg_artists = ArtistAccessor(self, "bg_artists")

    def __getitem__(self, key):
        return self._children[key]

    def __iter__(self):
        return iter(chain(*self._children.values()))

    def add(self, m):
        self._children.setdefault(m.layer, WeakOrderedCollection()).add(m)

    def remove(self, m):
        self._children[m.layer].remove(m)
        if len(self._children[m.layer]) == 0:
            del self._children[m.layer]

    def _get_artists(self, layer=None):
        if layer is None:
            return chain(*(m._artists for m in self))

        return chain(*(m._artists for m in self.get_maps(layer)))

    def _get_bg_artists(self, layer=None):
        if layer is None:
            return chain(*(m._bg_artists for m in self))

        return chain(*(m._bg_artists for m in self.get_maps(layer)))

    def _get_maps(self, layer):
        return self._children.get(layer, [])

    def get_layers(self):
        return list(self._children)

    def get_artists(self, layer=None):
        return list(self._get_artists(layer))

    def get_bg_artists(self, layer=None):
        return list(self._get_bg_artists(layer))

    def get_maps(self, layer):
        return list(self._get_maps(layer))


class Hooks:
    def __init__(self, *args, **kwargs):
        self.__hooks = dict()

        super().__init__(*args, **kwargs)

    def add_hook(self, hook, method, permanent=True, layer="all", unique=True):
        self.__add(
            hook=hook, method=method, permanent=permanent, layer=layer, unique=unique
        )

    def remove_hook(self, hook, method=None, permanent=None, layer=None, silent=True):
        self.__remove(
            hook=hook, method=method, permanent=permanent, layer=layer, silent=silent
        )

    def run_hook(self, name, layer="all", **kwargs):
        # always run callbacks assigned to the "all" layer...
        if layer != "all":
            self.__run(name, layer="all", **kwargs)

        self.__run(name, layer=layer, **kwargs)

        if name == "layer_activation":
            self.figure._EOmaps_parent._emit_signal("lazyLayerActivated")

    def _get_hooks(self, name, layer="all", permanent=False):
        if (hook := self.__hooks.get(name, None)) is None:
            return []

        return hook.get(permanent, {}).get(layer, [])

    def __run(self, name, layer="all", **kwargs):
        if (hook := self.__hooks.get(name, None)) is None:
            return

        single_shot_cb = hook.get(False, {}).get(layer, [])
        permanent_cb = hook.get(True, {}).get(layer, [])

        # run single-shot actions
        while len(single_shot_cb) > 0:
            try:
                action = single_shot_cb.pop(0)
                action(layer=layer, **kwargs)
            except Exception as ex:
                _log.error(
                    f"EOmaps: Issue during single-shot hook {action}: {ex}",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

        # run permanent actions
        for action in permanent_cb:
            try:
                action(layer=layer, **kwargs)
            except Exception as ex:
                _log.error(
                    f"EOmaps: Issue during permanent hook {action}: {ex}",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

    def __add(self, hook, method, permanent=False, layer="all", unique=True):
        cb = (
            self.__hooks.setdefault(hook, {})
            .setdefault(permanent, {})
            .setdefault(layer, [])
        )

        if not unique or method not in cb:
            cb.append(method)

    def __remove(self, hook, method=None, permanent=None, layer=None, silent=True):
        # if permanent is None, try to remove method as either temporary or
        # permanent callback
        if permanent is None:
            # try to remove method from permanent hook
            q = self.__remove(
                hook=hook, method=method, permanent=True, layer=layer, silent=True
            )
            # if no method is specified, also remove all temporary hooks of layer!
            if q is False or method is None:
                # try to remove method from temporary hook if not found in permanent
                q = self.__remove(
                    hook=hook, method=method, permanent=False, layer=layer, silent=True
                )
            if q is False and not silent:
                _log.warning(f"EOmaps: method {method} not found in hook '{hook}'")

            return q

        found = False
        if (hook := self.__hooks.get(hook, None)) is not None:
            if method is None:
                if layer is None:
                    # if method is None, and layer is None, remove ALL callbacks of hook
                    q = hook.pop(permanent, None) is not None
                else:
                    # remove ALL callbacks assigned to the specified layer
                    if (hook_callbacks := hook.get(permanent, None)) is not None:
                        q = hook_callbacks.pop(layer, None) is not None
                    else:
                        q = False
                return q

            # search for method
            if (hook_callbacks := hook.get(permanent, None)) is not None:
                # if None is passed as layer, traverse all layer assignments
                for l in (layer,) if layer else hook_callbacks.keys():
                    cb = hook_callbacks.get(l, [])
                    if method in cb:
                        found = True
                        break

        if not found:
            if not silent:
                _log.warning(f"EOmaps: method {method} not found in hook '{hook}'")
            return False

        try:
            cb.remove(method)
            return True
        except Exception as ex:
            _log.debug(
                f"EOmaps: unable to remove method {method} from '{hook}' hooks: {ex}",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )
            return False


# taken from https://matplotlib.org/stable/tutorials/advanced/blitting.html#class-based-example
class BlitManager(LayerParser, Hooks):
    """Manager used to schedule draw events, cache backgrounds, etc."""

    _snapshot_on_update = False

    def __init__(self, f, bg_layer="base"):
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

        self._f = _proxy(f)
        self._children = ChildAccessor()

        self._bg_layer = bg_layer
        self._bg_layers = {}

        self._managed_axes = WeakOrderedCollection()

        # the name of the layer at which all "unmanaged" artists are drawn
        self._unmanaged_artists_layer = "base"

        # grab the background on every draw
        self._cid_draw = self.canvas.mpl_connect("draw_event", self._on_draw_cb)

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

        self._refetch_blank = True
        self._blank_bg = None

        self._clear_on_layer_change = False

        self._on_layer_change_running = False

        # a weak set containing artists that should NOT be identified as
        # unmanaged artists
        self._ignored_unmanaged_artists = WeakOrderedCollection()

        super().__init__()

    @property
    def _artists(self):
        return self._children.artists

        artists = {}
        for m in self._children:
            artists.setdefault(m.layer, list()).extend(m._artists)
        return artists

    @property
    def _bg_artists(self):
        return self._children.bg_artists

        artists = {}
        for m in self._children:
            artists.setdefault(m.layer, list()).extend(m._bg_artists)

        return artists

    def _remove_artist(self, artist, layer=None):
        for m in self._children:
            if artist in m._artists:
                m._remove_artist(artist)
                break

    def _remove_bg_artist(self, artist, layer=None):
        for m in self._children:
            if artist in m._artists:
                m._remove_bg_artist(artist)
                break

    # TODO layer is currently ignored!
    def remove_artist(self, artist, layer=None):
        for m in self._children:
            if artist in m._artists:
                m.remove_artist(artist)
                break

    # TODO layer is currently ignored!
    def remove_bg_artist(self, artist, layer=None, draw=False):
        for m in self._children:
            if artist in m._bg_artists:
                m.remove_bg_artist(artist, draw=draw)
                break

    @property
    def figure(self):
        """The matplotlib figure instance."""
        return self._f

    @property
    def canvas(self):
        """The figure canvas instance."""
        return self.figure.canvas

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
        for m in self._children:
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
        # TODO fix this!
        # if hasattr(self._m.parent, "_wms_legend"):
        #     for layer, legends in self._m.parent._wms_legend.items():
        #         layer_visible = self._layer_is_subset(val, layer)

        #         if layer_visible:
        #             for i in legends:
        #                 i.set_visible(True)
        #         else:
        #             for i in legends:
        #                 i.set_visible(False)

        if self._clear_on_layer_change:
            self._clear_temp_artists("on_layer_change")

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
            artists.extend(self._artists[l])

        # make the list unique but maintain order (dicts keep order for python>3.7)
        artists = dict.fromkeys(artists)
        # sort artists by zorder (respecting inset-map priority)
        artists = sorted(artists, key=self._bg_artists_sort)

        return artists

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
            artists.extend(self._bg_artists[l])

            # make sure to also trigger drawing unmanaged artists on inset-maps!
            if l in (
                self._unmanaged_artists_layer,
                f"**inset_{self._unmanaged_artists_layer}",
            ):
                artists.extend(self._get_unmanaged_artists())

        # make the list unique but maintain order (dicts keep order for python>3.7)
        artists = dict.fromkeys(artists)
        # sort artists by zorder (respecting inset-map priority)
        artists = sorted(artists, key=self._bg_artists_sort)

        return artists

    def on_layer(self, func, layer=None, persistent=False, **kwargs):
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
        """
        method_evaluated = False
        # in case the layer is currently visible, directly execute the callback
        if layer == "all" or layer in self._get_active_layers_alphas[0]:
            ret = func(layer, **kwargs)
            method_evaluated = True
            if persistent is False:
                return ret

        @wraps(func)
        def layer_callback(layer):
            func(layer, **kwargs)

        if _log.getEffectiveLevel() <= 10:
            logmsg = (
                f"Adding {'persistent' if persistent else 'single-shot'} "
                f"layer change action for: '{layer if layer else 'all layers'}': "
                f"{getattr(layer_callback, '__qualname__', layer_callback)}"
            )
            _log.debug(logmsg)

        if layer is None:
            self.add_hook("layer_change", layer_callback, persistent)
        else:
            # treat inset-map layers like normal layers
            if layer.startswith("**inset_"):
                layer = layer[8:]

            self.add_hook("layer_activation", layer_callback, persistent, layer=layer)

        self.run_hook("on_layer_callback_added")

        # clear cached backgrounds to enforce a re-draw of the target-layer
        for l in list(self._bg_layers):
            if layer in l.split("|"):
                self._bg_layers.pop(l)

        # return the return-value of the callback in case it is submitted
        # as persistent callback and immediately evaluated
        if method_evaluated:
            return ret

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

        self.run_hook("before_update")

        if clear:
            self._clear_temp_artists(clear)

        # restore the background
        # add additional layers (background, spines etc.)
        show_layer = self._get_showlayer_name()

        if show_layer not in self._bg_layers:
            # make sure the background is properly fetched
            self.fetch_bg(show_layer)

        cv.restore_region(self._get_background(show_layer))

        self.run_hook("after_restore")

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

        self.run_hook("after_update")

        # let the GUI event loop process anything it has to do
        # don't do this! it is causing infinite loops
        # cv.flush_events()

        # TODO do we need this?
        # if blit and BlitManager._snapshot_on_update is True:
        #     self._m.snapshot(clear=clear_snapshot)

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
        maxes = {m.ax for m in (self._children) if getattr(m, "_new_axis_map", False)}
        return maxes

    def _get_managed_axes(self):
        return (*self._get_all_map_axes(), *self._managed_axes)

    def _get_unmanaged_axes(self):
        # return a list of all axes that are not managed by the blit-manager
        # (to ensure that "unmanaged" axes are drawn as well)

        # EOmaps axes
        managed_axes = self._get_managed_axes()
        allaxes = set(self.figure.axes)

        unmanaged_axes = allaxes.difference(managed_axes)
        return unmanaged_axes

    def _get_artist_zorder(self, a):
        try:
            return a.get_zorder()
        except Exception:
            _log.error(f"EOmaps: unalble to identify zorder of {a}... using 99")
            return 99

    def _get_active_bg(self, exclude_artists=None):
        with self._without_artists(artists=exclude_artists, layer=self.bg_layer):
            # fetch the current background (incl. dynamic artists)
            self.update()

            with ExitStack() as stack:
                # get rid of the figure background patch
                # (done by putting the patch on the **BG** layer!)

                # get rid of the axes background patch
                for ax_i in self._get_all_map_axes():
                    stack.enter_context(
                        ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                    )
                stack.enter_context(
                    self.figure.patch._cm_set(facecolor="none", edgecolor="none")
                )

                bg = self.canvas.copy_from_bbox(self.figure.bbox)

        return bg

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

        def action(*args, **kwargs):
            renderer = self._get_renderer()
            if renderer is None:
                return

            if self.bg_layer == layer:
                return

            x0, y0, w, h = bbox.bounds

            # make sure to restore the initial background
            init_bg = renderer.copy_from_bbox(self.figure.bbox)
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

    def _get_showlayer_name(self, layer=None, transparent=False):
        # combine all layers that should be shown
        # (e.g. to add spines, backgrounds and inset-maps)

        if layer is None:
            layer = self.bg_layer

        # pass private layers through
        if layer.startswith("__"):
            return layer

        if transparent is True:
            show_layers = [layer, "**SPINES**"]
        else:
            show_layers = ["**BG**", layer, "**SPINES**"]

        # show inset map layers and spines only if they contain at least 1 artist
        inset_Q = False
        for l in self._parse_multi_layer_str(layer)[0]:
            narts = len(self._bg_artists["**inset_" + l])

            if narts > 0:
                show_layers.append(f"**inset_{l}")
                inset_Q = True

        if inset_Q:
            show_layers.append("**inset_**SPINES**")

        return self._get_combined_layer_name(*show_layers)

    def _get_unmanaged_artists(self):
        # return all artists not explicitly managed by the blit-manager
        # (e.g. any artist added via cartopy or matplotlib functions)
        managed_artists = set(
            chain(
                self._bg_artists,
                self._artists,
                self._ignored_unmanaged_artists,
            )
        )

        axes = {m.ax for m in self._children if m.ax is not None}

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
        if layer.startswith("**"):
            return

        with self._cx_on_layer_change_running():
            # only execute persistent layer-change callbacks if the layer changed!
            if new:
                # TODO check how to handle "layer change" actions
                self.run_hook("layer_change", layer=layer)

            sublayers, _ = self._parse_multi_layer_str(layer)
            for l in sublayers:
                # individual callables executed if a specific layer is activated
                # persistent callbacks
                self.run_hook("layer_activation", layer=l)

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
            if layer not in ["**BG**"]:
                # get rid of the axes background patches for all layers except
                # the **BG** layer
                # (the figure background patch is on the "**BG**" layer)
                for ax_i in self._get_all_map_axes():
                    stack.enter_context(
                        ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                    )

            # execute actions before fetching new artists
            # (e.g. update data based on extent etc.)
            self.run_hook("before_fetch_bg", layer=layer, bbox=bbox)

            # get all relevant artists to plot and remember zorders
            # self.get_bg_artists() already returns artists sorted by zorder!
            if layer in ["**SPINES**", "**BG**", "**inset_**SPINES**"]:
                # avoid fetching artists from the "all" layer for private layers
                allartists = self.get_bg_artists(layer)
            else:
                if layer.startswith("**inset"):
                    allartists = self.get_bg_artists(["**inset_all", layer])
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

        except Exception:
            # we need to catch exceptions since QT does not like them...
            if loglevel <= 5:
                _log.log(5, "There was an error during draw!", exc_info=True)

    @contextmanager
    def _without_artists(self, artists=None, layer=None):
        try:
            removed_artists = {layer: set(), "all": set()}
            if artists is None:
                yield
            else:
                for a in artists:
                    if a in self._artists[layer]:
                        self._remove_artist(a, layer=layer)
                        removed_artists[layer].add(a)
                    elif a in self._artists["all"]:
                        self._remove_artist(a, layer="all")
                        removed_artists["all"].add(a)

                yield
        finally:
            for layer, artists in removed_artists.items():
                for a in artists:
                    self.add_artist(a, layer=layer)

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
            bg = renderer.copy_from_bbox(self.figure.bbox)
            gc.restore()
            return bg

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
            layers = list(chain(*(self._parse_multi_layer_str(l)[0] for l in layers)))
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
            sorted(self._artists[layer], key=self._get_artist_zorder)
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

    # TODO fix this for EOmaps v9.0!
    def _clear_all_temp_artists(self):
        _log.warning("clear_all_temp_artists NotImplemented for EOmaps v9.0")
        # for method in self._m.cb._methods:
        #     container = getattr(self._m.cb, method, None)
        #     if container:
        #         container._clear_temporary_artists()
        #     self._clear_temp_artists(method)

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
                        met_artists.remove(art)
        else:
            artists = self._artists_to_clear.pop(method, [])
            while len(artists) > 0:
                art = artists.pop(-1)
                art.set_visible(False)
                self.remove_artist(art)

                try:
                    self._artists_to_clear.get("on_layer_change", []).remove(art)
                except ValueError:
                    # ignore errors if the artist is not present in the list
                    pass

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
            except Exception:
                _log.debug(
                    f"EOmaps-cleanup: Problem while clearing dynamic artist:\n {a}"
                )

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
        self.remove_hook("layer_activation", method=None, permanent=None, layer=layer)

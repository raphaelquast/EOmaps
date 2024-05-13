# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Container classes for callback management"""

import logging
from types import SimpleNamespace
from functools import partial, wraps
from itertools import chain
from weakref import proxy

from .callbacks import (
    ClickCallbacks,
    PickCallbacks,
    KeypressCallbacks,
    MoveCallbacks,
)
from .helpers import register_modules

import matplotlib.pyplot as plt
from pyproj import Transformer
import numpy as np

_log = logging.getLogger(__name__)


class GeoDataFramePicker:
    """Collection of pick-methods for geopandas.GeoDataFrames"""

    def __init__(self, gdf, val_key, pick_method):
        self.gdf = gdf
        self.val_key = val_key
        self.pick_method = pick_method

    def get_picker(self):
        (gpd,) = register_modules("geopandas")
        if self.pick_method == "contains":
            return self._contains_picker
        elif self.pick_method == "centroids":
            from scipy.spatial import cKDTree

            self.tree = cKDTree(
                list(map(lambda x: (x.x, x.y), self.gdf.geometry.centroid))
            )
            return self._centroids_picker
        else:
            raise TypeError(
                f"EOmaps: {self.pick_method} is not a valid " "pick_method!"
            )

    def _contains_picker(self, artist, mouseevent):
        (gpd,) = register_modules("geopandas")

        try:
            query = getattr(self.gdf, "contains")(
                gpd.points_from_xy(
                    np.atleast_1d(mouseevent.xdata),
                    np.atleast_1d(mouseevent.ydata),
                )[0]
            )

            if query.any():

                ID = self.gdf.index[query][0]
                ind = query.values.nonzero()[0][0]

                if self.val_key:
                    val = self.gdf[query][self.val_key].iloc[0]
                else:
                    val = None

                if artist.get_array() is not None:
                    val_numeric = artist.norm(artist.get_array()[ind])
                    val_color = artist.cmap(val_numeric)
                else:
                    val_numeric = None
                    val_color = None

                return True, dict(
                    ID=ID,
                    ind=ind,
                    val=val,
                    val_color=val_color,
                    pos=(mouseevent.xdata, mouseevent.ydata),
                )
            else:
                return False, dict()
        except Exception:
            return False, dict()

    def _centroids_picker(self, artist, mouseevent):
        try:
            dist, ind = self.tree.query((mouseevent.xdata, mouseevent.ydata), 1)
            ID = self.gdf.index[ind]

            if self.val_key is not None:
                val = self.gdf.iloc[ind][self.val_key]
            else:
                val = None

            pos = self.tree.data[ind].tolist()
            try:
                val_numeric = artist.norm(artist.get_array()[ID])
                val_color = artist.cmap(val_numeric)
            except Exception:
                val_color = None

            return True, dict(ID=ID, pos=pos, val=val, ind=ind, val_color=val_color)

        except Exception:
            return False, dict()


class _CallbackContainer(object):
    """Base-class for callback containers."""

    def __init__(self, m, cb_class=None, method="click", parent_container=None):
        self._m = m
        self._parent_container = parent_container

        if self._parent_container is None:
            self._temporary_artists = []
        else:
            self._temporary_artists = self._parent_container._temporary_artists

        self._fwd_cbs = dict()

        self._method = method
        self._event = None

        self._execute_on_all_layers = False
        self._execute_while_toolbar_active = False

    def _getobj(self, m):
        """Get the equivalent callback container on another maps object."""
        return getattr(m.cb, self._method, None)

    @property
    def _objs(self):
        """Get the callback-container objects associated with the event-axes."""
        # Note: it is possible that more than 1 Maps objects are
        # assigned to the same axis!
        objs = []
        if self._event is not None:
            if hasattr(self._event, "mouseevent"):
                event = self._event.mouseevent
            else:
                event = self._event

            # make sure that "all" layer callbacks are executed before other callbacks
            ms, malls = [], []
            for m in reversed((*self._m.parent._children, self._m.parent)):
                if m.layer == "all":
                    malls.append(m)
                else:
                    ms.append(m)
            ms = ms + malls

            if self._method in ["keypress"]:
                for m in ms:
                    # always execute keypress callbacks irrespective of the mouse-pos
                    obj = self._getobj(m)

                    # only include objects that are on the same layer
                    # (irrespective if a toolbar mode is active or not)
                    if (
                        obj is not None
                        and obj._execute_cb(obj._m.layer)
                        # and not obj._check_toolbar_mode()
                    ):
                        objs.append(obj)
            else:
                for m in ms:
                    # don't use "is" in here since Maps-children are proxies
                    # (and so are their attributes)!
                    if event.inaxes == m.ax:
                        obj = self._getobj(m)
                        # only include objects that are on the same layer
                        # (and only if no toolbar mode is active!)
                        if (
                            obj is not None
                            and obj._execute_cb(obj._m.layer)
                            and not obj._check_toolbar_mode()
                        ):
                            objs.append(obj)
        return objs

    def _clear_temporary_artists(self):
        while len(self._temporary_artists) > 0:
            art = self._temporary_artists.pop(-1)
            self._m.BM._artists_to_clear.setdefault(self._method, []).append(art)

    def _sort_cbs(self, cbs):
        _cb_list = self._attach._available_callbacks()
        if not cbs:
            return set()
        cbnames = set([i.rsplit("__", 1)[0].rsplit("_", 1)[0] for i in cbs])
        sortp = _cb_list + list(set(_cb_list) ^ cbnames)
        return sorted(
            list(cbs), key=lambda w: sortp.index(w.rsplit("__", 1)[0].rsplit("_", 1)[0])
        )

    def __repr__(self):
        txt = "Attached callbacks:\n    " + "\n    ".join(
            f"{key}" for key in self.get.attached_callbacks
        )
        return txt

    def forward_events(self, *args):
        """
        Forward callback-events from this Maps-object to other Maps-objects.

        (e.g. share events one-way)

        Parameters
        ----------
        args : eomaps.Maps
            The Maps-objects that should execute the callback.
        """
        for m in args:
            self._fwd_cbs[id(m)] = m

    def share_events(self, *args):
        """
        Share callback-events between this Maps-object and other Maps-objects.

        (e.g. share events both ways)

        Parameters
        ----------
        args : eomaps.Maps
            The Maps-objects that should execute the callback.
        """
        for m1 in (self._m, *args):
            for m2 in (self._m, *args):
                if m1 is not m2:
                    self._getobj(m1)._fwd_cbs[id(m2)] = m2

        if self._method == "click":
            self._m.cb._click_move.share_events(*args)

    def add_temporary_artist(self, artist, layer=None):
        """
        Make an artist temporary (remove it from the map at the next event).

        Parameters
        ----------
        artist : matplotlib.artist
            The artist to use
        layer : str or None, optional
            The layer to put the artist on.
            If None, the layer of the used Maps-object is used. (e.g. `m.layer`)
        """
        if layer is None:
            layer = self._m.layer

        # in case the artist has already been added as normal or background
        # artist, remove it first!
        if artist in chain(*self._m.BM._bg_artists.values()):
            self._m.BM.remove_bg_artist(artist)

        if artist in chain(*self._m.BM._artists.values()):
            self._m.BM.remove_artist(artist)

        self._m.BM.add_artist(artist, layer=layer)
        self._temporary_artists.append(artist)

    def _execute_cb(self, layer):
        """
        Get bool if a callback assigned on "layer" should be executed.

        - True if the callback is assigned to the "all" layer
        - True if the corresponding layer is currently active
        - True if the corresponding layer is part of a currently active "multi-layer"
          (e.g.  "layer|layer2" or "layer|layer2{0.5}" )

        Parameters
        ----------
        layer : str
            The name of the layer to which the callback is attached.

        Returns
        -------
        bool
            Indicator if the callback should be executed on the currently visible
            layer or not.
        """
        if self.execute_on_all_layers or layer == "all":
            return True

        return self._m.BM._layer_visible(layer)

    @property
    def execute_on_all_layers(self):
        """Indicator if callbacks of this container are executed on all layers."""
        if self._parent_container is not None:
            return self._parent_container._execute_on_all_layers

        return self._execute_on_all_layers

    def set_execute_on_all_layers(self, q):
        """
        If True, callbacks of this container are executed even if the associated
        layer is not visible.

        (By default, callbacks are only executed if the associated layer is visible!)

        Parameters
        ----------
        q : bool
            True if callbacks should be executed irrespective of the visible layer.
        """

        if q:
            _log.debug(
                f"EOmaps: {self._method} callbacks of the Maps-object {self._m} "
                "are executed on all layers!"
            )

        if self._parent_container is not None:
            raise TypeError(
                f"EOmaps: 'execute_on_all_layers' is inherited for {self._method}!"
            )
        self._execute_on_all_layers = q

    def _check_toolbar_mode(self):
        if self._execute_while_toolbar_active:
            return False

        # returns True if a toolbar mode is active and False otherwise
        if (
            self._m.f.canvas.toolbar is not None
        ) and self._m.f.canvas.toolbar.mode != "":
            return True
        else:
            return False

    def set_execute_during_toolbar_action(self, q):
        """
        Set if callbacks should be executed during a toolbar action (e.g. pan/zoom).

        By default, callbacks are not executed during toolbar actions to make sure
        pan/zoom is smooth. (e.g. to avoid things like constant re-fetching of webmaps
        if a peek-layer callback is active during pan/zoom)

        Parameters
        ----------
        q : bool
            If True, callbacks will be triggered independent of the toolbar state.
            if False, callbacks will only trigger if no toolbar action is active.

        """
        self._execute_while_toolbar_active = q

    def _try_decorator(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception:
                _log.error("problem during callback", exc_info=True)

        return inner

    def _attach_decorator(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            return self._add_callback(
                callback=self._try_decorator(func), *args, **kwargs
            )

        return inner


def _apply_decorator_to_all_public_methods(decorator):
    def decorate(cls):
        for attr in filter(lambda x: not x.startswith("_"), dir(cls)):
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate


class _ClickContainer(_CallbackContainer):
    """
    A container for attaching callbacks and accessing return-objects.

    attach : accessor for callbacks.
        Executing the functions will attach the associated callback to the map!

    get : accessor for return-objects
        A container to provide easy-access to the return-values of the callbacks.

    """

    def __init__(self, m, cb_cls=None, method="pick", default_button=1, **kwargs):
        super().__init__(m, cb_cls, method, **kwargs)

        # a dict to identify connected _move callbacks
        # (e.g. to remove "_move" and "click" cbs in one go)
        self._connected_move_cbs = dict()

        self._sticky_modifiers = []

        # the default button to use when attaching callbacks
        self._default_button = default_button

        self.attach = self._attach(self)
        self.attach = _apply_decorator_to_all_public_methods(self._attach_decorator)(
            self.attach
        )

        self.get = self._get(self)

    class _attach:
        """
        Attach custom or pre-defined callbacks to the map.

        Callback-functions accept the following additional keyword-arguments:

        double_click : bool
            Indicator if the callback should be executed on double-click (True)
            or on single-click events (False). The default is False
        button : int
            The mouse-button to use for executing the callback:

                - LEFT = 1
                - MIDDLE = 2
                - RIGHT = 3
                - BACK = 8
                - FORWARD = 9

            The default is None in which case 1 (e.g. LEFT is used)
        modifier : str or None
            Define a keypress-modifier to execute the callback only if the
            corresponding key is pressed on the keyboard.

            - If None, the callback is executed if no modifier is activated.

            The default is None.
        on_motion : bool
            !! Only relevant for "click" callbacks !!

            - True: Continuously execute the callback if the mouse is moved while the
              assigned button is pressed.
            - False: Only execute the callback on clicks.

            The default is True.

        For additional keyword-arguments check the doc of the callback-functions!

        Examples
        --------
        Get a (temporary) annotation on a LEFT-double-click:

            >>> m.cb.click.attach.annotate(double_click=True, button=1, permanent=False)

        Permanently color LEFT-clicked pixels red with a black border:

            >>> m.cb.pick.attach.mark(facecolor="r", edgecolor="k", permanent=True)

        Attach a customly defined callback

            >>> def some_callback(self, asdf, **kwargs):
            >>>     print("hello world")
            >>>     print("the position of the clicked pixel", kwargs["pos"])
            >>>     print("the data-index of the clicked pixel", kwargs["ID"])
            >>>     print("data-value of the clicked pixel", kwargs["val"])
            >>>     print("the plot-crs is:", self.crs_plot)

            >>> m.cb.pick.attach(some_callback, double_click=False, button=1, asdf=1)

        """

        def __init__(self, parent):
            self._parent = parent
            self.m = parent._m
            self._temporary_artists = self._parent._temporary_artists

        def __call__(self, f, double_click=False, button=None, modifier=None, **kwargs):
            """
            Add a custom callback-function to the map.

            Parameters
            ----------
            f : callable
                the function to attach to the map.
                The call-signature is:

                >>> def some_callback(asdf, **kwargs):
                >>>     print("hello world")
                >>>     print("the position of the clicked pixel", kwargs["pos"])
                >>>     print("the data-index of the clicked pixel", kwargs["ID"])
                >>>     print("data-value of the clicked pixel", kwargs["val"])
                >>>
                >>> m.cb.attach(some_callback, asdf=1)

            double_click : bool
                Indicator if the callback should be executed on double-click (True)
                or on single-click events (False)
            button : int
                The mouse-button to use for executing the callback:

                    - LEFT = 1
                    - MIDDLE = 2
                    - RIGHT = 3
                    - BACK = 8
                    - FORWARD = 9

                The default is None in which case 1 (e.g. the LEFT button) is used
            modifier : str or None
                Define a keypress-modifier to execute the callback only if the
                corresponding key is pressed on the keyboard.

                - If None, the callback is executed if no modifier is activated.

                The default is None.
            on_motion : bool
                !! Only relevant for "click" callbacks !!

                - True: Continuously execute the callback if the mouse is moved while the
                  assigned button is pressed.
                - False: Only execute the callback on clicks.

                The default is True.
            kwargs :
                kwargs passed to the callback-function
                For documentation of the individual functions check the docs in `m.cb`

            Returns
            -------
            cid : int
                the ID of the attached callback

            """
            if button is None:
                button = self._parent._default_button

            return self._parent._add_callback(
                callback=f,
                double_click=double_click,
                button=button,
                modifier=modifier,
                **kwargs,
            )

        @classmethod
        def _available_callbacks(cls):
            return list(filter(lambda x: not x.startswith("_"), dir(cls)))

    class _get:
        """Accessor for objects generated/retrieved by callbacks."""

        def __init__(self, parent):
            self._parent = parent
            self.m = self._parent._m

            self.cbs = dict()

        @property
        def picked_object(self):
            """Get the most recent picked object."""
            if hasattr(self._parent.attach, "picked_object"):
                return self._parent.attach.picked_object
            else:
                _log.warning(
                    "EOmaps: No picked objects found. Attach "
                    "the 'load' callback first!"
                )

        @property
        def picked_vals(self):
            """Get a list of all picked values."""
            if hasattr(self._parent.attach, "picked_vals"):
                return self._parent.attach.picked_vals
            else:
                _log.warning(
                    "EOmaps: No picked values found. Attach "
                    "the 'get_values' callback first!"
                )

        @property
        def permanent_markers(self):
            """Get a list of all permanent markers."""
            if hasattr(self._parent.attach, "permanent_markers"):
                return self._parent.attach.permanent_markers
            else:
                _log.warning(
                    "EOmaps: No permanent markers found. Attach "
                    "the 'mark' callback with 'permanent=True' first!"
                )

        @property
        def permanent_annotations(self):
            """Get a list of all permanent annotations."""
            if hasattr(self._parent.attach, "permanent_annotations"):
                return self._parent.attach.permanent_annotations
            else:
                _log.warning(
                    "EOmaps: No permanent annotations found. Attach "
                    "the 'annotate' callback with 'permanent=True' first!"
                )

        @property
        def attached_callbacks(self):
            """Get a list of all IDs of attached callbacks."""
            cbs = []
            for ds, dsdict in self.cbs.items():
                for b, bdict in dsdict.items():
                    for name in bdict.keys():
                        cbs.append(f"{name}__{ds}__{b}")

            return cbs

    def _parse_cid(self, cid):
        """
        Parse a callbac-id.

        Parameters
        ----------
        cid : TYPE
            DESCRIPTION.

        Returns
        -------
        name : str
            the callback name.
        layer : str
            the layer to which the callback is attached.
        ds : str
            indicator if double- or single-click is used.
        b : str
            the button (e.g. 1, 2, 3 for left, middle, right)
        m : str
            the keypress modifier.
        """
        # do this to allow double-underscores in the layer-name

        name, rest = cid.split("__", 1)
        layer, ds, b, m = rest.rsplit("__", 3)

        return name, layer, ds, b, m

    def remove(self, callback=None):
        """
        Remove previously attached callbacks from the map.

        Parameters
        ----------
        callback : str
            the name of the callback to remove
            (e.g. the return-value of `m.cb.<method>.attach.<callback>()`)

        """
        # remove motion callbacks connected to click-callbacks
        if self._method == "click":
            if callback in self._connected_move_cbs:
                for i in self._connected_move_cbs[callback]:
                    self._m.cb._click_move.remove(i)
                self._connected_move_cbs.pop(callback)

        if callback is not None:
            name, layer, ds, b, m = self._parse_cid(callback)

        cbname = name + "__" + layer
        bname = f"{b}__{m}"
        dsdict = self.get.cbs.get(ds, None)

        if dsdict is not None:
            if bname in dsdict:
                bdict = dsdict.get(bname)
            else:
                _log.error(f"EOmaps: There is no callback named {callback}")
                return
        else:
            _log.error(f"EOmaps: There is no callback named {callback}")
            return

        if bdict is not None:
            if cbname in bdict:
                del bdict[cbname]

                # call cleanup methods on removal
                fname = name.rsplit("_", 1)[0]
                if hasattr(self._attach, f"_{fname}_cleanup"):
                    getattr(self._attach, f"_{fname}_cleanup")(self.attach)
            else:
                _log.error(f"EOmaps: There is no callback named {callback}")

    def set_sticky_modifiers(self, *args):
        """
        Define keys on the keyboard that should be treated as "sticky modifiers".

        "sticky modifiers" are used in "click"- "pick"- and "move" callbacks to define
        modifiers that should remain active even if the corresponding key on the
        keyboard is released.

        - a "sticky modifier" <KEY> will remain activated until

          - "ctrl + <KEY>" is pressed to deactivate the sticky modifier
          - another sticky modifier key is pressed on the keyboard

        Parameters
        ----------
        args : str
            Any positional argument passed to this function will be used as
            sticky-modifier, e.g.:

            >>> m.cb.click.set_sticky_modifiers("a", "1", "x")

        Examples
        --------
        >>> m = Maps()
        >>> m.cb.click.attach.annotate(modifier="1")
        >>> m.cb.click.set_sticky_modifiers("1")

        """
        self._sticky_modifiers = list(map(str, args))

        if self._method == "click":
            self._m.cb._click_move._sticky_modifiers = args

    def _init_picker(self):
        assert (
            self._m.coll is not None
        ), "you can only attach pick-callbacks after calling `plot_map()`!"

        try:
            # Lazily make a plotted dataset pickable a
            if getattr(self._m, "tree", None) is None:
                from .helpers import SearchTree

                self._m.tree = SearchTree(m=self._m._proxy(self._m))
                self._m.cb.pick._set_artist(self._m.coll)
                self._m.cb.pick._init_cbs()
                self._m.cb._methods.add("pick")
        except Exception as ex:
            _log.exception(
                "EOmaps: There was an error while trying to initialize "
                f"pick-callbacks!",
            )

    def _add_callback(
        self,
        *args,
        callback=None,
        double_click=False,
        button=None,
        modifier=None,
        on_motion=None,
        **kwargs,
    ):
        """
        Attach a callback to the plot that will be executed if a pixel is clicked.

        A list of pre-defined callbacks (accessible via `m.cb`) or customly defined
        functions can be used.

            >>> # to add a pre-defined callback use:
            >>> cid = m._add_callback("annotate", <kwargs passed to m.cb.annotate>)
            >>> # to remove the callback again, call:
            >>> m.remove_callback(cid)

        Parameters
        ----------
        callback : callable or str
            The callback-function to attach.

            If a string is provided, it will be used to assign the associated function
            from the `m.cb` collection:
                - "annotate" : add annotations to the clicked pixel
                - "mark" : add markers to the clicked pixel
                - "plot" : dynamically update a plot with the clicked values
                - "print_to_console" : print info of the clicked pixel to the console
                - "get_values" : save properties of the clicked pixel to a dict
                - "load" : use the ID of the clicked pixel to load data
                - "clear_annotations" : clear all existing annotations
                - "clear_markers" : clear all existing markers

            You can also define a custom function with the following call-signature:
                >>> def some_callback(asdf, **kwargs):
                >>>     print("hello world")
                >>>     print("the position of the clicked pixel", kwargs["pos"])
                >>>     print("the data-index of the clicked pixel", kwargs["ID"])
                >>>     print("data-value of the clicked pixel", kwargs["val"])
                >>>     print("asdf is set to:", asdf)

                >>> m.cb.attach(some_callback, double_click=False, button=1, asdf=1)

        double_click : bool
            Indicator if the callback should be executed on double-click (True)
            or on single-click events (False)
        button : int
            The mouse-button to use for executing the callback:

                - LEFT = 1
                - MIDDLE = 2
                - RIGHT = 3
                - BACK = 8
                - FORWARD = 9
            The default is None in which case 1 (e.g. LEFT is used)
        modifier : str or None
            Define a keypress-modifier to execute the callback only if the
            corresponding key is pressed on the keyboard.

            - If None, the callback is executed if no modifier is activated.

            The default is None.
        on_motion : bool or None, optional
            !! Only relevant for "click" callbacks !!

            - True: Continuously execute the callback if the mouse is moved while the
              assigned button is pressed.
            - False: Only execute the callback on clicks.
            - None: use True for default callbacks that support on_motion and False
              for all other callbacks (incl. custom callbacks)

            The default is None.
        **kwargs :
            kwargs passed to the callback-function
            For documentation of the individual functions check the docs in `m.cb`

        Returns
        -------
        cbname : str
            the identification string of the callback
            (to remove the callback, use `m.cb.remove(cbname)`)

        """
        if button is None:
            button = self._default_button

        if self._method == "pick":
            if self._m.coll is None:
                # lazily initialize the picker when the layer is fetched
                self._m._data_manager._on_next_fetch.append(self._init_picker)
            else:
                self._init_picker()

        cb_name = callback if isinstance(callback, str) else callback.__name__
        # attach "on_move" callbacks
        movecb_name = None

        # set on_motion=True as default for "click" callbacks that
        # are also supported as move callbacks and False otherwise
        if self._method == "click" and on_motion is None:
            if hasattr(self._m.cb._click_move._attach, cb_name):
                on_motion = True
            else:
                on_motion = False
        elif on_motion is None:
            on_motion = False

        if self._method == "click" and on_motion is True:
            # attach associated default click+move callbacks if available
            if isinstance(callback, str) and not hasattr(
                self._m.cb._click_move._attach, callback
            ):
                on_motion = False
                _log.warning(
                    f"Using 'on_motion' = True for the '{callback}' callback has no effect!"
                )

            if on_motion:
                movecb_name = self._m.cb._click_move._add_callback(
                    *args,
                    callback=callback,
                    double_click=double_click,
                    button=button,
                    modifier=modifier,
                    **kwargs,
                )
        elif on_motion is True:
            _log.warning(
                "EOmaps: 'on_motion=True' is only possible for " "'click' callbacks!"
            )

        assert not all(
            i in kwargs for i in ["pos", "ID", "val", "double_click", "button"]
        ), 'the names "pos", "ID", "val" cannot be used as keyword-arguments!'

        if isinstance(callback, str):
            assert hasattr(self._attach, callback), (
                f"The function '{callback}' does not exist as a pre-defined {self._method} callback."
                + " Use one of:\n    - "
                + "\n    - ".join(self._attach._available_callbacks())
            )
            callback = getattr(self._attach, callback)

        if double_click is True:
            btn_key = "double"
        elif double_click == "release":
            btn_key = "release"
        else:
            btn_key = "single"

        # check for modifiers
        button_modifier = f"{button}__{modifier}"

        d = self.get.cbs.setdefault(btn_key, dict()).setdefault(button_modifier, dict())

        # get a unique name for the callback
        # name_idx__layer
        ncb = [
            int(i.split("__")[0].rsplit("_", 1)[1])
            for i in d
            if i.startswith(callback.__name__)
        ]
        cbkey = (
            callback.__name__
            + f"_{max(ncb) + 1 if len(ncb) > 0 else 0}"
            + f"__{self._m.layer}"
        )

        d[cbkey] = partial(callback, *args, **kwargs)

        # add mouse-button assignment as suffix to the name (with __ separator)
        cbname = cbkey + f"__{btn_key}__{button}__{modifier}"  # TODO

        if movecb_name is not None:
            self._connected_move_cbs[cbname] = [movecb_name]

        return cbname


class ClickContainer(_ClickContainer):
    """
    Callbacks that are executed if you click anywhere on the Map.

    NOTE
    ----
    You can use `on_motion=False` when attaching a callback to avoid triggering
    the callback if the mouse is moved while a button is pressed.

    Methods
    -------
    attach : accessor for callbacks.
        Executing the functions will attach the associated callback to the map!

    get : accessor for return-objects
        A container to provide easy-access to the return-values of the callbacks.

    remove : remove prviously added callbacks from the map

    forward_events : forward events to connected maps-objects

    share_events : share events between connected maps-objects (e.g. forward both ways)

    set_sticky_modifiers : define keypress-modifiers that remain active after release

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._cid_button_press_event = None
        self._cid_button_release_event = None
        self._cid_motion_event = None

        self._event = None

    class _attach(_ClickContainer._attach, ClickCallbacks):
        __doc__ = _ClickContainer._attach.__doc__
        pass

    class _get(_ClickContainer._get):
        __doc__ = _ClickContainer._get.__doc__
        pass

    # to make namespace accessible for sphinx
    attach = _attach
    get = _get

    def _init_cbs(self):
        if self._m.parent is self._m:
            self._add_click_callback()

    def _get_clickdict(self, event):
        clickdict = dict(
            pos=(event.xdata, event.ydata),
            ID=None,
            val=None,
            ind=None,
        )

        return clickdict

    def _execute_cbs(self, event, cids):
        """
        Execute a list of callbacks based on an event and the cid

        Parameters
        ----------
        event :
            The event to use.
        cids : list of str
            A list of the cids of the callbacks that should be executed.

        """
        clickdict = self._get_clickdict(event)

        for cid in cids:
            name, layer, ds, button, mod = self._parse_cid(cid)
            cbs = self.get.cbs.get(ds, dict()).get(f"{button}__{mod}", dict())
            cb = cbs.get(f"{name}__{layer}", None)
            if cb is not None:
                cb(**clickdict)

    def _onclick(self, event):
        clickdict = self._get_clickdict(event)

        if event.dblclick:
            cbs = self.get.cbs.get("double", dict())
        else:
            cbs = self.get.cbs.get("single", dict())

        # check for keypress-modifiers
        if (
            event.key is None
            and self._m.cb.keypress._modifier in self._sticky_modifiers
        ):
            # in case sticky_modifiers are defined, use the last pressed modifier
            event_key = self._m.cb.keypress._modifier
        else:
            event_key = event.key

        button_modifier = f"{event.button}__{event_key}"

        self._event = event

        if button_modifier in cbs:
            bcbs = cbs[button_modifier]

            for key in self._sort_cbs(bcbs):
                layer = key.split("__", 1)[1]
                if not self._execute_cb(layer):
                    return

                cb = bcbs[key]
                if clickdict is not None:
                    cb(**clickdict)

    def _onrelease(self, event):
        cbs = self.get.cbs.get("release", dict())

        # check for keypress-modifiers
        if (
            event.key is None
            and self._m.cb.keypress._modifier in self._sticky_modifiers
        ):
            # in case sticky_modifiers are defined, use the last pressed modifier
            event_key = self._m.cb.keypress._modifier
        else:
            event_key = event.key

        button_modifier = f"{event.button}__{event_key}"

        if button_modifier in cbs:
            clickdict = self._get_clickdict(event)
            bcbs = cbs[button_modifier]
            for cb in bcbs.values():
                cb(**clickdict)

    def _reset_cids(self):
        # clear all temporary artists
        self._clear_temporary_artists()
        self._m.BM._clear_temp_artists(self._method)

        if self._cid_button_press_event:
            self._m.f.canvas.mpl_disconnect(self._cid_button_press_event)
        self._cid_button_press_event = None

        if self._cid_motion_event:
            self._m.f.canvas.mpl_disconnect(self._cid_motion_event)
        self._cid_motion_event = None

        if self._cid_button_release_event:
            self._m.f.canvas.mpl_disconnect(self._cid_button_release_event)
        self._cid_button_release_event = None

    def _add_click_callback(self):
        def clickcb(event):
            if (
                not self._m.cb.get_execute_callbacks()
                and not self._method == "_always_active"
            ):
                return

            try:
                self._event = event

                # execute onclick on the maps object that belongs to the clicked axis
                # and forward the event to all forwarded maps-objects
                for obj in self._objs:
                    # clear temporary artists before executing new callbacks to avoid
                    # having old artists around when callbacks are triggered again
                    obj._clear_temporary_artists()
                    obj._onclick(event)

                    # forward callbacks to the connected maps-objects
                    obj._fwd_cb(event)

                self._m.BM._clear_temp_artists(self._method)

                self._m.parent.BM.update(clear=self._method)
            except ReferenceError:
                pass

        def releasecb(event):
            if (
                not self._m.cb.get_execute_callbacks()
                and not self._method == "_always_active"
            ):
                return

            try:
                self._event = event

                # execute onclick on the maps object that belongs to the clicked axis
                # and forward the event to all forwarded maps-objects
                for obj in self._objs:
                    # don't clear temporary artists in here since we want
                    # click (or click+move) artists to remain on the plot when the
                    # button is released!
                    obj._onrelease(event)
                    # forward callbacks to the connected maps-objects
                    obj._fwd_cb(event)

            except ReferenceError:
                # ignore errors caused by no-longer existing weakrefs
                pass

        if self._cid_button_press_event is None:
            # ------------- add a callback
            self._cid_button_press_event = self._m.f.canvas.mpl_connect(
                "button_press_event", clickcb
            )

        if self._cid_button_release_event is None:
            # ------------- add a callback
            self._cid_button_release_event = self._m.f.canvas.mpl_connect(
                "button_release_event", releasecb
            )

    def _fwd_cb(self, event):
        # click container events are MouseEvents!
        if event.inaxes != self._m.ax:
            return

        if event.name == "button_release_event":
            for key, m in self._fwd_cbs.items():
                obj = self._getobj(m)
                if obj is None:
                    continue
                obj._onrelease(event)

        else:
            for key, m in self._fwd_cbs.items():
                obj = self._getobj(m)
                # clear all temporary artists that are still around
                obj._clear_temporary_artists()
                if obj is None:
                    continue

                transformer = Transformer.from_crs(
                    self._m.crs_plot,
                    m.crs_plot,
                    always_xy=True,
                )

                # transform the coordinates of the clicked location
                xdata, ydata = transformer.transform(event.xdata, event.ydata)

                dummymouseevent = SimpleNamespace(
                    inaxes=m.ax,
                    dblclick=event.dblclick,
                    button=event.button,
                    xdata=xdata,
                    ydata=ydata,
                    key=event.key
                    # x=event.mouseevent.x,
                    # y=event.mouseevent.y,
                )

                obj._onclick(dummymouseevent)


class MoveContainer(ClickContainer):
    """
    Callbacks that are executed if you move the mouse without holding down a button.

    Methods
    -------
    attach : accessor for callbacks.
        Executing the functions will attach the associated callback to the map!

    get : accessor for return-objects
        A container to provide easy-access to the return-values of the callbacks.

    remove : remove prviously added callbacks from the map

    forward_events : forward events to connected maps-objects

    share_events : share events between connected maps-objects (e.g. forward both ways)

    set_sticky_modifiers : define keypress-modifiers that remain active after release

    """

    # this is just a copy of ClickContainer to manage motion-sensitive callbacks

    def __init__(self, button_down=False, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self._cid_motion_event = None

        self._button_down = button_down

    class _attach(_ClickContainer._attach, MoveCallbacks):
        __doc__ = _ClickContainer._attach.__doc__
        pass

    class _get(_ClickContainer._get):
        __doc__ = _ClickContainer._get.__doc__
        pass

    # to make namespace accessible for sphinx
    attach = _attach
    get = _get

    def _init_cbs(self):
        if self._m.parent is self._m:
            self._add_move_callback()

    def _reset_cids(self):
        # clear all temporary artists
        self._clear_temporary_artists()
        self._m.BM._clear_temp_artists(self._method)

        if self._cid_motion_event:
            self._m.f.canvas.mpl_disconnect(self._cid_motion_event)
        self._cid_motion_event = None

    def _add_move_callback(self):
        def movecb(event):
            if not self._m.cb.get_execute_callbacks():
                return

            try:
                self._event = event
                # only execute movecb if a mouse-button is held down
                # and only if the motion is happening inside the axes
                if self._button_down:
                    if not event.button:  # or (event.inaxes != self._m.ax):
                        # always clear temporary move-artists
                        if self._method == "move":
                            for obj in self._objs:
                                obj._clear_temporary_artists()
                            self._m.BM._clear_temp_artists(self._method)
                        return
                else:
                    if event.button:  # or (event.inaxes != self._m.ax):
                        # always clear temporary move-artists
                        if self._method == "move":
                            for obj in self._objs:
                                obj._clear_temporary_artists()
                            self._m.BM._clear_temp_artists(self._method)
                        return

                # execute onclick on the maps object that belongs to the clicked axis
                # and forward the event to all forwarded maps-objects
                call_update = False
                for obj in self._objs:
                    # check if there is a reason to update (e.g. an attached callback)
                    if call_update is False:
                        if len(obj.get.attached_callbacks) > 0:
                            call_update = True

                    # clear temporary artists before executing new callbacks to avoid
                    # having old artists around when callbacks are triggered again
                    obj._clear_temporary_artists()
                    self._m.BM._clear_temp_artists(self._method)
                    obj._onclick(event)

                    # forward callbacks to the connected maps-objects
                    obj._fwd_cb(event)

                # only update if a callback is attached
                # (to avoid lag in webagg backed due to slow updates)
                if call_update:
                    if self._button_down:
                        if event.button:
                            self._m.parent.BM.update(clear=self._method)
                    else:
                        self._m.parent.BM.update(clear=self._method)

            except ReferenceError:
                pass

        if self._cid_motion_event is None:
            # for click-callbacks, allow motion-detection
            self._cid_motion_event = self._m.f.canvas.mpl_connect(
                "motion_notify_event", movecb
            )


class PickContainer(_ClickContainer):
    """
    Callbacks that select the nearest datapoint if you click on the map.

    The event will search for the closest data-point and execute the callback
    with the properties (e.g. position , ID, value) of the selected point.

    Note
    ----
    To speed up identification of points for very large datasets, the search
    is limited to points located inside a "search rectangle".
    The side-length of this rectangle is determined in the plot-crs and can be
    set via `m.cb.pick.set_props(search_radius=...)`.

    The default is to use a side-length of 50 times the dataset-radius.

    Methods
    -------
    attach : accessor for callbacks.
        Executing the functions will attach the associated callback to the map!

    get : accessor for return-objects
        A container to provide easy-access to the return-values of the callbacks.

    remove : remove prviously added callbacks from the map

    forward_events : forward events to connected maps-objects

    share_events : share events between connected maps-objects (e.g. forward both ways)

    set_sticky_modifiers : define keypress-modifiers that remain active after release

    set_props : set the picking behaviour (e.g. number of points, search radius, etc.)

    """

    def __init__(self, picker_name="default", picker=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cid_pick_event = dict()
        self._picker_name = picker_name
        self._artist = None

        self._n_ids = 1
        self._consecutive_multipick = False
        self._pick_relative_to_closest = True

        self._search_radius = "50"

        if picker is None:
            self._picker = self._default_picker
        else:
            self._picker = picker

        # indicator how shared pick-events identify the relevant datapoint
        self._ensure_same_pick_id = False

    class _attach(_ClickContainer._attach, PickCallbacks):
        __doc__ = _ClickContainer._attach.__doc__
        pass

    class _get(_ClickContainer._get):
        __doc__ = _ClickContainer._get.__doc__
        pass

    # to make namespace accessible for sphinx
    attach = _attach
    get = _get

    def __getitem__(self, name):
        name = str(name)
        if name.startswith("_"):
            container_name = "_pick__" + name[1:]
        else:
            container_name = "pick__" + name

        if hasattr(self._m.cb, container_name):
            return getattr(self._m.cb, container_name)
        else:
            _log.error(
                f"the picker {name} does not exist...", "use `m.cb.add_picker` first!"
            )

    def share_events(self, *args, ensure_same_id=False):
        """
        Share callback-events between this Maps-object and other Maps-objects.

        (e.g. share events both ways)

        Note
        ----
        For **pick-events**, you can use the additional keyword-argument
        `ensure_same_id` to make sure that all events pick the exact same ID.

        Parameters
        ----------
        args : eomaps.Maps
            The Maps-objects that should execute the callback.

        ensure_same_id : bool
            If True, all pick-events are triggered by the same ID value.
            (e.g. the ID of the datapoint that was actually picked)

            If False, each map executes the pick-event with respect to the reprojected
            mouse-position and identifies the closest datapoint to use.

            The default is False
        """
        self._ensure_same_pick_id = ensure_same_id

        for m in args:
            self._getobj(m)._ensure_same_pick_id = ensure_same_id

        super().share_events(*args)

    def set_props(
        self,
        n=None,
        consecutive_pick=None,
        pick_relative_to_closest=None,
        search_radius=None,
    ):
        """
        Set the picker-properties (number of picked points, max. search radius, etc.).

        Only provided arguments will be updated!

        Parameters
        ----------
        n : int, optional
            The number of nearest neighbours to pick at each pick-event.
            The default is 1.
        consecutive_pick : bool, optional

            - If True, pick-callbacks will be executed consecutively for each
              picked datapoint.
            - if False, pick-callbacks will get lists of all picked values
              as input-arguments

            The default is False.
        pick_relative_to_closest : bool, optional
            ONLY relevant if `n > 1`.

            - If True: pick (n) nearest neighbours based on the center of the
              closest identified datapoint
            - If False: pick (n) nearest neighbours based on the click-position

            The default is True.
        search_radius : int, float, str or None optional
            Set the radius of the area that is used to limit the number of
            pixels when searching for nearest-neighbours.

            - if `int` or `float`, the radius of the circle in units of the plot_crs
            - if `str`, a multiplication-factor for the estimated data-radius.

              NOTE: The multiplied radius is defined in the plot projection!
              If the data was provided in a different projection, the radius
              estimated from the re-projected data is used (might be different
              from the actual shape radius!)

            The default is "50" (e.g. 50 times the data-radius).

        """
        if n is not None:
            self._n_ids = n

        if consecutive_pick is not None:
            self._consecutive_multipick = consecutive_pick

        if pick_relative_to_closest is not None:
            self._pick_relative_to_closest = pick_relative_to_closest

        if search_radius is not None:
            self._search_radius = search_radius

    def _set_artist(self, artist):
        # use a weakref-proxy to make sure the artist can be garbage-collected
        # if it is deleted (or if the figure is closed)
        self._artist = proxy(artist)
        self._artist.set_picker(self._picker)

    def _init_cbs(self):
        # if self._m.parent is self._m:
        self._add_pick_callback()

    def _default_picker(self, artist, event):
        # make sure that objects are only picked if we are on the right layer
        if not self._execute_cb(self._m.layer):
            return False, None

        try:
            # if no pick-callback is attached, don't identify the picked point
            if len(self.get.cbs) == 0:
                return False, None
        except ReferenceError:
            # in case we encounter a reference-error, remove the picker from the artist
            # (happens if the picker originates from a no-longer existing Maps object)
            self._artist.set_picker(None)
            return False, None

        if (event.inaxes != self._m.ax) or not hasattr(self._m, "tree"):
            return False, dict(ind=None, dblclick=event.dblclick, button=event.button)

        # make sure non-finite coordinates (resulting from projections in
        # forwarded callbacks) don't lead to issues
        if not np.isfinite((event.xdata, event.ydata)).all():
            return False, dict(ind=None, dblclick=event.dblclick, button=event.button)

        # update the search-radius if necessary
        # (do this here to allow setting a multiplier for the dataset-radius
        # without having to plot it first!)
        if self._search_radius != self._m.tree._search_radius:
            self._m.tree.set_search_radius(self._search_radius)

        # find the closest point to the clicked pixel
        index = self._m.tree.query(
            (event.xdata, event.ydata),
            k=self._n_ids,
            pick_relative_to_closest=self._pick_relative_to_closest,
        )

        if index is not None:
            pos = self._m._data_manager._get_xy_from_index(index, reprojected=True)
            val = self._m._data_manager._get_val_from_index(index)
            ID = self._m._data_manager._get_id_from_index(index)

            try:
                val_color = artist.cmap(artist.norm(val))
            except Exception:
                val_color = None

            return True, dict(
                dblclick=event.dblclick,
                button=event.button,
                ind=index,
                ID=ID,
                pos=pos,
                val=val,
                val_color=val_color,
            )
        else:
            # do this to "unpick" previously picked datapoints if you click
            # outside the data-extent
            return True, dict(ind=None, dblclick=event.dblclick, button=event.button)

        return False, None

    def _get_pickdict(self, event):
        event_ind = getattr(event, "ind", None)
        if event_ind is None:
            if _log.getEffectiveLevel() <= logging.DEBUG:
                _log.debug(f"Pick-event without index encountered: {event}")
            return

        n_inds = len(np.atleast_1d(event_ind))
        # mouseevent = event.mouseevent
        noval = [None] * n_inds if n_inds > 1 else None

        ID = getattr(event, "ID", noval)
        pos = getattr(event, "pos", noval)
        val = getattr(event, "val", noval)
        ind = getattr(event, "ind", noval)
        val_color = getattr(event, "val_color", noval)

        if ind is not None:
            if self._consecutive_multipick is False:
                # return all picked values as arrays
                clickdict = dict(
                    ID=ID,  # convert IDs to numpy-arrays!
                    pos=pos,
                    val=val,
                    ind=ind,
                    val_color=val_color,
                    picker_name=self._picker_name,
                )

                return clickdict
            else:
                if n_inds > 1:
                    clickdicts = []
                    for i in range(n_inds):
                        clickdict = dict(
                            ID=ID[i],
                            pos=(pos[0][i], pos[1][i]),
                            val=val[i],
                            ind=ind[i],
                            val_color=val_color[i],
                            picker_name=self._picker_name,
                        )
                        clickdicts.append(clickdict)
                else:
                    clickdicts = [
                        dict(
                            ID=ID,  # convert IDs to numpy-arrays!
                            pos=pos,
                            val=val,
                            ind=ind,
                            val_color=val_color,
                            picker_name=self._picker_name,
                        )
                    ]

                return clickdicts

    def _onpick(self, event):
        if not self._artist_picked(event):
            return

        # only execute onpick if the correct layer is visible
        # (relevant for forwarded callbacks)
        if not self._execute_cb(self._m.layer):
            return

        # make sure temporary artists are cleared before executing new callbacks
        # to avoid having old artists around when callbacks are triggered again
        self._clear_temporary_artists()
        self._m.BM._clear_temp_artists(self._method)

        clickdict = self._get_pickdict(event)

        # if no data was found, don't execute the callbacks
        if clickdict is None:
            return

        if event.mouseevent.dblclick:
            cbs = self.get.cbs.get("double", dict())
        else:
            cbs = self.get.cbs.get("single", dict())

        # check for keypress-modifiers
        if (
            event.mouseevent.key is None
            and self._m.cb.keypress._modifier in self._sticky_modifiers
        ):
            # in case sticky_modifiers are defined, use the last pressed modifier
            event_key = self._m.cb.keypress._modifier
        else:
            event_key = event.mouseevent.key

        button_modifier = f"{event.mouseevent.button}__{event_key}"

        if button_modifier in cbs:
            bcbs = cbs[button_modifier]

            for key in self._sort_cbs(bcbs):
                layer = key.split("__", 1)[1]
                if not self._execute_cb(layer):
                    # only execute callbacks if the layer name of the associated
                    # maps-object is active
                    return

                cb = bcbs[key]
                if self._consecutive_multipick is False:
                    cb(**clickdict)
                else:
                    for c in clickdict:
                        cb(**c)

    def _reset_cids(self):
        # clear all temporary artists
        self._clear_temporary_artists()
        self._m.BM._clear_temp_artists(self._method)

        for method, cid in self._cid_pick_event.items():
            self._m.f.canvas.mpl_disconnect(cid)
        self._cid_pick_event.clear()

    def _artist_picked(self, event):
        # use == instead of "is" here since self._artist is a weakref proxy!
        if self._artist == event.artist:
            return True
        else:
            # handle contour-plot artists explicitly
            if self._artist.__class__.__name__ == "_CollectionAccessor":
                if any(i is event.artist for i in self._artist.collections):
                    return True
            else:
                return False

    def _add_pick_callback(self):
        # execute onpick and forward the event to all connected Maps-objects

        def pickcb(event):
            if not self._m.cb.get_execute_callbacks():
                return

            try:
                # make sure pickcb is only executed if we are on the right layer
                if not self._execute_cb(self._m.layer):
                    return

                if not self._artist_picked(event):
                    return

                self._event = event

                # execute "_onpick" on the maps-object that belongs to the clicked axes
                # and forward the event to all forwarded maps-objects
                self._onpick(event)
                # forward callbacks to the connected maps-objects
                self._fwd_cb(event, self._picker_name)

                # don't update here... the click-callback will take care of it!
            except ReferenceError:
                pass

        # attach the callbacks (only once per method!)
        if self._method not in self._cid_pick_event:
            self._cid_pick_event[self._method] = self._m.f.canvas.mpl_connect(
                "pick_event", pickcb
            )

    def _fwd_cb(self, event, picker_name):
        # PickEvents have a .mouseevent property for the associated MouseEvent!
        if event.mouseevent.inaxes != self._m.ax:
            return
        for key, m in self._fwd_cbs.items():
            obj = self._getobj(m)
            if obj is None:
                continue

            transformer = Transformer.from_crs(
                self._m.crs_plot,
                m.crs_plot,
                always_xy=True,
            )

            # transform the coordinates of the clicked location to the
            # crs of the map
            xdata, ydata = transformer.transform(
                event.mouseevent.xdata, event.mouseevent.ydata
            )

            dummymouseevent = SimpleNamespace(
                inaxes=m.ax,
                dblclick=event.mouseevent.dblclick,
                button=event.mouseevent.button,
                xdata=xdata,
                ydata=ydata,
                key=event.mouseevent.key,
                # x=event.mouseevent.x,
                # y=event.mouseevent.y,
            )
            dummyevent = SimpleNamespace(
                artist=obj._artist,
                dblclick=event.mouseevent.dblclick,
                button=event.mouseevent.button,
                # inaxes=m.ax,
                mouseevent=dummymouseevent,
                # picker_name=picker_name,
            )

            if self._ensure_same_pick_id is False:
                # execute a new pick-event and use the identified point

                pick = obj._picker(obj._artist, dummymouseevent)
                if pick[1] is not None:
                    dummyevent.ID = pick[1].get("ID", None)
                    dummyevent.ind = pick[1].get("ind", None)
                    dummyevent.val = pick[1].get("val", None)
                    dummyevent.pos = pick[1].get("pos", None)
                    dummyevent.val_color = pick[1].get("val_color", None)
                else:
                    dummyevent.ind = None
            else:
                # use the ID identified by the parent pick-event to obtain values etc.
                ID = getattr(event, "ID", None)
                if ID is not None:
                    ind = m._data_manager._get_ind_from_ID(ID)
                    if ind is not None:
                        # TODO check why arrays with 1 entry need to be converted here
                        if len(ind) == 1:
                            ind = ind[0]

                        val = m._data_manager._get_val_from_index(ind)
                        pos = m._data_manager._get_xy_from_index(ind, reprojected=True)

                        try:
                            val_color = obj._artist.cmap(obj._artist.norm(val))
                        except Exception:
                            val_color = None

                        dummyevent.ID = ID
                        dummyevent.ind = ind
                        dummyevent.val = val
                        dummyevent.pos = pos
                        dummyevent.val_color = val_color
                    else:
                        dummyevent.ID = None
                        dummyevent.ind = None

            obj._onpick(dummyevent)


class KeypressContainer(_CallbackContainer):
    """
    Callbacks that are executed if you press a key on the keyboard.

    Methods
    -------
    attach : accessor for callbacks.
        Executing the functions will attach the associated callback to the map!

    get : accessor for return-objects
        Accessor for objects generated/retrieved by callbacks.

    remove : remove prviously added callbacks from the map

    forward_events : forward events to connected maps-objects

    share_events : share events between connected maps-objects (e.g. forward both ways)

    set_sticky_modifiers : define keypress-modifiers that remain active after release

    """

    def __init__(self, m, cb_cls=None, method="keypress"):
        super().__init__(m, cb_cls, method)

        self._cid_keypress_event = None

        # remember last pressed key (for use as "sticky_modifier")
        self._modifier = None

        self.attach = self._attach(self)
        self.attach = _apply_decorator_to_all_public_methods(self._attach_decorator)(
            self.attach
        )

        self.get = self._get(self)

    def _init_cbs(self):
        if self._m.parent is self._m:
            self._initialize_callbacks()

    def _reset_cids(self):
        # clear all temporary artists
        self._clear_temporary_artists()
        self._m.BM._clear_temp_artists(self._method)

        if self._cid_keypress_event:
            self._m.f.canvas.mpl_disconnect(self._cid_keypress_event)
        self._cid_keypress_event = None

    def _initialize_callbacks(self):
        def _onpress(event):
            if not self._m.cb.get_execute_callbacks():
                return

            try:
                self._event = event

                # remember keypress event in case sticky modifiers are used for
                # click or pick callbacks
                k = str(event.key)

                if self._modifier is not None and (
                    k == "ctrl+" + self._modifier or k == "escape"
                ):
                    self._modifier = None
                    _log.info("EOmaps: sticky modifier set to: None")
                elif self._modifier != k:
                    methods = []
                    if k in self._m.cb.click._sticky_modifiers:
                        methods.append("click")

                    if k in self._m.cb.pick._sticky_modifiers:
                        methods.append("pick")

                    if k in self._m.cb.move._sticky_modifiers:
                        methods.append("move")

                    if methods:
                        _log.info(
                            "EOmaps: sticky modifier set to: "
                            f"{k} ({', '.join(methods)})"
                        )
                        self._modifier = k

                for obj in self._objs:
                    # only trigger callbacks on the right layer
                    if not self._execute_cb(obj._m.layer):
                        continue
                    if any(i in obj.get.cbs for i in (event.key, None)):
                        # do this to allow deleting callbacks with a callback
                        # otherwise modifying a dict during iteration is problematic!
                        cbs = {
                            **obj.get.cbs.get(event.key, dict()),
                            **obj.get.cbs.get(None, dict()),
                        }

                        names = list(cbs)
                        for name in names:
                            if name in cbs:
                                cbs[name](key=event.key)

                # DO NOT UPDATE in here!
                # otherwise keypress modifiers for peek-layer callbacks will
                # have glitches!
                # self._m.parent.BM.update(clear=self._method)
            except ReferenceError:
                pass

        if self._m is self._m.parent:
            self._cid_keypress_event = self._m.f.canvas.mpl_connect(
                "key_press_event", _onpress
            )

    class _attach(KeypressCallbacks):
        """
        Attach custom or pre-defined callbacks on keypress events.

        Each callback takes 1 additional keyword-arguments:

        key : str or None
            The key to use.

            - Modifiers are attached with a '+', e.g. "alt+d"
            - If None, the callback will be fired on any key!

        For additional keyword-arguments check the doc of the callback-functions!

        Examples
        --------
        Attach a pre-defined callback:

        >>> m.cb.keypress.attach.switch_layer(layer=1, key="1")

        Attach a custom callback:

        >>> def cb(**kwargs):
        >>>     ... do something ...
        >>>
        >>> m.cb.keypress.attach(cb, key="3")

        """

        def __init__(self, parent):
            self._parent = parent
            self._m = parent._m
            self._temporary_artists = self._parent._temporary_artists

        def __call__(self, f, key, **kwargs):
            """
            Add a custom callback-function to the map.

            Parameters
            ----------
            f : callable
                the function to attach to the map.
                The call-signature is:

                >>> def some_callback(asdf, **kwargs):
                >>>     print("hello world, asdf=", asdf)
                >>>
                >>> m.cb.attach(some_callback, asdf=1)
            key : str or None
                The key to use.

                - Modifiers are attached with a '+', e.g. "alt+d"
                - If None, the callback will be fired on any key!

            **kwargs :
                kwargs passed to the callback-function
                For documentation of the individual functions check the docs in `m.cb`

            Returns
            -------
            cid : int
                the ID of the attached callback

            """
            if key is not None and not isinstance(key, str):
                raise TypeError(
                    "EOmaps: The 'key' for keypress-callbacks must be a string!"
                )

            return self._parent._add_callback(f, key, **kwargs)

        @classmethod
        def _available_callbacks(cls):
            return list(filter(lambda x: not x.startswith("_"), dir(cls)))

    class _get:
        """Accessor for objects generated/retrieved by callbacks."""

        def __init__(self, parent):
            self.m = parent._m
            self.cbs = dict()

        @property
        def attached_callbacks(self):
            """Get a list of all IDs of attached callbacks."""
            cbs = []
            for key, cbdict in self.cbs.items():
                for name, cb in cbdict.items():
                    cbs.append(f"{name}__{key}")

            return cbs

    # to make namespace accessible for sphinx
    attach = _attach
    get = _get

    def _parse_cid(self, cid):
        name, rest = cid.split("__", 1)
        layer, key = rest.rsplit("__", 1)

        return name, layer, key

    def remove(self, callback=None):
        """
        Remove an attached callback from the figure.

        Parameters
        ----------
        callback : int, str or tuple
            if str: the name of the callback to remove
                    (`<function_name>_<count>__<layer>__<key>`)

        """
        if callback is not None:
            name, layer, key = self._parse_cid(callback)

        cbname = name + "__" + layer

        cbs = self.get.cbs.get(key, None)

        if cbs is not None:
            if cbname in cbs:
                del cbs[cbname]

                # call cleanup methods on removal
                fname = name.rsplit("_", 1)[0]
                if hasattr(self._attach, f"_{fname}_cleanup"):
                    getattr(self._attach, f"_{fname}_cleanup")()
            else:
                _log.error(f"EOmaps: there is no callback named {callback}")
        else:
            _log.error(f"EOmaps: there is no callback named {callback}")

    def _add_callback(self, callback, key="x", **kwargs):
        """
        Attach a callback to the plot that will be executed if a key is pressed.

        A list of pre-defined callbacks (accessible via `m.cb`) or customly defined
        functions can be used.

            >>> # to add a pre-defined callback use:
            >>> cid = m._add_callback("annotate", <kwargs passed to m.cb.annotate>)
            >>> # to remove the callback again, call:
            >>> m.remove_callback(cid)

        Parameters
        ----------
        callback : callable or str
            The callback-function to attach.

        key : str or None
            The key to use.

            - Modifiers are attached with a '+', e.g. "alt+d"
            - If None, the callback will be fired on any key!

        **kwargs :
            kwargs passed to the callback-function
            For documentation of the individual functions check the docs in `m.cb`

        Returns
        -------
        cbname : str
            the identification string of the callback
            (to remove the callback, use `m.cb.remove(cbname)`)

        """
        if isinstance(callback, str):
            assert hasattr(self._attach, callback), (
                f"The function '{callback}' does not exist as a pre-defined callback."
                + " Use one of:\n    - "
                + "\n    - ".join(self._attach._available_callbacks())
            )
            callback = getattr(self._attach, callback)

        cbdict = self.get.cbs.setdefault(key, dict())

        # get a unique name for the callback
        ncb = [
            int(i.rsplit("__", 1)[0].rsplit("_", 1)[1])
            for i in cbdict
            if i.startswith(callback.__name__)
        ]
        cbkey = (
            callback.__name__
            + f"_{max(ncb) + 1 if len(ncb) > 0 else 0}"
            + f"__{self._m.layer}"
        )

        # append the callback
        cbdict[cbkey] = partial(callback, **kwargs)

        return cbkey + f"__{key}"


class CallbackContainer:
    """
    Accessor for attaching callbacks and accessing return-objects.

    Methods
    -------
    click : Execute functions when clicking on the map
    move : Execute functions when clicking on the map
    keypress : Execute functions if you press a key on the keyboard
    pick : Execute functions that "pick" the closest datapoint(s)

    """

    pick = PickContainer
    click = ClickContainer
    move = MoveContainer
    keypress = KeypressContainer

    def __init__(self, m):
        self._m = m

        self._methods = {
            "click",
            "pick",
            "move",
            "keypress",
            "_click_move",
            "_always_active",
        }

        self.click = ClickContainer(
            m=self._m,
            cb_cls=ClickCallbacks,
            method="click",
        )
        # internal "always_active" click container to handle click-callbacks
        # that should be executed even if m._execute_callbacks is False.
        # (used in AnnotationEditor)
        self._always_active = ClickContainer(
            m=self._m,
            cb_cls=ClickCallbacks,
            method="_always_active",
        )

        # a move-container that shares temporary artists with the click-container
        self._click_move = MoveContainer(
            m=self._m,
            cb_cls=MoveCallbacks,
            method="_click_move",
            parent_container=self.click,
            button_down=True,
        )

        self.move = MoveContainer(
            m=self._m,
            cb_cls=MoveCallbacks,
            method="move",
            button_down=False,
            default_button=None,
        )

        self.pick = PickContainer(
            m=self._m,
            cb_cls=PickCallbacks,
            method="pick",
        )

        self.keypress = KeypressContainer(
            m=self._m,
            cb_cls=KeypressCallbacks,
            method="keypress",
        )

    def get_execute_callbacks(self):
        """
        Get if callbacks should be executed or not.

        Returns
        -------
        bool
            If True, callbacks are executed.

        """
        return self._m.parent._execute_callbacks

    def execute_callbacks(self, val):
        """
        Activate / deactivate triggering callbacks.

        Parameters
        ----------
        val : bool
            If True, callbacks will be executed.
        """
        self._m.parent._execute_callbacks = val

    def add_picker(self, name, artist, picker):
        """
        Attach a custom picker to an artist.

        Once attached, callbacks can be assigned just like the default
        click/pick callbacks via:

            >>> m.cb.pick__<name>. ...

        Parameters
        ----------
        name : str, optional
            a unique identifier that will be used to identify the pick method.
        artist : a matplotlib artist, optional
            the artist that should become pickable.
            (it must support `artist.set_picker()`)
            The default is None.
        picker : callable, optional
            A callable that is used to perform the picking.
            The default is None, in which case the default picker is used.
            The call-signature is:

            >>> def picker(artist, mouseevent):
            >>>     # if the pick is NOT successful:
            >>>     return False, dict()
            >>>     ...
            >>>     # if the pick is successful:
            >>>     return True, dict(ID, pos, val, ind)

        Note
        ----
        If the name starts with an underscore (e.g. "_MyPicker") then the
        associated container will be accessible via `m.cb._pick__MyPicker`
        or via `m.cb.pick["_MyPicker"]`. (This is useful to setup pickers that
        are only used internally)
        """
        name = str(name)

        if picker is not None:
            assert name != "default", "'default' is not a valid picker name!"

        # if it already exists, return the existing one
        assert not hasattr(self._m.cb, name), "the picker '{name}' is already attached!"

        if name == "default":
            method = "pick"
        else:
            if name.startswith("_"):
                method = "_pick__" + name[1:]
            else:
                method = "pick__" + name

        new_pick = PickContainer(
            m=self._m,
            cb_cls=PickCallbacks,
            method=method,
            picker_name=name,
            picker=picker,
        )
        new_pick.__doc__ == PickContainer.__doc__
        new_pick._set_artist(artist)
        new_pick._init_cbs()

        # add the picker method to the accessible cbs
        setattr(self._m.cb, new_pick._method, new_pick)
        self._methods.add(new_pick._method)

        return new_pick

    def _init_cbs(self):
        for method in self._methods:
            obj = getattr(self, method)
            obj._init_cbs()

        self._remove_default_keymaps()

    def _clear_callbacks(self):
        # clear all callback containers
        for method in self._methods:
            obj = getattr(self, method)
            obj.get.cbs.clear()

    def _reset_cids(self):
        # reset the callback functions (required to re-attach the callbacks
        # in case the figure is closed and re-initialized)
        for method in self._methods:
            obj = getattr(self, method)
            obj._reset_cids()

    @staticmethod
    def _remove_default_keymaps():
        # unattach default keymaps to avoid interaction with keypress events
        assignments = dict()
        assignments["keymap.back"] = ["c", "left"]
        assignments["keymap.forward"] = ["v", "right"]
        assignments["keymap.grid"] = ["g"]
        assignments["keymap.grid_minor"] = ["G"]
        assignments["keymap.home"] = ["h", "r"]
        assignments["keymap.quit"] = ["q"]
        assignments["keymap.save"] = ["s"]
        assignments["keymap.xscale"] = ["k", "L"]
        assignments["keymap.yscale"] = ["l"]

        for key, val in assignments.items():
            for v in val:
                try:
                    plt.rcParams[key].remove(v)
                except Exception:
                    pass

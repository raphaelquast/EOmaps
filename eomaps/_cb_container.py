from eomaps.callbacks import (
    click_callbacks,
    pick_callbacks,
    keypress_callbacks,
    move_callbacks,
)
from types import SimpleNamespace

from functools import update_wrapper, partial, wraps
from collections import defaultdict
import matplotlib.pyplot as plt

from pyproj import Transformer

import numpy as np


class _cb_container(object):
    """base-class for callback containers"""

    def __init__(self, m, cb_class=None, method="click", tmp_artists=None):
        self._m = m

        if tmp_artists is None:
            self._temporary_artists = []
        else:
            self._temporary_artists = tmp_artists

        self._cb = cb_class(m, self._temporary_artists)
        self._cb_list = cb_class._cb_list

        self.attach = self._attach(self)
        self.get = self._get(self)

        self._fwd_cbs = dict()

        self._method = method
        self._event = None

    def _getobj(self, m):
        """get the equivalent callback container on another maps object"""
        return getattr(m.cb, self._method, None)

    @property
    def _objs(self):
        """
        get the callback-container objects associated with the axes that
        the event belonged to
        """
        # Note: it is possible that more than 1 Maps objects are
        # assigned to the same axis!
        objs = []
        if self._event is not None:
            if hasattr(self._event, "mouseevent"):
                event = self._event.mouseevent
            else:
                event = self._event

            for m in [*self._m.parent._children, self._m.parent]:
                # don't use "is" in here since Maps-children are proxies
                # (and so are their attributes)!
                if event.inaxes == m.figure.ax:
                    obj = self._getobj(m)
                    if obj is not None:
                        objs.append(obj)
        return objs

    def _clear_temporary_artists(self):
        while len(self._temporary_artists) > 0:
            art = self._temporary_artists.pop(-1)
            self._m.BM._artists_to_clear[self._method].append(art)

    def _sort_cbs(self, cbs):
        if not cbs:
            return set()
        cbnames = set([i.rsplit("__", 1)[0].rsplit("_", 1)[0] for i in cbs])
        sortp = self._cb_list + list(set(self._cb_list) ^ cbnames)
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
        Forward callback-events from this Maps-object to other Maps-objects

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
        Share callback-events between this Maps-object and all other Maps-objects

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

    def add_temporary_artist(self, artist):
        """
        Make an artist temporary (remove it from the map at the next event)

        Parameters
        ----------
        artist : matplotlib.artist
            the artist to use
        """
        self._m.BM.add_artist(artist)
        self._temporary_artists.append(artist)


class _click_container(_cb_container):
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

    class _attach:
        """
        Attach custom or pre-defined callbacks to the map.

        Each callback-function takes 2 additional keyword-arguments:

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

        Examples:
        ---------
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

            # attach pre-defined callbacks
            for cb in self._parent._cb_list:
                setattr(
                    self,
                    cb,
                    update_wrapper(
                        partial(self._parent._add_callback, callback=cb),
                        getattr(self._parent._cb, cb),
                    ),
                )

        def __call__(self, f, double_click=False, button=None, modifier=None, **kwargs):
            """
            add a custom callback-function to the map

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

            if self._parent._method == "pick":
                assert (
                    self._parent._m.figure.coll is not None
                ), "you can only attach pick-callbacks after calling `plot_map()`!"

            return self._parent._add_callback(
                callback=f,
                double_click=double_click,
                button=button,
                modifier=modifier,
                **kwargs,
            )

    class _get:
        """
        Accessor for objects generated/retrieved by callbacks.
        """

        def __init__(self, parent):
            self.m = parent._m
            self.cb = parent._cb

            self.cbs = defaultdict(lambda: defaultdict(dict))

        @property
        def picked_object(self):
            if hasattr(self.cb, "picked_object"):
                return self.cb.picked_object
            else:
                print("EOmaps: attach the 'load' callback first!")

        @property
        def picked_vals(self):
            if hasattr(self.cb, "picked_vals"):
                return self.cb.picked_vals
            else:
                print("EOmaps: attach the 'get_vals' callback first!")

        @property
        def permanent_markers(self):
            if hasattr(self.cb, "permanent_markers"):
                return self.cb.permanent_markers
            else:
                print("EOmaps: attach the 'mark' callback with 'permanent=True' first!")

        @property
        def permanent_annotations(self):
            if hasattr(self.cb, "permanent_annotations"):
                return self.cb.permanent_annotations
            else:
                print(
                    "EOmaps: attach the 'annotate' callback with 'permanent=True' first!"
                )

        @property
        def attached_callbacks(self):
            cbs = []
            for ds, dsdict in self.cbs.items():
                for b, bdict in dsdict.items():
                    for name in bdict.keys():
                        cbs.append(f"{name}__{ds}__{b}")

            return cbs

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

        if callback is not None:
            s = callback.split("__")
            name, layer, ds, b, m = s

        cbname = name + "__" + layer
        bname = f"{b}__{m}"
        dsdict = self.get.cbs.get(ds, None)

        if dsdict is not None:
            if bname in dsdict:
                bdict = dsdict.get(bname)
            else:
                print(f"EOmaps: there is no callback named {callback}")
                return
        else:
            print(f"EOmaps: there is no callback named {callback}")
            return

        if bdict is not None:
            if cbname in bdict:
                del bdict[cbname]

                # call cleanup methods on removal
                fname = name.rsplit("_", 1)[0]
                if hasattr(self._cb, f"_{fname}_cleanup"):
                    getattr(self._cb, f"_{fname}_cleanup")()
            else:
                print(f"EOmaps: there is no callback named {callback}")

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

    def _add_callback(
        self,
        *args,
        callback=None,
        double_click=False,
        button=None,
        modifier=None,
        **kwargs,
    ):
        """
        Attach a callback to the plot that will be executed if a pixel is clicked

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
        on_motion : bool
            !! Only relevant for "click" callbacks !!

            - True: Continuously execute the callback if the mouse is moved while the
              assigned button is pressed.
            - False: Only execute the callback on clicks.

            The default is True.
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
            assert self._m.figure.coll is not None, (
                "you can only attach pick-callbacks after plotting a dataset!"
                + "... use `m.plot_map()` first."
            )

        # attach "on_move" callbacks
        movecb_name = None
        # set on_motion True for "click" callbacks and False otherwise
        on_motion = kwargs.pop("on_motion", True if self._method == "click" else False)
        if self._method == "click" and on_motion is True:
            movecb_name = self._m.cb._click_move._add_callback(
                *args,
                callback=callback,
                double_click=double_click,
                button=button,
                modifier=modifier,
                **kwargs,
            )
        elif on_motion is True:
            print("EOmaps: 'on_motion=True' is only possible for 'click' callbacks!")

        assert not all(
            i in kwargs for i in ["pos", "ID", "val", "double_click", "button"]
        ), 'the names "pos", "ID", "val" cannot be used as keyword-arguments!'

        if isinstance(callback, str):
            assert hasattr(self._cb, callback), (
                f"The function '{callback}' does not exist as a pre-defined callback."
                + " Use one of:\n    - "
                + "\n    - ".join(self._cb_list)
            )
            callback = getattr(self._cb, callback)

        if double_click is True:
            btn_key = "double"
        elif double_click == "release":
            btn_key = "release"
        else:
            btn_key = "single"

        # check for modifiers
        button_modifier = f"{button}__{modifier}"

        d = self.get.cbs[btn_key][button_modifier]

        # get a unique name for the callback
        # name_idx__layer
        ncb = [
            int(i.split("__", 1)[0].rsplit("_", 1)[1])
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


class cb_click_container(_click_container):
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

    def _onclick(self, event):
        clickdict = self._get_clickdict(event)

        if event.dblclick:
            cbs = self.get.cbs["double"]
        else:
            cbs = self.get.cbs["single"]

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
            bcbs = cbs[button_modifier]

            for key in self._sort_cbs(bcbs):
                layer = key.split("__")[1]
                if layer != "all" and layer != str(self._m.BM.bg_layer):
                    return

                cb = bcbs[key]
                if clickdict is not None:
                    cb(**clickdict)

    def _onrelease(self, event):
        cbs = self.get.cbs["release"]

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
        if self._cid_button_press_event:
            self._m.figure.f.canvas.mpl_disconnect(self._cid_button_press_event)
        self._cid_button_press_event = None

        if self._cid_motion_event:
            self._m.figure.f.canvas.mpl_disconnect(self._cid_motion_event)
        self._cid_motion_event = None

        if self._cid_button_release_event:
            self._m.figure.f.canvas.mpl_disconnect(self._cid_button_release_event)
        self._cid_button_release_event = None

    def _add_click_callback(self):
        def clickcb(event):
            try:
                self._event = event

                # ignore callbacks while dragging axes
                if self._m._ignore_cb_events:
                    return
                # don't execute callbacks if a toolbar-action is active
                if (
                    self._m.figure.f.canvas.toolbar is not None
                ) and self._m.figure.f.canvas.toolbar.mode != "":
                    return

                # execute onclick on the maps object that belongs to the clicked axis
                # and forward the event to all forwarded maps-objects

                for obj in self._objs:
                    # clear temporary artists before executing new callbacks to avoid
                    # having old artists around when callbacks are triggered again
                    obj._clear_temporary_artists()
                    self._m.BM._clear_temp_artists(self._method)
                    obj._onclick(event)

                    # forward callbacks to the connected maps-objects
                    obj._fwd_cb(event)

                self._m.parent.BM.update(clear=self._method)
            except ReferenceError:
                pass

        def releasecb(event):
            try:
                # ignore callbacks while dragging axes
                if self._m._ignore_cb_events:
                    return
                # don't execute callbacks if a toolbar-action is active
                if (
                    self._m.figure.f.canvas.toolbar is not None
                ) and self._m.figure.f.canvas.toolbar.mode != "":
                    return

                # clear temporary click artists when the mouse-button is released
                self._m.BM._clear_temp_artists(self._method)

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
            # self._m.parent.BM.update(clear=False)

        if self._cid_button_press_event is None:
            # ------------- add a callback
            self._cid_button_press_event = self._m.figure.f.canvas.mpl_connect(
                "button_press_event", clickcb
            )

        if self._cid_button_release_event is None:
            # ------------- add a callback
            self._cid_button_release_event = self._m.figure.f.canvas.mpl_connect(
                "button_release_event", releasecb
            )

    def _fwd_cb(self, event):
        # click container events are MouseEvents!
        if event.inaxes != self._m.figure.ax:
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
                    inaxes=m.figure.ax,
                    dblclick=event.dblclick,
                    button=event.button,
                    xdata=xdata,
                    ydata=ydata,
                    key=event.key
                    # x=event.mouseevent.x,
                    # y=event.mouseevent.y,
                )

                obj._onclick(dummymouseevent)
                # append clear-action again since it will already be executed
                # by the first click!
                m.BM._after_update_actions.append(obj._clear_temporary_artists)


class cb_move_container(cb_click_container):
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

    # this is just a copy of cb_click_container to manage motion-sensitive callbacks

    def __init__(self, button_down=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._cid_motion_event = None

        self._button_down = button_down

    def _init_cbs(self):
        if self._m.parent is self._m:
            self._add_move_callback()

    def _reset_cids(self):
        if self._cid_motion_event:
            self._m.figure.f.canvas.mpl_disconnect(self._cid_motion_event)
        self._cid_motion_event = None

    def _add_move_callback(self):
        def movecb(event):
            try:
                self._event = event
                # only execute movecb if a mouse-button is holded down
                # and only if the motion is happening inside the axes
                if self._button_down:
                    if not event.button:  # or (event.inaxes != self._m.figure.ax):
                        # always clear temporary move-artists
                        if self._method == "move":
                            for obj in self._objs:
                                obj._clear_temporary_artists()
                            self._m.BM._clear_temp_artists(self._method)
                        return
                else:
                    if event.button:  # or (event.inaxes != self._m.figure.ax):
                        # always clear temporary move-artists
                        if self._method == "move":
                            for obj in self._objs:
                                obj._clear_temporary_artists()
                            self._m.BM._clear_temp_artists(self._method)
                        return

                # ignore callbacks while dragging axes
                if self._m._ignore_cb_events:
                    return
                # don't execute callbacks if a toolbar-action is active
                if (
                    self._m.figure.f.canvas.toolbar is not None
                ) and self._m.figure.f.canvas.toolbar.mode != "":
                    return

                # execute onclick on the maps object that belongs to the clicked axis
                # and forward the event to all forwarded maps-objects
                for obj in self._objs:
                    # clear temporary artists before executing new callbacks to avoid
                    # having old artists around when callbacks are triggered again
                    obj._clear_temporary_artists()
                    self._m.BM._clear_temp_artists(self._method)
                    obj._onclick(event)

                    # forward callbacks to the connected maps-objects
                    obj._fwd_cb(event)

                self._m.parent.BM.update(clear=self._method)
            except ReferenceError:
                pass

        if self._cid_motion_event is None:
            # for click-callbacks, allow motion-detection
            self._cid_motion_event = self._m.figure.f.canvas.mpl_connect(
                "motion_notify_event", movecb
            )


class cb_pick_container(_click_container):
    """
    Callbacks that select the nearest datapoint if you click on the map.
    (you must plot a dataset with `m.plot_map()` first!)

    The event will search for the closest data-point and execute the callback
    with the properties (e.g. position , ID, value) of the selected point.

    Note
    ----
    The threshold for the default picker can be set via the `pick_distance` argument.
    Use `m.plot_map(pick_distance=20)` to specify the maximal distance (in pixels)
    that is used to identify the closest datapoint.

    Methods
    --------
    attach : accessor for callbacks.
        Executing the functions will attach the associated callback to the map!

    get : accessor for return-objects
        A container to provide easy-access to the return-values of the callbacks.

    remove : remove prviously added callbacks from the map

    forward_events : forward events to connected maps-objects

    share_events : share events between connected maps-objects (e.g. forward both ways)

    set_sticky_modifiers : define keypress-modifiers that remain active after release

    """

    def __init__(self, picker_name="default", picker=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cid_pick_event = dict()
        self._picker_name = picker_name
        self._artist = None
        self._pick_distance = np.inf

        if picker is None:
            self._picker = self._default_picker
        else:
            self._picker = picker

    def __getitem__(self, name):
        name = str(name)
        if name.startswith("_"):
            container_name = "_pick__" + name[1:]
        else:
            container_name = "pick__" + name

        if hasattr(self._m.cb, container_name):
            return getattr(self._m.cb, container_name)
        else:
            print(
                f"the picker {name} does not exist...", "use `m.cb.add_picker` first!"
            )

    def _set_artist(self, artist):
        self._artist = artist
        self._artist.set_picker(self._picker)

    def _init_cbs(self):
        # if self._m.parent is self._m:
        self._add_pick_callback()

    def _default_picker(self, artist, event):

        # make sure that objects are only picked if we are on the right layer
        if self._m.layer != "all" and self._m.layer != self._m.BM.bg_layer:
            return False, None

        try:
            # if no pick-callback is attached, don't identify the picked point
            if len(self._m.cb.pick.get.cbs) == 0:
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

        # find the closest point to the clicked pixel
        dist, index = self._m.tree.query((event.xdata, event.ydata))

        if index is not None:
            return True, dict(
                ind=index, dblclick=event.dblclick, button=event.button, dist=dist
            )
        else:
            return True, dict(
                ind=None, dblclick=event.dblclick, button=event.button, dist=dist
            )

        return False, None

    def _get_pickdict(self, event):
        ind = event.ind
        if ind is not None:
            if self._m.figure.coll is not None and event.artist is self._m.figure.coll:
                clickdict = dict(
                    pos=(
                        self._m._props["x0"].flat[ind],
                        self._m._props["y0"].flat[ind],
                    ),
                    ID=self._m._props["ids"].flat[ind],
                    val=self._m._props["z_data"][ind],
                    ind=ind,
                    picker_name=self._picker_name,
                )
            else:
                clickdict = dict(
                    ID=getattr(event, "ID", None),
                    pos=getattr(
                        event, "pos", (event.mouseevent.xdata, event.mouseevent.ydata)
                    ),
                    val=getattr(event, "val", None),
                    ind=getattr(event, "ind", None),
                    picker_name=self._picker_name,
                )
            return clickdict

    def _onpick(self, event):
        if event.artist is not self._artist:
            return

        # only execute onpick if the correct layer is visible
        # (relevant for forwarded callbacks)
        if self._m.layer != "all" and self._m.layer != self._m.BM.bg_layer:
            return

        # don't execute callbacks if a toolbar-action is active
        if (
            self._m.figure.f.canvas.toolbar is not None
        ) and self._m.figure.f.canvas.toolbar.mode != "":
            return

        clickdict = self._get_pickdict(event)

        if event.mouseevent.dblclick:
            cbs = self.get.cbs["double"]
        else:
            cbs = self.get.cbs["single"]

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
                layer = key.split("__")[1]
                if layer != "all" and layer != str(self._m.BM.bg_layer):
                    # TODO
                    # only execute callbacks if the layer name of the associated
                    # maps-object is active
                    return

                cb = bcbs[key]
                if clickdict is not None:
                    cb(**clickdict)

    def _reset_cids(self):
        for method, cid in self._cid_pick_event.items():
            self._m.figure.f.canvas.mpl_disconnect(cid)
        self._cid_pick_event.clear()

    def _add_pick_callback(self):
        # execute onpick and forward the event to all connected Maps-objects

        def pickcb(event):
            try:

                # make sure pickcb is only executed if we are on the right layer
                if self._m.layer != "all" and self._m.layer != self._m.BM.bg_layer:
                    return

                # check if we want to ignore callbacks
                if self._m._ignore_cb_events:
                    return

                # don't execute callbacks if a toolbar-action is active
                if (
                    self._m.figure.f.canvas.toolbar is not None
                ) and self._m.figure.f.canvas.toolbar.mode != "":
                    return

                if not self._artist is event.artist:
                    return

                # make sure temporary artists are cleared before executing new callbacks
                # to avoid having old artists around when callbacks are triggered again
                self._m.BM._clear_temp_artists(self._method)

                self._event = event
                # check if the artists has a custom picker assigned

                self._m.BM._clear_temp_artists(self._method)

                # execute "_onpick" on the maps-object that belongs to the clicked axes
                # and forward the event to all forwarded maps-objects
                self._onpick(event)
                # forward callbacks to the connected maps-objects
                self._fwd_cb(event, self._picker_name)

                self._m.BM._after_update_actions.append(self._clear_temporary_artists)
                self._m.BM._clear_temp_artists(self._method)

                # self._m.parent.BM.update(clear=self._method)
                self._m.parent.BM._clear_temp_artists(self._method)
                # don't update here... the click-callback will take care of it!
            except ReferenceError:
                pass

        # attach the callbacks (only once per method!)
        if self._method not in self._cid_pick_event:
            self._cid_pick_event[self._method] = self._m.figure.f.canvas.mpl_connect(
                "pick_event", pickcb
            )

    def _fwd_cb(self, event, picker_name):
        # PickEvents have a .mouseevent property for the associated MouseEvent!
        if event.mouseevent.inaxes != self._m.figure.ax:
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
                inaxes=m.figure.ax,
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
                # inaxes=m.figure.ax,
                mouseevent=dummymouseevent,
                # picker_name=picker_name,
            )

            pick = obj._picker(obj._artist, dummymouseevent)

            if pick[1] is not None:
                dummyevent.ID = pick[1].get("ID", None)
                dummyevent.ind = pick[1].get("ind", None)
                dummyevent.val = pick[1].get("val", None)

                if "dist" in pick[1]:
                    dummyevent.dist = pick[1].get("dist", None)
            else:
                dummyevent.ind = None
                dummyevent.dist = None

            obj._onpick(dummyevent)
            m.BM._after_update_actions.append(obj._clear_temporary_artists)


class keypress_container(_cb_container):
    """
    Callbacks that are executed if you press a key on the keyboard.

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

    def __init__(self, m, cb_cls=None, method="keypress"):
        super().__init__(m, cb_cls, method)

        self._cid_keypress_event = None

        # remember last pressed key (for use as "sticky_modifier")
        self._modifier = None

    def _init_cbs(self):
        if self._m.parent is self._m:
            self._initialize_callbacks()

    def _reset_cids(self):
        if self._cid_keypress_event:
            self._m.figure.f.canvas.mpl_disconnect(self._cid_keypress_event)
        self._cid_keypress_event = None

    def _initialize_callbacks(self):
        def _onpress(event):
            try:
                if self._m.parent._layout_editor._modifier_pressed:
                    return

                self._event = event

                # remember keypress event in case sticky modifiers are used for
                # click or pick callbacks
                k = str(event.key)

                if self._modifier is not None and (
                    k == "ctrl+" + self._modifier or k == "escape"
                ):
                    self._modifier = None
                    print("EOmaps: sticky modifier: None")
                elif self._modifier != k:
                    methods = []
                    if k in self._m.cb.click._sticky_modifiers:
                        methods.append("click")

                    if k in self._m.cb.pick._sticky_modifiers:
                        methods.append("pick")

                    if k in self._m.cb.move._sticky_modifiers:
                        methods.append("move")

                    if methods:
                        print(f"EOmaps: sticky modifier: {k} ({', '.join(methods)})")
                        self._modifier = k

                update = False
                for obj in self._objs:
                    # only trigger callbacks on the right layer
                    if (obj._m.layer != "all") and (
                        obj._m.layer != self._m.BM.bg_layer
                    ):
                        continue
                    if event.key in obj.get.cbs:
                        update = True
                        # do this to allow deleting callbacks with a callback
                        # otherwise modifying a dict during iteration is problematic!
                        cbs = obj.get.cbs[event.key]
                        names = list(cbs)
                        for name in names:
                            if name in cbs:
                                cbs[name](key=event.key)
                if update:
                    self._m.parent.BM.update(clear=self._method)
            except ReferenceError:
                pass

        if self._m is self._m.parent:
            self._cid_keypress_event = self._m.figure.f.canvas.mpl_connect(
                "key_press_event", _onpress
            )

    class _attach:
        """
        Attach custom or pre-defined callbacks on keypress events.

        Each callback takes 1 additional keyword-arguments:

        key : str
            the key to use
            (modifiers are attached with a '+', e.g. "alt+d" )

        For additional keyword-arguments check the doc of the callback-functions!

        Examples
        --------

            >>> m.cb.keypress.attach.switch_layer(layer=1, key="1")

        """

        def __init__(self, parent):
            self._parent = parent

            # attach pre-defined callbacks
            for cb in self._parent._cb_list:
                setattr(
                    self,
                    cb,
                    update_wrapper(
                        partial(self._parent._add_callback, callback=cb),
                        getattr(self._parent._cb, cb),
                    ),
                )

        def __call__(self, f, key, **kwargs):
            """
            add a custom callback-function to the map

            Parameters
            ----------
            f : callable
                the function to attach to the map.
                The call-signature is:

                >>> def some_callback(asdf, **kwargs):
                >>>     print("hello world, asdf=", asdf)
                >>>
                >>> m.cb.attach(some_callback, asdf=1)

            key : str
                the key to use
                (modifiers are attached with a '+', e.g. "alt+d" )

            **kwargs :
                kwargs passed to the callback-function
                For documentation of the individual functions check the docs in `m.cb`

            Returns
            -------
            cid : int
                the ID of the attached callback

            """

            if not isinstance(key, str):
                raise TypeError(
                    "EOmaps: The 'key' for keypress-callbacks must be a string!"
                )

            return self._parent._add_callback(f, key, **kwargs)

    class _get:
        def __init__(self, parent):
            self.m = parent._m
            self.cb = parent._cb

            self.cbs = defaultdict(dict)

        @property
        def attached_callbacks(self):
            cbs = []
            for key, cbdict in self.cbs.items():
                for name, cb in cbdict.items():
                    cbs.append(f"{name}__{key}")

            return cbs

    def remove(self, callback=None):
        """
        remove an attached callback from the figure

        Parameters
        ----------
        callback : int, str or tuple
            if str: the name of the callback to remove
                    (`<function_name>_<count>__<layer>__<key>`)
        """

        if callback is not None:
            name, layer, key = callback.split("__")

        cbname = name + "__" + layer

        cbs = self.get.cbs.get(key, None)

        if cbs is not None:
            if cbname in cbs:
                del cbs[cbname]

                # call cleanup methods on removal
                fname = name.rsplit("_", 1)[0]
                if hasattr(self._cb, f"_{fname}_cleanup"):
                    getattr(self._cb, f"_{fname}_cleanup")()
            else:
                print(f"EOmaps: there is no callback named {callback}")
        else:
            print(f"EOmaps: there is no callback named {callback}")

    def _add_callback(self, callback, key="x", **kwargs):
        """
        Attach a callback to the plot that will be executed if a key is pressed

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

        key : str
            the key to use
            (modifiers are attached with a '+', e.g. "alt+d" )

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
            assert hasattr(self._cb, callback), (
                f"The function '{callback}' does not exist as a pre-defined callback."
                + " Use one of:\n    - "
                + "\n    - ".join(self._cb_list)
            )
            callback = getattr(self._cb, callback)

        cbdict = self.get.cbs[key]
        # get a unique name for the callback
        ncb = [
            int(i.rsplit("_", 1)[1]) for i in cbdict if i.startswith(callback.__name__)
        ]
        cbkey = (
            callback.__name__
            + f"_{max(ncb) + 1 if len(ncb) > 0 else 0}"
            + f"__{self._m.layer}"
        )

        # append the callback
        cbdict[cbkey] = partial(callback, **kwargs)

        return cbkey + f"__{key}"


class cb_container:
    """
    Accessor for attaching callbacks and accessing return-objects.

    Methods
    -------

    - **click** : Execute functions when clicking on the map

    - **pick** : Execute functions when you "pick" a pixel on the  map
      - only available if a dataset has been plotted via `m.plot_map()`

    - **keypress** : Execute functions if you press a key on the keyboard

    """

    def __init__(self, m):
        self._m = m

        self._methods = ["click", "move", "keypress", "_click_move"]

        self._click = cb_click_container(
            m=self._m,
            cb_cls=click_callbacks,
            method="click",
        )
        # a move-container that shares temporary artists with the click-container
        self._click_move = cb_move_container(
            m=self._m,
            cb_cls=click_callbacks,
            method="_click_move",
            tmp_artists=self._click._temporary_artists,
            button_down=True,
        )

        self._move = cb_move_container(
            m=self._m,
            cb_cls=move_callbacks,
            method="move",
            button_down=False,
            default_button=None,
        )

        self._pick = cb_pick_container(
            m=self._m,
            cb_cls=pick_callbacks,
            method="pick",
        )

        self._keypress = keypress_container(
            m=self._m,
            cb_cls=keypress_callbacks,
            method="keypress",
        )

    @property
    @wraps(cb_click_container)
    def click(self):
        return self._click

    @property
    @wraps(cb_move_container)
    def move(self):
        return self._move

    @property
    @wraps(cb_pick_container)
    def pick(self):
        return self._pick

    @property
    @wraps(keypress_container)
    def keypress(self):
        return self._keypress

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
        associated container will be accessible via `m._cb._pick__MyPicker`
        or via `m.cb.pick["_MyPicker"]. (This is useful to setup pickers that
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

        new_pick = cb_pick_container(
            m=self._m,
            cb_cls=pick_callbacks,
            method=method,
            picker_name=name,
            picker=picker,
        )
        new_pick.__doc__ == cb_pick_container.__doc__
        new_pick._set_artist(artist)
        new_pick._init_cbs()

        # add the picker method to the accessible cbs
        setattr(self._m.cb, new_pick._method, new_pick)
        self._methods.append(new_pick._method)

        return new_pick

    def _init_cbs(self):
        for method in self._methods:
            obj = getattr(self, method)
            obj._init_cbs()

        self._remove_default_keymaps()

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
        assignments["keymap.pan"] = ["p"]
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

from matplotlib.legend import DraggableLegend
from matplotlib.lines import Line2D
from matplotlib.widgets import Slider
from functools import wraps


class SelectorButtons:
    # A custom button implementation that uses a legend as container-artist
    # ... adapted from https://stackoverflow.com/a/71323434/9703451
    def __init__(
        self,
        f,
        labels,
        active=None,
        activecolor="blue",
        inactive_color="w",
        size=10,
        **kwargs,
    ):
        """
        A class to add buttons to switch layers.

        Parameters
        ----------
        f : `matplotlib.Figure`
            The matplotlib figure to use
        labels : list of str
            The button labels.
        active : int
            The index of the initially selected button.
        activecolor : color
            The color of the selected button.
        size : float
            Size of the radio buttons
        Further parameters are passed on to `Legend`.
        """

        self.activecolor = activecolor
        self.inactive_color = inactive_color
        self.value_selected = None

        self._active = None

        self.labels = labels

        circles = []
        for label in labels:
            p = Line2D(
                [],
                [],
                markersize=size,
                marker="o",
                markeredgecolor="black",
                markerfacecolor=inactive_color,
                lw=0,
            )

            circles.append(p)

        kwargs.setdefault("frameon", True)
        kwargs.setdefault("loc", "upper center")

        self.leg = f.legend(circles, self.labels, **kwargs)

        self.circles = self.leg.legendHandles

        for c in self.circles:
            c.set_picker(10)

        f.canvas.mpl_connect("pick_event", self._clicked)

        self._draggable_box = None

        if active is None:
            self.set_active(self.circles[0])
        else:
            self.set_active(self.circles[self.labels.index(active)])

    def set_active(self, artist):
        if self._active is not None:
            self._active.set_markerfacecolor(self.inactive_color)

        if artist not in self.circles:
            self._active = None
            return

        self._active = artist
        self._active.set_markerfacecolor("r")

    def on_clicked(self, art):
        pass

    def _clicked(self, event):
        if event.mouseevent.button == 1 and event.artist in self.circles:
            self.set_active(event.artist)
            self.on_clicked(self.circles.index(event.artist))

    def set_draggable(self, b, m):
        """
        Enable or disable mouse dragging support for the buttons

        Parameters
        ----------
        b : bool
            Whether mouse dragging is enabled.
        """
        if b:
            if self._draggable_box is None:
                self._draggable_box = DraggableLegend_new(legend=self.leg, m=m)
        else:
            if self._draggable_box is not None:
                self._draggable_box.disconnect()
            self._draggable_box = None


class DraggableLegend_new(DraggableLegend):
    # Supercharce DraggableLegend use the EOmaps Blit-manager

    def __init__(self, m=None, *args, **kwargs):
        self._m = m
        super().__init__(*args, **kwargs)

    def on_motion(self, evt):
        if self._check_still_parented() and self.got_artist:
            dx = evt.x - self.mouse_x
            dy = evt.y - self.mouse_y
            self.update_offset(dx, dy)
            self._m.BM.update()

    def on_pick(self, evt):
        if self._check_still_parented() and evt.artist == self.ref_artist:
            self._m._ignore_cb_events = True
            self.mouse_x = evt.mouseevent.x
            self.mouse_y = evt.mouseevent.y
            self.got_artist = True
            self._c1 = self.canvas.mpl_connect("motion_notify_event", self.on_motion)
            self.save_offset()

    def on_release(self, event):
        if self._check_still_parented() and self.got_artist:
            self._m._ignore_cb_events = False
            self.finalize_offset()
            self.got_artist = False
            self.canvas.mpl_disconnect(self._c1)


class _layer_selector:
    def __init__(self, m):
        self._m = m

        self._sliders = []
        self._selectors = []

        # register a function to update all associated widgets on a layer-chance
        self._m.BM.on_layer(lambda m, l: self._update_widgets(l), persistent=True)

    def _update_widgets(self, l):
        # this function is called whenever the background-layer changed
        # to synchronize changes across all selectors and sliders
        # see setter for   helpers.BM._bg_layer
        for s in self._sliders:
            if l in s._labels:
                s.eventson = False
                s.set_val(s._labels.index(l))
                s.eventson = True

        for s in self._selectors:
            if l in s.labels:
                s.set_active(s.circles[s.labels.index(l)])

    def _new_selector(self, layers=None, draggable=True, exclude_layers=None, **kwargs):
        """
        Get a button-widget that can be used to select the displayed plot-layer.

        Note
        ----
        In general, layers are only drawn "on demand", so if you switch to a layer that
        has not been shown yet, it needs to be drawn first.

        - Depending on the complexity (WebMaps, Overlays, very large datasets etc.) this
          might take a few seconds.
        - Once the layer has been drawn, it is cached and switching between arbitrarily
          complex layers should be fast.
        - If the extent of the map changes (e.g. pan/zoom) or a new feature is added to
          the layer, it will be re-drawn.

        Parameters
        ----------
        layers : list or None, optional
            A list of layer-names that should appear in the selector.
            If None, all available layers (except the "all" layer) are shown.
            The default is None.
        draggable : bool, optional
            Indicator if the widget should be draggable or not.
            The default is True.
        exclude_layers : list or None
            A list of layer-names that should be excluded.
            Only relevant if `layers=None` is used.
            The default is None in which case only the "all" layer is excluded.
            (Same as `exclude = ["all"]`. Use `exclude=[]` to get all available layers.)
        kwargs :
            All additional arguments are passed to `plt.legend`

            Some useful arguments are:

            - ncol: the numer of columns to use
            - size: the size of the markers
            - fontsize: the fontsize of the labels
            - loc: the position of the widget with respect to the figure.
              Any combination of the strings ["upper", "lower"] and
              ["left", "right", "center"] is possible.
            - bbox_to_anchor: offset from the loc-position in figure coordinates
              e.g.: (loc="upper center", bbox_to_anchor=(0.5, 1.1))

        Returns
        -------
        s : SelectorButtons
            The SelectorButtons instance. To remove the widget, use `s.remove()`

        Examples
        --------
        >>> from eomaps import Maps
        >>> m = Maps(layer="coastline")
        >>> m2 = m.new_layer(layer="ocean")
        >>> m.add_feature.preset.coastline()
        >>> m2.add_feature.preset.ocean()
        >>> s = m.util.layer_selector()

        # to remove the widget, simply use
        >>> s.remove()

        """

        if layers is None:
            if exclude_layers is None:
                exclude_layers = ["all"]
            layers = self._m._get_layers(exclude=exclude_layers)

        assert (
            len(layers) > 0
        ), "EOmaps: There are no layers with artists available.. plot something first!"

        s = SelectorButtons(self._m.figure.f, layers, **kwargs)

        def update(val):
            l = layers[int(val)]

            # make sure we re-fetch the artist states on a layer change during
            # draggable-axes
            drag = self._m.parent._draggable_axes
            d = False
            if drag._modifier_pressed:
                drag._undo_draggable()
                d = True

            self._m.BM.bg_layer = l

            if d:
                drag._make_draggable()
            else:
                self._m.BM.update(blit=False)
                self._m.BM.canvas.draw_idle()

        s.on_clicked = update
        s.set_draggable(draggable, m=self._m)

        def remove():
            self._m.BM.remove_artist(s.leg)
            s.leg.remove()
            if s in self._selectors:
                self._selectors.remove(s)

        s.remove = remove

        self._m.BM.add_artist(s.leg)
        # keep a reference to the buttons to make sure they stay interactive
        self._selectors.append(s)

        # update widgets to make sure the right layer is selected
        self._update_widgets(self._m.BM.bg_layer)

        return s

    def _new_slider(
        self,
        layers=None,
        pos=None,
        txt_patch_props=None,
        exclude_layers=None,
        **kwargs,
    ):
        """
        Get a slider-widget that can be used to switch between layers.

        Note
        ----
        In general, layers are only drawn "on demand", so if you switch to a layer that
        has not been shown yet, it needs to be drawn first.

        - Depending on the complexity (WebMaps, Overlays, very large datasets etc.) this
          might take a few seconds.
        - Once the layer has been drawn, it is cached and switching between arbitrarily
          complex layers should be fast.
        - If the extent of the map changes (e.g. pan/zoom) or a new feature is added to
          the layer, it will be re-drawn.

        Parameters
        ----------
        layers : list or None, optional
            A list of layer-names that should appear in the selector.
            If None, all available layers (except the "all" layer) are shown.
            The default is None.
        pos : list or None, optional
            The position of the slider in figure-coordinates, provided as:
            (x0, y0, width, height).
            If None, the slider will be added at the bottom of the current axis.
            The default is None.
        txt_patch_props : dict or None
            A dict used to style the background-patch of the text (e.g. the layer-names)

            For example:

            >>> dict(fc="w", ec="none", alpha=0.75, boxstyle="round, pad=.25")

            - If None, no background patch will be added to the text.

            The default is None.
        exclude_layers : list or None
            A list of layer-names that should be excluded.
            Only relevant if `layers=None` is used.
            The default is None in which case only the "all" layer is excluded.
            (Same as `exclude = ["all"]`. Use `exclude=[]` to get all available layers.)
        kwargs :
            Additional kwargs are passed to matplotlib.widgets.Slider

            The default is
            >>> dict(initcolor="none",
            >>>      handle_style=dict(facecolor=".8", edgecolor="k", size=7),
            >>>      label=None,
            >>>      track_color="0.8",
            >>>      color="0.2"
            >>>      )


        Returns
        -------
        s : Slider
            The slider instance. To remove the widget, use `s.remove()`

        Examples
        --------
        >>> from eomaps import Maps
        >>> m = Maps(layer="coastline")
        >>> m2 = m.new_layer(layer="ocean")
        >>> m.add_feature.preset.coastline()
        >>> m2.add_feature.preset.ocean()
        >>> s = m.util.layer_slider()

        # to remove the widget, simply use
        >>> s.remove()

        """
        if layers is None:
            if exclude_layers is None:
                exclude_layers = ["all"]
            layers = self._m._get_layers(exclude=exclude_layers)

        assert (
            len(layers) > 0
        ), "EOmaps: There are no layers with artists available.. plot something first!"

        if pos is None:
            ax_slider = self._m.figure.f.add_axes(
                [
                    self._m.ax.get_position().x0,
                    self._m.ax.get_position().y0 - 0.05,
                    self._m.ax.get_position().width * 0.75,
                    0.05,
                ]
            )
        else:
            ax_slider = self._m.figure.f.add_axes(pos)

        kwargs.setdefault("color", ".2")  # remove start-position marker
        kwargs.setdefault("track_color", ".8")  # remove start-position marker
        kwargs.setdefault("initcolor", "none")  # remove start-position marker
        kwargs.setdefault("handle_style", dict(facecolor=".8", edgecolor="k", size=7))
        kwargs.setdefault("label", None)

        s = Slider(
            ax_slider, valmin=0, valmax=len(layers) - 1, valinit=0, valstep=1, **kwargs
        )
        s._labels = layers

        # add some background-patch style for the text
        if txt_patch_props is not None:
            s.valtext.set_bbox(txt_patch_props)

        def fmt(val):
            if val < len(layers):
                return layers[val]
            else:
                return "---"

        s._format = fmt
        s._handle.set_marker("D")

        s.track.set_edgecolor("none")
        h = s.track.get_height() / 2
        s.track.set_height(h)
        s.track.set_y(s.track.get_y() + h / 2)

        def update(val):
            l = layers[int(val)]
            # make sure we re-fetch the artist states on a layer change during
            # draggable-axes
            drag = self._m.parent._draggable_axes
            d = False
            if drag._modifier_pressed:
                drag._undo_draggable()
                d = True

            self._m.BM.bg_layer = l

            if d:
                drag._make_draggable()

            self._m.BM.update()

        self._m.BM.add_artist(ax_slider)

        s.on_changed(update)

        # keep a reference to the slider to make sure it stays interactive
        self._sliders.append(s)

        def remove():
            self._m.BM.remove_artist(ax_slider)
            s.disconnect_events()
            ax_slider.remove()
            if s in self._sliders:
                self._sliders.remove(s)
            self._m.BM.update()

        s.remove = remove

        # update widgets to make sure the right layer is selected
        self._update_widgets(self._m.BM.bg_layer)

        return s

    @wraps(_new_selector)
    def __call__(self, method, *args, **kwargs):
        if method == "buttons":
            self._new_selector(*args, **kwargs)
        elif method == "slider":
            self._new_slider(*args, **kwargs)
        else:
            raise TypeError(f"'{self._method}' is not a valid layer-selector method")


class utilities:
    """
    A collection of utility tools that can be added to EOmaps plots
    """

    def __init__(self, m):
        self._m = m

        self._layer_selector = _layer_selector(m)

    @property
    @wraps(_layer_selector._new_selector)
    def layer_selector(self):
        return self._layer_selector._new_selector

    @property
    @wraps(_layer_selector._new_slider)
    def layer_slider(self):
        return self._layer_selector._new_slider

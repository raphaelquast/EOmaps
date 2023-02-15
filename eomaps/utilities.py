from matplotlib.legend import DraggableLegend
from matplotlib.lines import Line2D
from matplotlib.widgets import Slider
from functools import wraps
from matplotlib.pyplot import Artist, rcParams


class SelectorButtons(Artist):
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
        super().__init__()

        self.activecolor = activecolor
        self.inactive_color = inactive_color
        self.marker_size = size
        self.value_selected = None

        self._active = None

        self.labels = labels

        circles = []
        for label in labels:
            p = Line2D(
                [],
                [],
                markersize=self.marker_size,
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
            if len(self.circles) > 0:
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
            self.legend.stale = True
            self._m.BM.update()

    def on_pick(self, evt):
        if self._check_still_parented() and evt.artist == self.ref_artist:
            self._m.cb.execute_callbacks(False)
            self.mouse_x = evt.mouseevent.x
            self.mouse_y = evt.mouseevent.y
            self.got_artist = True
            self._c1 = self.canvas.mpl_connect("motion_notify_event", self.on_motion)
            self.save_offset()

    def on_release(self, event):
        if self._check_still_parented() and self.got_artist:
            self._m.cb.execute_callbacks(True)
            self.finalize_offset()
            self.got_artist = False
            self.canvas.mpl_disconnect(self._c1)


class LayerSelector(SelectorButtons):
    def __init__(
        self, m, layers=None, draggable=True, exclude_layers=None, name=None, **kwargs
    ):
        """
        A button-widget that can be used to select the displayed plot-layer.

        Note
        ----
        In general, layers are only drawn "on demand", so if you switch to a layer that
        has not been shown yet, it needs to be drawn first.

        - Depending on the complexity (WebMaps, Overlays, very large datasets etc.) this
          might take a few seconds.
        - Once the layer has been drawn, it is cached and switching even between
          layers with many features should be fast.
        - If the extent of the map changes (e.g. pan/zoom) or new features are added to
          the layer, it will be re-drawn.

        Parameters
        ----------
        layers : list or None, optional
            A list of layer-names that should appear in the selector.
            If None, all available layers (except the "all" layer) are shown, and the
            layers are automatically updated whenever a new layer is created on the map.
            (check the 'exclude_layers' parameter for excluding specific layers)
            The default is None.
        draggable : bool, optional
            Indicator if the widget should be draggable or not.
            The default is True.
        exclude_layers : list or None
            A list of layer-names that should be excluded.
            Only relevant if `layers=None` is used.
            The default is None in which case only the "all" layer is excluded.
            (Same as `exclude = ["all"]`. Use `exclude=[]` to get all available layers.)
        name : str
            The name of the slider (used to identify the object)
            If None, a unique identifier is used.
        kwargs :
            All additional arguments are passed to `plt.legend`

            Some useful arguments are:

            - ncol: the number of columns to use
            - size: the size of the markers
            - fontsize: the fontsize of the labels
            - loc: the position of the widget with respect to the figure.
              Any combination of the strings ["upper", "lower"] and
              ["left", "right", "center"] is possible.
            - bbox_to_anchor: offset from the loc-position in figure coordinates
              e.g.: (loc="upper center", bbox_to_anchor=(0.5, 1.1))

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

        self._init_args = {
            "layers": layers,
            "draggable": draggable,
            "exclude_layers": exclude_layers,
            **kwargs,
        }

        if layers is None:
            if exclude_layers is None:
                exclude_layers = ["all"]
            layers = m._get_layers(exclude=exclude_layers)

        # assert (
        #     len(layers) > 0
        # ), "EOmaps: There are no layers with artists available.. plot something first!"

        super().__init__(m.f, layers, **kwargs)

        self.set_draggable(draggable, m=m)
        self._m = m

        self.set_zorder(9999)  # make sure the widget is on top of other artists
        self.figure = self._m.f  # make sure the figure is set for the artist
        self.set_animated(True)

        self._m.BM.add_artist(self.leg, layer="all")

        # keep a reference to the buttons to make sure they stay interactive
        if name is None:
            keys = (
                key for key in self._m.util._selectors if key.startswith("selector_")
            )
            ns = []
            for key in keys:
                try:
                    ns.append(int(key[9:]))
                except:
                    pass

            name = f"selector_{max(ns) + 1 if ns else 0}"

        self._init_args["name"] = name
        self._m.util._selectors[name] = self

    def on_clicked(self, val):
        l = self.labels[int(val)]

        self._m.BM.bg_layer = l

        self._m.BM.update(blit=False)
        self._m.BM.canvas.draw_idle()

    def _reinit(self):
        """
        re-initialize the widget (to update layers etc.)

        Returns
        -------
        s : LayerSelector
            The new selector object (the old one is deleted!)

        """

        if self._init_args["draggable"] is True:
            # get the current position of the offsetbox and use it as loc when
            # initializing the new legend
            if hasattr(self._draggable_box, "offsetbox_x"):
                self._draggable_box.save_offset()
                loc = self._draggable_box.get_loc_in_canvas()
                loc = set(self._m.f.transFigure.inverted().transform(loc))
                self._init_args.update(dict(loc=loc))

        self.remove()

        self.__init__(m=self._m, **self._init_args)
        self._m.util._update_widgets()
        self._m.BM.update()

    def remove(self):
        """
        Remove the widget from the map
        """

        self._m.BM.remove_artist(self.leg)
        self.leg.remove()

        del self._m.util._selectors[self._init_args["name"]]
        self._m.BM.update()


class LayerSlider(Slider):
    def __init__(
        self,
        m,
        layers=None,
        pos=None,
        txt_patch_props=None,
        exclude_layers=None,
        name=None,
        **kwargs,
    ):
        """
        Get a slider-widget that can be used to switch between layers.

        By default, the widget will auto-update itself if new layers are created!

        Note
        ----
        In general, layers are only drawn "on demand", so if you switch to a layer that
        has not been shown yet, it needs to be drawn first.

        - Depending on the complexity (WebMaps, Overlays, very large datasets etc.) this
          might take a few seconds.
        - Once the layer has been drawn, it is cached and switching even between
          layers with many features should be fast.
        - If the extent of the map changes (e.g. pan/zoom) or new features are added to
          the layer, it will be re-drawn.

        Parameters
        ----------
        layers : list or None, optional
            A list of layer-names that should appear in the selector.
            If None, all available layers (except the "all" layer) are shown, and the
            layers are automatically updated whenever a new layer is created on the map.
            (check the 'exclude_layers' parameter for excluding specific layers)
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
        name : str
            The name of the slider (used to identify the object)
            If None, a unique identifier is used.
        kwargs :
            Additional kwargs are passed to matplotlib.widgets.Slider

            The default is

            >>> dict(initcolor="none",
            >>>      handle_style=dict(facecolor=".8", edgecolor="k", size=7),
            >>>      label=None,
            >>>      track_color="0.8",
            >>>      color="0.2"
            >>>      )

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
        self._m = m

        self._init_args = {
            "layers": layers,
            "txt_patch_props": txt_patch_props,
            "exclude_layers": exclude_layers,
            **kwargs,
        }

        if layers is None:
            if exclude_layers is None:
                exclude_layers = ["all"]
            layers = self._m._get_layers(exclude=exclude_layers)

        # assert (
        #     len(layers) > 0
        # ), "EOmaps: There are no layers with artists available.. plot something first!"

        if pos is None:
            ax_slider = self._m.f.add_axes(
                [
                    self._m.ax.get_position().x0,
                    self._m.ax.get_position().y0 - 0.05,
                    self._m.ax.get_position().width * 0.75,
                    0.05,
                ]
            )
        else:
            ax_slider = self._m.f.add_axes(pos)

        ax_slider.set_label("slider")

        kwargs.setdefault("color", ".2")  # remove start-position marker
        kwargs.setdefault("track_color", ".8")  # remove start-position marker
        kwargs.setdefault("initcolor", "none")  # remove start-position marker
        kwargs.setdefault("handle_style", dict(facecolor=".8", edgecolor="k", size=7))
        kwargs.setdefault("label", None)

        # use a small minimal value for valmax to avoid "vmin==vmax" warnings
        # in case only 1 layer is available
        super().__init__(
            ax_slider,
            valmin=0,
            valmax=max(len(layers) - 1, 0.01),
            valinit=0,
            valstep=1,
            **kwargs,
        )

        self.drawon = False

        self._layers = layers

        # add some background-patch style for the text
        if txt_patch_props is not None:
            self.valtext.set_bbox(txt_patch_props)

        def fmt(val):
            if val < len(layers):
                return layers[val]
            else:
                return "---"

        self._format = fmt
        self._handle.set_marker("D")

        self.track.set_edgecolor("none")
        h = self.track.get_height() / 2
        self.track.set_height(h)
        self.track.set_y(self.track.get_y() + h / 2)

        self._m.BM.add_artist(ax_slider, layer="all")

        self.on_changed(self._on_changed)

        # keep a reference to the slider to make sure it stays interactive
        if name is None:
            keys = (key for key in self._m.util._sliders if key.startswith("slider_"))
            ns = []
            for key in keys:
                try:
                    ns.append(int(key[7:]))
                except:
                    pass

            name = f"slider_{max(ns) + 1 if ns else 0}"

        self._init_args["name"] = name
        self._m.util._sliders[name] = self

    def set_layers(self, layers):
        self._layers = layers
        self.valmax = max(len(layers) - 1, 0.01)
        self.ax.set_xlim(self.valmin, self.valmax)

        if self._m.BM.bg_layer in self._layers:
            currval = self._layers.index(self._m.BM.bg_layer)
            self.set_val(currval)
        else:
            self.set_val(0)

        self._on_changed(self.val)

        self._m.util._update_widgets()
        self._m.BM.update()

    def _reinit(self):
        """
        re-initialize the widget (to update layers etc.)

        Returns
        -------
        s : LayerSlider
            The new slider object (the old one is deleted!)

        """
        self.remove()

        self.__init__(m=self._m, pos=self.ax.get_position(), **self._init_args)
        self._m.util._update_widgets()
        self._m.BM.update()

    def _on_changed(self, val):
        l = self._layers[int(val)]
        self._m.BM.bg_layer = l
        self._m.BM.update()

    def remove(self):
        """
        Remove the widget from the map
        """

        self._m.BM.remove_artist(self.ax)
        self.disconnect_events()
        self.ax.remove()

        del self._m.util._sliders[self._init_args["name"]]

        self._m.BM.update()


class utilities:
    """
    A collection of utility tools that can be added to EOmaps plots
    """

    def __init__(self, m):
        self._m = m

        self._selectors = dict()
        self._sliders = dict()

        # register a function to update all associated widgets on a layer-chance
        self._m.BM.on_layer(
            lambda m, layer: self._update_widgets(layer), persistent=True
        )

    def _update_widgets(self, l=None):
        if l is None:
            l = self._m.BM._bg_layer

        # this function is called whenever the background-layer changed
        # to synchronize changes across all selectors and sliders
        # see setter for   helpers.BM._bg_layer
        for s in self._sliders.values():
            try:
                s.eventson = False
                s.set_val(s._layers.index(l))
                s.valtext.set_text(l)
                s.valtext.set_color(rcParams["text.color"])
                s.eventson = True
            except ValueError:
                s.valtext.set_text(self._m.BM._bg_layer)
                s.valtext.set_color("r")
                pass
            except IndexError:
                s.valtext.set_text(self._m.BM._bg_layer)
                s.valtext.set_color("r")
                pass
            finally:
                s.eventson = True

        for s in self._selectors.values():
            try:
                s.set_active(s.circles[s.labels.index(l)])
            except ValueError:
                s.set_active(None)
            except IndexError:
                s.set_active(None)

    def _reinit_widgets(self):
        # re-initialize ALL sliders and button widgets to update the available layers

        for s in (*self._sliders.values(), *self._selectors.values()):
            s._reinit()

    def remove(self, name=None, what="all"):
        # TODO doc
        if name is not None:
            if name in self._sliders:
                self._sliders[name].remove()
            elif name in self._selectors:
                self._selectors[name].remove()
            return

        if what == "sliders":
            for s in self._sliders.values():
                s.remove()
        elif what == "selectors":
            for s in self._selectors.values():
                s.remove()
        elif what == "all":
            for s in (*self._sliders.values(), *self._selectors.values()):
                s.remove()
        else:
            raise TypeError(
                "EOmaps: 'what' must be one of 'sliders', 'selectors' or 'all'"
            )

    @wraps(LayerSelector.__init__)
    def layer_selector(self, **kwargs):
        s = LayerSelector(m=self._m, **kwargs)
        # update widgets to make sure the right layer is selected
        self._update_widgets()
        return s

    @wraps(LayerSlider.__init__)
    def layer_slider(self, **kwargs):
        s = LayerSlider(m=self._m, **kwargs)
        # update widgets to make sure the right layer is selected
        self._update_widgets()
        return s

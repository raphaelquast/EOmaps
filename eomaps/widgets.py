from abc import abstractmethod
from functools import wraps

import numpy as np
import matplotlib.pyplot as plt

from . import _log
from ._blit_manager import LayerParser

try:
    import ipywidgets
except ImportError:
    _log.exception("EOmaps-widgets are missing the required dependency 'ipywidgets'!")


def _check_backend():
    backend = plt.get_backend()
    if "ipympl" not in backend.lower():
        raise AssertionError(
            "EOmaps-widgets only work with the 'ipympl (widget)' backend! "
            "Make sure you have 'ipympl' installed and use the magic-command "
            "'%matplotlib widget' to switch to the interactive jupyter backend!"
        )


# %% Layer Selector Widgets


class _LayerSelectionWidget:
    def __init__(self, m, layers=None):
        """
        A widget to switch layers of a given Maps-object.

        Parameters
        ----------
        m : eomaps.Maps
            The Maps-object to use.
        layers : list, optional
            A list of layer-names to use.
            If None, all available layers of the provided Maps-object are used.

            The following options are possible:

            A list of layer-names

            >>> ["layer1", "layer2", ...]

            A list of layer-names and/or layer-names with transparency-assignments

            >>> ["layer1", "layer2", ("layer", 0.4)]

            To provide explict display-names for a layer, pass a list of the form
            `[display-name, <layer-assignment>]`

            >>> [["My Layer", "layer1"],
            >>>  ["My secondl lyer", "layer2"],
            >>>  ["Multiple layers", ("layer1",
            >>>                       ("layer", 0.4))]
            >>> ]

        """
        _check_backend()

        self._m = m
        self._set_layers(layers)

    def _set_layers(self, layers):
        if layers is None:
            self._layers = self._m._get_layers()
        else:

            self._layers = []
            for l in layers:
                if isinstance(l, str):
                    self._layers.append((l, l))
                elif isinstance(l, tuple):
                    l = self._parse_layer(l)
                    self._layers.append((l, l))
                elif isinstance(l, list):
                    self._layers.append((l[0], self._parse_layer(l[1])))

    @staticmethod
    def _parse_layer(l):
        # check if a single transparent layer is provided
        if isinstance(l, tuple):
            if (
                len(l) == 2
                and isinstance(l[0], str)
                and isinstance(l[1], (int, float, np.number))
            ):
                return LayerParser._get_combined_layer_name(l)
            else:
                return LayerParser._get_combined_layer_name(*l)
        else:
            return l

    def handler(self, change):
        try:
            if self.value is not None:
                self._m.show_layer(self.value)
                self._m.BM.update()
        except Exception:
            _log.error("Problem in LayerSelectionWidget handler...", exc_info=True)


class LayerDropdown(ipywidgets.Dropdown, _LayerSelectionWidget):
    _description = "Layers"

    @wraps(_LayerSelectionWidget.__init__)
    def __init__(self, *args, description=None, **kwargs):

        _LayerSelectionWidget.__init__(self, *args, **kwargs)

        super().__init__(
            options=self._layers,
            description=self._description if description is None else description,
            value=self._m.BM.bg_layer if self._m.BM.bg_layer in self._layers else None,
        )

        self.observe(self.handler)


class LayerSelect(ipywidgets.Select, _LayerSelectionWidget):
    _description = "Layers"

    @wraps(_LayerSelectionWidget.__init__)
    def __init__(self, *args, description=None, **kwargs):

        _LayerSelectionWidget.__init__(self, *args, **kwargs)

        super().__init__(
            options=self._layers,
            description=self._description if description is None else description,
            value=self._m.BM.bg_layer if self._m.BM.bg_layer in self._layers else None,
        )

        self.observe(self.handler)


class LayerSelectionSlider(ipywidgets.SelectionSlider, _LayerSelectionWidget):
    _description = "Layers"

    @wraps(_LayerSelectionWidget.__init__)
    def __init__(self, *args, description=None, **kwargs):

        _LayerSelectionWidget.__init__(self, *args, **kwargs)

        super().__init__(
            options=self._layers,
            description=self._description if description is None else description,
            value=self._m.BM.bg_layer if self._m.BM.bg_layer in self._layers else None,
        )

        self.observe(self.handler)


class LayerToggleButtons(ipywidgets.ToggleButtons, _LayerSelectionWidget):
    _description = "Layers"

    @wraps(_LayerSelectionWidget.__init__)
    def __init__(self, *args, description=None, **kwargs):

        _LayerSelectionWidget.__init__(self, *args, **kwargs)

        super().__init__(
            options=self._layers,
            description=self._description if description is None else description,
            value=self._m.BM.bg_layer if self._m.BM.bg_layer in self._layers else None,
        )

        self.observe(self.handler)


class LayerRadioButtons(ipywidgets.RadioButtons, _LayerSelectionWidget):
    _description = "Layers"

    @wraps(_LayerSelectionWidget.__init__)
    def __init__(self, *args, description=None, **kwargs):

        _LayerSelectionWidget.__init__(self, *args, **kwargs)

        super().__init__(
            options=self._layers,
            description=self._description if description is None else description,
            value=self._m.BM.bg_layer if self._m.BM.bg_layer in self._layers else None,
        )

        self.observe(self.handler)


class LayerSelectionRangeSlider(ipywidgets.SelectionRangeSlider, _LayerSelectionWidget):
    _description = "Layers"

    @wraps(_LayerSelectionWidget.__init__)
    def __init__(self, *args, description=None, **kwargs):

        _LayerSelectionWidget.__init__(self, *args, **kwargs)

        super().__init__(
            options=self._layers,
            description=self._description if description is None else description,
            value=(self._m.BM.bg_layer, self._m.BM.bg_layer)
            if self._m.BM.bg_layer in self._layers
            else (self._layers[0][1],),
        )

        self.observe(self.handler)

    def handler(self, change):
        try:
            if self.value is not None:
                i0 = self._layers.index(self.value[0])
                i1 = self._layers.index(self.value[1])

                if i0 == i1:
                    self._m.show_layer(self.value[0])
                else:
                    self._m.show_layer(*self._layers[i0 : i1 + 1])
        except Exception:
            _log.error("Problem in MultiLayerSelectionWidget handler...", exc_info=True)


class LayerSelectMultiple(ipywidgets.SelectMultiple, _LayerSelectionWidget):
    _description = "Layers"

    @wraps(_LayerSelectionWidget.__init__)
    def __init__(self, *args, description=None, **kwargs):

        _LayerSelectionWidget.__init__(self, *args, **kwargs)
        super().__init__(
            options=self._layers,
            description=self._description if description is None else description,
            value=(self._m.BM.bg_layer,)
            if self._m.BM.bg_layer in self._layers
            else (self._layers[0][1],),
        )

        self.observe(self.handler)

    def handler(self, change):
        try:
            if self.value is not None:
                self._m.show_layer(*self.value)
        except Exception:
            _log.error("Problem in MultiLayerSelectionWidget handler...", exc_info=True)


# %% Overlay Widgets


class OverlaySlider(ipywidgets.FloatSlider):
    def __init__(self, m, layer):
        """
        A Slider to overlay a selected layer on top of other layers

        Parameters
        ----------
        m : eomaps.Maps
            The Maps-object to use.
        layer : str
            The layer to overlay.

        """
        self._m = m
        _check_backend()

        self._layer = layer

        super().__init__(
            value=0, min=0, max=1, step=0.01, description=f"Overlay\n'{layer}':"
        )

        self._last_value = self.value

        self.observe(self.handler)

    def handler(self, change):
        try:
            layers, alphas = LayerParser._parse_multi_layer_str(self._m.BM.bg_layer)

            # in case the active layer has the overlay on top, strip off the overlay
            # from the active layer!
            if layers[-1] == self._layer and alphas[-1] == self._last_value:
                base = LayerParser._get_combined_layer_name(
                    *zip(layers[:-1], alphas[:-1])
                )
            else:
                base = self._m.BM.bg_layer

            self._m.show_layer(base, (self._layer, self.value))

            self._last_value = self.value
            plt.pause(0.01)  # spin event-loop to avoid flickering for very fast updates
        except Exception:
            _log.error("Problem in OverlaySlider handler...", exc_info=True)


# %% CallbackWidgets


class _CallbackWidget:
    def __init__(self, m, **kwargs):
        self._m = m
        _check_backend()

        self._kwargs = kwargs
        self._cid = None

    @abstractmethod
    def attach_callback(self, **kwargs):
        """Attach the callback to the map and return the cid."""
        return "cid"

    def handler(self, change):
        try:
            if self.value is True and self._cid is None:
                self._cid = self.attach_callback(**self._kwargs)

            if self.value is False and self._cid is not None:
                self._cid = self._m.all.cb.click.remove(self._cid)
        except Exception:
            _log.error("Problem in Checkbox handler...", exc_info=True)


class _CallbackCheckbox(ipywidgets.Checkbox, _CallbackWidget):
    _description = "Callback Checkbox"

    @wraps(_CallbackWidget.__init__)
    def __init__(self, *args, value=False, description=None, **kwargs):
        _CallbackWidget.__init__(self, *args, **kwargs)
        super().__init__(
            value=value,
            description=description if description is not None else self._description,
        )
        self.observe(self.handler)


class ClickAnnotateCheckbox(_CallbackCheckbox):
    _description = "Annotate (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.annotate(**kwargs)


class ClickMarkCheckbox(_CallbackCheckbox):
    _description = "Mark (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.mark(**kwargs)


class ClickPrintToConsoleCheckbox(_CallbackCheckbox):
    _description = "Print (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.print_to_console(**kwargs)


# NOTE: pick callbacks are attached to the provided Maps objects,
#       click callback are attached to m.all!
class PickAnnotateCheckbox(_CallbackCheckbox):
    _description = "Annotate (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.annotate(**kwargs)


class PickMarkCheckbox(_CallbackCheckbox):
    _description = "Mark (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.mark(**kwargs)


class PickPrintToConsoleCheckbox(_CallbackCheckbox):
    _description = "Print (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.print_to_console(**kwargs)

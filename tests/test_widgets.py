import pytest
from eomaps import Maps, widgets
import matplotlib.pyplot as plt

import warnings

warnings.filterwarnings("ignore", "EOmaps-widgets only work with the")


@pytest.mark.parametrize(
    "widget",
    [
        widgets.LayerDropdown,
        widgets.LayerSelect,
        widgets.LayerSelectMultiple,
        widgets.LayerSelectionSlider,
        widgets.LayerSelectionRangeSlider,
        widgets.LayerToggleButtons,
        widgets.LayerRadioButtons,
    ],
)
@pytest.mark.parametrize(
    "use_layers", [None, [["layer1", ("coast",)], ["layer2", ("ocean", "coast")]]]
)
def test_selector_widgets(widget, use_layers):
    m = Maps(layer="all")
    m.add_feature.preset.coastline(layer="coast")
    m.add_feature.preset.ocean(layer="ocean")
    m.show_layer("coast")

    w = widget(m, layers=use_layers)
    layers = w._layers

    # check if layers are correctly identified
    if use_layers is None:
        assert layers == m._get_layers(), "layers not correctly identified"
    else:
        assert layers == [m.BM._get_combined_layer_name(*i[1]) for i in use_layers]

    state = w.get_state()

    # check if labels are correctly identified
    if use_layers is None:
        if use_layers is None:
            assert state["_options_labels"] == tuple(
                layers
            ), "layers not correctly identified"
        else:
            assert state["_options_labels"] == [
                i[0] for i in use_layers
            ], "layers not correctly identified"

    for i in range(len(layers)):
        if widget in (widgets.LayerSelectMultiple, widgets.LayerSelectionRangeSlider):
            state["index"] = (0, i)
        else:
            state["index"] = i

        w.set_state(state)
        m.redraw()

        found_layer = m.BM.bg_layer

        if widget in (widgets.LayerSelectMultiple,):
            expected_layer = m.BM._get_combined_layer_name(layers[0], layers[i])
        elif widget in (widgets.LayerSelectionRangeSlider,):
            expected_layer = m.BM._get_combined_layer_name(*layers[0 : i + 1])
        else:
            expected_layer = layers[i]

        assert (
            found_layer == expected_layer
        ), f"layer not properly changed... found: '{found_layer}', expected: '{expected_layer}'"

    plt.close("all")


@pytest.mark.parametrize(
    "widget",
    [
        widgets.ClickAnnotateCheckbox,
        widgets.ClickMarkCheckbox,
        widgets.ClickPrintToConsoleCheckbox,
        widgets.ClickPeekLayerCheckbox,
        widgets.PickAnnotateCheckbox,
        widgets.PickMarkCheckbox,
        widgets.PickPrintToConsoleCheckbox,
    ],
)
def test_callback_widgets(widget):
    m = Maps(layer="all")
    m.set_data(*[[1, 2, 3]] * 3)
    m.plot_map()

    m.add_feature.preset.coastline(layer="coast")
    m.add_feature.preset.ocean(layer="ocean")
    m.show_layer("coast")

    if widget in (widgets.ClickPeekLayerCheckbox,):
        w = widget(m, layer="coast")
    else:
        w = widget(m)

    state = w.get_state()
    state["value"] = True
    w.set_state(state)

    if widget.__name__.startswith("Pick"):
        cbs = m.cb.pick
    elif widget.__name__.startswith("Click"):
        cbs = m.all.cb.click

    assert cbs.get.attached_callbacks == [w._cid], "callback not attached"

    state["value"] = False
    w.set_state(state)

    assert cbs.get.attached_callbacks == [], "callback not removed"


@pytest.mark.parametrize(
    "widget",
    [
        widgets.LayerOverlaySlider,
    ],
)
def test_overlay_widgets(widget):
    m = Maps(layer="all")
    m.add_feature.preset.coastline(layer="coast")
    m.add_feature.preset.ocean(layer="ocean")
    m.show_layer("coast")

    w = widget(m, layer="ocean")
    state = w.get_state()

    for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
        state["value"] = val
        w.set_state(state)

        assert m.BM.bg_layer == m.BM._get_combined_layer_name(
            "coast", ("ocean", val)
        ), "Overlay not properly assigned"
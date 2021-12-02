⚙ API
=======

🔸 Initialize Maps objects
----------------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps
    eomaps.Maps.copy
    eomaps.MapsGrid


🔸 Set specifications
-----------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.set_shape
    eomaps.Maps.set_data
    eomaps.Maps.set_data_specs
    eomaps.Maps.set_plot_specs
    eomaps.Maps.set_classify_specs


You can also get/set the specs with:

.. code-block:: python

    eomaps.Maps.data_specs.<...name...>
    eomaps.Maps.plot_specs.<...name...>
    eomaps.Maps.classify_specs.<...name...>


🔸 Plot the map and save it
-----------------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.plot_map
    eomaps.Maps.savefig

    eomaps.Maps.figure


🔸 Add layers and objects
---------------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.add_wms
    eomaps.Maps.add_wmts
    eomaps.Maps.add_gdf
    eomaps.Maps.add_overlay
    eomaps.Maps.add_overlay_legend
    eomaps.Maps.add_coastlines

    eomaps.Maps.add_marker
    eomaps.Maps.add_annotation
    eomaps.Maps.add_colorbar


🔸 Miscellaneous
------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.get_crs
    eomaps.Maps.CRS
    eomaps.Maps.CLASSIFIERS
    eomaps.Maps.indicate_masked_points
    eomaps.Maps.parent
    eomaps.Maps.BM
    eomaps.Maps.crs_plot
    eomaps.Maps.join_limits




🔸 Callbacks - make the map interactive!
------------------------------------------

Callbacks are used to execute functions when you click on the map.

They can be attached to a map via:

.. code-block:: python

    m = Maps()
    ...
    m.cb.< METHOD >.attach.< CALLBACK >( **kwargs )

`< METHOD >` defines the way how callbacks are executed.

.. currentmodule:: eomaps._cb_container.cb_container

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    click
    pick
    keypress
    dynamic


`< CALLBACK >` indicates the action you want to assign o the event.
There are many pre-defined callbacks but it is also possible to define custom
functions and attach them to the map via:

.. code-block:: python

    def some_callback(self, asdf, **kwargs):
        print("hello world")
        print("the position of the clicked pixel", kwargs["pos"])
        print("the data-index of the nearest datapoint", kwargs["ID"])
        print("data-value of the nearest datapoint", kwargs["val"])

        # `self` points to the underlying Maps-object, so you can
        # access all properties of the Maps object via:
        print("the plot-crs is:", self.plot_specs["plot_crs"])
        ...
        ...

    m.cb.pick.attach(some_callback, double_click=False, button=1, asdf=1)



Pre-defined click & pick callbacks
..................................

Callbacks that can be used with both `m.cb.click` and `m.cb.pick`:

.. currentmodule:: eomaps.callbacks._click_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    peek_layer
    annotate
    clear_annotations
    mark
    clear_markers
    get_values
    print_to_console

Callbacks that can be used only with `m.cb.pick`:

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    load

Pre-defined keypress callbacks
..............................

Callbacks that can be used with `m.cb.keypress`

.. currentmodule:: eomaps.callbacks.keypress_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    switch_layer

Pre-defined dynamic callbacks
.............................

Callbacks that can be used with `m.cb.dynamic`

.. currentmodule:: eomaps.callbacks.dynamic_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    indicate_extent

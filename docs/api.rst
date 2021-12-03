⚙ Usage
=========

🚀 Basics
---------

🌐 Initialization of Maps objects
.................................

To initialize a new `Maps` object, simply use:

.. code-block:: python

    from eomaps import Maps
    m = Maps( ... )


To initialize a grid of `Maps` objects (e.g. a grid of maps in the same figure),
use:

.. code-block:: python

    from eomaps import MapsGrid
    mgrid = MapsGrid(r=2, c=2, ... )
    # you can then access the individual Maps-objects via:
    mgrid.m_0_0
    mgrid.m_0_1
    mgrid.m_1_0
    mgrid.m_1_1


.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps
    MapsGrid


If you want to create multiple maps-objects with similar properties, use:

.. code-block:: python

    from eomaps import Maps

    m = Maps()
    ...
    m2 = m.copy()

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.copy

🌍 Set plot specifications
..........................

The appearance of the plot can be adjusted by setting the following properties
of the Maps object:

.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    set_shape
    set_data
    set_plot_specs
    set_classify_specs

Alternatively, you can also get/set the properties with:

.. code-block:: python

    m = Maps()
    m.data_specs.< property > = ...
    m.plot_specs.< property > = ...
    m.classify_specs.< property > = ...


The CRS usable for plotting as well as available classifiers that can be used
to classify the data are accessible via `Maps.CRS` and `Maps.CLASSIFIERS`:

.. code-block:: python

    m = Maps()
    m.set_classify_specs(Maps.CLASSFIERS.Quantiles, k=5)
    m.plot_specs.crs = Maps.CRS.Orthographic(central_latitude=45)


🗺 Plot the map and save it
...........................

Maps based on WebMap layers can be directly generated via:

.. code-block:: python

    m = Maps()
    m.add_wms.< WebMap service >.add_layer.< Layer Name >()

If you want to plot a map based on a dataset, use:

.. code-block:: python

    m = Maps()
    m.set_data( < the data specifications > )
    m.plot_map()

Once the map is generated, a snapshot of the map can be saved at any time by using:

.. code-block:: python

    m.savefig( "snapshot1.png", dpi=300 )


.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    plot_map
    savefig


🛸 Callbacks - make the map interactive!
----------------------------------------

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


🛰 How to add WebMap service layers
-----------------------------------

WebMap services (TS/WMS/WMTS) can be attached to the map via:

.. code-block:: python

    m = Maps()
    m.add_wms.attach.< SERVICE > ... .add_layer.< LAYER >( layer=1 )

.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    add_wms


< SERVICE > hereby specifies the pre-defined WebMap service you want to add.


.. note::
    Services might be nested directory structures!
    The actual layer is always added via the `add_layer` directive.

        :code:`m.add_wms.<...>. ... .<...>.add_layer.<...>()`

    Some of the services dynamically fetch the structure via HTML-requests.
    Therefore it can take a short moment before autocompletion is capable of
    showing you the available options!
    A list of available layers from a sub-folder can be fetched via:

        :code:`m.add_wms.<...>. ... .<...>.layers`


.. currentmodule:: eomaps._containers.wms_container

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    OpenStreetMap
    ESA_WorldCover
    NASA_GIBS
    ISRIC_SoilGrids
    EEA_DiscoMap
    ESRI_ArcGIS
    S1GBM
    Austria


🏕 Adding additional features and overlays
------------------------------------------

Static annotations and markers can be added to the map via:

.. code-block:: python

    m = Maps()
    ...
    m.add_annotation( ... )
    m.add_marker( ... )

.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    add_marker
    add_annotation

Overlays from NaturalEarth and `geopandas.GeoDataFrames` can be added via:

.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    add_gdf
    add_overlay
    add_overlay_legend
    add_coastlines



🔸 Miscellaneous
----------------
some additional functions and properties that might come in handy:

.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:

    join_limits
    get_crs
    indicate_masked_points
    BM
    parent
    crs_plot
    add_colorbar

⚙ Usage
=========

🚀 Basics
---------

🌐 Initialization of Maps objects
.................................

To initialize a new ``Maps`` object, simply use:

.. code-block:: python

    from eomaps import Maps
    m = Maps( ... )


To copy an existing ``Maps``-object (and share selected specifications), use:

.. code-block:: python

    from eomaps import Maps

    m = Maps()
    ...
    m2 = m.copy(...)

To create a ``Maps``-object that represents an additional layer of an already existing map,
use one of the following:
(In this way, the newly created ``Maps`` object will share the same figure and plot-axis.)

.. code-block:: python

    from eomaps import Maps

    m = Maps()
    ...
    m_layer1 = Maps(parent=m)
    m_layer2 = m.copy(connect=True)




.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps
    Maps.copy



𝄜 Multiple maps in one figure
..............................

To initialize (and manage) a grid of ``Maps`` objects, you can use a ``MapsGrid``:

.. code-block:: python

    from eomaps import MapsGrid
    mgrid = MapsGrid(r=2, c=2, ... )
    # you can then access the individual Maps-objects via:
    mgrid.m_0_0
    mgrid.m_0_1
    mgrid.m_1_0
    mgrid.m_1_1

    # to perform actions on all Maps-objects, simply loop over the MapsGrid object
    for m in mgrid:
        ...

❗ It is also possible to customize the positioning of the axes and **combine EOmaps plots with ordinary matplotlib axes** in one grid via the ``m_inits`` and ``ax_inits`` arguments!

- if ``m_inits`` is provided, the specifications are used to initialize ``Maps`` objects (accessible via ``mgrid.m_<key>``)
- if ``ax_inits`` is provided, the specifications are used to initialize ordinary matplotlib axes (accessible via ``mgrid.ax_<key>``)

- To specify axes that span over multiple rows or columns, simply use ``slice(start, stop)``.
- The initialization of the axes is based on matplotlib's `GridSpec <https://matplotlib.org/stable/api/_as_gen/matplotlib.gridspec.GridSpec.html>`_ functionality. All additional keyword-arguments (``width_ratios, height_ratios, etc.``) are passed to the initialization of the GridSpec object.


.. code-block:: python

    from eomaps import MapsGrid

    # initialize a grid with 2 Maps objects and 1 ordinary matplotlib axes
    mgrid = MapsGrid(2, 2,
                     m_inits=dict(top_row=(0, slice(0, 2)),
                                  bottom_left=(1, 0)),
                     ax_inits=dict(bottom_right=(1, 1)),
                     width_ratios=(1, 2),
                     height_ratios=(2, 1))

    mgrid.m_top_row # a map extending over the entire top-row of the grid
    mgrid.m_bottom_left # a map in the bottom left corner of the grid

    mgrid.ax_bottom_right # an ordinary matplotlib axes in the bottom right corner of the grid


.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    MapsGrid
    MapsGrid.create_axes


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

If you want to plot a map based on a dataset, first set the data and then
call :code:`m.plot_map()`:

.. code-block:: python

    m = Maps()
    m.set_data( < the data specifications > )
    m.plot_map()


If you only want to add a WebMap layer, simply use:

.. code-block:: python

    m = Maps()
    m.add_wms.< WebMap service >.add_layer.< Layer Name >()


Once the map is generated, a snapshot of the map can be saved at any time by using:


.. code-block:: python

    m.savefig( "snapshot1.png", dpi=300, ... )


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

It is highly recommended to use the native crs of the WebMap service in order
to avoid re-projecting the images (which degrades image quality and takes
some time to finish...)

.. code-block:: python

    m = Maps()
    m.plot_specs.crs = Maps.CRS.GOOGLE_MERCATOR # (at best the native crs of the service!)
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

Global WebMap services:

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

Services specific for Austria (Europa)

.. currentmodule:: eomaps._containers

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Austria.AT_basemap
    Austria.Wien_basemap


🏕 Additional features and overlays
-----------------------------------

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


📏 Scalebars
------------

A scalebar can be added to a map via:

.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    add_scalebar

.. code-block:: python

    m = Maps()
    ...
    s = m.add_scalebar( ... )
    # to remove it, use
    s.remove()


.. Note::

    The scalebar is a pickable object!
    Click on it with the LEFT mouse button to drag it around, and use the RIGHT
    mouse button to make it fixed again.

    If the scalebar is picked (indicated by a red border), you can use the following
    keys for adjusting some of the ScaleBar properties:

    - ``delte``: remove the scalebar from the plot
    - ``+``  and ``-``: rotate the scalebar
    - ``up/down/left/right``: increase the size of the frame
    - ``alt + up/down/left/right``: decrease the size of the frame


The scalebar has the following useful methods assigned:

.. currentmodule:: eomaps.scalebar.ScaleBar

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    set_scale_props
    set_patch_props
    set_label_props
    set_position
    get_position
    remove
    cb_offset_interval
    cb_rotate_interval

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

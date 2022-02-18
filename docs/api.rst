⚙ Usage
=========

🚀 Basics
---------

🌐 Initialization of Maps objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| EOmaps is all about ``Maps`` objects.
| To start creating a new map (in this case a plot in ``epsg=4326``, e.g. lon/lat projection), simply use:

.. code-block:: python

    from eomaps import Maps
    m = Maps(crs=4326)

Possible ways for specifying the crs for plotting are:

- if you provide an ``integer``, it is identified as an epsg-code.
- All other CRS usable for plotting are accessible via ``Maps.CRS``,
  e.g.: ``crs=Maps.CRS.Orthographic()`` or ``crs=Maps.CRS.Equi7Grid_projection("EU")``.

Once you have created your first ``Maps`` object, you can create **additional layers on the same map** by using:

.. code-block:: python

    m2 = m.new_layer(...)

(``m2`` is then just another ``Maps`` object that shares the figure and plot-axes with ``m``)


.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps
    Maps.new_layer
    Maps.copy


🔵 Setting the data and plot-shape
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To assign a dataset to a ``Maps`` object, use ``m.set_data``.
The shapes that are used to represent the data-points are then assigned via ``m.set_shape``.

.. code-block:: python

    m = Maps()
    m.set_data(data, xcoord, ycoord, parameter)
    m.set_shape.rectangles(radius=1, radius_crs=4326)
    m.plot_map()

    m2 = m.new_layer()
    m2.set_data(...)
    ...

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.set_data
    Maps.set_shape

Possible shapes that work nicely for datasets with up to 1M data-points:

.. currentmodule:: eomaps._shapes.shapes

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    geod_circles
    ellipses
    rectangles
    voroni_diagram
    delaunay_triangulation

For extremely large datasets (>1M datapoints), it is recommended to use
"shading" instead of representing each data-point with a projected polygon.

Possible shapes that can be used to quickly generate a plot for millions of pixels are:

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    shade_points
    shade_raster

If shading is used, a dynamic averaging of the data based on the screen-resolution
is performed (resampling based on the mean-value is used by default).

.. note::

    The "shade"-shapes require the additional ``datashader`` dependency!
    You can install it via:
    ``conda install -c conda-forge datashader``


🌍 Customizing the plot
~~~~~~~~~~~~~~~~~~~~~~~

The general appearance of the plot can be adjusted by setting the ``plot_specs`` and ``classify_specs``
of the Maps object:

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.set_plot_specs
    Maps.set_classify_specs

The available classifiers that can be used to classify the data (provided by ``mapclassify``) are accessible via `Maps.CLASSIFIERS`:

.. code-block:: python

    m = Maps()
    m.set_data(...)
    m.set_shape.ellipses(...)

    m.set_classify_specs(Maps.CLASSFIERS.Quantiles, k=5)
    m.classify_specs.k = 10 # alternative way for setting classify-specs

    m.set_plot_specs(cmap="RdBu", histbins=20)
    m.plot_specs.alpha = .5 # alternative way for setting plot-specs


🗺 Plot the map and save it
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to plot a map based on a dataset, first set the data and then
call ``m.plot_map()``.

Any additional keyword-arguments passed to ``m.plot_map()`` are forwarded to the actual
plot-command for the selected shape.

Some useful arguments that are supported by most shapes (except "shade"-shapes) are:

    - "fc" or "facecolor" : the face-color of the shapes
    - "ec" or "edgecolor" : the edge-color of the shapes
    - "lw" or "linewidth" : the linewidth of the shapes
    - "alpha" : the alpha-transparency

.. code-block:: python

    m = Maps()
    m.set_data(...)
    ...
    m.plot_map(fc="none", ec="g", lw=2, alpha=0.5)

You can then continue to add :ref:`colorbar`, :ref:`annotations_and_markers`,
:ref:`scalebar`, :ref:`compass`,  :ref:`webmap_layers` or :ref:`geodataframe` to the map,
or you can start to add :ref:`callbacks`.

Once the map is ready, a snapshot of the map can be saved at any time by using:

.. code-block:: python

    m.savefig( "snapshot1.png", dpi=300, ... )


.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.plot_map
    Maps.savefig


𝄜 Multiple maps in one figure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``MapsGrid`` objects can be used to create (and manage) multiple maps in one figure.

A ``MapsGrid`` creates a grid of ``Maps`` objects (and/or ordinary ``matpltolib`` axes),
and provides convenience-functions to perform actions on all maps of the figure.

.. code-block:: python

    from eomaps import MapsGrid
    mgrid = MapsGrid(r=2, c=2, crs=..., ... )
    # you can then access the individual Maps-objects via:
    mgrid.m_0_0
    mgrid.m_0_1
    mgrid.m_1_0
    mgrid.m_1_1

    # to perform actions on all Maps-objects, simply loop over the MapsGrid object
    for m in mgrid:
        ...

Custom grids and mixed axes
***************************

Fully customized grid-definitions can be specified by providing ``m_inits`` and/or ``ax_inits`` dictionaries
of the following structure:

- The keys of the dictionary are used to identify the objects
- The values of the dictionary are used to identify the position of the associated axes
- The position can be either an integer ``N``, a tuple of integers or slices ``(row, col)``
- Axes that span over multiple rows or columns, can be specified via ``slice(start, stop)``

.. code-block:: python

    dict(
        name1 = N  # position the axis at the Nth grid cell (counting firs)
        name2 = (row, col), # position the axis at the (row, col) grid-cell
        name3 = (row, slice(col_start, col_end)) # span the axis over multiple columns
        name4 = (slice(row_start, row_end), col) # span the axis over multiple rows
        )

- ``m_inits`` is used to initialize ``Maps`` objects
- ``ax_inits`` is used to initialize ordinary ``matplotlib`` axes

The individual ``Maps``-objects and ``matpltolib-Axes`` are then accessible via:

.. code-block:: python

    mg = MapsGrid(2, 3,
                  m_inits=dict(left=(0, 0), right=(0, 2)),
                  ax_inits=dict(someplot=(1, slice(0, 3)))
                  )
    mg.m_left   # the Maps object with the name "left"
    mg.m_right   # the Maps object with the name "right"

    mg.ax_someplot   # the ordinary matplotlib-axis with the name "someplot"


❗ NOTE: if ``m_inits`` and/or ``ax_inits`` are provided, ONLY the explicitly defined objects are initialized!


- The initialization of the axes is based on matplotlib's `GridSpec <https://matplotlib.org/stable/api/_as_gen/matplotlib.gridspec.GridSpec.html>`_ functionality.
  All additional keyword-arguments (``width_ratios, height_ratios, etc.``) are passed to the initialization of the ``GridSpec`` object.

- To specify unique ``crs`` for each ``Maps`` object, provide a dictionary of ``crs`` specifications.

.. code-block:: python

    from eomaps import MapsGrid

    # initialize a grid with 2 Maps objects and 1 ordinary matplotlib axes
    mgrid = MapsGrid(2, 2,
                     m_inits=dict(top_row=(0, slice(0, 2)),
                                  bottom_left=(1, 0)),
                     crs=dict(top_row=4326,
                              bottom_left=3857),
                     ax_inits=dict(bottom_right=(1, 1)),
                     width_ratios=(1, 2),
                     height_ratios=(2, 1))

    mgrid.m_top_row # a map extending over the entire top-row of the grid (in epsg=4326)
    mgrid.m_bottom_left # a map in the bottom left corner of the grid (in epsg=3857)

    mgrid.ax_bottom_right # an ordinary matplotlib axes in the bottom right corner of the grid


.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    MapsGrid
    MapsGrid.join_limits
    MapsGrid.share_click_events
    MapsGrid.share_pick_events
    MapsGrid.set_data_specs
    MapsGrid.set_plot_specs
    MapsGrid.set_classify_specs
    MapsGrid.add_wms
    MapsGrid.add_feature
    MapsGrid.add_annotation
    MapsGrid.add_marker
    MapsGrid.add_gdf



.. _callbacks:

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
    :nosignatures:
    :template: only_names_in_toc.rst

    click
    pick
    keypress
    dynamic


`< CALLBACK >` indicates the action you want to assign o the event.
There are many pre-defined callbacks, but it is also possible to define custom
functions and attach them to the map.

Pre-defined click & pick callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Callbacks that can be used with both `m.cb.click` and `m.cb.pick`:

.. currentmodule:: eomaps.callbacks.click_callbacks

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

.. currentmodule:: eomaps.callbacks.pick_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    load
    highlight_geometry

Pre-defined keypress callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Callbacks that can be used with `m.cb.keypress`

.. currentmodule:: eomaps.callbacks.keypress_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    switch_layer

Pre-defined dynamic callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Callbacks that can be used with `m.cb.dynamic`

.. currentmodule:: eomaps.callbacks.dynamic_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    indicate_extent

.. _webmap_layers:


Custom callbacks
~~~~~~~~~~~~~~~~

Custom callback functions can be attached to the map via:

.. code-block:: python

    def some_callback(self, asdf, **kwargs):
        print("hello world")
        print("the position of the clicked pixel in plot-coordinates", kwargs["pos"])
        print("the dataset-index of the nearest datapoint", kwargs["ID"])
        print("data-value of the nearest datapoint", kwargs["val"])

        # `self` points to the underlying Maps-object, so you can
        # access all properties of the Maps object via:
        print("the plot-crs is:", self.plot_specs["plot_crs"])
        ...
        ...

    # attaching custom callbacks works completely similar for "click", "pick" and "keypress"!
    m = Maps()
    ...
    m.cb.pick.attach(some_callback, double_click=False, button=1, asdf=1)
    m.cb.click.attach(some_callback, double_click=False, button=2, asdf=1)
    m.cb.keypress.attach(some_callback, key="x", asdf=1)


- ❗ for pick callbacks, ``ID`` and ``val`` are not available!
- ❗ for click callbacks the kwargs ``ID`` and ``val`` are not available!
- ❗ for keypress callbacks the kwargs ``ID`` and ``val`` and ``pos`` are not available!

🛰 WebMap service layers
------------------------

WebMap services (TS/WMS/WMTS) can be attached to the map via:

.. code-block:: python

    m.add_wms.attach.< SERVICE > ... .add_layer.< LAYER >(...)


``< SERVICE >`` hereby specifies the pre-defined WebMap service you want to add,
and ``< LAYER >`` indicates the actual layer-name.

.. code-block:: python

    m = Maps(Maps.CRS.GOOGLE_MERCATOR) # (the native crs of the service)
    m.add_wms.OpenStreetMap.add_layer.default()

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_wms


.. note::
    It is highly recommended (and sometimes even required) to use the native crs
    of the WebMap service in order to avoid re-projecting the images
    (which degrades image quality and sometimes takes quite a lot of time to finish...)

    - most services come either in ``epsg=4326`` or in ``Maps.CRS.GOOGLE_MERCATOR`` projection


Pre-defined (global) WebMap services:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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


.. note::
    Services might be nested directory structures!
    The actual layer is always added via the `add_layer` directive.

        :code:`m.add_wms.<...>. ... .<...>.add_layer.<...>()`

    Some of the services dynamically fetch the structure via HTML-requests.
    Therefore it can take a short moment before autocompletion is capable of
    showing you the available options!
    A list of available layers from a sub-folder can be fetched via:

        :code:`m.add_wms.<...>. ... .<...>.layers`


.. _geodataframe:

🌵 GeoDataFrames and NaturalEarth features
------------------------------------------

A ``geopandas.GeoDataFrame`` can be added to the map via ``m.add_gdf()``.

.. code-block:: python

    import geopandas as gpd

    gdf = gpd.GeoDataFrame(geometries=[...], crs=...)

    m = Maps()
    m.add_gdf(gdf, fc="r", ec="g", lw=2)


It is possible to make the shapes of a ``GeoDataFrame`` pickable
(e.g. usable with ``m.cb.pick`` callbacks) by providing a ``picker_name``
(and optionally specifying a ``pick_method``).

Once the ``picker_name`` is specified, pick-callbacks can be attached via:

- ``m.cb.pick[<PICKER NAME>].attach.< CALLBACK >()``

| For example, to highlight the clicked country, you could use:

.. code-block:: python

    m = Maps()
    # get the GeoDataFrame for a given NaturalEarth feature
    gdf = m.add_feature.cultural_110m.admin_0_countries.get_gdf()

    # pick the shapes of the GeoDataFrame based on a "contains" query
    m.add_gdf(gdf, picker_name="countries", pick_method="contains")

    # temporarily highlight the picked geometry
    m.cb.pick["countries"].attach.highlight_geometry(fc="r", ec="g", lw=2)


Feature-layers provided by `NaturalEarth <https://www.naturalearthdata.com>` can be directly added to the plot via ``m.add_feature``.
If ``geopandas`` is installed, ``GeoDataFrames`` are used to visualize the features, and all aforementioned
functionalities of ``m.add_gdf`` can be used with NaturalEarth features as well!


The general call-signature is:

.. code-block:: python

    m = Maps()
    # just call the feature to add it to the map
    m.add_feature.< CATEGORY >.< FEATURE >(...)

    # if you only want to get the associated GeoDataFrame, you can use
    gdf = m.add_feature.< CATEGORY >.< FEATURE >.get_gdf()

Where ``< CATEGORY >`` specifies the resolution and general category of the feature, e.g.:
- cultural_10m, cultural_50m, cultural_110m
- physical_10m, physical_50m, physical_110m
- preset

.. code-block:: python

    m = Maps()
    m.add_feature.preset.ocean()
    m.add_feature.preset.coastline()
    m.add_feature.cultural_110m.admin_0_pacific_groupings(ec="r", lw=2)

    # (ONLY if geopandas is installed)
    m.add_feature.preset.countries(fc="none", ec="k", picker_name="countries", pick_method="contains")
    m.cb.pick["countries"].attach. ...

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_gdf
    Maps.add_feature

.. _annotations_and_markers:

🏕 Annotations and markers
--------------------------

Static annotations and markers can be added to the map via:

.. code-block:: python

    m = Maps()
    ...
    m.add_annotation( ... )
    m.add_marker( ... )

To indicate a rectangular area in a given crs, simply use ``m.indicate_extent``:

.. code-block:: python

    m = Maps(Maps.CRS.Orthographic())
    m.add_feature.preset.coastline()
    m.indicate_extent(x0=-45, y0=-45, x1=45, y1=45, crs=4326, fc="r", ec="k", alpha=0.5)


.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    add_marker
    add_annotation
    indicate_extent

.. _colorbar:

🌈 Colorbars (with a histogram)
-------------------------------

A colorbar with a colored histogram on top can be added to the map via ``m.add_colorbar``.

.. note::
    You must plot a dataset first! (e.g. by calling ``m.plot_map()``)
    The colorbar always represents the dataset that was used in the last call to ``m.plot_map()``.
    If you need multiple colorbars, use an individual layer for each dataset! (e.g. via ``m2  = m.new_layer()``)

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_colorbar


.. _scalebar:

📏 Scalebars
------------

A scalebar can be added to a map via:

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_scalebar

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

.. _compass:

🧭 Compass (or North Arrow)
---------------------------

A compass can be added to the map via:

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_compass

The compass object is dynamically updated if you pan/zoom the map, and it can be
dragged around on the map with the mouse.

.. code-block:: python

    m = Maps()
    m.add_feature.preset.coastline()
    c1 = m.add_compass(pos=(.25, .25), style="compass")
    c2 = m.add_compass(pos=(.5, .25), style="north arrow")    # to remove it, use

    c1.set_patch(facecolor="g", edgecolor="k", linewidth=2)

The returned ``compass`` object has the following useful methods assigned:

.. currentmodule:: eomaps.scalebar.Compass

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    set_patch
    set_scale
    set_pickable
    remove


📦 Reading data (NetCDF, GeoTIFF, CSV...)
-----------------------------------------

EOmaps provides some basic capabilities to read and plot directly from commonly used file-types.

.. note::

    The readers are intended for well-structured datasets!
    If they fail, simply read and extract the data manually and
    then set the data as usual via ``m.set_data(...)``.

    Under the hood, EOmaps uses the following libraries to read data:

    - GeoTIFF (``rioxarray`` + ``xarray.open_dataset``)
    - NetCDF (``xarray.open_dataset``)
    - CSV (``pandas.read_csv``)


Read relevant data from a file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``m.read_file.<filetype>(...)`` can be used to read all relevant data (e.g. values, coordinates & crs) from a file.

.. code-block:: python

    m = Maps()
    data = m.read_data.NetCDF(
        "the filepath",
        parameter="adsf",
        coords=("longitude", "latitude"),
        data_crs=4326,
        isel=dict(time=123)
        )
    m.set_data(**data)
    ...
    m.plot_map()


.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.read_file

.. currentmodule:: eomaps.reader

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    read_file.GeoTIFF
    read_file.NetCDF
    read_file.CSV

Initialize Maps-objects from a file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Maps.from_file.<filetype>(...)`` can be used to directly initialize a ``Maps`` object from a file.
(This is particularly useful if you have a well-defined file-structure that you need to access regularly)

.. code-block:: python

    m = Maps.from_file.GeoTIFF(
        "the filepath",
        classify_specs=dict(Maps.CLASSFIERS.Quantiles, k=10),
        plot_specs=dict(cmap="RdBu")
        )
    m.add_colorbar()
    m.cb.pick.attach.annotate()


.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.from_file

.. currentmodule:: eomaps.reader

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    from_file.GeoTIFF
    from_file.NetCDF
    from_file.CSV

Add new layers to existing Maps-objects from a file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to ``Maps.from_file``, a new layer based on a file can be added to an existing ``Maps`` object via ``Maps.new_layer_from_file.<filetype>(...)``.

.. code-block:: python

    m = Maps8()
    m.add_feature.preset.coastline()

    m2 = m.new_layer_from_file(
        "the filepath",
        parameter="adsf",
        coords=("longitude", "latitude"),
        data_crs=4326,
        isel=dict(time=123),
        classify_specs=dict(Maps.CLASSFIERS.Quantiles, k=10),
        plot_specs=dict(cmap="RdBu")
        )

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.new_layer_from_file

.. currentmodule:: eomaps.reader

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    new_layer_from_file.GeoTIFF
    new_layer_from_file.NetCDF
    new_layer_from_file.CSV





🔸 Miscellaneous
----------------
some additional functions and properties that might come in handy:

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:

    Maps.join_limits
    Maps.get_crs
    Maps.indicate_masked_points
    Maps.BM
    Maps.parent
    Maps.crs_plot
    Maps.add_colorbar

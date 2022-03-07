⚙ Usage
=========

🚀 Basics
---------

🌐 Initialization of Maps objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| EOmaps is all about ``Maps`` objects.                                                                    |
| To start creating a new (empty) map (in this case a plot in ``epsg=4326``, e.g. lon/lat projection), simply use: |

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

Possible shapes that can be used to quickly generate a plot for millions of datapoints are:

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


.. image:: _static/minigifs/plot_shapes.gif


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
or you can start to add :ref:`utility` and :ref:`callbacks`.

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

- ❗ for click callbacks the kwargs ``ID`` and ``val`` are set to ``None``!
- ❗ for keypress callbacks the kwargs ``ID`` and ``val`` and ``pos`` are set to ``None``!

.. _webmap_layers:

🛰 WebMap layers
----------------

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

.. table::
    :widths: 50 50
    :align: center

    +------------------------------------------------------------------------------------------------+-----------------------------------------+
    | .. code-block:: python                                                                         | .. image:: _static/minigifs/add_wms.png |
    |                                                                                                |   :align: center                        |
    |     from eomaps import Maps, MapsGrid                                                          |                                         |
    |     mg = MapsGrid(crs=Maps.CRS.GOOGLE_MERCATOR)                                                |                                         |
    |     mg.join_limits()                                                                           |                                         |
    |                                                                                                |                                         |
    |     mg.m_0_0.add_wms.OpenStreetMap.add_layer.default()                                         |                                         |
    |     mg.m_0_1.add_wms.OpenStreetMap.add_layer.stamen_toner()                                    |                                         |
    |                                                                                                |                                         |
    |     mg.m_1_1.add_wms.S1GBM.add_layer.vv()                                                      |                                         |
    |                                                                                                |                                         |
    |     # ... for more advanced                                                                    |                                         |
    |     layer = mg.m_1_0.add_wms.ISRIC_SoilGrids.nitrogen.add_layer.nitrogen_0_5cm_mean            |                                         |
    |     layer()                    # call the layer to add it to the map                           |                                         |
    |     layer.info                 # the "info" property provides useful informations on the layer |                                         |
    |     layer.add_legend()         # if a legend is provided, you can add id via:                  |                                         |
    |     layer.set_extent_to_bbox() # set the extent according to the boundingBox                   |                                         |
    |                                                                                                |                                         |
    +------------------------------------------------------------------------------------------------+-----------------------------------------+








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

💠 GeoDataFrames
~~~~~~~~~~~~~~~~~

A ``geopandas.GeoDataFrame`` can be added to the map via ``m.add_gdf()``.

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_gdf

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

.. table::
    :widths: 50 50
    :align: center

    +----------------------------------------------------------------------------+----------------------------------------------+
    | .. code-block:: python                                                     | .. image:: _static/minigifs/add_gdf_pick.gif |
    |                                                                            |   :align: center                             |
    |     from eomaps import Maps                                                |                                              |
    |     m = Maps()                                                             |                                              |
    |     # get the GeoDataFrame for a given NaturalEarth feature                |                                              |
    |     gdf = m.add_feature.cultural_110m.admin_0_countries.get_gdf()          |                                              |
    |                                                                            |                                              |
    |     # pick the shapes of the GeoDataFrame based on a "contains" query      |                                              |
    |     m.add_gdf(gdf, picker_name="countries", pick_method="contains")        |                                              |
    |                                                                            |                                              |
    |     # temporarily highlight the picked geometry                            |                                              |
    |     m.cb.pick["countries"].attach.highlight_geometry(fc="r", ec="g", lw=2) |                                              |
    |                                                                            |                                              |
    +----------------------------------------------------------------------------+----------------------------------------------+


🌴 NaturalEarth features
~~~~~~~~~~~~~~~~~~~~~~~~

Feature-layers provided by `NaturalEarth <https://www.naturalearthdata.com>`_ can be directly added to the plot via ``m.add_feature``.

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_feature

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

The most commonly used features are available as preset-layers:

.. currentmodule:: eomaps._containers._NaturalEarth_presets

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    coastline
    ocean
    land
    countries

+-------------------------------------------------------------------------+-------------------------------------------------+
| .. code-block:: python                                                  | .. image:: _static/minigifs/add_feature.gif     |
|                                                                         |   :align: center                                |
|     from eomaps import Maps                                             |                                                 |
|     m = Maps()                                                          |                                                 |
|     m.add_feature.preset.coastline()                                    |                                                 |
|     m.add_feature.preset.ocean()                                        |                                                 |
|     m.add_feature.preset.land()                                         |                                                 |
|     m.add_feature.preset.countries()                                    |                                                 |
|                                                                         |                                                 |
|     m.add_feature.physical_110m.lakes(ec="b")                           |                                                 |
|     m.add_feature.cultural_110m.admin_0_pacific_groupings(ec="m", lw=2) |                                                 |
|                                                                         |                                                 |
|     # (only if geopandas is installed)                                  |                                                 |
|     places = m.add_feature.cultural_110m.populated_places.get_gdf()     |                                                 |
|     m.add_gdf(places, markersize=places.NATSCALE/10, fc="r")            |                                                 |
|                                                                         |                                                 |
+-------------------------------------------------------------------------+-------------------------------------------------+

.. note::

    If ``geopandas`` is installed, ``GeoDataFrames`` are used to visualize the features, and all aforementioned
    functionalities of ``m.add_gdf`` can also directly be used with ``m.add_feature``!


.. _annotations_and_markers:

🏕 Annotations and Markers
--------------------------

🔴 Markers
~~~~~~~~~~~

Static markers can be added to the map via ``m.add_marker()``.

- If a dataset has been plotted, you can mark any datapoint via its ID, e.g. ``ID=...``
- To add a marker at an arbitrary position, use ``xy=(...)``

  - By default, the coordinates are assumed to be provided in the plot-crs
  - You can specify arbitrary coordinates via ``xy_crs=...``

- The radius is defined via ``radius=...``

  - By default, the radius is assumed to be provided in the plot-crs
  - You can specify the radius in an arbitrary crs via ``radius_crs=...``

- The marker-shape is set via ``shape=...``

  - Possible arguments are ``"ellipses"``, ``"rectangles"``, ``"geod_circles"``

- Additional keyword-arguments are passed to the matplotlib collections used to draw the shapes
  (e.g. "facecolor", "edgecolor", "linewidth", "alpha", etc.)

- Multiple markers can be added in one go by using lists for ``xy``, ``radius``, etc.


🛸 For dynamic markers checkout ``m.cb.click.attach.mark()`` or ``m.cb.pick.attach.mark()``


.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    add_marker

.. table::
    :widths: 50 50
    :align: center

    +---------------------------------------------------------------------------+-----------------------------------------+
    | .. code-block:: python                                                    | .. image:: _static/minigifs/markers.png |
    |                                                                           |   :align: center                        |
    |     from eomaps import Maps                                               |                                         |
    |     m = Maps(crs=4326)                                                    |                                         |
    |     m.add_feature.preset.coastline()                                      |                                         |
    |                                                                           |                                         |
    |     # ----- SINGLE MARKERS                                                |                                         |
    |     # by default, MARKER DIMENSIONS are defined in units of the plot-crs! |                                         |
    |     m.add_marker(xy=(0, 0), radius=20, shape="rectangles",                |                                         |
    |                  fc="y", ec="r", ls=":", lw=2)                            |                                         |
    |     m.add_marker(xy=(0, 0), radius=10, shape="ellipses",                  |                                         |
    |                  fc="darkorange", ec="r", ls=":", lw=2)                   |                                         |
    |                                                                           |                                         |
    |     # MARKER DIMENSIONS can be specified in any CRS!                      |                                         |
    |     m.add_marker(xy=(12000000, 0), xy_crs=3857,                           |                                         |
    |                  radius=5000000, radius_crs=3857,                         |                                         |
    |                  fc=(.5, .5, 0, .4), ec="r", lw=3, n=100)                 |                                         |
    |                                                                           |                                         |
    |     # GEODETIC CIRCLES with radius defined in meters                      |                                         |
    |     m.add_marker(xy=(-135, 35), radius=3000000, shape="geod_circles",     |                                         |
    |                  fc="none", ec="r", hatch="///", lw=2, n=100)             |                                         |
    |                                                                           |                                         |
    |     # ----- MULTIPLE MARKERS                                              |                                         |
    |     x = [-80, -40, 40, 80]    # x-coordinates of the markers              |                                         |
    |     fc = ["r", "g", "b", "c"] # the colors of the markers                 |                                         |
    |                                                                           |                                         |
    |     # N markers with the same radius                                      |                                         |
    |     m.add_marker(xy=(x, [-60]*4), radius=10, fc=fc)                       |                                         |
    |                                                                           |                                         |
    |     # N markers with different radius and properties                      |                                         |
    |     m.add_marker(xy=(x, [0]*4),  radius=[15, 10, 5, 2],                   |                                         |
    |                  fc=fc, ec=["none", "r", "g", "b"], alpha=[1, .5, 1, .5]) |                                         |
    |                                                                           |                                         |
    |     # N markers with different widths and heights                         |                                         |
    |     radius = ([15, 10, 5, 15], [5, 15, 15, 2])                            |                                         |
    |     m.add_marker(xy=(x, [60]*4), radius=radius, fc=fc)                    |                                         |
    +---------------------------------------------------------------------------+-----------------------------------------+


📑 Annotations
~~~~~~~~~~~~~~

Static annotations can be added to the map via ``m.add_annotation()``.

- The location is defined completely similar to ``m.add_marker()`` above.

  - You can annotate a datapoint via its ID, or arbitrary coordinates in any crs.

- Additional arguments are passed to matplotlibs ``plt.annotate`` and ``plt.text``

  - This gives a lot of flexibility to style the annotations!


🛸 For dynamic annotations checkout ``m.cb.click.attach.annotate()`` or ``m.cb.pick.attach.annotate()``


.. table::
    :widths: 50 50
    :align: center

    +----------------------------------------------------------------------------+---------------------------------------------+
    | .. code-block:: python                                                     | .. image:: _static/minigifs/annotations.png |
    |                                                                            |   :align: center                            |
    |     from eomaps import Maps                                                |                                             |
    |     import numpy as np                                                     |                                             |
    |     x, y = np.mgrid[-45:45, 20:60]                                         |                                             |
    |                                                                            |                                             |
    |     m = Maps(crs=4326)                                                     |                                             |
    |     m.set_data(x+y, x, y)                                                  |                                             |
    |     m.add_feature.preset.coastline(ec="k", lw=.75)                         |                                             |
    |     m.plot_map()                                                           |                                             |
    |                                                                            |                                             |
    |     # annotate any point in the dataset via the data-index                 |                                             |
    |     m.add_annotation(ID=345)                                               |                                             |
    |     # annotate an arbitrary position (in the plot-crs)                     |                                             |
    |     m.add_annotation(                                                      |                                             |
    |         xy=(20,25), text="A formula:\n $z=\sqrt{x^2+y^2}$",                |                                             |
    |         fontweight="bold", bbox=dict(fc=".6", ec="none", pad=2))           |                                             |
    |     # annotate coordinates defined in arbitrary crs                        |                                             |
    |     m.add_annotation(                                                      |                                             |
    |         xy=(2873921, 6527868), xy_crs=3857, xytext=(5,5),                  |                                             |
    |         text="A location defined \nin epsg 3857", fontsize=8,              |                                             |
    |         rotation=-45, bbox=dict(fc="skyblue", ec="k", ls="--", pad=2))     |                                             |
    |                                                                            |                                             |
    |     # functions can be used for more complex text                          |                                             |
    |     def text(m, ID, val, pos, ind):                                        |                                             |
    |         return f"lon={pos[0]}\nlat={pos[1]}"                               |                                             |
    |                                                                            |                                             |
    |     props = dict(xy=(-1.5, 38.45), text=text,                              |                                             |
    |                  arrowprops=dict(arrowstyle="-|>", fc="fuchsia",           |                                             |
    |                                  mutation_scale=15))                       |                                             |
    |     m.add_annotation(**props, xytext=(20, 20), color="darkred")            |                                             |
    |     m.add_annotation(**props, xytext=(-60, 20), color="purple")            |                                             |
    |     m.add_annotation(**props, xytext=(-60, -40), color="dodgerblue")       |                                             |
    |     m.add_annotation(**props, xytext=(20, -40), color="olive")             |                                             |
    |                                                                            |                                             |
    |     m.add_annotation(ID=2500, text=lambda ID, **kwargs: str(ID),           |                                             |
    |                      color="w", fontweight="bold", rotation=90,            |                                             |
    |                      arrowprops=dict(width=5, fc="b", ec="orange", lw=2),  |                                             |
    |                      bbox=dict(boxstyle="round, rounding_size=.8, pad=.5", |                                             |
    |                                fc="b", ec="orange", lw=2))                 |                                             |
    |                                                                            |                                             |
    |     m.add_annotation(ID=803, xytext=(-80,60),                              |                                             |
    |                      bbox=dict(ec="r", fc="gold", lw=3),                   |                                             |
    |                      arrowprops=dict(                                      |                                             |
    |                          arrowstyle="fancy", relpos=(.48,-.2),             |                                             |
    |                          mutation_scale=40, fc="r",                        |                                             |
    |                          connectionstyle="angle3, angleA=90, angleB=-25")) |                                             |
    |                                                                            |                                             |
    +----------------------------------------------------------------------------+---------------------------------------------+



▭ Rectangular areas
~~~~~~~~~~~~~~~~~~~

To indicate rectangular areas in any given crs, simply use ``m.indicate_extent``:

.. currentmodule:: eomaps.Maps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    indicate_extent


.. table::
    :widths: 50 50
    :align: center

    +-----------------------------------------------------------------------+-------------------------------------------------+
    | .. code-block:: python                                                | .. image:: _static/minigifs/indicate_extent.png |
    |                                                                       |   :align: center                                |
    |     from eomaps import Maps                                           |                                                 |
    |     m = Maps(crs=3035)                                                |                                                 |
    |     m.add_feature.preset.coastline(ec="k")                            |                                                 |
    |                                                                       |                                                 |
    |     # indicate a lon/lat rectangle                                    |                                                 |
    |     m.indicate_extent(-20, 35, 40, 50, hatch="//", fc="none", ec="r") |                                                 |
    |                                                                       |                                                 |
    |     # indicate some rectangles in epsg:3035                           |                                                 |
    |     hatches = ["*", "xxxx", "...."]                                   |                                                 |
    |     colors = ["yellow", "r", "darkblue"]                              |                                                 |
    |     for i, h, c in zip(range(3), hatches, colors):                    |                                                 |
    |         pos0 = (2e6 + i*2e6, 7e6, 3.5e6 + i*2e6, 9e6)                 |                                                 |
    |         pos1 = (2e6 + i*2e6, 7e6 + 3e6, 3.5e6 + i*2e6, 9e6 + 3e6)     |                                                 |
    |                                                                       |                                                 |
    |         m.indicate_extent(*pos0, crs=3857, hatch=h, lw=0.25, ec=c)    |                                                 |
    |         m.indicate_extent(*pos1, crs=3857, hatch=h, lw=0.25, ec=c)    |                                                 |
    |                                                                       |                                                 |
    |     # indicate a rectangle in Equi7Grid projection                    |                                                 |
    |     try: # (requires equi7grid package)                               |                                                 |
    |         m.indicate_extent(1000000, 1000000, 4800000, 4800000,         |                                                 |
    |                           crs=Maps.CRS.Equi7Grid_projection("EU"),    |                                                 |
    |                           fc="g", alpha=0.5, ec="k")                  |                                                 |
    |     except:                                                           |                                                 |
    |         pass                                                          |                                                 |
    +-----------------------------------------------------------------------+-------------------------------------------------+

.. _colorbar:

🌈 Colorbars (with a histogram)
-------------------------------

A colorbar with a colored histogram on top can be added to the map via ``m.add_colorbar``.

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_colorbar

.. table::
    :widths: 70 30
    :align: center

    +--------------------------------------------------------------------+------------------------------------------+
    | .. code-block:: python                                             | .. image:: _static/minigifs/colorbar.png |
    |                                                                    |   :align: center                         |
    |   from eomaps import Maps                                          |                                          |
    |   import numpy as np                                               |                                          |
    |   x, y = np.mgrid[-45:45, 20:60]                                   |                                          |
    |                                                                    |                                          |
    |   m = Maps()                                                       |                                          |
    |   m.add_feature.preset.coastline()                                 |                                          |
    |   m.set_data(data=x+y, xcoord=x, ycoord=y, crs=4326)               |                                          |
    |   m.set_classify_specs(scheme=Maps.CLASSIFIERS.EqualInterval, k=5) |                                          |
    |   m.plot_map()                                                     |                                          |
    |   m.add_colorbar(label="what a nice colorbar", histbins="bins")    |                                          |
    |                                                                    |                                          |
    +--------------------------------------------------------------------+------------------------------------------+

.. note::
    You must plot a dataset first! (e.g. by calling ``m.plot_map()``)
    The colorbar always represents the dataset that was used in the last call to ``m.plot_map()``.
    If you need multiple colorbars, use an individual layer for each dataset! (e.g. via ``m2  = m.new_layer()``)


.. _scalebar:

📏 Scalebars
------------

A scalebar can be added to a map via ``s = m.add_scalebar()``:

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_scalebar

.. table::
    :widths: 70 30
    :align: center

    +-----------------------------------+------------------------------------------+
    | .. code-block:: python            | .. image:: _static/minigifs/scalebar.gif |
    |                                   |   :align: center                         |
    |   from eomaps import Maps         |                                          |
    |   m = Maps(Maps.CRS.Sinusoidal()) |                                          |
    |   m.add_feature.preset.ocean()    |                                          |
    |   s = m.add_scalebar()            |                                          |
    +-----------------------------------+------------------------------------------+

The returned ``ScaleBar`` object provides the following useful methods:

.. currentmodule:: eomaps.scalebar

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    ScaleBar.remove
    ScaleBar.set_position
    ScaleBar.get_position
    ScaleBar.set_label_props
    ScaleBar.set_patch_props
    ScaleBar.set_scale_props
    ScaleBar.cb_offset_interval
    ScaleBar.cb_rotate_interval

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

.. _compass:

🧭 Compass (or North Arrow)
---------------------------

A compass can be added to the map via ``m.add_compass()``:

.. currentmodule:: eomaps

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_compass

.. table::
    :widths: 70 30
    :align: center

    +--------------------------------------+-----------------------------------------+
    | .. code-block:: python               | .. image:: _static/minigifs/compass.gif |
    |                                      |   :align: center                        |
    |   from eomaps import Maps            |                                         |
    |   m = Maps(Maps.CRS.Stereographic()) |                                         |
    |   m.add_feature.preset.ocean()       |                                         |
    |                                      |                                         |
    |   m.add_compass()                    |                                         |
    +--------------------------------------+-----------------------------------------+



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

.. _utility:


🦜 Utility widgets
------------------

Some helpful utility widgets can be added to a map via ``m.util.<...>``

.. currentmodule:: eomaps

.. autosummary::
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.util

Layer switching
~~~~~~~~~~~~~~~

To simplify switching between layers, there are currently 2 widgets available:

- ``m.util.layer_selector()`` : Add a set of clickable buttons to the map that activates the corresponding layers.
- ``m.util.layer_slider()`` : Add a slider to the map that iterates through the available layers.

.. currentmodule:: eomaps.utilities.utilities

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    layer_selector
    layer_slider


.. table::
    :widths: 70 30
    :align: center

    +------------------------------------+-------------------------------------------------+
    | .. code-block:: python             | .. image:: _static/minigifs/layer_selector.gif  |
    |                                    |    :align: center                               |
    |   from eomaps import Maps          |                                                 |
    |   m = Maps(layer="coastline")      |                                                 |
    |   m.add_feature.preset.coastline() |                                                 |
    |                                    |                                                 |
    |   m2 = m.new_layer(layer="ocean")  |                                                 |
    |   m2.add_feature.preset.ocean()    |                                                 |
    |                                    |                                                 |
    |   m.util.layer_selector()          |                                                 |
    +------------------------------------+-------------------------------------------------+


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

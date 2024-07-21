.. _basics:

🌱 Basics
---------

.. contents:: Contents
    :depth: 1
    :local:

Getting started
~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps

| EOmaps is all about :py:class:`Maps` objects.

The first :py:class:`Maps` object that is created will initialize a
`matplotlib.Figure <https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.figure.html>`_ and a
`cartopy.GeoAxes <https://scitools.org.uk/cartopy/docs/latest/reference/generated/cartopy.mpl.geoaxes.GeoAxes.html?highlight=geoaxes#cartopy.mpl.geoaxes.GeoAxes>`_
for a map.


.. grid:: 1 1 1 2

    .. grid-item::
        :columns: 12 12 12 8

        .. code-block:: python
            :name: test_init_map_objects

            from eomaps import Maps
            m = Maps(                        # Create a Maps-object
                crs=4326,                    #     Use lon/lat (epsg=4326) projection
                layer="base",                #     Assign the layer-name "base"
                figsize=(6, 5))              #     Set the figure-size to 6x5

            m.set_extent((-25, 35, 30, 70))  # Set the extent of the map
            m.set_frame(linewidth=3)         # Set the linewidth of the frame

            m.add_feature.preset.coastline() # Add coastlines
            m.add_feature.preset.ocean()     # Add ocean-coloring
            m.add_title("My first map",      # Add a title
                        fontsize=16)         #     With a fontsize of 16pt

    .. grid-item::
        :columns: 8 8 8 4

        .. image:: ../../_static/minigifs/basics_first_map.png


- ``crs`` represents the projection used for plotting
- ``layer`` represents the name of the layer associated with the Maps-object (see :ref:`layers`).
- all additional keyword arguments are forwarded to the creation of the `matplotlib-figure <https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.figure.html>`_
  (e.g.: ``figsize``, ``frameon``, ``edgecolor`` etc).


.. dropdown:: Possible ways for specifying the ``crs`` for plotting
    :open:
    :icon: info
    :color: info

    - If you provide an integer, it is identified as an epsg-code (e.g. ``4326``, ``3035``, etc.)

      - 4326 defaults to `PlateCarree` projection

    - All other CRS usable for plotting are accessible via ``Maps.CRS``, e.g.: ``crs=Maps.CRS.Orthographic()``, ``crs=Maps.CRS.Equi7_EU``...

      - ``Maps.CRS`` is just an accessor for ``cartopy.crs``
      - For a full list of available projections see: `Cartopy projections <https://scitools.org.uk/cartopy/docs/v0.15/crs/projections.html>`_

.. autosummary::
    :nosignatures:

    Maps
    Maps.CRS
    Maps.set_extent
    Maps.add_title

.. _layers:


Layer management
~~~~~~~~~~~~~~~~

A :py:class:`Maps` object represents one (or more) of the following things **on the assigned layer**:

- a collection of features, callbacks,..
- a single dataset  (and associated callbacks)


You can create as many layers as you need! The following image explains how it works in general:

.. image:: ../../_static/intro.png
   :width: 70%

.. dropdown:: Creating new layers
    :icon: info
    :color: info

    To create **a NEW layer**, use :py:meth:`m.new_layer("layer-name") <Maps.new_layer>`.

    - Features, Colorbars etc. added to a :py:class:`Maps` object are only visible if the associated layer is visible.
    - Callbacks are only executed if the associated layer is visible.
    - See :ref:`combine_layers` on how to select the currently visible layer(s).


    .. code-block:: python
        :name: test_layers_create_new_layer

        from eomaps import Maps
        m = Maps()                           # same as `m = Maps(crs=4326, layer="base")`
        m.add_feature.preset.coastline()     # add coastlines to the "base" layer

        m_ocean = m.new_layer(layer="ocean") # create a new layer named "ocean"
        m_ocean.add_feature.preset.ocean()   # features on this layer will only be visible if the "ocean" layer is visible!

        m.show_layer("ocean")                # show the "ocean" layer
        m.util.layer_selector()              # get a utility widget to quickly switch between existing layers


.. dropdown:: Multiple ``Maps`` objects on the same layer
    :icon: info
    :color: info

    If no explicit layer-name is provided, (e.g. :py:meth:`m.new_layer() <Maps.new_layer>`) the returned :py:class:`Maps` object will use the same layer as the parent :py:class:`Maps` object.

    - This is especially useful if you want to plot **multiple datasets on the same map and layer**.


    .. code-block:: python
        :name: test_layers_on_same_layer

        from eomaps import Maps
        m = Maps()                           # same as `m = Maps(layer="base")`
        m.add_feature.preset.coastline()     # add coastlines to the "base" layer

        m2 = m.new_layer()                   # "m2" is just another Maps-object on the same layer as "m"!
        m2.set_data(                         # assign a dataset to this Maps-object
            data=[.14,.25,.38],
            x=[1,2,3], y=[3,5,7],
            crs=4326)
        m2.plot_map()                        # plot the data
        m2.cb.pick.attach.annotate()         # attach a callback that picks datapoints from the data assigned to "m2"


.. dropdown:: The "all" layer
    :icon: info
    :color: info

    | There is one layer-name that has a special meaning... the ``"all"`` layer.
    | Any callbacks and features added to this layer will be **executed on ALL other layers** as well!

    You can add features and callbacks to the ``all`` layer via:

    - using the shortcut ``m.all. ...``
    - creating a dedicated :py:class:`Maps` object via ``m_all = Maps(layer="all")`` or ``m_all = m.new_layer("all")``
    - using the "layer" kwarg of functions e.g. ``m.plot_map(layer="all")``

    .. code-block:: python
        :name: test_all_layer

        from eomaps import Maps
        m = Maps()
        m.all.add_feature.preset.coastline() # add coastlines to ALL layers of the map

        m_ocean = m.new_layer(layer="ocean") # create a new layer named "ocean"
        m_ocean.add_feature.preset.ocean()   # add ocean-coloring to the "ocean" layer
        m.show_layer("ocean")                # show the "ocean" layer (note that it has coastlines as well!)

.. dropdown:: Artists added with methods **outside of EOmaps**
    :icon: info
    :color: info


    If you use methods that are **NOT provided by EOmaps**, the corresponding artists will always appear on the ``"base"`` layer by default!
    (e.g. ``cartopy`` or ``matplotlib`` methods accessible via ``m.ax.`` or ``m.f.`` like ``m.ax.plot(...)``)

    In most cases this behavior is sufficient... for more complicated use-cases, artists must be explicitly added to the **Blit Manager** (``m.BM``) so that ``EOmaps`` can handle drawing accordingly.

    To put the artists on dedicated layers, use one of the the following options:

    - For artists that are dynamically updated on each event, use ``m.BM.add_artist(artist, layer=...)``
    - For "background" artists that only require updates on pan/zoom/resize, use ``m.BM.add_bg_artist(artist, layer=...)``


    .. code-block:: python
        :name: test_add_custom_artists

        from eomaps import Maps
        m = Maps()
        m.all.add_feature.preset.coastline() # add coastlines to ALL layers of the map

        # draw a red X over the whole axis and put the lines
        # as background-artists on the layer "mylayer"
        (l1, ) = m.ax.plot([0, 1], [0, 1], lw=5, c="r", transform=m.ax.transAxes)
        (l2, ) = m.ax.plot([0, 1], [1, 0], lw=5, c="r", transform=m.ax.transAxes)

        m.BM.add_bg_artist(l1, layer="mylayer")
        m.BM.add_bg_artist(l2, layer="mylayer")
        m.show_layer("mylayer")

.. _combine_layers:

🗗 Combine & compare multiple layers
************************************

All maps of a figure always show **the same visible layer**.

The visible layer can be a **single layer-name**, or a **combination of multiple layer-names** in order to to transparently combine/overlay multiple layers.

.. dropdown:: Using the :ref:`companion_widget` to switch/overlay layers
    :icon: info
    :color: info

    Usually it is most convenient to combine and compare layers via the :ref:`companion_widget`.

    - Use the **dropdown-list** at the top-right to select a single layer or overlay multiple layers.

      - Click on a single layer to make it the visible layer.
      - Hold down ``control`` or ``shift`` to overlay multiple layers.

    .. image:: ../../_static/minigifs/select_layers_dropdown.gif

    |

    - Select one or more layers to dynamically adjust the stacking-order via the **layer-tabs** of the **Compare** and **Edit** views.

      - Hold down ``control`` while clicking on a tab to make it the visible layer.
      - Hold down ``shift`` while clicking on a tab to overlay multiple layers.
      - Re-arrange the tabs to change the stacking-order of the layers.

    .. image:: ../../_static/minigifs/rearrange_layers.gif

.. dropdown:: Programmatically switch/overlay layers
    :icon: info
    :color: info


    To programmatically switch between layers or view a layer that represents a **combination of multiple existing layers**, use :py:meth:`Maps.show_layer`.

    If you provide a single layer-name, the map will show the corresponding layer, e.g. ``m.show_layer("my_layer")``

    To **(transparently) overlay multiple existing layers**, use one of the following options:

    - Provide **multiple layer names or tuples** of the form ``(< layer-name >, < transparency [0-1] >)``

      - ``m.show_layer("A", "B")`` will overlay all features of the layer ``B`` on top of the layer ``A``.
      - ``m.show_layer("A", ("B", 0.5))`` will overlay the layer ``B`` with 50% transparency on top of the layer ``A``.

    - Provide a **combined layer name** by separating the individual layer names you want to show with a ``"|"`` character.

      - ``m.show_layer("A|B")`` will overlay all features of the layer ``B`` on top of the layer ``A``.
      - To transparently overlay a layer, add the transparency to the layer-name in curly-brackets, e.g.: ``"<layer-name>{<transparency>}"``.

        - ``m.show_layer("A|B{0.5}")`` will overlay the layer ``B`` with 50% transparency on top of the layer ``A``.


    .. code-block:: python
        :name: test_transparent_layer_overlay

        from eomaps import Maps
        m = Maps(layer="first")
        m.add_feature.physical.land(fc="k")

        m2 = m.new_layer("second")                # create a new layer and plot some data
        m2.add_feature.preset.ocean(zorder=2)
        m2.set_data(data=[.14,.25,.38],
                    x=[10,20,30], y=[30,50,70],
                    crs=4326)
        m2.plot_map(zorder=1)                     # plot the data "below" the ocean

        m.show_layer("first", ("second", .75))   # overlay the second layer with 25% transparency


.. dropdown:: Interactively overlay layers
    :icon: info
    :color: info

    .. currentmodule:: eomaps.callbacks.ClickCallbacks

    If you want to interactively overlay a part of the screen with a different layer, have a look at :py:meth:`peek_layer` callbacks!

    .. autosummary::
        :nosignatures:

        peek_layer

    .. code-block:: python
        :name: test_peek_layer_cb

        from eomaps import Maps
        m = Maps()
        m.all.add_feature.preset.coastline()
        m.add_feature.preset.urban_areas()

        m.add_feature.preset.ocean(layer="ocean")
        m.add_feature.physical.land(layer="land", fc="g")
        m.cb.click.attach.peek_layer(layer=["ocean", ("land", 0.5)], shape="round", how=0.4)


.. dropdown:: The "stacking order" of features and layers
    :icon: info
    :color: info

    The stacking order of features at the **same layer** is controlled by the ``zorder`` argument.

      - e.g. ``m.plot_map(zorder=1)`` or ``m.add_feature.cultural.urban_areas(zorder=10)``

    If you stack **multiple layers** on top of each other, the stacking is determined by the order of the layer-names (from right to left)

      - e.g. ``m.show_layer("A", "B")`` will show the layer ``"B"`` on top of the layer ``"A"``
      - you can stack as many layers as you like! ``m.show_layer("A", "B", ("C", 0.5), "D", ...)``

.. currentmodule:: eomaps.eomaps

.. autosummary::
    :nosignatures:

    Maps.new_layer
    Maps.all
    Maps.show
    Maps.show_layer
    Maps.fetch_layers


Image export (jpeg, png, svg, etc.)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the map is ready, an image of the map can be saved at any time by using :py:meth:`Maps.savefig`

.. code-block:: python
    :name: test_savefig_01

    from eomaps import Maps
    m = Maps()
    m.add_feature.preset.ocean()
    m.savefig("snapshot1.png", dpi=200, transparent=True)


To adjust the margins of the subplots, use :py:meth:`m.subplots_adjust`, or have a look at the :ref:`layout_editor`!

.. code-block:: python
    :name: test_subplots_adjust

    from eomaps import Maps
    m = Maps()
    m.subplots_adjust(left=0.1, right=0.9, bottom=0.05, top=0.95)

.. dropdown:: Export to clipboard (``ctrl + c``)
    :icon: info
    :color: info

    If you use ``PyQt5`` as matplotlib-backend, you can also press (``control`` + ``c``) to export the figure to the clipboard.

    The export will be performed using the **currently set export-parameters** in the :ref:`companion_widget` .
    Alternatively, you can also programmatically set the export-parameters via :py:meth:`Maps.set_clipboard_kwargs` .

.. dropdown:: Notes on exporting high-dpi figures
    :icon: info
    :color: info

    EOmaps tries its best to follow the WYSIWYG concept (e.g. *"What You See Is What You Get"*).
    However, if you export the map with a dpi-value other than ``100``, there are certain circumstances
    where the final image might look different.
    To summarize:

    - Changing the dpi of the figure requires a re-draw of all plotted datasets.

      - if you use ``shade`` shapes to represent the data, using a higher dpi-value can result in a very different appearance of the data!

    - WebMap services usually come as image-tiles with 96 dpi

      - by default, images are not re-fetched when saving the map to keep the original appearance
      - If you want to re-fetch the WebMap based on the export-dpi, use ``m.savefig(refetch_wms=True)``.

        - Note: increasing the dpi will result in an increase in the number of tiles that have to be fetched. If the number of required tiles is too large, the server might reject the request and the map might have gaps or no tiles at all.


.. currentmodule:: eomaps.eomaps

.. autosummary::
    :nosignatures:

    Maps.savefig
    Maps.subplots_adjust
    Maps.set_clipboard_kwargs



.. _multiple_maps:

Multiple Maps (and/or plots) in one figure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to combine multiple ``EOmaps`` maps and/or ordinary ``matpltolib`` plots in one figure.

The **figure** used by a :py:class:`Maps` object is set via the ``f`` argument, e.g.: ``m = Maps(f=...)``.
If no figure is provided, a new figure is created whenever you initialize a :py:class:`Maps` object.
The figure-instance of an existing :py:class:`Maps` object is accessible via ``m.f``


- To add a map to an existing figure, use ``m2 = m.new_map()`` (requires EOmaps >= v6.1) or pass the figure-instance on initialization of a new :py:class:`Maps` object.
- To add a ordinary ``matplotlib`` plot to a figure containing an eomaps-map, use ``m.f.add_subplot()`` or ``m.f.add_axes()``.


The **initial position of the axes** used by a :py:class:`Maps` object is set via the ``ax`` argument,
e.g.: ``m = Maps(ax=...)`` or ``m2 = m.new_map(ax=...)``

- The syntax for positioning axes is similar to matplotlibs ``f.add_subplot()`` or ``f.add_axes()``
- The axis-instance of an existing :py:class:`Maps` object is accessible via ``m.ax``
- ...for more information, checkout the matplotlib tutorial: `Customizing Figure Layouts <https://matplotlib.org/3.1.1/tutorials/intermediate/gridspec.html#sphx-glr-tutorials-intermediate-gridspec-py>`_


.. note::

    Make sure to have a look at the :ref:`layout_editor` on how to re-position and re-scale axes to arbitrary positions!


.. currentmodule:: eomaps.eomaps

.. autosummary::
    :nosignatures:

    Maps
    Maps.new_map

In the following, the most commonly used cases are introduced:

Grid positioning
****************
To position the map in a (virtual) grid, one of the following options are possible:

- Three integers ``(nrows, ncols, index)`` (or 2 integers and a tuple).

  - The map will take the ``index`` position on a grid with ``nrows`` rows and ``ncols`` columns.
  - ``index`` starts at 1 in the upper left corner and increases to the right.
  - ``index`` can also be a two-tuple specifying the (first, last)
    indices (1-based, and including last) of the map, e.g., ``Maps(ax=(3, 1, (1, 2)))`` makes a map that spans the upper 2/3 of the figure.


.. grid:: 1 1 1 2

    .. grid-item::
        :columns: 12 12 12 8

         .. code-block:: python
             :name: test_gridpos_1

             from eomaps import Maps
             # ----- initialize a figure with an EOmaps map
             # position = item 1 of a 2x1 grid
             m = Maps(ax=(2, 1, 1))
             # ----- add a normal matplotlib axes
             # position = item 2 of a 2x1 grid
             ax = m.f.add_subplot(2, 1, 2)

    .. grid-item-card::
        :columns: 6 6 6 4
        :img-background: ../../_static/grids/grid1.png


.. grid:: 1 1 1 2

    .. grid-item::
        :columns: 12 12 12 8

        .. code-block:: python
            :name: test_gridpos_2

            from eomaps import Maps
            # ----- initialize a figure with an EOmaps map
            # position = item 1 of a 2x2 grid
            m = Maps(ax=(2, 2, 1))
            # ----- add another Map to the same figure
            # position = item 3 of a 2x2 grid
            m2 = m.new_map(ax=(2, 2, 3))
            # ----- add a normal matplotlib axes
            # position = second item of a 1x2 grid
            ax = m.f.add_subplot(1, 2, 2)

    .. grid-item-card::
        :columns: 6 6 6 4
        :img-background: ../../_static/grids/grid2.png


.. grid:: 1 1 1 2

    .. grid-item::
        :columns: 12 12 12 8

        .. code-block:: python
            :name: test_gridpos_3

            from eomaps import Maps
            # ----- initialize a figure with an EOmaps map
            # position = item 1 of a 2x2 grid
            m = Maps(ax=(2, 2, 1))
            # ----- add another Map to the same figure
            # position = item 3 of a 2x2 grid
            m2 = m.new_map(ax=(2, 2, 3))
            # ----- add a normal matplotlib axes
            # position = second item of a 1x2 grid
            ax = m.f.add_subplot(1, 2, 2)

    .. grid-item-card::
        :columns: 6 6 6 4
        :img-background: ../../_static/grids/grid3.png





- A 3-digit integer.

  - The digits are interpreted as if given separately as three single-digit integers, i.e. ``Maps(ax=235)`` is the same as ``Maps(ax=(2, 3, 5))``.
  - Note that this can only be used if there are no more than 9 subplots.

.. grid:: 1 1 1 2

    .. grid-item::
        :columns: 12 12 12 8

        .. code-block:: python
            :name: test_gridpos_4

            from eomaps import Maps
            # ----- initialize a figure with an EOmaps map
            m = Maps(ax=211)
            # ----- add a normal matplotlib axes
            ax = m.f.add_subplot(212)

    .. grid-item-card::
        :columns: 6 6 6 4
        :img-background: ../../_static/grids/grid4.png


.. grid:: 1 1 1 2

    .. grid-item::
        :columns: 12 12 12 8

        .. code-block:: python
            :name: test_gridpos_5

            from eomaps import Maps
            # ----- initialize a figure with an EOmaps map
            m = Maps(ax=221)
            # ----- add 2 more Maps to the same figure
            m2 = m.new_map(ax=222)
            m3 = m.new_map(ax=223)
            # ----- add a normal matplotlib axes
            ax = m.f.add_subplot(224)

    .. grid-item-card::
        :columns: 6 6 6 4
        :img-background: ../../_static/grids/grid5.png



- A matplotlib `GridSpec <https://matplotlib.org/stable/api/_as_gen/matplotlib.gridspec.GridSpec.html>`_

.. grid:: 1 1 1 2

    .. grid-item::
        :columns: 12 12 12 8

        .. code-block:: python
            :name: test_gridpos_6

            from matplotlib.gridspec import GridSpec
            from eomaps import Maps

            gs = GridSpec(2, 2)
            m = Maps(ax=gs[0,0])
            m2 = m.new_map(ax=gs[0,1])
            ax = m.f.add_subplot(gs[1,:])

    .. grid-item-card::
        :columns: 6 6 6 4
        :img-background: ../../_static/grids/grid6.png


Absolute positioning
********************

To set the absolute position of the map, provide a list of 4 floats representing ``(left, bottom, width, height)``.

  - The absolute position of the map expressed in relative figure coordinates (e.g. ranging from 0 to 1)

.. note::

    Since the effective size of the Map is dependent on the current zoom-region, the position always
    represents the **maximal area** that can be occupied by the map!

    Also, using ``m.f.tight_layout()`` will not work with axes added in this way.


.. grid:: 1 1 1 2

    .. grid-item::
        :columns: 12 12 12 8

        .. code-block:: python
            :name: test_gridpos_abspos

            from eomaps import Maps
            # ----- initialize a figure with an EOmaps map
            m = Maps(ax=(.07, 0.53, .6, .3))
            # ----- add a normal matplotlib axes
            ax = m.f.add_axes((.35, .15, .6, .2))

    .. grid-item-card::
        :columns: 6 6 6 4
        :img-background: ../../_static/grids/grid7.png


Using already existing figures / axes
*************************************

It is also possible to insert an EOmaps map into an existing figure or reuse an existing axes.

  - To put a map on an existing figure, provide the figure-instance via ``m = Maps(f= <the figure instance>)``
  - To use an existing axes, provide the axes-instance via ``m = Maps(ax= <the axes instance>)``

    - NOTE: The axes **MUST** be a cartopy-``GeoAxes``!

.. code-block:: python
    :name: test_use_existing_figure

    import matplotlib.pyplot as plt
    import cartopy
    from eomaps import Maps

    f = plt.figure(figsize=(10, 7))
    ax = f.add_subplot(projection=cartopy.crs.Mollweide())

    m = Maps(f=f, ax=ax)


Dynamic updates of plots in the same figure
*******************************************

    As soon as a :py:class:`Maps`-object is attached to a figure, EOmaps will handle re-drawing of the figure!
    Therefore **dynamically updated** artists must be added to the "blit-manager" (``m.BM``) to ensure
    that they are correctly updated.

    - use ``m.BM.add_artist(artist, layer=...)`` if the artist should be re-drawn on **any event** in the figure
    - use ``m.BM.add_bg_artist(artist, layer=...)`` if the artist should **only** be re-drawn if the extent of the map changes

.. note::

    In most cases it is sufficient to simply add the whole axes-object as artist via ``m.BM.add_artist(...)``.

    This ensures that all artists of the axes are updated as well!


Here's an example to show how it works:



.. grid:: 1 1 1 2

    .. grid-item::

        .. code-block:: python
            :name: test_dynamic_axes_updates

            from eomaps import Maps

            # Initialize a new figure with an EOmaps map
            m = Maps(ax=223)
            m.ax.set_title("click me!")
            m.add_feature.preset.coastline()
            m.cb.click.attach.mark(radius=20, fc="none", ec="r", lw=2)

            # Add another map to the figure
            m2 = m.new_map(ax=224, crs=Maps.CRS.Mollweide())
            m2.add_feature.preset.coastline()
            m2.add_feature.preset.ocean()
            m2.cb.click.attach.mark(radius=20, fc="none", ec="r", lw=2, n=200)

            # Add a "normal" matplotlib plot to the figure
            ax = m.f.add_subplot(211)
            # Since we want to dynamically update the data on the axis, it must be
            # added to the BlitManager to ensure that the artists are properly updated.
            # (EOmaps handles interactive re-drawing of the figure)
            m.BM.add_artist(ax, layer=m.layer)

            # plot some static data on the axis
            ax.plot([10, 20, 30, 40, 50], [10, 20, 30, 40, 50])

            # define a callback that plots markers on the axis if you click on the map
            def cb(pos, **kwargs):
                ax.plot(*pos, marker="o")

            m.cb.click.attach(cb)        # attach the callback to the first map
            m.cb.click.share_events(m2)  # share click events between the 2 maps

    .. grid-item::

        .. image:: ../../_static/minigifs/dynamic_axes_updates.gif


MapsGrid objects
****************
.. currentmodule:: eomaps.eomaps

:py:class:`MapsGrid` objects can be used to create (and manage) multiple maps in one figure.

.. note::

    While :py:class:`MapsGrid` objects provide some convenience, starting with EOmaps v6.x,
    the preferred way of combining multiple maps and/or matplotlib axes in a figure
    is by using one of the options presented in the previous sections!

A :py:class:`MapsGrid` creates a grid of :py:class:`Maps` objects (and/or ordinary ``matpltolib`` axes),
and provides convenience-functions to perform actions on all maps of the figure.

.. code-block:: python
    :name: test_mapsgrid_01

    from eomaps import MapsGrid
    mg = MapsGrid(r=2, c=2, crs=4326)
    # you can then access the individual Maps-objects via:
    mg.m_0_0.add_feature.preset.ocean()
    mg.m_0_1.add_feature.preset.land()
    mg.m_1_0.add_feature.preset.urban_areas()
    mg.m_1_1.add_feature.preset.rivers_lake_centerlines()

    m_0_0_ocean = mg.m_0_0.new_layer("ocean")
    m_0_0_ocean.add_feature.preset.ocean()

    # functions executed on MapsGrid objects will be executed on all Maps-objects:
    mg.add_feature.preset.coastline()
    mg.add_compass()

    # to perform more complex actions on all Maps-objects, simply loop over the MapsGrid object
    for m in mg:
        m.add_gridlines(10, c="lightblue")

    # set the margins of the plot-grid
    mg.subplots_adjust(left=0.1, right=0.9, bottom=0.05, top=0.95, hspace=0.1, wspace=0.05)


Make sure to checkout the :ref:`layout_editor` which greatly simplifies the arrangement of multiple axes within a figure!

Custom grids and mixed axes
+++++++++++++++++++++++++++

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

- ``m_inits`` is used to initialize :py:class:`Maps` objects
- ``ax_inits`` is used to initialize ordinary ``matplotlib`` axes

The individual :py:class:`Maps` objects and ``matpltolib-Axes`` are then accessible via:

.. code-block:: python
    :name: test_mapsgrid_custom

    from eomaps import MapsGrid
    mg = MapsGrid(2, 3,
                m_inits=dict(ocean=(0, 0), land=(0, 2)),
                ax_inits=dict(someplot=(1, slice(0, 3)))
                )
    # Maps object with the name "left"
    mg.m_ocean.add_feature.preset.ocean()
    # the Maps object with the name "right"
    mg.m_land.add_feature.preset.land()

    # the ordinary matplotlib-axis with the name "someplot"
    mg.ax_someplot.plot([1,2,3], marker="o")
    mg.subplots_adjust(left=0.1, right=0.9, bottom=0.2, top=0.9)

❗ NOTE: if ``m_inits`` and/or ``ax_inits`` are provided, ONLY the explicitly defined objects are initialized!


- The initialization of the axes is based on matplotlib's `GridSpec <https://matplotlib.org/stable/api/_as_gen/matplotlib.gridspec.GridSpec.html>`_ functionality.
  All additional keyword-arguments (``width_ratios, height_ratios, etc.``) are passed to the initialization of the ``GridSpec`` object.

- To specify unique ``crs`` for each :py:class:`Maps` object, provide a dictionary of ``crs`` specifications.

.. code-block:: python
    :name: test_mapsgrid_custom_02

    from eomaps import MapsGrid
    # initialize a grid with 2 Maps objects and 1 ordinary matplotlib axes
    mg = MapsGrid(2, 2,
                m_inits=dict(top_row=(0, slice(0, 2)),
                            bottom_left=(1, 0)),
                crs=dict(top_row=4326,
                        bottom_left=3857),
                ax_inits=dict(bottom_right=(1, 1)),
                width_ratios=(1, 2),
                height_ratios=(2, 1))

    # a map extending over the entire top-row of the grid (in epsg=4326)
    mg.m_top_row.add_feature.preset.coastline()

    # a map in the bottom left corner of the grid (in epsg=3857)
    mg.m_bottom_left.add_feature.preset.ocean()

    # an ordinary matplotlib axes in the bottom right corner of the grid
    mg.ax_bottom_right.plot([1, 2, 3], marker="o")
    mg.subplots_adjust(left=0.1, right=0.9, bottom=0.1, top=0.9)


.. currentmodule:: eomaps.mapsgrid

.. autosummary::
    :nosignatures:

    MapsGrid
    MapsGrid.join_limits
    MapsGrid.share_click_events
    MapsGrid.share_pick_events
    MapsGrid.set_data
    MapsGrid.set_classify_specs
    MapsGrid.add_wms
    MapsGrid.add_feature
    MapsGrid.add_annotation
    MapsGrid.add_marker
    MapsGrid.add_gdf


Naming conventions and autocompletion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The goal of EOmaps is to provide a comprehensive, yet easy-to-use interface.

To avoid having to remember a lot of names, a concise naming-convention is applied so
that autocompletion can quickly narrow-down the search to relevant functions and properties.

Once a few basics keywords have been remembered, finding the right functions and properties should be quick and easy.

.. note::

    EOmaps works best in conjunction with "dynamic autocompletion", e.g. by using an interactive
    console where you instantiate a :py:class:`Maps` object first and then access dynamically updated properties
    and docstrings on the object.

    To clarify:

    - First, execute ``m = Maps()`` in an interactive console
    - then (inside the console, not inside the editor!) use autocompletion on ``m.`` to get
      autocompletion for dynamically updated attributes.

    For example the following accessors only work properly after the :py:class:`Maps` object has been initialized

    - :py:class:`Maps.add_wms` browse available WebMap services
    - :py:class:`Maps.set_classify` browse available classification schemes


The following list provides an overview of the naming-conventions used within EOmaps:

Add features to a map - "m.add\_"
*********************************
All functions that add features to a map start with ``add_``, e.g.:

- :py:class:`Maps.add_feature`, :py:class:`Maps.add_wms`, :py:meth:`Maps.add_annotation`, :py:meth:`Maps.add_marker`, :py:meth:`Maps.add_gdf`, ...

WebMap services (e.g. :py:class:`Maps.add_wms`) are fetched dynamically from the respective APIs.
Therefore the structure can vary from one WMS to another.
The used convention is the following:

- You can navigate into the structure of the API by using "dot-access" continuously
- once you reach a level that provides layers that can be added to the map, the ``.add_layer.`` directive will be visible
- any ``<LAYER>`` returned by ``.add_layer.<LAYER>`` can be added to the map by simply calling it, e.g.:

   - ``m.add_wms.OpenStreetMap.add_layer.default()``
   - ``m.add_wms.OpenStreetMap.OSM_mundialis.add_layer.OSM_WMS()``

Set data specifications - "m.set\_"
***********************************
All functions that set properties of the associated dataset start with ``set_``, e.g.:

- :py:meth:`Maps.set_data`, :py:class:`Maps.set_classify`, :py:class:`Maps.set_shape`, ...

Create new Maps-objects - "m.new\_"
***********************************
Actions that result in a new :py:class:`Maps` objects start with ``new_``.

- :py:meth:`Maps.new_layer`, :py:meth:`Maps.new_inset_map`, ...

Callbacks - "m.cb."
*******************
Everything related to callbacks is grouped under the ``cb`` accessor.

- use ``m.cb.<METHOD>.attach.<CALLBACK>()`` to attach pre-defined callbacks

  - ``<METHOD>`` hereby can be one of ``click``, ``pick`` or ``keypress``
    (but there's no need to remember since autocompletion will do the job!).

- use ``m.cb.<METHOD>.attach(custom_cb)`` to attach a custom callback

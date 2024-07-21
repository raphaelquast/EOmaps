
.. _vector_data:

💠 Vector Data
---------------

.. currentmodule:: eomaps.eomaps

For vector data visualization, EOmaps utilizes the plotting capabilities of  `geopandas <https://geopandas.org/en/stable/>`_ .

A ``geopandas.GeoDataFrame`` can be added to the map via :py:meth:`Maps.add_gdf`.
This is basically just a wrapper for the plotting capabilities of `geopandas <https://geopandas.org/en/stable/>`_
(e.g. `GeoDataFrame.plot(...) <https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.plot.html>`_ )
supercharged with EOmaps features.

- If you provide a string or `pathlib.Path` object to :py:meth:`Maps.add_gdf`, the contents of the file will be read into a ``GeoDataFrame``
  via `geopandas.read_file() <https://geopandas.org/en/stable/docs/user_guide/io.html#reading-spatial-data>`_.

  - Many file-types such as *shapefile*, *GeoPackage*, *geojson* ... are supported!


.. autosummary::
    :nosignatures:

    Maps.add_gdf


.. code-block:: python
    :name: test_add_gdf

    from eomaps import Maps
    # import geopandas as gpd
    # gdf = gpd.GeoDataFrame(geometries=[...], crs=...)<>

    m = Maps()
    # load the "ocean" data from NaturalEarth as a GeoDataFrame
    gdf = m.add_feature.physical.ocean.get_gdf(scale=50)
    # add the GeoDataFrame to the map
    m.add_gdf(gdf, fc="r", ec="g", lw=2)


It is possible to make the shapes of a ``GeoDataFrame`` pickable
(e.g. usable with ``m.cb.pick`` callbacks) by providing a ``picker_name``
(and specifying a ``pick_method``).

- use ``pick_method="contains"`` if your ``GeoDataFrame`` consists of **polygon-geometries** (the default)

  - pick a geometry if `geometry.contains(mouse-click-position) == True`

- use ``pick_method="centroids"`` if your ``GeoDataFrame`` consists of **point-geometries**

  - pick the geometry with the closest centroid


Once the ``picker_name`` is specified, pick-callbacks can be attached via:

- ``m.cb.pick[<PICKER NAME>].attach.< CALLBACK >()``


For example, to highlight the clicked country, you could use:


.. grid:: 1 1 1 2

    .. grid-item::

         .. code-block:: python
            :name: test_pick_gdf

            from eomaps import Maps
            m = Maps()
            # get the GeoDataFrame for a given NaturalEarth feature
            gdf = m.add_feature.cultural.admin_0_countries.get_gdf(scale=110)

            # pick the shapes of the GeoDataFrame based on a "contains" query
            m.add_gdf(gdf, picker_name="countries", pick_method="contains")

            # temporarily highlight the picked geometry
            m.cb.pick["countries"].attach.highlight_geometry(fc="r", ec="g", lw=2)

    .. grid-item::

        .. image:: ../../_static/minigifs/add_gdf_pick.gif
            :width: 75%

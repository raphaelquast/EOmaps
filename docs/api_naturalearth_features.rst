
.. _ne_features:

🌵 NaturalEarth features
------------------------

.. currentmodule:: eomaps.eomaps

Feature-layers provided by `NaturalEarth <https://www.naturalearthdata.com>`_ can be directly added to the map via :py:meth:`Maps.add_feature`.

.. autosummary::
    :nosignatures:

    Maps.add_feature


The call-signature is: ``m.add_feature.< CATEGORY >.< FEATURE >(...)``:

``< CATEGORY >`` specifies the general category of the feature, e.g.:

- ``cultural``: **cultural** features (e.g. countries, states etc.)
- ``physical``: **physical** features (e.g. coastlines, land, ocean etc.)
- ``preset``: a set of pre-defined layers for convenience (see below)

``< FEATURE >`` is the name of the NaturalEarth feature, e.g. ``"coastlines", "admin_0_countries"`` etc..

.. table::

    +-------------------------------------------------------------------------+-------------------------------------------------+
    | .. code-block:: python                                                  | .. image:: _static/minigifs/add_feature.gif     |
    |     :name: test_add_features                                            |   :align: center                                |
    |                                                                         |                                                 |
    |     from eomaps import Maps                                             | |img_minsize|                                   |
    |     m = Maps()                                                          |                                                 |
    |     m.add_feature.preset.coastline()                                    |                                                 |
    |     m.add_feature.preset.ocean()                                        |                                                 |
    |     m.add_feature.preset.land()                                         |                                                 |
    |     m.add_feature.preset.countries()                                    |                                                 |
    |                                                                         |                                                 |
    |     m.add_feature.physical.lakes(scale=110, ec="b")                     |                                                 |
    |     m.add_feature.cultural.admin_0_pacific_groupings(fc="none", ec="m") |                                                 |
    |                                                                         |                                                 |
    |     # (only if geopandas is installed)                                  |                                                 |
    |     places = m.add_feature.cultural.populated_places.get_gdf(scale=110) |                                                 |
    |     m.add_gdf(places, markersize=places.NATSCALE/10, fc="r")            |                                                 |
    |                                                                         |                                                 |
    +-------------------------------------------------------------------------+-------------------------------------------------+


`NaturalEarth <https://www.naturalearthdata.com>`_ provides features in 3 different scales: 1:10m, 1:50m, 1:110m.
By default EOmaps uses features at 1:50m scale. To set the scale manually, simply use the ``scale`` argument
when calling the feature.

- It is also possible to automatically update the scale based on the map-extent by using ``scale="auto"``.
  (Note that if you zoom into a new scale the data might need to be downloaded and reprojected so the map might be irresponsive for a couple of seconds until everything is properly cached.)

For convenience, multiple preset-features can also be added in one go via:

.. code-block:: python
    :name: test_add_multi_preset_features

    from eomaps import Maps
    m = Maps()
    m.add_feature.preset("coastline", "ocean", "land", scale=50)

If you want to get a ``geopandas.GeoDataFrame`` containing all shapes and metadata of a feature, use:
(Have a look at :ref:`vector_data` on how to add the obtained ``GeoDataFrame`` to the map)

.. code-block:: python
    :name: test_get_gdf

    from eomaps import Maps
    m = Maps()
    gdf = m.add_feature.physical.coastline.get_gdf(scale=10)

The most commonly used features are accessible with pre-defined colors via the ``preset`` category:

.. currentmodule:: eomaps.ne_features.NaturalEarth_presets

.. autosummary::
    :nosignatures:

    coastline
    ocean
    land
    countries
    urban_areas
    lakes
    rivers_lake_centerlines

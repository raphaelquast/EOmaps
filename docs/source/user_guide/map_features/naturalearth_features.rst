.. _ne_features:

🌵 NaturalEarth features
========================

EOmaps provides access to a large amount of basic map features provided by `NaturalEarth <https://www.naturalearthdata.com/>`_ via :py:meth:`Maps.add_feature <eomaps.Maps.add_feature>`.

.. note::
   The first time a feature is added to a map, the corresponding dataset is downloaded and stored locally for subsequent use.

.. dropdown:: Where is the data stored?

   EOmaps uses `cartopy's` API to download and cache the features.
   Run the following lines to get the used data-cache directory:

   .. code-block:: python

      from cartopy import config
      print(config["data_dir"])

Preset Features
---------------
For the most commonly used features, style-presets are available:

.. currentmodule:: eomaps.eomaps.Maps

.. autosummary::
    :nosignatures:

    add_feature.preset.coastline
    add_feature.preset.ocean
    add_feature.preset.land
    add_feature.preset.countries
    add_feature.preset.urban_areas
    add_feature.preset.lakes
    add_feature.preset.rivers_lake_centerlines

To add individual preset features (and optionally override style properties), use:

.. code-block:: python

   m.add_feature.preset.<FEATURE-NAME>(**STYLE-KWARGS)

.. tip::
   Th
   e native projection of the provided feature shapes is `epsg 4326` (e.g. PlateCarree or lon/lat projection).
   If you create a map in a different projection, the features have to be re-projected which might take some time.
   Re-projected features are cached until the kernel is restarted, so creating the same figure again will be much faster!


.. code-block:: python

    from eomaps import Maps
    m = Maps(facecolor="none", figsize=(6, 3.5))
    m.add_feature.preset.coastline()
    m.add_feature.preset.land()
    m.add_feature.preset.ocean()
    m.add_feature.preset.urban_areas()
    m.show()

.. image:: /_static/example_images/naturalearth_features/output1.png
   :width: 70%

You can override the feature-styles of the presets to quickly adjust the look of a map!

.. code-block:: python

    from eomaps import Maps
    m = Maps(facecolor="none", figsize=(6, 3.5))
    m.set_frame(ec="none")
    m.add_feature.preset.coastline()
    m.add_feature.preset.land(fc="darkkhaki")
    m.add_feature.preset.ocean(hatch="////", ec="w")
    m.add_feature.preset.urban_areas(ec="r", lw=0.25)
    m.show()

.. image:: /_static/example_images/naturalearth_features/output2.png
    :width: 70%


.. tip::
   It is also possible to add multiple features in one go with:
   (In this case, the provided style arguments are applied to **all** added features!)

   .. code-block:: python

      m.add_feature.preset(*FEATURE-NAMES, **STYLE-KWARGS)

.. code-block:: python

    from eomaps import Maps
    m = Maps(facecolor="none", figsize=(6, 3.5))
    m.add_feature.preset.coastline(lw=0.4)
    m.add_feature.preset("ocean", "land", "lakes", "rivers_lake_centerlines", "urban_areas", lw=0.2, alpha=0.5)
    m.show()

.. image:: /_static/example_images/naturalearth_features/output3.png
    :width: 70%


General Features
----------------

`NaturalEarth <https://www.naturalearthdata.com/>`_ provides features in 2 categories: **physical** and **cultural**.

You can access all available features of a corresponding category with:

.. code-block:: python

   m.add_feature.cultural.<FEATURE-NAME>(**STYLE-KWARGS)

.. code-block:: python

   m.add_feature.physical.<FEATURE-NAME>(**STYLE-KWARGS)

.. note::
   NaturalEarth provides features in 3 different scales: 1/10, 1/50 and 1/110.
   By default, an appropriate scale is selected based on the visible extent.
   You can manually select the scale to use with the ``scale`` argument (e.g. ``m.add_feature.physical.coastline(scale=10)``)

.. code-block:: python

    from eomaps import Maps
    m = Maps(facecolor="none")
    m.set_frame(rounded=0.2, ec="darkred", lw=3)
    m.set_extent_to_location("europe")

    m.add_feature.cultural.time_zones(fc="none", ec="teal")
    m.add_feature.cultural.admin_0_countries(fc="none", ec="k", lw=0.5)
    m.add_feature.cultural.urban_areas_landscan(fc="r", ec="none")
    m.add_feature.physical.lakes_europe(fc="b", ec="darkblue")
    m.add_feature.physical.rivers_europe(fc="none", ec="dodgerblue", lw=0.3)
    m.show()

.. image:: /_static/example_images/naturalearth_features/output4.png
    :width: 70%


Advanced usage - getting a hand on the data
-------------------------------------------

For more advanced use-cases, it can be necessary to access the underlying datasets.

.. tip::
   With EOmaps, you can quickly load the data of a selected feature as a `geopandas.GeoDataFrame` with:

   .. code-block:: python

      gdf = m.add_feature.cultural.<FEATURE-NAME>.get_gdf()

.. code-block:: python

    from eomaps import Maps
    m = Maps(facecolor="none")
    m.set_frame(rounded=0.3)
    m.add_feature.preset("coastline", "ocean", "land", alpha=0.5)


This will load the corresponding NaturalEarth dataset of the feature, containing the geometries and all associated metadata.

For example, the first 10 rows of the `places` GeoDataFrame look like this:


.. code-block:: python

    from IPython.display import display, HTML
    style = places[:10].style.set_table_styles([dict(selector="tr", props=[("font-size", "8pt")])])

    display(
        HTML(
            "<div style='width: 100%; height: 40ex; overflow: auto'>" +
            style.to_html() +
            "</div>"
        )
    )


You can then modify the obtained `GeoDataFrame` as you need and finally add it to the map with :py:meth:`Maps.add_gdf <eomaps.Maps.add_gdf>`

.. code-block:: python

    places = m.add_feature.cultural.populated_places.get_gdf(scale=110)

    m.show()

.. image:: /_static/example_images/naturalearth_features/output5.png
    :width: 70%

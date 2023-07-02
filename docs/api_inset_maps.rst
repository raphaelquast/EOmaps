
🔬 Inset Maps
--------------

.. contents:: Contents:
    :local:
    :depth: 1

How to create inset maps
~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps

Inset maps are used to show zoomed-in regions of a map and can be created with :py:meth:`Maps.new_inset_map`.

.. code-block:: python
    :name: test_inset_maps_01

    from eomaps import Maps
    m = Maps()                                      # the "parent" Maps-object (e.g. the "big" map)
    m.add_feature.preset.coastline()
    m_i = m.new_inset_map(xy=(125, 40), radius=10)  # a new Maps-object that represents the inset-map
    m_i.add_feature.preset.ocean()                  # it can be used just like any other Maps-objects!
    m_i.add_indicator_line()

- An inset-map is defined by it's center-position and a radius
- The used boundary-shape can be one of:

  - "ellipses" (e.g. projected ellipses with a radius defined in a given crs)
  - "rectangles" (e.g. projected rectangles with a radius defined in a given crs)
  - "geod_circles" (e.g. geodesic circles with a radius defined in meters)


For convenience, inset-map objects have the following special methods defined:

.. currentmodule:: eomaps.inset_maps

.. autosummary::
    :nosignatures:

    InsetMaps.set_inset_position
    InsetMaps.add_extent_indicator
    InsetMaps.add_indicator_line


Checkout the associated example on how to use inset-maps: :ref:`EOmaps_examples_inset_maps`

To quickly re-position (and re-size) inset-maps, have a look at the :ref:`layout_editor`!

.. table::
    :widths: 60 40
    :align: center

    +-----------------------------------------------------------------+--------------------------------------------+
    | .. code-block:: python                                          | .. image:: _static/minigifs/inset_maps.png |
    |     :name: test_inset_maps_02                                   |   :align: center                           |
    |                                                                 |                                            |
    |     from eomaps import Maps                                     | |img_minsize|                              |
    |     m = Maps(Maps.CRS.PlateCarree(central_longitude=-60))       |                                            |
    |     m.add_feature.preset.ocean()                                |                                            |
    |                                                                 |                                            |
    |     m_i = m.new_inset_map(xy=(5, 45), radius=10,                |                                            |
    |                           plot_position=(.3, .5), plot_size=.7, |                                            |
    |                           boundary=dict(ec="r", lw=4),          |                                            |
    |                           indicate_extent=dict(fc=(1,0,0,.5),   |                                            |
    |                                                ec="r", lw=1)    |                                            |
    |                           )                                     |                                            |
    |     m_i.add_indicator_line(m, c="r")                            |                                            |
    |                                                                 |                                            |
    |     m_i.add_feature.preset.coastline()                          |                                            |
    |     m_i.add_feature.preset.countries()                          |                                            |
    |     m_i.add_feature.preset.ocean()                              |                                            |
    |     m_i.add_feature.cultural.urban_areas(fc="r", scale=10)      |                                            |
    |     m_i.add_feature.physical.rivers_europe(ec="b", lw=0.25,     |                                            |
    |                                            fc="none", scale=10) |                                            |
    |     m_i.add_feature.physical.lakes_europe(fc="b", scale=10)     |                                            |
    |                                                                 |                                            |
    +-----------------------------------------------------------------+--------------------------------------------+

.. currentmodule:: eomaps.eomaps.Maps

.. autosummary::
    :nosignatures:

    new_inset_map


.. _zoomed_in_views_on_datasets:

Zoomed in views on datasets
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps

To simplify the creation of "zoomed-in" views on datasets, both the data and the classification
of the data must be the same.

For this purpose, EOmaps provides 2 convenience-functions:

- :py:meth:`Maps.inherit_data` : Use the same dataset as another :py:class:`Maps` object
- :py:meth:`Maps.inherit_classification`: Use the same classification as another :py:class:`Maps` object

  - Note that this means that the classification specs as well as ``vmin``, ``vmax`` and the used ``colormap`` will be the same!


.. code-block:: python
    :name: test_zoomed_in_data_maps

    from eomaps import Maps
    import numpy as np

    x, y = np.meshgrid(np.linspace(-20, 20, 50), np.linspace(-50, 60, 100))
    data = x + y

    m = Maps(ax=131)
    m.set_data(data, x, y)
    m.set_shape.raster()
    m.set_classify.Quantiles(k=10)
    m.plot_map(cmap="tab10", vmin=-10, vmax=40)

    # Create a new inset-map that shows a zoomed-in view on a given dataset
    m_inset = m.new_inset_map(xy=(5, 20), radius=8, plot_position=(0.75, .5))

    # inherit both the data and the classification specs from "m"
    m_inset.inherit_data(m)
    m_inset.inherit_classification(m)

    m_inset.set_shape.rectangles()
    m_inset.plot_map(ec="k", lw=0.25)

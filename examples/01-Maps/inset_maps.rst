===================================================
Inset-maps - get a zoomed-in view on selected areas
===================================================

Quickly create nice inset-maps to show details for specific regions.

- the location and extent of the inset can be defined in any given crs

  - (or as a geodesic circle with a radius defined in meters)

- the inset-map can have a different crs than the "parent" map

(requires EOmaps >= v4.1)


.. image:: /_static/example_images/example_inset_maps.png
    :width: 75%
    :align: center


.. literalinclude:: ../../../../examples/01-Maps/inset_maps.py

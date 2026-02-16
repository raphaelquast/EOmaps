===================================================
AGG filters - visual effects for your map-features!
===================================================

This more advanced example shows how to use the `AGG filter`_ feature of
matplotlib to get nice blurry country-boarders.

- A custom AGG filter is defined to apply a "gaussian blurr" to artists
- The filter is applied to the country-boundaries and map-frames



(requires EOmaps >= v9.0)


.. image:: /_static/example_images/example_agg_filters.png
    :width: 75%
    :align: center


.. literalinclude:: /../../examples/01-Maps/agg_filter.py


.. _AGG filter: https://matplotlib.org/stable/gallery/misc/demo_agg_filter.html

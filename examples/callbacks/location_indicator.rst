==================================================
Location indicator - dynamically updated gridlines
==================================================

.. currentmodule:: eomaps.eomaps

Example how to add a dynamically updated location-indicator to a map.

- Add dynamically updated gridlines with :py:meth:`add_gridlines(..., dynamic=True) <Maps.add_gridlines>` .
- Use :py:meth:`~Maps.transform_plot_to_lonlat()` to transform plot-coordinates to longitude/latitude values.
- Use the :py:meth:`~Maps.cb.move.make_artists_temporary()` contextmanager to remove
  all artists that are created within the context at the next `move` event.

(requires EOmaps >= v8.4)


.. image:: /_static/example_images/example_location_indicator.gif
    :width: 75%
    :align: center


.. literalinclude:: /../../examples/callbacks/location_indicator.py

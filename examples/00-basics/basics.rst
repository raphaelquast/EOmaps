========================
Basic data visualization
========================

.. currentmodule:: eomaps.eomaps

A example how to quickly visualize a dataset.

- Initialize a Maps-object with :py:class:`m = Maps() <Maps>`
- Assign a dataset to a :py:class:`Maps` object via :py:meth:`Maps.set_data()`
- Call :py:meth:`~Maps.plot_map()` to plot the data.
- Use :py:meth:`~Maps.add_colorbar()` after plotting a dataset to add a colorbar
  with a histogram on top to the figure.
- Use :py:meth:`~Maps.add_compass()` to add a compass to the map.
- Use :py:meth:`~Maps.add_logo()` to add a logo to the map.
- Use :py:meth:`Maps.cb.pick.attach.annotate()` to add a pre-defined callback that
  provides you with information on the closest datapoint if you click on the map.

.. image:: /_static/example_images/example_basics.gif
   :align: center


.. literalinclude:: /../../examples/01-Maps/basics.py

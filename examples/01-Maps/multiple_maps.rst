=====================================
Multiple Maps and Data-classification
=====================================

.. currentmodule:: eomaps.eomaps

- Create additional :py:class:`Maps` objects on a figure with :py:meth:`Maps.new_map()`
- | Classify your data via :py:attr:`Maps.set_classify`
  | (using classifiers provided by the ``mapclassify`` module)
- Set the way how datasets are represented on the map with :py:attr:`Maps.set_shape`
- Add callback functions that are executed if you click on a map with :py:attr:`Maps.cb.click.attach`
- Add callback functions that are executed if you click on a datapoint of a map with :py:attr:`Maps.cb.pick.attach`
- Share callback events between :py:class:`Maps`-objects with
  :py:meth:`Maps.cb.click.share_events()` and :py:meth:`Maps.cb.pick.share_events()`
- Use :py:meth:`Maps.apply_layout` to restore a previously saved map-layout.


.. image:: /_static/example_images/example_multiple_maps.gif
    :width: 75%
    :align: center

.. literalinclude:: ../../../../examples/01-Maps/multiple_maps.py

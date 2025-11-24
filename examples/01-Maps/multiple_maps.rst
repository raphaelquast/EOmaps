=====================================
Multiple Maps and Data-classification
=====================================

-  Create grids of maps via ``MapsGrid``
-  | Classify your data via ``m.set_classify_specs(scheme, **kwargs)``
   | (using classifiers provided by the ``mapclassify`` module)
-  | Add individual callback functions to each subplot via
   | ``m.cb.click.attach``, ``m.cb.pick.attach``
-  | Share events between Maps-objects of the MapsGrid via
   | ``mg.share_click_events()`` and ``mg.share_pick_events()``

.. image:: /_static/example_images/example_multiple_maps.gif
    :width: 75%
    :align: center

.. literalinclude:: ../../../../examples/01-Maps/multiple_maps.py




.. _shape_drawer:

|iconDraw| Draw shapes on the map
---------------------------------

.. currentmodule:: eomaps.eomaps

Starting with EOmaps v5.0 it is possible to draw simple shapes on the map using :py:class:`Maps.draw`.

- | The shapes can be saved to disk as geo-coded shapefiles using ``m.draw.save_shapes(filepath)``.
  | (Saving shapes requires the ``geopandas`` module!)

- To remove the most recently drawn shape use ``m.draw.remove_last_shape()``.

.. table::
    :widths: 60 40
    :align: center

    +--------------------------------------+---------------------------------------------+
    | .. code-block:: python               | .. image:: _static/minigifs/draw_shapes.gif |
    |                                      |   :align: center                            |
    |     m = Maps()                       |                                             |
    |     m.add_feature.preset.coastline() |                                             |
    |     m.draw.polygon()                 |                                             |
    +--------------------------------------+---------------------------------------------+

.. note::

    Drawing capabilities are fully integrated in the :ref:`companion_widget`.
    In most cases it is much more convenient to draw shapes with the widget
    instead of executing the commands in a console!

    In case you still stick to using the commands for drawing shape,
    it is important to know that the calls for drawing shapes are
    **non-blocking** and starting a new draw will silently cancel
    active draws!



.. currentmodule:: eomaps.draw

.. autosummary::
    :nosignatures:

    ShapeDrawer.new_drawer
    ShapeDrawer.rectangle
    ShapeDrawer.circle
    ShapeDrawer.polygon
    ShapeDrawer.save_shapes
    ShapeDrawer.remove_last_shape

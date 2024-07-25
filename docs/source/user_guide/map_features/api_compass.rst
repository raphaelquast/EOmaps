

.. _compass:

🧭 Compass (or North Arrow)
---------------------------
.. currentmodule:: eomaps.eomaps

A compass can be added to the map via :py:meth:`Maps.add_compass`:

- To add a **North-Arrow**, use ``m.add_compass(style="north arrow")``

.. admonition:: Interacting with the compass

    The compass is a pickable object!

    Click on it with the LEFT mouse button to drag it around!

    While a compass is picked (and the LEFT mouse button is pressed), the following
    additional interactions are available:

    - press ``delete`` on the keyboard: remove the compass from the plot
    - rotate the ``mouse wheel``: scale the size of the compass

.. autosummary::
    :nosignatures:

    Maps.add_compass


.. grid:: 1 1 1 2

    .. grid-item::

         .. code-block:: python
            :name: test_add_compass

            from eomaps import Maps
            m = Maps(Maps.CRS.Stereographic())
            m.add_feature.preset.ocean()

            m.add_compass()

    .. grid-item::

        .. image:: /_static/minigifs/compass.gif
            :width: 50%


The compass object is dynamically updated if you pan/zoom the map, and it can be
dragged around on the map with the mouse.

The returned ``compass`` object has the following useful methods assigned:

.. currentmodule:: eomaps.compass

.. autosummary::
    :nosignatures:

    Compass.remove
    Compass.set_patch
    Compass.set_scale
    Compass.set_pickable
    Compass.set_ignore_invalid_angles
    Compass.get_position
    Compass.get_scale

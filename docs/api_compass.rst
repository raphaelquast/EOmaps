

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

    - press ``delte`` on the keyboard: remove the compass from the plot
    - rotate the ``mouse wheel``: scale the size of the compass

.. autosummary::
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.add_compass



.. table::
    :widths: 70 30
    :align: center

    +--------------------------------------+-----------------------------------------+
    | .. code-block:: python               | .. image:: _static/minigifs/compass.gif |
    |   :name: test_add_compass            |   :align: center                        |
    |                                      |                                         |
    |   from eomaps import Maps            |                                         |
    |   m = Maps(Maps.CRS.Stereographic()) |                                         |
    |   m.add_feature.preset.ocean()       |                                         |
    |                                      |                                         |
    |   m.add_compass()                    |                                         |
    +--------------------------------------+-----------------------------------------+

The compass object is dynamically updated if you pan/zoom the map, and it can be
dragged around on the map with the mouse.

The returned ``compass`` object has the following useful methods assigned:

.. currentmodule:: eomaps.compass

.. autosummary::
    :nosignatures:
    :template: only_names_in_toc.rst

    Compass.remove
    Compass.set_patch
    Compass.set_scale
    Compass.set_pickable
    Compass.set_ignore_invalid_angles
    Compass.get_position
    Compass.get_scale

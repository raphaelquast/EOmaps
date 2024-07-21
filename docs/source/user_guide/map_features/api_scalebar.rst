
.. _scalebar:

📏 Scalebars
------------

.. currentmodule:: eomaps.eomaps

A scalebar can be added to a map via :py:meth:`Maps.add_scalebar`.

- By default, the scalebar will **dynamically estimate an appropriate scale and position** based on the currently visible map extent.

  - To change the number of segments for the scalebar, use ``s = m.add_scalebar(n=5)`` or ``s.set_n(5)``
  - To set the length of the segments to a fixed distance, use ``s = m.add_scalebar(scale=1000)`` or ``s.set_scale(1000)``
  - To fix the position of the scalebar, use ``s = m.add_scalebar(pos=(20, 40))`` or ``s.set_position(20, 40)``

In addition, many style properties of the scalebar can be adjusted to get the look you want.

 - check the associated setter-functions ``ScaleBar.set_< label / scale / lines / labels >_props`` below!

.. autosummary::
    :nosignatures:

    Maps.add_scalebar



.. grid:: 1 1 1 2

    .. grid-item::

         .. code-block:: python
            :name: test_add_scalebar

            from eomaps import Maps
            m = Maps(Maps.CRS.Sinusoidal())
            m.add_feature.preset.ocean()
            s = m.add_scalebar()

    .. grid-item::

        .. image:: ../../_static/minigifs/scalebar.gif
            :width: 50%


.. admonition:: Interacting with the scalebar

    The scalebar is a pickable object!

    Click on it with the LEFT mouse button to drag it around, and use the RIGHT
    mouse button (or press ``escape``) to make it fixed again.

    If the scalebar is picked (indicated by a red border), you can use the following
    functionalities to adjust some of the ScaleBar properties:

    - use the ``scroll-wheel`` to adjust the auto-scale of the scalebar (hold down ``shift`` for larger steps)
    - use ``control`` + ``scroll-wheel`` to adjust the size of the labels

    - press ``delete`` to remove the scalebar from the plot
    - press ``+``  or ``-`` to rotate the scalebar
    - press ``up/down/left/right`` to increase the size of the frame
    - press ``alt + up/down/left/right``: decrease the size of the frame
    - press ``control + left/right``: to increase / decrease the spacing between labels and scale
    - press ``control + up/down``: to rotate the labels

    Note: Once you have created a nice scalebar, you can always use ``s.print_code()`` to get an
    executable code that will reproduce the current appearance of the scalebar.

.. currentmodule:: eomaps.scalebar

The returned :py:class:`ScaleBar` object provides the following useful methods:

.. autosummary::
    :nosignatures:

    ScaleBar
    ScaleBar.print_code
    ScaleBar.apply_preset
    ScaleBar.remove
    ScaleBar.set_scale
    ScaleBar.set_n
    ScaleBar.set_position
    ScaleBar.set_label_props
    ScaleBar.set_scale_props
    ScaleBar.set_line_props
    ScaleBar.set_patch_props
    ScaleBar.set_auto_scale
    ScaleBar.set_pickable
    ScaleBar.set_size_factor
    ScaleBar.get_position
    ScaleBar.get_scale
    ScaleBar.get_size_factor

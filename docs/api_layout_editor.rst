
.. _layout_editor:

|iconLayout| Layout Editor
--------------------------

EOmaps provides a **Layout Editor** that can be used to quickly re-arrange the positions of all axes of a figure.
You can use it to simply drag the axes the mouse to the desired locations and change their size with the scroll-wheel.

**Keyboard shortcuts** are assigned as follows:

.. table::
    :widths: 52 45
    :align: center

    +-----------------------------------------------------------------------------------------+-----------------------------------------------+
    | - Press ``ALT + L``: enter the **Layout Editor** mode                                   | .. image:: _static/minigifs/layout_editor.gif |
    | - Press ``ALT + L`` again or ``escape`` to exit the **Layout Editor**                   |     :align: center                            |
    |                                                                                         |                                               |
    | **Pick** and **re-arrange** the axes as you like with the mouse.                        |                                               |
    |                                                                                         |                                               |
    | - To pick **multiple axes**, hold down ``shift``!                                       |                                               |
    | - | **Resize** picked axes with the **scroll-wheel**                                    |                                               |
    |   | (or by pressing the ``+`` and ``-`` keys)                                           |                                               |
    | - Hold down ``h`` or ``v`` to change horizontal/vertical size                           |                                               |
    | - Hold down ``control`` to change ratio between colorbar and histogram                  |                                               |
    |                                                                                         |                                               |
    | **Snap-To-Grid:**                                                                       |                                               |
    |                                                                                         |                                               |
    | - Press keys ``1-9`` to set the grid-spacing for the **"snap-to-grid"** functionality   |                                               |
    | - Press ``0`` to deactivate **"snap-to-grid"**                                          |                                               |
    |                                                                                         |                                               |
    | **Undo, Redo, Save:**                                                                   |                                               |
    |                                                                                         |                                               |
    | - Press ``control + z`` to undo the last step                                           |                                               |
    | - Press ``control + y`` to redo the last undone step                                    |                                               |
    | - Press ``P`` to print the current layout to the console                                |                                               |
    |                                                                                         |                                               |
    +-----------------------------------------------------------------------------------------+-----------------------------------------------+



Save and restore layouts
~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps

Once a layout (e.g. the desired position of the axes within a figure) has been arranged,
the layout can be saved and re-applied with:

- 🌟 :py:meth:`Maps.get_layout`: get the current layout (or dump the layout as a json-file)
- 🌟 :py:meth:`Maps.apply_layout`: apply a given layout (or load and apply the layout from a json-file)


It is also possible to enter the **Layout Editor** and save the layout automatically on exit with:

- 🌟 ``m.edit_layout(filepath=...)``: enter LayoutEditor and save layout as a json-file on exit


.. note::

    A layout can only be restored if the number (and order) of the axes remains the same!
    In other words:

    - you always need to save a new layout-file after adding additional axes (or colorbars!) to a map


.. currentmodule:: eomaps.eomaps.Maps

.. autosummary::
    :nosignatures:

    get_layout
    apply_layout
    edit_layout

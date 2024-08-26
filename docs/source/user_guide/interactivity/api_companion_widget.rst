

.. _companion_widget:

🧰 Companion Widget
--------------------

EOmaps comes with an awesome companion widget that provides many useful features for interactive data analysis.

- To activate the widget, press ``W`` on the keyboard **while the mouse is on top of the map you want to edit**.

  - If multiple maps are present in the figure, a green border indicates the map that is currently targeted by the widget.
  - Once the widget is initialized, pressing ``W`` will show/hide the widget.



.. |question_symbol| image:: ../../../../eomaps/qtcompanion/icons/info.png
  :height: 25px

.. admonition:: What are all those buttons and sliders for??

    To get information on how the individual controls work, simply **click on the** |question_symbol| **symbol** in the top left corner of the widget!

    - This will activate **help tooltips** that explain the individual controls.


.. image:: /_static/minigifs/companion_widget.gif
    :align: center

.. raw:: html

  <br>


.. admonition:: Setting figure export parameters on ``ctrl + c``

    Starting with EOmaps v7.0 it is possible to use ``ctrl + c`` to export a figure to the clipboard.

    This export will always use the **currently set export parameters** in the Companion Widget!


.. note::

    The companion-widget is written in ``PyQt5`` and therefore **only** works when using
    the ``matplotlib qt5agg`` backend (matplotlibs default if QT5 is installed)!

    To manually set the backend, execute the following lines at the start of your script:

    .. code-block:: python

        import matplotlib
        matplotlib.use("qt5agg")

    For more details, have a look at :ref:`configuring_the_editor`.



Additional information on Features and WebMaps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starting with EOmaps v7.1 the widget provides a new useful functionality to **quickly access important
information** of :ref:`Features <ne_features>` and :ref:`WebMaps <webmap_layers>` that were used to create a map.

If there is additional information available for an artist of a map, a |question_symbol| symbol will appear
next to the corresponding entry in the **Edit** tab that will open a popup window containing the following information:

- **Notes** and **infos** on the features
- Links to **sources**, **references** and **licensing details** (without warranty for correctness!)
- The **source code** to reproduce the current appearance of the feature

.. image:: /_static/minigifs/companion_widget_feature_info.gif
  :width: 50%

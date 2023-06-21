

.. _companion_widget:

🧰 Companion Widget
--------------------

Starting with v5.0, EOmaps comes with an awesome **companion widget** that greatly
simplifies using interactive capabilities.

- To activate the widget, press ``w`` on the keyboard **while the mouse is on top of the map you want to edit**.

  - If multiple maps are present in the figure, a green border indicates the map that is currently targeted by the widget.
  - Once the widget is initialized, pressing ``w`` will show/hide the widget.


.. admonition:: What are all those buttons and sliders for??

    To get information on how the individual controls work, simply **click on the** ``?`` **symbol** in the top left corner of the widget!

    - This will activate **help tooltips** that explain the individual controls.


.. image:: _static/minigifs/companion_widget.gif
    :align: center


.. note::

    The companion-widget is written in ``PyQt5`` and therefore **only** works when using
    the ``matplotlib qt5agg`` backend (matplotlibs default if QT5 is installed)!

    To manually set the backend, execute the following lines at the start of your script:

    .. code-block:: python

        import matplotlib
        matplotlib.use("qt5agg")

    For more details, have a look at :ref:`configuring_the_editor`.

The main purpose of the widget is to provide easy-access to features that usually don't need to go into
a python-script, such as:

- Compare layers (e.g. overlay multiple layers)
- Switch between existing layers (or combine existing layers)
- Add simple click or pick callbacks
- Quickly create new WebMap layers (or add WebMap services to existing layers)
- Draw shapes, add Annotations and NaturalEarth features to the map
- Quick-edit existing map-artists
  (show/hide, remove or set basic properties color, linewidth, zorder)
- Save the current state of the map to a file (at the desired dpi setting)
- A basic interface to plot data from files (with drag-and-drop support)
  (csv, NetCDF, GeoTIFF, shapefile)

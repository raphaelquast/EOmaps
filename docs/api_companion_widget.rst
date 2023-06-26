

.. _companion_widget:

🧰 Companion Widget
--------------------

EOmaps comes with an awesome companion widget that provides many useful features for interactive data analysis.

- To activate the widget, press ``W`` on the keyboard **while the mouse is on top of the map you want to edit**.

  - If multiple maps are present in the figure, a green border indicates the map that is currently targeted by the widget.
  - Once the widget is initialized, pressing ``W`` will show/hide the widget.



.. |question_symbol| image:: ../eomaps/qtcompanion/icons/info.png
  :height: 25px

.. admonition:: What are all those buttons and sliders for??

    To get information on how the individual controls work, simply **click on the** |question_symbol| **symbol** in the top left corner of the widget!

    - This will activate **help tooltips** that explain the individual controls.


.. image:: _static/minigifs/companion_widget.gif
    :align: center


.. raw:: html

  <br>

.. note::

    The companion-widget is written in ``PyQt5`` and therefore **only** works when using
    the ``matplotlib qt5agg`` backend (matplotlibs default if QT5 is installed)!

    To manually set the backend, execute the following lines at the start of your script:

    .. code-block:: python

        import matplotlib
        matplotlib.use("qt5agg")

    For more details, have a look at :ref:`configuring_the_editor`.

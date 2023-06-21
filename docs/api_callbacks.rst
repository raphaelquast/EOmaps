
.. _callbacks:

🛸 Callbacks - make the map interactive!
----------------------------------------

.. currentmodule:: eomaps

Callbacks are used to execute functions when you click on the map or press a key on the keyboard.

They can be attached to a :py:class:`Maps` object via:

.. code-block:: python

    m = Maps()
    ...
    m.cb.< EVENT >.attach.< CALLBACK >( **kwargs )

``< EVENT >`` specifies the event that will trigger the callback:

.. table::
    :width: 100 %
    :widths: auto

    +--------------------------------------------------------------+----------------------------------------------------------------------------------+
    | :class:`click <eomaps._cb_container.cb_click_container>`     | Callbacks that are executed if you click anywhere on the Map.                    |
    +--------------------------------------------------------------+----------------------------------------------------------------------------------+
    | :class:`pick <eomaps._cb_container.cb_pick_container>`       | Callbacks that select the nearest datapoint(s) if you click on the map.          |
    +--------------------------------------------------------------+----------------------------------------------------------------------------------+
    | :class:`move <eomaps._cb_container.cb_move_container>`       | Callbacks that are executed if you press a key on the keyboard.                  |
    +--------------------------------------------------------------+----------------------------------------------------------------------------------+
    | :class:`keypress <eomaps._cb_container.keypress_container>`  | Callbacks that are executed if you move the mouse without holding down a button. |
    +--------------------------------------------------------------+----------------------------------------------------------------------------------+


``< CALLBACK >`` specifies the action you want to assign to the event.

There are many :ref:`predefined_callbacks`, but it is also possible to define :ref:`custom_callbacks` and attach them to the map.


.. table::
    :width: 100 %
    :widths: auto

    +-----------------------------------------------------------------------------------+--------------------------------------------------+
    | .. code-block:: python                                                            | .. image:: _static/minigifs/simple_callbacks.gif |
    |     :name: test_add_callbacks                                                     |   :align: center                                 |
    |                                                                                   |                                                  |
    |     from eomaps import Maps                                                       |                                                  |
    |     import numpy as np                                                            |                                                  |
    |     x, y = np.mgrid[-45:45, 20:60]                                                |                                                  |
    |                                                                                   |                                                  |
    |     m = Maps(Maps.CRS.Orthographic())                                             |                                                  |
    |     m.all.add_feature.preset.coastline()                                          |                                                  |
    |     m.set_data(data=x+y**2, x=x, y=y, crs=4326)                                   |                                                  |
    |     m.plot_map()                                                                  |                                                  |
    |                                                                                   |                                                  |
    |     m2 = m.new_layer(copy_data_specs=True, layer="second_layer")                  |                                                  |
    |     m2.plot_map(cmap="tab10")                                                     |                                                  |
    |                                                                                   |                                                  |
    |     # get an annotation if you RIGHT-click anywhere on the map                    |                                                  |
    |     m.cb.click.attach.annotate(xytext=(-60, -60),                                 |                                                  |
    |                                bbox=dict(boxstyle="round", fc="r"))               |                                                  |
    |                                                                                   |                                                  |
    |     # pick the nearest datapoint if you click on the MIDDLE mouse button          |                                                  |
    |     m.cb.pick.attach.annotate(button=2)                                           |                                                  |
    |     m.cb.pick.attach.mark(buffer=1, permanent=False, fc="none", ec="r", button=2) |                                                  |
    |     m.cb.pick.attach.mark(buffer=4, permanent=False, fc="none", ec="r", button=2) |                                                  |
    |                                                                                   |                                                  |
    |     # peek at the second layer if you LEFT-click on the map                       |                                                  |
    |     m.cb.click.attach.peek_layer("second_layer", how=.25, button=3)               |                                                  |
    +-----------------------------------------------------------------------------------+--------------------------------------------------+


.. Note::

    Callbacks are only executed if the layer of the associated :py:class:`Maps` object is actually visible!
    (This assures that pick-callbacks always refer to the visible dataset.)

    To define callbacks that are executed independent of the visible layer, attach it to the ``"all"``
    layer using something like ``m.all.cb.click.attach.annotate()``.


In addition, each callback-container supports the following useful methods:

.. table::
    :width: 100 %
    :widths: auto

    +---------------------------------------------------------------------------------------------+---------------------------------------------------------------------------+
    | :class:`attach <eomaps._cb_container._click_container._attach>`                             | Attach custom or pre-defined callbacks to the map.                        |
    +---------------------------------------------------------------------------------------------+---------------------------------------------------------------------------+
    | :class:`remove <eomaps._cb_container._click_container.remove>`                              | Remove previously attached callbacks from the map.                        |
    +---------------------------------------------------------------------------------------------+---------------------------------------------------------------------------+
    | :class:`get <eomaps._cb_container._click_container._get>`                                   | Accessor for objects generated/retrieved by callbacks.                    |
    +---------------------------------------------------------------------------------------------+---------------------------------------------------------------------------+
    | :class:`set_sticky_modifiers <eomaps._cb_container._click_container.set_sticky_modifiers>`  | Define keys on the keyboard that should be treated as "sticky modifiers". |
    +---------------------------------------------------------------------------------------------+---------------------------------------------------------------------------+


.. currentmodule:: eomaps._cb_container._cb_container

.. autosummary::
    :nosignatures:
    :template: only_names_in_toc.rst

    share_events
    forward_events
    add_temporary_artist


.. _predefined_callbacks:

🍬 Pre-defined callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~

Pre-defined click, pick and move callbacks
******************************************

Callbacks that can be used with ``m.cb.click``, ``m.cb.pick`` and ``m.cb.move``:

.. currentmodule:: eomaps.callbacks.click_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    peek_layer
    annotate
    mark
    print_to_console


Callbacks that can be used with ``m.cb.click`` and ``m.cb.pick``:

.. currentmodule:: eomaps.callbacks.click_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    get_values
    clear_annotations
    clear_markers


Callbacks that can be used only with ``m.cb.pick``:

.. currentmodule:: eomaps.callbacks.pick_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    load
    highlight_geometry


Pre-defined keypress callbacks
******************************

Callbacks that can be used with ``m.cb.keypress``

.. currentmodule:: eomaps.callbacks.keypress_callbacks

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    switch_layer
    fetch_layers


.. _custom_callbacks:

👽 Custom callbacks
~~~~~~~~~~~~~~~~~~~

Custom callback functions can be attached to the map via:

.. code-block:: python

    m = Maps()
    ...
    m.cb.< EVENT >.attach(< CALLBACK FUNCTION >, **kwargs )


The ``< CALLBACK FUNCTION >`` must accept the following keyword-arguments:

- ``ID``: The ID of the picked data point

  - The index-value if a ``pandas.DataFrame`` is used as data
  - The (flattened) numerical index if a ``list`` or ``numpy.array`` is used as data

- ``ind``: The (flattened) numerical index (even if ``pandas.DataFrames`` are used)
- ``pos``: The coordinates of the picked data point in the crs of the plot
- ``val``: The value of the picked data point
- ``val_color``: The color of the picked data point


.. code-block:: python

    def some_callback(custom_kwarg, **kwargs):
        print("the value of 'custom_kwarg' is", custom_kwarg)
        print("the position of the clicked pixel in plot-coordinates", kwargs["pos"])
        print("the dataset-index of the nearest datapoint", kwargs["ID"])
        print("data-value of the nearest datapoint", kwargs["val"])
        print("the color of the nearest datapoint", kwargs["val_color"])
        print("the numerical index of the nearest datapoint", kwargs["ind"])
        ...

    # attaching custom callbacks works completely similar for "click", "pick" and "keypress"!
    m = Maps()
    ...
    m.cb.pick.attach(some_callback, double_click=False, button=1, custom_kwarg=1)
    m.cb.click.attach(some_callback, double_click=False, button=2, custom_kwarg=2)
    m.cb.keypress.attach(some_callback, key="x", custom_kwarg=3)


.. note::

    - ❗ for click callbacks, ``ID``, ``ind``, ``val`` and ``val_color`` are set to ``None``!
    - ❗ for keypress callbacks, ``ID``, ``ind``, ``pos`` ,``val`` and ``val_color`` are set to ``None``!

    For better readability it is recommended that you "unpack" used arguments like this:

    .. code-block:: python

        def cb(ID, val, **kwargs):
            print(f"the ID is {ID} and the value is {val}")




👾 Using modifiers for pick- click- and move callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to trigger ``pick``, ``click`` or ``move`` callbacks **only if a specific key is pressed on the keyboard**.

This is achieved by specifying a ``modifier`` when attaching a callback, e.g.:

.. code-block:: python
    :name: test_callback_modifiers

    from eomaps import Maps
    m = Maps()
    m.add_feature.preset.coastline()
    # a callback that is executed if NO modifier is pressed
    m.cb.move.attach.mark(radius=5)
    # a callback that is executed if 1 is pressed while moving the mouse
    m.cb.move.attach.mark(modifier="1", radius=10, fc="r", ec="g")
    # a callback that is executed if 2 is pressed while moving the mouse
    m.cb.move.attach.mark(modifier="2", radius=15, fc="none", ec="b")


To keep the last pressed modifier active until a new modifier is activated,
you can make it "sticky" by using ``m.cb.move.set_sticky_modifiers()``.

- "Sticky modifiers" remain activated until

  - A new (sticky) modifier is activated
  - ``ctrl + <current (sticky) modifier>`` is pressed
  - ``escape`` is pressed

NOTE: sticky modifiers are defined for each callback method individually!
(e.g. sticky modifiers are unique for click, pick and move callbacks)

.. code-block:: python
    :name: test_callback_sticky_modifiers

    from eomaps import Maps
    m = Maps()
    m.add_feature.preset.coastline()

    # a callback that is executed if 1 is pressed while clicking on the map
    m.cb.click.attach.annotate(modifier="1", text="modifier 1 active")
    # a callback that is executed if 2 is pressed while clicking on the map
    m.cb.click.attach.annotate(modifier="2", text="modifier 2 active")

    # make the modifiers 1 and 2 sticky for click callbacks
    m.cb.click.set_sticky_modifiers("1", "2")

    # note that the modifier 1 is not sticky for move callbacks!
    # m.cb.move.set_sticky_modifiers("1")  # (uncomment to make it sticky)
    m.cb.move.attach.mark(radius=5)
    m.cb.move.attach.mark(modifier="1", radius=5, fc="r")


🍭 Picking N nearest neighbours
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

[requires EOmaps >= 5.4]

By default pick-callbacks pick the nearest data point with respect to the click position.

To customize the picking-behavior, use ``m.cb.pick.set_props()``. The following properties can be adjusted:

- ``n``: The (maximum) number of data points to pick within the search-circle.
- ``search_radius``: The radius of a circle (in units of the plot-crs) that is used to identify the nearest neighbours.
- ``pick_relative_to_closest``: Set the center of the search-circle.

  - If True, the nearest neighbours are searched relative to the closest identified data point.
  - If False, the nearest neighbours are searched relative to the click position.

- ``consecutive_pick``: Pick data points individually or altogether.

  - If True, callbacks are executed for each picked point individually
  - If False, callbacks are executed only once and get lists of all picked values as input-arguments.

.. currentmodule:: eomaps._cb_container.cb_pick_container

.. autosummary::
    :nosignatures:
    :template: only_names_in_toc.rst

    set_props


.. table::
    :widths: 50 50
    :align: center

    +--------------------------------------------------------------------------------+--------------------------------------------+
    | .. code-block:: python                                                         | .. image:: _static/minigifs/pick_multi.gif |
    |     :name: test_callbacks_multi_pick                                           |   :align: center                           |
    |                                                                                |                                            |
    |     from eomaps import Maps                                                    |                                            |
    |     import numpy as np                                                         |                                            |
    |                                                                                |                                            |
    |     # create some random data                                                  |                                            |
    |     x, y = np.mgrid[-30:67, -12:50]                                            |                                            |
    |     data = np.random.randint(0, 100, x.shape)                                  |                                            |
    |                                                                                |                                            |
    |     # a callback to indicate the search-radius                                 |                                            |
    |     def indicate_search_radius(m, pos, *args, **kwargs):                       |                                            |
    |         art = m.add_marker(                                                    |                                            |
    |             xy=(np.atleast_1d(pos[0])[0],                                      |                                            |
    |                 np.atleast_1d(pos[1])[0]),                                     |                                            |
    |             shape="ellipses", radius=m.tree.d, radius_crs="out",               |                                            |
    |             n=100, fc="none", ec="k", lw=2)                                    |                                            |
    |         m.cb.pick.add_temporary_artist(art)                                    |                                            |
    |                                                                                |                                            |
    |     # a callback to set the number of picked neighbours                        |                                            |
    |     def pick_n_neighbours(m, n, **kwargs):                                     |                                            |
    |         m.cb.pick.set_props(n=n)                                               |                                            |
    |                                                                                |                                            |
    |                                                                                |                                            |
    |     m = Maps()                                                                 |                                            |
    |     m.add_feature.preset.coastline()                                           |                                            |
    |     m.set_data(data, x, y)                                                     |                                            |
    |     m.plot_map()                                                               |                                            |
    |     m.cb.pick.set_props(n=50, search_radius=10, pick_relative_to_closest=True) |                                            |
    |                                                                                |                                            |
    |     m.cb.pick.attach.annotate()                                                |                                            |
    |     m.cb.pick.attach.mark(fc="none", ec="r")                                   |                                            |
    |     m.cb.pick.attach(indicate_search_radius, m=m)                              |                                            |
    |                                                                                |                                            |
    |     for key, n in (("1", 1), ("2", 9), ("3", 50), ("4", 500)):                 |                                            |
    |         m.cb.keypress.attach(pick_n_neighbours, key=key, m=m, n=n)             |                                            |
    +--------------------------------------------------------------------------------+--------------------------------------------+

📍 Picking a dataset without plotting it first
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps

It is possible to attach ``pick`` callbacks to a :py:class:`Maps` object without plotting the data first
by using :py:meth:`Maps.make_dataset_pickable`.

.. code-block:: python
    :name: test_make_dataset_pickable

    from eomaps import Maps
    m = Maps()
    m.set_extent((0, 40, 30, 70))
    m.add_feature.preset.coastline()
    m.set_data([1, 2, 3], [10, 20, 30], [40, 50, 60])
    m.make_dataset_pickable()
    # now it's possible to attach pick-callbacks even though the data is still "invisible"
    m.cb.pick.attach.annotate()

.. note::

    Using :py:meth:`make_dataset_pickable` is ONLY necessary if you want to use ``pick``
    callbacks without actually plotting the data! Otherwise a call to :py:meth:`Maps.plot_map`
    is sufficient!

.. autosummary::
    :toctree: generated
    :nosignatures:
    :template: only_names_in_toc.rst

    Maps.make_dataset_pickable

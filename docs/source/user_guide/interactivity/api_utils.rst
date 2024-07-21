
.. _utility:

🔦 Utilities
-------------

.. currentmodule:: eomaps.eomaps

Some helpful utility widgets can be added to a map via :py:class:`Maps.util`.

.. autosummary::
    :nosignatures:

    Maps.util


Layer switching
~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.utilities

To simplify switching between layers, there are currently 2 widgets available:

- ``m.util.layer_selector()`` : Add a set of clickable :py:class:`LayerSelector` buttons to the map that activates the corresponding layers.
- ``m.util.layer_slider()`` : Add a :py:class:`LayerSlider` to the map that iterates through the available layers.

By default, the widgets will show all available layers (except the "all" layer) and the widget will be
**automatically updated** whenever a new layer is created on the map.

- To show only a subset of layers, provide an explicit list via: ``layers=[...layer names...]``.
- To exclude certain layers from the widget, use ``exclude_layers=[...layer-names to exclude...]``
- To remove a previously created widget ``s`` from the map, simply use ``s.remove()``

.. currentmodule:: eomaps.eomaps.Maps.util

.. autosummary::
    :nosignatures:

    layer_selector
    layer_slider



.. grid:: 1 1 1 2

    .. grid-item::

         .. code-block:: python
            :name: test_add_utils

            from eomaps import Maps
            m = Maps(layer="coastline")
            m.add_feature.preset.coastline()

            m2 = m.new_layer(layer="ocean")
            m2.add_feature.preset.ocean()

            s = m.util.layer_selector()

    .. grid-item::

        .. image:: ../../_static/minigifs/layer_selector.gif
            :width: 50%



🔸 Miscellaneous
----------------
Some additional functions and properties that might come in handy:

.. currentmodule:: eomaps.eomaps

.. autosummary::
    :nosignatures:

    Maps.on_layer_activation
    Maps.set_extent_to_location
    Maps.get_crs
    Maps.BM
    Maps.join_limits
    Maps.snapshot
    Maps.refetch_wms_on_size_change
    Maps.fetch_companion_wms_layers
    Maps.inherit_classification
    Maps.inherit_data


.. currentmodule:: eomaps

To customize the logging level, use :py:meth:`set_loglevel`:

.. code-block:: python
    :name: test_logging_set_level

    from eomaps import Maps, set_loglevel
    set_loglevel("info", fmt="timed")

    m = Maps()
    m.set_data([1, 2, 3], [1, 2, 3], [1, 2, 3])
    m.plot_map()

.. autosummary::
    :nosignatures:

    set_loglevel

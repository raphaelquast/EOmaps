

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


Logging
~~~~~~~
.. currentmodule:: eomaps

EOmaps uses the `logging <https://docs.python.org/3/library/logging.html>`_ module to handle messaging.
By default only messages with levels ``"warning"`` or ``"error"`` are shown.

To customize the logging level (and the formatting), use :py:meth:`set_loglevel`.

For example, if you want to get more detailed status messages during runtime, use:

.. code-block:: python
    :name: test_logging_set_level

    from eomaps import Maps, set_loglevel
    set_loglevel("info")

    m = Maps()
    m.set_data([1, 2, 3], [1, 2, 3], [1, 2, 3])
    m.plot_map()

    # 14:47:07.583 INFO: EOmaps: Starting to reproject 3 datapoints
    # 14:47:07.586 INFO: EOmaps: Done reprojecting
    # 14:47:07.696 INFO: EOmaps: Plotting 3 datapoints (ellipses)
    # 14:47:07.697 INFO: EOmaps: Estimating shape radius...
    # 14:47:07.698 INFO: EOmaps: radius = 5.e-01


.. autosummary::
    :nosignatures:

    set_loglevel

📚Logging
==========

.. currentmodule:: eomaps

EOmaps uses the `logging <https://docs.python.org/3/library/logging.html>`_ module to handle messaging.
By default only messages with levels ``"warning"`` or ``"error"`` are shown.

To customize the logging level (and the formatting), use :py:meth:`set_loglevel` or :py:meth:`Maps.config`.

For example, if you want to get more detailed status messages during runtime, use:

.. code-block:: python
    :name: test_logging_set_level

    from eomaps import Maps
    Maps.config(log_level="debug")

    # alternatively (for more customization) you can also use:
    # from eomaps import set_loglevel
    # set_loglevel("debug")

    m = Maps()
    m.set_data([1, 2, 3], [1, 2, 3], [1, 2, 3])
    m.plot_map()

    # 17:05:26.157 DEBUG: EOmaps: New figure created
    # 17:05:26.177 DEBUG: EOmaps: Preparing dataset
    # 17:05:26.181 INFO: EOmaps: Plotting 3 datapoints (ellipses)
    # 17:05:26.182 INFO: EOmaps: Estimating shape radius...
    # 17:05:26.183 INFO: EOmaps: radius = 5.e-01

.. autosummary::
    :nosignatures:

    set_loglevel

.. currentmodule:: eomaps.eomaps

.. autosummary::
    :nosignatures:

    Maps.config

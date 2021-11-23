⚙ API
=====

🔸 Initialize Maps objects
--------------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps
    eomaps.Maps.copy
    eomaps.MapsGrid


🔸 Set specifications
---------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.set_shape
    eomaps.Maps.set_data
    eomaps.Maps.set_data_specs
    eomaps.Maps.set_plot_specs
    eomaps.Maps.set_classify_specs


You can also get/set the specs with:

.. code-block:: python

    eomaps.Maps.data_specs.<...name...>
    eomaps.Maps.plot_specs.<...name...>
    eomaps.Maps.classify_specs.<...name...>


🔸 Plot the map and save it
---------------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.plot_map
    eomaps.Maps.savefig

    eomaps.Maps.figure


🔸 Add layers and objects
-------------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.add_wms
    eomaps.Maps.add_wmts
    eomaps.Maps.add_gdf
    eomaps.Maps.add_overlay
    eomaps.Maps.add_overlay_legend
    eomaps.Maps.add_coastlines

    eomaps.Maps.add_marker
    eomaps.Maps.add_annotation
    eomaps.Maps.add_colorbar

🔸 Connect Maps objects
-----------------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.connect
    eomaps.Maps.join_limits


🔸 Miscellaneous
----------------

.. autosummary::
    :toctree: generated
    :nosignatures:

    eomaps.Maps.get_crs
    eomaps.Maps.CRS
    eomaps.Maps.CLASSIFIERS
    eomaps.Maps.indicate_masked_points
    eomaps.Maps.parent
    eomaps.Maps.BM
    eomaps.Maps.crs_plot
    eomaps.Maps.layer

🔸 Add Callbacks
----------------

.. autosummary::
    :toctree: generated
    :nosignatures:


    eomaps.Maps.cb
    eomaps.Maps.cb.click
    eomaps.Maps.cb.pick
    eomaps.Maps.cb.keypress
    eomaps.Maps.cb.dynamic
    eomaps.Maps.cb.data

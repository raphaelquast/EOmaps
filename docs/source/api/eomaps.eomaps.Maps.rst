:orphan:

..
  NOTE: this file is copied to ../generated/eomaps.eomaps.Maps.rst before the docs are generated (see conf.py)
  to serve as the auto-generated file for Maps-objects!

:py:class:`Maps`
================

.. currentmodule:: eomaps.eomaps

.. autoclass:: Maps

Properties
----------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.f
    Maps.ax
    Maps.layer
    Maps.crs_plot

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.data
    Maps.data_specs
    Maps.classify_specs
    Maps.colorbar



Layers and Maps
---------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.new_map
    Maps.new_inset_map


.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.new_layer


.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.new_layer_from_file
    Maps.from_file


.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.show_layer
    Maps.fetch_layers
    Maps.on_layer_activation


Map Features
------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.add_feature
    Maps.add_wms


.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.add_gdf
    Maps.add_annotation
    Maps.add_marker
    Maps.add_line
    Maps.add_logo
    Maps.add_title
    Maps.indicate_extent


.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.add_compass
    Maps.add_gridlines
    Maps.add_scalebar

Callbacks
---------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.cb


.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.cb.click
    Maps.cb.pick
    Maps.cb.keypress
    Maps.cb.move


Data visualization
------------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.set_data
    Maps.set_shape
    Maps.set_classify
    Maps.set_classify_specs

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.inherit_data
    Maps.inherit_classification

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.plot_map
    Maps.add_colorbar
    Maps.make_dataset_pickable


Map Extent
----------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.set_extent
    Maps.get_extent
    Maps.set_extent_to_location
    Maps.join_limits


Layout and Export
-----------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.savefig
    Maps.snapshot

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.set_frame
    Maps.subplots_adjust

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.edit_layout
    Maps.get_layout
    Maps.apply_layout


Utilities
---------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.util
    Maps.draw
    Maps.edit_annotations


Miscellaneous
-------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.config
    Maps.BM

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.delay_draw
    Maps.fetch_companion_wms_layers
    Maps.refetch_wms_on_size_change
    Maps.cleanup
    Maps.get_crs

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.read_file.GeoTIFF
    Maps.read_file.NetCDF
    Maps.read_file.CSV

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst
    :nosignatures:

    Maps.show
    Maps.redraw
    Maps.copy

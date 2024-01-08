The :py:class:`Maps` object
===========================

.. currentmodule:: eomaps.eomaps

.. autosummary::
    :toctree: ../generated
    :template: custom-class-template.rst

    Maps


Class Methods
-------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.config

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.from_file.GeoTIFF
    Maps.from_file.NetCDF
    Maps.from_file.CSV

General Properties
------------------

.. autosummary::
    :toctree: ../generated
    :nosignatures:
    :template: obj_with_attributes_no_toc.rst

    Maps.f
    Maps.ax
    Maps.layer
    Maps.crs_plot

.. autosummary::
    :toctree: ../generated
    :nosignatures:
    :template: obj_with_attributes_no_toc.rst

    Maps.data
    Maps.colorbar

New Maps and Layers
-------------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.new_layer
    Maps.new_layer_from_file

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.new_map
    Maps.new_inset_map


Map Features
------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.add_feature
    Maps.add_wms

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

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

    Maps.add_compass
    Maps.add_gridlines
    Maps.add_scalebar



Data visualization
------------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.set_data
    Maps.set_shape
    Maps.set_classify
    Maps.set_classify_specs

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.inherit_data
    Maps.inherit_classification

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.plot_map
    Maps.add_colorbar
    Maps.make_dataset_pickable


Layer management
----------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.show_layer
    Maps.fetch_layers
    Maps.on_layer_activation


Figure Layout and Export
------------------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.set_frame
    Maps.savefig
    Maps.snapshot

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.subplots_adjust
    Maps.edit_layout
    Maps.get_layout
    Maps.apply_layout


Map Extent
----------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.set_extent
    Maps.get_extent
    Maps.set_extent_to_location
    Maps.join_limits


Interactive Editing
-------------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.edit_annotations
    Maps.draw


Miscellaneous
-------------

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.fetch_companion_wms_layers
    Maps.refetch_wms_on_size_change
    Maps.cleanup
    Maps.get_crs

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.read_file.GeoTIFF
    Maps.read_file.NetCDF
    Maps.read_file.CSV

.. autosummary::
    :toctree: ../generated
    :template: obj_with_attributes_no_toc.rst

    Maps.show
    Maps.redraw
    Maps.copy

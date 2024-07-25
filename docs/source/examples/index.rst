.. include:: substitutions.rst

.. _EOmaps_examples:

🗺 EOmaps examples
==================

This page contains a collection of examples that show how to create beautiful maps. Click on any image to see the full image and source code.


Basic data visualization
------------------------

.. nbgallery::
    :name: basics-gallery
    :glob:

    gallery/basics/*

Manage Maps
-----------

.. this part is used to generate toc
.. toctree::
    :hidden:
    :maxdepth: 1

    gallery/Maps/index

.. this part is used to generate the gallery
.. nblinkgallery::
    :name: Maps-gallery
    :glob:

    gallery/Maps/example_multiple_maps
    gallery/Maps/example_inset_maps


Images, Contours, WebMap
------------------------


.. this part is used to generate toc
.. toctree::
    :hidden:
    :maxdepth: 1

    gallery/images/index

.. this part is used to generate the gallery
.. nblinkgallery::
    :name: images-gallery
    :glob:

    gallery/images/RGB
    gallery/images/example_contour
    gallery/images/example_webmaps

Points, Lines, Polygons
-----------------------

.. this part is used to generate toc
.. toctree::
    :hidden:
    :maxdepth: 1

    gallery/geometry/index

.. this part is used to generate the gallery
.. nblinkgallery::
    :name: geometry-gallery
    :glob:

    gallery/geometry/example_lines
    gallery/geometry/example_vector_data



Geographical Map Components
---------------------------

.. this part is used to generate toc
.. toctree::
    :hidden:
    :maxdepth: 1

    gallery/geomap_components/index

.. this part is used to generate the gallery
.. nblinkgallery::
    :name: geomap_components-gallery
    :glob:

    gallery/geomap_components/example_gridlines
    gallery/geomap_components/example_scalebars

Overlays, markers, annotations
---------------------------------

.. nbgallery::
    :name: overlays-gallery
    :glob:

    gallery/overlays/*

Customize the appearance of the plot
------------------------------------

.. nbgallery::
    :name: custom-gallery
    :glob:

    gallery/custom/*

Widgets for data analysis
-------------------------

.. this part is used to generate toc
.. toctree::
    :hidden:
    :maxdepth: 1

    gallery/widgets/index

.. this part is used to generate the gallery
.. nblinkgallery::
    :name: widgets-gallery
    :glob:

    gallery/widgets/example_timeseries
    gallery/widgets/example_row_col_selector

Callbacks : turn your maps into interactive widgets
---------------------------------------------------

.. nbgallery::
    :name: callbacks-gallery
    :glob:

    gallery/callbacks/*

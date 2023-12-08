.. include:: substitutions.rst

.. image:: _static/logo.png
  :width: 40%
  :align: center
  :target: https://github.com/raphaelquast/EOmaps

.. raw:: html

    <br>
    <font size=5>Welcome to the documentation for <b>EOmaps</b>!</font>
    <p>


Here you can find detailed explanations on all the functionalities of EOmaps.

.. admonition:: Interested in contributing to EOmaps?

    | Found a bug or got an idea for an interesting feature?
    | Open an issue on `GitHub <https://github.com/raphaelquast/EOmaps>`_ or head over to the :doc:`contribute` to see how to setup EOmaps for development!



Getting Started
---------------

To get started, have a look at the :doc:`api_basics` section to get to know
the basic concepts of EOmaps.

In addition, there is also the :doc:`api_companion_widget` GUI that can be used to interactively edit/compare/overlay maps and explore the features and functionalities.

Data Visualization
------------------

Want to visualize some data? Have a look at the :doc:`api_data_visualization` section to learn how to create beautiful maps with your datasets!

EOmaps provides a variety of plot-shapes so you can select a shape that suits the structure, size and spatial representativeness of your data:


.. raw:: html

    <table width="100%" style="font-size:90%; table-layout:fixed; overflow:scroll;">
    <tr>
    <th width="20%">Ellipses</th>
    <th width="20%">Rectangles</th>
    <th width="20%">Geodesic Circles</th>
    <th width="20%">Raster</th>
    <th width="20%">Scatter Points</th>
    </tr>
    <tr>
    <th width="20%"><a href=api_data_visualization.html#ellipses><img src="_static/shape_imgs/ellipses.png"/></a></th>
    <th width="20%"><a href=api_data_visualization.html#rectangles><img src="_static/shape_imgs/rectangles.png"/></a></th>
    <th width="20%"><a href=api_data_visualization.html#geodesic-circles><img src="_static/shape_imgs/geod_circles.png"/></a></th>
    <th width="20%"><a href=api_data_visualization.html#raster><img src="_static/shape_imgs/raster.png"/></a></th>
    <th width="20%"><a href=api_data_visualization.html#scatter-points><img src="_static/shape_imgs/scatter_points.png"/></a></th>
    </tr>
    <tr>
    <th width="20%">Contour</th>
    <th width="20%">Voronoi Diagram</th>
    <th width="20%">Delaunay Triangulation</th>
    <th width="20%">Shade Raster</th>
    <th width="20%">Shade Points</th>
    </tr>
    <tr>
    <th width="20%"><a href=api_data_visualization.html#contour><img src="_static/shape_imgs/contour_filled.png"/></a></th>
    <th width="20%"><a href=api_data_visualization.html#voronoi-diagram><img src="_static/shape_imgs/voronoi_diagram.png"/></a></th>
    <th width="20%"><a href=api_data_visualization.html#delaunay-triangulation><img src="_static/shape_imgs/delaunay_triangulation.png"/></a></th>
    <th width="20%"><a href=api_data_visualization.html#shade-raster><img src="_static/shape_imgs/shade_raster.png"/></a></th>
    <th width="20%"><a href=api_data_visualization.html#shade-points><img src="_static/shape_imgs/shade_points.png"/></a></th>
    </tr>
    </table>


.. raw:: html

    </p>



Map Features
------------


EOmaps provides many useful tools to customize your maps.


.. list-table::
    :width: 100%
    :widths: 50 50

    * - |  :doc:`api_inset_maps`
        |  Create zoomed-in views on specific regions of a map.
      - |  :doc:`api_naturalearth_features`
        |  Add basic map features (coastlines, ocean-coloring etc. ) to the map.

    * - |  :doc:`api_webmaps`
        |  Add imagery provided by WebMap services (ts, wms, wmts, xyz) to the map.
      - |  :doc:`api_vector_data`
        |  Add vector geometries to the map.

    * - |  :doc:`api_annotations_markers_etc`
        |  Add markers, annotations, lines, logos etc. to the map.
      - |  :doc:`api_scalebar`
        |  Add a scalebar to the map.

    * - |  :doc:`api_compass`
        |  Add a compass (or North Arrow) to the map.
      - |  :doc:`api_gridlines`
        |  Add grid-lines (and optionally grid-labels) to the map.


Interactivity
-------------

With a few lines of code, you can turn your maps into interactive data-analysis widgets!

.. list-table::
    :width: 100%
    :widths: 50 50

    * - |  :doc:`api_companion_widget`
        |  A graphical user-interface to interact with the map.
      - |  :doc:`api_callbacks`
        |  Turn your maps into interactive data-analysis widgets.
    * - |  :doc:`api_layout_editor`
        |  Interactively re-arrange and re-size axes of a figure.
      - |  :doc:`api_draw`
        |  Interactively draw geometries on a map and export them as shapefiles.
    * - |  :doc:`api_utils`
        |  A collection of utility widgets (layer-sliders, layer-selectors)
      -

Miscellaneous
~~~~~~~~~~~~~

.. list-table::
    :width: 100%
    :widths: 50 50

    * - |  :doc:`api_logging`
        |  Details on logging.
      - |  :doc:`api_command_line_interface`
        |  How to use the command-line interface `eomaps`.
    * - |  :doc:`api_read_data`
        |  Read data from NetCDF, GeoTIFF or CSV files.
      - |  :doc:`api_misc`
        |  Additional functions and properties that might come in handy.




Examples
--------

Make sure to check out the :doc:`EOmaps_examples` for an overview of the capabilities (incl. source code)!

.. table::
   :width: 100%

   +-----------+-----------+-----------+-----------+-----------+
   | |eximg01| | |eximg02| | |eximg03| | |eximg04| | |eximg05| |
   +-----------+-----------+-----------+-----------+-----------+
   | |eximg06| | |eximg07| | |eximg08| | |eximg09| | |eximg10| |
   +-----------+-----------+-----------+-----------+-----------+
   | |eximg11| | |eximg12| | |eximg13| | |eximg14| | |eximg15| |
   +-----------+-----------+-----------+-----------+-----------+


.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: General

    installation
    FAQ


.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: How to use EOmaps

    api_basics
    api_data_visualization

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Map Features

    notebooks/inset_maps.ipynb
    notebooks/naturalearth_features.ipynb
    api_webmaps
    api_vector_data

    api_annotations_markers_etc
    api_scalebar
    api_compass
    api_gridlines

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Interactivity

    api_callbacks
    api_companion_widget
    api_layout_editor
    api_draw
    api_utils


.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Miscellaneous

    api_read_data
    api_command_line_interface
    api_logging
    api_misc


.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Examples

   EOmaps_examples


.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contribute

   contribute

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: API Reference

   reference

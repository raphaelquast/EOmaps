.. include:: substitutions.rst

.. image:: _static/logo.png
  :width: 40%
  :align: center
  :target: https://github.com/raphaelquast/EOmaps

.. raw:: html

    <br>
    <font size=5>Welcome to the documentation for <b>EOmaps</b>!</font>
    <p>


Here you can find detailed explanations on all the features and functionalities of EOmaps.


.. card:: Found a bug or got an idea for an interesting feature?

    .. grid:: 1 1 2 2
        :gutter: 1
        :margin: 0

        .. grid-item-card:: :doc:`contribute`
            :link: contribute
            :link-type: doc

            Get all information you need to start contributing to EOmaps!

        .. grid-item-card:: GitHub
            :link: https://github.com/raphaelquast/EOmaps/
            :link-type: url

            Open an issue or start a discussion on GitHub!



Getting Started
---------------

To get started, have a look at the :doc:`installation` instructions and the  :doc:`api_basics` section to learn how to use EOmaps!

In addition, there is also the :doc:`api_companion_widget` GUI that can be used to interactively edit/compare/overlay maps and explore the features and functionalities.


Data Visualization
------------------

Want to visualize some data? Have a look at the :doc:`api_data_visualization` section to learn how to create beautiful maps with your datasets!

EOmaps provides a variety of plot-shapes so you can select a shape that suits the structure, size and spatial representativeness of your data:

.. grid:: 2 2 5 5
    :gutter: 1

    .. grid-item-card:: Ellipses
        :img-bottom: _static/shape_imgs/ellipses.png
        :link: shp_ellipses
        :link-type: ref

    .. grid-item-card:: Rectangles
        :img-bottom: _static/shape_imgs/rectangles.png
        :link: shp_rectangles
        :link-type: ref

    .. grid-item-card:: Geodesic Circles
        :img-bottom: _static/shape_imgs/geod_circles.png
        :link: shp_geod_circles
        :link-type: ref

    .. grid-item-card:: raster
        :img-bottom: _static/shape_imgs/raster.png
        :link: shp_raster
        :link-type: ref

    .. grid-item-card:: Scatter Points
        :img-bottom: _static/shape_imgs/scatter_points.png
        :link: shp_scatter
        :link-type: ref

    .. grid-item-card:: Contour
        :img-bottom: _static/shape_imgs/contour.png
        :link: shp_contour
        :link-type: ref

    .. grid-item-card:: Voronoi Diagram
        :img-bottom: _static/shape_imgs/voronoi_diagram.png
        :link: shp_voronoi
        :link-type: ref

    .. grid-item-card:: Delaunay Triangulation
        :img-bottom: _static/shape_imgs/delaunay_triangulation.png
        :link: shp_delaunay
        :link-type: ref

    .. grid-item-card:: Shade Raster
        :img-bottom: _static/shape_imgs/shade_raster.png
        :link: shp_shade_raster
        :link-type: ref

    .. grid-item-card:: Shade Points
        :img-bottom: _static/shape_imgs/shade_points.png
        :link: shp_shade_points
        :link-type: ref


Map Features
------------

EOmaps provides many useful tools to customize your maps.

.. grid:: 1 1 1 2
    :gutter: 1

    .. grid-item-card:: :doc:`notebooks/naturalearth_features`
        :link: notebooks/naturalearth_features
        :link-type: doc
        :shadow: none

        Add basic map features (coastlines, ocean-coloring etc. ) to the map.

    .. grid-item-card:: :doc:`api_webmaps`
        :link: api_webmaps
        :link-type: doc
        :shadow: none

        Add imagery provided by WebMap services to the map.

    .. grid-item-card:: :doc:`notebooks/inset_maps`
        :link: notebooks/inset_maps
        :link-type: doc
        :shadow: none

        Create zoomed-in views on specific regions of a map.

    .. grid-item-card:: :doc:`api_vector_data`
        :link: api_vector_data
        :link-type: doc
        :shadow: none

        Add vector geometries to the map.

    .. grid-item-card:: :doc:`api_annotations_markers_etc`
        :link: api_annotations_markers_etc
        :link-type: doc
        :shadow: none

        Add markers, annotations, lines, logos etc. to the map.

    .. grid-item-card:: :doc:`api_scalebar`
        :link: api_scalebar
        :link-type: doc
        :shadow: none

        Add a scalebar to the map.

    .. grid-item-card:: :doc:`api_compass`
        :link: api_compass
        :link-type: doc
        :shadow: none

        Add a compass (or North Arrow) to the map.

    .. grid-item-card:: :doc:`api_gridlines`
        :link: api_gridlines
        :link-type: doc
        :shadow: none

        Add grid-lines (and optionally grid-labels) to the map.


Interactivity
-------------

With a few lines of code, you can turn your maps into interactive data-analysis widgets!

.. grid:: 1 1 1 2
    :gutter: 1

    .. grid-item-card:: :doc:`api_companion_widget`
        :link: api_companion_widget
        :link-type: doc
        :shadow: none

        A graphical user-interface to interact with the map.

    .. grid-item-card:: :doc:`api_callbacks`
        :link: api_callbacks
        :link-type: doc
        :shadow: none

        Turn your maps into interactive data-analysis widgets.

    .. grid-item-card:: :doc:`api_layout_editor`
        :link: api_layout_editor
        :link-type: doc
        :shadow: none

        Interactively re-arrange and re-size axes of a figure.

    .. grid-item-card:: :doc:`api_draw`
        :link: api_draw
        :link-type: doc
        :shadow: none

        Interactively draw geometries on a map and export them as shapefiles.

    .. grid-item-card:: :doc:`api_utils`
        :link: api_utils
        :link-type: doc
        :shadow: none

        A collection of utility widgets (layer-sliders, layer-selectors)


Miscellaneous
~~~~~~~~~~~~~

.. grid:: 1 1 1 2
    :gutter: 1

    .. grid-item-card:: :doc:`api_logging`
        :link: api_logging
        :link-type: doc
        :shadow: none

        Details on logging.

    .. grid-item-card:: :doc:`api_command_line_interface`
        :link: api_command_line_interface
        :link-type: doc
        :shadow: none

        How to use the ``eomaps`` command-line interface.

    .. grid-item-card:: :doc:`api_read_data`
        :link: api_companion_widget
        :link-type: doc
        :shadow: none

        Read data from NetCDF, GeoTIFF or CSV files.

    .. grid-item-card:: :doc:`api_misc`
        :link: api_misc
        :link-type: doc
        :shadow: none

        Additional functions and properties that might come in handy.


API Reference
~~~~~~~~~~~~~

.. grid:: 1 1 1 2
    :gutter: 1

    .. grid-item-card:: EOmaps API reference
        :link: api/reference
        :link-type: doc
        :shadow: none

        Detailed information on the API of EOmaps.


Examples
--------

Make sure to check out the :doc:`Examples <EOmaps_examples>` for an overview of the capabilities (incl. source code)!

.. include:: example_galery.rst

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: General

    installation
    FAQ

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contribute

   contribute

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
   :maxdepth: 1
   :caption: API Reference

   api/reference

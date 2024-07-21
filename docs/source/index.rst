.. include:: examples/substitutions.rst

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

        .. grid-item-card:: :doc:`contribute/contribute`
            :link: contribute/contribute
            :link-type: doc

            Get all information you need to start contributing to EOmaps!

        .. grid-item-card:: GitHub
            :link: https://github.com/raphaelquast/EOmaps/
            :link-type: url

            Open an issue or start a discussion on GitHub!



Getting Started
---------------

To get started, have a look at the :doc:`installation` instructions and the  :doc:`user_guide/how_to_use/api_basics` section to learn how to use EOmaps!

In addition, there is also the :doc:`user_guide/interactivity/api_companion_widget` GUI that can be used to interactively edit/compare/overlay maps and explore the features and functionalities.


Data Visualization
------------------

Want to visualize some data? Have a look at the :doc:`user_guide/how_to_use/api_data_visualization` section to learn how to create beautiful maps with your datasets!

EOmaps provides a variety of plot-shapes so you can select a shape that suits the structure, size and spatial representativeness of your data:

 .. include:: _shape_table.rst

Map Features
------------

EOmaps provides many useful tools to customize your maps.

.. grid:: 1 1 1 2
    :gutter: 1

    .. grid-item-card:: :doc:`user_guide/map_features/naturalearth_features`
        :link: user_guide/map_features/naturalearth_features
        :link-type: doc
        :shadow: none

        Add basic map features (coastlines, ocean-coloring etc. ) to the map.

    .. grid-item-card:: :doc:`user_guide/map_features/api_webmaps`
        :link: user_guide/map_features/api_webmaps
        :link-type: doc
        :shadow: none

        Add imagery provided by WebMap services to the map.

    .. grid-item-card:: :doc:`user_guide/map_features/inset_maps`
        :link: user_guide/map_features/inset_maps
        :link-type: doc
        :shadow: none

        Create zoomed-in views on specific regions of a map.

    .. grid-item-card:: :doc:`user_guide/map_features/api_vector_data`
        :link: user_guide/map_features/api_vector_data
        :link-type: doc
        :shadow: none

        Add vector geometries to the map.

    .. grid-item-card:: :doc:`user_guide/map_features/api_annotations_markers_etc`
        :link: user_guide/map_features/api_annotations_markers_etc
        :link-type: doc
        :shadow: none

        Add markers, annotations, lines, logos etc. to the map.

    .. grid-item-card:: :doc:`user_guide/map_features/api_scalebar`
        :link: user_guide/map_features/api_scalebar
        :link-type: doc
        :shadow: none

        Add a scalebar to the map.

    .. grid-item-card:: :doc:`user_guide/map_features/api_compass`
        :link: user_guide/map_features/api_compass
        :link-type: doc
        :shadow: none

        Add a compass (or North Arrow) to the map.

    .. grid-item-card:: :doc:`user_guide/map_features/api_gridlines`
        :link: user_guide/map_features/api_gridlines
        :link-type: doc
        :shadow: none

        Add grid-lines (and optionally grid-labels) to the map.


Interactivity
-------------

With a few lines of code, you can turn your maps into interactive data-analysis widgets!

.. grid:: 1 1 1 2
    :gutter: 1

    .. grid-item-card:: :doc:`user_guide/interactivity/api_companion_widget`
        :link: user_guide/interactivity/api_companion_widget
        :link-type: doc
        :shadow: none

        A graphical user-interface to interact with the map.

    .. grid-item-card:: :doc:`user_guide/interactivity/api_callbacks`
        :link: user_guide/interactivity/api_callbacks
        :link-type: doc
        :shadow: none

        Turn your maps into interactive data-analysis widgets.

    .. grid-item-card:: :doc:`user_guide/interactivity/api_layout_editor`
        :link: user_guide/interactivity/api_layout_editor
        :link-type: doc
        :shadow: none

        Interactively re-arrange and re-size axes of a figure.

    .. grid-item-card:: :doc:`user_guide/interactivity/api_draw`
        :link: user_guide/interactivity/api_draw
        :link-type: doc
        :shadow: none

        Interactively draw geometries on a map and export them as shapefiles.

    .. grid-item-card:: :doc:`user_guide/interactivity/api_utils`
        :link: user_guide/interactivity/api_utils
        :link-type: doc
        :shadow: none

        A collection of utility widgets (layer-sliders, layer-selectors)

    .. grid-item-card:: :doc:`user_guide/interactivity/widgets`
        :link: user_guide/interactivity/widgets
        :link-type: doc
        :shadow: none

        A collection of Jupyter Widgets (for Jupyter Notebooks)





Miscellaneous
~~~~~~~~~~~~~

.. grid:: 1 1 1 2
    :gutter: 1

    .. grid-item-card:: :doc:`user_guide/miscellaneous/api_logging`
        :link: user_guide/miscellaneous/api_logging
        :link-type: doc
        :shadow: none

        Details on logging.

    .. grid-item-card:: :doc:`user_guide/miscellaneous/api_command_line_interface`
        :link: user_guide/miscellaneous/api_command_line_interface
        :link-type: doc
        :shadow: none

        How to use the ``eomaps`` command-line interface.

    .. grid-item-card:: :doc:`user_guide/miscellaneous/api_read_data`
        :link: user_guide/miscellaneous/api_read_data
        :link-type: doc
        :shadow: none

        Read data from NetCDF, GeoTIFF or CSV files.

    .. grid-item-card:: :doc:`user_guide/miscellaneous/api_misc`
        :link: user_guide/miscellaneous/api_misc
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

Make sure to check out the :doc:`Examples <examples/EOmaps_examples>` for an overview of the capabilities (incl. source code)!

.. include:: examples/example_galery.rst



.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: General

    installation
    user_guide/index
    examples/EOmaps_examples
    api/reference
    contribute/contribute
    FAQ

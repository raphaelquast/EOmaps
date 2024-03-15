.. _command_line_interface:

⛭ Command Line Interface
=========================

EOmaps provides a basic command line interface to quickly create simple maps or to get a quick-look at a dataset without having to open an editor.

To start a new EOmaps map from the command-line, simply type ``eomaps`` and hit enter.

In addition, the following optional parameters can be provided:

- ``--help`` get additional help on how to use the ``eomaps`` command
- ``--crs`` set the coordinate reference system of the map
- ``--location`` query the location via the OpenStreetMap Nominatim service and set the map-extent
- ``--file`` a path to a file that should be opened for plotting
- ``--ne`` add NaturalEarth features to the map
- ``--wms`` add some selected WebMap services to the map

Make sure to checkout the :ref:`companion_widget` which provides a lot of features to customize the map once it's created!

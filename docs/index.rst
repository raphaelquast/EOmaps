.. image:: _static/logo.png
  :width: 40%
  :align: center
  :target: https://github.com/raphaelquast/EOmaps

|

Welcome to the documentation for **EOmaps**!

EOmaps is a Python package to visualize and analyze geographical datasets.
It is built on top of ``matplotlib`` and ``cartopy`` and aims to provide an
intuitive and easy-to-use interface to handle the following tasks:

| ▶ Speed up and simplify the creation and comparison of maps
| ▶ Visualize small datasets as well as millions of datapoints
| ▶ Handle 1D and 2D datasets and create plots from NetCDF, GeoTIFF or CSV files
| ▶ Take care of re-projecting the data
| ▶ Compare or overlay different plot-layers and WebMap services
| ▶ Use the maps as interactive data-analysis widgets (e.g. execute functions if you click on the map)
| ▶ Provide a versatile set of tools to customize the maps
| ▶ Arrange multiple maps in one figure
| ▶ Get a nice colorbar with a histogram on top
| ▶ Export high resolution images
|
| A detailed overview on how to use EOmaps is given in the :doc:`api`.
| Make sure to check out the :doc:`EOmaps_examples` for an overview of the capabilities (incl. source code)!

----------


Contents
--------

 .. toctree::
    :maxdepth: 1
    :caption: General

    general

.. toctree::
  :maxdepth: 2
  :glob:
  :includehidden:
  :caption: How to use EOmaps

  api


.. toctree::
   :maxdepth: 2

   EOmaps_examples



.. toctree::
   :maxdepth: 2
   :caption: Contribute

   contribute

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   reference

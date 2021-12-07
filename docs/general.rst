🌳 General
==========

.. _installation:


🐛 Installation
###############
(To speed up the process... have a look at `(mamba) <https://github.com/mamba-org/mamba>`_ )


🐜 Manual installation
----------------------

The recommended way to install EOmaps with `conda` and `pip`:

0. | (only if you're on WINDOWS)
   | due to an issue with libspatialindex.dll for the conda-forge build of rtree, install rtree from default channel
     `(check the corresponding issue on rtree-feedstock) <https://github.com/conda-forge/rtree-feedstock/issues/31>`_

    .. code-block:: console

       conda install "rtree>=0.9.7"

1. install required dependencies from `conda-forge` channel

    .. code-block:: console

       conda install -c conda-forge numpy scipy pandas geopandas "matplotlib>=3.0" "cartopy>=0.20.0" descartes mapclassify pyproj pyepsg


  1.1 For WebMap capabilities (e.g. WMS or WMTS services) you need some more:

      .. code-block:: console

         conda install -c conda-forge owslib requests xmltodict cairosvg

2. finally, install EOmaps from pip

    .. code-block:: console

       pip install eomaps


🐞 From .yml file
-----------------

Here's a yaml-file that you can use to install all you need in one go:

.. code-block:: yaml

    name: eomaps
    channels:
      - conda-forge
      - defaults

    dependencies:
      - python=3.7
      - rtree
      - numpy
      - scipy
      - pandas
      - geopandas
      - matplotlib>=3.0
      - cartopy>=0.20.0
      - descartes
      - mapclassify
      - pyproj
      - pyepsg
      # --------------for WebMaps
      - owslib
      - requests
      - xmltodict
      - cairosvg
      - pip
      - pip :
        - eomaps

To install a fresh environment use:

.. code-block:: console

    conda env create -f <link to the above yml-file>

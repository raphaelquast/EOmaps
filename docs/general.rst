🌳 General
==========

.. _installation:


🐛 Installation
###############

🦋 Recommended way (via ``conda``)
----------------------------------

EOmaps is available via the ``conda-forge`` channel and can be installed via:

  .. code-block:: console

    conda install -c conda-forge eomaps

This should make sure all required dependencies are correctly installed.

.. admonition:: Speed up the installation

  Since EOMaps dependencies can be demanding to solve for ``conda`` it is highly recommended to have a look at `mamba <https://github.com/mamba-org/mamba>`_
  (a C++ re-implementation of ``conda`` that provides a remarkable speedup)

  To install ``mamba``, simply use:

  .. code-block:: console

    conda install -c conda-forge mamba

  Once ``mamba`` is installed, you just need to replace the term ``conda`` with ``mamba`` and you're good to go!

  .. code-block:: console

    mamba install -c conda-forge eomaps


A quick tutorial on how to get started from scratch is available here: :ref:`quickstart_guide`


🐜 optional dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~
To use the full potential of EOmaps, some additional dependencies might be required

.. admonition:: Note on ``matplotlib`` backends

  By default EOmaps requires only a minimal version of ``matplotlib`` that does not include bindings for
  all available `matplotlib backends <https://matplotlib.org/stable/users/explain/backends.html?highlight=backend#backends>`_.

  - To install all backends, explicitly use: ``conda install -c conda-forge matplotlib``  (or ``mamba ...``)
  - For ``QtAgg``, just install the ``pyqt`` bindings via ``conda install -c conda-forge pyqt``


- `Pandas <https://pandas.pydata.org/>`_

  - The go-to library for data-analysis.
  - If installed, ``pandas.DataFrames`` can be used as datasets in EOmaps

    - Install via ``conda install -c conda-forge pandas`` (or ``mamba ...``)

- `GeoPandas <https://geopandas.org>`_

  - An awesome extension to ``pandas`` for working with geometric (``shapely``) objects.
  - Required for ``m.add_gdf()`` and extends the functionalities of ``m.add_feature()``

    - Install via ``conda install -c conda-forge geopandas`` (or ``mamba ...``)


- `Datashader <https://datashader.org>`_

  - Provides remarkable capabilities for very fast visualization of extremely large datasets (>1M datapoints)
  - Required for the plot-shapes: ``m.set_shape.shade_points()`` and ``m.set_shape.shade_raster()``

    - Install via ``conda install -c conda-forge datashader`` (or ``mamba ...``)


- `Xarray <https://xarray.pydata.org>`_ and `RioXarray <https://github.com/corteva/rioxarray>`_

  - Reading capabilities for NetCDF and GeoTIFF files
  - Required for the plot-shape: ``m.set_shape.shade_raster()`` and for ``m.read_file.GeoTIFF`` and ``m.read_file.NetCDF``

    - Install via ``conda install -c conda-forge xarray rioxarray`` (or ``mamba ...``)


- `Equi7Grid <https://github.com/TUW-GEO/Equi7Grid>`_

  - A library to work with data provided in Equi7Grid projections
  - Required for using the projection: ``Maps.CRS.Equi7Grid_projection()``

    - Install via ``pip install equi7grid``


🐞 Alternative way (via ``pip``)
-----------------------------------
EOmaps is also available via ``pip`` and can be installed using

  .. code-block:: console

    pip install eomaps


However, it is not guaranteed that all dependencies are correctly resolved and some manual
tweaking of the environment might be required to ensure that all packages work as expected.

A list of the dependencies can be found below:

.. code-block:: yaml

    dependencies:
      - python >=3.7
      - rtree
      - numpy
      - scipy
      - matplotlib >=3.0
      - cartopy >=0.20.0
      - descartes
      - mapclassify
      - pyproj
      - pyepsg
      # -------------- for WebMaps
      - owslib
      - requests
      - xmltodict
      - cairosvg
      # -------------- optional
      - pandas
      - geopandas
      - datashader
      - xarray
      - rioxarray
      # -------------- for building the docs
      - sphinx
      - sphinx-copybutton
      - sphinx_rtd_theme
      - mock
      # -------------- for Equi7Grid projections
      - pip
      - pip:
        - equi7grid

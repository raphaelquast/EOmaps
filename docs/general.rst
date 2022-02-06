🌳 General
==========

.. _installation:


🐛 Installation
###############

🐜 Recommended way (via ``conda``)
------------------------------
(To speed up the process... have a look at `mamba <https://github.com/mamba-org/mamba>`_ )

EOmaps is available via the ``conda-forge`` channel and can be installed via:

  .. code-block:: console

      conda install -c conda-forge eomaps


This should make sure all required dependencies are correctly installed.

.. admonition:: Note on using ``geopandas``

    | `Geopandas <https://geopandas.org/en/stable/index.html>`_ is an optional dependency (only required for ``m.add_overlay()`` and ``m.add_gdf()``).
    | To install geopandas, simply use: ``conda install -c conda-forge geopandas``


.. admonition:: Note on ``matplotlib`` backends

  By default EOmaps requires only a minimal version of ``matplotlib`` that does not include bindings for
  all available `matplotlib backends <https://matplotlib.org/stable/users/explain/backends.html?highlight=backend#backends>`_.

  - To install all backends, explicitly use: ``conda install -c conda-forge matplotlib``
  - For ``QtAgg``, just install the ``pyqt`` bindings via ``conda install -c conda-forge pyqt``



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
      # -------------- optional
      - pandas
      - geopandas
      # -------------- for WebMaps
      - owslib
      - requests
      - xmltodict
      - cairosvg
      # -------------- only for building the docs
      - sphinx
      - sphinx-copybutton
      - sphinx_rtd_theme
      - mock

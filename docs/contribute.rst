.. _contribute:


🚀 Contribution Guide
======================

👷 Get in touch
---------------

Hey! Nice to see that you're interested in contributing to `EOmaps <https://github.com/raphaelquast/EOmaps>`_!

If you need help to get started or got some questions, open a new `Issue on GitHub <https://github.com/raphaelquast/EOmaps/issues>`_
or post a message on `gitter <https://app.gitter.im/#/room/#EOmaps:gitter.im>`_ and I'll see what I can do!

Any contributions are welcome!


⚙ How to set up a development environment
-----------------------------------------

To get started you need a working ``python`` installation.
I recommend using `miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ to set up ``python`` with the following steps:

- download latest `miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ installer and install
- open `anaconda prompt <https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html#starting-conda>`_ (or normal terminal on ``linux``)
- | install `mamba <https://github.com/mamba-org/mamba>`_ with
  | ``conda install -c conda-forge mamba``
- | create a development environment from the ``eomaps.yml`` file with
  | ``mamba env create -f < path to eomaps.yml >``

Content of ``eomaps.yml``:

.. code-block:: console

    name: eomaps
    channels:
    - conda-forge

    dependencies:
    # --------------for eomaps
    - numpy
    - scipy
    - matplotlib>=3.0
    - cartopy>=0.20.0
    - descartes
    - mapclassify
    - pyproj
    - pyepsg
    # --------------for DataFrames
    - pandas
    # --------------for vector data
    - geopandas
    # --------------for data-shading
    - datashader
    # --------------for GeoTIFF and NetCDF files
    - netcdf4
    - xarray
    - rioxarray
    # --------------for WebMaps
    - owslib
    - requests
    - xmltodict
    - cairosvg
    # --------------for testing
    - coveralls
    - pytest
    - pytest-cov
    # ..............for version control
    - git
    # --------------for building the docs
    - sphinx-copybutton
    - sphinx
    - docutils
    - pip
    - pip:
        - sphinx_rtd_theme

Getting started
---------------

The source code of EOmaps is managed on GitHub.

To get started, create a new **fork** of the `EOmaps repository <https://github.com/raphaelquast/EOmaps>`_
to get your own copy of the source code.

Then, open a terminal, navigate to the folder you want to work in and clone the repository to get a local copy via:

.. code-block:: console

    git clone < url to fork of eomaps repository>

For development, first checkout the ``dev`` branch which contains all pending changes for the next release.
Then create a new feature or bug-fix branch via:

.. code-block:: console

    git checkout dev
    git checkout -b "awesome_new_feature"


Once you're done or want some feedback, open a `pull request <>`_ on GitHub!

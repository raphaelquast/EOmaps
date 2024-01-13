.. _installation:


🐛 Installation
================

.. contents:: Contents:
    :local:
    :depth: 1


Via ``conda`` and ``mamba``
---------------------------

EOmaps is available via the ``conda-forge`` channel and can be installed via:

  .. code-block:: console

    conda install -c conda-forge eomaps


This will install all required and optional dependencies.


.. admonition:: Greatly speed up the installation!

    Since the dependencies of EOmaps can be demanding to solve for ``conda``, it is **highly recommended**
    that you use `mamba <https://github.com/mamba-org/mamba>`_ to install EOmaps!

    ``mamba`` is a reimplementation of the conda package manager in C++, capable of solving environments a lot faster.

    The best way to get started is to use `miniforge <https://github.com/conda-forge/miniforge>`_.

    However, you can also install ``mamba`` into an existing ``conda`` environment with:

    .. code-block:: console

        conda install -c conda-forge mamba


    Once ``mamba`` is installed, you just need to replace the term ``conda`` with ``mamba`` and you're good to go!

    .. code-block:: console

        mamba install -c conda-forge eomaps


    Alternatively you can also configure ``conda`` to use the ``libmamba`` solver by default.
    (More info here: `A Faster Solver for Conda: Libmamba <https://www.anaconda.com/blog/a-faster-conda-for-a-growing-community>`_  )


A quick tutorial on how to **get started from scratch** is available here: :ref:`quickstart_guide`

More details on how to **configure your favorite IDE** to work with EOmaps can be found in the FAQ section
:ref:`configuring_the_editor`.



Via ``pip``
-----------

EOmaps is also available on ``pip``.

To install EOmaps with a **minimal set of dependencies**, use:

  .. code-block:: console

    pip install eomaps


Optional dependencies
~~~~~~~~~~~~~~~~~~~~~

Some features (:ref:`webmap_layers`, :ref:`companion_widget`, etc.) require additional dependencies.
To use them you have to install the required dependency-groups:

To get all features of EOmaps, you can use one of:

.. code-block:: console

    pip install eomaps[all]       # ALL optional dependencies
    pip install eomaps[all_nogui] # All optional dependencies (except ``Qt`` GUI framework)


In addition, you can use the following dependency-groups to activate only selected features:

.. code-block:: console

    pip install eomaps[wms]       # dependencies required for WebMap services
    pip install eomaps[gui]       # dependencies for ``Qt`` GUI framework and the CompanionWidget
    pip install eomaps[io]        # add support for ``pandas``, ``xarray``, ``geopandas`` and ``rioxarray``
    pip install eomaps[shade]     # add capabilities to visualize extremely large datasets (via ``datashader``)
    pip install eomaps[classify]  # add support for ``mapclassify`` to classify datasets


(It is also possible to combine dependency-groups, e.g.: ``pip install eomaps[wms, gui]``)

A list of all associated packages can be found in :ref:`setup_a_dev_env` or in the ``pyproject.toml`` file.

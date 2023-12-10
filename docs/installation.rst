.. _installation:


🐛 Installation
================

.. contents:: Contents:
    :local:
    :depth: 1

Recommended way (via ``conda`` and ``mamba``)
---------------------------------------------

EOmaps is available via the ``conda-forge`` channel and can be installed via:

  .. code-block:: console

    conda install -c conda-forge eomaps

This should make sure all required dependencies are correctly installed.

.. admonition:: Greatly speed up the installation!

  Since the dependencies of EOmaps can be demanding to solve for the classic ``conda`` solver, it is **highly recommended**
  that you use `mamba <https://github.com/mamba-org/mamba>`_ to install EOmaps!

  To install ``mamba``, simply use:

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

Alternative way (via ``pip``)
-----------------------------
EOmaps is also available on ``pip`` and can be installed via

  .. code-block:: console

    pip install eomaps


However, it is **not guaranteed that all dependencies are correctly resolved** and some manual
tweaking of the environment might be required to ensure that all packages work as expected.
Especially dependencies on C/C++ libraries such as ``geos`` or ``pyproj`` have to be configured
carefully to set up everying correctly. If you are not sure what you're doing, use ``conda + mamba``!

A list of all required dependencies can be found in :ref:`setup_a_dev_env`

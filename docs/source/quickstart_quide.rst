
.. _quickstart_guide:

🚲 From 0 to EOmaps - a quickstart guide
*****************************************

The following section is intended to provide a quick overview on how to get started using ``EOmaps``.

The guide is intended to be concise and covers only the most important information to get things running.
Links to websites that provide additional information are provided throughout the text.

.. note ::

    This tutorial is intended to get you up and running from scratch as fast as possible
    using 100% free and open-source tools. It does not cover alternative ways on how to setup python
    or how to use alternative editors etc.

    Feel free to start a `discussion <https://github.com/raphaelquast/EOmaps/discussions>`_ of open an
    `issue <https://github.com/raphaelquast/EOmaps/issues>`_ if you have additional questions or suggestions!


**Prerequisites:**

- A computer (Windows / MacOS / Linux)
  - no root access required
- basics on how to work with a terminal
- basic python knowledge


Getting started - set up a python environment
---------------------------------------------

There are of course many ways to set up a python environment... in the following, we will use the (free and open-source) ``conda``
package manager which greatly simplifies the creation of environments that depend on both python and c++ libraries
(A lot of python-packages for geo-libraries are just bindings to c++ libraries such as GDAL or PyProj).

``conda`` is available for MacOS, Windows and Linux.
For more details, see `conda-docs <https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html>`_ .

The fastest way to get started is to use ``miniconda``, a minimalistic installer that includes only
``conda``, ``python`` and a minimal set of additional packages.

.. admonition:: TODO (~10 min)

    Download and install the latest version of ``miniconda`` from:

    https://docs.conda.io/en/latest/miniconda.html


After the installation is finished, open a ``Anaconda Prompt`` terminal (if you need help, see `"starting conda" <https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html#starting-conda>`_ ).

By default, the terminal starts in the conda-environment ``base`` (you should see the name in brackets on the left).

Before creating a new dedicated python-environment, we'll first install ``mamba`` into the ``base`` environment
to speedup the installation process. (for details on mamba, have a look at the `mamba-docs <https://mamba.readthedocs.io/en/latest/index.html>`_ !)

- NOTE: The use of ``mamba`` is optional (but highly recommended)! If you don't want to use it, just replace the term ``mamba`` with ``conda`` in
  all subsequent commands.

.. admonition:: TODO (~1 min) install ``mamba``:

    Install ``mamba`` from the ``conda-forge`` channel with the following command (in the Anaconda Prompt terminal):

    .. code-block:: shell

        conda install -c conda-forge mamba

Now that ``mamba`` is installed, we can use it to create a new python environment, and install the following packages:

- As editor to write and execute python-code we will use the awesome (free and open-source) `spyder-IDE <https://www.spyder-ide.org/>`_
- in addition, we install ``eomaps`` and ``matplotlib`` (the latter is only required to make sure matplotlib backends such as `Qt5Agg` are installed)

  - all required dependencies will be automatically determined and installed during the process

.. admonition:: TODO (~15 min, ~500mb) setup environment:

    Setup a new python environment named ``eomaps`` and install
    ``EOmaps`` and the ``spyder`` IDE.

    .. code-block:: shell

        mamba create -n eomaps -c conda-forge spyder eomaps matplotlib

    Once the list of required packages is determined, confirm the installation with ``y`` and wait until
    it is completed.


Finally, all that's left to do is to activate the environment and start the editor!

.. admonition:: TODO (~1 min) activate environment, start and setup the spyder IDE:

    To activate the environment, use:

    .. code-block:: shell

        conda activate eomaps

    After activating the environment, we can start the ``spyder IDE`` with:

    .. code-block:: shell

        spyder


    As a last step, we need to adjust the default plot-settings of the ``spyder IDE`` to make sure that
    ``matplotlib`` plots are generated as interactive widgets

    - By default, plots are rendered as static images into the "plots-pane"... to avoid this and create
      interactive ``matplotlib`` widgets instead, go to the **preferences**, select the **IPython console** section
      and set the **Graphics backend** to **Automatic** :

    .. image:: _static/spyder_preferences.png


Now you're ready for your first map! -> head over to :ref:`EOmaps_examples` and run one of the example-codes!


.. admonition:: A few quick ``spyder IDE`` tips:

    In ``spyder`` you will work with an interactive ``IPython`` console.
    This allows you to dynamically execute parts of a script and immediately see the outcome.

    - use ``F9`` to execute the selected code (or the current line if nothing is selected)
    - use ``F5`` to execute the current script (e.g. the whole file)
    - use ``shift + enter`` to execute the currently selected code-block
      (code-blocks are separated by ``# %%``)

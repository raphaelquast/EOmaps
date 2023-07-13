.. _contribute:


🚀 Contribution Guide
======================

👷 Get in touch
---------------

Hey! Nice to see that you're interested in contributing to `EOmaps <https://github.com/raphaelquast/EOmaps>`_!

If you need help to get started or got some questions, open a new `Issue on GitHub <https://github.com/raphaelquast/EOmaps/issues>`_,
start a `Discussion on GitHub <https://github.com/raphaelquast/EOmaps/discussions/categories/contribution>`_ or post a message on `gitter <https://app.gitter.im/#/room/#EOmaps:gitter.im>`_ and I'll see what I can do!

Any contributions are welcome!

- New feature implementations (or ideas for new features)
- Enhancements for existing features
- Bug-fixes, code-style improvements, unittests etc.
- Documentation updates
- Outreach (e.g. blog-posts, tutorials, talks ... )
- ...


.. _setup_a_dev_env:

⚙ How to set up a development environment
-----------------------------------------

To get started you need a working ``python`` installation.
I recommend using `miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ to set up ``python`` with the following steps:

- Download the latest `miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ installer and install
- Open `anaconda prompt <https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html#starting-conda>`_ (or normal terminal on ``linux``)
- | Install `mamba <https://github.com/mamba-org/mamba>`_ with
  | ``conda install -c conda-forge mamba``
- | Create a development environment from the ``eomaps.yml`` file with
  | ``mamba env create -f < path to eomaps.yml >``

Content of ``eomaps.yml``:

.. literalinclude:: ../tests/test_env.yml

As editor, I recommend using the awesome, free and open-source `Spyder IDE <https://github.com/spyder-ide/spyder>`_.
You can install it directly into your environment via:

.. code-block:: console

    mamba install -c conda-forge spyder



Getting started
---------------

The source code of EOmaps is managed on `GitHub <https://github.com/raphaelquast/EOmaps>`_.

.. note::

  To contribute to the repository, you'll need a working installation of `git <https://git-scm.com/>`_ and `pre-commit <https://pre-commit.com/>`_.

  - To install ``git``, either get the latest installer from `here <https://git-scm.com/>`_ or install only for your current environment via ``mamba install -c conda-forge git``.
  - To install ``pre-commit``, use ``mamba install -c conda-forge pre-commit`` (see :ref:`below <pre_commit>`).


To get started, create a new **fork** of the `EOmaps repository <https://github.com/raphaelquast/EOmaps/fork>`_
to get your own copy of the source code.

Then, open a terminal, navigate to the folder you want to work in and clone the forked repository via:

.. code-block:: console

    git clone < url to fork of EOmaps repository >

For development, make sure that you first checkout the ``dev`` branch which contains all pending changes for the next release.
Then, create a new feature or bug-fix branch and start coding!

.. code-block:: console

    git checkout dev
    git checkout -b "awesome_new_feature"


Once you're done or in case you want/need some feedback, open a `pull request <https://github.com/raphaelquast/EOmaps/pulls>`_ on GitHub!

.. _pre_commit:

Pre-commit hooks
----------------

To ensure uniform code formatting, EOmaps uses `pre-commit hooks <https://pre-commit.com/>`_ to automatically check (and fix) code-style issues such as:

- Trailing spaces in `.py` files
- Compliance to the used `black <https://github.com/psf/black>`_ code formatting standards

To install ``pre-commit`` in your current environment, use ``mamba install -c conda-forge pre-commit``.

To initialize pre-commit hooks in your current environment, navigate to the directory where you cloned the EOmaps repository and run the following command:
(e.g. the parent directory containing the file `.pre-commit-config.yaml`)


.. code-block:: console

  pre-commit install

This will install the required pre-commit hooks in your current environment so that they are run **automatically prior to each commit**.
(The first time pre-commit is run, the necessary packages will have to be installed which might take a short moment)


.. note::

  This means that all files will be auto-formatted prior to each commit to comply with the used code-formatting standards and
  only commits that comply with all pre-commit hooks can be pushed to GitHub.


To run the pre-commit hooks manually on selected files, simply **add the files you want to commit** with ``git add < filename >`` and then run ``pre-commit``.
(If you want to run the hooks on all files, use ``pre-commit run --all-files``)

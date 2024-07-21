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


Getting started
---------------

The source code of EOmaps is managed on `GitHub <https://github.com/raphaelquast/EOmaps>`_.

To get started, create a new `fork <https://docs.github.com/en/get-started/quickstart/fork-a-repo>`_ of the `EOmaps repository <https://github.com/raphaelquast/EOmaps/fork>`_
to get your own copy of the source code.

Then, open a terminal, navigate to the folder you want to work in and clone the forked repository via:

.. code-block:: console

    git clone < link to your fork of the EOmaps repository >

For development, make sure that you first checkout the ``dev`` branch which contains all pending changes for the next release.
Then, create a new feature or bug-fix branch and start coding!

.. code-block:: console

    git checkout dev
    git checkout -b "awesome_new_feature"


Once you're done or in case you want/need some feedback, open a `pull request <https://github.com/raphaelquast/EOmaps/pulls>`_ on GitHub!

.. _pre_commit:



.. _setup_a_dev_env:

How to set up a development environment
---------------------------------------

To contribute to ``EOmaps``, you need a working ``python`` installation.

I recommend using `miniforge <https://github.com/conda-forge/miniforge>`__, a minimalistic installer that contains the package-managers `conda <https://docs.conda.io/en/latest/>`_ and `mamba <https://github.com/mamba-org/mamba>`_ already pre-configured to use the `conda-forge <https://anaconda.org/conda-forge>`_ channel by default.


You can set up ``python`` with the following steps:

- Download the latest `miniforge <https://github.com/conda-forge/miniforge#download>`__ installer and install
- On Windows, miniforge is not added to the system path by default. To use `conda/mamba`, open `Miniforge Prompt <https://github.com/conda-forge/miniforge#usage>`__! For `Linux` and `OS X` you should be able to use the normal command prompt.
- | Create a new development environment from the ``eomaps/environment.yml`` file with
  | ``mamba env create -f < path to environment.yml >``

Content of ``environment.yml``:

.. literalinclude:: ../../../environment.yml



.. tip::

    As editor, I recommend using the awesome, free and open-source `Spyder IDE <https://github.com/spyder-ide/spyder>`_.
    You can install it directly into your environment via:

    .. code-block:: console

        mamba install -c conda-forge spyder



Development Practices
---------------------

This section provides a guide to how we conduct development in the EOmaps repository. Please follow the practices outlined here when contributing directly to this repository.

Testing
~~~~~~~

After making changes, please test changes locally before creating a pull request. The following tests will be executed after any commit or pull request, so we ask that you perform the following sequence locally to track down any new issues from your changes.

The `environment.yml` file already contains the packages required to run the tests locally, e.g.:

- `pytest <https://docs.pytest.org>`__ to run the tests
- `pytest-cov <https://github.com/pytest-dev/pytest-cov>`__ and `coveralls <https://github.com/TheKevJames/coveralls-python>`__ to track lines covered by the tests
- `pytest-mpl <https://pytest-mpl.readthedocs.io/en/stable/>`__ to perform image comparisons

To run the primary test suite and generate coverage report, navigate to the parent `eomaps` directory and run:

.. code-block:: console

    python -m pytest -v --cov eomaps --mpl

Some of the tests compare exported images with a set of baseline-images to ensure stable image exports and to catch
potential issues that are not detected by the code based tests.

If changes require an update of the baseline images, you have to invoke
`pytest-mpl <https://pytest-mpl.readthedocs.io/en/stable/>`__ with the `mpl-generate-path` option:

.. code-block:: console

    python -m pytest -v --cov eomaps --mpl --mpl-generate-path=tests/baseline

This will update all images in the `tests/baseline` folder.

.. note::

    During the tests, a lot of figures will be created and destroyed!

    Before updating new baseline images, make sure to manually check that they look exactly as expected!


.. tip::

   You can run only a subset of the tests by using the ``-k`` flag! (This will select only tests whose names contain the provided keyword)

   .. code-block:: console

      python -m pytest -k <QUERY KEYWORD>

   (see `pytest command-line-flags <https://docs.pytest.org/en/7.3.x/reference/reference.html#command-line-flags>`_ for more details)


.. tip::

    Unit testing can take some time, if you wish to speed it up, you can install `pytest-xdist <https://github.com/pytest-dev/pytest-xdist>`_ to leverage multiple processes with the ``-n`` flag.

    .. code-block:: console

        python -m pytest -n <NUMBER OF CORES>

Style Checking
~~~~~~~~~~~~~~

To ensure uniform code style, EOmaps uses `pre-commit hooks <https://pre-commit.com/>`_ to automatically check (and fix) code-style issues such as:

- Removal of trailing whitespaces in `.py` files
- Making sure that files end with a newline
- Compliance to the used `black <https://github.com/psf/black>`_ code formatting standards


To initialize pre-commit hooks in your current environment, first install `pre-commit hooks <https://pre-commit.com/>`_ with

.. code-block:: console

  mamba install -c conda-forge pre-commit


Then navigate to the directory where you cloned the EOmaps repository and run the following command: (e.g. the  directory that contains the ``.pre-commit-config.yaml`` file)


.. code-block:: console

  pre-commit install

This will install the required pre-commit hooks in your current environment so that they are run **automatically prior to each commit**.
(The first time pre-commit is run, the necessary packages will have to be installed which might take a short moment)


.. code-block:: console

    git commit -m "added my cool feature"

    check python ast.........................................................Passed
    check for merge conflicts................................................Passed
    fix end of files.........................................................Passed
    trim trailing whitespace.................................................Passed
    mixed line ending........................................................Passed
    black....................................................................Passed


.. note::

  This means that all files will be **auto-formatted** prior to each commit to comply with the used code-formatting standards and only commits that comply with all pre-commit hooks can be pushed to GitHub.


  ⚠ After running the pre-commit hooks, some files might have new changes that must be staged for commit again!


.. tip::

    - To run the pre-commit hooks manually on selected files, simply **add the files you want to commit** with ``git add < filename >`` and then run ``pre-commit``
    - If you want to run the hooks on all files, use ``pre-commit run --all-files``

.. tip::

  If you have issues related to ``setuptools`` when installing ``pre-commit``, see
  `pre-commit Issue #2178 comment <https://github.com/pre-commit/pre-commit/issues/2178#issuecomment-1002163763>`_
  for a potential resolution.





Building the Documentation
--------------------------

The documentation of EOmaps is written with `Sphinx <https://www.sphinx-doc.org/en/master/>`_ using the markup language `ReStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_.


To build the documentation locally, simply navigate to the folder ``eomaps/docs`` and then run

.. code-block::

    make html


The first time the documentation is built, all auto-generated files parsed from the python-code have to be generated which might take a bit of time. Subsequent calls will be much faster since they only update files that contain changes!

- Once finished, you will find a new folder in the EOmaps directory (``eomaps/docs/build/html``) that contains all the source files for the documentation.
- Open ``eomaps/docs/build/html/index.html`` to get to the starting-page!


.. admonition:: Automating the build process

    Manually re-building the documentation can be tedious... fortunately it is possible to **automatically re-build
    the documentation** if a file changed and **live-reload** the local docs in the browser with the awesome `sphinx-autobuild <https://github.com/executablebooks/sphinx-autobuild>`_ package.


    To install, run ``mamba install -c conda-forge sphinx-autobuild``.

    After installation, navigate to the ``eomaps`` directory and  start the automatic build-process with

    .. code-block::

        sphinx-autobuild docs docs/build/html --ignore ["generated/*"] --open-browser


    This will trigger a first build of the documentation and start a http server that hosts the local
    documentation (and live reloads it as soon as the build process finished)

    The url of the http-server will be printed to the console (the default is: ``127.0.0.1:8000``).


.. tip::

    As editor for the docs I recommend the nice minimalistic free and open-source editor `retext <https://github.com/retext-project/retext>`_.

    It provides syntax-highlighting and live-preview for both Markdown and ReStructuredText.

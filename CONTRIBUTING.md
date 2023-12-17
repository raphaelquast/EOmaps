# Contributing to EOmaps

Interested in contributing to EOmaps? Awesome! Any contributions are welcome!

## Found an issue or got an idea for a interesting feature?

Head over to the [GitHub issues](https://github.com/raphaelquast/EOmaps/issues) page and file a new bug-report or a feature request!
We greatly appreciate any ideas how we can improve the code and documentation.

## Contributing to the Codebase

EOmaps aims to be a feature-rich, performant and user-friendly tool for geographic data visualization and analysis. We highly welcome pull-requests for bug-fixes, improvements or entirely new features to improve the package!

A detailed introduction on how to setup a development environment to contribute code to EOmaps is provided in the [Contribution Guide](https://eomaps.readthedocs.io/en/latest/contribute.html) of the documentation.

If you got some questions or need help to get started, don't hesitate to get in touch by opening a new [issue](https://github.com/raphaelquast/EOmaps/issues), or [discussion](https://github.com/raphaelquast/EOmaps/discussions) on GitHub!

## General infos

- All of the `EOmaps` codebase is hosted on [GitHub](https://github.com/)

- [Black](https://github.com/psf/black) is used to ensure a consistent code format throughout the project

  - [pre-commit hooks](https://pre-commit.com/) are used to ensure that new code confirms to the code-style

- Automatic testing is performed via [pytest](https://docs.pytest.org/), [codecov](https://about.codecov.io/) and [GitHub Actions](https://github.com/features/actions)

- The documentation is generated with [sphinx](https://www.sphinx-doc.org/en/master/) and hosted on [ReadTheDocs](https://docs.readthedocs.io)

- Releases are hosted on [pypi](https://pypi.org/project/EOmaps/) and [conda-forge](https://anaconda.org/conda-forge/eomaps)

## Development Practices

This section provides a guide to how we conduct development in the EOmaps repository. Please follow the practices outlined here when contributing directly to this repository.

### Testing

After making changes, please test changes locally before creating a pull request. The following tests will be executed after any commit or pull request, so we ask that you perform the following sequence locally to track down any new issues from your changes.

To run our comprehensive suite of unit tests, install all the dependencies listed in `tests/test_env.yml`:

```bash
# Install dependencies (to be filled in)
```

Then, if you have everything installed, you can run the various test suites.

#### Unit Testing

Run the primary test suite and generate coverage report:

.. code:: bash

   python -m pytest -v --cov eomaps

Unit testing can take some time, if you wish to speed it up, set the
number of processors with the ``-n`` flag. This uses ``pytest-xdist`` to
leverage multiple processes. Example usage:

.. code:: bash

   python -m pytest -n <NUMCORE> --cov eomaps

#### Style Checking

To ensure your code meets minimum code styling standards, run::

  pip install pre-commit
  pre-commit run --all-files

If you have issues related to ``setuptools`` when installing ``pre-commit``, see
`pre-commit Issue #2178 comment <https://github.com/pre-commit/pre-commit/issues/2178#issuecomment-1002163763>`_
for a potential resolution.

You can also install this as a pre-commit hook by running::

  pre-commit install

This way, it's not possible for you to push code that fails the style
checks. For example, each commit automatically checks that you meet the style
requirements::

  $ pre-commit install
  $ git commit -m "added my cool feature"
  check python ast.........................................................Passed
  check for merge conflicts................................................Passed
  fix end of files.........................................................Passed
  trim trailing whitespace.................................................Passed
  mixed line ending........................................................Passed
  black....................................................................Passed

The actual installation of the environment happens before the first commit
following ``pre-commit install``. This will take a bit longer, but subsequent
commits will only trigger the actual style checks.

### Building the Documentation

Build the documentation on Linux or Mac OS with:

.. code:: bash

   make -C doc html

Build the documentation on Windows with:

.. code:: winbatch

   cd doc
   python -msphinx -M html source build
   python -msphinx -M html . build

The generated documentation can be found in the ``doc/build/html``
directory.

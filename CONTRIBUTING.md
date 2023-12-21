# Contributing to EOmaps

Interested in contributing to EOmaps? Awesome! Any contributions are welcome!

## Found an issue or got an idea for a interesting feature?

Head over to the [GitHub issues](https://github.com/raphaelquast/EOmaps/issues) page and file a new bug-report or a feature request!
We greatly appreciate any ideas how we can improve the code and documentation.

## Contributing to the Codebase

EOmaps aims to be a feature-rich, performant and user-friendly tool for geographic data visualization and analysis. We highly welcome pull-requests for bug-fixes, improvements or entirely new features to improve the package!

If you got some questions or need help to get started, don't hesitate to get in touch by opening a new [issue](https://github.com/raphaelquast/EOmaps/issues), or [discussion](https://github.com/raphaelquast/EOmaps/discussions) on GitHub!

## General infos

- All of the `EOmaps` codebase is hosted on [GitHub](https://github.com/)

- [Black](https://github.com/psf/black) is used to ensure a consistent code format throughout the project

  - [pre-commit hooks](https://pre-commit.com/) are used to ensure that new code confirms to the code-style

- Automatic testing is performed via [pytest](https://docs.pytest.org/), [codecov](https://about.codecov.io/) and [GitHub Actions](https://github.com/features/actions)

- The documentation is generated with [sphinx](https://www.sphinx-doc.org/en/master/) and hosted on [ReadTheDocs](https://docs.readthedocs.io)

- Releases are hosted on [pypi](https://pypi.org/project/EOmaps/) and [conda-forge](https://anaconda.org/conda-forge/eomaps)

## Development Practices

This section provides a **quick overview** how we conduct development in the EOmaps repository.

**More detailed instructions** on how to setup a development environment and contribute code to EOmaps are provided in the [Contribution Guide](https://eomaps.readthedocs.io/en/latest/contribute.html) of the documentation!


### Testing

After making changes, please test changes locally before creating a pull request. The following tests will be executed after any commit or pull request, so we ask that you perform the following sequence locally to track down any new issues from your changes.

Run the primary test suite and generate coverage report:

```bash
python -m pytest -v --cov eomaps
```

Unit testing can take some time, if you wish to speed it up, set the
number of processors with the ``-n`` flag. This uses [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) to leverage multiple processes. Example usage:

```bash
python -m pytest -n <NUMCORE> --cov eomaps
```

> NOTE: During the tests, a lot of figures will be created and destroyed!

### Style Checking

To ensure your code meets minimum code styling standards, run:

```bash
pip install pre-commit
pre-commit run --all-files
```

You can also install this as a pre-commit hook by running::

```bash
pre-commit install
```

This way, pre-commits will run automatically before each commit to ensure that you do not push code that fails the style checks.

## Building the Documentation

Build the documentation, navigate to the `eomaps/docs` directory (containing the `make.bat`) file and then run:

```bash
make html
```

The generated documentation can be found in the ``doc/build/html``
directory.

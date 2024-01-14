"""Test running all python-files in docs/examples that start with 'example_' """
from pathlib import Path
import matplotlib.pyplot as plt
import unittest


def gen_test(name, code):
    def test(*args, **kwargs):
        try:
            exec(code)
        except Exception as ex:
            raise AssertionError(f"Example '{name}' failed.") from ex
        finally:
            plt.close("all")

    return test


class _TestSequenceMeta(type):
    def __new__(mcs, name, bases, tests):
        # the path to the folder containing the example scripts
        parent_path = Path(__file__).parent.parent / "docs" / "examples"

        examples = filter(
            lambda x: x.stem.startswith("example_") and x.suffix == ".py",
            parent_path.iterdir(),
        )

        # generate unique tests for each example
        for f in examples:
            test_name = f"test_{f.stem}"
            tests[test_name] = gen_test(name, f.read_text())

        return type.__new__(mcs, name, bases, tests)


class TestExamples(unittest.TestCase, metaclass=_TestSequenceMeta):
    pass

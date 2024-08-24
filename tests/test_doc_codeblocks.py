from pathlib import Path
from docutils.core import publish_doctree
from docutils.utils import Reporter
import matplotlib.pyplot as plt
import unittest
import os


def gen_test(i, name, code):
    def test(*args, **kwargs):
        try:
            exec(code)
        except Exception as ex:
            raise AssertionError(
                f"Documentation code-block {i}: '{name}' failed."
            ) from ex
        finally:
            plt.close("all")

    return test


def is_test_code_block(node):
    return (
        node.tagname == "literal_block"
        and "code" in node.attributes["classes"]
        and len(node.attributes["ids"]) > 0
        and node.attributes["ids"][0].startswith("test")
    )


def is_any_code_block(node):
    return node.tagname == "literal_block" and "code" in node.attributes["classes"]


def _parse_codeblocks_as_test(p, tests, condition=is_test_code_block):
    with open(p, "r", encoding="utf8") as file:
        data = file.read()

    # initialize a "Publisher" to parse the file
    doctree = publish_doctree(
        data, settings_overrides={"report_level": Reporter.SEVERE_LEVEL}
    )

    # get a list of all code-blocks in the file
    code_blocks = list(doctree.findall(condition=condition))

    # generate unique tests for each code snippet
    for i, node in enumerate(code_blocks):
        source_code = node.astext()
        names = node.attributes.get("names")
        if len(names) > 0:
            name = names[0]
        else:
            name = p.name

        test_name = f"test_{p.stem}_{i}"
        tests[test_name] = gen_test(i, name, source_code)


# the path to the re-structured text file that should be analyzed
docs_path = Path(__file__).parent.parent / "docs" / "source"
examples_path = Path(__file__).parent.parent / "examples"


class _TestDocsSequenceMeta(type):
    """
    Metaclass to create tests from each code-block in the documentation
    whose ID starts with "test_".
    """

    def __new__(mcs, name, bases, tests):
        # remember current working directory
        cwd = os.getcwd()

        # set cwd to doc parent path to avoid issues with 'include' statements
        for p in docs_path.rglob("*.rst"):
            os.chdir(p.parent)
            _parse_codeblocks_as_test(p, tests, condition=is_test_code_block)

        os.chdir(cwd)

        return type.__new__(mcs, name, bases, tests)


class _TestExamplesSequenceMeta(type):
    """
    Metaclass to create tests from each code-block found in the examples directory.
    """

    def __new__(mcs, name, bases, tests):
        # remember current working directory
        cwd = os.getcwd()

        # set cwd to doc user_guide path to avoid issues with 'include' statements
        os.chdir(docs_path / "user_guide")

        for p in examples_path.rglob("*.rst"):
            _parse_codeblocks_as_test(p, tests, condition=is_any_code_block)

        os.chdir(cwd)

        return type.__new__(mcs, name, bases, tests)


class TestDocumentationCodeblocks(unittest.TestCase, metaclass=_TestDocsSequenceMeta):
    pass


class TestExamplesCodeblocks(unittest.TestCase, metaclass=_TestExamplesSequenceMeta):
    pass

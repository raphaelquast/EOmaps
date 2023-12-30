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


def is_code_block(node):
    return (
        node.tagname == "literal_block"
        and "code" in node.attributes["classes"]
        and len(node.attributes["ids"]) > 0
        and node.attributes["ids"][0].startswith("test")
    )


class _TestSequenceMeta(type):
    def __new__(mcs, name, bases, tests):
        # the path to the re-structured text file that should be analyzed
        parent_path = Path(__file__).parent.parent / "docs"
        # set cwd to doc parent path to avoid issues with 'include' statements
        cwd = os.getcwd()
        os.chdir(parent_path)

        for p in filter(lambda x: x.suffix == ".rst", parent_path.iterdir()):
            with open(p, "r", encoding="utf8") as file:
                data = file.read()

            # initialize a "Publisher" to parse the file
            doctree = publish_doctree(
                data, settings_overrides={"report_level": Reporter.SEVERE_LEVEL}
            )

            # get a list of all code-blocks in the file
            # replace .traverse with .findall once docutils > 18.1 is used!
            if hasattr(doctree, "findall"):
                code_blocks = list(doctree.findall(condition=is_code_block))
            else:
                code_blocks = list(doctree.traverse(condition=is_code_block))

            # generate unique tests for each code snippet
            for i, node in enumerate(code_blocks):
                source_code = node.astext()
                name = node.attributes["names"][0]

                test_name = f"test_{p.stem}_{i}"
                tests[test_name] = gen_test(i, name, source_code)

        os.chdir(cwd)

        return type.__new__(mcs, name, bases, tests)


class TestDocumentationCodeblocks(unittest.TestCase, metaclass=_TestSequenceMeta):
    pass

"""
Test all Jupyter Notebook code-cells from the docs.

NOTE:
All code cells of a notebook are concatenated as if they have been written as a
single pyhton-script that is executed in one go!

This is done to avoid issues with cells that are not "standalone"
(e.g. that require previous cells to be executed)

> Cells with a cell-tag: "ignore_in_unittest"  will be ignored!

"""

from pathlib import Path

import pytest
import nbformat
import matplotlib.pyplot as plt

plt.ion()  # use interactive mode to avoid blocking images

basepath = Path(__file__).parent.parent / "docs"
note_files = list(basepath.rglob("*.ipynb"))


class TestDocNotebooks:
    def _use_cell(self, cell):
        # select cells that should be used for testing
        # - cell must be a code-cell
        # - cell tags must not contain a tag called "ignore_in_unittest"

        checks = (
            cell.get("cell_type", "") == "code",
            "ignore_in_unittest" not in cell.get("metadata", {}).get("tags", []),
        )

        return all(checks)

    @pytest.mark.parametrize(
        "notebook",
        note_files,
        ids=lambda x: x.stem,
    )
    def test_doc_notebook(self, notebook):
        with open(notebook, encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
            # parse all code-cells from notebook
            code_cells = [i["source"] for i in nb["cells"] if self._use_cell(i)]
            # make sure plt.ion() is called before each test!
            code = "import matplotlib.pyplot as plt\n" "plt.ion()\n" "\n"

            for c in code_cells:
                for l in c.split("\n"):
                    # exclude lines that use magic commands (e.g. starting with %)
                    if not l.startswith("%"):
                        code += f"{l}\n"

            # run code (use a shared dict for locals and globals to avoid issues
            # with undefined variables)
            d = dict()
            exec(code, d, d)

        plt.close("all")

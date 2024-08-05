import re
import shutil
import warnings
from pathlib import Path

import nbformat
from docutils.core import publish_doctree
from docutils.nodes import title

toc_gallery = """
.. toctree::
    :hidden:
    :maxdepth: 1
"""


grid = """
.. grid:: 2 3 3 4
"""

grid_item_card = r"""
    .. grid-item-card:: :ref:`{ref_name}`
        :img-top: {img_path}
        :link: {ref_name}
        :link-type: ref
"""


def get_rst_title(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    doctree = publish_doctree(content)

    title_node = doctree.next_node(title)

    if title_node:
        return title_node.astext()
    else:
        return None


def find_notebook_images(notebook_path):
    with open(notebook_path, "r", encoding="utf-8") as f:
        notebook = nbformat.read(f, as_version=4)
    images = []
    for cell in notebook.cells:
        if cell.cell_type == "markdown":
            markdown_images = re.findall(r"!\[.*?\]\((.*?)\)", cell.source)
            images.extend(markdown_images)
    return images


def to_section_title(title):
    header_line = "-" * len(title)
    sec_title = f"\n\n{title}\n{header_line}\n"
    return sec_title


def add_notebook_ref(notebook_in: Path, notebook_out: Path):
    with open(notebook_in, "r", encoding="utf-8") as f:
        notebook = nbformat.read(f, as_version=4)

    cell_ref = f"({notebook_in.stem})="
    new_cell = nbformat.v4.new_markdown_cell(cell_ref)
    notebook.cells.insert(0, new_cell)

    if notebook_out.parent.exists() is False:
        notebook_out.parent.mkdir(parents=True)
    with open(notebook_out, "w", encoding="utf-8") as f:
        nbformat.write(notebook, f)


def gen_sub_gallery(
    gallery_header_file: Path,
    examples_dir: Path,
    gallery_dir: Path,
):
    """Generate the gallery for a subfolder.

    Parameters
    ----------
    gallery_header_file : Path
        The path to the gallery header file.
    examples_dir: Path,
        The path to the examples directory.
    gallery_dir : Path
        The path to the output gallery directory.
    """
    notebook_files = list(gallery_header_file.parent.glob("*.ipynb"))

    toc_gallery_str = ""
    grid_item_card_str = ""
    for notebook_file in notebook_files:
        notebook_name = notebook_file.stem
        sub_notebook_file = notebook_file.relative_to(examples_dir)
        notebook_output = gallery_dir / sub_notebook_file

        add_notebook_ref(notebook_file, notebook_output)

        ref_name = f"{notebook_name}"
        # Find the first image in the notebook
        images = find_notebook_images(notebook_file)
        if len(images) == 0:
            warnings.warn(f"No images found in {notebook_file}")
        img_path = images[0]

        grid_item_card_str += grid_item_card.format(
            ref_name=ref_name, img_path=img_path
        )

        toc_gallery_str += f"\n    {ref_name}"

    toc_gallery_str = toc_gallery + toc_gallery_str
    grid_str = grid + grid_item_card_str
    return toc_gallery_str, grid_str


def append_str_to_rst(
    header_in: Path,
    header_out: Path,
    append_str: str,
):
    """Append the gallery string to the gallery header file.

    Parameters
    ----------
    header_in : Path
        The path to the gallery header file.
    header_out : Path
        The path to the output gallery header file.
    append_str : str
        The string to append to the gallery header file.
    """
    if not header_out.exists():
        header_out.parent.mkdir(parents=True, exist_ok=True)
        with open(header_out, "w", encoding="utf-8") as dst:
            with open(header_in, "r", encoding="utf-8") as src:
                content = src.read() + append_str
            dst.write(content)
    else:
        with open(header_out, "a", encoding="utf-8") as f:
            f.write(append_str)


def main(examples_dir, gallery_dir):
    examples_dir = Path(examples_dir)
    gallery_dir = Path(gallery_dir)
    shutil.rmtree(gallery_dir, ignore_errors=True)

    home_header_file = examples_dir / "GALLERY_HEADER.rst"
    if home_header_file.exists() is False:
        raise FileNotFoundError(f"{home_header_file} not found.")
    home_header_out_file = gallery_dir / "GALLERY_HEADER.rst"

    gallery_header_files = list(examples_dir.rglob("GALLERY_HEADER.rst"))

    toc_index_str = ""
    for sub_header_file in gallery_header_files:
        if sub_header_file.samefile(home_header_file):
            continue

        # add sub-gallery to the home gallery toc
        sub_path_rst = sub_header_file.relative_to(examples_dir)
        toc_index_str += f"\n    {sub_path_rst.with_suffix('').as_posix()}"

        # generate the sub-gallery
        toc_sub_str, grid_str = gen_sub_gallery(
            sub_header_file, examples_dir, gallery_dir
        )
        # write the sub-gallery to the sub-gallery header file
        sub_header_out_file = gallery_dir / sub_path_rst
        append_str_to_rst(sub_header_file, sub_header_out_file, grid_str)
        append_str_to_rst(sub_header_file, sub_header_out_file, toc_sub_str)

        # add the sub-gallery to the home gallery
        section_title = to_section_title(get_rst_title(sub_header_file))
        append_str_to_rst(home_header_file, home_header_out_file, section_title)
        append_str_to_rst(home_header_file, home_header_out_file, grid_str)

    # add toc index to home gallery
    toc_index_str = toc_gallery + toc_index_str
    append_str_to_rst(home_header_file, home_header_out_file, toc_index_str)

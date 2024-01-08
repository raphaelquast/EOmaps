# Configuration file for the Sphinx documentation builder.
import sys, os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))
sys.path.insert(0, os.path.abspath(".."))

from eomaps import Maps


def make_feature_toctree_file():
    preset = (f for f in dir(Maps.add_feature.preset) if not f.startswith("_"))
    physical = (f for f in dir(Maps.add_feature.physical) if not f.startswith("_"))
    cultural = (f for f in dir(Maps.add_feature.cultural) if not f.startswith("_"))
    shapes = (f for f in dir(Maps.set_shape) if not f.startswith("_"))
    draw = (f for f in dir(Maps.draw) if not f.startswith("_"))
    wms = (f for f in dir(Maps.add_wms) if not f.startswith("_"))
    files = (f for f in dir(Maps.from_file) if not f.startswith("_"))
    read_files = (f for f in dir(Maps.read_file) if not f.startswith("_"))

    s = (
        ":orphan:\n"
        ".. currentmodule:: eomaps.eomaps\n"
        ".. autosummary::\n"
        "    :toctree: generated\n"
        "    :nosignatures:\n"
        "    :template: obj_with_attributes_no_toc.rst\n\n"
        "    Maps.add_wms\n"
        "    Maps.set_shape\n"
        "    Maps.config\n"
        "    Maps.draw\n"
        "    Maps.add_feature\n"
        "    Maps.add_feature.preset\n"
        "    Maps.add_feature.physical\n"
        "    Maps.add_feature.cultural\n"
        + "\n".join(
            [
                "\n".join([f"    Maps.add_feature.preset.{f}" for f in preset]),
                "\n".join([f"    Maps.add_feature.physical.{f}" for f in physical]),
                "\n".join(
                    [f"    Maps.add_feature.physical.{f}.get_gdf" for f in physical]
                ),
                "\n".join([f"    Maps.add_feature.cultural.{f}" for f in cultural]),
                "\n".join(
                    [f"    Maps.add_feature.cultural.{f}.get_gdf" for f in cultural]
                ),
                "\n".join([f"    Maps.set_shape.{f}" for f in shapes]),
                "\n".join([f"    Maps.draw.{f}" for f in draw]),
                "\n".join([f"    Maps.add_wms.{f}" for f in wms]),
                "\n".join([f"    Maps.from_file.{f}" for f in files]),
                "\n".join([f"    Maps.read_file.{f}" for f in read_files]),
            ]
        )
    )

    with open("autodoc_additional_props.rst", "w") as file:
        file.write(s)


make_feature_toctree_file()


def setup(app):
    app.add_css_file("custom_css.css")

    # need to assign the names here, otherwise autodoc won't document these classes,
    # and will instead just say 'alias of ...'
    # see https://stackoverflow.com/a/58982001/9703451
    Maps.add_feature.__name__ = "add_feature"
    Maps.add_feature.preset.__name__ = "preset"
    Maps.add_feature.cultural.__name__ = "cultural"
    Maps.add_feature.physical.__name__ = "physical"
    Maps.set_shape.__name__ = "set_shape"
    Maps.draw.__name__ = "draw"
    Maps.add_wms.__name__ = "add_wms"


# -- Project information

project = "EOmaps"
author = "Raphael Quast"

# -- General configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "sphinx_rtd_theme",
    "myst_nb",
    "sphinx_design",
]


# -- Options for EPUB output
epub_show_urls = "footnote"


templates_path = ["_templates"]
html_static_path = ["_static"]

html_theme = "sphinx_rtd_theme"


autosummary_generate = ["full_reference.rst", "autodoc_additional_props.rst"]

autodoc_default_options = {
    "member-order": "alphabetical",
}

# Napoleon settings
napoleon_numpy_docstring = True
napoleon_google_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

myst_update_mathjax = False  # to use single $x^2$ for equations
myst_render_markdown_format = "myst"  # to parse markdown output with MyST parser
myst_enable_extensions = ["dollarmath", "colon_fence"]
myst_title_to_header = True

nb_execution_mode = "off"
nb_execution_timeout = 120

# handle compiler warnings for duplicate labels due to documents
# included via the  ..include:: directive
exclude_patterns = [
    "build",
    "jupyter_execute/*",
    ".jupyter_cache/*",
    ".virtual_documents/*",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".ipynb": "myst-nb",
    ".myst": "myst-nb",
}

# a global substitution used to fix issues with images in tables
# in the mobile-theme (without a span they get resized to 0. This forces a size
# of at least 20% of the browser-window size)

rst_prolog = """
    .. |img_minsize| raw:: html

       <span style="display: inline-block; width: 20vw; height: 0px;"></span>
    """

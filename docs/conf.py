# Configuration file for the Sphinx documentation builder.
import sys, os

sys.path.insert(0, os.path.abspath(".." + os.sep + ".."))
sys.path.insert(0, os.path.abspath(".."))


def setup(app):
    app.add_css_file("custom_css.css")


from eomaps import Maps  # to run __init__.py

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


autosummary_generate = ["reference.rst"]
# autodoc_default_options = {
#     "member-order": "groupwise",
#     "inherited-members": True,
# }

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

nb_execution_mode = "cache"
nb_execution_timeout = 120

# handle compiler warnings for duplicate labels due to documents
# included via the  ..include:: directive
exclude_patterns = [
    "introduction.rst",
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

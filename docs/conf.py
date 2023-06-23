# Configuration file for the Sphinx documentation builder.
import sys, os

sys.path.insert(0, os.path.abspath(".." + os.sep + ".."))
sys.path.insert(0, os.path.abspath(".."))


def setup(app):
    app.add_css_file("custom_css.css")


# import mock

# MOCK_MODULES = [
#     "rtree",
#     "numpy",
#     "scipy",
#     "scipy.spatial",
#     "pandas",
#     "geopandas",
#     "matplotlib",
#     "matplotlib.pyplot",
#     "matplotlib.colors",
#     "matplotlib.gridspec",
#     "matplotlib.transforms",
#     "matplotlib.tri",
#     "matplotlib.collections",
#     "matplotlib.textpath",
#     "matplotlib.patches",
#     "matplotlib.transforms",
#     "matplotlib.font_manager",
#     "matplotlib.offsetbox",
#     "cartopy",
#     "cartopy.io",
#     "cartopy.io.img_tiles",
#     "cartopy.feature",
#     "descartes",
#     "mapclassify",
#     "pyproj",
#     "pyepsg",
#     "owslib",
#     "owslib.wmts",
#     "owslib.wms",
#     "PIL",
#     "Image",
#     "urllib3.exceptions",
#     "requests",
#     "requests.exceptions",
#     "xmltodict",
#     "cairosvg",
# ]

# for mod_name in MOCK_MODULES:
#     sys.modules[mod_name] = mock.Mock()

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
]


# -- Options for EPUB output
epub_show_urls = "footnote"


templates_path = ["_templates"]
html_static_path = ["_static"]

html_theme = "sphinx_rtd_theme"


autosummary_generate = ["reference.rst"]
autodoc_default_options = {
    "member-order": "groupwise",
    "inherited-members": True,
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

# handle compiler warnings for duplicate labels due to documents
# included via the  ..include:: directive
exclude_patterns = ["introduction.rst"]

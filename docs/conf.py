# Configuration file for the Sphinx documentation builder.
import sys, os

sys.path.insert(0, os.path.abspath(".." + os.sep + ".."))
sys.path.insert(0, os.path.abspath(".."))
import mock

MOCK_MODULES = [
    "rtree",
    "numpy",
    "scipy",
    "scipy.spatial",
    "pandas",
    "geopandas",
    "matplotlib",
    "cartopy",
    "descartes",
    "mapclassify",
    "pyproj",
    "pyepsg",
    "owslib",
    "requests",
    "requests.exceptions",
    "xmltodict",
    "cairosvg",
]

for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = mock.Mock()

import eomaps  # to run __init__.py


# -- Project information

project = "EOmaps"
author = "Raphael Quast"

# -- General configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    #'sphinx.ext.intersphinx',
    "sphinx.ext.napoleon",
]

# autodoc_default_options = {
#     'members': True,
#     'autoclass_content': 'class',
#     'member-order': 'bysource',
#     'special-members': '__init__',
#     'undoc-members': True,
#     'exclude-members': '__weakref__',
# }

# -- Options for EPUB output
epub_show_urls = "footnote"


templates_path = ["_templates"]


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

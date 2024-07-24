# Configuration file for the Sphinx documentation builder.
import os
import sys

from docutils.nodes import reference

from eomaps import Maps

sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))
sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("."))

from docs.source.gen_autodoc_file import make_feature_toctree_file

make_feature_toctree_file()


def mpl_rc_role_subst(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    A custom role to avoid 'undefined role' warnings when processing inherited
    docstrings from matplotlib that use the 'rc' role.

    Each :rc: role is just turned into a link to the matplotlib rcparams file where you
    can find the actual default value.
    """

    node = reference(
        "",
        f"matpltolib rcParams['{text}']",
        refuri=r"https://matplotlib.org/stable/users/explain/customizing.html#matplotlibrc-sample",
    )
    return [node], []


def setup(app):
    # add rc role to avoid undefined role warnings from inherited docstrings.
    app.add_role("rc", mpl_rc_role_subst)

    # add handling for skip-member event
    app.connect("autodoc-skip-member", autodoc_skip_member)

    # By default, autodoc will print 'alias of ...' for aliases.
    # This can be avoided by explicitly setting the __name__ property.
    # see https://stackoverflow.com/a/58982001/9703451
    Maps.add_feature.__name__ = "add_feature"
    Maps.add_feature.preset.__name__ = "preset"
    Maps.add_feature.cultural.__name__ = "cultural"
    Maps.add_feature.physical.__name__ = "physical"
    Maps.set_shape.__name__ = "set_shape"
    Maps.draw.__name__ = "draw"
    Maps.add_wms.__name__ = "add_wms"
    Maps.util.__name__ = "util"
    Maps.cb.__name__ = "cb"

    Maps.cb.click.__name__ = "click"
    Maps.cb.click.attach.__name__ = "attach"
    Maps.cb.click.get.__name__ = "get"

    Maps.cb.pick.__name__ = "pick"
    Maps.cb.pick.attach.__name__ = "attach"
    Maps.cb.pick.get.__name__ = "get"

    Maps.cb.keypress.__name__ = "keypress"
    Maps.cb.keypress.attach.__name__ = "attach"
    Maps.cb.keypress.get.__name__ = "get"

    Maps.cb.move.__name__ = "move"
    Maps.cb.move.attach.__name__ = "attach"
    Maps.cb.move.get.__name__ = "get"

    Maps.BM.__name__ = "BM"

    Maps.data_specs.__name__ = "data_specs"
    Maps.classify_specs.__name__ = "classify_specs"


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
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "pydata_sphinx_theme",
    "myst_nb",
    "sphinx_design",
]


# add mapping for matplotlib-docs to resolve warning about undefined labels
# in inherited docstrings
intersphinx_mapping = {"mpl": ("https://matplotlib.org/stable", None)}


# -- Options for EPUB output
epub_show_urls = "footnote"


templates_path = ["_templates"]
html_static_path = ["_static"]
html_css_files = ["custom_css.css"]

# PyData theme options
html_theme = "pydata_sphinx_theme"
html_logo = "../../logos/EO_Maps_Logo_V6.png"
html_theme_options = {
    "collapse_navigation": False,
    "show_nav_level": 2,
    "show_toc_level": 2,
    "header_links_before_dropdown": 10,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/raphaelquast/EOmaps",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/eomaps/",
            "icon": "fa-brands fa-python",
            "type": "fontawesome",
        },
    ],
}

autosummary_generate = ["api/autodoc_additional_props.rst"]  # "full_reference.rst",

autodoc_default_options = {
    "member-order": "alphabetical",
}


def autodoc_skip_member(app, what, name, obj, skip, options):
    # explicitly skip __init__ methods (to ensure they don't show up as methods)
    exclude = name in ("__init__",)
    return True if exclude else None


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
    # files starting with eomaps. are copied to the generated folder
    # (check "make_feature_toctree_file()" for more details.
    "api/eomaps.*",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".ipynb": "myst-nb",
    ".myst": "myst-nb",
}

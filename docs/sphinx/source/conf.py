"""
Base configuration.

### DO NOT CHANGE ####

Make changes in conf_local.py only.

"""
import os
import sys
from pathlib import Path

import yaml

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("../../.."))

# # LOCAL CONF --------------------------------------------------------------

import conf_local  # required to access specific vars

# -- Project information -----------------------------------------------------

project = conf_local.project
copyright = conf_local.copyright
author = conf_local.author

# -- Version information -----------------------------------------------------

version = conf_local.VERSION

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "myst_parser",
    "autoapi.extension",
    "sphinx.ext.mathjax",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to _source directory, that match files and
# directories to ignore when looking for _source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "build",
    "Thumbs.db",
    ".DS_Store",
    "build/*",
]

# -- Auto API settings

if conf_local.autoapi_dirs:
    autoapi_dirs = conf_local.autoapi_dirs
else:
    autoapi_dirs = ["../../../app"]

autoapi_type = "python"

autoapi_options = [
    "members",
    "undoc-members",
    "private-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
    "show-inheritance",
    "show-inheritance-diagram",
]
autoapi_member_order = "groupwise"
suppress_warnings = ["autoapi"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = "sphinx_book_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".

html_static_path = ["_static"]

# which class content to include
autoclass_content = "init"  # init

# MyST
# noinspection SpellCheckingInspection
# https://myst-parser.readthedocs.io/en/latest/syntax/optional.html
myst_enable_extensions = [
    "amsmath",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 2

# Is required for integration of OpenAPI / fastAPI into docs only
# If there is no app.main we assume that there is no fastAPI present
try:
    sys.path.append(os.path.relpath("../../../app"))
    sys.path.append(str(Path(__file__).parents[3]))

    from app.main import app

    openapi_json = app.openapi()
    with (Path(__file__).parents[2] / "files" / "openapi.yaml").open("w") as f:
        yaml.dump(openapi_json, f)
        print("updated openapi.yaml")

    # append extensions to default
    extensions.extend(
        [
            "sphinxcontrib.openapi",
            "app.main",  # reference to main.py, required for openapi
        ]
    )

except ImportError:
    pass

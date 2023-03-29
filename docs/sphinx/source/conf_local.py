"""
Local configuration
Contains all localized variables
"""

# -- Project information -----------------------------------------------------

project = "Tito API Wrapper"
copyright = "PySV/Königsweg"
author = "Königsweg"


# set if path is NOT default "../../../app"
autoapi_dirs = []


# change for packages
try:
    from app import __version__

    VERSION = __version__
except (ImportError, NameError):
    VERSION = ""

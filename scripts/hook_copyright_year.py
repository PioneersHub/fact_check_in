"""Alter config on run
https://www.mkdocs.org/user-guide/configuration/#hooks
"""

from datetime import datetime


def on_config(config, **kwargs):  # noqa ARG001
    config.copyright = f"Copyright © {datetime.now().year} Your Name"
    config.copyright = (
        f"Copyright © 2024{'-' + str(datetime.now().year) if datetime.now().year > 2024 else ''} Pioneers Hub gGmbH – "  # noqa: PLR2004
        f'<a href="#__consent">Change cookie settings</a>'
    )

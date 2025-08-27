#!/usr/bin/env python3
"""Sync README.md to docs/index.md for MkDocs"""

import shutil
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent
    readme_path = project_root / "README.md"
    docs_index = project_root / "docs" / "index.md"

    # Ensure docs directory exists
    docs_index.parent.mkdir(exist_ok=True)

    # Copy README to docs/index.md
    shutil.copy2(readme_path, docs_index)
    print(f"Copied {readme_path} to {docs_index}")


if __name__ == "__main__":
    main()

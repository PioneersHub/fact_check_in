"""
Dynamic router loading based on configured backend.

This module loads:
1. Common routers that are always included
2. Both backend-specific routers (Tito and Pretix) so all endpoints are available
   regardless of which backend is active at runtime. This allows tests and runtime
   to switch backends without restarting.
"""

import importlib
import traceback
from pathlib import Path

from app import log

# List to hold all routers that will be loaded into the main app
routers = []

# Get the base path for router modules
base_path = Path(__file__).parent

# First, load common routers (those directly in the routers directory)
for path_to_module in base_path.glob("*.py"):
    if path_to_module.stem[0] == "_":
        continue  # ignore sunder and dunder-files
    if path_to_module.stem == "tickets":
        continue  # Skip legacy tickets.py during transition

    package = __name__
    try:
        log.debug(f"adding common router from {path_to_module.stem}")
        router = importlib.import_module(f".{path_to_module.stem}", package=package)
        if hasattr(router, "router"):  # Check if module exports a router
            routers.append(router)
            log.debug(f"added common router from {path_to_module.stem}")
    except ImportError as e:
        log.error(f"ImportError: failed to import router from {path_to_module.stem}: {e}")
    except Exception as e:
        traceback.print_exc()
        log.error(f"error importing router from {path_to_module.stem}: {e}")


class BackendRouterModule:
    def __init__(self, router):
        self.router = router


# Second, always load BOTH backend-specific routers so all endpoints are available
for _backend_name, _backend_module_path, _backend_class in [
    ("tito", "app.tito.backend", "TitoBackend"),
    ("pretix", "app.pretix.backend", "PretixBackend"),
]:
    try:
        log.info(f"Loading router for {_backend_name} backend")
        _mod = importlib.import_module(_backend_module_path)
        _backend = getattr(_mod, _backend_class)()
        _backend_router = _backend.get_router()
        routers.append(BackendRouterModule(_backend_router))
        log.info(f"Successfully loaded {_backend_name} router")
    except Exception as e:
        log.error(f"Failed to load {_backend_name} router: {e}")
        traceback.print_exc()

log.info(f"Total routers loaded: {len(routers)}")

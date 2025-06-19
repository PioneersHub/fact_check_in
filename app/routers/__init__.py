"""
Dynamic router loading based on configured backend.

This module loads:
1. Common routers that are always included
2. Backend-specific routers based on the configured backend (Tito or Pretix)
"""

import importlib
import traceback
from pathlib import Path

from app import log
from app.ticketing.backend import get_backend_name, get_ticketing_backend

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

# Second, load backend-specific router
try:
    backend_name = get_backend_name()
    log.info(f"Loading router for {backend_name} backend")

    # Get the backend instance and its router
    backend = get_ticketing_backend()
    backend_router = backend.get_router()

    # Create a wrapper module for the backend router
    class BackendRouterModule:
        def __init__(self, router):
            self.router = router

    # Add the backend router to our routers list
    routers.append(BackendRouterModule(backend_router))
    log.info(f"Successfully loaded {backend_name} router")

except Exception as e:
    log.error(f"Failed to load backend-specific router: {e}")
    traceback.print_exc()

log.info(f"Total routers loaded: {len(routers)}")

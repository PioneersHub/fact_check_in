import importlib
import traceback
from pathlib import Path

base_path = Path(__file__).parent

routers = []
for path_to_module in base_path.glob("**/*.py"):
    if path_to_module.stem[0] == "_":
        continue  # ignore sunder and dunder-files
    # adding all routers dynamically
    parent_name = path_to_module.relative_to(base_path).parent.name
    package = __name__ if parent_name == "" else ".".join([__name__, parent_name])
    try:
        print(f"adding router from {path_to_module.stem} to routers")
        router = importlib.import_module(f".{path_to_module.stem}", package=package)
        routers.append(router)
        print(f"added router from {path_to_module.stem} to routers")
    except ImportError as e:
        print(f"ImportError: failed to import router from {path_to_module.stem}: {e}")
    except Exception as e:
        traceback.print_exc()
        print(f"error importing router from {path_to_module.stem}: {e}")

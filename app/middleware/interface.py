import json
import re

from unidecode import unidecode

from app.config import CONFIG, project_root


class Interface:
    # Singleton
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(*args, **kwargs)
        return cls._instance

    def __init__(self, in_dummy_mode=True):
        if not hasattr(self, "initialized"):  # Ensure __init__ is called only once
            self.initialized = True
        self._in_dummy_mode = in_dummy_mode
        self.all_sales: dict = {}
        self.all_releases: dict = {}
        self._release_id_map: dict = {}
        self._activity_release_id_map: dict = {}
        self._valid_ticket_ids: dict = {}
        self.initial_data_loaded: bool = False
        self.categories: dict = {}  # For Pretix categories
        if self.in_dummy_mode:
            self.set_dummy_data()

    @property
    def in_dummy_mode(self):
        return self._in_dummy_mode

    @in_dummy_mode.setter
    def in_dummy_mode(self, value):
        self._in_dummy_mode = value

    @property
    def release_id_map(self):
        if not self._release_id_map:
            self._release_id_map = {v["id"]: v for v in self.all_releases.values()}
        return self._release_id_map

    @property
    def valid_ticket_ids(self):
        if not self._valid_ticket_ids:
            self._valid_ticket_ids = {
                v["id"]: v for k, v in self.release_id_map.items() if set(v.get("activities", [])) & set(CONFIG.include_activities)
            }
        return self._valid_ticket_ids

    @property
    def activity_release_id_map(self):
        if not self._activity_release_id_map:
            collect = {}
            for a in self.release_id_map.values():
                for b in a["activities"]:
                    try:
                        collect[b].add(a["id"])
                    except KeyError:
                        collect[b] = {
                            a["id"],
                        }
            self._activity_release_id_map = collect
        return self._activity_release_id_map

    @classmethod
    def exclude_this_ticket_type(cls, ticket_name: str):
        """Filter by ticket name substrings"""
        for pattern in CONFIG.exclude_ticket_patterns:
            if pattern.lower() in ticket_name.lower():
                return True

    def valid_ticket_types(self, data):
        """List of qualified ticket types (releases)"""
        return [x for x in data if not self.exclude_this_ticket_type(x["title"])]

    @classmethod
    def normalization(cls, txt):
        """Remove all diacritic marks, normalize everything to ascii, and make all upper case"""
        txt = re.sub(r"\s{2,}", " ", txt).strip()
        return unidecode(txt).upper()

    def set_dummy_data(self):
        # Check which backend is being used
        import os

        from app.config import CONFIG

        backend_name = os.environ.get("TICKETING_BACKEND") or CONFIG.get("TICKETING_BACKEND", "tito")

        if backend_name.lower() == "pretix":
            # Load Pretix-specific fake data
            releases_file = "fake_all_releases_pretix.json"
            sales_file = "fake_all_sales_pretix.json"
        else:
            # Load Tito fake data (default)
            releases_file = "fake_all_releases.json"
            sales_file = "fake_all_sales.json"

        with (project_root / f"tests/test_data/{releases_file}").open() as f:
            self.all_releases = json.load(f)
        with (project_root / f"tests/test_data/{sales_file}").open() as f:
            self.all_sales = json.load(f)

        # For Pretix, extract categories from releases
        if backend_name.lower() == "pretix":
            self.categories = {}
            for release in self.all_releases.values():
                if release.get("category"):
                    cat = release["category"]
                    self.categories[cat["id"]] = cat

        self.initial_data_loaded = True

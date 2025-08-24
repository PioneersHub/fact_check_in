import json
import os
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
        self._all_sales: dict = {}
        self.all_releases: dict = {}
        self._release_id_map: dict = {}
        self._activity_release_id_map: dict = {}
        self._valid_ticket_ids: dict = {}
        self._valid_order_ids: dict = {}
        self._valid_order_email_combo: dict = {}
        self._valid_emails: dict = {}
        self._valid_names: dict = {}
        self._valid_order_name_combo: dict = {}
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
        return None

    @property
    def all_sales(self):
        return self._all_sales

    @all_sales.setter
    def all_sales(self, value):
        self._all_sales = value
        self.valid_order_ids = "trigger update"
        self.valid_order_email_combo = "trigger update"
        self.valid_order_name_combo = "trigger update"

    @property
    def valid_order_email_combo(self):
        if not self._valid_order_email_combo:
            self.valid_order_email_combo = "trigger refresh"
        return self._valid_order_email_combo

    @valid_order_email_combo.setter
    def valid_order_email_combo(self, value):
        print(f"valid_order_email_combo: {value}")
        # value is not relevant here, all_sales is the source
        self._valid_order_email_combo = {(x["order"], x["email"]): x for x in self.all_sales.values() if x["email"]}

    @property
    def valid_emails(self):
        if not self._valid_emails:
            self.valid_emails = "trigger refresh"
        return self._valid_emails

    @valid_emails.setter
    def valid_emails(self, value):
        print(f"valid_emails: {value}")
        # value is not relevant here, all_sales is the source
        self._valid_emails = {x["email"]: x for x in self.all_sales.values() if x["email"]}

    @property
    def valid_order_name_combo(self):
        if not self._valid_order_email_combo:
            self.valid_order_email_combo = "trigger refresh"
        return self._valid_order_name_combo

    @valid_order_name_combo.setter
    def valid_order_name_combo(self, value):
        print(f"valid_order_name_combo: {value}")
        # value is not relevant here, all_sales is the source
        self._valid_order_name_combo = {(x["order"], x["name"].strip().upper()): x for x in self.all_sales.values() if x["name"].strip()}

    @property
    def valid_names(self):
        if not self._valid_order_email_combo:
            self.valid_names = "trigger refresh"
        return self._valid_names

    @valid_names.setter
    def valid_names(self, value):
        print(f"valid_names: {value}")
        # value is not relevant here, all_sales is the source
        self._valid_names = {x["name"].strip().upper(): x for x in self.all_sales.values()}

    @property
    def valid_order_ids(self):
        if not self._valid_order_ids:
            self._valid_order_ids = "trigger refresh"
        return self._valid_order_ids

    @valid_order_ids.setter
    def valid_order_ids(self, value):
        print(f"valid_order_ids: {value}")
        # value is not relevant here, all_sales is the source
        self._valid_order_ids = {x["order"]: x for x in self.all_sales.values()}

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

        backend_name = os.environ.get("TICKETING_BACKEND")
        if not backend_name:
            raise RuntimeError("TICKETING_BACKEND environment variable not set")

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

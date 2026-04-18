import json
import re

from unidecode import unidecode

from app.config import CONFIG, project_root


class Interface:
    # Singleton
    _instance = None

    def __new__(cls, *_args, **_kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, in_dummy_mode=True):
        if not hasattr(self, "initialized"):  # Ensure __init__ is called only once
            self.initialized = True
        self._in_dummy_mode = in_dummy_mode
        self._all_sales: dict = {}
        self._all_releases: dict = {}
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
        self.addon_positions: list[dict] = []  # Add-on order positions (e.g., T-shirts)
        self.item_variations: dict[int, str] = {}  # Variation ID → name mapping
        if self.in_dummy_mode:
            self.set_dummy_data()

    @property
    def in_dummy_mode(self):
        return self._in_dummy_mode

    @in_dummy_mode.setter
    def in_dummy_mode(self, value):
        self._in_dummy_mode = value

    @property
    def all_releases(self):
        return self._all_releases

    @all_releases.setter
    def all_releases(self, value):
        self._all_releases = value
        # Invalidate all caches derived from releases
        self._release_id_map = {}
        self._valid_ticket_ids = {}
        self._activity_release_id_map = {}

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
        """Filter by ticket name substrings."""
        for pattern in CONFIG.exclude_ticket_patterns:
            if pattern.lower() in ticket_name.lower():
                return True
        return None

    @property
    def all_sales(self):
        return self._all_sales

    @all_sales.setter
    def all_sales(self, value: object) -> None:
        # value must be a dict, but typed as object to keep setter callable with
        # any trigger value (the actual data is read from self._all_sales).
        # Every derived cache must be rebuilt here; otherwise a later refresh
        # that adds new sales would leave stale lookup dicts and cause false
        # 404s on /validate_email/ and /validate_name/ for freshly sold tickets.
        self._all_sales = value  # type: ignore[assignment]
        self.valid_order_ids = None  # type: ignore[assignment]  # trigger cache rebuild
        self.valid_order_email_combo = None  # type: ignore[assignment]  # trigger cache rebuild
        self.valid_order_name_combo = None  # type: ignore[assignment]  # trigger cache rebuild
        self.valid_emails = None  # type: ignore[assignment]  # trigger cache rebuild
        self.valid_names = None  # type: ignore[assignment]  # trigger cache rebuild

    @property
    def valid_order_email_combo(self):
        if not self._valid_order_email_combo:
            self.valid_order_email_combo = "trigger refresh"  # type: ignore[assignment]
        return self._valid_order_email_combo

    @valid_order_email_combo.setter
    def valid_order_email_combo(self, _value: object) -> None:
        # _value is ignored; the dict is always rebuilt from self.all_sales.
        self._valid_order_email_combo = {(x["order"], x["email"]): x for x in self.all_sales.values() if x.get("order") and x.get("email")}

    @property
    def valid_emails(self):
        if not self._valid_emails:
            self.valid_emails = None  # trigger rebuild
        return self._valid_emails

    @valid_emails.setter
    def valid_emails(self, _value: object) -> None:
        # _value is ignored; the dict is always rebuilt from self.all_sales.
        self._valid_emails = {x["email"]: x for x in self.all_sales.values() if x["email"]}

    @property
    def valid_order_name_combo(self):
        if not self._valid_order_email_combo:
            self.valid_order_email_combo = "trigger refresh"  # type: ignore[assignment]
        return self._valid_order_name_combo

    @valid_order_name_combo.setter
    def valid_order_name_combo(self, _value: object) -> None:
        # _value is ignored; the dict is always rebuilt from self.all_sales.
        self._valid_order_name_combo = {
            (x["order"], x["name"].strip().upper()): x for x in self.all_sales.values() if x.get("order") and x.get("name", "").strip()
        }

    @property
    def valid_names(self):
        if not self._valid_order_email_combo:
            self.valid_names = None  # trigger rebuild
        return self._valid_names

    @valid_names.setter
    def valid_names(self, _value: object) -> None:
        # _value is ignored; the dict is always rebuilt from self.all_sales.
        self._valid_names = {x["name"].strip().upper(): x for x in self.all_sales.values()}

    @property
    def valid_order_ids(self):
        if not self._valid_order_ids:
            self.valid_order_ids = None  # trigger rebuild via setter
        return self._valid_order_ids

    @valid_order_ids.setter
    def valid_order_ids(self, _value: object) -> None:
        # _value is ignored; the dict is always rebuilt from self.all_sales.
        self._valid_order_ids = {x["order"]: x for x in self.all_sales.values() if x.get("order")}

    def valid_ticket_types(self, data):
        """Return list of qualified ticket types (releases)."""
        return [x for x in data if not self.exclude_this_ticket_type(x["title"])]

    @classmethod
    def normalization(cls, txt):
        """Remove all diacritic marks, normalize to ASCII, and make upper case."""
        txt = re.sub(r"\s{2,}", " ", txt).strip()
        return unidecode(txt).upper()

    def set_dummy_data(self):
        # Check which backend is being used
        backend_name = CONFIG.get("TICKETING_BACKEND")
        if not backend_name:
            raise RuntimeError("TICKETING_BACKEND not set")

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

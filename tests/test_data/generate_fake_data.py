import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

faker = Faker()
faker.seed_instance(42)  # Ensure reproducibility

# Predefined categories with fixed IDs and activities
categories_success = {
    "BUSINESS (IN-PERSON)": {
        "id": 1478120,
        "activities": ["on_site", "seat-person-monday", "seat-person-tuesday", "seat-person-wednesday", "sale_on_site", "online_access"],
    },
    "BUSINESS (ONLINE)": {"id": 1478123, "activities": ["remote_sale", "online_access"]},
    "DAY PASS MONDAY (IN-PERSON)": {"id": 1482880, "activities": ["on_site", "seat-person-monday", "online_access"]},
    "DAY PASS TUESDAY (IN-PERSON)": {"id": 1482881, "activities": ["seat-person-tuesday", "online_access"]},
    "DAY PASS WEDNESDAY (IN-PERSON)": {"id": 1482882, "activities": ["seat-person-wednesday", "online_access"]},
    "GRANT TICKET (IN-PERSON)": {
        "id": 1484848,
        "activities": ["on_site", "seat-person-monday", "seat-person-tuesday", "seat-person-wednesday", "free_on_site", "online_access"],
    },
    "GRANT TICKET (ONLINE)": {"id": 1484849, "activities": ["remote_sale", "online_access"]},
    "INDIVIDUAL (IN-PERSON)": {
        "id": 1478121,
        "activities": ["on_site", "seat-person-monday", "seat-person-tuesday", "seat-person-wednesday", "sale_on_site", "online_access"],
    },
    "INDIVIDUAL (ONLINE)": {"id": 1478124, "activities": ["remote_sale", "online_access"]},
    "KEYNOTE": {"id": 1495000, "activities": ["social_event", "online_access"]},
    "ORGANISER TICKET (IN-PERSON)": {
        "id": 1484846,
        "activities": [
            "on_site",
            "seat-person-monday",
            "seat-person-tuesday",
            "seat-person-wednesday",
            "free_on_site",
            "social_event",
            "online_access",
        ],
    },
    "PYLADIES TICKET (IN-PERSON)": {
        "id": 1484850,
        "activities": ["on_site", "seat-person-monday", "seat-person-tuesday", "seat-person-wednesday", "free_on_site", "online_access"],
    },
    "PYLADIES TICKET (ONLINE)": {"id": 1484851, "activities": ["remote_sale", "online_access"]},
    "SPEAKER TICKET (IN-PERSON)": {
        "id": 1484845,
        "activities": ["on_site", "seat-person-monday", "seat-person-tuesday", "seat-person-wednesday", "free_on_site", "online_access"],
    },
    "SPONSOR (IN-PERSON)": {
        "id": 1478315,
        "activities": [
            "on_site",
            "seat-person-monday",
            "seat-person-tuesday",
            "seat-person-wednesday",
            "sponsors_on_site",
            "online_access",
        ],
    },
    "SPONSOR (ONLINE)": {"id": 1478316, "activities": ["remote_sale", "online_access"]},
    "STUDENT (IN-PERSON)": {
        "id": 1478122,
        "activities": ["on_site", "seat-person-monday", "seat-person-tuesday", "seat-person-wednesday", "sale_on_site", "online_access"],
    },
    "STUDENT (ONLINE)": {"id": 1478125, "activities": ["remote_sale", "online_access"]},
    "VOLUNTEER TICKET (IN-PERSON)": {
        "id": 1484847,
        "activities": ["on_site", "seat-person-monday", "seat-person-tuesday", "seat-person-wednesday", "free_on_site", "online_access"],
    },
}

categories_fail = {
    "1 PIECE OF LUGGAGE ON MONDAY": {"id": 1495774, "activities": []},
    "1 PIECE OF LUGGAGE ON WEDNESDAY": {"id": 1495775, "activities": []},
    "CHILDCARE MONDAY": {"id": 1491499, "activities": ["childcare"]},
    "CHILDCARE TUESDAY": {"id": 1491500, "activities": ["childcare"]},
    "CHILDCARE WEDNESDAY": {"id": 1491501, "activities": ["childcare"]},
}


# Function to generate fake structured data with constant IDs
def generate_fake_all_releases():
    data = {}
    categories = {}
    categories.update(categories_success)
    categories.update(categories_fail)
    for category, details in categories_success.items():
        data[category] = {"activities": details["activities"], "id": details["id"], "title": category.title()}

    return data


# Generate fake structured data
fake_all_releases = generate_fake_all_releases()


def generate_fake_reference():
    return "".join(random.choices(string.ascii_uppercase, k=4)) + f"-{random.randint(1, 10)}"


def get_random_category_id(successful_items=True):
    if successful_items:
        return random.choice(list(categories_success.values()))["id"]
    return random.choice(list(categories_fail.values()))["id"]


def generate_fake_all_sales(successful_items=True):
    created_at = faker.date_time_this_year().isoformat() + "+02:00"  # Fake timestamp with timezone
    updated_at = (datetime.fromisoformat(created_at[:-6]) + timedelta(minutes=random.randint(1, 60))).isoformat() + "+02:00"

    first_name = faker.first_name()
    last_name = faker.last_name()
    email = faker.email()

    return {
        "assigned": True,
        "created_at": created_at,
        "email": f"{first_name.lower()}.{last_name.lower()}@{email.split('@')[1]}",
        "first_name": first_name,
        "last_name": last_name,
        "name": f"{first_name} {last_name}",
        "reference": generate_fake_reference(),
        "registration_id": faker.random_int(min=10000000, max=99999999),
        "release_id": get_random_category_id(successful_items),
        "state": "assigned",
        "updated_at": updated_at,
    }


# Generate fake sales
fake_all_sales = [generate_fake_all_sales(successful_items=True) for i in range(35)]
# generate unassigned sales
for i in range(-5, 0):  # Last 5 elements
    fake_all_sales[i].update(
        {
            "email": "",
            "first_name": "",
            "last_name": "",
            "name": "",
            "state": "unassigned",  # Fixed typo: "undassigned" → "unassigned"
            "assigned": False,
        }
    )
fake_all_sales_fail = {x["reference"].upper(): x for x in fake_all_sales[-5:]}
fake_all_sales = {x["reference"].upper(): x for x in fake_all_sales[:-5]}

more_fails = [generate_fake_all_sales(successful_items=False) for i in range(10)]
more_fails = {x["reference"].upper(): x for x in more_fails}
fake_all_sales_fail.update(more_fails)


here = Path(__file__).parent

with (here / "fake_all_sales.json").open("w") as f:
    json.dump(fake_all_sales, f, indent=2)
with (here / "fake_all_sales_fail.json").open("w") as f:
    json.dump(fake_all_sales_fail, f, indent=2)
with (here / "fake_all_releases.json").open("w") as f:
    json.dump(fake_all_releases, f, indent=2)

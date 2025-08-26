# test_tickets.py
import json
import logging
import os
from pathlib import Path

os.environ["FAKE_CHECK_IN_TEST_MODE"] = "1"
os.environ["TICKETING_BACKEND"] = "tito"  # These tests are for Tito backend

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import emails, one_of, text

# Import reset_interface but NOT the app yet
from app import reset_interface

# Set logging level to WARNING to suppress HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
# Set logging level to WARNING to suppress faker logs
logging.getLogger("faker").setLevel(logging.WARNING)


# Load the fake data using absolute paths based on this file's location
test_dir = Path(__file__).parent
with open(test_dir / "test_data" / "fake_all_sales.json") as f:
    fake_data = json.load(f)

with open(test_dir / "test_data" / "fake_all_sales_fail.json") as f:
    fake_data_fail = json.load(f)

# Router is already included via main.py dynamic loading


@pytest.fixture
def client():
    # Import app here AFTER environment is set
    from app.main import app

    # make sure to run against test data and not the live API
    reset_interface(dummy_mode=True)
    return TestClient(app)


@pytest.mark.parametrize("reference,ticket", fake_data.items())
def test_validate_name(client, reference, ticket):
    attendee = {"ticket_id": reference, "name": ticket["name"]}
    response = client.post("/tickets/validate_name/", json=attendee)
    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["is_attendee"] == (ticket["state"] != "unassigned")


@pytest.mark.parametrize("reference,ticket", fake_data_fail.items())
def test_validate_name_fail(client, reference, ticket):
    attendee = {"ticket_id": reference, "name": ticket["name"]}
    response = client.post("/tickets/validate_name/", json=attendee)
    if not reference or not ticket.get("name"):
        assert response.status_code == 422  # Unprocessable Entity  # noqa: PLR2004
    else:
        assert response.status_code != 200  # noqa: PLR2004
        data = response.json()
        assert not data["is_attendee"]
        assert "hint" in data


# random data tests must all fail
@settings(max_examples=50, deadline=2000)
@given(reference=st.text(min_size=1, max_size=10))
def test_validate_random_reference(reference):
    from app.main import app

    with TestClient(app) as client:
        attendee = {"ticket_id": reference, "name": "Test Name"}
        response = client.post("/tickets/validate_name/", json=attendee)
        assert response.status_code in [404, 422]


@settings(max_examples=50, deadline=2000)
@given(name=st.text(min_size=1, max_size=50))
def test_validate_random_name(name):
    from app.main import app

    with TestClient(app) as client:
        attendee = {"ticket_id": "TestID", "name": name}
        response = client.post("/tickets/validate_name/", json=attendee)
        assert response.status_code in [404, 422]


@settings(max_examples=50, deadline=2000)
@given(email=one_of(emails(), text(min_size=1, max_size=50)))
def test_validate_random_email(email):
    from app.main import app

    with TestClient(app) as client:
        attendee = {"ticket_id": "TestID", "name": "Test Name", "email": email}
        response = client.post("/tickets/validate_name/", json=attendee)
        assert response.status_code in [404, 422]


# Run the tests
if __name__ == "__main__":
    pytest.main()

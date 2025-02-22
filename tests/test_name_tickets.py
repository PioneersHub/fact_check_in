# test_tickets.py
import json
import logging
import os

os.environ["FAKE_CHECK_IN_TEST_MODE"] = "1"

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import emails, one_of, text

from app import reset_interface
from app.main import app
from app.routers.tickets import router

# Set logging level to WARNING to suppress HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
# Set logging level to WARNING to suppress faker logs
logging.getLogger("faker").setLevel(logging.WARNING)


# Load the fake data
with open("test_data/fake_all_sales.json") as f:
    fake_data = json.load(f)

with open("test_data/fake_all_sales_fail.json") as f:
    fake_data_fail = json.load(f)

# Add the router to the app for testing
app.include_router(router)


@pytest.fixture
def client():
    # make sure to run against test data and not the live API
    reset_interface(dummy_mode=True)
    return TestClient(app)


@pytest.mark.parametrize("reference,ticket", fake_data.items())
def test_validate_name(client, reference, ticket):
    attendee = {"ticket_id": reference, "name": ticket["name"]}
    response = client.post("/tickets/validate_name/", json=attendee)
    assert response.status_code == 200
    data = response.json()
    assert data["is_attendee"] == (ticket["state"] != "unassigned")


@pytest.mark.parametrize("reference,ticket", fake_data_fail.items())
def test_validate_name_fail(client, reference, ticket):
    attendee = {"ticket_id": reference, "name": ticket["name"]}
    response = client.post("/tickets/validate_name/", json=attendee)
    if not reference or not ticket.get("name"):
        assert response.status_code == 422  # Unprocessable Entity
    else:
        assert response.status_code != 200
        data = response.json()
        assert data["is_attendee"] == False
        assert "hint" in data


# random data tests must all fail
@settings(max_examples=50, deadline=2000)
@given(reference=st.text(min_size=1, max_size=10))
def test_validate_random_reference(reference):
    with TestClient(app) as client:
        attendee = {"ticket_id": reference, "name": "Test Name"}
        response = client.post("/tickets/validate_name/", json=attendee)
        assert response.status_code in [404, 422]


@settings(max_examples=50, deadline=2000)
@given(name=st.text(min_size=1, max_size=50))
def test_validate_random_name(name):
    with TestClient(app) as client:
        attendee = {"ticket_id": "TestID", "name": name}
        response = client.post("/tickets/validate_name/", json=attendee)
        assert response.status_code in [404, 422]


@settings(max_examples=50, deadline=2000)
@given(email=one_of(emails(), text(min_size=1, max_size=50)))
def test_validate_random_email(email):
    with TestClient(app) as client:
        attendee = {"ticket_id": "TestID", "name": "Test Name", "email": email}
        response = client.post("/tickets/validate_name/", json=attendee)
        assert response.status_code in [404, 422]


# Run the tests
if __name__ == "__main__":
    pytest.main()

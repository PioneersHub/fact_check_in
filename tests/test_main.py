import pytest


@pytest.mark.smoke_test
def test_healthcheck(app_client):
    response = app_client.get("/healthcheck/alive")
    assert response.status_code == 200
    assert response.json() == {"alive": True}

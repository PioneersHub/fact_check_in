from http import HTTPStatus

import pytest


@pytest.mark.smoke_test
def test_healthcheck(app_client):
    response = app_client.get("/healthcheck/alive")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"alive": True}

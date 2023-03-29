import pytest


@pytest.mark.smoke_test
def test_healthcheck(app_client):
    response = app_client.get("/healthcheck/alive")
    assert response.status_code == 200
    assert response.json() == {"message": "I'm alive!"}


@pytest.mark.smoke_test
def test_environment(app_client):
    response = app_client.get("/healthcheck/environment")
    assert response.status_code == 200


@pytest.mark.smoke_test
def test_python_env(app_client):
    response = app_client.get("/healthcheck/python_env")
    j = response.json()
    assert response.status_code == 200
    assert "pytest" in j
    assert "requests" in j


@pytest.mark.smoke_test
def test_static(app_client):
    response = app_client.get("/static")
    assert response.status_code == 200
    print(response.text)

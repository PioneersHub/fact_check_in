"""Tests for OAuth2/Keycloak authentication.

Uses real RSA key pairs and mocked OIDC discovery / JWKS endpoints to verify JWT validation works
correctly.
"""

import time
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

# -- RSA key fixtures --

ISSUER_URL = "https://keycloak.test/realms/test-realm"
AUDIENCE = "test-client"


@pytest.fixture(scope="module")
def rsa_keypair():
    """Generate an RSA key pair for signing test JWTs."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key, private_key.public_key()


@pytest.fixture(scope="module")
def jwks_response(rsa_keypair):
    """Build a JWKS response containing the test public key."""
    _, public_key = rsa_keypair
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = "test-key-id"
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return {"keys": [jwk]}


def _make_token(  # noqa: PLR0913
    rsa_keypair,
    *,
    exp_offset: int = 3600,
    issuer: str = ISSUER_URL,
    audience: str = AUDIENCE,
    include_sub: bool = True,
    extra_claims: dict | None = None,
) -> str:
    """Create a signed JWT with the given claims."""
    private_key, _ = rsa_keypair
    now = int(time.time())
    payload = {
        "iss": issuer,
        "aud": audience,
        "exp": now + exp_offset,
        "iat": now,
        **({"sub": "test-user-id"} if include_sub else {}),
        **(extra_claims or {}),
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-id"},
    )


def _mock_oidc_discovery(jwks_uri: str):
    """Return a side_effect for requests.get that serves OIDC discovery."""
    discovery_doc = {
        "issuer": ISSUER_URL,
        "jwks_uri": jwks_uri,
        "authorization_endpoint": f"{ISSUER_URL}/protocol/openid-connect/auth",
        "token_endpoint": f"{ISSUER_URL}/protocol/openid-connect/token",
    }

    def side_effect(url, **kwargs):  # noqa: ARG001
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = discovery_doc
        return mock_resp

    return side_effect


def _clear_auth_caches():
    """Clear all auth caches between tests."""
    from app.auth import _get_jwks_client, _get_oidc_config, get_auth_config

    _get_oidc_config.cache.clear()  # type: ignore[attr-defined]
    _get_jwks_client.cache.clear()  # type: ignore[attr-defined]
    get_auth_config.cache_clear()


@pytest.fixture
def auth_client(monkeypatch, jwks_response) -> Generator[TestClient]:
    """Test client with Keycloak OAuth2 authentication enabled."""
    from app.config import CONFIG

    monkeypatch.setenv("TICKETING_BACKEND", "tito")
    monkeypatch.setenv("OIDC_ISSUER_URL", ISSUER_URL)
    monkeypatch.setenv("OIDC_AUDIENCE", AUDIENCE)
    CONFIG["TICKETING_BACKEND"] = "tito"

    _clear_auth_caches()

    from app import reset_interface
    from app.main import app

    reset_interface(dummy_mode=True)

    jwks_uri = f"{ISSUER_URL}/protocol/openid-connect/certs"
    with (
        patch("requests.get", side_effect=_mock_oidc_discovery(jwks_uri)),
        patch.object(
            jwt.PyJWKClient,
            "fetch_data",
            return_value=jwks_response,
        ),
    ):
        yield TestClient(app)

    _clear_auth_caches()


@pytest.fixture
def noauth_client(monkeypatch) -> Generator[TestClient]:
    """Test client with authentication disabled (no OIDC config)."""
    from app.config import CONFIG

    monkeypatch.setenv("TICKETING_BACKEND", "tito")
    monkeypatch.delenv("OIDC_ISSUER_URL", raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)
    CONFIG["TICKETING_BACKEND"] = "tito"

    _clear_auth_caches()

    from app import reset_interface
    from app.main import app

    reset_interface(dummy_mode=True)
    yield TestClient(app)

    _clear_auth_caches()


# -- Auth enabled tests --


class TestOAuth2Enabled:
    """Tests when OIDC_ISSUER_URL is set and auth is required."""

    def test_valid_token_passes(self, auth_client, rsa_keypair):
        token = _make_token(rsa_keypair)
        response = auth_client.get(
            "/tickets/ticket_count/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200  # noqa: PLR2004

    def test_missing_token_returns_401(self, auth_client):
        response = auth_client.get("/tickets/ticket_count/")
        assert response.status_code == 401  # noqa: PLR2004
        assert response.json()["detail"] == "Missing authentication credentials"

    def test_expired_token_returns_401(self, auth_client, rsa_keypair):
        token = _make_token(rsa_keypair, exp_offset=-3600)
        response = auth_client.get(
            "/tickets/ticket_count/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401  # noqa: PLR2004
        assert response.json()["detail"] == "Token has expired"

    def test_wrong_audience_returns_401(self, auth_client, rsa_keypair):
        token = _make_token(rsa_keypair, audience="wrong-client")
        response = auth_client.get(
            "/tickets/ticket_count/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401  # noqa: PLR2004
        assert response.json()["detail"] == "Invalid token audience"

    def test_wrong_issuer_returns_401(self, auth_client, rsa_keypair):
        token = _make_token(rsa_keypair, issuer="https://evil.example.com")
        response = auth_client.get(
            "/tickets/ticket_count/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401  # noqa: PLR2004
        assert response.json()["detail"] == "Invalid token issuer"

    def test_missing_sub_claim_returns_401(self, auth_client, rsa_keypair):
        """Tokens without a 'sub' claim should be rejected."""
        token = _make_token(rsa_keypair, include_sub=False)
        response = auth_client.get(
            "/tickets/ticket_count/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401  # noqa: PLR2004
        assert response.json()["detail"] == "Token missing required claims"

    def test_garbage_token_returns_401(self, auth_client):
        response = auth_client.get(
            "/tickets/ticket_count/",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        assert response.status_code == 401  # noqa: PLR2004
        assert response.json()["detail"] == "Invalid or malformed token"

    def test_healthcheck_no_auth_required(self, auth_client):
        """Healthcheck endpoints remain public even with auth enabled."""
        response = auth_client.get("/healthcheck/alive")
        assert response.status_code == 200  # noqa: PLR2004
        assert response.json() == {"alive": True}

    def test_root_no_auth_required(self, auth_client):
        """Root endpoint remains public even with auth enabled."""
        response = auth_client.get("/")
        assert response.status_code == 200  # noqa: PLR2004
        assert response.json() == {"alive": True}

    def test_post_endpoint_requires_auth(self, auth_client):
        """POST endpoints also require auth."""
        response = auth_client.post(
            "/tickets/validate_name/",
            json={"ticket_id": "TEST123", "name": "Test User"},
        )
        assert response.status_code == 401  # noqa: PLR2004

    def test_post_endpoint_with_auth(self, auth_client, rsa_keypair):
        """POST endpoints work with valid auth."""
        token = _make_token(rsa_keypair)
        response = auth_client.post(
            "/tickets/validate_name/",
            json={"ticket_id": "TEST123", "name": "Test User"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should not be 401 - the request is authenticated.
        # It may be 404 (ticket not found) which is correct behavior.
        assert response.status_code != 401  # noqa: PLR2004


# -- Auth disabled tests --


class TestOAuth2Disabled:
    """Tests when OIDC_ISSUER_URL is not set and auth is disabled."""

    def test_request_without_token_passes(self, noauth_client):
        response = noauth_client.get("/tickets/ticket_count/")
        assert response.status_code == 200  # noqa: PLR2004

    def test_healthcheck_still_works(self, noauth_client):
        response = noauth_client.get("/healthcheck/alive")
        assert response.status_code == 200  # noqa: PLR2004

    def test_request_with_token_still_passes(self, noauth_client):
        """Providing a token when auth is disabled should not cause errors."""
        response = noauth_client.get(
            "/tickets/ticket_count/",
            headers={"Authorization": "Bearer some-token"},
        )
        assert response.status_code == 200  # noqa: PLR2004

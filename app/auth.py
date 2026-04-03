"""OAuth2 authentication via Keycloak (or any OIDC provider).

Validates JWT Bearer tokens using the provider's JWKS (JSON Web Key Set).
OIDC discovery is used to automatically resolve the JWKS URI from the issuer URL.

Configuration via environment variables:
    OIDC_ISSUER_URL  - Keycloak realm URL, e.g.
                       https://keycloak.example.com/realms/my-realm
    OIDC_AUDIENCE    - Expected JWT audience (usually the Keycloak client ID).
                       Defaults to "account" if not set.
    OIDC_ALGORITHMS  - Comma-separated signing algorithms. Defaults to "RS256".

When OIDC_ISSUER_URL is not set, authentication is completely disabled and all requests pass through
with a dev-mode sentinel. This keeps local development simple.
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Annotated, Any

import jwt
import requests
from cachetools import TTLCache, cached
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# -- Configuration ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuthConfig:
    """OIDC auth settings, loaded once from environment variables."""

    issuer_url: str = ""
    audience: str = "account"
    algorithms: list[str] = field(default_factory=lambda: ["RS256"])

    @property
    def enabled(self) -> bool:
        return bool(self.issuer_url)


@lru_cache(maxsize=1)
def get_auth_config() -> AuthConfig:
    """Load auth config from env vars once and cache it forever."""
    issuer = os.environ.get("OIDC_ISSUER_URL", "").rstrip("/")
    audience = os.environ.get("OIDC_AUDIENCE", "account")
    algorithms = [a.strip() for a in os.environ.get("OIDC_ALGORITHMS", "RS256").split(",")]
    return AuthConfig(issuer_url=issuer, audience=audience, algorithms=algorithms)


# -- Token claims model -----------------------------------------------------------


class TokenClaims(BaseModel):
    """Decoded and validated JWT claims.

    Contains standard OIDC claims plus a flag indicating whether auth
    was actually performed (disabled_auth=True in dev mode).
    """

    sub: str
    iss: str = ""
    aud: str | list[str] = ""
    exp: int = 0
    scope: str = ""
    disabled_auth: bool = False


#: Sentinel returned when auth is disabled (no OIDC_ISSUER_URL set).
#: Route handlers can check ``claims.disabled_auth`` if they need to
#: distinguish between authenticated and unauthenticated contexts.
_DEV_CLAIMS = TokenClaims(sub="dev-user", disabled_auth=True)


# -- OIDC / JWKS helpers ----------------------------------------------------------


# auto_error=False so we can return a clear 401 instead of the default 403
# when the Authorization header is missing entirely.
_bearer_scheme = HTTPBearer(auto_error=False)

_cache_lock = threading.Lock()


@cached(cache=TTLCache(maxsize=1, ttl=3600), lock=_cache_lock)  # type: ignore[misc]
def _get_oidc_config(issuer_url: str) -> dict[str, Any]:
    """Fetch and cache the OIDC discovery document.

    Cached for 1 hour since OIDC metadata rarely changes. The lock
    prevents concurrent cold-cache requests from duplicating the fetch.
    """
    discovery_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
    resp = requests.get(discovery_url, timeout=10)
    resp.raise_for_status()
    return resp.json()


@cached(cache=TTLCache(maxsize=1, ttl=3600), lock=_cache_lock)  # type: ignore[misc]
def _get_jwks_client(jwks_uri: str) -> jwt.PyJWKClient:
    """Create and cache a PyJWKClient for the given JWKS URI.

    The client itself caches keys internally, and this outer cache
    avoids re-creating the client object on every request.
    """
    return jwt.PyJWKClient(jwks_uri, cache_keys=True, lifespan=3600)


# -- Token decoding ---------------------------------------------------------------


def _decode_token(token: str, config: AuthConfig) -> TokenClaims:
    """Decode and validate a JWT against the Keycloak OIDC provider.

    Verifies signature (via JWKS), expiration, issuer, audience, and sub.
    Raises HTTPException on any validation failure.
    """
    try:
        oidc_config = _get_oidc_config(config.issuer_url)

        jwks_uri = oidc_config.get("jwks_uri")
        if not jwks_uri:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC discovery document missing jwks_uri",
            )

        jwks_client = _get_jwks_client(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=config.algorithms,
            audience=config.audience,
            issuer=config.issuer_url,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        return TokenClaims.model_validate(claims)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.MissingRequiredClaimError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        logger.debug("JWT validation failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except requests.RequestException:
        logger.error("Failed to reach OIDC provider", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from None


# -- FastAPI dependency ------------------------------------------------------------


def verify_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> TokenClaims:
    """FastAPI dependency that validates the OAuth2 Bearer token.

    Returns a TokenClaims with the decoded JWT claims. When auth is
    disabled (OIDC_ISSUER_URL not set), returns a dev-mode sentinel
    with disabled_auth=True.

    FastAPI runs sync dependencies in a threadpool, so the blocking
    requests.get call for OIDC discovery (only on cold cache) does
    not block the async event loop.
    """
    config = get_auth_config()

    if not config.enabled:
        return _DEV_CLAIMS

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _decode_token(credentials.credentials, config)

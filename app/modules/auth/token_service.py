import asyncio

import jwt
from jwt import PyJWKClient

from app.core.config import settings


if not settings.cognito_user_pool_id:
    raise RuntimeError(
        "COGNITO_USER_POOL_ID is not configured."
    )

ISSUER = (
    f"https://cognito-idp.{settings.aws_region}.amazonaws.com/"
    f"{settings.cognito_user_pool_id}"
)

JWKS_URL = f"{ISSUER}/.well-known/jwks.json"

jwks_client = PyJWKClient(JWKS_URL)


def _verify_access_token(token: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(
        token
    )

    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=ISSUER,
        options={
            "verify_aud": False,
            "require": ["exp", "iat", "iss", "sub"],
        },
    )

    if claims.get("token_use") != "access":
        raise jwt.InvalidTokenError(
            "An access token is required."
        )

    if claims.get("client_id") != settings.cognito_client_id:
        raise jwt.InvalidTokenError(
            "Token was issued to a different app client."
        )

    return claims


async def verify_access_token(token: str) -> dict:
    return await asyncio.to_thread(
        _verify_access_token,
        token,
    )
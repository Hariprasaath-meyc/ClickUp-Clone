
import base64
import hashlib
import hmac

import boto3

from app.core.config import settings


def get_cognito_client():
    if not settings.COGNITO_CLIENT_ID:
        raise RuntimeError(
            "COGNITO_CLIENT_ID is not configured"
        )

    return boto3.client(
        "cognito-idp",
        region_name=settings.AWS_REGION,
    )


def calculate_secret_hash(username: str) -> str:
    client_id = settings.COGNITO_CLIENT_ID
    client_secret = settings.COGNITO_CLIENT_SECRET

    if not client_id or not client_secret:
        raise RuntimeError(
            "Cognito client ID and secret must be configured"
        )

    message = username + client_id

    digest = hmac.new(
        client_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.b64encode(digest).decode("utf-8")

def refresh_cognito_session(
    refresh_token: str,
    username: str,
) -> dict:
    client = get_cognito_client()

    response = client.initiate_auth(
        ClientId=settings.COGNITO_CLIENT_ID,
        AuthFlow="REFRESH_TOKEN_AUTH",
        AuthParameters={
            "REFRESH_TOKEN": refresh_token,
            "SECRET_HASH": calculate_secret_hash(username),
        },
    )

    return response["AuthenticationResult"]
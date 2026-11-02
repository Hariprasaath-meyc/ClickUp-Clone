import boto3

from app.core.config import settings


def get_cognito_client():

    if not settings.cognito_client_id:
        raise RuntimeError(
            "COGNITO_CLIENT_ID is not configured"
        )

    return boto3.client(
        "cognito-idp",
        region_name=settings.aws_region,
    )


def refresh_cognito_session(
    refresh_token: str,
) -> dict:

    client = get_cognito_client()

    if not settings.cognito_client_secret:
        raise RuntimeError(
            "COGNITO_CLIENT_SECRET is not configured"
        )

    response = client.get_tokens_from_refresh_token(
        RefreshToken=refresh_token,
        ClientId=settings.cognito_client_id,
        ClientSecret=settings.cognito_client_secret,
    )

    return response["AuthenticationResult"]
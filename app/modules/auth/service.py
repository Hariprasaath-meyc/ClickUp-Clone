
import asyncio
import base64
import email
import hashlib
import hmac

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


cognito = boto3.client(
    "cognito-idp",
    region_name=settings.aws_region,
)

def calculate_secret_hash(username: str) -> str:
    message = username + settings.cognito_client_id

    digest = hmac.new(
        settings.cognito_client_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.b64encode(digest).decode("utf-8")

#Signup, confirm_signup, and resend_confirmation_code 
class AuthService:
    @staticmethod
    async def signup(
        name: str,
        email: str,
        password: str,
    ) -> dict:
        try:
            result = await asyncio.to_thread(
                cognito.sign_up,
                ClientId=settings.cognito_client_id,
                SecretHash=calculate_secret_hash(email),
                Username=email,
                Password=password,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "name", "Value": name},
                ],
            )

            return {
                "user_id": result["UserSub"],
                "email": email,
                "name": name,
                "confirmed": result.get("UserConfirmed", False),
            }

        except ClientError as exc:
            error = exc.response.get("Error", {})
            code = error.get("Code")

            messages = {
                "UsernameExistsException":
                    "An account with this email already exists.",
                "InvalidPasswordException":
                    "The password does not meet Cognito's requirements.",
                "InvalidParameterException":
                    "One or more signup inputs are invalid.",
                "LimitExceededException":
                    "The signup limit has been reached.",
                "TooManyRequestsException":
                    "Too many requests. Please try again later.",
            }

            if code in messages:
                raise ValueError(messages[code]) from exc

            raise RuntimeError(
                "Cognito signup failed."
            ) from exc

    
    @staticmethod
    async def confirm_signup(
        email: str,
        confirmation_code: str,
    ) -> dict:
        try:
            await asyncio.to_thread(
                cognito.confirm_sign_up,
                ClientId=settings.cognito_client_id,
                Username=email,
                ConfirmationCode=confirmation_code,
                SecretHash=calculate_secret_hash(email),
            )

            return {
                "success": True,
                "message": "Email confirmed successfully.",
            }

        except ClientError as exc:
            error = exc.response.get("Error", {})
            code = error.get("Code")

            messages = {
                "CodeMismatchException":
                    "The confirmation code is incorrect.",
                "ExpiredCodeException":
                    "The confirmation code has expired.",
                "UserNotFoundException":
                    "The account was not found.",
                "NotAuthorizedException":
                    "The account may already be confirmed or the request is not authorized.",
                "TooManyFailedAttemptsException":
                    "Too many incorrect attempts. Try again later.",
            }

            if code in messages:
                raise ValueError(messages[code]) from exc

            raise RuntimeError(
                "Cognito confirmation failed."
            ) from exc
        
    @staticmethod
    async def resend_confirmation_code(email: str) -> dict:
        try:
            result = await asyncio.to_thread(
                cognito.resend_confirmation_code,
                ClientId=settings.cognito_client_id,
                Username=email,
                SecretHash=calculate_secret_hash(email),
            )

            return {
                "message": "A new confirmation code was requested.",
                "delivery": result.get("CodeDeliveryDetails", {}),
            }

        except ClientError as exc:
            error = exc.response.get("Error", {})
            print(
                "Cognito resend error:",
                error.get("Code"),
                error.get("Message"),
            )
            raise RuntimeError(
                "Could not resend the confirmation code."
            ) from exc

#User login method
    
    @staticmethod
    async def login(email: str, password: str) -> dict:
        email = email.strip()

        try:
            result = await asyncio.to_thread(
                cognito.initiate_auth,
                ClientId=settings.cognito_client_id,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": email,
                    "PASSWORD": password,
                    "SECRET_HASH": calculate_secret_hash(email),
                },
            )

            if result.get("ChallengeName"):
                raise ValueError(
                    "Additional authentication is required."
                )

            tokens = result.get("AuthenticationResult")

            if not tokens or not tokens.get("AccessToken"):
                raise RuntimeError(
                    "Cognito did not return an access token."
                )

            return {
                "access_token": tokens["AccessToken"],
                "id_token": tokens["IdToken"],
                "refresh_token": tokens.get("RefreshToken"),
                "expires_in": tokens["ExpiresIn"],
                "token_type": tokens.get("TokenType", "Bearer"),
            }

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            print("Cognito login error code:", error_code)

            if error_code in {
                "NotAuthorizedException",
                "UserNotFoundException",
            }:
                raise ValueError(
                    "Invalid email or password."
                ) from exc

            if error_code == "UserNotConfirmedException":
                raise ValueError(
                    "Please confirm your email before logging in."
                ) from exc

            if error_code == "PasswordResetRequiredException":
                raise ValueError(
                    "A password reset is required."
                ) from exc

            if error_code in {
                "TooManyRequestsException",
                "LimitExceededException",
            }:
                raise ValueError(
                    "Too many authentication attempts. Try again later."
                ) from exc

            raise RuntimeError(
                "Cognito authentication failed."
            ) from exc
        
    @staticmethod
    async def refresh_session(
        refresh_token: str,
        username: str,
    ) -> dict:
        username = username.strip()
        try:
            result = await asyncio.to_thread(
                cognito.initiate_auth,
                ClientId=settings.cognito_client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token,
                    "SECRET_HASH": calculate_secret_hash(username),
                },
            )

            tokens = result.get("AuthenticationResult")

            if not tokens or not tokens.get("AccessToken"):
                raise RuntimeError(
                    "Cognito did not return a refreshed access token."
                )

            return {
                "access_token": tokens["AccessToken"],
                "id_token": tokens.get("IdToken"),
                "expires_in": tokens["ExpiresIn"],
                "token_type": tokens.get("TokenType", "Bearer"),
            }

        except ClientError as exc:
            error = exc.response.get("Error", {})

            print("Cognito refresh error code:", error.get("Code"))
            print("Cognito refresh error message:", error.get("Message"))

            error_code = error.get("Code", "")

            if error_code in {
                "NotAuthorizedException",
                "UserNotFoundException",
            }:
                raise ValueError(
                    "The refresh token is invalid or expired."
                ) from exc

            if error_code in {
                "TooManyRequestsException",
                "LimitExceededException",
            }:
                raise ValueError(
                    "Too many refresh attempts. Try again later."
                ) from exc

            raise RuntimeError(
                "Cognito session refresh failed."
            ) from exc

    @staticmethod
    async def logout(access_token: str) -> dict:
        try:
            await asyncio.to_thread(
                cognito.global_sign_out,
                AccessToken=access_token,
            )

            return {
                "success": True,
                "message": "Logged out successfully.",
            }

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")

            if error_code in {
                "NotAuthorizedException",
                "InvalidParameterException",
            }:
                raise ValueError(
                    "The access token is invalid or expired."
                ) from exc

            if error_code in {
                "TooManyRequestsException",
                "LimitExceededException",
            }:
                raise ValueError(
                    "Too many logout attempts. Try again later."
                ) from exc

            raise RuntimeError(
                "Cognito logout failed."
            ) from exc
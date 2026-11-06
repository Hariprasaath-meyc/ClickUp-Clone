
import asyncio
import base64
import hashlib
import hmac
from datetime import datetime, timezone
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
import boto3
from botocore.exceptions import ClientError
import logging
from datetime import datetime, timezone, timedelta
from app.modules.users.models import User
from app.core.config import settings
from app.modules.auth.cognito import (
    get_cognito_client,
    refresh_cognito_session,
)
from app.modules.users.repository import UserRepository



logger = logging.getLogger(__name__)

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
        display_name: str,
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
                    {"Name": "name", "Value": display_name},
                ],
            )

            return {
                "user_id": result["UserSub"],
                "email": email,
                "display_name": display_name,
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
                raise ValueError(messages[code]) from None

            raise RuntimeError("Cognito signup failed.") from exc
    
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

            delivery = result.get("CodeDeliveryDetails", {})

            return {
                "confirmation_required": True,
                "message": "A new confirmation code was requested.",
                "delivery": {
                    "destination": delivery.get("Destination"),
                    "delivery_medium": delivery.get("DeliveryMedium"),
                    "attribute_name": delivery.get("AttributeName"),
                },
            }

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")

            messages = {
                "UserNotFoundException": "The account was not found.",
                "NotAuthorizedException": "The confirmation code cannot be resent for this account.",
                "TooManyRequestsException": "Too many requests. Please try again later.",
                "LimitExceededException": "The resend limit has been reached. Try again later.",
            }

            if error_code in messages:
                raise ValueError(messages[error_code]) from None

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
            logger.warning(
                "Cognito login rejected | error_code=%s",
                error_code,
            )

            if error_code in {
                "NotAuthorizedException",
                "UserNotFoundException",
            }:
                raise ValueError(
                    "Invalid email or password."
                ) from None

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
    ) -> dict:

        try:
            result = await asyncio.to_thread(
                refresh_cognito_session,
                refresh_token,
            )

            if not result:
                raise RuntimeError(
                    "Cognito returned an empty authentication result."
                )

            return {
                "access_token": result["AccessToken"],
                "id_token": result.get("IdToken"),
                "expires_in": result["ExpiresIn"],
                "token_type": result["TokenType"],
                "refresh_token": result.get("RefreshToken"),
            }

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")

            if error_code in {
                "NotAuthorizedException",
                "InvalidParameterException",
            }:
                raise ValueError(
                    "Your session has expired or been revoked. Please log in again."
                ) from None

            raise RuntimeError(
                "Unable to refresh your session. Please try again later."
            ) from exc
        
    @staticmethod
    async def logout(
        db: AsyncSession,
        user: User,
        access_token: str,
    ) -> dict:

        try:
            await asyncio.to_thread(
                cognito.global_sign_out,
                AccessToken=access_token,
            )

            user.tokens_valid_after = (
                datetime.now(timezone.utc).replace(microsecond=0)
                + timedelta(seconds=1)
            )

            await db.commit()

            return {
                "success": True,
                "message": "Logged out successfully.",
            }

        except ClientError as exc:
            await db.rollback()

            error_code = exc.response.get("Error", {}).get("Code", "")

            if error_code in {
                "NotAuthorizedException",
                "InvalidParameterException",
            }:
                raise ValueError(
                    "The access token is invalid or expired."
                ) from None

            if error_code in {
                "TooManyRequestsException",
                "LimitExceededException",
            }:
                raise ValueError(
                    "Too many logout attempts. Try again later."
                ) from None

            raise RuntimeError("Cognito logout failed.") from exc

        except Exception:
            await db.rollback()
            raise

        
    @staticmethod
    async def get_authenticated_identity(
        access_token: str,
    ) -> dict:
        try:
            result = await asyncio.to_thread(
                cognito.get_user,
                AccessToken=access_token,
            )

            attributes = {
                item["Name"]: item["Value"]
                for item in result.get("UserAttributes", [])
            }

            if attributes.get("email_verified") != "true":
                raise ValueError(
                    "Please verify your email before continuing."
                )

            return {
                "cognito_sub": attributes["sub"],
                "email": attributes["email"],
                "display_name": attributes.get("name", ""),
            }

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")

            if error_code in {
                "NotAuthorizedException",
                "UserNotFoundException",
            }:
                raise ValueError(
                    "Your authentication session is invalid or expired."
                ) from exc

            raise RuntimeError(
                "Unable to verify the Cognito identity."
            ) from exc
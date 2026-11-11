import strawberry
from graphql import GraphQLError
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.types import Info

from app.modules.auth.authorization import require_authenticated_user
from app.modules.auth.schemas.inputs import (
    ConfirmSignupInput,SignupInput,
)

from app.modules.auth.service import AuthService
from app.modules.auth.types import (
    CodeDeliveryDetails,
    LoginResult,
    LogoutResult,
    RefreshSessionResult,
    SignupResult,
)
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService

email_validator = TypeAdapter(EmailStr)

@strawberry.type
class AuthMutation:
    @strawberry.mutation
    async def signup(
        self,
        email: str,
        password: str,
        display_name: str,
    ) -> SignupResult:

        try:
            payload = SignupInput(
                email=email,
                password=password,
                display_name=display_name,
            )

            result = await AuthService.signup(
                email=str(payload.email),
                password=payload.password,
                display_name=payload.display_name,
            )

            return SignupResult(
                confirmation_required=not result["confirmed"],
                message=(
                    "Signup successful. Please verify your email."
                    if not result["confirmed"]
                    else "Signup successful."
                ),
            )

        except ValidationError as exc:
            error = exc.errors()[0]
            field = error["loc"][0]
            error_type = error["type"]

            messages = {
                ("email", "value_error"): (
                    "Please provide a valid email address."
                ),
                ("password", "string_too_short"): (
                    "Password cannot be empty."
                ),
                ("display_name", "string_too_short"): (
                    "Display name cannot be empty."
                ),
                ("display_name", "string_too_long"): (
                    "Display name cannot exceed 100 characters."
                ),
            }

            message = messages.get(
                (field, error_type),
                "Invalid signup information.",
            )

            raise GraphQLError(message) from exc

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

    # Confirm Signup Mutation
    @strawberry.mutation
    async def confirm_signup(
        self,
        email: str,
        confirmation_code: str,
    ) -> SignupResult:

        try:
            payload = ConfirmSignupInput(
                email=email,
                confirmation_code=confirmation_code,
            )

            result = await AuthService.confirm_signup(
                email=str(payload.email),
                confirmation_code=payload.confirmation_code,
            )

            return SignupResult(
                confirmation_required=not result["success"],
                message=result["message"],
            )

        except ValidationError as exc:
            error = exc.errors()[0]
            field = error["loc"][0]

            messages = {
                "email": "Please provide a valid email address.",
                "confirmation_code": "Confirmation code cannot be empty.",
            }

            raise GraphQLError(
                messages.get(field, "Invalid input provided.")
            ) from exc

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

    # Resend Confirmation Code Mutation
    @strawberry.mutation
    async def resend_confirmation_code(
        self,
        info: Info,
        email: str,
    ) -> SignupResult:

        try:
            validated_email = str(email_validator.validate_python(email))

            result = await AuthService.resend_confirmation_code(
                email=validated_email,
            )

            return SignupResult(
                confirmation_required=True,
                message=result["message"],
                delivery=(
                    CodeDeliveryDetails(**result["delivery"])
                    if result.get("delivery")
                    else None
                ),
            )

        except ValidationError as exc:
            raise GraphQLError("Invalid email address.") from exc

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

    # Login Mutation
    @strawberry.mutation
    async def login(
        self,
        info: Info,
        email: str,
        password: str,
    ) -> LoginResult:

        db: AsyncSession = info.context["db"]

        try:
            validated_email = str(email_validator.validate_python(email))

            # Step 1: Authenticate with Cognito.
            result = await AuthService.login(
                email=validated_email,
                password=password,
            )

            # Step 2: Retrieve verified identity from Cognito.
            identity = await AuthService.get_authenticated_identity(
                access_token=result["access_token"],
            )

            # Step 3: Create or retrieve the local PostgreSQL user.
            await UserService.create_from_cognito(
                db,
                cognito_sub=identity["cognito_sub"],
                email=identity["email"],
                display_name=identity["display_name"],
            )

            # Step 4: Commit local database changes.
            await db.commit()

            return LoginResult(**result)

        except ValidationError as exc:
            await db.rollback()
            raise GraphQLError("Invalid email address.") from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception:
            await db.rollback()
            raise

    # Refresh Session Mutation
    @strawberry.mutation
    async def refresh_session(
        self,
        info: Info,
        refresh_token: str,
    ) -> RefreshSessionResult:

        try:
            result = await AuthService.refresh_session(
                refresh_token=refresh_token,
            )

            return RefreshSessionResult(**result)

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

    # Logout Mutation
    @strawberry.mutation
    async def logout(
        self,
        info: Info,
    ) -> LogoutResult:

        db = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            access_token = info.context.get("access_token")

            if not access_token:
                raise GraphQLError("Access token not found.")

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User not found.")

            result = await AuthService.logout(
                db=db,
                user=user,
                access_token=access_token,
            )

            return LogoutResult(**result)

        except GraphQLError:
            raise

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

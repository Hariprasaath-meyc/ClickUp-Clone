
from multiprocessing.pool import MapResult

import strawberry
from graphql import GraphQLError
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.auth.service import AuthService
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


email_validator = TypeAdapter(EmailStr)


#Class for the result of the me query
@strawberry.type
class MeResult:
    id: strawberry.ID
    email: str
    display_name: str

    
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "ClickUp Clone GraphQL API is running"

    @strawberry.field
    async def me(
    self,
    info: strawberry.Info,
    ) -> MeResult:
        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError(
                "No application profile exists for this account."
            )

        return MeResult(
            id=strawberry.ID(str(user.id)),
            email=user.email,
            display_name=user.display_name,
        )

#Class for the result of the signup mutation
@strawberry.type
class SignupResult:
    profile_id: strawberry.ID
    confirmation_required: bool
    message: str

#Class for the result of the login mutation
@strawberry.type
class LoginResult:
    access_token: str
    id_token: str
    refresh_token: str | None
    expires_in: int
    token_type: str








@strawberry.type
class Mutation:
    @strawberry.mutation
    async def signup(
        self,
        info: strawberry.Info,
        name: str,
        email: str,
        password: str,
    ) -> SignupResult:
        name = name.strip()

        if not name or len(name) > 100:
            raise GraphQLError("Name must be between 1 and 100 characters.")

        try:
            email = str(email_validator.validate_python(email))
        except ValidationError as exc:
            raise GraphQLError("Enter a valid email address.") from exc

        if len(password) < 8 or len(password) > 256:
            raise GraphQLError(
                "Password must be between 8 and 256 characters."
            )

        db: AsyncSession = info.context["db"]

        try:
            identity = await AuthService.signup(
                name=name,
                email=email,
                password=password,
            )
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        except RuntimeError as exc:
            raise GraphQLError(
                "Signup could not be completed. Please try again later."
            ) from exc

        try:
            profile = await UserService.create_from_cognito(
                db,
                cognito_sub=identity["user_id"],
                email=identity["email"],
                display_name=identity["name"],
            )
        except ValueError as exc:
            # Cognito may already have created the identity.
            # Do not claim that the complete signup succeeded.
            raise GraphQLError(
                "The identity was created, but the user profile could not be saved. "
                "Please contact support."
            ) from exc

        return SignupResult(
            profile_id=strawberry.ID(str(profile.id)),
            confirmation_required=not identity["confirmed"],
            message=(
                "Signup successful. Check your email for the confirmation code."
                if not identity["confirmed"]
                else "Signup successful."
            ),
        )
    
    @strawberry.mutation
    async def confirm_signup(
        self,
        email: str,
        confirmation_code: str,
    ) -> str:
        try:
            result = await AuthService.confirm_signup(
                email=email,
                confirmation_code=confirmation_code,
            )
            return result["message"]

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

        except RuntimeError as exc:
            raise GraphQLError(
                "Confirmation could not be completed."
            ) from exc
    
    @strawberry.mutation
    async def resend_confirmation_code(self, email: str) -> str:
        try:
            result = await AuthService.resend_confirmation_code(email)
            return result["message"]
        except RuntimeError as exc:
            raise GraphQLError(
                "Could not resend confirmation code. Check the server logs."
            ) from exc

    @strawberry.mutation
    async def login(
        self,
        email: str,
        password: str,
    ) -> LoginResult:
        try:
            result = await AuthService.login(
                email=email,
                password=password,
            )

            return LoginResult(**result)

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

        except RuntimeError as exc:
            raise GraphQLError(
                "Unable to complete login."
            ) from exc




schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)

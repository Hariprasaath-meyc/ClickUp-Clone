
from datetime import datetime
from uuid import UUID
from sqlalchemy import select
import strawberry
from graphql import GraphQLError
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.modules.auth.authorization import require_authenticated_user
from app.modules.auth.service import AuthService
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService
from app.modules.users.types import UpdateMyProfileInput
from app.modules.workspaces.models import Workspace, WorkspaceMember
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.service import create_workspace
from app.modules.workspaces.types import SlugAvailabilityType, UpdateWorkspaceInput, WorkspaceType


email_validator = TypeAdapter(EmailStr)


# --------------------------------------------------
# GraphQL input types
# --------------------------------------------------

@strawberry.input
class CreateWorkspaceInput:
    name: str
    slug: str

# --------------------------------------------------
# GraphQL result types
# --------------------------------------------------

@strawberry.type
class UserProfileResult:
    display_name: str
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class MeResult:
    id: strawberry.ID
    email: str
    profile: UserProfileResult


@strawberry.type
class SignupResult:
    # profile_id: strawberry.ID
    confirmation_required: bool
    message: str


@strawberry.type
class LoginResult:
    access_token: str
    id_token: str
    refresh_token: str | None
    expires_in: int
    token_type: str


@strawberry.type
class RefreshSessionResult:
    access_token: str
    id_token: str | None
    expires_in: int
    token_type: str


@strawberry.type
class LogoutResult:
    success: bool
    message: str



@strawberry.type
class WorkspaceResult:
    id: strawberry.ID
    name: str
    slug: str
    created_by: strawberry.ID
    created_at: datetime

# --------------------------------------------------
# Query
# --------------------------------------------------

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

        profile = await UserRepository.get_profile_by_user_id(
            db,
            user.id,
        )

        if profile is None:
            raise GraphQLError(
                "User profile not found."
            )

        return MeResult(
            id=strawberry.ID(str(user.id)),
            email=user.email,
            profile=UserProfileResult(
                display_name=profile.display_name,
                avatar_url=profile.avatar_url,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            ),
        )
    
    @strawberry.field
    async def my_workspaces(
        self,
        info: strawberry.Info,
    ) -> list[WorkspaceType]:
        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        workspaces = await WorkspaceRepository.get_user_workspaces(
            db=db,
            user_id=user.id,
        )

        return [
            WorkspaceType(
                id=strawberry.ID(str(workspace.id)),
                name=workspace.name,
                slug=workspace.slug,
                created_by=strawberry.ID(str(workspace.created_by)),
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
            )
            for workspace in workspaces
        ]

    @strawberry.field
    async def get_workspace(
        self,
        info: strawberry.Info,
        id: strawberry.ID,
    ) -> WorkspaceType:
        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        try:
            workspace_id = UUID(str(id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace ID.") from exc

        workspace = await WorkspaceRepository.get_by_id(
            db=db,
            workspace_id=workspace_id,
        )

        if workspace is None:
            raise GraphQLError("Workspace not found.")

        # Verify that the user belongs to this workspace.
        membership_result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
        )

        membership = membership_result.scalar_one_or_none()

        if membership is None:
            raise GraphQLError(
                "You do not have access to this workspace."
            )

        return WorkspaceType(
            id=strawberry.ID(str(workspace.id)),
            name=workspace.name,
            slug=workspace.slug,
            created_by=strawberry.ID(str(workspace.created_by)),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    @strawberry.field
    async def check_slug_availability(
        self,
        info: strawberry.Info,
        slug: str,
    ) -> SlugAvailabilityType:
        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]

        # Ensure the requester is authenticated.
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError(
                "User not found. Please log in again."
            )

        normalized_slug = slug.strip().lower()

        if not normalized_slug or len(normalized_slug) > 100:
            raise GraphQLError(
                "Slug must be between 1 and 100 characters."
            )

        is_taken = await WorkspaceRepository.is_slug_taken(
            db=db,
            slug=normalized_slug,
        )

        return SlugAvailabilityType(
            slug=normalized_slug,
            available=not is_taken,
        )
    
    @strawberry.field
    async def get_workspace_by_slug(
        self,
        info: strawberry.Info,
        slug: str,
    ) -> WorkspaceType:
        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError(
                "User not found. Please log in again."
            )

        normalized_slug = slug.strip().lower()

        if not normalized_slug or len(normalized_slug) > 100:
            raise GraphQLError(
                "Slug must be between 1 and 100 characters."
            )

        workspace = await WorkspaceRepository.get_by_slug(
            db=db,
            slug=normalized_slug,
        )

        if workspace is None:
            raise GraphQLError("Workspace not found.")

        membership_result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
        )

        if membership_result.scalar_one_or_none() is None:
            raise GraphQLError(
                "You do not have access to this workspace."
            )

        return WorkspaceType(
            id=strawberry.ID(str(workspace.id)),
            name=workspace.name,
            slug=workspace.slug,
            created_by=strawberry.ID(str(workspace.created_by)),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
# --------------------------------------------------
# Mutation
# --------------------------------------------------

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
        email = email.strip()

        if not name or len(name) > 100:
            raise GraphQLError(
                "Name must be between 1 and 100 characters."
            )

        try:
            email = str(
                email_validator.validate_python(email)
            )
        except ValidationError as exc:
            raise GraphQLError(
                "Enter a valid email address."
            ) from exc

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

        # try:
        #     profile = await UserService.create_from_cognito(
        #         db,
        #         cognito_sub=identity["user_id"],
        #         email=identity["email"],
        #         display_name=identity["name"],
        #     )
        # except ValueError as exc:
        #     raise GraphQLError(
        #         "The identity was created, but the user profile "
        #         "could not be saved. Please contact support."
        #     ) from exc

        return SignupResult(
    confirmation_required=not identity["confirmed"],
    message=(
        "Signup successful. Check your email for "
        "the confirmation code."
        if not identity["confirmed"]
        else "Signup successful. You can now log in."
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
    async def resend_confirmation_code(
        self,
        email: str,
    ) -> str:
        try:
            result = await AuthService.resend_confirmation_code(
                email
            )
            return result["message"]

        except RuntimeError as exc:
            raise GraphQLError(
                "Could not resend confirmation code. "
                "Check the server logs."
            ) from exc

    @strawberry.mutation
    async def login(
        self,
        info: strawberry.Info,
        email: str,
        password: str,
    ) -> LoginResult:
        db: AsyncSession = info.context["db"]

        try:
            # 1. Authenticate with Cognito.
            result = await AuthService.login(
                email=email,
                password=password,
            )

            # 2. Retrieve identity attributes using the access token.
            identity = await AuthService.get_authenticated_identity(
                access_token=result["access_token"],
            )

            # 3. Create the local user/profile if needed,
            # or retrieve the existing user.
            await UserService.create_from_cognito(
                db,
                cognito_sub=identity["cognito_sub"],
                email=identity["email"],
                display_name=identity["display_name"],
            )

            # 4. Return the Cognito tokens.
            return LoginResult(**result)

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

        except RuntimeError as exc:
            raise GraphQLError(
                "Unable to complete login."
            ) from exc

        
    @strawberry.mutation
    async def update_my_profile(
        self,
        info: strawberry.Info,
        input: UpdateMyProfileInput,
    ) -> UserProfileResult:
        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found.")

        profile = await UserRepository.get_profile_by_user_id(
            db,
            user.id,
        )

        if profile is None:
            raise GraphQLError("User profile not found.")

        if input.display_name is not None:
            display_name = input.display_name.strip()

            if not display_name:
                raise GraphQLError(
                    "Display name cannot be empty."
                )

            if len(display_name) > 100:
                raise GraphQLError(
                    "Display name cannot exceed 100 characters."
                )

            profile.display_name = display_name

        if input.avatar_url is not None:
            profile.avatar_url = input.avatar_url

        await db.commit()
        await db.refresh(profile)

        return UserProfileResult(
            display_name=profile.display_name,
            avatar_url=profile.avatar_url,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    @strawberry.mutation
    async def refresh_session(
        self,
        refresh_token: str,
        cognito_sub: str,
    ) -> RefreshSessionResult:
        try:
            result = await AuthService.refresh_session(
                refresh_token=refresh_token,
                username=cognito_sub,
            )

            return RefreshSessionResult(**result)

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

        except RuntimeError as exc:
            raise GraphQLError(
                "Unable to refresh the session."
            ) from exc

    @strawberry.mutation
    async def logout(
        self,
        info: strawberry.Info,
    ) -> LogoutResult:
        # Confirm that the request is authenticated.
        require_authenticated_user(info)

        # Get the verified request's access token.
        access_token = info.context.get("access_token")

        if not access_token:
            raise GraphQLError(
                "Access token is missing from the request context."
            )

        try:
            result = await AuthService.logout(
                access_token=access_token,
            )

            return LogoutResult(**result)

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

        except RuntimeError as exc:
            raise GraphQLError(
                "Unable to complete logout."
            ) from exc

    @strawberry.mutation
    async def create_workspace(
        self,
        info: strawberry.Info,
        input: CreateWorkspaceInput,
    ) -> WorkspaceResult:
        # 1. Verify the request is authenticated.
        claims = require_authenticated_user(info)

        # 2. Get the database session.
        db: AsyncSession = info.context["db"]

        # 3. Find the application user using the verified Cognito subject.
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError(
                "User not found. Please log in again."
            )

        # 4. Validate workspace input.
        name = input.name.strip()
        slug = input.slug.strip().lower()

        if not name or len(name) > 100:
            raise GraphQLError(
                "Workspace name must be between 1 and 100 characters."
            )

        if not slug or len(slug) > 100:
            raise GraphQLError(
                "Workspace slug must be between 1 and 100 characters."
            )

        # 5. Create the workspace and its RBAC records.
        try:
            workspace = await create_workspace(
                db=db,
                user_id=user.id,
                name=name,
                slug=slug,
            )

            await db.commit()

            return WorkspaceResult(
                id=strawberry.ID(str(workspace.id)),
                name=workspace.name,
                slug=workspace.slug,
                created_by=strawberry.ID(str(workspace.created_by)),
                created_at=workspace.created_at,
            )

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError(
                "The workspace could not be created. The slug may already be in use."
            ) from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception:
            await db.rollback()
            raise

    @strawberry.mutation
    async def update_workspace(
        self,
        info: strawberry.Info,
        input: UpdateWorkspaceInput,
    ) -> WorkspaceType:
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        try:
            workspace_id = UUID(str(input.id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace ID.") from exc

        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()

        if workspace is None:
            raise GraphQLError("Workspace not found.")

        membership_result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
        )

        if membership_result.scalar_one_or_none() is None:
            raise GraphQLError(
                "You do not have access to this workspace."
            )

        name = input.name.strip() if input.name is not None else None
        slug = input.slug.strip().lower() if input.slug is not None else None

        if name is not None and not 1 <= len(name) <= 100:
            raise GraphQLError(
                "Workspace name must be between 1 and 100 characters."
            )

        if slug is not None and not 1 <= len(slug) <= 100:
            raise GraphQLError(
                "Workspace slug must be between 1 and 100 characters."
            )

        if name is None and slug is None:
            raise GraphQLError(
                "Provide at least one field to update."
            )

        try:
            workspace = await WorkspaceRepository.update(
                db,
                workspace,
                name=name,
                slug=slug,
            )

            await db.commit()

            return WorkspaceType(
                id=strawberry.ID(str(workspace.id)),
                name=workspace.name,
                slug=workspace.slug,
                created_by=strawberry.ID(str(workspace.created_by)),
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
            )

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to update workspace. The slug may already be in use."
            ) from exc

        except Exception:
            await db.rollback()
            raise
# --------------------------------------------------
# Schema registration
# --------------------------------------------------

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)

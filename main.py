
import logging
from contextlib import asynccontextmanager

import jwt
from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging.config import setup_logging
from app.core.middleware.request_logging import RequestLoggingMiddleware
from app.db.session import engine, get_db
from app.graphql.error_handler import CentralizedGraphQLRouter
from app.graphql.schema import schema
from app.modules.auth.token_service import verify_access_token


# Configure logging before application initialization.
setup_logging()

logger = logging.getLogger(__name__)


# Verify the Cognito access token.
async def get_authenticated_claims(
    request: Request,
) -> dict | None:

    authorization = request.headers.get("Authorization")

    if not authorization:
        return None

    scheme, separator, token = authorization.partition(" ")

    if (
        scheme.lower() != "bearer"
        or not separator
        or not token
    ):
        return None

    try:
        return await verify_access_token(token)

    except (jwt.InvalidTokenError, jwt.PyJWKClientError):
        return None


# Build the GraphQL request context.
async def get_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:

    authorization = request.headers.get("Authorization")
    access_token = None

    if authorization:
        scheme, separator, token = authorization.partition(" ")

        if (
            scheme.lower() == "bearer"
            and separator
            and token
        ):
            access_token = token

    claims = await get_authenticated_claims(request)

    return {
        "db": db,
        "current_user": claims,
        "access_token": access_token,
    }


# Application lifespan.
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization"
    ],
)

# Register request logging middleware.
app.add_middleware(RequestLoggingMiddleware)


# Register centralized GraphQL error handling.
graphql_app = CentralizedGraphQLRouter(
    schema,
    context_getter=get_context,
)

app.include_router(
    graphql_app,
    prefix="/graphql",
)


# Health check endpoint.
@app.get("/health")
async def health_check():
    return {"status": "ok"}

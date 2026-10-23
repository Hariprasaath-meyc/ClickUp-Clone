from contextlib import asynccontextmanager
from urllib import request

from fastapi import Depends, FastAPI, Request
from graphql import GraphQLError
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import GraphQLRouter

from app.core.config import settings
from app.db.session import engine, get_db
from app.graphql.schema import schema
from app.modules.auth.token_service import verify_access_token


async def get_authenticated_claims(
    request: Request,
) -> dict | None:
    authorization = request.headers.get(
        "Authorization"
    )

    if not authorization:
        return None

    scheme, separator, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not separator or not token:
        raise GraphQLError(
            "Invalid Authorization header."
        )

    try:
        return await verify_access_token(token)
    except (jwt.InvalidTokenError, jwt.PyJWKClientError):
        raise GraphQLError(
            "Invalid or expired access token."
        )
    


async def get_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    claims = await get_authenticated_claims(request)
    return {"db": db,
             "current_user": claims,}

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
)

app.include_router(
    graphql_app,
    prefix="/graphql",
)

@app.get("/health")
def health_check():
    return {"status": "ok"}



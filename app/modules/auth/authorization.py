
from typing import Any

from graphql import GraphQLError


def require_authenticated_user(
    info: Any,
) -> dict:
    current_user = info.context.get("current_user")

    if not current_user:
        raise GraphQLError(
            "Authentication required. Please log in."
        )

    return current_user

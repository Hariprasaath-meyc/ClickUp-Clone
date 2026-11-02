import logging

from fastapi import Request
from strawberry.fastapi import GraphQLRouter
from strawberry.http import GraphQLHTTPResponse
from strawberry.types import ExecutionResult

logger = logging.getLogger(__name__)


class CentralizedGraphQLRouter(GraphQLRouter):

    async def process_result(
        self,
        request: Request,
        result: ExecutionResult,
    ) -> GraphQLHTTPResponse:

        request_id = getattr(
            request.state,
            "request_id",
            "-",
        )

        response: GraphQLHTTPResponse = {
            "data": result.data,
        }

        if result.errors:

            formatted_errors = []

            for error in result.errors:

                original_error = error.original_error

                if original_error is not None:

                    logger.error(
                        "Unexpected GraphQL execution error | "
                        "request_id=%s | path=%s",
                        request_id,
                        error.path,
                        exc_info=(
                            type(original_error),
                            original_error,
                            original_error.__traceback__,
                        ),
                    )

                    formatted_error = {
                        "message": "Internal server error",
                    }

                    if error.locations:
                        formatted_error["locations"] = [
                            {
                                "line": loc.line,
                                "column": loc.column,
                            }
                            for loc in error.locations
                        ]

                    if error.path:
                        formatted_error["path"] = error.path

                    formatted_error["extensions"] = {
                        "code": "INTERNAL_SERVER_ERROR",
                        "requestId": request_id,
                    }

                else:

                    # Expected GraphQL errors and validation errors.
                    formatted_error = error.formatted.copy()

                    extensions = dict(
                        formatted_error.get("extensions") or {}
                    )

                    extensions["requestId"] = request_id

                    formatted_error["extensions"] = extensions

                formatted_errors.append(formatted_error)

            response["errors"] = formatted_errors

        return response
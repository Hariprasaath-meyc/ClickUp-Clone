import logging
import time
import uuid

from app.core.logging.context import request_id_ctx

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())

        token = request_id_ctx.set(request_id)

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        start_time = time.perf_counter()

        async def send_with_request_id(message):

            if message["type"] == "http.response.start":
                # Avoid duplicate request ID headers.
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ]
                headers.append(
                    (
                        b"x-request-id",
                        request_id.encode("utf-8"),
                    )
                )

                message["headers"] = headers

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_with_request_id,
            )

        except Exception:
            logger.exception("Unhandled HTTP application exception")

            raise

        finally:
            duration = (time.perf_counter() - start_time) * 1000

            logger.info(
                "HTTP request completed | method=%s | path=%s | duration=%.2fms",
                scope["method"],
                scope["path"],
                duration,
            )

            request_id_ctx.reset(token)

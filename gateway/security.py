"""Shared development-only bearer boundary for gateway and reference adapter.

No OAuth, rate limit, TLS termination, per-user access control or public ingress
security is implied. Authenticated HTTP requests are bounded to 1 MiB.
"""

import hmac
import os
from fastapi.responses import JSONResponse

# Bound authenticated HTTP request bodies before FastAPI decodes JSON or loads
# optional experimental handlers. This is a local resource limit, not a rate
# limiter, reverse proxy, or production DoS defense.
MAX_GATEWAY_BODY_BYTES = 1024 * 1024


class GatewayAuthMiddleware:
    """Small fail-closed development bearer-token boundary for HTTP and WS.

    Only the static public homepage (GET /) is unauthenticated. This protects
    both declared HTTP routes and any optional, dynamically added endpoints.
    The token must be provisioned outside the repository. This is not OAuth,
    RBAC, session authentication, or evidence of production-ready security.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope_type = scope.get("type")
        if scope_type not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        if (
            scope_type == "http"
            and scope.get("path") == "/"
            and scope.get("method") == "GET"
        ):
            return await self.app(scope, receive, send)

        token = os.environ.get("LRS_GATEWAY_API_TOKEN", "")
        # Long tokens reduce accidental use of short demo credentials. Refuse
        # to serve non-public routes with unset/weak configuration.
        configured = (
            32 <= len(token) <= 512
            and token.isascii()
            and not any(c.isspace() for c in token)
        )
        if not configured:
            if scope_type == "websocket":
                await send({"type": "websocket.close", "code": 1013})
            else:
                response = JSONResponse(
                    {"detail": "Gateway authentication is not configured"},
                    status_code=503,
                    headers={"Cache-Control": "no-store"},
                )
                await response(scope, receive, send)
            return

        supplied = [
            value for name, value in scope.get("headers", [])
            if name.lower() == b"authorization"
        ]
        expected = b"Bearer " + token.encode("ascii")
        authorized = len(supplied) == 1 and hmac.compare_digest(
            supplied[0], expected
        )
        if not authorized:
            if scope_type == "websocket":
                await send({"type": "websocket.close", "code": 4401})
            else:
                response = JSONResponse(
                    {"detail": "Bearer token required"},
                    status_code=401,
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "Cache-Control": "no-store",
                    },
                )
                await response(scope, receive, send)
            return
        if scope_type == "http":
            # Authenticate first so unauthenticated traffic cannot force body
            # buffering. Enforce both declared size and streamed bytes; chunked
            # requests must not bypass the limit.
            lengths = [
                value for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ]
            if len(lengths) > 1:
                response = JSONResponse(
                    {"detail": "Invalid Content-Length headers"},
                    status_code=400, headers={"Cache-Control": "no-store"},
                )
                await response(scope, receive, send)
                return
            if lengths:
                try:
                    declared = int(lengths[0].decode("ascii"))
                    if declared < 0:
                        raise ValueError("negative length")
                except (UnicodeDecodeError, ValueError):
                    response = JSONResponse(
                        {"detail": "Invalid Content-Length"},
                        status_code=400, headers={"Cache-Control": "no-store"},
                    )
                    await response(scope, receive, send)
                    return
                if declared > MAX_GATEWAY_BODY_BYTES:
                    response = JSONResponse(
                        {"detail": "Gateway request body limit exceeded"},
                        status_code=413, headers={"Cache-Control": "no-store"},
                    )
                    await response(scope, receive, send)
                    return

            chunks = []
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    continue
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > MAX_GATEWAY_BODY_BYTES:
                    response = JSONResponse(
                        {"detail": "Gateway request body limit exceeded"},
                        status_code=413, headers={"Cache-Control": "no-store"},
                    )
                    await response(scope, receive, send)
                    return
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break

            # Replay the bounded body exactly once to the existing ASGI app;
            # later receive calls retain disconnect semantics.
            body = b"".join(chunks)
            replayed = False

            async def replay_receive():
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            return await self.app(scope, replay_receive, send)

        return await self.app(scope, receive, send)



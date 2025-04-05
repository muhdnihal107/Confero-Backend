# rooms/middleware.py
import jwt
import logging
from django.conf import settings
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs
from types import SimpleNamespace

logger = logging.getLogger(__name__)

async def get_user(user_id):
    if user_id:
        return SimpleNamespace(id=user_id, is_authenticated=True, is_anonymous=False)
    return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)

        token = params.get("token", [None])[0]  # Extract token safely
        if token:
            logger.info("Extracted token: %s", token)

            try:
                decoded_token = jwt.decode(
                    token,
                    settings.SIMPLE_JWT["SIGNING_KEY"],
                    algorithms=["HS256"]
                )
                logger.info("Decoded token: %s", decoded_token)

                user_id = decoded_token.get("user_id")
                if user_id:
                    scope["user"] = await get_user(user_id)
                else:
                    logger.warning("No user_id in token")
                    scope["user"] = AnonymousUser()

            except jwt.ExpiredSignatureError:
                logger.error("Token expired")
                scope["user"] = AnonymousUser()
            except jwt.InvalidTokenError as e:
                logger.error("Invalid token: %s", str(e))
                scope["user"] = AnonymousUser()
        else:
            logger.warning("No token provided")
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
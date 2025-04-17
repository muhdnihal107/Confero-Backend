# chat_service/chats/middleware.py
import jwt
import logging
from django.conf import settings
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs
from types import SimpleNamespace
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

@sync_to_async
def fetch_user_profile_from_token(token):
    """Extract user profile from JWT token."""
    try:
        decoded_token = jwt.decode(token, settings.SIMPLE_JWT["SIGNING_KEY"], algorithms=["HS256"])
        logger.info("Decoded token: %s", {k: v for k, v in decoded_token.items() if k != 'jti'})
        user_id = decoded_token.get("user_id")
        email = decoded_token.get("email")
        username = decoded_token.get("username")
        if user_id and email and username:
            return SimpleNamespace(
                id=user_id,
                email=email,
                username=username,
                is_authenticated=True,
                is_anonymous=False
            )
        else:
            logger.warning("Token missing required fields: user_id, email, or username")
            return None
    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.error("Invalid token: %s", str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error decoding token: %s", str(e))
        return None

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)

        token = params.get("token", [None])[0]
        if token:
            logger.info("Extracted token: %s", token[:20] + "..." if len(token) > 20 else token)
            try:
                user = await fetch_user_profile_from_token(token)
                if user and user.email:
                    scope["user"] = user
                else:
                    logger.warning("No valid user profile from token")
                    scope["user"] = AnonymousUser()
            except Exception as e:
                logger.error("Unexpected error processing token: %s", str(e))
                scope["user"] = AnonymousUser()
        else:
            logger.warning("No token provided")
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
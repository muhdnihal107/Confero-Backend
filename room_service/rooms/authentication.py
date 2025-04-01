# authentication.py
import logging
import jwt
from types import SimpleNamespace
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

logger = logging.getLogger("django")

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        logger.debug(f"Auth header: {auth_header}")

        if not auth_header or not auth_header.startswith("Bearer "):
            logger.debug("No valid Bearer token provided")
            return None

        token = auth_header.split(" ")[1]
        logger.debug(f"Token: {token}")

        try:
            decoded_token = jwt.decode(
                token,
                settings.SIMPLE_JWT['SIGNING_KEY'],
                algorithms=["HS256"]
            )
            logger.debug(f"Decoded token: {decoded_token}")

            user_id = decoded_token.get("user_id")
            if not user_id:
                logger.error("No user_id in token")
                raise AuthenticationFailed("Invalid token")

            user_data = {
                "id": user_id,
                "username": decoded_token.get("username"),
                "email": decoded_token.get("email"),
                "is_authenticated": True
            }
            user = SimpleNamespace(**user_data)
            logger.debug(f"User object: {vars(user)}")
            return user, None

        except jwt.ExpiredSignatureError:
            logger.error("Token expired")
            raise AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError:
            logger.error("Invalid token")
            raise AuthenticationFailed("Invalid token")
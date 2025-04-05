# rooms/authentication.py
import logging
import jwt
from types import SimpleNamespace
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)  # Changed to __name__ for consistency

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("No valid Authorization header")
            return None
        token = auth_header.split(" ")[1]
        logger.info("Token from Authorization header: %s", token)

        try:
            decoded_token = jwt.decode(
                token,
                settings.SIMPLE_JWT["SIGNING_KEY"],
                algorithms=["HS256"]
            )
            logger.info("Decoded token: %s", decoded_token)
            user_id = decoded_token.get("user_id")
            if not user_id:
                raise AuthenticationFailed("Invalid token")
            user_data = {
                "id": user_id,
                "username": decoded_token.get("username", ""),
                "email": decoded_token.get("email", ""),
                "is_authenticated": True
            }
            user = SimpleNamespace(**user_data)
            return user, None
        except jwt.ExpiredSignatureError:
            logger.error("Token expired")
            raise AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error("Invalid token: %s", str(e))
            raise AuthenticationFailed("Invalid token")
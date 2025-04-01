
import logging
import jwt  # PyJWT library
from types import SimpleNamespace

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger("django")

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return None  # No token provided, let DRF handle unauthenticated requests

        token = auth_header.split(" ")[1]  # Extract token from header

        try:
            # Decode JWT token locally
            decoded_token = jwt.decode(
                token,
                settings.SIMPLE_JWT['SIGNING_KEY'],  # Shared secret key
                algorithms=["HS256"]
            )
            
            user_id = decoded_token.get("user_id")
            if not user_id:
                raise AuthenticationFailed("Invalid token")

            # Create a dummy user object from decoded token data
            user_data = {
                "id": user_id,
                "username": decoded_token.get("username", ""),
                "email": decoded_token.get("email", ""),
                "is_authenticated": True
            }
            user = SimpleNamespace(**user_data)
            return user, None  # Return user object

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token")


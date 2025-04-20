# rooms/authentication/http_auth.py
import logging
import jwt
from types import SimpleNamespace
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

class CustomJWTAuthentication(BaseAuthentication):
    """
    JWT authentication for HTTP requests (REST API)
    """
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        
        # Check authorization header format
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("No valid Authorization header")
            return None
            
        token = auth_header.split(" ")[1]
        logger.debug("Token extracted from Authorization header")

        try:
            # Decode and verify JWT token
            decoded_token = jwt.decode(
                token,
                settings.SIMPLE_JWT["SIGNING_KEY"],
                algorithms=["HS256"]
            )
            logger.info("Token successfully decoded for user_id: %s", decoded_token.get("user_id"))
            
            # Validate required token fields
            user_id = decoded_token.get("user_id")
            if not user_id:
                raise AuthenticationFailed("Invalid token: missing user_id")
                
            # Create simple user object
            user_data = {
                "id": user_id,
                "username": decoded_token.get("username", ""),
                "email": decoded_token.get("email", ""),
                "is_authenticated": True,
                "is_anonymous": False
            }
            user = SimpleNamespace(**user_data)
            
            return user, None
            
        except jwt.ExpiredSignatureError:
            logger.error("Token expired")
            raise AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error("Invalid token: %s", str(e))
            raise AuthenticationFailed("Invalid token")
        except Exception as e:
            logger.error("Unexpected authentication error: %s", str(e))
            raise AuthenticationFailed("Authentication failed")
# import logging
# from types import SimpleNamespace
# import requests
# from django.conf import settings
# from rest_framework.exceptions import AuthenticationFailed
# from rest_framework_simplejwt.authentication import JWTAuthentication

# logger = logging.getLogger("django")

# class CustomJWTAuthentication(JWTAuthentication):
#     def get_user(self, validated_token):
#         user_id = validated_token.get("user_id")

#         if not user_id:
#             raise AuthenticationFailed("Invalid token")

#         user_service_url = f"{settings.AUTH_SERVICE_URL}auth/user-details/{user_id}/"

#         logger.info(f"Requesting user data from: {user_service_url}")

#         try:
#             response = requests.get(
#                 user_service_url, 
#                 headers={"Authorization": f"Bearer {str(validated_token)}"}
#             )

#             if response.status_code == 200:
#                 user_data = response.json()
#                 return SimpleNamespace(**user_data, is_authenticated=True)
#             else:
#                 raise AuthenticationFailed("User not found")

#         except requests.exceptions.RequestException:
#             logger.error(f"Error while contacting user service at: {user_service_url}")
#             raise AuthenticationFailed("User service unavailable")
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


# chat_service/chats/auth.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
from django.conf import settings
from types import SimpleNamespace

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, settings.SIMPLE_JWT['SIGNING_KEY'], algorithms=['HS256'])
            user_id = payload.get('user_id')
            email = payload.get('email')
            username = payload.get('username')
            if not (user_id and email and username):
                raise AuthenticationFailed('Invalid token payload')
            user = SimpleNamespace(
                id=user_id,
                email=email,
                username=username,
                is_authenticated=True,
                is_anonymous=False
            )
            return (user, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
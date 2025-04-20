# rooms/authentication/websocket_auth.py
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
def get_user_from_token(token):
    """
    Async function to validate JWT token and return user object
    """
    try:
        decoded_token = jwt.decode(
            token,
            settings.SIMPLE_JWT["SIGNING_KEY"],
            algorithms=["HS256"]
        )
        logger.debug("WebSocket token decoded successfully")
        
        # Validate required fields
        user_id = decoded_token.get("user_id")
        email = decoded_token.get("email")
        username = decoded_token.get("username")
        
        if not all([user_id, email, username]):
            logger.warning("Token missing required fields")
            return None
            
        return SimpleNamespace(
            id=user_id,
            email=email,
            username=username,
            is_authenticated=True,
            is_anonymous=False
        )
        
    except jwt.ExpiredSignatureError:
        logger.error("WebSocket token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.error("Invalid WebSocket token: %s", str(e))
        return None
    except Exception as e:
        logger.error("Unexpected WebSocket auth error: %s", str(e))
        return None

class WebSocketJWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for WebSocket connections
    """
    async def __call__(self, scope, receive, send):
        # Extract token from query string
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]
        
        if not token:
            logger.warning("No token provided in WebSocket connection")
            scope["user"] = AnonymousUser()
            return await self.inner(scope, receive, send)
            
        logger.debug("Processing WebSocket token")
        
        try:
            user = await get_user_from_token(token)
            if user:
                scope["user"] = user
                logger.info("WebSocket authenticated for user %s", user.id)
            else:
                scope["user"] = AnonymousUser()
                logger.warning("Invalid user from WebSocket token")
                
        except Exception as e:
            logger.error("WebSocket auth processing failed: %s", str(e))
            scope["user"] = AnonymousUser()
            
        return await self.inner(scope, receive, send)
        
    async def close_connection(self, scope, send, code, reason):
        """
        Properly close WebSocket connection with error code
        """
        if 'channel_layer' in scope and scope['channel_layer']:
            await scope['channel_layer'].group_discard(
                scope['channel_name'], 
                scope['channel_name']
            )
        await send({
            'type': 'websocket.close',
            'code': code,
            'reason': reason.encode('utf-8')
        })
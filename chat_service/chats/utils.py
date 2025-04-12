# chat_service/chats/utils.py
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def validate_user(email: str) -> bool:
    """
    Check if a user exists by querying auth_service.
    """
    try:
        response = requests.get(
            f"{settings.AUTH_SERVICE_URL}users/{email}/",
            headers={'Authorization': f'Bearer {settings.JWT_SIGNING_KEY}'},
            timeout=5
        )
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"Failed to validate user {email}: {e}")
        return False

def are_friends(email1: str, email2: str) -> bool:
    """
    Check if two users are friends by querying auth_service.
    """
    try:
        response = requests.get(
            f"{settings.AUTH_SERVICE_URL}friendships/check/",
            params={'user1': email1, 'user2': email2},
            headers={'Authorization': f'Bearer {settings.JWT_SIGNING_KEY}'},
            timeout=5
        )
        return response.status_code == 200 and response.json().get('are_friends', False)
    except requests.RequestException as e:
        logger.error(f"Failed to check friendship {email1} - {email2}: {e}")
        return False
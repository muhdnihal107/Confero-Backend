# auth_service/accounts/permissions.py
from rest_framework.permissions import IsAuthenticated, BasePermission

class CustomPermission(BasePermission):
    def has_permission(self, request, view):
        # Allow unauthenticated access to specific paths
        allowed_views = ['RegisterView', 'LoginView']
        if view.__class__.__name__ in allowed_views:
            return True  # Allow access without authentication
        # Otherwise, require authentication
        return IsAuthenticated().has_permission(request, view)
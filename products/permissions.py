from rest_framework.permissions import BasePermission

class IsStoreManager(BasePermission):
    """
    Allows access only to users in the 'Store Manager' group.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'is_store_manager') and request.user.is_store_manager()


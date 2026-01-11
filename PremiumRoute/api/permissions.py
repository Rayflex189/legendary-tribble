from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if the object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to all users, but write access only to staff.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to all users, but write access only to admins.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.user_type == 'admin'

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allow access to object owners or admin users.
    """
    
    def has_object_permission(self, request, view, obj):
        if request.user.user_type == 'admin':
            return True
        
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False
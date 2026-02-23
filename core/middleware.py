from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
from .models import TenantMembership


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware that enforces tenant isolation by:
    1. Extracting tenant context from user's membership
    2. Attaching tenant to request object
    3. Blocking access if user has no tenant membership
    """

    def process_request(self, request):
        # Skip tenant check for unauthenticated users, admin, healthz, and auth endpoints
        if not request.user.is_authenticated:
            return None

        if request.path.startswith('/admin/') or request.path == '/healthz' or request.path.startswith('/debug/'):
            return None

        # Superusers can access without tenant
        if request.user.is_superuser:
            request.tenant = None
            request.tenant_role = None
            return None

        # Get user's first active tenant membership
        try:
            membership = TenantMembership.objects.select_related('tenant').filter(
                user=request.user,
                tenant__is_active=True
            ).first()

            if membership:
                request.tenant = membership.tenant
                request.tenant_role = membership.role
                # Debug logging
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"User {request.user.email} - Tenant: {membership.tenant.name}, Role: {membership.role} (type: {type(membership.role)})")
            else:
                # User has no tenant membership
                request.tenant = None
                request.tenant_role = None
                return HttpResponseForbidden("You are not associated with any active tenant.")

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"TenantMiddleware error for user {request.user.email}: {e}")
            request.tenant = None
            request.tenant_role = None

        return None

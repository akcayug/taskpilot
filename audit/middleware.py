"""
Audit middleware for logging requests and changes.
"""
from django.utils.deprecation import MiddlewareMixin
from audit.models import AuditLog


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to audit critical actions.
    Logs are created via signals, but this middleware ensures
    request context is available for audit logging.
    """

    def process_request(self, request):
        """Store request start time for performance monitoring."""
        import time
        request._audit_start_time = time.time()

    def process_response(self, request, response):
        """Log response time if needed for monitoring."""
        # This middleware primarily ensures request context exists
        # Actual audit logging happens via signals in audit/signals.py
        return response

    def process_exception(self, request, exception):
        """Log exceptions for critical failures."""
        if request.user.is_authenticated:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action='ERROR',
                    resource_type='Request',
                    resource_id=0,
                    changes={
                        'path': request.path,
                        'method': request.method,
                        'exception': str(exception),
                        'exception_type': exception.__class__.__name__
                    }
                )
            except Exception:
                # Don't fail the request if audit logging fails
                pass

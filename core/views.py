from django.http import JsonResponse
from django.db import connection


def healthz(request):
    """
    Health check endpoint that verifies:
    1. Web service is running
    2. Database connectivity

    Returns 200 OK if healthy, 503 Service Unavailable if not
    """
    try:
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return JsonResponse({
            "status": "healthy",
            "database": "connected"
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status=503)

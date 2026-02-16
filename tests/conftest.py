import pytest
from django.conf import settings


@pytest.fixture(scope='session', autouse=True)
def django_test_settings():
    """Configure Django settings for testing"""
    # Configure Celery to execute tasks synchronously during tests
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    # Use in-memory broker for testing
    settings.CELERY_BROKER_URL = 'memory://'
    settings.CELERY_RESULT_BACKEND = 'cache+memory://'

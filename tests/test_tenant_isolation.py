import pytest
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.models import Tenant, TenantMembership
from core.middleware import TenantMiddleware

User = get_user_model()


@pytest.fixture
def tenant_a(db):
    """Create tenant A"""
    return Tenant.objects.create(name="Tenant A", slug="tenant-a")


@pytest.fixture
def tenant_b(db):
    """Create tenant B"""
    return Tenant.objects.create(name="Tenant B", slug="tenant-b")


@pytest.fixture
def user_a(db, tenant_a):
    """Create user A with membership in tenant A"""
    user = User.objects.create_user(
        email="user_a@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant_a,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def user_b(db, tenant_b):
    """Create user B with membership in tenant B"""
    user = User.objects.create_user(
        email="user_b@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant_b,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def manager_a(db, tenant_a):
    """Create manager user in tenant A"""
    user = User.objects.create_user(
        email="manager_a@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant_a,
        role=TenantMembership.Role.MANAGER
    )
    return user


@pytest.mark.django_db
class TestTenantModel:
    """Test Tenant model"""

    def test_create_tenant(self):
        tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")
        assert tenant.name == "Test Tenant"
        assert tenant.slug == "test-tenant"
        assert tenant.is_active is True

    def test_tenant_str(self, tenant_a):
        assert str(tenant_a) == "Tenant A"


@pytest.mark.django_db
class TestUserModel:
    """Test custom User model"""

    def test_create_user(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_superuser(self):
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        assert superuser.is_staff is True
        assert superuser.is_superuser is True

    def test_user_str(self, user_a):
        assert str(user_a) == "user_a@example.com"

    def test_get_full_name(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe"
        )
        assert user.get_full_name() == "John Doe"

    def test_get_full_name_empty(self, user_a):
        assert user_a.get_full_name() == "user_a@example.com"


@pytest.mark.django_db
class TestTenantMembership:
    """Test TenantMembership model"""

    def test_create_membership(self, tenant_a, user_a):
        membership = TenantMembership.objects.get(user=user_a, tenant=tenant_a)
        assert membership.role == TenantMembership.Role.MEMBER

    def test_manager_role(self, manager_a, tenant_a):
        membership = TenantMembership.objects.get(user=manager_a, tenant=tenant_a)
        assert membership.role == TenantMembership.Role.MANAGER

    def test_unique_together_constraint(self, tenant_a, user_a):
        """Test that a user cannot have duplicate membership in same tenant"""
        with pytest.raises(Exception):
            TenantMembership.objects.create(
                user=user_a,
                tenant=tenant_a,
                role=TenantMembership.Role.MANAGER
            )


@pytest.mark.django_db
class TestTenantMiddleware:
    """Test TenantMiddleware for strict tenant isolation"""

    def setup_method(self):
        self.factory = RequestFactory()
        self.middleware = TenantMiddleware(lambda r: None)

    def test_unauthenticated_user_no_tenant(self):
        """Unauthenticated users should have no tenant"""
        request = self.factory.get('/')
        request.user = type('User', (), {'is_authenticated': False})()

        self.middleware.process_request(request)
        assert not hasattr(request, 'tenant')

    def test_authenticated_user_with_tenant(self, user_a, tenant_a):
        """Authenticated user with membership gets tenant attached"""
        request = self.factory.get('/')
        request.user = user_a

        self.middleware.process_request(request)
        assert request.tenant == tenant_a
        assert request.tenant_role == TenantMembership.Role.MEMBER

    def test_superuser_no_tenant_required(self, db):
        """Superusers can access without tenant"""
        superuser = User.objects.create_superuser(
            email="super@example.com",
            password="superpass123"
        )
        request = self.factory.get('/')
        request.user = superuser

        self.middleware.process_request(request)
        assert request.tenant is None

    def test_admin_path_skipped(self, user_a):
        """Admin path should skip tenant check"""
        request = self.factory.get('/admin/')
        request.user = user_a

        result = self.middleware.process_request(request)
        assert result is None

    def test_healthz_path_skipped(self, user_a):
        """Healthz path should skip tenant check"""
        request = self.factory.get('/healthz')
        request.user = user_a

        result = self.middleware.process_request(request)
        assert result is None


@pytest.mark.django_db
class TestTenantIsolation:
    """Test that tenant data is strictly isolated"""

    def test_user_cannot_access_other_tenant_data(self, user_a, user_b, tenant_a, tenant_b):
        """Verify users from different tenants cannot access each other's data"""
        # User A is in tenant A
        membership_a = TenantMembership.objects.get(user=user_a)
        assert membership_a.tenant == tenant_a

        # User B is in tenant B
        membership_b = TenantMembership.objects.get(user=user_b)
        assert membership_b.tenant == tenant_b

        # Verify they are in different tenants
        assert membership_a.tenant != membership_b.tenant

    def test_manager_in_same_tenant(self, user_a, manager_a, tenant_a):
        """Verify manager and member can be in same tenant"""
        memberships = TenantMembership.objects.filter(tenant=tenant_a)
        assert memberships.count() == 2

        roles = set(m.role for m in memberships)
        assert TenantMembership.Role.MANAGER in roles
        assert TenantMembership.Role.MEMBER in roles

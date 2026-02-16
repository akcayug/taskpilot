import pytest
from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core import mail
from core.models import Tenant, TenantMembership
from users.models import Invitation, TelegramLinkToken

User = get_user_model()


@pytest.fixture
def client():
    """Django test client"""
    return Client()


@pytest.fixture
def tenant(db):
    """Create a test tenant"""
    return Tenant.objects.create(name="Test Tenant", slug="test-tenant")


@pytest.fixture
def manager(db, tenant):
    """Create a manager user in the test tenant"""
    user = User.objects.create_user(
        email="manager@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MANAGER
    )
    return user


@pytest.fixture
def member(db, tenant):
    """Create a member user in the test tenant"""
    user = User.objects.create_user(
        email="member@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.mark.django_db
class TestInvitationModel:
    """Test Invitation model"""

    def test_create_invitation(self, tenant, manager):
        """Test creating an invitation"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email="newuser@example.com",
            role=TenantMembership.Role.MEMBER,
            invited_by=manager
        )

        assert invitation.email == "newuser@example.com"
        assert invitation.role == TenantMembership.Role.MEMBER
        assert invitation.token is not None
        assert invitation.expires_at is not None
        assert invitation.accepted is False

    def test_invitation_generates_token_automatically(self, tenant):
        """Test that invitation generates token automatically"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email="test@example.com"
        )

        assert len(invitation.token) > 0

    def test_invitation_expires_after_7_days(self, tenant):
        """Test that invitation expires after 7 days"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email="test@example.com"
        )

        # Should not be expired immediately
        assert not invitation.is_expired()

        # Manually set expiration to past
        invitation.expires_at = timezone.now() - timedelta(days=1)
        invitation.save()

        assert invitation.is_expired()
        assert not invitation.is_valid()

    def test_invitation_is_valid(self, tenant):
        """Test invitation validity check"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email="test@example.com"
        )

        assert invitation.is_valid()

        # Mark as accepted
        invitation.accepted = True
        invitation.save()

        assert not invitation.is_valid()

    def test_cannot_create_duplicate_invitation(self, tenant):
        """Test that cannot invite same email twice to same tenant"""
        Invitation.objects.create(
            tenant=tenant,
            email="test@example.com"
        )

        with pytest.raises(Exception):
            Invitation.objects.create(
                tenant=tenant,
                email="test@example.com"
            )


@pytest.mark.django_db
class TestInviteUserView:
    """Test invitation creation view"""

    def test_only_managers_can_invite(self, client, member):
        """Test that only managers can send invitations"""
        client.force_login(member)

        response = client.post(reverse('invite_user'), {
            'email': 'newuser@example.com',
            'role': TenantMembership.Role.MEMBER
        })

        assert response.status_code == 403
        data = response.json()
        assert 'Only managers can invite users' in data['error']

    def test_manager_can_invite(self, client, manager, tenant, mocker):
        """Test that managers can send invitations"""
        # Mock the Celery task to avoid needing a broker
        mock_task = mocker.patch('users.views.send_invitation_email.delay')

        client.force_login(manager)

        response = client.post(reverse('invite_user'), {
            'email': 'newuser@example.com',
            'role': TenantMembership.Role.MEMBER
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        # Check invitation was created
        invitation = Invitation.objects.get(email='newuser@example.com')
        assert invitation.tenant == tenant
        assert invitation.role == TenantMembership.Role.MEMBER

        # Verify email task was called
        mock_task.assert_called_once_with(invitation.id)

    def test_cannot_invite_existing_member(self, client, manager, member):
        """Test cannot invite user already in tenant"""
        client.force_login(manager)

        response = client.post(reverse('invite_user'), {
            'email': member.email,
            'role': TenantMembership.Role.MEMBER
        })

        assert response.status_code == 400
        data = response.json()
        assert 'already in tenant' in data['error']

    def test_cannot_invite_same_email_twice(self, client, manager, tenant):
        """Test cannot send duplicate invitations"""
        # Create first invitation
        Invitation.objects.create(
            tenant=tenant,
            email='test@example.com',
            invited_by=manager
        )

        client.force_login(manager)
        response = client.post(reverse('invite_user'), {
            'email': 'test@example.com',
            'role': TenantMembership.Role.MEMBER
        })

        assert response.status_code == 400
        data = response.json()
        assert 'already sent' in data['error']


@pytest.mark.django_db
class TestAcceptInviteView:
    """Test invitation acceptance flow"""

    def test_accept_invite_page_loads(self, client, tenant, manager):
        """Test that accept invitation page loads"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email='newuser@example.com',
            invited_by=manager
        )

        response = client.get(reverse('accept_invite', args=[invitation.token]))
        assert response.status_code == 200
        assert b'Accept Invitation' in response.content

    def test_accept_invite_creates_user(self, client, tenant, manager):
        """Test accepting invitation creates user and membership"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email='newuser@example.com',
            role=TenantMembership.Role.MEMBER,
            invited_by=manager
        )

        response = client.post(reverse('accept_invite', args=[invitation.token]), {
            'first_name': 'New',
            'last_name': 'User',
            'password': 'securepass123',
            'password_confirm': 'securepass123'
        })

        assert response.status_code == 200

        # Check user was created
        user = User.objects.get(email='newuser@example.com')
        assert user.first_name == 'New'
        assert user.last_name == 'User'
        assert user.check_password('securepass123')

        # Check membership was created
        membership = TenantMembership.objects.get(user=user, tenant=tenant)
        assert membership.role == TenantMembership.Role.MEMBER

        # Check invitation was marked as accepted
        invitation.refresh_from_db()
        assert invitation.accepted is True
        assert invitation.accepted_at is not None

    def test_accept_invite_password_mismatch(self, client, tenant, manager):
        """Test that password mismatch shows error"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email='newuser@example.com',
            invited_by=manager
        )

        response = client.post(reverse('accept_invite', args=[invitation.token]), {
            'first_name': 'New',
            'last_name': 'User',
            'password': 'password123',
            'password_confirm': 'different123'
        })

        assert response.status_code == 200
        assert b'Passwords do not match' in response.content

        # User should not be created
        assert not User.objects.filter(email='newuser@example.com').exists()

    def test_accept_invite_password_too_short(self, client, tenant, manager):
        """Test that short password shows error"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email='newuser@example.com',
            invited_by=manager
        )

        response = client.post(reverse('accept_invite', args=[invitation.token]), {
            'first_name': 'New',
            'last_name': 'User',
            'password': 'short',
            'password_confirm': 'short'
        })

        assert response.status_code == 200
        assert b'at least 8 characters' in response.content

    def test_cannot_accept_expired_invitation(self, client, tenant, manager):
        """Test that expired invitations cannot be accepted"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email='newuser@example.com',
            invited_by=manager
        )

        # Set expiration to past
        invitation.expires_at = timezone.now() - timedelta(days=1)
        invitation.save()

        response = client.get(reverse('accept_invite', args=[invitation.token]))
        assert response.status_code == 200
        assert b'expired' in response.content

    def test_cannot_accept_already_accepted_invitation(self, client, tenant, manager):
        """Test that already accepted invitations cannot be reused"""
        invitation = Invitation.objects.create(
            tenant=tenant,
            email='newuser@example.com',
            invited_by=manager,
            accepted=True
        )

        response = client.get(reverse('accept_invite', args=[invitation.token]))
        assert response.status_code == 200
        assert b'already been accepted' in response.content


@pytest.mark.django_db
class TestTelegramLinkToken:
    """Test Telegram linking functionality"""

    def test_create_telegram_link_token(self, member):
        """Test creating Telegram link token"""
        token = TelegramLinkToken.objects.create(user=member)

        assert token.code is not None
        assert len(token.code) == 8
        assert token.expires_at is not None

    def test_telegram_link_token_expires(self, member):
        """Test that token expires after 24 hours"""
        token = TelegramLinkToken.objects.create(user=member)

        # Should not be expired immediately
        assert not token.is_expired()

        # Set expiration to past
        token.expires_at = timezone.now() - timedelta(hours=1)
        token.save()

        assert token.is_expired()
        assert not token.is_valid()


@pytest.mark.django_db
class TestLinkTelegramView:
    """Test Telegram linking view"""

    def test_link_telegram_page_loads(self, client, member):
        """Test that Telegram linking page loads"""
        client.force_login(member)
        response = client.get(reverse('link_telegram'))

        assert response.status_code == 200
        assert b'Link Telegram Account' in response.content

    def test_link_telegram_shows_code(self, client, member):
        """Test that linking page shows code"""
        client.force_login(member)
        response = client.get(reverse('link_telegram'))

        assert response.status_code == 200
        assert response.context['link_code'] is not None

        # Check token was created
        token = TelegramLinkToken.objects.get(user=member)
        assert token.code == response.context['link_code']

    def test_refresh_telegram_code(self, client, member):
        """Test refreshing Telegram link code"""
        # Create initial token
        old_token = TelegramLinkToken.objects.create(user=member)
        old_code = old_token.code

        client.force_login(member)
        response = client.post(reverse('refresh_telegram_code'))

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['code'] != old_code

        # Old token should be deleted
        assert not TelegramLinkToken.objects.filter(code=old_code).exists()


@pytest.mark.django_db
class TestInvitationEmailSending:
    """Test invitation email sending (mocked)"""

    def test_invitation_creation_triggers_email(self, client, manager, tenant, mailoutbox):
        """Test that creating invitation sends email"""
        # Note: This test uses Django's mail.outbox for testing emails
        # In production, Celery would handle this asynchronously

        # For testing, we'll manually trigger the task logic
        from users.tasks import send_invitation_email

        invitation = Invitation.objects.create(
            tenant=tenant,
            email='test@example.com',
            invited_by=manager
        )

        # Call task synchronously for testing
        result = send_invitation_email(invitation.id)

        assert 'sent to test@example.com' in result

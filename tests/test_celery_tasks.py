"""Tests for Celery periodic tasks."""
import pytest
from datetime import date, timedelta
from django.utils import timezone
from unittest.mock import patch, MagicMock
from core.models import User, Tenant, TenantMembership
from tasks.models import Project, Task
from users.models import Invitation, TelegramLinkToken
from workers.tasks import (
    send_daily_reminders,
    send_due_today_notifications,
    send_overdue_reminders,
    cleanup_expired_invitations,
    cleanup_expired_telegram_tokens,
)


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(name="Test Tenant", slug="test-tenant")


@pytest.fixture
def user_with_telegram(db, tenant):
    """Create a user with Telegram linked."""
    user = User.objects.create_user(
        email="user@example.com",
        password="password123",
        telegram_id=12345678,
        telegram_username="testuser"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def user_without_telegram(db, tenant):
    """Create a user without Telegram linked."""
    user = User.objects.create_user(
        email="nobot@example.com",
        password="password123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def project(db, tenant):
    """Create a test project."""
    return Project.objects.create(
        name="Test Project",
        tenant=tenant
    )


@pytest.mark.django_db
class TestSendDailyReminders:
    """Tests for send_daily_reminders task."""

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'})
    @patch('workers.tasks.requests.post')
    def test_sends_reminder_to_user_with_pending_tasks(
        self, mock_post, user_with_telegram, project
    ):
        """Should send daily reminder to user with pending tasks."""
        # Create pending tasks
        Task.objects.create(
            title="Task 1",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.TODO,
            priority=Task.Priority.HIGH,
            due_date=date.today()
        )
        Task.objects.create(
            title="Task 2",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.MEDIUM
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_daily_reminders()

        assert "Sent daily reminders to 1 users" in result
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['chat_id'] == user_with_telegram.telegram_id
        assert 'Good morning!' in call_args[1]['json']['text']
        assert 'Task 1' in call_args[1]['json']['text']
        assert 'Task 2' in call_args[1]['json']['text']

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'})
    @patch('workers.tasks.requests.post')
    def test_skips_users_without_telegram(
        self, mock_post, user_without_telegram, project
    ):
        """Should skip users without Telegram linked."""
        Task.objects.create(
            title="Task 1",
            project=project,
            tenant=project.tenant,
            assignee=user_without_telegram,
            status=Task.Status.TODO
        )

        result = send_daily_reminders()

        assert "Sent daily reminders to 0 users" in result
        mock_post.assert_not_called()

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'})
    @patch('workers.tasks.requests.post')
    def test_skips_users_with_no_pending_tasks(
        self, mock_post, user_with_telegram, project
    ):
        """Should skip users with no pending tasks."""
        Task.objects.create(
            title="Completed Task",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.DONE
        )

        result = send_daily_reminders()

        assert "Sent daily reminders to 0 users" in result
        mock_post.assert_not_called()

    def test_returns_error_when_bot_token_not_configured(self):
        """Should return error when TELEGRAM_BOT_TOKEN is not set."""
        with patch.dict('os.environ', {}, clear=True):
            result = send_daily_reminders()
            assert result == "TELEGRAM_BOT_TOKEN not configured"


@pytest.mark.django_db
class TestSendDueTodayNotifications:
    """Tests for send_due_today_notifications task."""

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'})
    @patch('workers.tasks.requests.post')
    def test_sends_notification_for_tasks_due_today(
        self, mock_post, user_with_telegram, project
    ):
        """Should send notification for tasks due today."""
        task = Task.objects.create(
            title="Due Today Task",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.TODO,
            priority=Task.Priority.HIGH,
            due_date=date.today()
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_due_today_notifications()

        assert "Sent due today notifications for 1 tasks" in result
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['chat_id'] == user_with_telegram.telegram_id
        assert 'Task Due Today!' in call_args[1]['json']['text']
        assert task.title in call_args[1]['json']['text']

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'})
    @patch('workers.tasks.requests.post')
    def test_skips_tasks_not_due_today(
        self, mock_post, user_with_telegram, project
    ):
        """Should skip tasks not due today."""
        Task.objects.create(
            title="Future Task",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.TODO,
            due_date=date.today() + timedelta(days=1)
        )

        result = send_due_today_notifications()

        assert "Sent due today notifications for 0 tasks" in result
        mock_post.assert_not_called()

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'})
    @patch('workers.tasks.requests.post')
    def test_skips_completed_tasks(
        self, mock_post, user_with_telegram, project
    ):
        """Should skip completed tasks even if due today."""
        Task.objects.create(
            title="Completed Task",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.DONE,
            due_date=date.today()
        )

        result = send_due_today_notifications()

        assert "Sent due today notifications for 0 tasks" in result
        mock_post.assert_not_called()


@pytest.mark.django_db
class TestSendOverdueReminders:
    """Tests for send_overdue_reminders task."""

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'})
    @patch('workers.tasks.requests.post')
    def test_sends_reminders_for_overdue_tasks(
        self, mock_post, user_with_telegram, project
    ):
        """Should send reminders for overdue tasks."""
        Task.objects.create(
            title="Overdue Task 1",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.TODO,
            priority=Task.Priority.HIGH,
            due_date=date.today() - timedelta(days=2)
        )
        Task.objects.create(
            title="Overdue Task 2",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.MEDIUM,
            due_date=date.today() - timedelta(days=1)
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_overdue_reminders()

        assert "Sent overdue reminders to 1 users" in result
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['chat_id'] == user_with_telegram.telegram_id
        assert 'overdue' in call_args[1]['json']['text'].lower()
        assert 'Overdue Task 1' in call_args[1]['json']['text']
        assert 'Overdue Task 2' in call_args[1]['json']['text']

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'})
    @patch('workers.tasks.requests.post')
    def test_groups_overdue_tasks_by_user(
        self, mock_post, user_with_telegram, project, tenant
    ):
        """Should group overdue tasks by user."""
        # Create another user
        user2 = User.objects.create_user(
            email="user2@example.com",
            password="password123",
            telegram_id=87654321,
            telegram_username="user2"
        )
        TenantMembership.objects.create(
            user=user2,
            tenant=tenant,
            role=TenantMembership.Role.MEMBER
        )

        Task.objects.create(
            title="Overdue Task User 1",
            project=project,
            tenant=project.tenant,
            assignee=user_with_telegram,
            status=Task.Status.TODO,
            due_date=date.today() - timedelta(days=1)
        )
        Task.objects.create(
            title="Overdue Task User 2",
            project=project,
            tenant=project.tenant,
            assignee=user2,
            status=Task.Status.TODO,
            due_date=date.today() - timedelta(days=1)
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_overdue_reminders()

        assert "Sent overdue reminders to 2 users" in result
        assert mock_post.call_count == 2


@pytest.mark.django_db
class TestCleanupExpiredInvitations:
    """Tests for cleanup_expired_invitations task."""

    def test_deletes_expired_invitations(self, tenant):
        """Should delete expired invitations."""
        # Create expired invitation
        expired = Invitation.objects.create(
            email="expired@example.com",
            tenant=tenant,
            invited_by=None,
            role=TenantMembership.Role.MEMBER,
            expires_at=timezone.now() - timedelta(days=1)
        )

        # Create valid invitation
        valid = Invitation.objects.create(
            email="valid@example.com",
            tenant=tenant,
            invited_by=None,
            role=TenantMembership.Role.MEMBER,
            expires_at=timezone.now() + timedelta(days=1)
        )

        result = cleanup_expired_invitations()

        assert "Deleted 1 expired invitations" in result
        assert not Invitation.objects.filter(id=expired.id).exists()
        assert Invitation.objects.filter(id=valid.id).exists()

    def test_does_not_delete_accepted_invitations(self, tenant):
        """Should not delete accepted invitations even if expired."""
        accepted = Invitation.objects.create(
            email="accepted@example.com",
            tenant=tenant,
            invited_by=None,
            role=TenantMembership.Role.MEMBER,
            expires_at=timezone.now() - timedelta(days=1),
            accepted=True
        )

        result = cleanup_expired_invitations()

        assert "Deleted 0 expired invitations" in result
        assert Invitation.objects.filter(id=accepted.id).exists()


@pytest.mark.django_db
class TestCleanupExpiredTelegramTokens:
    """Tests for cleanup_expired_telegram_tokens task."""

    def test_deletes_expired_tokens(self, user_with_telegram, tenant):
        """Should delete expired Telegram link tokens."""
        # Create another user for the valid token (OneToOneField constraint)
        user2 = User.objects.create_user(
            email="user2@example.com",
            password="password123"
        )
        TenantMembership.objects.create(
            user=user2,
            tenant=tenant,
            role=TenantMembership.Role.MEMBER
        )

        # Create expired token
        expired = TelegramLinkToken.objects.create(
            user=user_with_telegram,
            expires_at=timezone.now() - timedelta(hours=1)
        )

        # Create valid token with different user
        valid = TelegramLinkToken.objects.create(
            user=user2,
            expires_at=timezone.now() + timedelta(hours=1)
        )

        result = cleanup_expired_telegram_tokens()

        assert "Deleted 1 expired Telegram link tokens" in result
        assert not TelegramLinkToken.objects.filter(id=expired.id).exists()
        assert TelegramLinkToken.objects.filter(id=valid.id).exists()

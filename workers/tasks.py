import os
import requests
from datetime import date, timedelta
from celery import shared_task
from django.utils import timezone
from django.db.models import Q


@shared_task
def send_daily_reminders():
    """
    Send daily digest of pending tasks to all users with Telegram linked.
    Runs at 8:00 AM every day.
    """
    from core.models import User
    from tasks.models import Task

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return "TELEGRAM_BOT_TOKEN not configured"

    # Get all users with Telegram linked
    users = User.objects.filter(telegram_id__isnull=False)

    sent_count = 0
    for user in users:
        # Get user's pending tasks (TODO and IN_PROGRESS)
        membership = user.memberships.select_related('tenant').first()
        if not membership:
            continue

        pending_tasks = Task.objects.filter(
            tenant=membership.tenant,
            assignee=user,
            status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS]
        ).select_related('project').order_by('due_date')

        if not pending_tasks.exists():
            continue

        # Build message
        message = "🌅 *Good morning!*\n\n"
        message += f"You have *{pending_tasks.count()}* pending tasks:\n\n"

        for task in pending_tasks[:10]:  # Limit to 10 tasks
            status_emoji = '📋' if task.status == Task.Status.TODO else '⏳'
            priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(task.priority, '•')

            due_info = ""
            if task.due_date:
                if task.due_date == date.today():
                    due_info = " ⚠️ *Due today!*"
                elif task.due_date < date.today():
                    due_info = f" ❗ *Overdue by {(date.today() - task.due_date).days} days*"
                elif task.due_date <= date.today() + timedelta(days=3):
                    due_info = f" 📅 Due {task.due_date.strftime('%b %d')}"

            message += f"{status_emoji} {priority_emoji} {task.title}{due_info}\n"

        if pending_tasks.count() > 10:
            message += f"\n_...and {pending_tasks.count() - 10} more tasks_\n"

        message += "\n💡 Use /mytasks to see all your tasks"

        # Send via Telegram API
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, json={
                'chat_id': user.telegram_id,
                'text': message,
                'parse_mode': 'Markdown'
            })
            response.raise_for_status()
            sent_count += 1
        except Exception as e:
            print(f"Failed to send daily reminder to {user.email}: {str(e)}")

    return f"Sent daily reminders to {sent_count} users"


@shared_task
def send_due_today_notifications():
    """
    Send notifications for tasks due today.
    Runs at 9:00 AM every day.
    """
    from core.models import User
    from tasks.models import Task

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return "TELEGRAM_BOT_TOKEN not configured"

    # Get tasks due today
    today = date.today()
    due_today_tasks = Task.objects.filter(
        due_date=today,
        status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS],
        assignee__telegram_id__isnull=False
    ).select_related('assignee', 'project')

    sent_count = 0
    for task in due_today_tasks:
        user = task.assignee

        # Build message
        priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(task.priority, '•')
        status_emoji = '📋' if task.status == Task.Status.TODO else '⏳'

        message = (
            f"⚠️ *Task Due Today!*\n\n"
            f"{status_emoji} {priority_emoji} *{task.title}*\n\n"
            f"Project: {task.project.name}\n"
            f"Status: {task.get_status_display()}\n"
            f"Priority: {task.priority}\n\n"
            f"💡 Use /task {task.id} to view details"
        )

        # Send via Telegram API
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, json={
                'chat_id': user.telegram_id,
                'text': message,
                'parse_mode': 'Markdown'
            })
            response.raise_for_status()
            sent_count += 1
        except Exception as e:
            print(f"Failed to send due today notification to {user.email}: {str(e)}")

    return f"Sent due today notifications for {sent_count} tasks"


@shared_task
def send_overdue_reminders():
    """
    Send reminders for overdue tasks.
    Can be scheduled separately or called on-demand.
    """
    from core.models import User
    from tasks.models import Task

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return "TELEGRAM_BOT_TOKEN not configured"

    # Get overdue tasks
    today = date.today()
    overdue_tasks = Task.objects.filter(
        due_date__lt=today,
        status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS],
        assignee__telegram_id__isnull=False
    ).select_related('assignee', 'project')

    # Group by user
    user_tasks = {}
    for task in overdue_tasks:
        if task.assignee.id not in user_tasks:
            user_tasks[task.assignee.id] = []
        user_tasks[task.assignee.id].append(task)

    sent_count = 0
    for user_id, tasks in user_tasks.items():
        user = tasks[0].assignee

        # Build message
        message = f"❗ *You have {len(tasks)} overdue task(s):*\n\n"

        for task in tasks[:5]:  # Limit to 5 tasks
            days_overdue = (today - task.due_date).days
            priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(task.priority, '•')

            message += (
                f"{priority_emoji} *{task.title}*\n"
                f"   Overdue by {days_overdue} day(s)\n"
                f"   Project: {task.project.name}\n\n"
            )

        if len(tasks) > 5:
            message += f"_...and {len(tasks) - 5} more overdue tasks_\n\n"

        message += "💡 Use /mytasks to see all your tasks"

        # Send via Telegram API
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, json={
                'chat_id': user.telegram_id,
                'text': message,
                'parse_mode': 'Markdown'
            })
            response.raise_for_status()
            sent_count += 1
        except Exception as e:
            print(f"Failed to send overdue reminder to {user.email}: {str(e)}")

    return f"Sent overdue reminders to {sent_count} users"


@shared_task
def cleanup_expired_invitations():
    """
    Clean up expired invitations.
    Can be run periodically to keep database clean.
    """
    from users.models import Invitation
    from django.utils import timezone

    # Delete invitations that are expired and not accepted
    deleted_count, _ = Invitation.objects.filter(
        expires_at__lt=timezone.now(),
        accepted=False
    ).delete()

    return f"Deleted {deleted_count} expired invitations"


@shared_task
def cleanup_expired_telegram_tokens():
    """
    Clean up expired Telegram link tokens.
    Can be run periodically to keep database clean.
    """
    from users.models import TelegramLinkToken
    from django.utils import timezone

    # Delete expired tokens
    deleted_count, _ = TelegramLinkToken.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()

    return f"Deleted {deleted_count} expired Telegram link tokens"

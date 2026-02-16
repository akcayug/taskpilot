from telegram import Update
from telegram.ext import ContextTypes
from .keyboards import (
    get_priority_keyboard,
    get_status_keyboard,
    get_task_actions_keyboard
)
from .api_client import TaskPilotAPI


class BotHandlers:
    """Handlers for bot commands and callbacks"""

    def __init__(self, api_client: TaskPilotAPI, web_url: str):
        self.api = api_client
        self.web_url = web_url

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        telegram_id = update.effective_user.id
        user = self.api.get_user_by_telegram_id(telegram_id)

        if user:
            await update.message.reply_text(
                f"Welcome back, {user['first_name']}! 👋\n\n"
                "Use /mytasks to see your tasks or /newtask to create a new one."
            )
        else:
            await update.message.reply_text(
                "Welcome to TaskPilot! 🚀\n\n"
                "To get started, you need to link your Telegram account:\n\n"
                f"1. Visit {self.web_url}\n"
                "2. Log in to your account\n"
                "3. Go to Settings → Link Telegram\n"
                "4. Use the command: /link <YOUR_CODE>\n\n"
                "After linking, you'll be able to manage your tasks right here in Telegram!"
            )

    async def link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /link <code> command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide your linking code.\n"
                "Usage: /link <CODE>\n\n"
                f"Get your code from: {self.web_url}/telegram/link/"
            )
            return

        code = context.args[0].upper()
        telegram_id = update.effective_user.id
        telegram_username = update.effective_user.username or ""

        result = self.api.link_telegram_account(code, telegram_id, telegram_username)

        if 'error' in result:
            await update.message.reply_text(
                f"❌ Failed to link account: {result['error']}\n\n"
                "Please check your code and try again."
            )
        else:
            await update.message.reply_text(
                "✅ Account linked successfully!\n\n"
                "You can now use:\n"
                "• /mytasks - View your assigned tasks\n"
                "• /newtask - Create a new task"
            )

    async def my_tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mytasks command"""
        telegram_id = update.effective_user.id

        # Check if user is linked
        user = self.api.get_user_by_telegram_id(telegram_id)
        if not user:
            await update.message.reply_text(
                "❌ You need to link your account first.\n"
                f"Visit {self.web_url} to get your linking code, then use /link <CODE>"
            )
            return

        # Get user's tasks
        tasks = self.api.get_user_tasks(telegram_id)

        if not tasks:
            await update.message.reply_text(
                "📋 You have no assigned tasks.\n\n"
                "Use /newtask to create a new task."
            )
            return

        # Format tasks by status
        status_emojis = {
            'TODO': '📋',
            'IN_PROGRESS': '⏳',
            'DONE': '✅',
            'ARCHIVED': '📦'
        }

        priority_emojis = {
            'HIGH': '🔴',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }

        message = "📋 *Your Tasks*\n\n"

        for task in tasks[:10]:  # Limit to 10 tasks
            status_emoji = status_emojis.get(task['status'], '•')
            priority_emoji = priority_emojis.get(task['priority'], '•')

            message += (
                f"{status_emoji} *{task['title']}*\n"
                f"   {priority_emoji} {task['priority']} | "
                f"Project: {task['project']}\n"
                f"   Status: {task['status_display']}\n"
                f"   ID: #{task['id']}\n\n"
            )

        if len(tasks) > 10:
            message += f"\n_...and {len(tasks) - 10} more tasks_\n"

        message += "\n💡 Use /task <ID> to see task details"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def new_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /newtask command - start task creation flow"""
        telegram_id = update.effective_user.id

        # Check if user is linked
        user = self.api.get_user_by_telegram_id(telegram_id)
        if not user:
            await update.message.reply_text(
                "❌ You need to link your account first.\n"
                f"Visit {self.web_url} to get your linking code, then use /link <CODE>"
            )
            return

        # Get user's projects
        projects = self.api.get_user_projects(telegram_id)

        if not projects:
            await update.message.reply_text(
                "❌ No projects found. Please create a project in the web interface first.\n"
                f"Visit: {self.web_url}"
            )
            return

        # Store project list in user data
        context.user_data['projects'] = projects
        context.user_data['task_creation_step'] = 'awaiting_title'

        await update.message.reply_text(
            "🆕 *Create New Task*\n\n"
            "Please enter the task title:",
            parse_mode='Markdown'
        )

    async def task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /task <id> command - show task details"""
        if not context.args:
            await update.message.reply_text(
                "Please provide a task ID.\n"
                "Usage: /task <ID>"
            )
            return

        try:
            task_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
            return

        telegram_id = update.effective_user.id

        # Check if user is linked
        user = self.api.get_user_by_telegram_id(telegram_id)
        if not user:
            await update.message.reply_text(
                "❌ You need to link your account first.\n"
                f"Visit {self.web_url} to get your linking code, then use /link <CODE>"
            )
            return

        # Get task details
        task = self.api.get_task_details(telegram_id, task_id)

        if not task:
            await update.message.reply_text("❌ Task not found or you don't have access to it.")
            return

        # Format task details
        priority_emojis = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}
        status_emojis = {'TODO': '📋', 'IN_PROGRESS': '⏳', 'DONE': '✅', 'ARCHIVED': '📦'}

        message = (
            f"{status_emojis.get(task['status'], '•')} *{task['title']}*\n\n"
            f"*Project:* {task['project']}\n"
            f"*Status:* {task['status_display']}\n"
            f"*Priority:* {priority_emojis.get(task['priority'], '•')} {task['priority']}\n"
        )

        if task.get('description'):
            message += f"*Description:* {task['description']}\n"

        if task.get('due_date'):
            message += f"*Due Date:* {task['due_date']}\n"

        if task.get('assignee'):
            message += f"*Assignee:* {task['assignee']}\n"

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_task_actions_keyboard(task_id, task['status'])
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for task creation flow)"""
        if context.user_data.get('task_creation_step') == 'awaiting_title':
            # Store title and ask for priority
            context.user_data['task_title'] = update.message.text
            context.user_data['task_creation_step'] = 'awaiting_priority'

            await update.message.reply_text(
                f"✅ Title: *{update.message.text}*\n\n"
                "Now select the priority:",
                parse_mode='Markdown',
                reply_markup=get_priority_keyboard()
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()

        data = query.data
        telegram_id = update.effective_user.id

        # Cancel action
        if data == 'cancel':
            context.user_data.clear()
            await query.edit_message_text("❌ Action cancelled.")
            return

        # Priority selection (during task creation)
        if data.startswith('priority_'):
            priority = data.replace('priority_', '')
            context.user_data['task_priority'] = priority

            # Show project selection
            projects = context.user_data.get('projects', [])
            if not projects:
                await query.edit_message_text("❌ No projects available.")
                return

            # For simplicity, use first project (or implement project selection)
            project_id = projects[0]['id']

            # Create the task
            result = self.api.create_task(
                telegram_id,
                context.user_data['task_title'],
                project_id,
                priority
            )

            if 'error' in result:
                await query.edit_message_text(f"❌ Failed to create task: {result['error']}")
            else:
                await query.edit_message_text(
                    f"✅ *Task Created!*\n\n"
                    f"Title: {result['title']}\n"
                    f"Priority: {result['priority']}\n"
                    f"Project: {result['project']}\n"
                    f"Status: {result['status_display']}\n\n"
                    f"Task ID: #{result['id']}",
                    parse_mode='Markdown'
                )

            context.user_data.clear()

        # Status update
        elif data.startswith('status_'):
            new_status = data.replace('status_', '')
            task_id = context.user_data.get('current_task_id')

            if not task_id:
                await query.edit_message_text("❌ Task ID not found.")
                return

            result = self.api.update_task_status(telegram_id, task_id, new_status)

            if 'error' in result:
                await query.edit_message_text(f"❌ Failed to update status: {result['error']}")
            else:
                await query.edit_message_text(
                    f"✅ Task status updated to: *{result['status_display']}*",
                    parse_mode='Markdown'
                )

            context.user_data.pop('current_task_id', None)

        # Update status action
        elif data.startswith('update_status_'):
            task_id = int(data.replace('update_status_', ''))
            task = self.api.get_task_details(telegram_id, task_id)

            if not task:
                await query.edit_message_text("❌ Task not found.")
                return

            context.user_data['current_task_id'] = task_id

            await query.edit_message_text(
                f"Select new status for: *{task['title']}*\n"
                f"Current status: {task['status_display']}",
                parse_mode='Markdown',
                reply_markup=get_status_keyboard(task['status'])
            )

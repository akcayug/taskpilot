from telegram import Update
from telegram.ext import ContextTypes
from .keyboards import (
    get_priority_keyboard,
    get_status_keyboard,
    get_task_actions_keyboard,
    get_project_keyboard,
    get_assignee_keyboard,
    get_skip_keyboard
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
        response = self.api.get_user_tasks(telegram_id)
        tasks = response.get('tasks', [])

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

        # Store project list and start flow
        context.user_data['projects'] = projects
        context.user_data['task_creation_step'] = 'awaiting_project'

        await update.message.reply_text(
            "🆕 *Create New Task*\n\n"
            "Select a project:",
            parse_mode='Markdown',
            reply_markup=get_project_keyboard(projects)
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

    def _create_task_from_context(self, telegram_id, context):
        """Helper to create task from accumulated user_data"""
        return self.api.create_task(
            telegram_id=telegram_id,
            title=context.user_data['task_title'],
            project_id=context.user_data['task_project_id'],
            priority=context.user_data['task_priority'],
            description=context.user_data.get('task_description', ''),
            assignee_id=context.user_data.get('task_assignee_id'),
            due_date=context.user_data.get('task_due_date'),
        )

    async def _show_task_created(self, query, result, context):
        """Show task creation result and clear state"""
        if 'error' in result:
            await query.edit_message_text(f"❌ Failed to create task: {result['error']}")
        else:
            msg = (
                f"✅ *Task Created!*\n\n"
                f"Title: {result['title']}\n"
                f"Priority: {result['priority']}\n"
                f"Project: {result['project']}\n"
                f"Status: {result['status_display']}\n"
            )
            if result.get('assignee'):
                msg += f"Assignee: {result['assignee']}\n"
            if result.get('due_date'):
                msg += f"Due Date: {result['due_date']}\n"
            if result.get('description'):
                msg += f"Description: {result['description']}\n"
            msg += f"\nTask ID: #{result['id']}"
            await query.edit_message_text(msg, parse_mode='Markdown')
        context.user_data.clear()

    async def _ask_assignee(self, query, telegram_id, context):
        """Show assignee selection buttons"""
        members = self.api.get_tenant_members(telegram_id)
        if members:
            context.user_data['task_creation_step'] = 'awaiting_assignee'
            await query.edit_message_text(
                "👤 Select assignee:",
                reply_markup=get_assignee_keyboard(members)
            )
        else:
            # No members found, skip to priority
            context.user_data['task_creation_step'] = 'awaiting_priority'
            await query.edit_message_text(
                "Select the priority:",
                reply_markup=get_priority_keyboard()
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for task creation flow)"""
        step = context.user_data.get('task_creation_step')

        if step == 'awaiting_title':
            context.user_data['task_title'] = update.message.text
            context.user_data['task_creation_step'] = 'awaiting_description'

            await update.message.reply_text(
                f"✅ Title: *{update.message.text}*\n\n"
                "Enter a description (or tap Skip):",
                parse_mode='Markdown',
                reply_markup=get_skip_keyboard('skip_description')
            )

        elif step == 'awaiting_description':
            context.user_data['task_description'] = update.message.text
            telegram_id = update.effective_user.id

            # Fetch members and show assignee selection
            members = self.api.get_tenant_members(telegram_id)
            if members:
                context.user_data['task_creation_step'] = 'awaiting_assignee'
                await update.message.reply_text(
                    "👤 Select assignee:",
                    reply_markup=get_assignee_keyboard(members)
                )
            else:
                context.user_data['task_creation_step'] = 'awaiting_priority'
                await update.message.reply_text(
                    "Select the priority:",
                    reply_markup=get_priority_keyboard()
                )

        elif step == 'awaiting_due_date':
            date_text = update.message.text.strip()
            # Validate date format
            from datetime import date as date_type
            try:
                date_type.fromisoformat(date_text)
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid date format. Please use YYYY-MM-DD format.\n"
                    "Example: 2025-12-31",
                    reply_markup=get_skip_keyboard('skip_due_date')
                )
                return

            context.user_data['task_due_date'] = date_text
            telegram_id = update.effective_user.id

            # Create the task
            result = self._create_task_from_context(telegram_id, context)

            if 'error' in result:
                await update.message.reply_text(f"❌ Failed to create task: {result['error']}")
            else:
                msg = (
                    f"✅ *Task Created!*\n\n"
                    f"Title: {result['title']}\n"
                    f"Priority: {result['priority']}\n"
                    f"Project: {result['project']}\n"
                    f"Status: {result['status_display']}\n"
                )
                if result.get('assignee'):
                    msg += f"Assignee: {result['assignee']}\n"
                if result.get('due_date'):
                    msg += f"Due Date: {result['due_date']}\n"
                if result.get('description'):
                    msg += f"Description: {result['description']}\n"
                msg += f"\nTask ID: #{result['id']}"
                await update.message.reply_text(msg, parse_mode='Markdown')
            context.user_data.clear()

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

        # Project selection (step 1)
        if data.startswith('project_'):
            project_id = int(data.replace('project_', ''))
            context.user_data['task_project_id'] = project_id
            context.user_data['task_creation_step'] = 'awaiting_title'

            # Find project name for display
            projects = context.user_data.get('projects', [])
            project_name = next(
                (p['name'] for p in projects if p['id'] == project_id),
                'Unknown'
            )

            await query.edit_message_text(
                f"📁 Project: *{project_name}*\n\n"
                "Please enter the task title:",
                parse_mode='Markdown'
            )
            return

        # Skip description
        if data == 'skip_description':
            await self._ask_assignee(query, telegram_id, context)
            return

        # Assignee selection
        if data.startswith('assignee_'):
            assignee_id = int(data.replace('assignee_', ''))
            context.user_data['task_assignee_id'] = assignee_id
            context.user_data['task_creation_step'] = 'awaiting_priority'

            await query.edit_message_text(
                "Select the priority:",
                reply_markup=get_priority_keyboard()
            )
            return

        # Skip assignee
        if data == 'skip_assignee':
            context.user_data['task_assignee_id'] = None
            context.user_data['task_creation_step'] = 'awaiting_priority'

            await query.edit_message_text(
                "Select the priority:",
                reply_markup=get_priority_keyboard()
            )
            return

        # Priority selection (during task creation)
        if data.startswith('priority_'):
            priority = data.replace('priority_', '')

            # Check if this is part of task creation flow
            if context.user_data.get('task_creation_step') == 'awaiting_priority':
                context.user_data['task_priority'] = priority
                context.user_data['task_creation_step'] = 'awaiting_due_date'

                await query.edit_message_text(
                    f"Priority: *{priority}*\n\n"
                    "Enter due date (YYYY-MM-DD) or tap Skip:",
                    parse_mode='Markdown',
                    reply_markup=get_skip_keyboard('skip_due_date')
                )
                return

        # Skip due date - create task without due date
        if data == 'skip_due_date':
            result = self._create_task_from_context(telegram_id, context)
            await self._show_task_created(query, result, context)
            return

        # Status update
        if data.startswith('status_'):
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

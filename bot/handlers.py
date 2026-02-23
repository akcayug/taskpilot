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
            welcome_msg = (
                f"Welcome back, *{user['first_name']}*! 👋\n\n"
                "🚀 *Quick Start:*\n"
                "• /tasks - View all your tasks\n"
                "• /mytasks - View only assigned to you\n"
                "• /newtask - Create a new task\n"
                "• /help - See all commands\n\n"
                "💡 *Tips:*\n"
                "• Use voice messages for task descriptions\n"
                "• Filter tasks by project name\n"
                "• Tap buttons below for quick access"
            )
            await update.message.reply_text(
                welcome_msg,
                parse_mode='Markdown',
                reply_markup=self._get_main_menu()
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

    def _get_main_menu(self):
        """Get the persistent main menu keyboard"""
        from telegram import ReplyKeyboardMarkup, KeyboardButton

        keyboard = [
            [KeyboardButton("/tasks"), KeyboardButton("/mytasks")],
            [KeyboardButton("/newtask"), KeyboardButton("/help")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "📚 *TaskPilot Bot Commands*\n\n"
            "*Task Management:*\n"
            "/tasks - View all visible tasks\n"
            "/tasks ProjectName - Filter by project\n"
            "/tasks user:John - Filter by user's first name\n"
            "/mytasks - View only your assigned tasks\n"
            "/task <id> - View task details\n"
            "/newtask - Create a new task\n\n"
            "*Account:*\n"
            "/link <code> - Link your Telegram account\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n\n"
            "*Tips:*\n"
            "• Send voice messages for task descriptions (auto-transcribed & AI-improved)\n"
            "• Managers can see all tenant tasks\n"
            "• Members can only see assigned tasks\n"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

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
                "• /tasks - View all tasks\n"
                "• /mytasks - View your assigned tasks\n"
                "• /newtask - Create a new task\n"
                "• /help - See all commands",
                reply_markup=self._get_main_menu()
            )

    async def tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tasks command with optional filters

        Usage:
        /tasks - Show all visible tasks
        /tasks ProjectName - Filter by project name
        /tasks user:John - Filter by user's first name
        /tasks user:John Doe - Filter by full name
        """
        telegram_id = update.effective_user.id

        # Check if user is linked
        user = self.api.get_user_by_telegram_id(telegram_id)
        if not user:
            await update.message.reply_text(
                "❌ You need to link your account first.\n"
                f"Visit {self.web_url} to get your linking code, then use /link <CODE>"
            )
            return

        # Parse filter arguments
        project_filter = None
        assignee_filter = None
        filter_display_name = None

        if context.args:
            filter_arg = ' '.join(context.args)

            # Check if it's a user filter (starts with "user:")
            if filter_arg.lower().startswith('user:'):
                search_name = filter_arg[5:].strip().lower()

                # Get tenant members to find user by name
                members = self.api.get_tenant_members(telegram_id)
                for member in members:
                    full_name = member.get('name', '').lower()
                    first_name = member.get('first_name', '').lower()

                    # Match by first name or full name
                    if search_name == first_name or search_name == full_name:
                        assignee_filter = member['id']
                        filter_display_name = member.get('name', search_name)
                        break

                if not assignee_filter:
                    # Show available users
                    user_list = '\n'.join([f"• {m.get('name', 'Unknown')}" for m in members[:10]])
                    await update.message.reply_text(
                        f"❌ User '{filter_arg[5:]}' not found.\n\n"
                        f"Available users:\n{user_list}\n\n"
                        "Usage: /tasks user:FirstName"
                    )
                    return
            else:
                # Treat as project name filter
                projects = self.api.get_user_projects(telegram_id)
                for project in projects:
                    if project['name'].lower() == filter_arg.lower():
                        project_filter = project['id']
                        filter_display_name = project['name']
                        break

                if not project_filter:
                    # Show available projects
                    project_list = '\n'.join([f"• {p['name']}" for p in projects[:10]])
                    await update.message.reply_text(
                        f"❌ Project '{filter_arg}' not found.\n\n"
                        f"Available projects:\n{project_list}"
                    )
                    return

        # Get tasks with filters
        response = self.api.get_user_tasks(
            telegram_id,
            project_id=project_filter,
            assignee_id=assignee_filter
        )
        tasks = response.get('tasks', [])
        is_manager = response.get('is_manager', False)

        if not tasks:
            filter_text = ""
            if project_filter:
                filter_text = " matching this filter"
            await update.message.reply_text(
                f"📋 No tasks found{filter_text}.\n\n"
                "Use /newtask to create a new task."
            )
            return

        # Format tasks
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

        # Header
        if project_filter:
            header = f"📋 *Tasks in {filter_display_name}*\n\n"
        elif assignee_filter:
            header = f"📋 *Tasks for {filter_display_name}*\n\n"
        elif is_manager:
            header = "📋 *All Tenant Tasks*\n\n"
        else:
            header = "📋 *Your Visible Tasks*\n\n"

        message = header

        for task in tasks[:10]:  # Limit to 10 tasks
            status_emoji = status_emojis.get(task['status'], '•')
            priority_emoji = priority_emojis.get(task['priority'], '•')

            message += (
                f"{status_emoji} *{task['title']}*\n"
                f"   {priority_emoji} {task['priority']} | "
                f"Project: {task['project']}\n"
                f"   Assignee: {task['assignee']}\n"
                f"   ID: #{task['id']}\n\n"
            )

        if len(tasks) > 10:
            message += f"\n_...and {len(tasks) - 10} more tasks_\n"

        message += "\n💡 Use /task <ID> to see details"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def my_tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mytasks command - only shows tasks assigned to you"""
        telegram_id = update.effective_user.id

        # Check if user is linked
        user = self.api.get_user_by_telegram_id(telegram_id)
        if not user:
            await update.message.reply_text(
                "❌ You need to link your account first.\n"
                f"Visit {self.web_url} to get your linking code, then use /link <CODE>"
            )
            return

        # Get only tasks assigned to this user
        response = self.api.get_user_tasks(telegram_id, assignee_id=user.get('id'))
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

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages for task description"""
        step = context.user_data.get('task_creation_step')

        # Only process voice in description step
        if step != 'awaiting_description':
            await update.message.reply_text(
                "🎤 Voice messages are only supported when entering task description.\n"
                "Use /newtask to create a task."
            )
            return

        telegram_id = update.effective_user.id

        await update.message.reply_text("🎤 Transcribing voice message...")

        try:
            # Download voice file
            voice_file = await update.message.voice.get_file()
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                await voice_file.download_to_drive(tmp_path)

            # Transcribe
            from .speech_client import SpeechClient
            speech_client = SpeechClient()

            if not speech_client.is_available():
                await update.message.reply_text(
                    "❌ Voice transcription is not available. AI features need to be configured.\n"
                    "Please type your description instead."
                )
                os.unlink(tmp_path)
                return

            transcribed_text = await speech_client.transcribe_voice_message(tmp_path)
            os.unlink(tmp_path)

            if not transcribed_text:
                await update.message.reply_text(
                    "❌ Failed to transcribe voice message. Please type your description instead."
                )
                return

            # Show transcription
            await update.message.reply_text(
                f"📝 *Transcribed:*\n_{transcribed_text}_\n\n"
                "✨ Improving with AI...",
                parse_mode='Markdown'
            )

            # Improve with AI (uses tenant's system prompt and default language)
            improved_text = self.api.improve_text_with_ai(telegram_id, transcribed_text, mode='fix')

            if not improved_text:
                # AI not available, ask user to confirm transcription
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton

                keyboard = [[
                    InlineKeyboardButton("✅ OK", callback_data='voice_approve_raw'),
                    InlineKeyboardButton("❌ Try Again", callback_data='voice_reject')
                ]]

                context.user_data['voice_transcribed'] = transcribed_text

                await update.message.reply_text(
                    "⚠️ AI improvement not available.\n\n"
                    f"*Transcribed text:*\n{transcribed_text}\n\n"
                    "Is this correct?",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            # Show improved version and ask for confirmation
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [[
                InlineKeyboardButton("✅ Correct", callback_data='voice_approve'),
                InlineKeyboardButton("❌ Try Again", callback_data='voice_reject')
            ]]

            context.user_data['voice_transcribed'] = transcribed_text
            context.user_data['voice_improved'] = improved_text

            await update.message.reply_text(
                f"✨ *AI Improved Description:*\n\n{improved_text}\n\n"
                "❓ *Is this correct?*",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Error processing voice message: {str(e)}\n"
                "Please type your description instead."
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

        # Voice message approval - use AI improved text
        if data == 'voice_approve':
            improved_text = context.user_data.get('voice_improved')
            if improved_text:
                context.user_data['task_description'] = improved_text
                await query.edit_message_text(
                    f"✅ *Description saved:*\n\n{improved_text}",
                    parse_mode='Markdown'
                )

                # Continue to assignee selection
                members = self.api.get_tenant_members(telegram_id)
                if members:
                    context.user_data['task_creation_step'] = 'awaiting_assignee'
                    await query.message.reply_text(
                        "👤 Select assignee:",
                        reply_markup=get_assignee_keyboard(members)
                    )
                else:
                    context.user_data['task_creation_step'] = 'awaiting_priority'
                    await query.message.reply_text(
                        "Select the priority:",
                        reply_markup=get_priority_keyboard()
                    )
            return

        # Voice message approval - use raw transcription (when AI not available)
        if data == 'voice_approve_raw':
            transcribed_text = context.user_data.get('voice_transcribed')
            if transcribed_text:
                context.user_data['task_description'] = transcribed_text
                await query.edit_message_text(
                    f"✅ *Description saved:*\n\n{transcribed_text}",
                    parse_mode='Markdown'
                )

                # Continue to assignee selection
                members = self.api.get_tenant_members(telegram_id)
                if members:
                    context.user_data['task_creation_step'] = 'awaiting_assignee'
                    await query.message.reply_text(
                        "👤 Select assignee:",
                        reply_markup=get_assignee_keyboard(members)
                    )
                else:
                    context.user_data['task_creation_step'] = 'awaiting_priority'
                    await query.message.reply_text(
                        "Select the priority:",
                        reply_markup=get_priority_keyboard()
                    )
            return

        # Voice message rejection - ask for description again
        if data == 'voice_reject':
            await query.edit_message_text(
                "❌ Description rejected.\n\n"
                "Please send a new voice message or type your description:",
                reply_markup=get_skip_keyboard('skip_description')
            )
            # Keep awaiting_description step so user can send voice or text again
            context.user_data.pop('voice_transcribed', None)
            context.user_data.pop('voice_improved', None)
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

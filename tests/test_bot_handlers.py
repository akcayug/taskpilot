import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from telegram import Update, User as TelegramUser, Message, Chat
from telegram.ext import ContextTypes
from bot.handlers import BotHandlers
from bot.api_client import TaskPilotAPI


@pytest.fixture
def api_client():
    """Mock API client"""
    return Mock(spec=TaskPilotAPI)


@pytest.fixture
def bot_handlers(api_client):
    """Create BotHandlers instance"""
    return BotHandlers(api_client, 'http://localhost:8000')


@pytest.fixture
def mock_update():
    """Create mock Update object"""
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=TelegramUser)
    update.effective_user.id = 12345
    update.effective_user.username = 'testuser'
    update.message = AsyncMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


@pytest.fixture
def mock_context():
    """Create mock Context object"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {}
    return context


@pytest.mark.asyncio
class TestStartCommand:
    """Test /start command"""

    async def test_start_command_new_user(self, bot_handlers, api_client, mock_update, mock_context):
        """Test start command for new (unlinked) user"""
        api_client.get_user_by_telegram_id.return_value = None

        await bot_handlers.start_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'Welcome to TaskPilot' in call_args
        assert '/link' in call_args

    async def test_start_command_existing_user(self, bot_handlers, api_client, mock_update, mock_context):
        """Test start command for existing (linked) user"""
        api_client.get_user_by_telegram_id.return_value = {
            'id': 1,
            'first_name': 'John',
            'email': 'john@example.com'
        }

        await bot_handlers.start_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'Welcome back, John' in call_args
        assert '/mytasks' in call_args


@pytest.mark.asyncio
class TestLinkCommand:
    """Test /link command"""

    async def test_link_command_no_code(self, bot_handlers, api_client, mock_update, mock_context):
        """Test link command without code"""
        await bot_handlers.link_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'provide your linking code' in call_args

    async def test_link_command_success(self, bot_handlers, api_client, mock_update, mock_context):
        """Test successful account linking"""
        mock_context.args = ['ABC123']
        api_client.link_telegram_account.return_value = {
            'success': True,
            'user_id': 1
        }

        await bot_handlers.link_command(mock_update, mock_context)

        api_client.link_telegram_account.assert_called_once_with(
            'ABC123',
            12345,
            'testuser'
        )

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'linked successfully' in call_args

    async def test_link_command_failure(self, bot_handlers, api_client, mock_update, mock_context):
        """Test failed account linking"""
        mock_context.args = ['INVALID']
        api_client.link_telegram_account.return_value = {
            'error': 'Invalid code'
        }

        await bot_handlers.link_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'Failed to link' in call_args


@pytest.mark.asyncio
class TestMyTasksCommand:
    """Test /mytasks command"""

    async def test_my_tasks_unlinked_user(self, bot_handlers, api_client, mock_update, mock_context):
        """Test my tasks for unlinked user"""
        api_client.get_user_by_telegram_id.return_value = None

        await bot_handlers.my_tasks_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'need to link your account' in call_args

    async def test_my_tasks_no_tasks(self, bot_handlers, api_client, mock_update, mock_context):
        """Test my tasks when user has no tasks"""
        api_client.get_user_by_telegram_id.return_value = {'id': 1}
        api_client.get_user_tasks.return_value = []

        await bot_handlers.my_tasks_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'no assigned tasks' in call_args

    async def test_my_tasks_with_tasks(self, bot_handlers, api_client, mock_update, mock_context):
        """Test my tasks with tasks present"""
        api_client.get_user_by_telegram_id.return_value = {'id': 1}
        api_client.get_user_tasks.return_value = [
            {
                'id': 1,
                'title': 'Test Task',
                'status': 'TODO',
                'status_display': 'To Do',
                'priority': 'HIGH',
                'project': 'Test Project'
            }
        ]

        await bot_handlers.my_tasks_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'Test Task' in call_args
        assert 'HIGH' in call_args


@pytest.mark.asyncio
class TestNewTaskCommand:
    """Test /newtask command"""

    async def test_new_task_unlinked_user(self, bot_handlers, api_client, mock_update, mock_context):
        """Test new task for unlinked user"""
        api_client.get_user_by_telegram_id.return_value = None

        await bot_handlers.new_task_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'need to link your account' in call_args

    async def test_new_task_no_projects(self, bot_handlers, api_client, mock_update, mock_context):
        """Test new task when user has no projects"""
        api_client.get_user_by_telegram_id.return_value = {'id': 1}
        api_client.get_user_projects.return_value = []

        await bot_handlers.new_task_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'No projects found' in call_args

    async def test_new_task_start_flow(self, bot_handlers, api_client, mock_update, mock_context):
        """Test new task starts creation flow with project selection"""
        api_client.get_user_by_telegram_id.return_value = {'id': 1}
        api_client.get_user_projects.return_value = [
            {'id': 1, 'name': 'Test Project'}
        ]

        await bot_handlers.new_task_command(mock_update, mock_context)

        assert mock_context.user_data['task_creation_step'] == 'awaiting_project'
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'Select a project' in call_args


@pytest.mark.asyncio
class TestTaskCommand:
    """Test /task command"""

    async def test_task_command_no_id(self, bot_handlers, api_client, mock_update, mock_context):
        """Test task command without ID"""
        await bot_handlers.task_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'provide a task ID' in call_args

    async def test_task_command_invalid_id(self, bot_handlers, api_client, mock_update, mock_context):
        """Test task command with invalid ID"""
        mock_context.args = ['invalid']

        await bot_handlers.task_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'Invalid task ID' in call_args

    async def test_task_command_success(self, bot_handlers, api_client, mock_update, mock_context):
        """Test task command with valid ID"""
        mock_context.args = ['1']
        api_client.get_user_by_telegram_id.return_value = {'id': 1}
        api_client.get_task_details.return_value = {
            'id': 1,
            'title': 'Test Task',
            'description': 'Test description',
            'status': 'TODO',
            'status_display': 'To Do',
            'priority': 'HIGH',
            'project': 'Test Project',
            'assignee': 'John Doe',
            'due_date': None
        }

        await bot_handlers.task_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert 'Test Task' in call_args
        assert 'Test Project' in call_args


@pytest.mark.asyncio
class TestHandleMessage:
    """Test message handling"""

    async def test_handle_message_task_title(self, bot_handlers, api_client, mock_update, mock_context):
        """Test handling task title input moves to description step"""
        mock_context.user_data['task_creation_step'] = 'awaiting_title'
        mock_update.message.text = 'New Task Title'

        await bot_handlers.handle_message(mock_update, mock_context)

        assert mock_context.user_data['task_title'] == 'New Task Title'
        assert mock_context.user_data['task_creation_step'] == 'awaiting_description'
        mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
class TestHandleCallback:
    """Test callback query handling"""

    async def test_handle_callback_cancel(self, bot_handlers, api_client, mock_update, mock_context):
        """Test cancel callback"""
        mock_update.callback_query = AsyncMock()
        mock_update.callback_query.data = 'cancel'
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()

        await bot_handlers.handle_callback(mock_update, mock_context)

        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        assert 'cancelled' in mock_update.callback_query.edit_message_text.call_args[0][0]

    async def test_handle_callback_priority_selection(self, bot_handlers, api_client, mock_update, mock_context):
        """Test priority selection callback moves to due date step"""
        mock_update.callback_query = AsyncMock()
        mock_update.callback_query.data = 'priority_HIGH'
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()

        mock_context.user_data = {
            'task_creation_step': 'awaiting_priority',
            'task_title': 'Test Task',
            'task_project_id': 1,
            'projects': [{'id': 1, 'name': 'Test Project'}]
        }

        await bot_handlers.handle_callback(mock_update, mock_context)

        assert mock_context.user_data['task_priority'] == 'HIGH'
        assert mock_context.user_data['task_creation_step'] == 'awaiting_due_date'
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert 'due date' in call_args.lower()

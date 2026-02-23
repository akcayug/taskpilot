import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from .handlers import BotHandlers
from .api_client import TaskPilotAPI

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot"""
    # Get configuration from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    web_url = os.getenv('WEB_URL', 'http://localhost:8000')

    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

    # Initialize API client
    api_client = TaskPilotAPI(web_url)

    # Create application
    application = Application.builder().token(bot_token).build()

    # Initialize handlers
    bot_handlers = BotHandlers(api_client, web_url)

    # Register command handlers
    application.add_handler(CommandHandler("start", bot_handlers.start_command))
    application.add_handler(CommandHandler("help", bot_handlers.help_command))
    application.add_handler(CommandHandler("link", bot_handlers.link_command))
    application.add_handler(CommandHandler("tasks", bot_handlers.tasks_command))
    application.add_handler(CommandHandler("mytasks", bot_handlers.my_tasks_command))
    application.add_handler(CommandHandler("newtask", bot_handlers.new_task_command))
    application.add_handler(CommandHandler("task", bot_handlers.task_command))

    # Register voice message handler (for task description)
    application.add_handler(MessageHandler(
        filters.VOICE,
        bot_handlers.handle_voice
    ))

    # Register text message handler (for task creation flow)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        bot_handlers.handle_message
    ))

    # Register callback query handler
    application.add_handler(CallbackQueryHandler(bot_handlers.handle_callback))

    # Start the bot
    logger.info("Starting TaskPilot bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

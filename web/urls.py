from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    DashboardView,
    SettingsView,
    TaskFormDemoView,
    AITextSuggestionAPIView,
    TaskListAPIView,
    TaskInlineUpdateAPIView,
    ExportTasksView,
    TelegramLinkAPIView,
    TelegramUserAPIView,
    TelegramTasksAPIView,
    TelegramTaskDetailAPIView,
    TelegramTaskStatusAPIView,
    TelegramMembersAPIView,
    TelegramProjectsAPIView,
    TelegramSettingsAPIView
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('ai-demo/', TaskFormDemoView.as_view(), name='ai_demo'),
    path('api/tasks/', TaskListAPIView.as_view(), name='api_tasks'),
    path('api/tasks/<int:task_id>/', TaskInlineUpdateAPIView.as_view(), name='task_inline_update'),
    path('api/ai-suggest/', AITextSuggestionAPIView.as_view(), name='ai_suggest'),
    path('export/tasks/', ExportTasksView.as_view(), name='export_tasks'),

    # Telegram Bot API endpoints
    path('api/telegram/link', TelegramLinkAPIView.as_view(), name='telegram_link_api'),
    path('api/telegram/user/<int:telegram_id>/', TelegramUserAPIView.as_view(), name='telegram_user_api'),
    path('api/telegram/tasks', TelegramTasksAPIView.as_view(), name='telegram_tasks_api'),
    path('api/telegram/tasks/<int:task_id>/', TelegramTaskDetailAPIView.as_view(), name='telegram_task_detail_api'),
    path('api/telegram/tasks/<int:task_id>/status', TelegramTaskStatusAPIView.as_view(), name='telegram_task_status_api'),
    path('api/telegram/members', TelegramMembersAPIView.as_view(), name='telegram_members_api'),
    path('api/telegram/projects', TelegramProjectsAPIView.as_view(), name='telegram_projects_api'),
    path('api/telegram/settings', TelegramSettingsAPIView.as_view(), name='telegram_settings_api'),
]

from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    DebugTenantView,
    DashboardView,
    SettingsView,
    TaskFormView,
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
    TelegramSettingsAPIView,
    ProjectDetailView,
    SnapshotCreateView
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('debug/tenant/', DebugTenantView.as_view(), name='debug_tenant'),
    path('settings/', SettingsView.as_view(), name='settings'),

    # Task form (create/edit)
    path('tasks/new/', TaskFormView.as_view(), name='task_create'),
    path('tasks/<int:task_id>/edit/', TaskFormView.as_view(), name='task_edit'),

    # API endpoints
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

    # Project financial views
    path('projects/<int:project_id>/', ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:project_id>/snapshots/create/', SnapshotCreateView.as_view(), name='snapshot_create'),
]

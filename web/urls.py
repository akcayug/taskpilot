from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    DashboardView,
    TaskListAPIView,
    ExportTasksView,
    TelegramLinkAPIView,
    TelegramUserAPIView,
    TelegramTasksAPIView,
    TelegramTaskDetailAPIView,
    TelegramTaskStatusAPIView,
    TelegramMembersAPIView,
    TelegramProjectsAPIView
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/tasks/', TaskListAPIView.as_view(), name='api_tasks'),
    path('export/tasks/', ExportTasksView.as_view(), name='export_tasks'),

    # Telegram Bot API endpoints
    path('api/telegram/link', TelegramLinkAPIView.as_view(), name='telegram_link_api'),
    path('api/telegram/user/<int:telegram_id>/', TelegramUserAPIView.as_view(), name='telegram_user_api'),
    path('api/telegram/tasks', TelegramTasksAPIView.as_view(), name='telegram_tasks_api'),
    path('api/telegram/tasks/<int:task_id>/', TelegramTaskDetailAPIView.as_view(), name='telegram_task_detail_api'),
    path('api/telegram/tasks/<int:task_id>/status', TelegramTaskStatusAPIView.as_view(), name='telegram_task_status_api'),
    path('api/telegram/members', TelegramMembersAPIView.as_view(), name='telegram_members_api'),
    path('api/telegram/projects', TelegramProjectsAPIView.as_view(), name='telegram_projects_api'),
]

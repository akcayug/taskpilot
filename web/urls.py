from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    DashboardView,
    TaskListAPIView,
    ExportTasksView
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/tasks/', TaskListAPIView.as_view(), name='api_tasks'),
    path('export/tasks/', ExportTasksView.as_view(), name='export_tasks'),
]

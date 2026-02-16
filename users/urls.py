from django.urls import path
from .views import (
    InviteUserView,
    AcceptInviteView,
    LinkTelegramView,
    RefreshTelegramCodeView
)

urlpatterns = [
    path('invite/send/', InviteUserView.as_view(), name='invite_user'),
    path('invite/accept/<str:token>/', AcceptInviteView.as_view(), name='accept_invite'),
    path('telegram/link/', LinkTelegramView.as_view(), name='link_telegram'),
    path('telegram/refresh/', RefreshTelegramCodeView.as_view(), name='refresh_telegram_code'),
]

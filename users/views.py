from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.views import View
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from core.models import TenantMembership
from .models import Invitation, TelegramLinkToken
from .tasks import send_invitation_email

User = get_user_model()


class InviteUserView(LoginRequiredMixin, View):
    """Create and send invitation"""
    login_url = 'login'

    def post(self, request):
        email = request.POST.get('email')
        role = request.POST.get('role', TenantMembership.Role.MEMBER)
        tenant = getattr(request, 'tenant', None)

        if not tenant:
            return JsonResponse({'error': 'No tenant found'}, status=403)

        # Check if user has permission (must be manager)
        tenant_role = getattr(request, 'tenant_role', None)
        if tenant_role != TenantMembership.Role.MANAGER:
            return JsonResponse({'error': 'Only managers can invite users'}, status=403)

        # Check if invitation already exists
        if Invitation.objects.filter(tenant=tenant, email=email, accepted=False).exists():
            return JsonResponse({'error': 'Invitation already sent to this email'}, status=400)

        # Check if user already exists in tenant
        if User.objects.filter(email=email, memberships__tenant=tenant).exists():
            return JsonResponse({'error': 'User already in tenant'}, status=400)

        # Create invitation
        invitation = Invitation.objects.create(
            tenant=tenant,
            email=email,
            role=role,
            invited_by=request.user
        )

        # Send invitation email asynchronously
        send_invitation_email.delay(invitation.id)

        return JsonResponse({
            'success': True,
            'message': f'Invitation sent to {email}'
        })


class AcceptInviteView(View):
    """Accept invitation and create user account"""
    template_name = 'accept_invite.html'

    def get(self, request, token):
        invitation = get_object_or_404(Invitation, token=token)

        # Check if invitation is valid
        if invitation.accepted:
            return render(request, self.template_name, {
                'error': 'This invitation has already been accepted'
            })

        if invitation.is_expired():
            return render(request, self.template_name, {
                'error': 'This invitation has expired'
            })

        return render(request, self.template_name, {
            'invitation': invitation
        })

    @transaction.atomic
    def post(self, request, token):
        invitation = get_object_or_404(Invitation, token=token)

        # Validate invitation
        if invitation.accepted:
            return render(request, self.template_name, {
                'error': 'This invitation has already been accepted'
            })

        if invitation.is_expired():
            return render(request, self.template_name, {
                'error': 'This invitation has expired'
            })

        # Get form data
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        # Validate passwords
        if password != password_confirm:
            return render(request, self.template_name, {
                'invitation': invitation,
                'error': 'Passwords do not match'
            })

        if len(password) < 8:
            return render(request, self.template_name, {
                'invitation': invitation,
                'error': 'Password must be at least 8 characters'
            })

        # Create user
        user = User.objects.create_user(
            email=invitation.email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Create tenant membership
        TenantMembership.objects.create(
            user=user,
            tenant=invitation.tenant,
            role=invitation.role
        )

        # Mark invitation as accepted
        invitation.accepted = True
        invitation.accepted_at = timezone.now()
        invitation.save()

        return render(request, 'invite_accepted.html', {
            'user': user,
            'tenant': invitation.tenant
        })


class LinkTelegramView(LoginRequiredMixin, TemplateView):
    """Display Telegram linking code"""
    template_name = 'link_telegram.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get or create Telegram link token
        token, created = TelegramLinkToken.objects.get_or_create(
            user=self.request.user
        )

        # If token expired, delete and create new one
        if token.is_expired():
            token.delete()
            token = TelegramLinkToken.objects.create(user=self.request.user)

        context['link_code'] = token.code
        context['telegram_linked'] = self.request.user.telegram_id is not None

        return context


class RefreshTelegramCodeView(LoginRequiredMixin, View):
    """Refresh Telegram linking code"""
    login_url = 'login'

    def post(self, request):
        # Delete existing token
        TelegramLinkToken.objects.filter(user=request.user).delete()

        # Create new token
        token = TelegramLinkToken.objects.create(user=request.user)

        return JsonResponse({
            'success': True,
            'code': token.code
        })

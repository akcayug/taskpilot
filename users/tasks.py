from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Invitation


@shared_task
def send_invitation_email(invitation_id):
    """
    Send invitation email via Celery
    """
    try:
        invitation = Invitation.objects.select_related('tenant', 'invited_by').get(id=invitation_id)

        # Build invitation URL
        base_url = settings.BASE_URL if hasattr(settings, 'BASE_URL') else 'http://localhost:8000'
        invitation_url = f"{base_url}/invite/accept/{invitation.token}"

        # Render email content
        context = {
            'invitation': invitation,
            'invitation_url': invitation_url,
            'tenant_name': invitation.tenant.name,
            'invited_by': invitation.invited_by.get_full_name() if invitation.invited_by else 'TaskPilot',
            'expires_days': 7
        }

        html_message = render_to_string('invite_email.html', context)
        text_message = f"""
You've been invited to join {invitation.tenant.name} on TaskPilot!

Click the link below to accept your invitation:
{invitation_url}

This invitation will expire in 7 days.

If you didn't expect this invitation, you can safely ignore this email.
        """

        # Send email
        send_mail(
            subject=f"Invitation to join {invitation.tenant.name} on TaskPilot",
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
            html_message=html_message,
            fail_silently=False
        )

        return f"Invitation email sent to {invitation.email}"

    except Invitation.DoesNotExist:
        return f"Invitation {invitation_id} not found"
    except Exception as e:
        return f"Error sending invitation email: {str(e)}"

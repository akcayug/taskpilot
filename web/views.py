import csv
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.views.generic import TemplateView, CreateView, UpdateView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.urls import reverse_lazy
from tasks.models import Task, Project, ProjectFinancialSnapshot
from core.models import TenantSettings, User
from .llm_client import WebLLMClient
from decimal import Decimal


class LoginView(View):
    """User login view"""
    template_name = 'login.html'

    def get(self, request):
        # Redirect to dashboard if already logged in
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            return render(request, self.template_name, {
                'error': 'Invalid email or password'
            })


class LogoutView(View):
    """User logout view"""

    def post(self, request):
        logout(request)
        return redirect('login')


class DebugTenantView(LoginRequiredMixin, View):
    """Debug view to check tenant and role"""
    login_url = 'login'

    def get(self, request):
        from core.models import TenantMembership

        tenant = getattr(request, 'tenant', None)
        tenant_role = getattr(request, 'tenant_role', None)

        # Get membership directly
        membership = TenantMembership.objects.filter(user=request.user).first()

        debug_info = {
            'user_email': request.user.email,
            'user_is_authenticated': request.user.is_authenticated,
            'request_tenant': str(tenant) if tenant else 'None',
            'request_tenant_role': str(tenant_role) if tenant_role else 'None',
            'tenant_role_type': str(type(tenant_role)),
            'db_membership_exists': membership is not None,
        }

        if membership:
            debug_info.update({
                'db_tenant_name': membership.tenant.name,
                'db_tenant_active': membership.tenant.is_active,
                'db_role': membership.role,
                'db_role_type': str(type(membership.role)),
                'role_comparison_MANAGER': membership.role == 'MANAGER',
                'role_comparison_MEMBER': membership.role == 'MEMBER',
            })

        return JsonResponse(debug_info, json_dumps_params={'indent': 2})


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get tenant from request (set by TenantMiddleware)
        tenant = getattr(self.request, 'tenant', None)

        if tenant:
            # Get task statistics - members see only their own tasks
            tasks = Task.objects.filter(tenant=tenant)
            tenant_role = getattr(self.request, 'tenant_role', None)
            if tenant_role != 'MANAGER':
                tasks = tasks.filter(assignee=self.request.user)
            context['total_tasks'] = tasks.count()
            context['todo_count'] = tasks.filter(status=Task.Status.TODO).count()
            context['in_progress_count'] = tasks.filter(status=Task.Status.IN_PROGRESS).count()
            context['done_count'] = tasks.filter(status=Task.Status.DONE).count()
        else:
            context['total_tasks'] = 0
            context['todo_count'] = 0
            context['in_progress_count'] = 0
            context['done_count'] = 0

        return context


class TaskFormView(LoginRequiredMixin, TemplateView):
    """Task creation and editing view"""
    template_name = 'task_form.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request, 'tenant', None)
        task_id = kwargs.get('task_id')

        if tenant:
            # Get AI settings
            settings, _ = TenantSettings.objects.get_or_create(tenant=tenant)
            context['ai_enabled'] = settings.ai_enabled

            # Get projects for dropdown
            context['projects'] = Project.objects.filter(tenant=tenant).order_by('name')

            # Get team members for assignee dropdown
            from core.models import TenantMembership
            memberships = TenantMembership.objects.filter(tenant=tenant).select_related('user')
            context['team_members'] = [m.user for m in memberships]

            # If editing, get the task
            if task_id:
                context['task'] = get_object_or_404(Task, id=task_id, tenant=tenant)

        return context

    def post(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        tenant_role = getattr(request, 'tenant_role', None)
        task_id = kwargs.get('task_id')

        if not tenant:
            messages.error(request, "No tenant found")
            return redirect('dashboard')

        # Get form data
        project_id = request.POST.get('project')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        status = request.POST.get('status', 'TODO')
        priority = request.POST.get('priority', 'MEDIUM')
        assignee_id = request.POST.get('assignee')
        due_date = request.POST.get('due_date') or None
        action = request.POST.get('action', 'save')

        # Validate required fields
        if not project_id or not title:
            messages.error(request, "Project and Title are required")
            return self.get(request, *args, **kwargs)

        try:
            project = Project.objects.get(id=project_id, tenant=tenant)
        except Project.DoesNotExist:
            messages.error(request, "Invalid project selected")
            return self.get(request, *args, **kwargs)

        # Get assignee if provided
        assignee = None
        if assignee_id:
            try:
                assignee = User.objects.get(id=assignee_id)
                # Verify assignee belongs to this tenant
                from core.models import TenantMembership
                if not TenantMembership.objects.filter(user=assignee, tenant=tenant).exists():
                    messages.error(request, "Invalid assignee selected")
                    return self.get(request, *args, **kwargs)
            except User.DoesNotExist:
                messages.error(request, "Invalid assignee selected")
                return self.get(request, *args, **kwargs)

        # Create or update task
        if task_id:
            # Update existing task
            task = get_object_or_404(Task, id=task_id, tenant=tenant)

            # Check permissions: members can only edit their own tasks
            if tenant_role != 'MANAGER' and task.assignee != request.user:
                messages.error(request, "You don't have permission to edit this task")
                return redirect('dashboard')

            # Members cannot change assignee
            if tenant_role != 'MANAGER' and assignee and assignee != task.assignee:
                messages.error(request, "Only managers can reassign tasks")
                assignee = task.assignee

            task.project = project
            task.title = title
            task.description = description
            task.status = status
            task.priority = priority
            task.assignee = assignee
            task.due_date = due_date
            task.save()

            messages.success(request, f"Task '{task.title}' updated successfully")
            return redirect('dashboard')

        else:
            # Create new task
            task = Task.objects.create(
                tenant=tenant,
                project=project,
                title=title,
                description=description,
                status=status,
                priority=priority,
                assignee=assignee,
                due_date=due_date
            )

            messages.success(request, f"Task '{task.title}' created successfully")

            # Check if "Save & New" was clicked
            if action == 'save_and_new':
                return redirect('task_create')
            else:
                return redirect('dashboard')


class TaskFormDemoView(LoginRequiredMixin, TemplateView):
    """Demo view for AI helper on task forms"""
    template_name = 'task_form_demo.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request, 'tenant', None)

        if tenant:
            settings, created = TenantSettings.objects.get_or_create(tenant=tenant)
            context['ai_enabled'] = settings.ai_enabled
        else:
            context['ai_enabled'] = False

        return context


class SettingsView(LoginRequiredMixin, View):
    """Tenant settings view (manager-only)"""
    login_url = 'login'
    template_name = 'settings.html'

    def dispatch(self, request, *args, **kwargs):
        # Check if user is a manager
        tenant = getattr(request, 'tenant', None)
        tenant_role = getattr(request, 'tenant_role', None)

        if not tenant or tenant_role != 'MANAGER':
            return HttpResponse('Permission denied. Only managers can access settings.', status=403)

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        tenant = getattr(request, 'tenant')

        # Get or create settings for tenant
        settings, created = TenantSettings.objects.get_or_create(tenant=tenant)

        return render(request, self.template_name, {
            'settings': settings,
            'ai_modes': TenantSettings.AIMode.choices,
            'languages': TenantSettings.Language.choices
        })

    def post(self, request):
        tenant = getattr(request, 'tenant')

        # Get or create settings for tenant
        settings, created = TenantSettings.objects.get_or_create(tenant=tenant)

        # Validate and update settings
        try:
            # AI enabled (checkbox)
            settings.ai_enabled = request.POST.get('ai_enabled') == 'on'

            # AI system prompt (max 500 chars)
            ai_system_prompt = request.POST.get('ai_system_prompt', '').strip()
            if not ai_system_prompt:
                messages.error(request, 'AI system prompt is required')
                return self.get(request)
            if len(ai_system_prompt) > 500:
                messages.error(request, 'AI system prompt must be 500 characters or less')
                return self.get(request)
            settings.ai_system_prompt = ai_system_prompt

            # AI default mode
            ai_default_mode = request.POST.get('ai_default_mode')
            if ai_default_mode not in [choice[0] for choice in TenantSettings.AIMode.choices]:
                messages.error(request, 'Invalid AI mode selected')
                return self.get(request)
            settings.ai_default_mode = ai_default_mode

            # AI default language
            ai_default_language = request.POST.get('ai_default_language')
            if ai_default_language not in [choice[0] for choice in TenantSettings.Language.choices]:
                messages.error(request, 'Invalid language selected')
                return self.get(request)
            settings.ai_default_language = ai_default_language

            # Save settings
            settings.save()

            messages.success(request, 'Settings saved successfully')
            return redirect('settings')

        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')
            return self.get(request)


class AITextSuggestionAPIView(LoginRequiredMixin, View):
    """API endpoint for AI text suggestions"""
    login_url = 'login'

    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)

        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()
            mode = data.get('mode', 'fix')  # 'fix' or 'translate'
            field = data.get('field', 'title')  # 'title' or 'description'

            logger.info(f"AI suggestion request: field={field}, mode={mode}, text_length={len(text)}")

            if not text:
                return JsonResponse({'error': 'Text is required'}, status=400)

            tenant = getattr(request, 'tenant', None)
            if not tenant:
                logger.error("No tenant found for AI request")
                return JsonResponse({'error': 'No tenant found'}, status=403)

            # Get tenant settings
            settings, created = TenantSettings.objects.get_or_create(tenant=tenant)

            # Check if AI is enabled
            if not settings.ai_enabled:
                logger.warning(f"AI request rejected: AI not enabled for tenant {tenant.name}")
                return JsonResponse({'error': 'AI features are not enabled. Please enable in Settings.'}, status=403)

            # Initialize LLM client
            llm_client = WebLLMClient()

            if not llm_client.is_available():
                return JsonResponse({'error': 'AI service is not configured'}, status=500)

            # Get improved text from LLM
            result = llm_client.improve_text(
                text=text,
                system_prompt=settings.ai_system_prompt,
                mode=mode,
                target_language=settings.ai_default_language
            )

            if not result['success']:
                logger.error(f"AI processing failed: {result.get('error')}")
                return JsonResponse({'error': result.get('error', 'Failed to process text')}, status=500)

            # Create audit log
            from audit.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='AI_SUGGESTION',
                resource_type='Task',
                resource_id=None,
                changes={
                    'field': field,
                    'mode': mode,
                    'original': text,
                    'suggested': result['text']
                }
            )

            return JsonResponse({
                'original': text,
                'suggested': result['text'],
                'mode': mode
            })

        except json.JSONDecodeError:
            logger.error("Invalid JSON in AI request")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.exception(f"Unexpected error in AI suggestion: {e}")
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


class TaskListAPIView(LoginRequiredMixin, View):
    """API endpoint for DataTables to fetch tasks"""
    login_url = 'login'

    def get(self, request):
        tenant = getattr(request, 'tenant', None)

        if not tenant:
            return JsonResponse({
                'draw': int(request.GET.get('draw', 1)),
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            })

        # Get DataTables parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 25))
        search_value = request.GET.get('search[value]', '')

        # Filters
        status_filter = request.GET.get('status', '')
        priority_filter = request.GET.get('priority', '')
        assignee_filter = request.GET.get('assignee', '')

        # Base queryset - members see only their own tasks
        queryset = Task.objects.filter(tenant=tenant).select_related(
            'project', 'assignee'
        )
        tenant_role = getattr(request, 'tenant_role', None)
        if tenant_role != 'MANAGER':
            queryset = queryset.filter(assignee=request.user)

        # Apply filters
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if assignee_filter:
            queryset = queryset.filter(assignee_id=assignee_filter)

        # Search
        if search_value:
            queryset = queryset.filter(
                Q(title__icontains=search_value) |
                Q(description__icontains=search_value) |
                Q(project__name__icontains=search_value)
            )

        # Total records (respecting role-based access)
        base_qs = Task.objects.filter(tenant=tenant)
        if tenant_role != 'MANAGER':
            base_qs = base_qs.filter(assignee=request.user)
        records_total = base_qs.count()
        records_filtered = queryset.count()

        # Sorting
        order_column_idx = int(request.GET.get('order[0][column]', 0))
        order_dir = request.GET.get('order[0][dir]', 'desc')

        column_map = {
            0: 'title',
            1: 'project__name',
            2: 'assignee__email',
            3: 'due_date',
            4: 'priority',
            5: 'status',
            6: 'created_at'
        }

        order_column = column_map.get(order_column_idx, 'created_at')
        if order_dir == 'desc':
            order_column = f'-{order_column}'

        queryset = queryset.order_by(order_column)

        # Pagination
        tasks = queryset[start:start + length]

        # Format data
        data = []
        for task in tasks:
            data.append({
                'id': task.id,
                'title': task.title,
                'project': task.project.name,
                'project_id': task.project.id,
                'assignee': task.assignee.get_full_name() if task.assignee else 'Unassigned',
                'assignee_id': task.assignee_id,
                'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                'priority': task.get_priority_display(),
                'priority_value': task.priority,
                'status': task.get_status_display(),
                'status_value': task.status,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat()
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data
        })


class TaskInlineUpdateAPIView(LoginRequiredMixin, View):
    """API endpoint for inline task editing"""
    login_url = 'login'

    def patch(self, request, task_id):
        try:
            data = json.loads(request.body)
            tenant = getattr(request, 'tenant', None)
            tenant_role = getattr(request, 'tenant_role', None)

            if not tenant:
                return JsonResponse({'error': 'No tenant found'}, status=403)

            # Get task
            try:
                task = Task.objects.select_related('project', 'assignee').get(
                    id=task_id,
                    tenant=tenant
                )
            except Task.DoesNotExist:
                return JsonResponse({'error': 'Task not found'}, status=404)

            # Permission check: members can only edit their own assigned tasks
            if tenant_role != 'MANAGER' and task.assignee != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)

            # Conflict detection: check updated_at timestamp
            client_updated_at = data.get('updated_at')
            if client_updated_at:
                from datetime import datetime
                try:
                    client_dt = datetime.fromisoformat(client_updated_at.replace('Z', '+00:00'))
                    if task.updated_at.replace(tzinfo=None) > client_dt.replace(tzinfo=None):
                        return JsonResponse({
                            'error': 'Task has been modified by another user. Please refresh and try again.'
                        }, status=409)
                except (ValueError, AttributeError):
                    pass

            # Store old values for audit log
            old_values = {
                'title': task.title,
                'status': task.status,
                'priority': task.priority,
                'assignee_id': task.assignee_id,
                'due_date': str(task.due_date) if task.due_date else None,
            }

            # Update allowed fields
            updated_fields = []

            # Title (max 100 chars, all users can edit)
            if 'title' in data:
                new_title = data['title'][:100]  # Enforce max length
                if task.title != new_title:
                    task.title = new_title
                    updated_fields.append('title')

            # Status (validate transitions)
            if 'status' in data:
                from tasks.services import TaskService
                new_status = data['status']
                if task.status != new_status:
                    try:
                        TaskService.validate_status_transition(task, new_status)
                        task.status = new_status
                        updated_fields.append('status')
                    except ValidationError as e:
                        return JsonResponse({'error': str(e)}, status=400)

            # Priority
            if 'priority' in data:
                new_priority = data['priority']
                if new_priority in [c[0] for c in Task.Priority.choices]:
                    if task.priority != new_priority:
                        task.priority = new_priority
                        updated_fields.append('priority')

            # Due date
            if 'due_date' in data:
                from datetime import date as date_type
                new_due_date = data['due_date']
                parsed_due_date = None
                if new_due_date:
                    try:
                        parsed_due_date = date_type.fromisoformat(new_due_date)
                    except ValueError:
                        return JsonResponse({'error': 'Invalid date format'}, status=400)
                if task.due_date != parsed_due_date:
                    task.due_date = parsed_due_date
                    updated_fields.append('due_date')

            # Assignee (manager only)
            if 'assignee_id' in data:
                if tenant_role != 'MANAGER':
                    return JsonResponse({'error': 'Only managers can change assignee'}, status=403)

                new_assignee_id = data['assignee_id']
                if new_assignee_id:
                    from tasks.services import TaskService
                    from core.models import User
                    try:
                        new_assignee = User.objects.get(id=new_assignee_id)
                        TaskService.validate_assignee_in_tenant(task, new_assignee)
                        if task.assignee_id != new_assignee_id:
                            task.assignee = new_assignee
                            updated_fields.append('assignee')
                    except User.DoesNotExist:
                        return JsonResponse({'error': 'Assignee not found'}, status=400)
                    except ValidationError as e:
                        return JsonResponse({'error': str(e)}, status=400)
                else:
                    if task.assignee_id is not None:
                        task.assignee = None
                        updated_fields.append('assignee')

            # Save if any fields changed
            if updated_fields:
                task.save()

                # Create audit log
                from audit.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action='UPDATE',
                    resource_type='Task',
                    resource_id=task.id,
                    changes={
                        'updated_fields': updated_fields,
                        'old_values': old_values,
                        'new_values': {
                            'title': task.title,
                            'status': task.status,
                            'priority': task.priority,
                            'assignee_id': task.assignee_id,
                            'due_date': str(task.due_date) if task.due_date else None,
                        }
                    }
                )

            # Return updated task data
            return JsonResponse({
                'id': task.id,
                'title': task.title,
                'project': task.project.name,
                'assignee': task.assignee.get_full_name() if task.assignee else 'Unassigned',
                'assignee_id': task.assignee_id,
                'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                'priority': task.get_priority_display(),
                'priority_value': task.priority,
                'status': task.get_status_display(),
                'status_value': task.status,
                'updated_at': task.updated_at.isoformat()
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class ExportTasksView(LoginRequiredMixin, View):
    """Export tasks to CSV"""
    login_url = 'login'

    def get(self, request):
        tenant = getattr(request, 'tenant', None)

        if not tenant:
            return HttpResponse('No tenant found', status=403)

        # Get filters
        status_filter = request.GET.get('status', '')
        priority_filter = request.GET.get('priority', '')
        assignee_filter = request.GET.get('assignee', '')

        # Base queryset - members see only their own tasks
        queryset = Task.objects.filter(tenant=tenant).select_related(
            'project', 'assignee'
        )
        tenant_role = getattr(request, 'tenant_role', None)
        if tenant_role != 'MANAGER':
            queryset = queryset.filter(assignee=request.user)

        # Apply filters
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if assignee_filter:
            queryset = queryset.filter(assignee_id=assignee_filter)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tasks.csv"'

        writer = csv.writer(response)
        writer.writerow(['Title', 'Project', 'Assignee', 'Due Date', 'Priority', 'Status', 'Created At'])

        for task in queryset:
            writer.writerow([
                task.title,
                task.project.name,
                task.assignee.get_full_name() if task.assignee else 'Unassigned',
                task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                task.get_priority_display(),
                task.get_status_display(),
                task.created_at.strftime('%Y-%m-%d %H:%M')
            ])

        return response


class MembersAPIView(LoginRequiredMixin, View):
    """API endpoint to get tenant members for dropdowns"""
    login_url = 'login'

    def get(self, request):
        tenant = getattr(request, 'tenant', None)

        if not tenant:
            return JsonResponse({'error': 'No tenant found'}, status=403)

        # Get all members of the tenant
        from core.models import TenantMembership
        memberships = TenantMembership.objects.filter(
            tenant=tenant
        ).select_related('user')

        members = []
        for membership in memberships:
            user = membership.user
            members.append({
                'id': user.id,
                'full_name': user.get_full_name() or user.email,
                'email': user.email,
                'role': membership.role
            })

        return JsonResponse({'members': members})


# Telegram Bot API Views

@method_decorator(csrf_exempt, name='dispatch')
class TelegramLinkAPIView(View):
    """API endpoint for linking Telegram account"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            code = data.get('code')
            telegram_id = data.get('telegram_id')
            telegram_username = data.get('telegram_username', '')

            # Find link token
            from users.models import TelegramLinkToken
            from core.models import User

            try:
                token = TelegramLinkToken.objects.select_related('user').get(code=code)
            except TelegramLinkToken.DoesNotExist:
                return JsonResponse({'error': 'Invalid code'}, status=400)

            if token.is_expired():
                return JsonResponse({'error': 'Code expired'}, status=400)

            # Update user with Telegram info
            user = token.user
            user.telegram_id = telegram_id
            user.telegram_username = telegram_username
            user.save()

            # Delete token
            token.delete()

            return JsonResponse({
                'success': True,
                'user_id': user.id,
                'email': user.email
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramUserAPIView(View):
    """API endpoint to get user by Telegram ID"""

    def get(self, request, telegram_id):
        from core.models import User

        try:
            user = User.objects.get(telegram_id=telegram_id)
            return JsonResponse({
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'telegram_username': user.telegram_username
            })
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramTasksAPIView(View):
    """API endpoint for bot to get user's tasks"""

    def get(self, request):
        telegram_id = request.GET.get('telegram_id')

        if not telegram_id:
            return JsonResponse({'error': 'telegram_id required'}, status=400)

        from core.models import User, TenantMembership
        from tasks.models import Task

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not linked'}, status=404)

        # Get user's tenant and role
        membership = user.memberships.select_related('tenant').first()
        if not membership:
            return JsonResponse({'tasks': []})

        # Base queryset
        tasks = Task.objects.filter(tenant=membership.tenant).select_related('project', 'assignee')

        # RBAC: Member sees assigned tasks only, Manager sees all
        if membership.role != TenantMembership.Role.MANAGER:
            tasks = tasks.filter(assignee=user)

        # Apply filters
        status_filter = request.GET.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)

        project_filter = request.GET.get('project_id')
        if project_filter:
            try:
                tasks = tasks.filter(project_id=int(project_filter))
            except (ValueError, TypeError):
                pass

        tasks = tasks.order_by('-created_at')[:50]

        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'status_display': task.get_status_display(),
                'priority': task.priority,
                'project': task.project.name,
                'project_id': task.project_id,
                'assignee': task.assignee.get_full_name() if task.assignee else 'Unassigned',
                'due_date': task.due_date.isoformat() if task.due_date else None,
            })

        return JsonResponse({
            'tasks': tasks_data,
            'is_manager': membership.role == TenantMembership.Role.MANAGER
        })

    def post(self, request):
        """Create a new task via bot"""
        try:
            data = json.loads(request.body)
            telegram_id = data.get('telegram_id')
            title = data.get('title')
            project_id = data.get('project_id')
            priority = data.get('priority', 'MEDIUM')

            from core.models import User, TenantMembership
            from tasks.models import Task, Project

            try:
                user = User.objects.get(telegram_id=telegram_id)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not linked'}, status=404)

            # Get user's tenant
            membership = user.memberships.select_related('tenant').first()
            if not membership:
                return JsonResponse({'error': 'No tenant membership'}, status=403)

            try:
                # Verify project belongs to user's tenant
                project = Project.objects.get(id=project_id, tenant=membership.tenant)
            except Project.DoesNotExist:
                return JsonResponse({'error': 'Project not found'}, status=404)

            description = data.get('description', '')
            assignee_id = data.get('assignee_id')
            due_date = data.get('due_date')

            # Determine assignee
            assignee = user  # default to creator
            if assignee_id is not None:
                try:
                    assignee = User.objects.get(id=assignee_id)
                except User.DoesNotExist:
                    assignee = user

            # Parse due_date
            parsed_due_date = None
            if due_date:
                from datetime import date as date_type
                try:
                    parsed_due_date = date_type.fromisoformat(due_date)
                except ValueError:
                    pass

            # Create task
            task = Task.objects.create(
                tenant=project.tenant,
                project=project,
                title=title,
                description=description,
                assignee=assignee,
                priority=priority,
                due_date=parsed_due_date,
                status=Task.Status.TODO
            )

            return JsonResponse({
                'id': task.id,
                'title': task.title,
                'status': task.status,
                'status_display': task.get_status_display(),
                'priority': task.priority,
                'project': task.project.name,
                'assignee': task.assignee.get_full_name() if task.assignee else None,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'description': task.description,
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramTaskDetailAPIView(View):
    """API endpoint for getting task details"""

    def get(self, request, task_id):
        telegram_id = request.GET.get('telegram_id')

        if not telegram_id:
            return JsonResponse({'error': 'telegram_id required'}, status=400)

        from core.models import User, TenantMembership
        from tasks.models import Task

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not linked'}, status=404)

        # Get user's tenant and role
        membership = user.memberships.select_related('tenant').first()
        if not membership:
            return JsonResponse({'error': 'No tenant membership'}, status=403)

        try:
            # Managers can view any task in tenant, members only their assigned tasks
            if membership.role == TenantMembership.Role.MANAGER:
                task = Task.objects.select_related('project', 'assignee').get(
                    id=task_id,
                    tenant=membership.tenant
                )
            else:
                task = Task.objects.select_related('project', 'assignee').get(
                    id=task_id,
                    tenant=membership.tenant,
                    assignee=user
                )
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)

        return JsonResponse({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'status_display': task.get_status_display(),
            'priority': task.priority,
            'project': task.project.name,
            'assignee': task.assignee.get_full_name() if task.assignee else None,
            'due_date': task.due_date.isoformat() if task.due_date else None,
        })


@method_decorator(csrf_exempt, name='dispatch')
class TelegramTaskStatusAPIView(View):
    """API endpoint for updating task status"""

    def patch(self, request, task_id):
        try:
            data = json.loads(request.body)
            telegram_id = data.get('telegram_id')
            new_status = data.get('status')

            from core.models import User, TenantMembership
            from tasks.models import Task
            from tasks.services import TaskService

            try:
                user = User.objects.get(telegram_id=telegram_id)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not linked'}, status=404)

            # Get user's tenant and role
            membership = user.memberships.select_related('tenant').first()
            if not membership:
                return JsonResponse({'error': 'No tenant membership'}, status=403)

            try:
                # Managers can update any task in tenant, members only their assigned tasks
                if membership.role == TenantMembership.Role.MANAGER:
                    task = Task.objects.get(id=task_id, tenant=membership.tenant)
                else:
                    task = Task.objects.get(id=task_id, tenant=membership.tenant, assignee=user)
            except Task.DoesNotExist:
                return JsonResponse({'error': 'Task not found'}, status=404)

            # Update status via service (validates transitions)
            TaskService.update_task_status(task, new_status, user)

            return JsonResponse({
                'id': task.id,
                'title': task.title,
                'status': task.status,
                'status_display': task.get_status_display()
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramMembersAPIView(View):
    """API endpoint to get tenant members for assignee selection"""

    def get(self, request):
        telegram_id = request.GET.get('telegram_id')

        if not telegram_id:
            return JsonResponse({'error': 'telegram_id required'}, status=400)

        from core.models import User, TenantMembership

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not linked'}, status=404)

        membership = user.memberships.select_related('tenant').first()
        if not membership:
            return JsonResponse({'members': []})

        members = TenantMembership.objects.filter(
            tenant=membership.tenant
        ).select_related('user')

        members_data = []
        for m in members:
            members_data.append({
                'id': m.user.id,
                'email': m.user.email,
                'full_name': m.user.get_full_name(),
            })

        return JsonResponse({'members': members_data})


@method_decorator(csrf_exempt, name='dispatch')
class TelegramProjectsAPIView(View):
    """API endpoint to get user's projects"""

    def get(self, request):
        telegram_id = request.GET.get('telegram_id')

        if not telegram_id:
            return JsonResponse({'error': 'telegram_id required'}, status=400)

        from core.models import User
        from tasks.models import Project

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not linked'}, status=404)

        membership = user.memberships.select_related('tenant').first()
        if not membership:
            return JsonResponse({'projects': []})

        projects = Project.objects.filter(tenant=membership.tenant)

        projects_data = []
        for project in projects:
            projects_data.append({
                'id': project.id,
                'name': project.name,
                'description': project.description
            })

        return JsonResponse({'projects': projects_data})


@method_decorator(csrf_exempt, name='dispatch')
class TelegramSettingsAPIView(View):
    """API endpoint to get tenant settings for bot"""

    def get(self, request):
        telegram_id = request.GET.get('telegram_id')

        if not telegram_id:
            return JsonResponse({'error': 'telegram_id required'}, status=400)

        from core.models import User

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not linked'}, status=404)

        membership = user.memberships.select_related('tenant').first()
        if not membership:
            return JsonResponse({'error': 'No tenant membership'}, status=404)

        # Get or create settings for tenant
        settings, created = TenantSettings.objects.get_or_create(tenant=membership.tenant)

        return JsonResponse({
            'ai_enabled': settings.ai_enabled,
            'ai_system_prompt': settings.ai_system_prompt,
            'ai_default_mode': settings.ai_default_mode,
            'ai_default_language': settings.ai_default_language
        })


class ProjectDetailView(LoginRequiredMixin, TemplateView):
    """Project detail view with financial KPIs and snapshot history"""
    template_name = 'project_detail.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get tenant from request
        tenant = getattr(self.request, 'tenant', None)
        project_id = kwargs.get('project_id')

        # Get project with tenant isolation
        project = get_object_or_404(Project, id=project_id, tenant=tenant)

        # Get financial KPIs
        kpis = project.get_financial_kpis()

        # Get snapshot history - members see only their own, managers see all
        snapshots = project.snapshots.all()
        tenant_role = getattr(self.request, 'tenant_role', None)

        context['project'] = project
        context['kpis'] = kpis
        context['snapshots'] = snapshots
        context['is_manager'] = tenant_role == 'MANAGER'

        return context


class SnapshotCreateView(LoginRequiredMixin, View):
    """Create financial snapshot (manager-only)"""
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        # Check if user is a manager
        tenant = getattr(request, 'tenant', None)
        tenant_role = getattr(request, 'tenant_role', None)

        if not tenant or tenant_role != 'MANAGER':
            return HttpResponse('Permission denied. Only managers can create financial snapshots.', status=403)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, project_id):
        tenant = getattr(request, 'tenant')

        # Get project with tenant isolation
        project = get_object_or_404(Project, id=project_id, tenant=tenant)

        try:
            # Get form data
            total_completed_work = Decimal(request.POST.get('total_completed_work', '0'))
            total_paid_amount = Decimal(request.POST.get('total_paid_amount', '0'))
            total_retention_earned = Decimal(request.POST.get('total_retention_earned', '0'))
            notes = request.POST.get('notes', '').strip()

            # Validation: no negative values
            if total_completed_work < 0 or total_paid_amount < 0 or total_retention_earned < 0:
                messages.error(request, 'Values cannot be negative')
                return redirect('project_detail', project_id=project_id)

            # Validation: completed work cannot exceed contract total
            if total_completed_work > project.contract_total_amount:
                messages.error(request, 'Completed work cannot exceed contract total amount')
                return redirect('project_detail', project_id=project_id)

            # Validation: retention earned cannot exceed retention total
            if total_retention_earned > project.contract_retention_total:
                messages.error(request, 'Retention earned cannot exceed contract retention total')
                return redirect('project_detail', project_id=project_id)

            # Create snapshot
            snapshot = ProjectFinancialSnapshot.objects.create(
                project=project,
                total_completed_work=total_completed_work,
                total_paid_amount=total_paid_amount,
                total_retention_earned=total_retention_earned,
                notes=notes,
                created_by=request.user
            )

            # Create audit log
            from audit.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='CREATE',
                resource_type='ProjectFinancialSnapshot',
                resource_id=snapshot.id,
                changes={
                    'project_id': project.id,
                    'project_name': project.name,
                    'total_completed_work': str(total_completed_work),
                    'total_paid_amount': str(total_paid_amount),
                    'total_retention_earned': str(total_retention_earned),
                    'notes': notes
                }
            )

            messages.success(request, 'Financial snapshot created successfully')
            return redirect('project_detail', project_id=project_id)

        except (ValueError, TypeError) as e:
            messages.error(request, f'Invalid input: {str(e)}')
            return redirect('project_detail', project_id=project_id)
        except Exception as e:
            messages.error(request, f'Error creating snapshot: {str(e)}')
            return redirect('project_detail', project_id=project_id)

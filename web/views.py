import csv
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from tasks.models import Task


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


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get tenant from request (set by TenantMiddleware)
        tenant = getattr(self.request, 'tenant', None)

        if tenant:
            # Get task statistics
            tasks = Task.objects.filter(tenant=tenant)
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

        # Base queryset
        queryset = Task.objects.filter(tenant=tenant).select_related(
            'project', 'assignee'
        )

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

        # Total records
        records_total = Task.objects.filter(tenant=tenant).count()
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
                'assignee': task.assignee.get_full_name() if task.assignee else 'Unassigned',
                'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                'priority': task.get_priority_display(),
                'priority_value': task.priority,
                'status': task.get_status_display(),
                'status_value': task.status,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M')
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data
        })


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

        # Base queryset
        queryset = Task.objects.filter(tenant=tenant).select_related(
            'project', 'assignee'
        )

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

        from core.models import User
        from tasks.models import Task

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not linked'}, status=404)

        # Get user's tenant
        membership = user.memberships.select_related('tenant').first()
        if not membership:
            return JsonResponse({'tasks': []})

        # Get user's assigned tasks
        tasks = Task.objects.filter(
            tenant=membership.tenant,
            assignee=user
        ).select_related('project').order_by('-created_at')[:50]

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
                'due_date': task.due_date.isoformat() if task.due_date else None,
            })

        return JsonResponse({'tasks': tasks_data})

    def post(self, request):
        """Create a new task via bot"""
        try:
            data = json.loads(request.body)
            telegram_id = data.get('telegram_id')
            title = data.get('title')
            project_id = data.get('project_id')
            priority = data.get('priority', 'MEDIUM')

            from core.models import User
            from tasks.models import Task, Project

            try:
                user = User.objects.get(telegram_id=telegram_id)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not linked'}, status=404)

            try:
                project = Project.objects.get(id=project_id)
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

        from core.models import User
        from tasks.models import Task

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not linked'}, status=404)

        try:
            task = Task.objects.select_related('project', 'assignee').get(
                id=task_id,
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

            from core.models import User
            from tasks.models import Task
            from tasks.services import TaskService

            try:
                user = User.objects.get(telegram_id=telegram_id)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not linked'}, status=404)

            try:
                task = Task.objects.get(id=task_id, assignee=user)
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

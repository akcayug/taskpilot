import csv
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
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

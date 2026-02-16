from django.contrib import admin
from .models import Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'created_at']
    list_filter = ['tenant', 'created_at']
    search_fields = ['name', 'description', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['tenant']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('tenant')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'assignee', 'status', 'priority', 'due_date', 'created_at']
    list_filter = ['status', 'priority', 'tenant', 'created_at']
    search_fields = ['title', 'description', 'project__name', 'assignee__email']
    readonly_fields = ['tenant', 'created_at', 'updated_at']
    autocomplete_fields = ['project', 'assignee']

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'description', 'project')
        }),
        ('Assignment', {
            'fields': ('assignee', 'due_date', 'priority')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Metadata', {
            'fields': ('tenant', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('project', 'assignee', 'tenant')

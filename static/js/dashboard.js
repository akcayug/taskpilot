$(document).ready(function() {
    // Initialize DataTable
    const table = $('#tasksTable').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/api/tasks/',
            data: function(d) {
                d.status = $('#statusFilter').val();
                d.priority = $('#priorityFilter').val();
            }
        },
        columns: [
            {
                data: 'title',
                render: function(data, type, row) {
                    return '<strong>' + data + '</strong>';
                }
            },
            { data: 'project' },
            { data: 'assignee' },
            {
                data: 'due_date',
                render: function(data, type, row) {
                    if (!data) return '<span class="text-muted">No due date</span>';
                    return data;
                }
            },
            {
                data: 'priority',
                render: function(data, type, row) {
                    return '<span class="badge badge-priority-' + row.priority_value + '">' + data + '</span>';
                }
            },
            {
                data: 'status',
                render: function(data, type, row) {
                    return '<span class="badge badge-status-' + row.status_value + '">' + data + '</span>';
                }
            },
            { data: 'created_at' }
        ],
        order: [[6, 'desc']], // Sort by created_at descending
        pageLength: 25,
        language: {
            emptyTable: "No tasks found",
            info: "Showing _START_ to _END_ of _TOTAL_ tasks",
            infoEmpty: "Showing 0 to 0 of 0 tasks",
            infoFiltered: "(filtered from _MAX_ total tasks)",
            search: "Search:",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        },
        drawCallback: function() {
            // Reinitialize Lucide icons after table redraw
            lucide.createIcons();
        }
    });

    // Filter by status
    $('#statusFilter').on('change', function() {
        table.ajax.reload();
    });

    // Filter by priority
    $('#priorityFilter').on('change', function() {
        table.ajax.reload();
    });

    // Export to CSV
    $('#exportBtn').on('click', function() {
        const status = $('#statusFilter').val();
        const priority = $('#priorityFilter').val();

        let url = '/export/tasks/?';
        if (status) url += 'status=' + status + '&';
        if (priority) url += 'priority=' + priority;

        window.location.href = url;
    });
});

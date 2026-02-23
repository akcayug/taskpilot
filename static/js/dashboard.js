$(document).ready(function() {
    const isMobile = () => window.innerWidth < 768;
    const isManager = window.userRole === 'MANAGER';

    let table = null;
    let mobileData = {
        currentPage: 1,
        pageSize: 10,
        totalRecords: 0
    };
    let tenantMembers = []; // Cache for tenant members (assignee dropdown)
    let editingRow = null; // Track currently editing row

    // Fetch tenant members for assignee dropdown (managers only)
    if (isManager) {
        $.ajax({
            url: '/api/members/',
            method: 'GET',
            success: function(response) {
                tenantMembers = response.members || [];
            },
            error: function(xhr) {
                console.error('Failed to load team members:', xhr);
            }
        });
    }

    function getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Setup CSRF for AJAX requests
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCsrfToken());
            }
        }
    });

    function makeEditable(cell, field, row) {
        const value = row[field + '_value'] || row[field] || '';
        const $cell = $(cell);

        if (field === 'title') {
            $cell.html(`<input type="text" class="form-control form-control-sm" value="${escapeHtml(value)}" maxlength="100">`);
        } else if (field === 'status') {
            const statuses = ['TODO', 'IN_PROGRESS', 'DONE', 'ARCHIVED'];
            const statusLabels = {
                'TODO': 'To Do',
                'IN_PROGRESS': 'In Progress',
                'DONE': 'Done',
                'ARCHIVED': 'Archived'
            };
            let options = statuses.map(s =>
                `<option value="${s}" ${s === value ? 'selected' : ''}>${statusLabels[s]}</option>`
            ).join('');
            $cell.html(`<select class="form-select form-select-sm">${options}</select>`);
        } else if (field === 'priority') {
            const priorities = ['HIGH', 'MEDIUM', 'LOW'];
            const priorityLabels = {'HIGH': 'High', 'MEDIUM': 'Medium', 'LOW': 'Low'};
            let options = priorities.map(p =>
                `<option value="${p}" ${p === value ? 'selected' : ''}>${priorityLabels[p]}</option>`
            ).join('');
            $cell.html(`<select class="form-select form-select-sm">${options}</select>`);
        } else if (field === 'due_date') {
            $cell.html(`<input type="date" class="form-control form-control-sm" value="${value}">`);
        } else if (field === 'assignee' && isManager) {
            let options = '<option value="">Unassigned</option>';
            options += tenantMembers.map(m =>
                `<option value="${m.id}" ${m.id === row.assignee_id ? 'selected' : ''}>${escapeHtml(m.full_name)}</option>`
            ).join('');
            $cell.html(`<select class="form-select form-select-sm">${options}</select>`);
        }
    }

    function restoreDisplay(cell, field, row) {
        const $cell = $(cell);

        if (field === 'title') {
            $cell.html('<strong>' + escapeHtml(row.title) + '</strong>');
        } else if (field === 'project') {
            $cell.html('<a href="/projects/' + row.project_id + '/" class="text-decoration-none">' + escapeHtml(row.project) + '</a>');
        } else if (field === 'assignee') {
            $cell.html(escapeHtml(row.assignee));
        } else if (field === 'status') {
            $cell.html('<span class="badge badge-status-' + row.status_value + '">' + escapeHtml(row.status) + '</span>');
        } else if (field === 'priority') {
            $cell.html('<span class="badge badge-priority-' + row.priority_value + '">' + escapeHtml(row.priority) + '</span>');
        } else if (field === 'due_date') {
            const display = row.due_date || '<span class="text-muted">No due date</span>';
            $cell.html(display);
        } else if (field === 'updated_at') {
            $cell.html(escapeHtml(row.updated_at || row.created_at));
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function enterEditMode($row, rowData) {
        if (editingRow) {
            alert('Please save or cancel the current edit first');
            return;
        }

        editingRow = { $row, rowData };
        const cells = $row.find('td');

        // Make cells editable based on role
        makeEditable(cells[2], 'title', rowData); // Title
        makeEditable(cells[3], 'status', rowData); // Status
        makeEditable(cells[4], 'due_date', rowData); // Due date
        makeEditable(cells[5], 'priority', rowData); // Priority
        if (isManager) {
            makeEditable(cells[1], 'assignee', rowData); // Assignee (manager only)
        }

        // Change actions to save/cancel
        const $actionsCell = $(cells[7]);
        $actionsCell.html(`
            <button class="btn btn-sm btn-success save-btn" title="Save">
                <i data-lucide="check" class="icon-sm"></i>
            </button>
            <button class="btn btn-sm btn-secondary cancel-btn" title="Cancel">
                <i data-lucide="x" class="icon-sm"></i>
            </button>
        `);
        lucide.createIcons();
    }

    function exitEditMode(restore = true) {
        if (!editingRow) return;

        const { $row, rowData } = editingRow;
        const cells = $row.find('td');

        if (restore) {
            // Restore original values
            restoreDisplay(cells[1], 'assignee', rowData);
            restoreDisplay(cells[2], 'title', rowData);
            restoreDisplay(cells[3], 'status', rowData);
            restoreDisplay(cells[4], 'due_date', rowData);
            restoreDisplay(cells[5], 'priority', rowData);
        }

        // Restore actions
        const $actionsCell = $(cells[7]);
        $actionsCell.html(`
            <button class="btn btn-sm btn-primary edit-btn" title="Edit">
                <i data-lucide="edit-2" class="icon-sm"></i>
            </button>
        `);
        lucide.createIcons();

        editingRow = null;
    }

    function saveTask() {
        if (!editingRow) return;

        const { $row, rowData } = editingRow;
        const cells = $row.find('td');

        // Collect updated values
        const updates = {
            updated_at: rowData.updated_at || rowData.created_at
        };

        const $titleInput = $(cells[2]).find('input');
        if ($titleInput.length) updates.title = $titleInput.val();

        const $statusSelect = $(cells[3]).find('select');
        if ($statusSelect.length) updates.status = $statusSelect.val();

        const $dueDateInput = $(cells[4]).find('input');
        if ($dueDateInput.length) updates.due_date = $dueDateInput.val() || null;

        const $prioritySelect = $(cells[5]).find('select');
        if ($prioritySelect.length) updates.priority = $prioritySelect.val();

        if (isManager) {
            const $assigneeSelect = $(cells[1]).find('select');
            if ($assigneeSelect.length) {
                updates.assignee_id = $assigneeSelect.val() || null;
            }
        }

        // Show loading state
        const $actionsCell = $(cells[7]);
        $actionsCell.html('<span class="spinner-border spinner-border-sm"></span>');

        // Send PATCH request
        $.ajax({
            url: `/api/tasks/${rowData.id}/`,
            method: 'PATCH',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            data: JSON.stringify(updates),
            success: function(response) {
                // Update row data with response
                Object.assign(rowData, response);

                // Update cells with new values
                $(cells[1]).html(escapeHtml(response.assignee));
                $(cells[2]).html('<strong>' + escapeHtml(response.title) + '</strong>');
                $(cells[3]).html('<span class="badge badge-status-' + response.status_value + '">' + escapeHtml(response.status) + '</span>');
                $(cells[4]).html(response.due_date || '<span class="text-muted">No due date</span>');
                $(cells[5]).html('<span class="badge badge-priority-' + response.priority_value + '">' + escapeHtml(response.priority) + '</span>');
                $(cells[6]).html(escapeHtml(response.updated_at));

                exitEditMode(false);

                // Show success message briefly
                $actionsCell.html('<span class="text-success"><i data-lucide="check"></i></span>');
                lucide.createIcons();
                setTimeout(function() {
                    $actionsCell.html(`
                        <button class="btn btn-sm btn-primary edit-btn" title="Edit">
                            <i data-lucide="edit-2" class="icon-sm"></i>
                        </button>
                    `);
                    lucide.createIcons();
                }, 1000);
            },
            error: function(xhr) {
                exitEditMode(true);
                const error = xhr.responseJSON?.error || 'Failed to update task';
                alert('Error: ' + error);
            }
        });
    }

    function initDesktopView() {
        // Initialize DataTable for desktop with new column order
        table = $('#tasksTable').DataTable({
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
                // Project → Assignee → Title → Status → Due → Priority → Updated → Actions
                {
                    data: 'project',
                    render: function(data, type, row) {
                        return '<a href="/projects/' + row.project_id + '/" class="text-decoration-none">' + escapeHtml(data) + '</a>';
                    }
                },
                { data: 'assignee' },
                {
                    data: 'title',
                    render: function(data, type, row) {
                        return '<strong>' + escapeHtml(data) + '</strong>';
                    }
                },
                {
                    data: 'status',
                    render: function(data, type, row) {
                        return '<span class="badge badge-status-' + row.status_value + '">' + escapeHtml(data) + '</span>';
                    }
                },
                {
                    data: 'due_date',
                    render: function(data, type, row) {
                        if (!data) return '<span class="text-muted">No due date</span>';
                        return escapeHtml(data);
                    }
                },
                {
                    data: 'priority',
                    render: function(data, type, row) {
                        return '<span class="badge badge-priority-' + row.priority_value + '">' + escapeHtml(data) + '</span>';
                    }
                },
                {
                    data: 'updated_at',
                    render: function(data, type, row) {
                        return escapeHtml(data || row.created_at);
                    }
                },
                {
                    data: null,
                    orderable: false,
                    render: function(data, type, row) {
                        return `<div class="btn-group btn-group-sm" role="group">
                                    <a href="/tasks/${row.id}/edit/" class="btn btn-outline-primary" title="Edit Task">
                                        <i data-lucide="edit" class="icon-sm"></i>
                                    </a>
                                    <button class="btn btn-outline-secondary edit-btn" title="Quick Edit">
                                        <i data-lucide="edit-2" class="icon-sm"></i>
                                    </button>
                                </div>`;
                    }
                }
            ],
            order: [[6, 'desc']], // Sort by updated_at descending
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

        // Edit button click handler (delegated)
        $('#tasksTable tbody').on('click', '.edit-btn', function() {
            const $row = $(this).closest('tr');
            const rowData = table.row($row).data();
            enterEditMode($row, rowData);
        });

        // Save button click handler (delegated)
        $('#tasksTable tbody').on('click', '.save-btn', function() {
            saveTask();
        });

        // Cancel button click handler (delegated)
        $('#tasksTable tbody').on('click', '.cancel-btn', function() {
            exitEditMode(true);
        });

        // Filter by status
        $('#statusFilter').on('change', function() {
            table.ajax.reload();
        });

        // Filter by priority
        $('#priorityFilter').on('change', function() {
            table.ajax.reload();
        });
    }

    function createTaskCard(task) {
        const priorityClass = 'priority-' + task.priority_value;
        const dueDate = task.due_date || 'No due date';

        return `
            <div class="task-card ${priorityClass}" data-task-id="${task.id}">
                <div class="task-card-header">
                    <h6 class="task-card-title">${escapeHtml(task.title)}</h6>
                    <div class="task-card-badges">
                        <span class="badge badge-status-${task.status_value}">${escapeHtml(task.status)}</span>
                        <span class="badge badge-priority-${task.priority_value}">${escapeHtml(task.priority)}</span>
                    </div>
                </div>
                <div class="task-card-body">
                    <div class="task-card-info">
                        <i data-lucide="folder"></i>
                        <a href="/projects/${task.project_id}/" class="text-decoration-none">${escapeHtml(task.project)}</a>
                    </div>
                    <div class="task-card-info">
                        <i data-lucide="user"></i>
                        <span>${escapeHtml(task.assignee)}</span>
                    </div>
                    <div class="task-card-info">
                        <i data-lucide="calendar"></i>
                        <span>${escapeHtml(dueDate)}</span>
                    </div>
                </div>
                <div class="task-card-footer">
                    <span>Updated ${escapeHtml(task.updated_at || task.created_at)}</span>
                </div>
            </div>
        `;
    }

    function loadMobileTasks() {
        const $container = $('#mobileTasksList');
        const $prevBtn = $('#mobilePrevBtn');
        const $nextBtn = $('#mobileNextBtn');
        const $paginationInfo = $('#mobilePaginationInfo');

        // Show loading state
        $container.html('<div class="mobile-tasks-loading"><i data-lucide="loader" class="icon-lg"></i><p>Loading tasks...</p></div>');
        lucide.createIcons();

        // Calculate offset for server-side pagination
        const start = (mobileData.currentPage - 1) * mobileData.pageSize;

        $.ajax({
            url: '/api/tasks/',
            method: 'GET',
            data: {
                start: start,
                length: mobileData.pageSize,
                status: $('#statusFilter').val(),
                priority: $('#priorityFilter').val()
            },
            success: function(response) {
                mobileData.totalRecords = response.recordsFiltered;
                const tasks = response.data;

                if (tasks.length === 0) {
                    $container.html('<div class="mobile-tasks-loading"><p class="text-muted">No tasks found</p></div>');
                } else {
                    const cardsHtml = tasks.map(task => createTaskCard(task)).join('');
                    $container.html(cardsHtml);
                    lucide.createIcons();
                }

                // Update pagination
                const totalPages = Math.ceil(mobileData.totalRecords / mobileData.pageSize);
                const start = (mobileData.currentPage - 1) * mobileData.pageSize + 1;
                const end = Math.min(start + tasks.length - 1, mobileData.totalRecords);

                $paginationInfo.text(`${start}-${end} of ${mobileData.totalRecords}`);
                $prevBtn.prop('disabled', mobileData.currentPage === 1);
                $nextBtn.prop('disabled', mobileData.currentPage >= totalPages);
            },
            error: function() {
                $container.html('<div class="mobile-tasks-loading"><p class="text-danger">Error loading tasks</p></div>');
            }
        });
    }

    function initMobileView() {
        // Load initial tasks
        loadMobileTasks();

        // Filter handlers
        $('#statusFilter').on('change', function() {
            mobileData.currentPage = 1;
            loadMobileTasks();
        });

        $('#priorityFilter').on('change', function() {
            mobileData.currentPage = 1;
            loadMobileTasks();
        });

        // Pagination handlers
        $('#mobilePrevBtn').on('click', function() {
            if (mobileData.currentPage > 1) {
                mobileData.currentPage--;
                loadMobileTasks();
            }
        });

        $('#mobileNextBtn').on('click', function() {
            const totalPages = Math.ceil(mobileData.totalRecords / mobileData.pageSize);
            if (mobileData.currentPage < totalPages) {
                mobileData.currentPage++;
                loadMobileTasks();
            }
        });

        // Task card click handler (delegate for dynamic content)
        $('#mobileTasksList').on('click', '.task-card', function() {
            const taskId = $(this).data('task-id');
            // Navigate to task edit page
            window.location.href = `/tasks/${taskId}/edit/`;
        });
    }

    // Initialize appropriate view based on screen size
    if (isMobile()) {
        initMobileView();
    } else {
        initDesktopView();
    }

    // Handle window resize
    let resizeTimer;
    $(window).on('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            const nowMobile = isMobile();
            const wasDesktop = table !== null;

            // If switched from desktop to mobile
            if (nowMobile && wasDesktop) {
                if (table) {
                    table.destroy();
                    table = null;
                }
                mobileData.currentPage = 1;
                initMobileView();
            }
            // If switched from mobile to desktop
            else if (!nowMobile && !wasDesktop) {
                initDesktopView();
            }
        }, 250);
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

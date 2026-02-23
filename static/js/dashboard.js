$(document).ready(function() {
    const isMobile = () => window.innerWidth < 768;

    let table = null;
    let mobileData = {
        currentPage: 1,
        pageSize: 10,
        totalRecords: 0
    };

    function initDesktopView() {
        // Initialize DataTable for desktop
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
    }

    function createTaskCard(task) {
        const priorityClass = 'priority-' + task.priority_value;
        const dueDate = task.due_date || 'No due date';

        return `
            <div class="task-card ${priorityClass}" data-task-id="${task.id}">
                <div class="task-card-header">
                    <h6 class="task-card-title">${task.title}</h6>
                    <div class="task-card-badges">
                        <span class="badge badge-status-${task.status_value}">${task.status}</span>
                        <span class="badge badge-priority-${task.priority_value}">${task.priority}</span>
                    </div>
                </div>
                <div class="task-card-body">
                    <div class="task-card-info">
                        <i data-lucide="folder"></i>
                        <span>${task.project}</span>
                    </div>
                    <div class="task-card-info">
                        <i data-lucide="user"></i>
                        <span>${task.assignee}</span>
                    </div>
                    <div class="task-card-info">
                        <i data-lucide="calendar"></i>
                        <span>${dueDate}</span>
                    </div>
                </div>
                <div class="task-card-footer">
                    <span>Created ${task.created_at}</span>
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
            // TODO: Navigate to task detail page
            console.log('Task clicked:', taskId);
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

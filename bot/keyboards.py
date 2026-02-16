from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_priority_keyboard():
    """Create inline keyboard for task priority selection"""
    keyboard = [
        [
            InlineKeyboardButton("🔴 High", callback_data="priority_HIGH"),
            InlineKeyboardButton("🟡 Medium", callback_data="priority_MEDIUM"),
            InlineKeyboardButton("🟢 Low", callback_data="priority_LOW")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_status_keyboard(current_status):
    """Create inline keyboard for task status updates based on valid transitions"""

    # Define valid transitions
    valid_transitions = {
        'TODO': ['IN_PROGRESS', 'ARCHIVED'],
        'IN_PROGRESS': ['DONE', 'TODO', 'ARCHIVED'],
        'DONE': ['ARCHIVED', 'TODO'],
        'ARCHIVED': []
    }

    status_labels = {
        'TODO': '📋 To Do',
        'IN_PROGRESS': '⏳ In Progress',
        'DONE': '✅ Done',
        'ARCHIVED': '📦 Archived'
    }

    keyboard = []

    # Add valid transition buttons
    valid_next = valid_transitions.get(current_status, [])
    if valid_next:
        row = []
        for status in valid_next:
            row.append(InlineKeyboardButton(
                status_labels[status],
                callback_data=f"status_{status}"
            ))
            if len(row) == 2:  # Max 2 buttons per row
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

    # Add cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

    return InlineKeyboardMarkup(keyboard)


def get_task_actions_keyboard(task_id, status):
    """Create inline keyboard for task actions"""
    keyboard = [
        [InlineKeyboardButton("📝 Update Status", callback_data=f"update_status_{task_id}")]
    ]

    # Only show status change option if not archived
    if status != 'ARCHIVED':
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_task_{task_id}")])

    keyboard.append([InlineKeyboardButton("◀️ Back to Tasks", callback_data="my_tasks")])

    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard(action, task_id=None):
    """Create confirmation keyboard"""
    confirm_data = f"confirm_{action}"
    cancel_data = "cancel"

    if task_id:
        confirm_data += f"_{task_id}"

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=confirm_data),
            InlineKeyboardButton("❌ Cancel", callback_data=cancel_data)
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

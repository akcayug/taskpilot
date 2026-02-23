/**
 * AI Helper for Task Forms
 * Handles "Fix Language" and "Translate" buttons
 */

$(document).ready(function() {
    let currentField = null;
    let currentSuggestion = null;

    // Get CSRF token
    function getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Show loading state on button
    function setButtonLoading($btn, loading) {
        if (loading) {
            $btn.prop('disabled', true).addClass('loading');
            const icon = $btn.find('i');
            icon.data('original-icon', icon.attr('data-lucide'));
            icon.attr('data-lucide', 'loader');
        } else {
            $btn.prop('disabled', false).removeClass('loading');
            const icon = $btn.find('i');
            const originalIcon = icon.data('original-icon');
            if (originalIcon) {
                icon.attr('data-lucide', originalIcon);
            }
        }
        lucide.createIcons();
    }

    // Show error alert
    function showError(message) {
        const alert = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Error:</strong> ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        $('.card-body').prepend(alert);
        setTimeout(() => {
            $('.alert').fadeOut(() => $(this).remove());
        }, 5000);
    }

    // Escape HTML for security
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Handle AI button click
    $('.ai-btn').on('click', function() {
        const $btn = $(this);
        const fieldId = $btn.data('field');
        const mode = $btn.data('mode');
        const $field = $('#' + fieldId);

        const text = $field.val().trim();

        if (!text) {
            showError('Please enter some text first');
            return;
        }

        currentField = fieldId;

        // Show loading state
        setButtonLoading($btn, true);

        // Call AI API
        $.ajax({
            url: '/api/ai-suggest/',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            data: JSON.stringify({
                text: text,
                mode: mode,
                field: fieldId
            }),
            success: function(response) {
                currentSuggestion = response.suggested;

                // Show modal with suggestion
                $('#originalText').text(response.original);
                $('#suggestedText').text(response.suggested);

                const modal = new bootstrap.Modal(document.getElementById('aiSuggestionModal'));
                modal.show();

                setButtonLoading($btn, false);
            },
            error: function(xhr) {
                setButtonLoading($btn, false);

                const error = xhr.responseJSON?.error || 'Failed to get AI suggestion';
                showError(error);
            }
        });
    });

    // Handle Apply button in modal
    $('#applyBtn').on('click', function() {
        if (currentField && currentSuggestion) {
            $('#' + currentField).val(currentSuggestion);

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('aiSuggestionModal'));
            modal.hide();

            // Show success message
            const alert = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    <strong>Success!</strong> AI suggestion applied. You can still edit the text before saving.
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            $('.card-body').prepend(alert);
            setTimeout(() => {
                $('.alert').fadeOut(() => $(this).remove());
            }, 3000);

            // Reset state
            currentField = null;
            currentSuggestion = null;
        }
    });

    // Handle form submission (demo only)
    $('#taskForm').on('submit', function(e) {
        e.preventDefault();
        alert('This is a demo. In the actual implementation, this would save the task.');
    });
});

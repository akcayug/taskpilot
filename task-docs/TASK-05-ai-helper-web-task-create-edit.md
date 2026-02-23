# TASK-05: AI Helper Web Task Create/Edit

## Goal
Add LLM-powered text improvement buttons to task create/edit forms in web UI.

## Scope
- "Fix language" button on task create/edit form
- "Translate" button on task create/edit form
- Uses tenant AI settings (prompt, mode, target language)
- Calls external LLM API (OpenAI GPT-4)
- Shows suggestion in modal or side-by-side
- User clicks "Apply" to update form fields
- Audit log entry

## Non-Scope
- Real-time suggestion as user types
- Multiple language translation options (uses tenant default only)
- AI for other fields (priority, status, etc.)
- Automatic application of suggestions

## Touchpoints
- `web/templates/task_form.html` (create/edit form)
- `static/js/task_form.js` (AJAX calls to LLM endpoint)
- Create `web/views.py` (LLM suggestion endpoint)
- `web/urls.py`
- Create `web/llm_client.py` (OpenAI API integration)
- `audit/models.py` (log AI suggestions)

## UI Notes
- Buttons below title/description fields: [Fix Language] [Translate]
- On click: show loading spinner
- Show suggestion in modal: "Original: [text]" | "Suggested: [text]"
- Modal buttons: [Apply] [Cancel]
- Apply updates form field, user can edit further before saving

## Permission Notes
- Available to all users (manager and member)
- Uses tenant settings (must be enabled and configured)
- If AI disabled in tenant settings, hide buttons

## Acceptance Criteria
- [ ] "Fix language" button calls LLM with "fix" mode
- [ ] "Translate" button calls LLM with "translate" mode + target language
- [ ] Suggestion shown in modal
- [ ] Apply button updates form field
- [ ] Audit entry created: action="ai_suggestion_applied", details=before/after
- [ ] Error handling: API timeout, API error (show user-friendly message)
- [ ] Buttons hidden if AI disabled in tenant settings

## Verification
- Manual test: create task, click "Fix language", verify suggestion
- Manual test: click "Translate", verify translation to tenant language
- Check audit log: `AuditLog.objects.filter(action='ai_suggestion_applied')`
- Test error: disconnect OpenAI API, verify error message shown

## Risks
- LLM API latency (may take 2-5 seconds)
- API cost per request
- Prompt engineering for consistent output format
- User may apply suggestion and then manually modify (expected behavior)

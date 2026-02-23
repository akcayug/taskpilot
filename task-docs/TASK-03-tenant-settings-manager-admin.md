# TASK-03: Tenant Settings Manager Admin

## Goal
Create per-tenant settings UI accessible only to managers for configuring AI features.

## Scope
- Web-based settings page at `/settings`
- Settings stored per tenant:
  - AI enabled (boolean)
  - AI system prompt (text, max 500 chars)
  - Default mode: "fix" or "translate"
  - Default target language: en, tr, de, fr, es
- Form validation
- Manager-only access

## Non-Scope
- Django admin integration
- Multi-language UI (only target language for AI)
- API endpoints for settings (web form only)
- Settings history/versioning

## Touchpoints
- Create `core/models.py` (TenantSettings model or add fields to Tenant)
- Create `web/templates/settings.html`
- Create `web/views.py` (SettingsView)
- `web/urls.py`
- `core/middleware.py` (ensure tenant context)

## UI Notes
- Simple form with labeled fields
- Toggle switch for AI enabled
- Textarea for system prompt
- Dropdown for mode and language
- Save button with success message
- Show current values on load

## Permission Notes
- Only users with manager role can access
- Return 403 Forbidden for non-managers
- Check via `request.user.tenant_memberships.filter(tenant=request.tenant, role='Manager').exists()`

## Acceptance Criteria
- [ ] Manager can access /settings
- [ ] Member gets 403 Forbidden
- [ ] Settings persist to database
- [ ] Settings load correctly on page reload
- [ ] Form validation works (required fields, max lengths)
- [ ] Default values set for new tenants (AI disabled, default prompt, mode=fix, lang=en)

## Verification
- Login as member, access /settings → 403
- Login as manager, update settings, reload page → values persist
- Submit invalid values → validation errors shown
- Check database: `TenantSettings.objects.get(tenant=request.tenant)`

## Risks
- Settings may need migration if adding fields to Tenant model
- Default prompt text needs to be well-crafted for AI use

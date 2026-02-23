# TASK-04: Telegram Bot Tasks/Projects Filters + Speech-to-Task

## Goal
Enhance bot with filtered task listing and voice-to-task creation using LLM.

## Scope
- `/tasks` command with status and project filters
- `/add` command for interactive task creation
- Voice message support:
  - Transcribe audio (Whisper API)
  - Clean text with LLM (GPT-4 API)
  - Optionally translate using tenant settings
  - Show suggestion, user confirms
- Multi-tenant user support (select active tenant)

## Non-Scope
- Voice-to-text in web UI (bot only)
- Real-time streaming transcription
- Custom voice models
- Audio file uploads (voice messages only)

## Touchpoints
- `bot/handlers.py` (add /tasks, /add, voice handler)
- `bot/keyboards.py` (filter keyboards)
- `bot/api_client.py` (call web service for tasks, settings)
- Create `bot/llm_client.py` (OpenAI API integration)
- Create `bot/speech_client.py` (Whisper API integration)
- `.env` (add OPENAI_API_KEY)

## UI Notes
- `/tasks` shows inline keyboard: Filter by Status | Filter by Project
- Task list shows: title, status, due date, assignee
- Voice flow: "Send voice message" → "Processing..." → "Suggestion: [text]" → Confirm/Cancel buttons
- Multi-tenant: "Select tenant:" → keyboard with tenant names

## Permission Notes
- Member: sees assigned tasks only
- Manager: sees all tenant tasks
- Task creation respects RBAC (can only assign to tenant members)
- Voice-to-task inherits same permissions

## Acceptance Criteria
- [ ] `/tasks` shows filtered task list
- [ ] Manager sees all tasks, member sees assigned only
- [ ] Voice message → transcription → LLM suggestion → user confirms → task created
- [ ] Multi-tenant users can select active tenant
- [ ] LLM uses tenant system prompt from settings
- [ ] Translation uses tenant default language
- [ ] No automatic task creation (confirmation required)

## Verification
- Manual bot test: send voice message
- Verify transcription accuracy
- Verify LLM output uses tenant prompt
- Test multi-tenant user: belongs to 2 tenants, selects one
- Test manager vs member task visibility

## Risks
- Whisper API may have rate limits or latency
- Voice message file format compatibility
- LLM prompt engineering for reliable output
- Cost per API call (monitor usage)

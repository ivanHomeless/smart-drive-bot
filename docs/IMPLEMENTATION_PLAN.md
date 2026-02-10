# CarQuery AI Bot — Implementation Plan

## Context

Building a Telegram bot for a car dealership from scratch. The PRD (`PRD_CarQuery AI_Bot.md`) defines 5 service branches (sell, buy, find, check, legal) + AI freetext, each as a multi-step dialog that collects data and sends qualified leads to AmoCRM. The codebase is empty — only the PRD exists.

## Key Decisions

| Decision | Choice |
|----------|--------|
| FSM Storage | RedisStorage (state_ttl=1800, silent expiry) |
| FSM Pattern | Generic base class (declarative step configs) |
| AmoCRM Auth | Simplified OAuth (external integration, no web server) |
| Token Refresh | Lazy on-request + 401 retry (refresh_token is single-use) |
| AmoCRM | Mock mode for dev (AMOCRM_MOCK_MODE=true) |
| CRM Tasks | Deferred to v2 |
| Failed Leads Retry | In-process asyncio task (every 5 min) |
| DB Migrations | Alembic autogenerate from ORM models |
| Logging | Standard Python logging |
| Dependencies | requirements.txt only |
| Dockerfile | Multi-stage build |
| Bot Mode | Long polling only |
| Health Check | aiohttp on port 8080 /health |
| Testing | Alongside code |
| Bot Commands | /start, /help, /menu |
| Back on step 1 | Hidden (only Home shown) |
| /start mid-dialog | Warn first (Yes/No to reset) |
| Edit from confirmation | Pick field -> edit -> return to confirmation |
| Phone | International (phonenumbers lib) |
| Photos | Telegram file_ids only |
| AI Pre-fill | Pre-fill branch form with extracted entities |
| Custom budget | Single max number |
| Bad input | Generic error + repeat step |
| Localization | Russian only, hardcoded |
| Admin alerts | Same bot, ADMIN_CHAT_ID |
| Concurrency | One dialog at a time |

---

## Phase 0: Project Skeleton & Infrastructure [DONE]

**Goal:** Runnable project with Docker, DB, config, /start handler.

### Files to create:
- `requirements.txt` — aiogram 3.x, aiohttp, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, phonenumbers, redis
- `.env.example` — all vars from PRD s.8 + REDIS_URL, AMOCRM_MOCK_MODE, HEALTH_CHECK_PORT
- `.gitignore` — .env, .venv, __pycache__, .idea, logs/
- `src/__init__.py`
- `src/config.py` — Pydantic Settings with all env vars (Telegram, DB, Redis, AmoCRM + custom field IDs, OpenAI, App)
- `src/db/__init__.py`, `src/db/engine.py` — create_async_engine, async_sessionmaker(expire_on_commit=False)
- `src/db/models.py` — User, Lead, AmoToken, AiLog (from PRD s.6.3)
- `src/main.py` — entry point: logging, engine, Bot, Dispatcher(storage=RedisStorage), register middlewares/routers/commands, health check server, failed-leads retry task, dp.start_polling()
- `src/bot/__init__.py`
- `src/bot/handlers/__init__.py` — get_main_router() includes all sub-routers in order
- `src/bot/handlers/start.py` — /start (with mid-dialog warning), /help, /menu, service:* callback routing
- `src/bot/keyboards/main_menu.py` — 6 buttons in 2 columns per PRD s.3.3
- `src/bot/keyboards/navigation.py` — get_nav_keyboard(show_back, show_skip)
- `src/bot/middlewares/__init__.py`, `src/bot/middlewares/db.py` — DbSessionMiddleware
- `src/bot/middlewares/logging_mw.py` — log user_id, update type, duration
- `alembic.ini`, `alembic/env.py` (async), `alembic/versions/`
- `Dockerfile` — multi-stage (deps stage + runtime stage, python:3.12-slim)
- `docker-compose.yml` — bot, postgres:16-alpine, redis:7-alpine with healthchecks
- `tests/__init__.py`, `tests/conftest.py`, `tests/test_handlers/__init__.py`
- `tests/test_handlers/test_start.py`

### Tests:
- /start shows welcome + 6 buttons
- /start mid-dialog shows reset warning
- Config loads from env
- Health check returns 200

---

## Phase 1: Utilities, Common Handlers, Repositories [DONE]

**Goal:** Phone validation, retry decorator, formatters, navigation, throttling, DB repositories.

### Files:
- `src/utils/__init__.py`
- `src/utils/phone.py` — `validate_phone(text, default_region="RU") -> str | None` (E.164 via phonenumbers)
- `src/utils/retry.py` — `async_retry(max_attempts, backoff_base, retry_on, on_401)` decorator
- `src/utils/formatters.py` — `format_confirmation()`, `format_lead_note()`, `format_lead_title()`
- `src/utils/admin.py` — `notify_admin(bot, text)` sends to ADMIN_CHAT_ID
- `src/bot/filters/__init__.py`, `src/bot/filters/phone.py` — PhoneFilter (validates text or contact)
- `src/bot/handlers/common.py` — nav:home, confirm_reset:yes/no handlers
- `src/bot/handlers/errors.py` — global error handler + stale callback catch-all
- `src/bot/middlewares/throttling.py` — in-memory rate limiter per user_id
- `src/db/repositories/__init__.py`
- `src/db/repositories/user.py` — UserRepository (get_by_telegram_id, create_or_update)
- `src/db/repositories/lead.py` — LeadRepository (create, update_status, get_failed_leads, increment_retry)
- `src/db/repositories/token.py` — TokenRepository (get_current, save)
- `src/db/repositories/ai_log.py` — AiLogRepository

### Tests:
- validate_phone with valid RU, international, invalid inputs
- async_retry: retries, backoff, on_401 callback
- format_confirmation output matches PRD format
- PhoneFilter returns normalized phone or False
- nav:home clears state and shows menu
- All repository CRUD operations

---

## Phase 2: Generic Base FSM Handler (Core Architecture) [DONE]

**Goal:** Reusable dialog engine all 5 branches inherit from.

### File: `src/bot/handlers/base_dialog.py`

#### StepConfig dataclass:
```python
@dataclass
class StepConfig:
    key: str               # FSM data key (e.g., "car_brand")
    state: State           # aiogram State
    prompt_text: str       # Message to show user
    step_type: StepType    # TEXT_INPUT | BUTTON_SELECT | PHONE_INPUT | PHOTO_UPLOAD | CUSTOM
    buttons: list[tuple[str, str]] | None  # [(label, callback_value)]
    required: bool = True
    validator: Callable | None = None
    error_text: str = "..."
    display_label: str = ""
    keyboard_columns: int = 2
```

#### BaseDialogHandler class:
- Owns a `Router`, auto-registers handlers from `steps: list[StepConfig]`
- **Step types**: TEXT_INPUT (text + validator), BUTTON_SELECT (inline buttons), PHONE_INPUT (contact button + text fallback), PHOTO_UPLOAD (multi-photo + "Done" button), CUSTOM (override method)
- **Navigation**: nav:back and nav:skip registered per-branch via `StateFilter(self.states_group)` — no cross-branch interference
- **Back on step 0**: Hidden (keyboard built without Back button when step_index==0)
- **_advance()**: Moves to next step or confirmation. If `__editing_field__` is set in FSM data, returns to confirmation instead
- **Confirmation screen**: Shows all collected data, buttons: Send/Edit/Cancel
- **Edit flow**: confirm:edit -> show field list as buttons -> user picks field -> set `__editing_field__` in FSM data -> go to that step -> after input, `_advance()` detects `__editing_field__` -> return to confirmation
- **confirm:send**: Calls LeadProcessor, clears state, shows success/fallback message

### Also create:
- `src/bot/keyboards/confirm.py` — confirmation and edit-field keyboards

### Tests:
- Full step progression (step 0 -> 1 -> 2 -> confirmation)
- nav:back from step 2 returns to step 1
- nav:skip on optional step advances
- Back button absent on step 0
- Text validation: invalid -> error + re-prompt
- Edit flow: confirmation -> pick field -> edit -> return to confirmation
- confirm:cancel clears state

---

## Phase 3: All Five Service Branches [DONE]

**Goal:** Implement sell, buy, find, check, legal as BaseDialogHandler subclasses.

### Per branch: states file + keyboard file + handler file

**Sell** (`src/bot/states/sell.py`, `src/bot/keyboards/sell_kb.py`, `src/bot/handlers/sell.py`):
Steps: car_brand(text) -> year(buttons) -> mileage(text, numeric) -> price(buttons + text) -> photos(photo, optional) -> name(text) -> phone(phone) -> comment(text, optional)

**Buy** (`src/bot/states/buy.py`, `src/bot/keyboards/buy_kb.py`, `src/bot/handlers/buy.py`):
Steps: car_brand(text) -> budget(buttons + "custom" triggers single-number text input) -> year_from(buttons/text) -> transmission(buttons) -> drive(buttons) -> name -> phone -> comment
- Special: "custom budget" — clicking "Specify own" sets a flag, then text handler accepts a max number

**Find** (`src/bot/states/find.py`, `src/bot/keyboards/find_kb.py`, `src/bot/handlers/find.py`):
Steps: purpose(buttons + "Other" text) -> budget(buttons + custom) -> brand_preference(text + "Any" button) -> body_type(buttons) -> name -> phone -> comment

**Check** (`src/bot/states/check.py`, `src/bot/keyboards/check_kb.py`, `src/bot/handlers/check.py`):
Steps: check_type(buttons) -> car_brand(text) -> vin(text, optional) -> name -> phone -> comment

**Legal** (`src/bot/states/legal.py`, `src/bot/keyboards/legal_kb.py`, `src/bot/handlers/legal.py`):
Steps: question_type(buttons + "Other" text) -> description(text) -> name -> phone -> comment

### Tests per branch:
- Full happy path -> confirmation -> send
- Validation errors
- Skip optional steps
- Back navigation
- Edit from confirmation
- Custom budget / "Other" text flows

---

## Phase 4: AmoCRM Integration [DONE]

**Goal:** Full client with OAuth, mock mode, retry logic.

### Files:
- `src/services/__init__.py`, `src/services/amocrm/__init__.py`
- `src/services/amocrm/models.py` — AmoContact, AmoLead, AmoNote (Pydantic)
- `src/services/amocrm/auth.py` — AmoCRMAuth: simplified OAuth (external integration, no web server needed). Lazy token refresh (check before each call, refresh if <5 min to expiry), handle_401() force refresh, asyncio.Lock for concurrency safety. Cache token in memory + persist to DB. Each refresh_token is single-use — always save the new pair.
- `src/services/amocrm/client.py` — AmoCRMClient: _request() with @async_retry, 10s timeout, 401/429/5xx handling
- `src/services/amocrm/contacts.py` — ContactsService: find_by_phone, create, update
- `src/services/amocrm/leads.py` — LeadsService: create (with pipeline_id, status_id, custom_fields, _embedded.contacts)
- `src/services/amocrm/notes.py` — NotesService: add_to_lead
- `src/services/amocrm/mock.py` — MockAmoCRMClient: overrides _request() to log and return fake data. Instantiated when AMOCRM_MOCK_MODE=true
- `src/services/lead_processor.py` — LeadProcessor: process(user_id, telegram_user, service_type, data) orchestrates the full pipeline (DB lead -> find/create contact -> create lead -> add note -> update status). retry_failed_leads() for background task.

### Tests:
- Auth: cached vs expired token, 401 handling
- Client: retry on 429/5xx, timeout
- Mock client: returns valid fake responses
- LeadProcessor: happy path (sent), failure path (failed + admin notified)
- retry_failed_leads picks up and retries

---

## Phase 5: OpenAI AI Module [DONE]

**Goal:** Intent classification, entity extraction, freetext handler with pre-fill. Two-tier model strategy (gpt-4o-mini default, gpt-4o smart fallback).

### Files:
- `src/services/openai_client/__init__.py`
- `src/services/openai_client/models.py` — AIResponse(intent, confidence, entities, reply, model_used)
- `src/services/openai_client/prompts.py` — SYSTEM_PROMPT constant from PRD s.4.3
- `src/services/openai_client/client.py` — OpenAIClient.classify(user_message) -> AIResponse. 500 char truncation, 10s timeout, JSON parse with fallback. **Smart fallback**: if gpt-4o-mini returns confidence < 0.65, invalid JSON, or empty intent — automatically retries with gpt-4o.
- `src/bot/states/freetext.py` — FreetextStates(chatting)
- `src/bot/handlers/freetext.py` — service:freetext callback, message handler with: ai_message_count tracking (max 3 then escalate), confidence >= 0.7 -> suggest branch with pre-filled entities, otherwise -> reply text

### Smart fallback logic:
```python
response = await self._call_model(message, model=settings.OPENAI_MODEL)  # gpt-4o-mini
if needs_fallback(response):  # confidence < 0.65, bad JSON, empty intent
    response = await self._call_model(message, model=settings.OPENAI_FALLBACK_MODEL)  # gpt-4o
```

### AI Pre-fill mechanism:
When user accepts branch suggestion, entities from OpenAI (brand, model, year, budget, mileage) are stored in FSM data. The branch's `_send_step` detects pre-filled values and shows "Current value: {value}" with an "Accept" shortcut button.

### Tests:
- classify with gpt-4o-mini: valid JSON, high confidence -> no fallback
- classify with low confidence -> triggers gpt-4o fallback
- classify with invalid JSON from mini -> triggers gpt-4o fallback
- Freetext: 3 messages then escalation
- High confidence -> branch suggestion
- Pre-filled entities carried to branch

---

## Phase 6: Integration & Edge Cases [DONE]

**Goal:** Wire everything together, handle PRD edge case checklist.

### Work:
1. **Stale callbacks** — catch-all in errors.py: `callback.answer("Button no longer active", show_alert=True)`
2. **Unexpected content** — per-branch fallback: `message.answer("Please use text or buttons")`
3. **Wire LeadProcessor** into base_dialog.py confirm:send handler
4. **/start mid-dialog guard** — full flow with confirm_reset:yes/no
5. **Background retry task** — asyncio.create_task in main.py

### Tests:
- Full E2E: /start -> branch -> all steps -> confirm:send -> CRM (mock) -> success
- Failed CRM -> lead saved as failed -> admin notified
- Stale callback -> alert
- Unexpected content -> error prompt
- /start mid-dialog -> warning -> reset/continue

---

## Phase 7: Docker & Final Polish [DONE]

### Files:
- Final docker-compose.yml (bot + postgres + redis)
- `scripts/init_db.py` — programmatic Alembic upgrade
- `scripts/setup_amocrm.py` — one-time script: takes authorization code from AmoCRM UI (simplified auth), exchanges it for access_token + refresh_token via POST /oauth2/access_token, saves to DB. No web server needed.
- `tests/test_services/test_amocrm.py`
- `tests/test_services/test_openai_client.py`
- `tests/test_services/test_lead_processor.py`
- `tests/test_utils/test_phone.py`, `tests/test_utils/test_retry.py`

---

## Dependency Graph

```
Phase 0 (Skeleton)
  |
  v
Phase 1 (Utilities, Nav, Repos)
  |
  +---> Phase 2 (Base FSM Handler) ---> Phase 3 (5 Branches)
  |                                          |
  +---> Phase 4 (AmoCRM)                     |
  |         |                                |
  |         +-------> Phase 5 (OpenAI) <---+
  |                        |
  +----------------------->+
                           |
                     Phase 6 (Integration)
                           |
                     Phase 7 (Docker & Polish)
```

Phases 2 and 4 can run in parallel. Phase 3 depends on Phase 2. Phase 5 depends on Phases 3+4. Phase 6 integrates all.

---

## Verification

1. **Unit tests**: `pytest tests/` after each phase
2. **Manual smoke test**: Run bot locally with `AMOCRM_MOCK_MODE=true`, walk through each branch in Telegram
3. **Docker test**: `docker compose up -d --build`, verify bot responds, check health endpoint
4. **CRM integration test**: With real AmoCRM credentials, verify contact/lead/note creation
5. **Edge cases**: Run through PRD s.9 checklist (stale callbacks, /start mid-dialog, bad input, etc.)

---

## Status

All 7 phases are complete. 176 unit/integration tests pass (`pytest tests/`).

The bot is ready for production deployment with real AmoCRM credentials and OpenAI API key.

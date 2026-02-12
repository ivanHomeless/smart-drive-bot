"""Tests for BaseDialogHandler (Phase 2 core architecture)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message, Contact, PhotoSize

from src.bot.handlers.base_dialog import (
    BaseDialogHandler,
    StepConfig,
    StepType,
    SUCCESS_TEXT,
)
from src.bot.keyboards.main_menu import WELCOME_TEXT


# ---------------------------------------------------------------
# Test dialog: a minimal 3-step branch for testing
# ---------------------------------------------------------------

class SampleStates(StatesGroup):
    car_brand = State()
    year = State()
    comment = State()


class SampleDialogHandler(BaseDialogHandler):
    service_type = "test"
    states_group = SampleStates
    steps = [
        StepConfig(
            key="car_brand",
            state=SampleStates.car_brand,
            prompt_text="Введите марку авто:",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="year",
            state=SampleStates.year,
            prompt_text="Выберите год:",
            step_type=StepType.BUTTON_SELECT,
            buttons=[
                ("2020-2024", "2020-2024"),
                ("2015-2019", "2015-2019"),
                ("2010-2014", "2010-2014"),
            ],
        ),
        StepConfig(
            key="comment",
            state=SampleStates.comment,
            prompt_text="Комментарий (необязательно):",
            step_type=StepType.TEXT_INPUT,
            required=False,
        ),
    ]


# Instantiate handler once for all tests
test_handler = SampleDialogHandler()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def make_state(
    storage: MemoryStorage,
    state_value: str | None = None,
    data: dict | None = None,
) -> FSMContext:
    key = StorageKey(bot_id=1, chat_id=123, user_id=123)
    ctx = FSMContext(storage=storage, key=key)
    if state_value:
        await ctx.set_state(state_value)
    if data:
        await ctx.update_data(**data)
    return ctx


def make_callback(data: str) -> CallbackQuery:
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.message = MagicMock(spec=Message)
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    cb.from_user = MagicMock()
    cb.from_user.id = 123
    return cb


def make_message(text: str | None = None) -> Message:
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.answer = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 123
    return msg


# ---------------------------------------------------------------
# Tests: Entry
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_entry_starts_at_step_0():
    storage = MemoryStorage()
    state = await make_state(storage)
    cb = make_callback(f"service:test")

    await test_handler._on_entry(cb, state)

    current = await state.get_state()
    assert current == SampleStates.car_brand.state
    cb.answer.assert_called_once()


# ---------------------------------------------------------------
# Tests: Step progression
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_text_input_advances_to_next_step():
    """Text input on step 0 should save value and advance to step 1."""
    storage = MemoryStorage()
    state = await make_state(storage, state_value=SampleStates.car_brand.state)
    msg = make_message("Toyota Camry")

    handler_fn = test_handler._make_text_handler(test_handler.steps[0])
    await handler_fn(msg, state)

    data = await state.get_data()
    assert data["car_brand"] == "Toyota Camry"
    current = await state.get_state()
    assert current == SampleStates.year.state


@pytest.mark.asyncio
async def test_button_select_advances_to_next_step():
    """Button select on step 1 should save display label and advance."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.year.state,
        data={"car_brand": "Toyota Camry"},
    )
    cb = make_callback("step:year:2020-2024")

    handler_fn = test_handler._make_button_handler(test_handler.steps[1])
    await handler_fn(cb, state)

    data = await state.get_data()
    assert data["year"] == "2020-2024"
    # Should advance to step 2 (comment)
    current = await state.get_state()
    assert current == SampleStates.comment.state


@pytest.mark.asyncio
async def test_full_progression_to_confirmation():
    """Walk through all 3 steps and verify confirmation is shown."""
    storage = MemoryStorage()
    state = await make_state(storage)

    # Step 0: entry
    cb_entry = make_callback("service:test")
    await test_handler._on_entry(cb_entry, state)
    assert await state.get_state() == SampleStates.car_brand.state

    # Step 1: text input
    msg1 = make_message("BMW X5")
    handler_fn1 = test_handler._make_text_handler(test_handler.steps[0])
    await handler_fn1(msg1, state)
    assert await state.get_state() == SampleStates.year.state

    # Step 2: button select
    cb_year = make_callback("step:year:2015-2019")
    handler_fn2 = test_handler._make_button_handler(test_handler.steps[1])
    await handler_fn2(cb_year, state)
    assert await state.get_state() == SampleStates.comment.state

    # Step 3: text input (last step -> confirmation)
    msg3 = make_message("No comments")
    handler_fn3 = test_handler._make_text_handler(test_handler.steps[2])
    await handler_fn3(msg3, state)

    data = await state.get_data()
    assert data["car_brand"] == "BMW X5"
    assert data["year"] == "2015-2019"
    assert data["comment"] == "No comments"
    assert data.get("__confirming__") is True


# ---------------------------------------------------------------
# Tests: Navigation - back
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_nav_back_from_step_1_returns_to_step_0():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.year.state,
        data={"car_brand": "Toyota"},
    )
    cb = make_callback("nav:back")

    await test_handler._on_nav_back(cb, state)

    current = await state.get_state()
    assert current == SampleStates.car_brand.state


@pytest.mark.asyncio
async def test_nav_back_on_step_0_stays():
    """Back on step 0 should not go anywhere."""
    storage = MemoryStorage()
    state = await make_state(storage, state_value=SampleStates.car_brand.state)
    cb = make_callback("nav:back")

    await test_handler._on_nav_back(cb, state)

    current = await state.get_state()
    assert current == SampleStates.car_brand.state


# ---------------------------------------------------------------
# Tests: Navigation - skip
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_nav_skip_on_optional_step_advances():
    """Skip on optional step (comment) should advance to confirmation."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.comment.state,
        data={"car_brand": "Toyota", "year": "2020-2024"},
    )
    cb = make_callback("nav:skip")

    await test_handler._on_nav_skip(cb, state)

    data = await state.get_data()
    assert data.get("__confirming__") is True


@pytest.mark.asyncio
async def test_nav_skip_on_required_step_does_nothing():
    """Skip on required step (car_brand) should do nothing."""
    storage = MemoryStorage()
    state = await make_state(storage, state_value=SampleStates.car_brand.state)
    cb = make_callback("nav:skip")

    await test_handler._on_nav_skip(cb, state)

    # Should stay on the same step
    current = await state.get_state()
    assert current == SampleStates.car_brand.state


# ---------------------------------------------------------------
# Tests: Back button absent on step 0
# ---------------------------------------------------------------

def test_back_button_absent_on_step_0():
    """Step 0 keyboard should not have a Back button."""
    step = test_handler.steps[0]
    keyboard = test_handler._build_step_keyboard(step, step_index=0)

    callback_data_list = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
    ]
    assert "nav:back" not in callback_data_list
    assert "nav:home" in callback_data_list


def test_back_button_present_on_step_1():
    """Step 1 keyboard should have a Back button."""
    step = test_handler.steps[1]
    keyboard = test_handler._build_step_keyboard(step, step_index=1)

    callback_data_list = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
    ]
    assert "nav:back" in callback_data_list


def test_skip_button_present_on_optional_step():
    """Optional step should have a Skip button."""
    step = test_handler.steps[2]  # comment (optional)
    keyboard = test_handler._build_step_keyboard(step, step_index=2)

    callback_data_list = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
    ]
    assert "nav:skip" in callback_data_list


def test_skip_button_absent_on_required_step():
    """Required step should not have a Skip button."""
    step = test_handler.steps[0]  # car_brand (required)
    keyboard = test_handler._build_step_keyboard(step, step_index=0)

    callback_data_list = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
    ]
    assert "nav:skip" not in callback_data_list


# ---------------------------------------------------------------
# Tests: Text validation
# ---------------------------------------------------------------

class ValidatedStates(StatesGroup):
    mileage = State()


def validate_mileage(text: str) -> str | None:
    try:
        val = int(text.replace(" ", ""))
        if val < 0:
            return None
        return str(val)
    except ValueError:
        return None


class ValidatedDialogHandler(BaseDialogHandler):
    service_type = "validated_test"
    states_group = ValidatedStates
    steps = [
        StepConfig(
            key="mileage",
            state=ValidatedStates.mileage,
            prompt_text="Введите пробег:",
            step_type=StepType.TEXT_INPUT,
            validator=validate_mileage,
            error_text="Пробег должен быть числом.",
        ),
    ]


validated_handler = ValidatedDialogHandler()


@pytest.mark.asyncio
async def test_validator_rejects_invalid_input():
    storage = MemoryStorage()
    state = await make_state(storage, state_value=ValidatedStates.mileage.state)
    msg = make_message("not a number")

    handler_fn = validated_handler._make_text_handler(validated_handler.steps[0])
    await handler_fn(msg, state)

    # Should show error and stay on same step
    msg.answer.assert_called_once_with("Пробег должен быть числом.")
    data = await state.get_data()
    assert "mileage" not in data


@pytest.mark.asyncio
async def test_validator_accepts_valid_input():
    storage = MemoryStorage()
    state = await make_state(storage, state_value=ValidatedStates.mileage.state)
    msg = make_message("85000")

    handler_fn = validated_handler._make_text_handler(validated_handler.steps[0])
    await handler_fn(msg, state)

    data = await state.get_data()
    assert data["mileage"] == "85000"


# ---------------------------------------------------------------
# Tests: Edit flow
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirm_edit_shows_field_list():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.comment.state,
        data={
            "car_brand": "Toyota",
            "year": "2020-2024",
            "comment": "Test",
            "__confirming__": True,
        },
    )
    cb = make_callback("confirm:edit")

    await test_handler._on_confirm_edit(cb, state)

    cb.message.edit_text.assert_called_once()
    args, kwargs = cb.message.edit_text.call_args
    assert "редактирования" in args[0]
    keyboard = kwargs["reply_markup"]
    callback_data_list = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
    ]
    assert "edit_field:car_brand" in callback_data_list
    assert "edit_field:year" in callback_data_list
    assert "edit_field:back" in callback_data_list


@pytest.mark.asyncio
async def test_edit_field_select_navigates_to_step():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.comment.state,
        data={
            "car_brand": "Toyota",
            "year": "2020-2024",
            "__confirming__": True,
        },
    )
    cb = make_callback("edit_field:car_brand")

    await test_handler._on_edit_field_select(cb, state)

    current = await state.get_state()
    assert current == SampleStates.car_brand.state
    data = await state.get_data()
    assert data["__editing_field__"] == "car_brand"


@pytest.mark.asyncio
async def test_edit_field_back_returns_to_confirmation():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.comment.state,
        data={
            "car_brand": "Toyota",
            "year": "2020-2024",
            "__confirming__": True,
        },
    )
    cb = make_callback("edit_field:back")

    await test_handler._on_edit_field_select(cb, state)

    data = await state.get_data()
    assert data.get("__confirming__") is True


@pytest.mark.asyncio
async def test_after_editing_returns_to_confirmation():
    """After editing a field, _advance should return to confirmation."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.car_brand.state,
        data={
            "car_brand": "Toyota",
            "year": "2020-2024",
            "__editing_field__": "car_brand",
        },
    )
    msg = make_message("Honda Accord")

    handler_fn = test_handler._make_text_handler(test_handler.steps[0])
    await handler_fn(msg, state)

    data = await state.get_data()
    assert data["car_brand"] == "Honda Accord"
    assert data.get("__confirming__") is True
    assert data.get("__editing_field__") is None


# ---------------------------------------------------------------
# Tests: Confirm cancel
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirm_cancel_clears_state():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.comment.state,
        data={"car_brand": "Toyota", "__confirming__": True},
    )
    cb = make_callback("confirm:cancel")

    await test_handler._on_confirm_cancel(cb, state)

    current = await state.get_state()
    assert current is None
    cb.message.answer.assert_called_once()
    args = cb.message.answer.call_args[0]
    assert args[0] == WELCOME_TEXT


# ---------------------------------------------------------------
# Tests: Confirm send
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirm_send_clears_state_and_shows_success():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SampleStates.comment.state,
        data={
            "car_brand": "Toyota",
            "year": "2020-2024",
            "__confirming__": True,
        },
    )
    cb = make_callback("confirm:send")

    await test_handler._on_confirm_send(cb, state)

    current = await state.get_state()
    assert current is None
    cb.message.edit_text.assert_called_once_with(SUCCESS_TEXT)


# ---------------------------------------------------------------
# Tests: Photo upload
# ---------------------------------------------------------------

class PhotoStates(StatesGroup):
    photos = State()
    name = State()


class PhotoDialogHandler(BaseDialogHandler):
    service_type = "photo_test"
    states_group = PhotoStates
    steps = [
        StepConfig(
            key="photos",
            state=PhotoStates.photos,
            prompt_text="Отправьте фото:",
            step_type=StepType.PHOTO_UPLOAD,
            required=False,
        ),
        StepConfig(
            key="name",
            state=PhotoStates.name,
            prompt_text="Введите имя:",
            step_type=StepType.TEXT_INPUT,
        ),
    ]


photo_handler = PhotoDialogHandler()


@pytest.mark.asyncio
async def test_photo_upload_collects_file_ids():
    storage = MemoryStorage()
    state = await make_state(storage, state_value=PhotoStates.photos.state)

    msg = MagicMock(spec=Message)
    msg.answer = AsyncMock()
    photo1 = MagicMock(spec=PhotoSize)
    photo1.file_id = "file_id_1"
    photo2 = MagicMock(spec=PhotoSize)
    photo2.file_id = "file_id_1_large"
    msg.photo = [photo1, photo2]  # last is largest

    handler_fn = photo_handler._make_photo_handler(photo_handler.steps[0])
    await handler_fn(msg, state)

    data = await state.get_data()
    assert data["photos"] == ["file_id_1_large"]
    assert "1 шт." in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_photo_done_advances():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=PhotoStates.photos.state,
        data={"photos": ["file_id_1"]},
    )
    cb = make_callback("step:photos:done")

    handler_fn = photo_handler._make_photo_done_handler(photo_handler.steps[0])
    await handler_fn(cb, state)

    current = await state.get_state()
    assert current == PhotoStates.name.state


# ---------------------------------------------------------------
# Tests: StepConfig defaults
# ---------------------------------------------------------------

def test_step_config_auto_display_label():
    step = StepConfig(
        key="car_brand",
        state=SampleStates.car_brand,
        prompt_text="test",
        step_type=StepType.TEXT_INPUT,
    )
    assert step.display_label == "Марка/Модель"


def test_step_config_custom_display_label():
    step = StepConfig(
        key="car_brand",
        state=SampleStates.car_brand,
        prompt_text="test",
        step_type=StepType.TEXT_INPUT,
        display_label="Custom Label",
    )
    assert step.display_label == "Custom Label"

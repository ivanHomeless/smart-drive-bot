"""Tests for LeadProcessor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.lead_processor import LeadProcessor


def make_processor(
    find_contact_result=None,
    create_contact_id=1001,
    create_lead_id=2001,
    create_note_id=3001,
) -> tuple[LeadProcessor, dict]:
    """Create a LeadProcessor with mocked services."""
    contacts = MagicMock()
    contacts.find_by_phone = AsyncMock(return_value=find_contact_result)
    contacts.create = AsyncMock(return_value=create_contact_id)
    contacts.update = AsyncMock()

    leads_svc = MagicMock()
    leads_svc.create = AsyncMock(return_value=create_lead_id)

    notes = MagicMock()
    notes.add_to_lead = AsyncMock(return_value=create_note_id)

    bot = MagicMock()
    bot.send_message = AsyncMock()

    processor = LeadProcessor(contacts, leads_svc, notes, bot)
    mocks = {
        "contacts": contacts,
        "leads": leads_svc,
        "notes": notes,
        "bot": bot,
    }
    return processor, mocks


def make_session():
    """Create a mock DB session with user/lead repos."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


TELEGRAM_USER = {
    "id": 123456,
    "username": "testuser",
    "first_name": "Ivan",
}

SELL_DATA = {
    "car_brand": "Toyota Camry",
    "year": "2022",
    "mileage": "85 000 км",
    "price": "1 800 000",
    "name": "Ivan",
    "phone": "+79991234567",
}


# ---------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_lead_processor_happy_path_new_contact():
    """Full pipeline: new contact created, lead sent, note added."""
    processor, mocks = make_processor(find_contact_result=None)
    session = make_session()

    with patch("src.services.lead_processor.UserRepository") as MockUserRepo, \
         patch("src.services.lead_processor.LeadRepository") as MockLeadRepo:

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.amo_contact_id = None
        MockUserRepo.return_value.create_or_update = AsyncMock(return_value=mock_user)

        mock_lead = MagicMock()
        mock_lead.id = 10
        MockLeadRepo.return_value.create = AsyncMock(return_value=mock_lead)
        MockLeadRepo.return_value.update_status = AsyncMock()

        result = await processor.process(
            session=session,
            telegram_user=TELEGRAM_USER,
            service_type="sell",
            data=SELL_DATA,
        )

    assert result is True
    mocks["contacts"].find_by_phone.assert_called_once_with("+79991234567")
    mocks["contacts"].create.assert_called_once()
    mocks["leads"].create.assert_called_once()
    mocks["notes"].add_to_lead.assert_called_once()


@pytest.mark.asyncio
async def test_lead_processor_existing_contact():
    """Existing contact found by phone -> update, not create."""
    existing_contact = {"id": 5001, "name": "Old Contact"}
    processor, mocks = make_processor(find_contact_result=existing_contact)
    session = make_session()

    with patch("src.services.lead_processor.UserRepository") as MockUserRepo, \
         patch("src.services.lead_processor.LeadRepository") as MockLeadRepo:

        mock_user = MagicMock()
        mock_user.id = 1
        MockUserRepo.return_value.create_or_update = AsyncMock(return_value=mock_user)

        mock_lead = MagicMock()
        mock_lead.id = 10
        MockLeadRepo.return_value.create = AsyncMock(return_value=mock_lead)
        MockLeadRepo.return_value.update_status = AsyncMock()

        result = await processor.process(
            session=session,
            telegram_user=TELEGRAM_USER,
            service_type="sell",
            data=SELL_DATA,
        )

    assert result is True
    mocks["contacts"].create.assert_not_called()
    mocks["contacts"].update.assert_called_once_with(5001)


# ---------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_lead_processor_crm_failure():
    """CRM error -> lead saved as error, admin notified, returns False."""
    processor, mocks = make_processor()
    mocks["contacts"].find_by_phone.side_effect = RuntimeError("CRM unavailable")
    session = make_session()

    with patch("src.services.lead_processor.UserRepository") as MockUserRepo, \
         patch("src.services.lead_processor.LeadRepository") as MockLeadRepo, \
         patch("src.services.lead_processor.notify_admin", new_callable=AsyncMock) as mock_notify:

        mock_user = MagicMock()
        mock_user.id = 1
        MockUserRepo.return_value.create_or_update = AsyncMock(return_value=mock_user)

        mock_lead = MagicMock()
        mock_lead.id = 10
        MockLeadRepo.return_value.create = AsyncMock(return_value=mock_lead)
        MockLeadRepo.return_value.update_status = AsyncMock()

        result = await processor.process(
            session=session,
            telegram_user=TELEGRAM_USER,
            service_type="sell",
            data=SELL_DATA,
        )

    assert result is False
    # Lead should be updated to error status
    MockLeadRepo.return_value.update_status.assert_called()
    call_args = MockLeadRepo.return_value.update_status.call_args
    assert call_args.kwargs.get("status") == "error" or call_args[1].get("status") == "error"
    # Admin should be notified
    mock_notify.assert_called_once()


# ---------------------------------------------------------------
# Data persistence
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_lead_processor_saves_user():
    """User is saved/updated in DB with phone."""
    processor, mocks = make_processor()
    session = make_session()

    with patch("src.services.lead_processor.UserRepository") as MockUserRepo, \
         patch("src.services.lead_processor.LeadRepository") as MockLeadRepo:

        mock_user = MagicMock()
        mock_user.id = 1
        MockUserRepo.return_value.create_or_update = AsyncMock(return_value=mock_user)

        mock_lead = MagicMock()
        mock_lead.id = 10
        MockLeadRepo.return_value.create = AsyncMock(return_value=mock_lead)
        MockLeadRepo.return_value.update_status = AsyncMock()

        await processor.process(
            session=session,
            telegram_user=TELEGRAM_USER,
            service_type="sell",
            data=SELL_DATA,
        )

    MockUserRepo.return_value.create_or_update.assert_called_once_with(
        telegram_id=123456,
        username="testuser",
        first_name="Ivan",
        phone="+79991234567",
    )

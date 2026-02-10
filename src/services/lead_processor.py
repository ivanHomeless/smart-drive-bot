from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot

from src.config import settings
from src.db.repositories.lead import LeadRepository
from src.db.repositories.user import UserRepository
from src.services.amocrm.contacts import ContactsService
from src.services.amocrm.leads import LeadsService
from src.services.amocrm.notes import NotesService
from src.utils.admin import notify_admin
from src.utils.formatters import format_lead_note, format_lead_title

logger = logging.getLogger(__name__)


class LeadProcessor:
    """Orchestrates the full lead pipeline:
    DB lead -> find/create contact -> create lead -> add note -> update status.
    """

    def __init__(
        self,
        contacts: ContactsService,
        leads_service: LeadsService,
        notes: NotesService,
        bot: Bot,
    ) -> None:
        self._contacts = contacts
        self._leads = leads_service
        self._notes = notes
        self._bot = bot

    async def process(
        self,
        session: Any,
        telegram_user: dict,
        service_type: str,
        data: dict,
    ) -> bool:
        """Process a completed dialog into a CRM lead.

        Args:
            session: DB async session.
            telegram_user: dict with id, username, first_name.
            service_type: One of sell/buy/find/check/legal.
            data: Collected dialog data (cleaned, no __ keys).

        Returns:
            True if lead was sent to CRM successfully, False otherwise.
        """
        user_repo = UserRepository(session)
        lead_repo = LeadRepository(session)

        telegram_id = telegram_user["id"]
        username = telegram_user.get("username")
        first_name = telegram_user.get("first_name")
        phone = data.get("phone")
        name = data.get("name", first_name or "")

        # 1. Save/update user in DB
        db_user = await user_repo.create_or_update(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            phone=phone,
        )

        # 2. Create lead in DB with status=pending
        db_lead = await lead_repo.create(
            user_id=db_user.id,
            service_type=service_type,
            data=data,
            status="pending",
        )
        await session.commit()

        try:
            # 3. Find or create contact in AmoCRM
            contact_id = await self._find_or_create_contact(
                phone=phone,
                name=name,
                telegram_id=telegram_id,
                telegram_username=username,
            )

            # Update user with amo_contact_id
            db_user.amo_contact_id = contact_id
            await session.commit()

            # 4. Create lead in AmoCRM
            title = format_lead_title(service_type, data)
            amo_lead_id = await self._leads.create(
                title=title,
                contact_id=contact_id,
                service_type=service_type,
                data=data,
            )

            # 5. Add note to lead
            note_text = format_lead_note(service_type, data, telegram_user)
            await self._notes.add_to_lead(amo_lead_id, note_text)

            # 6. Update DB lead status to sent
            await lead_repo.update_status(
                lead_id=db_lead.id,
                status="sent",
                amo_lead_id=amo_lead_id,
            )
            await session.commit()

            logger.info(
                "Lead %d sent to AmoCRM (amo_lead_id=%d) for user %d",
                db_lead.id, amo_lead_id, telegram_id,
            )
            return True

        except Exception as exc:
            logger.exception("Failed to send lead %d to AmoCRM", db_lead.id)

            await session.rollback()
            await lead_repo.update_status(
                lead_id=db_lead.id,
                status="error",
                error_message=str(exc),
            )
            await session.commit()

            await notify_admin(
                self._bot,
                f"Ошибка отправки лида #{db_lead.id} в AmoCRM:\n{exc}",
            )
            return False

    async def _find_or_create_contact(
        self,
        phone: str | None,
        name: str,
        telegram_id: int,
        telegram_username: str | None,
    ) -> int:
        """Find existing contact by phone or create a new one."""
        if phone:
            existing = await self._contacts.find_by_phone(phone)
            if existing:
                contact_id = existing["id"]
                await self._contacts.update(contact_id)
                return contact_id

        contact_id = await self._contacts.create(
            name=name,
            phone=phone or "",
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
        return contact_id


async def retry_failed_leads(
    session_factory,
    contacts: ContactsService,
    leads_service: LeadsService,
    notes: NotesService,
    bot: Bot,
) -> int:
    """Retry sending failed leads. Returns count of successfully retried leads."""
    processor = LeadProcessor(contacts, leads_service, notes, bot)
    retried = 0

    async with session_factory() as session:
        lead_repo = LeadRepository(session)
        failed_leads = await lead_repo.get_failed_leads()

        for lead in failed_leads:
            await lead_repo.increment_retry(lead.id)
            await session.commit()

            telegram_user = {
                "id": lead.user.telegram_id if lead.user else 0,
                "username": lead.user.username if lead.user else None,
                "first_name": lead.user.first_name if lead.user else None,
            }

            try:
                phone = lead.data.get("phone")
                name = lead.data.get("name", "")

                contact_id = await processor._find_or_create_contact(
                    phone=phone,
                    name=name,
                    telegram_id=telegram_user["id"],
                    telegram_username=telegram_user.get("username"),
                )

                title = format_lead_title(lead.service_type, lead.data)
                amo_lead_id = await leads_service.create(
                    title=title,
                    contact_id=contact_id,
                    service_type=lead.service_type,
                    data=lead.data,
                )

                note_text = format_lead_note(
                    lead.service_type, lead.data, telegram_user
                )
                await notes.add_to_lead(amo_lead_id, note_text)

                await lead_repo.update_status(
                    lead_id=lead.id,
                    status="sent",
                    amo_lead_id=amo_lead_id,
                )
                await session.commit()
                retried += 1
                logger.info("Retried lead %d successfully", lead.id)

            except Exception as exc:
                logger.exception("Retry failed for lead %d", lead.id)
                await session.rollback()
                await lead_repo.update_status(
                    lead_id=lead.id,
                    status="error",
                    error_message=str(exc),
                )
                await session.commit()

    return retried

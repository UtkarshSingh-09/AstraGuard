"""
Twilio WhatsApp integration for AstraGuard.
Handles sending intervention messages, milestone celebrations, and morning pulses.
"""

from __future__ import annotations

import os
import logging
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("astraguard.integrations.twilio")

# Lazy import to avoid crashing if twilio not installed yet
_twilio_client = None


def _get_client():
    """Lazy-initialize Twilio client."""
    global _twilio_client
    if _twilio_client is None:
        try:
            from twilio.rest import Client

            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")

            if not account_sid or not auth_token:
                logger.error("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env")
                return None

            _twilio_client = Client(account_sid, auth_token)
            logger.info("Twilio client initialized successfully")
        except ImportError:
            logger.error("twilio package not installed. Run: pip install twilio")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            return None

    return _twilio_client


def _get_from_number() -> str:
    """Get the Twilio WhatsApp sender number."""
    return os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


async def send_whatsapp_message(
    to_number: str,
    message_body: str,
) -> dict:
    """
    Send a WhatsApp message via Twilio.

    Args:
        to_number: Recipient's phone number (e.g., "+919876543210")
        message_body: Message text (max 1600 chars for WhatsApp)

    Returns:
        {"success": bool, "sid": str | None, "error": str | None}
    """
    client = _get_client()
    if not client:
        return {
            "success": False,
            "sid": None,
            "error": "Twilio client not initialized. Check credentials in .env",
        }

    # Ensure WhatsApp prefix
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"

    # Truncate if too long
    if len(message_body) > 1600:
        message_body = message_body[:1590] + "..."
        logger.warning("Message truncated to 1600 chars")

    # Retry up to 3 times
    last_error = None
    for attempt in range(3):
        try:
            message = client.messages.create(
                from_=_get_from_number(),
                body=message_body,
                to=to_number,
            )
            logger.info(f"WhatsApp sent to {to_number}: SID={message.sid}")
            return {
                "success": True,
                "sid": message.sid,
                "error": None,
            }
        except Exception as e:
            last_error = str(e)
            logger.warning(f"WhatsApp send attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                import asyncio
                await asyncio.sleep(2 ** attempt)  # exponential backoff

    logger.error(f"WhatsApp send failed after 3 attempts: {last_error}")
    return {
        "success": False,
        "sid": None,
        "error": f"Failed after 3 attempts: {last_error}",
    }


async def send_intervention_alert(
    user_id: str,
    phone_number: str,
    intervention_data: dict,
) -> dict:
    """
    Format and send a behavioral intervention alert via WhatsApp.

    Args:
        user_id: User identifier (for logging)
        phone_number: WhatsApp number
        intervention_data: Output from BehavioralGuardAgent

    Returns:
        {"success": bool, "sid": str | None, "error": str | None}
    """
    message_data = intervention_data.get("intervention_message", {})
    message_body = message_data.get("whatsapp_message", "")

    if not message_body:
        # Fallback to extended message
        message_body = message_data.get("extended_message", "AstraGuard Alert")

    result = await send_whatsapp_message(phone_number, message_body)

    # Log the intervention (Ankit's backend should persist this to MongoDB)
    logger.info(
        f"Intervention for user {user_id}: "
        f"severity={message_data.get('type', 'UNKNOWN')}, "
        f"sent={result['success']}"
    )

    return result


async def send_milestone_message(
    phone_number: str,
    milestone_text: str,
) -> dict:
    """Send a SIP milestone celebration message."""
    return await send_whatsapp_message(phone_number, milestone_text)

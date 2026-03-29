from __future__ import annotations

import asyncio
import imaplib
from datetime import datetime, timezone
from email import message_from_bytes
from email.message import Message
from pathlib import Path
from typing import Any


def _utc_now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _is_pdf_attachment(part: Message) -> bool:
    filename = part.get_filename() or ""
    content_type = part.get_content_type()
    return filename.lower().endswith(".pdf") or content_type == "application/pdf"


def _extract_pdf_attachments(raw_email: bytes) -> list[tuple[str, bytes]]:
    msg = message_from_bytes(raw_email)
    attachments: list[tuple[str, bytes]] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        if not _is_pdf_attachment(part):
            continue
        filename = part.get_filename() or f"cas_{_utc_now_tag()}.pdf"
        payload = part.get_payload(decode=True) or b""
        if payload:
            attachments.append((filename, payload))
    return attachments


def _fetch_latest_cams_pdf_sync(
    *,
    email_address: str,
    app_password: str,
    imap_host: str,
    imap_port: int,
    max_messages_scan: int = 20,
) -> dict[str, Any] | None:
    mailbox = imaplib.IMAP4_SSL(imap_host, imap_port)
    try:
        mailbox.login(email_address, app_password)
        mailbox.select("INBOX")
        status, data = mailbox.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return None

        msg_ids = data[0].split()
        msg_ids = msg_ids[-max_messages_scan:]
        for msg_id in reversed(msg_ids):
            f_status, f_data = mailbox.fetch(msg_id, "(RFC822)")
            if f_status != "OK" or not f_data:
                continue
            raw = f_data[0][1] if isinstance(f_data[0], tuple) else b""
            if not raw:
                continue
            attachments = _extract_pdf_attachments(raw)
            if attachments:
                filename, content = attachments[0]
                return {"filename": filename, "content": content}
        return None
    finally:
        try:
            mailbox.close()
        except Exception:
            pass
        mailbox.logout()


async def wait_for_cams_pdf_from_mailbox(
    *,
    email_address: str,
    app_password: str,
    imap_host: str = "imap.gmail.com",
    imap_port: int = 993,
    timeout_seconds: int = 180,
    poll_interval_seconds: int = 20,
) -> dict[str, Any] | None:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < deadline:
        result = await asyncio.to_thread(
            _fetch_latest_cams_pdf_sync,
            email_address=email_address,
            app_password=app_password,
            imap_host=imap_host,
            imap_port=imap_port,
        )
        if result:
            return result
        await asyncio.sleep(poll_interval_seconds)
    return None


def save_attachment_file(*, filename: str, content: bytes, prefix: str = "cams") -> str:
    out_dir = Path("artifacts/uploads")
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{prefix}_{_utc_now_tag()}_{filename}".replace(" ", "_")
    out_path = out_dir / safe_name
    out_path.write_bytes(content)
    return str(out_path)

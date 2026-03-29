from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


@dataclass
class ProviderFetchResult:
    ok: bool
    code: str
    message: str
    payload: dict[str, Any] | None = None


class CASProviderClient:
    """
    Provider adapter interface for CAS retrieval.
    Current implementation is a non-breaking stub to enable routing and graceful fallback.
    Replace request_statement() with concrete provider API call when credentials are finalized.
    """

    def is_configured(self) -> bool:
        return bool(
            settings.cas_provider_enabled
            and settings.cas_provider_base_url
            and settings.cas_provider_api_key
        )

    async def request_statement(
        self,
        *,
        user_id: str,
        pan: str,
        email: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> ProviderFetchResult:
        if not self.is_configured():
            return ProviderFetchResult(
                ok=False,
                code="provider_not_configured",
                message="CAS provider is not configured",
            )

        # Placeholder for real provider integration.
        # Expected final behavior: create request, poll completion, attach PDF metadata.
        return ProviderFetchResult(
            ok=False,
            code="provider_not_implemented",
            message=f"{settings.cas_provider_name} adapter is configured but not implemented yet",
            payload={
                "provider": settings.cas_provider_name,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "pan_last4": pan[-4:],
                "email_hint": email[:3] + "***",
                "from_date": from_date,
                "to_date": to_date,
            },
        )


cas_provider_client = CASProviderClient()

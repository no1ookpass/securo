"""Akahu provider — New Zealand banks via a free Akahu Personal App.

Akahu (https://akahu.nz) is a NZ open-finance platform. A **Personal App** is
free and issues two static tokens from https://my.akahu.nz/developers:

- a User Access Token (``user_token_...``), scoped to *your own* Akahu
  account, and
- an App ID Token (``app_token_...``).

Because those tokens are inherently personal, this provider follows the
SimpleFIN model rather than the OAuth/aggregator model: each Securo user pastes
**their own** tokens into their own connection (Accounts → Connect Bank →
Akahu). There are no server-side credentials, no OAuth redirect, no
accreditation, and no per-user fees. Both tokens are pasted into the single
token field, in any order, and parsed by their stable prefixes here.

Personal App constraints that shape this module:

- No OAuth flow, no webhooks, no payments (read-only account + transaction
  data only).
- Reads go to ``GET /v1/accounts`` and ``GET /v1/accounts/{id}/transactions``
  authenticated with ``Authorization: Bearer <user_token>`` and
  ``X-Akahu-Id: <app_token>``.
- Personal apps get 365 days of historical transactions and a daily refresh
  cadence. Securo syncs by polling, so this fits the existing model — the
  default ``trigger_refresh`` (no-op) and daily scheduled syncs work as-is.

All Akahu-specific shapes (token prefixes, account types, ``cursor``
pagination, NZFCC category groups) are contained in this module.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx

from app.agents.services.crypto import decrypt, encrypt
from app.core.config import get_settings
from app.providers.base import (
    AccountData,
    BankProvider,
    ConnectionData,
    ProviderRateLimited,
    SessionExpiredError,
    TransactionData,
    mask_last4,
)

logger = logging.getLogger(__name__)

# Personal apps are granted 365 days of historical transactions; backfill that
# far on first connect (follow-up syncs pass an explicit `since`).
AKAHU_DEFAULT_HISTORY_DAYS = 365
AKAHU_TRANSACTION_PAGE_LIMIT = 20  # safety cap on pages (100 txns/page at Akahu)
AKAHU_HTTP_TIMEOUT = 30.0

# Token prefixes from my.akahu.nz/developers. Stable enough to locate the two
# tokens in a combined paste regardless of order or whitespace.
USER_TOKEN_PREFIX = "user_token_"
APP_TOKEN_PREFIX = "app_token_"


def _parse_tokens(raw: str) -> tuple[str, str]:
    """Split a pasted Personal App string into (user_token, app_token).

    Users paste the two tokens from the Akahu Developers page into the single
    token field. They carry stable prefixes, so we locate them by prefix and
    tolerate any order, surrounding whitespace, or newlines.
    """
    parts = raw.split()
    user_token = next((p for p in parts if p.startswith(USER_TOKEN_PREFIX)), None)
    app_token = next((p for p in parts if p.startswith(APP_TOKEN_PREFIX)), None)
    if not user_token or not app_token:
        raise ValueError(
            "Akahu needs both a User Access Token (user_token_…) and an App ID "
            "Token (app_token_…) from https://my.akahu.nz/developers — paste "
            "both, in any order."
        )
    return user_token, app_token


def _map_account_type(akahu_type: Optional[str]) -> str:
    """Map an Akahu account ``type`` to Securo's internal types."""
    mapping = {
        "CHECKING": "checking",
        "SAVINGS": "savings",
        "CREDITCARD": "credit_card",
    }
    return mapping.get((akahu_type or "").upper(), "checking")


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


class AkahuProvider(BankProvider):
    """Akahu Personal App connector (paste-your-own-tokens flow)."""

    @property
    def name(self) -> str:
        return "akahu"

    @property
    def flow_type(self) -> str:
        return "token"

    # ----- credentials -----

    @staticmethod
    def _tokens(credentials: dict) -> tuple[str, str]:
        """Return (user_token, app_token) plaintext from stored credentials."""
        user_token = decrypt(credentials.get("user_token_enc")) or credentials.get(
            "user_token"
        )
        app_token = decrypt(credentials.get("app_token_enc")) or credentials.get(
            "app_token"
        )
        return user_token or "", app_token or ""

    # ----- HTTP layer -----

    def _client(self, user_token: str, app_token: str) -> httpx.AsyncClient:
        settings = get_settings()
        base_url = f"{settings.akahu_api_url.rstrip('/')}/v1"
        return httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Akahu-Id": app_token,
                "Accept": "application/json",
                "User-Agent": "Securo/0.1 (+https://usesecuro.com)",
            },
            timeout=AKAHU_HTTP_TIMEOUT,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        user_token: str,
        app_token: str,
        params: Optional[dict] = None,
    ) -> dict:
        async with self._client(user_token, app_token) as client:
            resp = await client.request(method, path, params=params)
        if resp.status_code in (401, 403):
            # Invalid/revoked tokens, or the app isn't scoped for the resource.
            # Either way the user must re-paste fresh tokens from their Akahu
            # Developers page — surface it as a reconnect, not a hard error.
            raise SessionExpiredError(
                f"Akahu rejected the credentials ({resp.status_code} for {path}). "
                "Reconnect with fresh tokens from https://my.akahu.nz/developers"
            )
        if resp.status_code == 429:
            # Akahu is throttling us — transient, not a broken connection.
            raise ProviderRateLimited(
                f"Akahu {method} {path} → 429: {resp.text[:200]}"
            )
        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Akahu {method} {path} → {resp.status_code}: {resp.text[:300]}",
                request=resp.request,
                response=resp,
            )
        data = resp.json()
        if not data.get("success", True):
            raise RuntimeError(
                f"Akahu {method} {path} reported failure: {resp.text[:300]}"
            )
        return data

    # ----- connection flow (paste-a-token) -----

    def get_oauth_url(self, *args, **kwargs):  # type: ignore[override]
        raise NotImplementedError(
            "Akahu uses a paste-a-token flow (free Personal App), not OAuth redirect"
        )

    async def handle_oauth_callback(self, code: str) -> ConnectionData:
        """Validate the pasted tokens and produce the initial ConnectionData.

        ``code`` is the raw pasted string (both tokens). We hit ``/me`` to
        validate the credentials and capture a stable external id (the Akahu
        user id — all of the user's connected banks share one Personal App, so
        one Securo connection covers them, mirroring SimpleFIN's one-access-URL
        model), then fetch the account list for the initial ``AccountData``.
        """
        user_token, app_token = _parse_tokens(code)

        me = await self._request(
            "GET", "/me", user_token=user_token, app_token=app_token
        )
        # GET /me returns a single object under `item` (not a list under
        # `items`). Tolerate the list shape as a defensive fallback.
        me_item = me.get("item")
        if not isinstance(me_item, dict):
            me_items = me.get("items") or []
            me_item = me_items[0] if me_items else None
        user_id = me_item.get("_id") if isinstance(me_item, dict) else None
        if not user_id:
            raise RuntimeError("Akahu /me did not return a user id")

        accounts_payload = await self._request(
            "GET", "/accounts", user_token=user_token, app_token=app_token
        )
        accounts = [
            acc
            for acc in (
                self._build_account(raw)
                for raw in accounts_payload.get("items") or []
            )
            if acc is not None
        ]

        credentials: dict[str, Any] = {
            "user_token_enc": encrypt(user_token) or user_token,
            "app_token_enc": encrypt(app_token) or app_token,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        # Best-effort institution label + logo from the first account's
        # `connection` object (Akahu's account model). Fall back to "Akahu".
        institution_name = "Akahu"
        logo_url: Optional[str] = None
        for raw in accounts_payload.get("items") or []:
            if not isinstance(raw, dict):
                continue
            conn = raw.get("connection") or {}
            if conn.get("name"):
                institution_name = conn["name"]
            logo_url = logo_url or conn.get("logo")
            if institution_name != "Akahu" and logo_url:
                break

        return ConnectionData(
            external_id=str(user_id),
            institution_name=institution_name,
            credentials=credentials,
            accounts=accounts,
            logo_url=logo_url,
        )

    # ----- account / transaction reads -----

    @staticmethod
    def _build_account(raw: dict) -> Optional[AccountData]:
        account_id = raw.get("_id")
        if not account_id:
            return None
        if str(raw.get("status") or "ACTIVE").upper() == "INACTIVE":
            # Akahu lost access to this account; the stored Securo row and its
            # history stay put, but we don't re-create/refresh it this run.
            logger.info("Skipping INACTIVE Akahu account %s", account_id)
            return None
        balance_obj = raw.get("balance") or {}
        balance = _to_decimal(balance_obj.get("current")) or Decimal("0")
        currency = balance_obj.get("currency") or "NZD"
        acc_type = _map_account_type(raw.get("type"))
        if acc_type == "credit_card" and balance < 0:
            # Akahu reports card debt as a negative balance; Securo stores
            # positive-for-debt (same convention as Pluggy/Enable Banking).
            balance = -balance
        return AccountData(
            external_id=str(account_id),
            name=raw.get("name") or "Account",
            type=acc_type,
            balance=balance,
            currency=currency,
            credit_limit=(
                _to_decimal(balance_obj.get("limit")) if acc_type == "credit_card" else None
            ),
            masked_number=mask_last4(raw.get("formatted_account")),
            # One Akahu connection spans many institutions, so each account
            # carries its own institution (name/logo) via the account's
            # `connection` object — the sync layer links the account to the
            # right Institution row (issue #345: ASB vs Hatch vs Gem Visa).
            institution_external_id=((raw.get("connection") or {}).get("_id") or None),
            institution_name=((raw.get("connection") or {}).get("name") or None),
            institution_logo_url=((raw.get("connection") or {}).get("logo") or None),
        )

    async def get_accounts(self, credentials: dict) -> list[AccountData]:
        user_token, app_token = self._tokens(credentials)
        if not user_token or not app_token:
            raise SessionExpiredError("Akahu credentials missing; reconnect")
        payload = await self._request(
            "GET", "/accounts", user_token=user_token, app_token=app_token
        )
        return [
            acc
            for acc in (
                self._build_account(raw) for raw in payload.get("items") or []
            )
            if acc is not None
        ]

    async def get_transactions(
        self,
        credentials: dict,
        account_external_id: str,
        since: Optional[date] = None,
        payee_source: str = "auto",
    ) -> list[TransactionData]:
        user_token, app_token = self._tokens(credentials)
        if not user_token or not app_token:
            raise SessionExpiredError("Akahu credentials missing; reconnect")

        end = date.today()
        start = since or (end - timedelta(days=AKAHU_DEFAULT_HISTORY_DAYS))
        # Akahu's `start` is exclusive; back off a day so `since` is inclusive.
        params: dict[str, str] = {
            "start": (start - timedelta(days=1)).isoformat(),
            "end": end.isoformat(),
        }

        transactions: list[TransactionData] = []
        for _ in range(AKAHU_TRANSACTION_PAGE_LIMIT):
            page = await self._request(
                "GET",
                f"/accounts/{account_external_id}/transactions",
                user_token=user_token,
                app_token=app_token,
                params=params,
            )
            for raw in page.get("items") or []:
                if not isinstance(raw, dict):
                    continue
                parsed = self._build_transaction(raw, payee_source)
                if parsed:
                    transactions.append(parsed)
            cursor = (page.get("cursor") or {}).get("next")
            if not cursor:
                break
            params["cursor"] = cursor
        return transactions

    @staticmethod
    def _build_transaction(raw: dict, payee_source: str) -> Optional[TransactionData]:
        txn_id = raw.get("_id")
        if not txn_id:
            return None
        amount = _to_decimal(raw.get("amount"))
        if amount is None:
            return None
        # Akahu signs the amount (e.g. EFTPOS → -5.5); direction follows the
        # sign, mirroring how SimpleFIN derives debit/credit.
        txn_type = "debit" if amount < 0 else "credit"
        amount = amount.copy_abs()
        txn_date = _parse_iso_date(raw.get("date"))
        if not txn_date:
            return None
        description = (raw.get("description") or "Transaction").strip()[:500]

        payee: Optional[str] = None
        if payee_source in ("auto", "merchant"):
            payee = ((raw.get("merchant") or {}).get("name") or "").strip() or None

        category = raw.get("category") or {}
        pluggy_category = (
            ((category.get("groups") or {}).get("personal_finance") or {}).get("name")
            or category.get("name")
            or None
        )

        return TransactionData(
            external_id=str(txn_id),
            description=description,
            amount=amount,
            date=txn_date,
            type=txn_type,
            # Akahu transactions don't carry a currency; the sync layer
            # resolves None to the account's currency, then the user's.
            currency=None,
            status="posted",  # settled endpoint; pending is a separate one we skip
            payee=payee,
            pluggy_category=pluggy_category,
            raw_data=raw,
        )

    # ----- credential lifecycle -----

    async def refresh_credentials(self, credentials: dict) -> dict:
        user_token, app_token = self._tokens(credentials)
        if not user_token or not app_token:
            raise SessionExpiredError("Akahu credentials missing; reconnect")
        # Personal App tokens are long-lived; nothing to rotate.
        return credentials

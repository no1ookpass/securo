"""Unit tests for the Akahu provider (free Personal App, paste-a-token flow).

Fully fakeable via ``httpx.MockTransport`` — no Akahu credentials or network
needed. Each test stands up the smallest payload required and asserts the
parse / dispatch behavior we care about.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import httpx
import pytest

from app.providers.akahu import (
    AkahuProvider,
    _map_account_type,
    _parse_tokens,
    _parse_iso_date,
)
from app.providers.base import ProviderRateLimited, SessionExpiredError

USER_TOKEN = "user_token_1111111111111111111111111"
APP_TOKEN = "app_token_2222222222222222222222222"


def _patched_client(handler):
    """Replace AkahuProvider._client with one wired to a MockTransport.

    ``_client`` is a plain (non-async) factory in the provider, so the stub
    must be too — returning the client directly rather than a coroutine.
    """

    transport = httpx.MockTransport(handler)

    def fake_client(self, user_token, app_token):  # noqa: ANN001
        # Mirror the provider's base_url + auth headers so the request that
        # reaches the transport looks exactly like a real one.
        return httpx.AsyncClient(
            base_url="https://api.akahu.io/v1",
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Akahu-Id": app_token,
            },
            transport=transport,
            timeout=30,
        )

    return patch.object(AkahuProvider, "_client", fake_client)


def _auth_ok(request: httpx.Request) -> None:
    assert request.headers["Authorization"] == f"Bearer {USER_TOKEN}"
    assert request.headers["X-Akahu-Id"] == APP_TOKEN


# ----- pure helpers -----------------------------------------------------------


def test_parse_tokens_any_order_and_whitespace():
    assert _parse_tokens(f"{USER_TOKEN} {APP_TOKEN}") == (USER_TOKEN, APP_TOKEN)
    assert _parse_tokens(f"\n{APP_TOKEN}\n{USER_TOKEN}\n") == (USER_TOKEN, APP_TOKEN)


def test_parse_tokens_missing_token_raises():
    with pytest.raises(ValueError, match="both"):
        _parse_tokens(USER_TOKEN)
    with pytest.raises(ValueError, match="both"):
        _parse_tokens("garbage")


def test_map_account_type():
    assert _map_account_type("CHECKING") == "checking"
    assert _map_account_type("SAVINGS") == "savings"
    assert _map_account_type("CREDITCARD") == "credit_card"
    assert _map_account_type("LOAN") == "checking"  # unmodeled → fallback
    assert _map_account_type(None) == "checking"


def test_parse_iso_date():
    assert _parse_iso_date("2023-01-02T00:00:00.000Z") == date(2023, 1, 2)
    assert _parse_iso_date(None) is None
    assert _parse_iso_date("nope") is None


# ----- connection flow (token paste) ------------------------------------------


@pytest.mark.asyncio
async def test_handle_oauth_callback_validates_and_builds_connection():
    """Token paste → /me + /accounts → ConnectionData with encrypted creds."""

    def handler(request: httpx.Request) -> httpx.Response:
        _auth_ok(request)
        if request.url.path == "/v1/me":
            # Akahu returns the user object under `item` (singular), not `items`.
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "item": {"_id": "user_abc123", "email": "u@example.com"},
                },
            )
        if request.url.path == "/v1/accounts":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "items": [
                        {
                            "_id": "acc_1",
                            "name": "Everyday",
                            "type": "CHECKING",
                            "status": "ACTIVE",
                            "formatted_account": "12-3456-7890123-45",
                            "balance": {
                                "current": 1234.56,
                                "available": 1200.00,
                                "currency": "NZD",
                            },
                            "connection": {
                                "name": "Demo Bank",
                                "logo": "https://cdn.akahu.nz/logo.png",
                            },
                        }
                    ],
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    provider = AkahuProvider()
    with _patched_client(handler):
        conn = await provider.handle_oauth_callback(f"{USER_TOKEN} {APP_TOKEN}")

    assert conn.external_id == "user_abc123"
    assert conn.institution_name == "Demo Bank"
    assert conn.logo_url == "https://cdn.akahu.nz/logo.png"
    assert conn.accounts[0].logo_url == "https://cdn.akahu.nz/logo.png"
    assert "user_token_enc" in conn.credentials
    assert "app_token_enc" in conn.credentials
    # Plaintext tokens must never end up in credentials.
    assert USER_TOKEN not in str(conn.credentials)
    assert APP_TOKEN not in str(conn.credentials)
    assert len(conn.accounts) == 1
    acc = conn.accounts[0]
    assert acc.external_id == "acc_1"
    assert acc.balance == Decimal("1234.56")
    assert acc.currency == "NZD"
    assert acc.type == "checking"
    assert acc.masked_number == "2345"  # last 4 of the formatted number


@pytest.mark.asyncio
async def test_handle_oauth_callback_401_surfaces_session_expired():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"success": False, "message": "Unauthorized"})

    provider = AkahuProvider()
    with _patched_client(handler):
        with pytest.raises(SessionExpiredError):
            await provider.handle_oauth_callback(f"{USER_TOKEN} {APP_TOKEN}")


# ----- account mapping --------------------------------------------------------


@pytest.mark.asyncio
async def test_get_accounts_maps_types_and_skips_inactive():
    def handler(request: httpx.Request) -> httpx.Response:
        _auth_ok(request)
        assert request.url.path == "/v1/accounts"
        return httpx.Response(
            200,
            json={
                "success": True,
                "items": [
                    {
                        "_id": "acc_checking",
                        "name": "Everyday",
                        "type": "CHECKING",
                        "status": "ACTIVE",
                        "balance": {"current": 100, "currency": "NZD"},
                    },
                    {
                        "_id": "acc_savings",
                        "name": "Savings",
                        "type": "SAVINGS",
                        "status": "ACTIVE",
                        "balance": {"current": 500, "currency": "NZD"},
                    },
                    {
                        "_id": "acc_cc",
                        "name": "Platinum Card",
                        "type": "CREDITCARD",
                        "status": "ACTIVE",
                        "balance": {
                            "current": -432.10,
                            "limit": 5000,
                            "currency": "NZD",
                        },
                    },
                    {
                        "_id": "acc_inactive",
                        "name": "Old Loan",
                        "type": "LOAN",
                        "status": "INACTIVE",
                        "balance": {"current": 50, "currency": "NZD"},
                    },
                ],
            },
        )

    creds = {
        "user_token_enc": None,
        "app_token_enc": None,
        "user_token": USER_TOKEN,
        "app_token": APP_TOKEN,
    }
    provider = AkahuProvider()
    with _patched_client(handler):
        accounts = await provider.get_accounts(creds)

    by_id = {a.external_id: a for a in accounts}
    assert set(by_id) == {"acc_checking", "acc_savings", "acc_cc"}
    assert by_id["acc_checking"].type == "checking"
    assert by_id["acc_savings"].type == "savings"
    # Akahu reports card debt negative; Securo stores positive-for-debt.
    assert by_id["acc_cc"].type == "credit_card"
    assert by_id["acc_cc"].balance == Decimal("432.10")
    assert by_id["acc_cc"].credit_limit == Decimal("5000")


@pytest.mark.asyncio
async def test_get_accounts_401_surfaces_session_expired():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"success": False, "message": "Unauthorized"})

    creds = {
        "user_token_enc": None,
        "app_token_enc": None,
        "user_token": USER_TOKEN,
        "app_token": APP_TOKEN,
    }
    provider = AkahuProvider()
    with _patched_client(handler):
        with pytest.raises(SessionExpiredError):
            await provider.get_accounts(creds)


# ----- transaction mapping ----------------------------------------------------


def _txn_payload(items, cursor_next=None):
    payload = {"success": True, "items": items}
    if cursor_next:
        payload["cursor"] = {"next": cursor_next}
    return payload


@pytest.mark.asyncio
async def test_get_transactions_maps_fields_and_paginates():
    """Direction by sign, payee from merchant, category, cursor loop."""

    pages = iter(
        [
            _txn_payload(
                [
                    {
                        "_id": "trans_1",
                        "date": "2023-01-02T00:00:00.000Z",
                        "description": "Cafe",
                        "amount": -12.5,
                        "type": "EFTPOS",
                        "merchant": {"name": "Corner Cafe"},
                        "category": {
                            "name": "Cafes & Restaurants",
                            "groups": {"personal_finance": {"name": "Lifestyle"}},
                        },
                    },
                    {
                        "_id": "trans_2",
                        "date": "2023-01-03T00:00:00.000Z",
                        "description": "Salary",
                        "amount": 2000.0,
                        "type": "DIRECT CREDIT",
                    },
                ],
                cursor_next="cursor-1",
            ),
            _txn_payload(
                [
                    {
                        "_id": "trans_3",
                        "date": "2023-01-04T00:00:00.000Z",
                        "description": "Rent",
                        "amount": -800.0,
                        "type": "PAYMENT",
                    }
                ],
                cursor_next=None,
            ),
        ]
    )
    seen_cursors = []

    def handler(request: httpx.Request) -> httpx.Response:
        _auth_ok(request)
        assert request.url.path == "/v1/accounts/acc_1/transactions"
        assert request.url.params["start"]
        assert request.url.params["end"]
        seen_cursors.append(request.url.params.get("cursor"))
        return httpx.Response(200, json=next(pages))

    creds = {
        "user_token_enc": None,
        "app_token_enc": None,
        "user_token": USER_TOKEN,
        "app_token": APP_TOKEN,
    }
    provider = AkahuProvider()
    with _patched_client(handler):
        txns = await provider.get_transactions(creds, "acc_1", since=date(2023, 1, 1))

    # First page has no cursor param, second carries the returned cursor.
    assert seen_cursors == [None, "cursor-1"]

    by_id = {t.external_id: t for t in txns}
    assert len(by_id) == 3
    debit = by_id["trans_1"]
    assert debit.type == "debit"
    assert debit.amount == Decimal("12.50")
    assert debit.date == date(2023, 1, 2)
    assert debit.payee == "Corner Cafe"
    assert debit.pluggy_category == "Lifestyle"
    assert debit.status == "posted"
    assert debit.currency is None  # resolved to account currency by sync layer
    assert by_id["trans_2"].type == "credit"
    assert by_id["trans_2"].payee is None
    assert by_id["trans_3"].type == "debit"


@pytest.mark.asyncio
async def test_get_transactions_payee_source_none_omits_merchant():
    def handler(request: httpx.Request) -> httpx.Response:
        _auth_ok(request)
        return httpx.Response(
            200,
            json=_txn_payload(
                [
                    {
                        "_id": "trans_1",
                        "date": "2023-01-02T00:00:00.000Z",
                        "description": "Cafe",
                        "amount": -12.5,
                        "type": "EFTPOS",
                        "merchant": {"name": "Corner Cafe"},
                    }
                ]
            ),
        )

    creds = {
        "user_token_enc": None,
        "app_token_enc": None,
        "user_token": USER_TOKEN,
        "app_token": APP_TOKEN,
    }
    provider = AkahuProvider()
    with _patched_client(handler):
        txns = await provider.get_transactions(creds, "acc_1", payee_source="none")
    assert txns[0].payee is None


# ----- error mapping / credential lifecycle -----------------------------------


@pytest.mark.asyncio
async def test_get_transactions_429_surfaces_rate_limited():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    creds = {
        "user_token_enc": None,
        "app_token_enc": None,
        "user_token": USER_TOKEN,
        "app_token": APP_TOKEN,
    }
    provider = AkahuProvider()
    with _patched_client(handler):
        with pytest.raises(ProviderRateLimited):
            await provider.get_transactions(creds, "acc_1")


@pytest.mark.asyncio
async def test_refresh_credentials_missing_tokens_raises():
    provider = AkahuProvider()
    with pytest.raises(SessionExpiredError):
        await provider.refresh_credentials({})


@pytest.mark.asyncio
async def test_refresh_credentials_returns_unchanged():
    provider = AkahuProvider()
    creds = {
        "user_token_enc": None,
        "app_token_enc": None,
        "user_token": USER_TOKEN,
        "app_token": APP_TOKEN,
    }
    assert await provider.refresh_credentials(creds) is creds

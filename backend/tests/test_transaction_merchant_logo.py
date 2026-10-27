"""Merchant logos: what we surface from the provider payload, and what we refuse.

Akahu attaches `meta.logo` to roughly two rows in three, all on its own CDN. We
already keep the whole payload in `raw_data`, so this is a lookup rather than a
new column or a second request - but the URL comes from outside, so it is
checked before it reaches a browser that will fetch whatever it is handed.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.transactions import (
    MERCHANT_LOGO_PLACEHOLDER,
    _attach_merchant_logo,
)
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionRead

GOOD = "https://cdn.akahu.nz/logos/merchants/merchant_cjhbfab36000001pht7vyr9kj"


def _read() -> TransactionRead:
    # model_construct: this is a unit test of a mutation helper, so the other
    # required fields are immaterial and filling them all would hide the point.
    return TransactionRead.model_construct(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        description="PAK N SAVE SILVERDALE",
        amount=Decimal("-42.10"),
        date=date(2026, 10, 1),
        source="sync",
    )


def test_a_provider_logo_is_surfaced():
    tx = _read()
    _attach_merchant_logo(tx, {"meta": {"logo": GOOD, "particulars": "PAK N SAVE"}})
    assert tx.merchant_logo == GOOD


def test_a_logo_on_another_host_is_refused():
    """The browser fetches whatever it is given, so the host is pinned."""
    tx = _read()
    _attach_merchant_logo(tx, {"meta": {"logo": "https://evil.example/x.png"}})
    assert tx.merchant_logo is None


def test_the_providers_placeholder_is_not_a_logo():
    """Drawing it would hide the category icon behind a grey blob on every
    merchant Akahu does not recognise."""
    tx = _read()
    _attach_merchant_logo(
        tx, {"meta": {"logo": f"https://cdn.akahu.nz{MERCHANT_LOGO_PLACEHOLDER}"}}
    )
    assert tx.merchant_logo is None


@pytest.mark.parametrize(
    "raw",
    [None, {}, {"meta": None}, {"meta": {}}, {"meta": {"logo": None}}, {"meta": {"logo": 42}}],
)
def test_nothing_to_show_is_not_an_error(raw):
    tx = _read()
    _attach_merchant_logo(tx, raw)
    assert tx.merchant_logo is None


@pytest.mark.asyncio
async def test_the_list_carries_the_logo_and_only_the_list(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    account = Account(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Everyday", type="checking", balance=Decimal("0"), currency="NZD",
    )
    session.add(account)
    await session.flush()
    txn = Transaction(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        account_id=account.id, description="PAK N SAVE SILVERDALE",
        original_description="PAK N SAVE SILVERDALE", amount=Decimal("-42.10"),
        currency="NZD", date=date(2026, 10, 1), effective_date=date(2026, 10, 1),
        type="debit", source="sync", status="posted", external_id="ext-logo-1",
        raw_data={"_id": "ext-logo-1", "meta": {"logo": GOOD}},
    )
    session.add(txn)
    await session.commit()

    listed = await client.get("/api/transactions", headers=auth_headers)
    assert listed.status_code == 200, listed.text
    row = next(item for item in listed.json()["items"] if item["id"] == str(txn.id))
    assert row["merchant_logo"] == GOOD

    # The single-row endpoint leaves it null, the same way it leaves
    # `transfer_counterpart` null: the list is where an icon earns its place.
    single = await client.get(f"/api/transactions/{txn.id}", headers=auth_headers)
    assert single.status_code == 200, single.text
    assert single.json()["merchant_logo"] is None

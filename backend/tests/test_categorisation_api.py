"""The suggestions route proposes, never writes, and follows the workspace.

The contract this guards is the one the whole feature rests on: a suggestion
may appear on a row, but only a human action changes the category.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category
from app.models.payee import Payee
from app.models.transaction import Transaction

BASE = datetime(2026, 2, 1, tzinfo=timezone.utc)


async def _account(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Account:
    account = Account(
        id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
        name="Everyday", type="checking", balance=Decimal("0"), currency="NZD",
    )
    session.add(account)
    await session.flush()
    return account


async def _category(session: AsyncSession, workspace_id, user_id, name: str) -> Category:
    category = Category(
        id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
        name=name, icon="tag", color="#000", is_system=False,
    )
    session.add(category)
    await session.flush()
    return category


async def _transaction(
    session: AsyncSession,
    *,
    account: Account,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    payee: Payee,
    description: str,
    category: Category | None,
    when: datetime,
) -> Transaction:
    txn = Transaction(
        id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
        account_id=account.id, category_id=category.id if category else None,
        description=description, original_description=description,
        amount=Decimal("12.50"), currency="NZD", date=when.date(),
        effective_date=when.date(), type="debit", source="sync", status="posted",
        payee=payee.name, payee_id=payee.id, created_at=when,
    )
    session.add(txn)
    await session.flush()
    return txn


@pytest.mark.asyncio
async def test_suggestions_propose_a_category_and_never_write_one(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    account = await _account(session, test_workspace.id, test_user.id)
    groceries = await _category(session, test_workspace.id, test_user.id, "Groceries")
    woolworths = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Woolworths", source="sync",
    )
    session.add(woolworths)
    await session.flush()

    # Three prior decisions teach the merchant.
    for i in range(3):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=woolworths,
            description=f"WOOLWORTHS NZ/STORE {i}", category=groceries,
            when=BASE + timedelta(days=i),
        )
    pending = await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=woolworths,
        description="Woolworths Online Favona", category=None,
        when=BASE + timedelta(days=10),
    )
    await session.commit()

    response = await client.get(
        "/api/categorisation/suggestions",
        params={"transaction_ids": str(pending.id)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["transaction_id"] == str(pending.id)
    assert body[0]["category_id"] == str(groceries.id)
    assert body[0]["category_name"] == "Groceries"
    assert body[0]["source"] == "payee"
    assert body[0]["evidence"] == 3
    assert body[0]["confidence"] == 1.0

    # The route is read-only: the row is still uncategorised.
    await session.refresh(pending)
    assert pending.category_id is None


@pytest.mark.asyncio
async def test_suggestions_are_silent_when_the_evidence_is_thin(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    account = await _account(session, test_workspace.id, test_user.id)
    fuel = await _category(session, test_workspace.id, test_user.id, "Transport")
    gul = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Gull", source="sync",
    )
    session.add(gul)
    await session.flush()

    # One example is an anecdote, not a pattern.
    await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=gul,
        description="GULL PUKEKOHE", category=fuel, when=BASE,
    )
    pending = await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=gul,
        description="GULL PUKEKOHE", category=None, when=BASE + timedelta(days=3),
    )
    await session.commit()

    response = await client.get(
        "/api/categorisation/suggestions",
        params={"transaction_ids": str(pending.id)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_suggestions_ignore_rows_that_have_a_category(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    account = await _account(session, test_workspace.id, test_user.id)
    groceries = await _category(session, test_workspace.id, test_user.id, "Groceries")
    woolworths = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Woolworths", source="sync",
    )
    session.add(woolworths)
    await session.flush()

    for i in range(3):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=woolworths,
            description=f"WOOLWORTHS NZ/STORE {i}", category=groceries,
            when=BASE + timedelta(days=i),
        )
    already = await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=woolworths,
        description="WOOLWORTHS NZ/STORE 9", category=groceries,
        when=BASE + timedelta(days=5),
    )
    await session.commit()

    response = await client.get(
        "/api/categorisation/suggestions",
        params={"transaction_ids": str(already.id)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_suggestions_do_not_leak_across_workspaces(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """A merchant learned in another workspace must not appear here."""
    other_workspace_id = uuid.uuid4()
    from app.models.workspace import Workspace

    session.add(
        Workspace(
            id=other_workspace_id, name="Other", default_currency="NZD",
            created_by_user_id=test_user.id,
        )
    )
    await session.flush()

    other_account = await _account(session, other_workspace_id, test_user.id)
    other_groceries = await _category(
        session, other_workspace_id, test_user.id, "Groceries"
    )
    other_payee = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=other_workspace_id,
        name="Woolworths", source="sync",
    )
    session.add(other_payee)
    await session.flush()
    for i in range(3):
        await _transaction(
            session, account=other_account, user_id=test_user.id,
            workspace_id=other_workspace_id, payee=other_payee,
            description="WOOLWORTHS NZ/STORE", category=other_groceries,
            when=BASE + timedelta(days=i),
        )

    # Same merchant name, same user, but in the workspace under test and with
    # no history of its own.
    account = await _account(session, test_workspace.id, test_user.id)
    mine = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Woolworths", source="sync",
    )
    session.add(mine)
    await session.flush()
    pending = await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=mine,
        description="WOOLWORTHS NZ/STORE", category=None,
        when=BASE + timedelta(days=10),
    )
    await session.commit()

    response = await client.get(
        "/api/categorisation/suggestions",
        params={"transaction_ids": str(pending.id)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_without_ids_it_grades_the_newest_uncategorised_rows(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    account = await _account(session, test_workspace.id, test_user.id)
    groceries = await _category(session, test_workspace.id, test_user.id, "Groceries")
    woolworths = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Woolworths", source="sync",
    )
    session.add(woolworths)
    await session.flush()
    for i in range(3):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=woolworths,
            description=f"WOOLWORTHS NZ/STORE {i}", category=groceries,
            when=BASE + timedelta(days=i),
        )
    for i in range(2):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=woolworths,
            description="Woolworths Online Favona", category=None,
            when=BASE + timedelta(days=10 + i),
        )
    await session.commit()

    response = await client.get(
        "/api/categorisation/suggestions", params={"limit": 10}, headers=auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {row["category_name"] for row in response.json()} == {"Groceries"}

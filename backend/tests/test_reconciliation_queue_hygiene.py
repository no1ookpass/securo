"""The queue may only offer questions somebody can actually answer.

A transfer question names two rows. Either can vanish under it - a re-sync that
re-keys, the phantom-duplicate cleanup removing a twin, or a person deleting the
row - and the pair can be linked by something other than this queue. Every such
question used to stay pending for the full sixty-day staleness window, and each
one failed on click with "One of the transactions is no longer there".
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.reconciliation import ReconciliationSuggestion
from app.models.transaction import Transaction


async def _account(session, workspace_id, user_id, name: str) -> Account:
    account = Account(
        id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
        name=name, type="checking", balance=Decimal("0"), currency="NZD",
    )
    session.add(account)
    await session.flush()
    return account


async def _transaction(session, *, account, user_id, workspace_id, description, amount):
    txn = Transaction(
        id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
        account_id=account.id, description=description, original_description=description,
        amount=amount, currency="NZD", date=date(2026, 7, 12),
        effective_date=date(2026, 7, 12), type="debit", source="sync", status="posted",
        created_at=datetime.now(timezone.utc),
    )
    session.add(txn)
    await session.flush()
    return txn


async def _question(session, workspace_id, moved_id, other_id) -> ReconciliationSuggestion:
    row = ReconciliationSuggestion(
        id=uuid.uuid4(), workspace_id=workspace_id,
        transaction_id=moved_id, expectation_kind="transaction", expectation_id=other_id,
        strategy_id="exact_amount_nearby", node="transfers",
        amount=Decimal("300.00"), scores={"amount_exact": True}, status="pending",
        created_at=datetime.now(timezone.utc),
    )
    session.add(row)
    await session.flush()
    return row


async def _status(session, row) -> str:
    await session.refresh(row)
    return row.status


@pytest.mark.asyncio
async def test_a_question_whose_other_half_was_deleted_is_retired(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """The exact failure seen live: the second row is gone, so the pairing can
    never be made, and the button must stop being offered."""
    left = await _account(session, test_workspace.id, test_user.id, "Streamline")
    right = await _account(session, test_workspace.id, test_user.id, "Business Saver")
    moved = await _transaction(
        session, account=left, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MB TRANSFER EX 12-3072-0881656-50", amount=Decimal("-300.00"),
    )
    await _transaction(
        session, account=right, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MB TRANSFER TO 12-3072-0392414-56", amount=Decimal("300.00"),
    )
    question = await _question(
        session, test_workspace.id, moved.id, uuid.uuid4()  # the other half never exists
    )
    await session.commit()

    response = await client.get("/api/reconciliation/suggestions", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == []
    assert await _status(session, question) == "expired"


@pytest.mark.asyncio
async def test_a_question_whose_moved_row_was_deleted_is_retired(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    right = await _account(session, test_workspace.id, test_user.id, "Business Saver")
    other = await _transaction(
        session, account=right, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MB TRANSFER TO 12-3072-0392414-56", amount=Decimal("300.00"),
    )
    question = await _question(session, test_workspace.id, uuid.uuid4(), other.id)
    await session.commit()

    response = await client.get("/api/reconciliation/suggestions", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == []
    assert await _status(session, question) == "expired"


@pytest.mark.asyncio
async def test_a_question_about_an_already_linked_pair_is_retired(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """Something else linked them first - a sync's pair detection, or the person
    by hand. Accepting can only fail from here ("already part of a transfer"),
    so the question is spent."""
    left = await _account(session, test_workspace.id, test_user.id, "Streamline")
    right = await _account(session, test_workspace.id, test_user.id, "Business Saver")
    moved = await _transaction(
        session, account=left, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MB TRANSFER EX 12-3072-0881656-50", amount=Decimal("-300.00"),
    )
    other = await _transaction(
        session, account=right, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MB TRANSFER TO 12-3072-0392414-56", amount=Decimal("300.00"),
    )
    pair_id = uuid.uuid4()
    moved.transfer_pair_id = pair_id
    other.transfer_pair_id = pair_id
    question = await _question(session, test_workspace.id, moved.id, other.id)
    await session.commit()

    response = await client.get("/api/reconciliation/suggestions", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == []
    assert await _status(session, question) == "expired"


@pytest.mark.asyncio
async def test_a_question_that_can_still_be_answered_is_left_alone(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """The guard has to be exact: retiring a live question would silently
    discard a real decision."""
    left = await _account(session, test_workspace.id, test_user.id, "Streamline")
    right = await _account(session, test_workspace.id, test_user.id, "Business Saver")
    moved = await _transaction(
        session, account=left, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MB TRANSFER EX 12-3072-0881656-50", amount=Decimal("-300.00"),
    )
    other = await _transaction(
        session, account=right, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MB TRANSFER TO 12-3072-0392414-56", amount=Decimal("300.00"),
    )
    question = await _question(session, test_workspace.id, moved.id, other.id)
    await session.commit()

    response = await client.get("/api/reconciliation/suggestions", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == [str(question.id)]
    assert await _status(session, question) == "pending"


@pytest.mark.asyncio
async def test_age_still_expires_what_nobody_answered(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """The original behaviour, kept: the new checks must not replace it."""
    left = await _account(session, test_workspace.id, test_user.id, "Streamline")
    right = await _account(session, test_workspace.id, test_user.id, "Business Saver")
    moved = await _transaction(
        session, account=left, user_id=test_user.id, workspace_id=test_workspace.id,
        description="OLD TRANSFER", amount=Decimal("-300.00"),
    )
    other = await _transaction(
        session, account=right, user_id=test_user.id, workspace_id=test_workspace.id,
        description="OLD TRANSFER IN", amount=Decimal("300.00"),
    )
    question = await _question(session, test_workspace.id, moved.id, other.id)
    question.created_at = datetime.now(timezone.utc) - timedelta(days=61)
    await session.commit()

    await client.get("/api/reconciliation/suggestions", headers=auth_headers)

    assert await _status(session, question) == "expired"


@pytest.mark.asyncio
async def test_one_workspace_cannot_retire_anothers_questions(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """The sweep is workspace-scoped, so it must not touch foreign rows even
    though the ids it inspects come from those rows."""
    mine_left = await _account(session, test_workspace.id, test_user.id, "Streamline")
    mine_right = await _account(session, test_workspace.id, test_user.id, "Business Saver")
    moved = await _transaction(
        session, account=mine_left, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MINE", amount=Decimal("-300.00"),
    )
    other = await _transaction(
        session, account=mine_right, user_id=test_user.id, workspace_id=test_workspace.id,
        description="MINE IN", amount=Decimal("300.00"),
    )
    await _question(session, test_workspace.id, moved.id, other.id)
    await session.commit()

    foreign = (
        await session.execute(
            select(ReconciliationSuggestion).where(
                ReconciliationSuggestion.workspace_id != test_workspace.id
            ).limit(1)
        )
    ).scalars().all()

    await client.get("/api/reconciliation/suggestions", headers=auth_headers)

    for row in foreign:
        await session.refresh(row)
        assert row.status == "pending"

"""The suggestions route proposes, never writes, and follows the workspace.

The contract this guards is the one the whole feature rests on: a suggestion
may appear on a row, but only a human action changes the category.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
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


@pytest.mark.asyncio
async def test_a_merchant_with_two_legitimate_uses_suggests_its_majority(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """Bunnings is mostly Homeware, occasionally a child's own purchase.

    The old 80% purity floor abstained forever at 2-of-3. A clear majority with
    the split shown is the better answer: it is a suggestion, and the count
    tells you how thin it is.
    """
    account = await _account(session, test_workspace.id, test_user.id)
    homeware = await _category(session, test_workspace.id, test_user.id, "Homeware")
    splash = await _category(session, test_workspace.id, test_user.id, "Hayden Splash")
    bunnings = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Bunnings Warehouse", source="sync",
    )
    session.add(bunnings)
    await session.flush()

    for i, category in enumerate((homeware, homeware, splash)):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=bunnings,
            description=f"BUNNINGS WAREHOUSE STORE {i}", category=category,
            when=BASE + timedelta(days=i),
        )
    pending = await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=bunnings,
        description="BUNNINGS WAREHOUSE ALBANY", category=None,
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
    assert body[0]["category_name"] == "Homeware"
    assert body[0]["agreed"] == 2
    assert body[0]["evidence"] == 3
    assert round(body[0]["confidence"], 2) == 0.67


@pytest.mark.asyncio
async def test_a_tie_still_abstains(session: AsyncSession, client: AsyncClient, auth_headers: dict,
                                   test_user, test_workspace):
    """Two uses in equal measure is not a habit; say nothing."""
    account = await _account(session, test_workspace.id, test_user.id)
    homeware = await _category(session, test_workspace.id, test_user.id, "Homeware")
    splash = await _category(session, test_workspace.id, test_user.id, "Hayden Splash")
    payee = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Bunnings Warehouse", source="sync",
    )
    session.add(payee)
    await session.flush()

    for i, category in enumerate((homeware, splash)):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=payee,
            description=f"BUNNINGS WAREHOUSE STORE {i}", category=category,
            when=BASE + timedelta(days=i),
        )
    pending = await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=payee,
        description="BUNNINGS WAREHOUSE ALBANY", category=None,
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
async def test_the_list_filter_shows_only_rows_the_history_can_file(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """The "has suggestion" filter must describe the list, not the page.

    It exists so the backlog can be worked through in the ordinary table, which
    only works if the filter is resolved against everything - a filter that
    looked at one page would report "nothing left" the moment that page ran dry.
    """
    account = await _account(session, test_workspace.id, test_user.id)
    groceries = await _category(session, test_workspace.id, test_user.id, "Groceries")
    fuel = await _category(session, test_workspace.id, test_user.id, "Transport")
    woolworths = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Woolworths", source="sync",
    )
    gull = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Gull", source="sync",
    )
    stranger = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Somewhere New", source="sync",
    )
    session.add_all([woolworths, gull, stranger])
    await session.flush()

    for i in range(4):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=woolworths,
            description=f"WOOLWORTHS NZ/STORE {i}", category=groceries,
            when=BASE + timedelta(days=i),
        )
    for i in range(2):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=gull,
            description=f"GULL STATION {i}", category=fuel,
            when=BASE + timedelta(days=i),
        )
    recent = await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=gull,
        description="GULL PUKEKOHE", category=None, when=BASE + timedelta(days=20),
    )
    older = await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=woolworths,
        description="Woolworths Online Favona", category=None,
        when=BASE + timedelta(days=21),
    )
    # No history behind this one, so the memory has nothing to say about it.
    await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=stranger,
        description="SOMETHING UNSEEN 4471", category=None,
        when=BASE + timedelta(days=22),
    )
    await session.commit()

    response = await client.get(
        "/api/transactions", params={"has_suggestion": "true"}, headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert {item["id"] for item in body["items"]} == {str(recent.id), str(older.id)}
    assert body["total"] == 2

    # Both are reachable through pagination, which is the point of resolving the
    # filter up front instead of trimming whatever arrived on the page.
    first = await client.get(
        "/api/transactions",
        params={"has_suggestion": "true", "limit": 1, "page": 1},
        headers=auth_headers,
    )
    second = await client.get(
        "/api/transactions",
        params={"has_suggestion": "true", "limit": 1, "page": 2},
        headers=auth_headers,
    )
    assert first.json()["total"] == 2
    assert second.json()["total"] == 2
    assert len(first.json()["items"]) == 1
    assert first.json()["items"][0]["id"] != second.json()["items"][0]["id"]


async def test_the_list_filter_is_empty_when_nothing_can_be_filed(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    account = await _account(session, test_workspace.id, test_user.id)
    stranger = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Somewhere New", source="sync",
    )
    session.add(stranger)
    await session.flush()
    await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=stranger,
        description="SOMETHING UNSEEN 4471", category=None, when=BASE,
    )
    await session.commit()

    response = await client.get(
        "/api/transactions", params={"has_suggestion": "true"}, headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {
        "items": [], "total": 0, "page": 1, "limit": 50, "summary": None,
    }

    # The export has the same filter, and with nothing to file it must produce
    # an empty file rather than quietly handing back every transaction under the
    # name of a filtered export.
    export = await client.get(
        "/api/transactions/export",
        params={"has_suggestion": "true"},
        headers=auth_headers,
    )
    assert export.status_code == 200
    rows = [line for line in export.text.strip().splitlines() if line]
    assert len(rows) == 1  # the header row only
    assert "SOMETHING UNSEEN" not in export.text


async def test_the_csv_export_honours_the_suggestion_filter(
    session: AsyncSession, client: AsyncClient, auth_headers: dict,
    test_user, test_workspace,
):
    """A filtered table must not export more rows than it is showing."""
    account = await _account(session, test_workspace.id, test_user.id)
    groceries = await _category(session, test_workspace.id, test_user.id, "Groceries")
    woolworths = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Woolworths", source="sync",
    )
    stranger = Payee(
        id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
        name="Somewhere New", source="sync",
    )
    session.add_all([woolworths, stranger])
    await session.flush()

    for i in range(2):
        await _transaction(
            session, account=account, user_id=test_user.id,
            workspace_id=test_workspace.id, payee=woolworths,
            description=f"WOOLWORTHS NZ/STORE {i}", category=groceries,
            when=BASE + timedelta(days=i),
        )
    await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=woolworths,
        description="WOOLWORTHS NZ/BULK", category=None, when=BASE + timedelta(days=5),
    )
    await _transaction(
        session, account=account, user_id=test_user.id,
        workspace_id=test_workspace.id, payee=stranger,
        description="SOMETHING UNSEEN 4471", category=None, when=BASE + timedelta(days=6),
    )
    await session.commit()

    export = await client.get(
        "/api/transactions/export",
        params={"has_suggestion": "true"},
        headers=auth_headers,
    )
    assert export.status_code == 200
    rows = [line for line in export.text.strip().splitlines() if line]
    assert len(rows) == 2  # header + the one suggested row
    assert "WOOLWORTHS NZ/BULK" in export.text
    assert "SOMETHING UNSEEN" not in export.text

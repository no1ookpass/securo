"""The memory learns from history and from every decision made afterwards."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category
from app.models.payee import Payee
from app.models.transaction import Transaction
from app.services.categorisation_memory import (
    CategoryMemory,
    MIN_EVIDENCE,
    backtest,
    load_memory,
    normalise_tokens,
)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# normalisation
# ---------------------------------------------------------------------------


def test_normalise_strips_settlement_noise_and_numbers():
    assert normalise_tokens("UBER * EATS PENDING Christchurch") == {"uber", "eats", "christchurch"}
    assert normalise_tokens("WOOLWORTHS NZ/4-6 MOENUI OREWA") == {"woolworths", "moenui", "orewa"}
    assert normalise_tokens("Woolworths Onli/80 Favona Auckland") == {
        "woolworths", "onli", "favona", "auckland"
    }
    assert normalise_tokens(None) == frozenset()


def test_normalise_drops_the_tokens_that_misled_the_backtest():
    # "TFR TO ..." is a transfer, not a merchant; it suggested Education for rent.
    assert normalise_tokens("TFR TO Barfoot (Syme Rent") == {"barfoot", "syme", "rent"}
    # "online" suggested Groceries for a DIY store.
    assert normalise_tokens("BUNNINGS WAREHOUSE ONLINE ALBANY") == {
        "bunnings", "warehouse", "albany"
    }
    # A reference code voted from unrelated payments.
    assert normalise_tokens("FC02-0316-0494166-00 Movers") == {"movers"}
    # A brand that happens to start with a digit is still a brand.
    assert normalise_tokens("2DEGREES MOBILE") == {"2degrees", "mobile"}


def test_normalise_keeps_the_brand_even_when_everything_else_varies():
    variants = [
        "Woolworths Online Favona",
        "WOOLWORTHS NZ/SILVERDALE SILVERDALE",
        "WOOLWORTHS NZ/4-6 MOENUI OREWA",
        "Woolworths Onli/80 Favona Auckland",
    ]
    shared = set.intersection(*(set(normalise_tokens(v)) for v in variants))
    assert shared == {"woolworths"}


# ---------------------------------------------------------------------------
# the memory itself
# ---------------------------------------------------------------------------


def test_nothing_is_suggested_before_there_is_evidence():
    memory = CategoryMemory()
    groceries, coffee = uuid.uuid4(), uuid.uuid4()

    for _ in range(MIN_EVIDENCE - 1):
        memory.add(groceries, payee_id=uuid.UUID(int=1), description="WOOLWORTHS NZ/X")

    assert memory.suggest(payee_id=uuid.UUID(int=1), description="WOOLWORTHS NZ/X") is None

    memory.add(groceries, payee_id=uuid.UUID(int=1), description="WOOLWORTHS NZ/X")
    suggestion = memory.suggest(payee_id=uuid.UUID(int=1), description="WOOLWORTHS NZ/X")
    assert suggestion is not None
    assert suggestion.category_id == groceries
    assert suggestion.evidence == MIN_EVIDENCE
    assert suggestion.source == "payee"
    # A different merchant inherits nothing from Woolworths' history.
    assert memory.suggest(payee_id=uuid.UUID(int=2), description="Z ENERGY ALBANY") is None
    assert coffee  # keep the second id referenced


def test_a_split_vote_abstains_instead_of_guessing():
    memory = CategoryMemory()
    groceries, household = uuid.uuid4(), uuid.uuid4()
    payee = uuid.UUID(int=3)

    for _ in range(4):
        memory.add(groceries, payee_id=payee, description="WOOLWORTHS")
    for _ in range(4):
        memory.add(household, payee_id=payee, description="WOOLWORTHS")

    # 50/50: no suggestion at all, rather than the coin toss that comes first.
    assert memory.suggest(payee_id=payee, description="WOOLWORTHS") is None


def test_description_tokens_carry_the_learning_when_there_is_no_payee():
    """Imports and pending rows arrive without a merchant entity."""
    memory = CategoryMemory()
    groceries = uuid.uuid4()

    for description in (
        "WOOLWORTHS NZ/SILVERDALE SILVERDALE",
        "WOOLWORTHS NZ/4-6 MOENUI OREWA",
        "Woolworths Onli/80 Favona Auckland",
    ):
        memory.add(groceries, description=description)

    # A descriptor shape never seen before, and still no payee.
    suggestion = memory.suggest(description="Woolworths Online Favona")
    assert suggestion is not None
    assert suggestion.category_id == groceries
    assert suggestion.source == "description"
    assert suggestion.matched == "woolworths"
    assert suggestion.evidence == 3


def test_an_entity_with_history_beats_a_shared_token():
    """Uber Eats and Uber share tokens but are different payees."""
    memory = CategoryMemory()
    uber_eats, transport = uuid.uuid4(), uuid.uuid4()
    eats_payee, ride_payee = uuid.UUID(int=10), uuid.UUID(int=11)

    for _ in range(5):
        memory.add(uber_eats, payee_id=eats_payee, description="UBER *EATS HELP.UBER.COM")
    for _ in range(5):
        memory.add(transport, payee_id=ride_payee, description="UBER *TRIP HELP.UBER.COM")

    assert memory.suggest(payee_id=eats_payee, description="UBER *EATS X").category_id == uber_eats
    assert memory.suggest(payee_id=ride_payee, description="UBER *TRIP X").category_id == transport

    # With no payee the token "uber" is genuinely ambiguous, so it must abstain.
    assert memory.suggest(description="UBER *PENDING SOMEWHERE") is None


def test_a_token_shared_by_two_merchants_is_not_evidence():
    """`warehouse` belongs to both The Warehouse and Bunnings Warehouse.

    Before this gate the memory suggested Groceries for a DIY store, because
    The Warehouse's history is mostly groceries and the two descriptors share
    that one word.
    """
    memory = CategoryMemory()
    groceries, homeware = uuid.uuid4(), uuid.uuid4()
    the_warehouse, bunnings = uuid.UUID(int=30), uuid.UUID(int=31)

    for _ in range(4):
        memory.add(groceries, payee_id=the_warehouse, description="THE WAREHOUSE TAKAPUNA")
    memory.add(homeware, payee_id=bunnings, description="BUNNINGS WAREHOUSE ALBANY")

    # The shared token cannot speak for either merchant, and `bunnings` alone
    # has a single example, so both descriptors stay ungraded.
    assert memory.suggest(description="BUNNINGS WAREHOUSE OREWA") is None
    assert memory.suggest(description="THE WAREHOUSE WHANGAREI") is None


def test_a_token_seen_under_another_merchant_in_any_row_is_not_evidence():
    """`beach` belongs to a suburb, not to the supermarket that names it.

    It appeared under one payee among *categorised* rows, so the gate treated it
    as distinctive and suggested Groceries for a Mobil charge at the same beach.
    Descriptors that were never categorised still prove a word is not exclusive
    to one merchant.
    """
    memory = CategoryMemory()
    groceries = uuid.uuid4()
    four_square, mobil = uuid.UUID(int=40), uuid.UUID(int=41)

    for _ in range(3):
        memory.add(
            groceries, payee_id=four_square,
            description="FOUR SQUARE RED BEACH RED BEACH",
        )
    # Seen, never categorised: no category evidence, but a second merchant.
    memory.observe(payee_id=mobil, description="MOBIL RED BEACH RED BEACH")

    assert memory.suggest(description="MOBIL RED BEACH RED BEACH") is None
    # The merchant that is genuinely unique still resolves.
    assert memory.suggest(description="FOUR SQUARE RED BEACH").category_id == groceries


def test_a_token_seen_under_one_merchant_still_works():
    memory = CategoryMemory()
    groceries = uuid.uuid4()
    for _ in range(3):
        memory.add(
            groceries, payee_id=uuid.UUID(int=30), description="THE WAREHOUSE TAKAPUNA"
        )

    suggestion = memory.suggest(description="THE WAREHOUSE WHANGAREI")
    assert suggestion is not None
    assert suggestion.category_id == groceries
    assert suggestion.matched == "warehouse"


def test_a_new_decision_is_immediately_part_of_the_memory():
    """The property the whole design rests on: no retraining step."""
    memory = CategoryMemory()
    groceries = uuid.uuid4()
    payee = uuid.UUID(int=20)
    row = {"payee_id": payee, "description": "FOUR SQUARE KAIKOHE"}

    assert memory.suggest(**row) is None
    for _ in range(MIN_EVIDENCE - 1):
        memory.add(groceries, **row)
    assert memory.suggest(**row) is None

    # The user categorises once more; the next lookup already knows.
    memory.add(groceries, **row)
    suggestion = memory.suggest(**row)
    assert suggestion is not None and suggestion.category_id == groceries


# ---------------------------------------------------------------------------
# loading from history, and the backtest
# ---------------------------------------------------------------------------


async def _seed(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    payee_name: str,
    description: str,
    category: Category,
    when: datetime,
) -> Transaction:
    payee = await session.scalar(select(Payee).where(Payee.name == payee_name))
    if payee is None:
        payee = Payee(
            id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
            name=payee_name, source="sync",
        )
        session.add(payee)
        await session.flush()

    account = await session.scalar(
        select(Account).where(Account.workspace_id == workspace_id)
    )
    if account is None:
        account = Account(
            id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
            name="Everyday", type="checking", balance=Decimal("0"), currency="NZD",
        )
        session.add(account)
        await session.flush()

    txn = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        account_id=account.id,
        category_id=category.id,
        description=description,
        original_description=description,
        amount=Decimal("25.00"),
        currency="NZD",
        date=when.date(),
        effective_date=when.date(),
        type="debit",
        source="sync",
        status="posted",
        payee=payee_name,
        payee_id=payee.id,
        created_at=when,
    )
    session.add(txn)
    await session.flush()
    return txn


async def _category(session, workspace_id, user_id, name) -> Category:
    existing = await session.scalar(
        select(Category).where(
            Category.workspace_id == workspace_id, Category.name == name
        )
    )
    if existing is not None:
        return existing
    row = Category(
        id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
        name=name, icon="tag", color="#000", is_system=False,
    )
    session.add(row)
    await session.flush()
    return row


@pytest.mark.asyncio
async def test_load_memory_uses_history_and_ignores_opening_balances(
    session: AsyncSession, test_user, test_workspace,
):
    groceries = await _category(session, test_workspace.id, test_user.id, "Groceries")
    for i in range(3):
        await _seed(
            session, test_workspace.id, test_user.id,
            payee_name="Woolworths", description=f"WOOLWORTHS NZ/STORE {i}",
            category=groceries, when=BASE + timedelta(days=i),
        )
    await session.commit()

    memory = await load_memory(session, test_workspace.id)
    suggestion = memory.suggest(
        payee_id=None, description="WOOLWORTHS NZ/SILVERDALE SILVERDALE"
    )
    assert suggestion is not None
    assert suggestion.category_id == groceries.id

    # An opening-balance row is synthetic, so it must not teach the memory.
    opening = await _seed(
        session, test_workspace.id, test_user.id,
        payee_name="Opening", description="Opening balance",
        category=groceries, when=BASE + timedelta(days=10),
    )
    opening.source = "opening_balance"
    await session.commit()

    memory = await load_memory(session, test_workspace.id)
    assert memory.suggest(description="Opening balance") is None


@pytest.mark.asyncio
async def test_backtest_grades_each_row_against_earlier_decisions_only(
    session: AsyncSession, test_user, test_workspace,
):
    groceries = await _category(session, test_workspace.id, test_user.id, "Groceries")
    fuel = await _category(session, test_workspace.id, test_user.id, "Fuel")

    # Five Woolworths decisions, then a garage, then an unseen Woolworths store.
    for i in range(5):
        await _seed(
            session, test_workspace.id, test_user.id,
            payee_name="Woolworths", description=f"WOOLWORTHS NZ/STORE {i}",
            category=groceries, when=BASE + timedelta(days=i),
        )
    await _seed(
        session, test_workspace.id, test_user.id,
        payee_name="Z Energy", description="Z ENERGY ALBANY",
        category=fuel, when=BASE + timedelta(days=6),
    )
    await _seed(
        session, test_workspace.id, test_user.id,
        payee_name="Woolworths", description="Woolworths Online Favona",
        category=groceries, when=BASE + timedelta(days=7),
    )
    await session.commit()

    results = await backtest(session, test_workspace.id)
    strict = next(r for r in results if (r.min_evidence, r.min_share) == (3, 0.8))

    # Rows 1-3 have too little history to be graded; later ones are.
    assert strict.graded == 7
    assert strict.suggested >= 1
    assert strict.correct == strict.suggested
    assert strict.precision == 1.0


@pytest.mark.asyncio
async def test_load_memory_reads_token_ambiguity_from_uncategorised_rows(
    session: AsyncSession, test_user, test_workspace,
):
    """The Mobil-at-the-same-beach case, end to end through the loader."""
    groceries = await _category(session, test_workspace.id, test_user.id, "Groceries")
    for i in range(3):
        await _seed(
            session, test_workspace.id, test_user.id,
            payee_name="Four Square",
            description="FOUR SQUARE RED BEACH RED BEACH",
            category=groceries, when=BASE + timedelta(days=i),
        )
    # A fuel station at the same beach, never categorised.
    mobil = await _seed(
        session, test_workspace.id, test_user.id,
        payee_name="Mobil",
        description="MOBIL RED BEACH RED BEACH",
        category=groceries, when=BASE + timedelta(days=5),
    )
    mobil.category_id = None
    await session.commit()

    memory = await load_memory(session, test_workspace.id)
    assert memory.suggest(description="MOBIL RED BEACH RED BEACH") is None

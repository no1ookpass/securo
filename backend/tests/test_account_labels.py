"""Account labels: "Institution - Account", and never over a name a person typed.

The sync used to label an account with just its institution, so four Kiwibank
accounts all read "Kiwibank" - indistinguishable in every account picker. The
label is now built from both halves, and the fix reaches existing rows without a
re-sync because it only rewrites labels the sync itself owns.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.bank_connection import BankConnection
from app.models.institution import Institution
from app.models.workspace import Workspace
from app.services.connection_service import (
    _default_account_label,
    relabel_auto_account_names,
)


def test_the_label_names_both_halves():
    assert _default_account_label("Kiwibank", "waste not") == "Kiwibank - waste not"
    assert _default_account_label("ASB", "Streamline") == "ASB - Streamline"


def test_a_missing_half_does_not_produce_a_dangling_dash():
    assert _default_account_label("Kiwibank", "") == "Kiwibank"
    assert _default_account_label("Kiwibank", None) == "Kiwibank"
    assert _default_account_label(None, "waste not") is None
    assert _default_account_label("  ", "waste not") is None


def test_an_account_named_after_its_bank_is_not_doubled():
    """Some banks return the institution as the account name; "ASB - ASB" is
    noise, and the plain institution says everything it can."""
    assert _default_account_label("ASB", "ASB") == "ASB"
    assert _default_account_label("ASB", "asb") == "ASB"


async def _connection_with_institution(session, workspace_id, user_id, bank: str):
    connection = BankConnection(
        id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
        provider="akahu", external_id=f"conn-{uuid.uuid4()}",
        institution_name=bank, status="active",
    )
    session.add(connection)
    await session.flush()
    institution = Institution(
        id=uuid.uuid4(), connection_id=connection.id, name=bank,
    )
    session.add(institution)
    await session.flush()
    return connection, institution


def _account(workspace_id, user_id, connection_id, institution_id, name, display_name):
    return Account(
        id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id,
        connection_id=connection_id, institution_id=institution_id,
        external_id=f"acc-{uuid.uuid4()}", name=name, display_name=display_name,
        type="checking", balance=Decimal("0"), currency="NZD",
    )


@pytest.mark.asyncio
async def test_existing_bare_institution_labels_are_upgraded(
    session: AsyncSession, test_user, test_workspace,
):
    """The live shape: four accounts whose label is still just the bank."""
    connection, institution = await _connection_with_institution(
        session, test_workspace.id, test_user.id, "Kiwibank"
    )
    accounts = [
        _account(test_workspace.id, test_user.id, connection.id, institution.id, n, "Kiwibank")
        for n in ("waste not", "SAMBAMAJAM", ".", "Zero Visa")
    ]
    session.add_all(accounts)
    await session.commit()

    updated = await relabel_auto_account_names(session, test_workspace.id)
    await session.commit()

    assert updated == 4
    labels = sorted(a.display_name for a in accounts)
    assert labels == sorted(
        f"Kiwibank - {n}" for n in ("waste not", "SAMBAMAJAM", ".", "Zero Visa")
    )


@pytest.mark.asyncio
async def test_a_name_somebody_typed_is_left_alone(
    session: AsyncSession, test_user, test_workspace,
):
    """Five accounts in the live workspace were renamed by hand to tell them
    apart. Rewriting those would be the fix doing the same damage it repairs."""
    connection, institution = await _connection_with_institution(
        session, test_workspace.id, test_user.id, "ASB"
    )
    typed = _account(
        test_workspace.id, test_user.id, connection.id, institution.id,
        "Streamline", "ASB [Streamline]",
    )
    untouched = _account(
        test_workspace.id, test_user.id, connection.id, institution.id,
        "Visa Lite", "My own name",
    )
    session.add_all([typed, untouched])
    await session.commit()

    updated = await relabel_auto_account_names(session, test_workspace.id)
    await session.commit()

    assert updated == 0
    assert typed.display_name == "ASB [Streamline]"
    assert untouched.display_name == "My own name"


@pytest.mark.asyncio
async def test_an_empty_label_is_filled_and_the_run_is_idempotent(
    session: AsyncSession, test_user, test_workspace,
):
    connection, institution = await _connection_with_institution(
        session, test_workspace.id, test_user.id, "Hatch"
    )
    blank = _account(
        test_workspace.id, test_user.id, connection.id, institution.id,
        "Hayden's individual account", None,
    )
    session.add(blank)
    await session.commit()

    assert await relabel_auto_account_names(session, test_workspace.id) == 1
    assert blank.display_name == "Hatch - Hayden's individual account"
    await session.commit()

    # Second pass: nothing left to do, so a rerun after a failed deploy is free.
    assert await relabel_auto_account_names(session, test_workspace.id) == 0


@pytest.mark.asyncio
async def test_another_workspace_is_not_touched(
    session: AsyncSession, test_user, test_workspace,
):
    other = Workspace(
        id=uuid.uuid4(), name="Elsewhere", created_by_user_id=test_user.id,
    )
    session.add(other)
    await session.flush()

    connection, institution = await _connection_with_institution(
        session, other.id, test_user.id, "Kiwibank"
    )
    foreign = _account(
        other.id, test_user.id, connection.id, institution.id,
        "waste not", "Kiwibank",
    )
    session.add(foreign)
    await session.commit()

    await relabel_auto_account_names(session, test_workspace.id)
    await session.commit()

    assert foreign.display_name == "Kiwibank"


@pytest.mark.asyncio
async def test_a_renamed_institution_updates_the_label_it_wrote(
    session: AsyncSession, test_user, test_workspace,
):
    """Our own format is recognisable, so a bank that renames itself does not
    leave every account carrying the old name for ever."""
    connection, institution = await _connection_with_institution(
        session, test_workspace.id, test_user.id, "Chase"
    )
    account = _account(
        test_workspace.id, test_user.id, connection.id, institution.id,
        "Checking", "Chase - Checking",
    )
    session.add(account)
    await session.commit()

    institution.name = "Chase Bank"
    await session.flush()

    assert await relabel_auto_account_names(session, test_workspace.id) == 1
    assert account.display_name == "Chase Bank - Checking"


def test_an_account_named_inside_the_institution_is_not_repeated():
    assert _default_account_label(
        "XP Investimentos CCTVM S/A", "XP"
    ) == "XP Investimentos CCTVM S/A"

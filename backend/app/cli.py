"""CLI commands for managing the application."""
import asyncio
import sys
import uuid

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.user import User


async def generate_recurring() -> None:
    """Generate pending recurring transactions for all users."""
    from app.core.app_clock import use_timezone
    from app.models.user import User as UserModel
    from app.services import recurring_transaction_service

    async with async_session_maker() as session, use_timezone(session, fresh=True):
        result = await session.execute(select(UserModel))
        users = result.scalars().all()
        total = 0
        for user in users:
            count = await recurring_transaction_service.generate_pending(session, user.id)
            if count > 0:
                print(f"Generated {count} transactions for {user.email}")
                total += count
        print(f"Total generated: {total}")


async def create_user(email: str, password: str) -> None:
    """Create a new user with the given email and password."""
    from pwdlib import PasswordHash

    hasher = PasswordHash.recommended()

    async with async_session_maker() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Error: User with email '{email}' already exists.")
            sys.exit(1)

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hasher.hash(password),
            is_active=True,
            is_superuser=False,
            is_verified=True,
            preferences={
                "language": "pt-BR",
                "date_format": "DD/MM/YYYY",
                "timezone": "America/Sao_Paulo",
                "currency_display": "USD",
            },
        )
        session.add(user)
        await session.commit()
        print(f"User created successfully: {email}")


async def categorisation_backtest(workspace_id: str | None = None) -> None:
    """Replay every categorised transaction and score the category memory.

    Each row is graded only against decisions made before it, which is what
    production sees: history first, then each new categorisation becoming
    training data for the next. Read-only.
    """
    from app.models.category import Category
    from app.models.workspace import Workspace
    from app.services import categorisation_memory

    async with async_session_maker() as session:
        if workspace_id:
            workspace_ids = [uuid.UUID(workspace_id)]
        else:
            workspace_ids = list((await session.execute(select(Workspace.id))).scalars())

        for ws_id in workspace_ids:
            names = {
                str(row.id): row.name
                for row in await session.execute(
                    select(Category.id, Category.name).where(
                        Category.workspace_id == ws_id
                    )
                )
            }
            results = await categorisation_memory.backtest(session, ws_id)
            print(f"\nworkspace {ws_id}")
            print(
                f"{'min_ev':>6} {'share':>6} {'graded':>7} {'suggested':>10}"
                f" {'correct':>8} {'coverage':>9} {'precision':>10} {'payee/desc':>11}"
            )
            for result in results:
                print(
                    f"{result.min_evidence:>6} {result.min_share:>6.2f}"
                    f" {result.graded:>7} {result.suggested:>10} {result.correct:>8}"
                    f" {result.coverage:>8.0%} {result.precision:>9.0%}"
                    f" {result.by_payee:>5}/{result.by_description:<5}"
                )
            for result in results:
                if not result.mismatches:
                    continue
                print(f"  wrong at min_ev={result.min_evidence} share={result.min_share:.2f}:")
                for label, proposed, actual, source, matched in result.mismatches[:5]:
                    print(
                        f"    {label!r}: suggested {names.get(proposed, proposed)}"
                        f", was {names.get(actual, actual)}"
                        f" (via {source} {matched!r})"
                    )


async def connections_backfill(connection_id: str) -> None:
    """Re-read a connection's full history and import whatever is missing.

    A normal sync only looks back far enough to catch changes since the last
    one, so history an earlier (narrower) window skipped past is invisible to
    it forever. This asks every account on the connection from
    `FULL_HISTORY_SINCE` instead, through the ordinary sync path - the same
    dedupe, payee matching and rules any other sync gets.

    Safe to repeat: rows are matched on the provider's external id, so a second
    run imports nothing new.
    """
    from app.models.bank_connection import BankConnection
    from app.models.transaction import Transaction
    from app.services.connection_service import sync_connection
    from sqlalchemy import func

    async with async_session_maker() as session:
        connection = await session.get(BankConnection, uuid.UUID(connection_id))
        if connection is None:
            print(f"Error: no connection with id {connection_id}")
            sys.exit(1)

        before = await session.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.workspace_id == connection.workspace_id,
                Transaction.source != "opening_balance",
            )
        )
        print(
            f"Connection {connection.id} ({connection.provider}/"
            f"{connection.institution_name}): {before} transactions before"
        )

        await sync_connection(
            session,
            connection.id,
            connection.workspace_id,
            connection.user_id,
            full_history=True,
        )

        after = await session.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.workspace_id == connection.workspace_id,
                Transaction.source != "opening_balance",
            )
        )
        print(f"imported {after - before} new transactions; {after} now")
        await session.commit()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m app.cli create-user <email> <password>")
        print("  python -m app.cli generate-recurring")
        print("  python -m app.cli categorisation-backtest [workspace_id]")
        print("  python -m app.cli connections-backfill <connection_id>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create-user":
        if len(sys.argv) != 4:
            print("Usage: python -m app.cli create-user <email> <password>")
            sys.exit(1)
        email, password = sys.argv[2], sys.argv[3]
        asyncio.run(create_user(email, password))
    elif command == "generate-recurring":
        asyncio.run(generate_recurring())
    elif command == "categorisation-backtest":
        asyncio.run(
            categorisation_backtest(sys.argv[2] if len(sys.argv) > 2 else None)
        )
    elif command == "connections-backfill":
        if len(sys.argv) != 3:
            print("Usage: python -m app.cli connections-backfill <connection_id>")
            sys.exit(1)
        asyncio.run(connections_backfill(sys.argv[2]))
    else:
        print(f"Unknown command: {command}")
        print(
            "Available commands: create-user, generate-recurring,"
            " categorisation-backtest, connections-backfill"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

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


async def accounts_relabel(workspace_id: str | None = None) -> None:
    """Give synced accounts the "Institution - Account" label, without a re-sync.

    The sync used to label an account with just its institution, so every
    Kiwibank account read "Kiwibank". This rewrites only the labels the sync
    owns - empty ones, the bare institution, and our own "Institution - Account"
    form - and leaves anything a person typed alone. It touches no transactions
    and asks the provider for nothing.
    """
    from app.models.workspace import Workspace
    from app.services.connection_service import relabel_auto_account_names

    async with async_session_maker() as session:
        workspace_ids = (
            [uuid.UUID(workspace_id)]
            if workspace_id
            else list((await session.execute(select(Workspace.id))).scalars())
        )
        total = 0
        for ws_id in workspace_ids:
            updated = await relabel_auto_account_names(session, ws_id)
            print(f"workspace {ws_id}: relabelled {updated} account(s)")
            total += updated
        await session.commit()
        print(f"total relabelled: {total}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m app.cli create-user <email> <password>")
        print("  python -m app.cli accounts-relabel [workspace_id]")
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
    elif command == "accounts-relabel":
        asyncio.run(
            accounts_relabel(sys.argv[2] if len(sys.argv) > 2 else None)
        )
    else:
        print(f"Unknown command: {command}")
        print("Available commands: create-user, generate-recurring, accounts-relabel")
        sys.exit(1)


if __name__ == "__main__":
    main()

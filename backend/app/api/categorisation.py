"""Read-only route for the learned category suggestions.

The memory proposes; the user decides. There is deliberately no accept endpoint
here - accepting is the ordinary transaction update (`PATCH /api/transactions/{id}`
or the bulk categorise route), so a suggestion can never become a write on its
own.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace
from app.schemas.categorisation import (
    CategorisationQueueItemRead,
    CategorisationSuggestionRead,
)
from app.services import categorisation_memory

router = APIRouter(prefix="/api/categorisation", tags=["categorisation"])


@router.get("/suggestions", response_model=list[CategorisationSuggestionRead])
async def list_suggestions(
    transaction_ids: Optional[list[uuid.UUID]] = Query(
        None,
        description=(
            "Grade exactly these transactions (the rows on screen). Omit to grade "
            "the workspace's newest uncategorised rows instead."
        ),
    ),
    limit: int = Query(50, ge=1, le=200),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> list[CategorisationSuggestionRead]:
    """Categories the workspace's own history would suggest for uncategorised rows.

    Rows the memory is not confident about are simply absent from the response,
    so a client renders a chip for what comes back and nothing otherwise. The
    caller may pass the rows currently visible, which keeps the work proportional
    to a page rather than to the backlog.
    """
    graded = await categorisation_memory.grade_uncategorised(
        session,
        ctx.workspace.id,
        transaction_ids=transaction_ids,
        limit=limit,
    )
    return [
        CategorisationSuggestionRead(
            transaction_id=item.transaction_id,
            category_id=item.category_id,
            category_name=item.category_name,
            confidence=item.confidence,
            evidence=item.evidence,
            agreed=item.agreed,
            source=item.source,
            matched=item.matched,
        )
        for item in graded
    ]


@router.get("/queue", response_model=list[CategorisationQueueItemRead])
async def review_queue(
    limit: int = Query(200, ge=1, le=1000),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> list[CategorisationQueueItemRead]:
    """Every uncategorised row the memory can propose something for.

    Ordered by how much history backs the proposal, so a person clears a
    backlog one merchant at a time instead of scrolling the ledger hoping to
    meet a suggestion. Read-only, exactly like the single-row route.
    """
    items = await categorisation_memory.grade_queue(
        session, ctx.workspace.id, limit=limit
    )
    return [
        CategorisationQueueItemRead(
            transaction_id=item.transaction_id,
            category_id=item.category_id,
            category_name=item.category_name,
            confidence=item.confidence,
            evidence=item.evidence,
            agreed=item.agreed,
            source=item.source,
            matched=item.matched,
            description=item.description,
            date=item.date,
            amount=item.amount,
            currency=item.currency,
            account_name=item.account_name,
        )
        for item in items
    ]

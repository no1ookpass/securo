"""Schemas for the learned category suggestions.

A suggestion is a proposal, never a decision: nothing here writes a category.
Accepting one is an ordinary transaction update, so the write path stays the one
that already requires a human.
"""

import uuid
from typing import Literal

from pydantic import BaseModel


class CategorisationSuggestionRead(BaseModel):
    """A category the memory would propose for one uncategorised transaction."""

    transaction_id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    #: Share of the supporting decisions that agree, 0..1.
    confidence: float
    #: How many earlier decisions the proposal rests on, and how many agree. The
    #: pair reads as "2 of 3", which is more honest than a bare percentage.
    evidence: int
    agreed: int
    #: Which index spoke: the merchant entity, or a description token.
    source: Literal["payee", "description"]
    #: The payee name or the token that matched, for showing its origin.
    matched: str

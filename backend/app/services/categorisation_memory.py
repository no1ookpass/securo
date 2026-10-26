"""Instance-based category memory: learn from what the workspace already decided.

There is no authored pattern and no training step. Every transaction that
carries a category is an example; grading a new row is a weighted vote over the
examples that look most like it. Because the examples are the rows themselves, a
category chosen today is part of the memory the next time it is built - nothing
to retrain, nothing to invalidate.

Two indexes, consulted strongest first:

1. ``payee`` - the provider's merchant entity. Aggregators do the hard entity
   resolution for us: Akahu maps every Woolworths descriptor shape
   ("Woolworths Online Favona", "WOOLWORTHS NZ/SILVERDALE SILVERDALE", ...) onto
   one payee, and keeps Uber and Uber Eats apart.
2. ``description tokens`` - for rows with no payee (imports, manual entries,
   pending rows that arrive without a merchant). Only *distinctive* tokens
   count: a token becomes usable evidence once decisions about transactions
   containing it agree on one category.

A payee with its own history always beats a token: "UBER *EATS" and "UBER *TRIP"
are near-identical strings but different payees with different categories, so a
token vote must never override an entity vote.

Nothing here writes. A suggestion is a proposal with its evidence attached; the
caller decides whether to show it and the user decides whether to accept it.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction

#: Decisions about a key before it may suggest anything at all. One is an
#: anecdote; two is a repeat, which is the point at which "last time it was X"
#: becomes a fair guess.
MIN_EVIDENCE = 2
#: Share of those decisions the winning category must hold. This is a
#: clear-majority rule, not a purity rule: a merchant with two legitimate uses
#: (Bunnings is mostly Homeware, occasionally a child's own purchase) should
#: still suggest its majority, and the count is shown so a 2-of-3 guess cannot
#: be mistaken for a pattern. A tie (1-1, 3-3) stays below this and abstains.
MIN_SHARE = 0.6

#: Thresholds reported by the backtest so the defaults can be chosen from data.
BACKTEST_THRESHOLDS: tuple[tuple[int, float], ...] = ((1, 0.6), (2, 0.6), (3, 0.8))

#: How many different payees a token may appear under before it stops counting as
#: evidence. One is the useful case: "woolworths" only ever showed up under the
#: Woolworths payee, so it identifies that merchant. "warehouse" shows up under
#: both The Warehouse and Bunnings Warehouse, and letting it vote produced a
#: Groceries suggestion for a DIY store. Rows with no payee share the ``None``
#: "payee", which is why the import/manual fallback still works.
MAX_TOKEN_PAYEES = 1

#: How many different merchants may sit behind one ``PREFIX*`` before the prefix
#: stops counting as evidence. Same idea as :data:`MAX_TOKEN_PAYEES`, because the
#: same mistake showed up in a different disguise: tokens are drawn from the
#: whole descriptor, and a payment aggregator's prefix is a token too, but it
#: names the gateway rather than the shop. One prefix with several shops behind
#: it is a gateway; one shop is that shop's own word.
MAX_PREFIX_MERCHANTS = 1

#: Card-processor and settlement noise that carries no identity. Place and store
#: names are deliberately absent: they are exactly the part that varies, and
#: keeping them out of the token set is what lets the same brand match across
#: suburbs without a hand-written rule.
#:
#: Each entry below earned its place from the backtest rather than from taste:
#: `tfr` suggested Education for rent transfers, `online` suggested Groceries
#: for a DIY store, and `fc02`-shaped reference codes voted from unrelated
#: payments. The plain English words go too - "to", "from" and friends identify
#: nothing.
_NOISE_TOKENS = frozenset(
    {
        "pending", "eftpos", "pos", "purchase", "payment", "paymt", "txn",
        "transaction", "tfr", "ref", "reference", "card", "visa", "debit",
        "credit", "nz", "ltd", "limited", "co", "inc", "com", "www", "http",
        "https", "help", "online",
        "to", "from", "for", "and", "the", "of", "at",
    }
)

#: Reference codes that survived the digit filter: a short letter run followed by
#: digits (``fc02``) or the reverse (``2go``). Neither identifies a merchant.
_CODE_SHAPE = re.compile(r"^[a-z]{1,3}\d+$|^\d+[a-z]{1,3}$")

_SPLIT = re.compile(r"[^0-9a-z]+")

#: ``SMZ*Vapeys``: the part before the asterisk is a card aggregator, the part
#: after it is the shop. A space before the asterisk (``UBER * EATS``) is a
#: brand's own format and is left alone.
_STAR_PREFIX = re.compile(r"(?<![0-9a-z])([a-z0-9]{2,12})\*")


def normalise_tokens(text: Optional[str]) -> frozenset[str]:
    """Turn a bank descriptor into the set of tokens that identify the merchant.

    Upper-case, split on anything that is not a letter or digit, then drop pure
    numbers (store ids, card numbers, dates), one-character noise, reference
    codes and the settlement vocabulary above.
    """
    if not text:
        return frozenset()
    tokens = _SPLIT.split(text.lower())
    return frozenset(
        token
        for token in tokens
        if len(token) > 1
        and not token.isdigit()
        and token not in _NOISE_TOKENS
        and not _CODE_SHAPE.match(token)
    )


def star_prefix_merchants(text: Optional[str]) -> frozenset[tuple[str, str]]:
    """The ``(prefix, merchant)`` pairs a descriptor contains.

    ``SMZ*Vapeys Silverdale`` and ``SMZ*The Avenue Hair`` are two unrelated
    shops billed through one aggregator. The prefix is not the shop, so it must
    not be taught as one: without this, 27 decisions about a vape shop voted
    "Hayden Splash" for a $1292 hair salon charge at full confidence. The
    merchant half is the first token after the asterisk that would itself have
    been usable as a token.
    """
    if not text:
        return frozenset()
    lowered = text.lower()
    pairs = set()
    for match in _STAR_PREFIX.finditer(lowered):
        for token in _SPLIT.split(lowered[match.end() :]):
            if (
                len(token) > 1
                and not token.isdigit()
                and token not in _NOISE_TOKENS
                and not _CODE_SHAPE.match(token)
            ):
                pairs.add((match.group(1), token))
                break
    return frozenset(pairs)


@dataclass(frozen=True)
class Suggestion:
    """A proposed category and the decisions behind it."""

    category_id: uuid.UUID
    #: Winning category's share of the evidence, 0..1.
    confidence: float
    #: Number of prior decisions this rests on.
    evidence: int
    source: Literal["payee", "description"]
    #: The payee name or token that matched, for display.
    matched: str
    #: How the evidence splits, so a UI can say "11 Groceries, 1 Household".
    votes: dict[uuid.UUID, int] = field(default_factory=dict)


class CategoryMemory:
    """Counts of past decisions, indexed by payee and by distinctive token.

    Deliberately has no database dependency: the same object serves the sync
    path, the backtest and the tests. Feed it with :meth:`add` (or build it from
    rows with :func:`load_memory`) and ask it for :meth:`suggest`.
    """

    def __init__(self) -> None:
        self._by_payee: dict[uuid.UUID, Counter[uuid.UUID]] = {}
        self._by_token: dict[str, Counter[uuid.UUID]] = {}
        self._token_payees: dict[str, set[Optional[uuid.UUID]]] = {}
        self._prefix_merchants: dict[str, set[str]] = {}

    def _note_prefixes(self, description: Optional[str]) -> None:
        for prefix, merchant in star_prefix_merchants(description):
            self._prefix_merchants.setdefault(prefix, set()).add(merchant)

    def add(
        self,
        category_id: uuid.UUID,
        *,
        payee_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
    ) -> None:
        """Record one confirmed decision. Every categorisation is learning."""
        if payee_id is not None:
            self._by_payee.setdefault(payee_id, Counter())[category_id] += 1
        self._note_prefixes(description)
        for token in normalise_tokens(description):
            self._by_token.setdefault(token, Counter())[category_id] += 1
            self._token_payees.setdefault(token, set()).add(payee_id)

    def observe(
        self,
        *,
        payee_id: Optional[uuid.UUID],
        description: Optional[str],
    ) -> None:
        """Note that a descriptor exists, without treating it as a decision.

        Token ambiguity has to be judged against everything the workspace has,
        not only what it has categorised. "beach" appeared under a single payee
        among labelled rows (a supermarket whose descriptor happens to name the
        suburb), so it was treated as distinctive and voted Groceries for a
        Mobil charge at the same beach. Seeing every descriptor closes that gap:
        a word that turns up under more than one merchant anywhere is not
        evidence about either of them.
        """
        self._note_prefixes(description)
        for token in normalise_tokens(description):
            self._token_payees.setdefault(token, set()).add(payee_id)

    def __len__(self) -> int:
        return sum(sum(c.values()) for c in self._by_payee.values())

    @staticmethod
    def _vote(
        counter: Optional[Counter[uuid.UUID]],
        min_evidence: int,
        min_share: float,
    ) -> Optional[tuple[uuid.UUID, float, int]]:
        """Pick a winner from a counter, or nothing if the evidence is thin."""
        if not counter:
            return None
        total = sum(counter.values())
        if total < min_evidence:
            return None
        category_id, top = counter.most_common(1)[0]
        share = top / total
        if share < min_share:
            return None
        return category_id, share, total

    def suggest(
        self,
        *,
        payee_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        payee_name: Optional[str] = None,
        min_evidence: int = MIN_EVIDENCE,
        min_share: float = MIN_SHARE,
    ) -> Optional[Suggestion]:
        """Propose a category, or ``None`` when the memory is not sure enough."""
        if payee_id is not None:
            counter = self._by_payee.get(payee_id)
            vote = self._vote(counter, min_evidence, min_share)
            if vote is not None:
                category_id, share, total = vote
                return Suggestion(
                    category_id=category_id,
                    confidence=share,
                    evidence=total,
                    source="payee",
                    matched=payee_name or str(payee_id),
                    votes=dict(counter),
                )

        # No usable entity evidence: fall back to the most trustworthy single
        # token. One token, not a sum, so a row cannot accumulate evidence by
        # matching several weak tokens at once. A token shared by more than one
        # merchant is not evidence about either of them.
        best: Optional[Suggestion] = None
        best_rank: tuple[int, float] = (0, 0.0)
        shared_prefixes = {
            prefix
            for prefix, merchants in self._prefix_merchants.items()
            if len(merchants) > MAX_PREFIX_MERCHANTS
        }
        for token in normalise_tokens(description):
            if token in shared_prefixes:
                continue
            if len(self._token_payees.get(token, ())) > MAX_TOKEN_PAYEES:
                continue
            counter = self._by_token.get(token)
            vote = self._vote(counter, min_evidence, min_share)
            if vote is None:
                continue
            category_id, share, total = vote
            rank = (total, share)
            if rank <= best_rank:
                continue
            best_rank = rank
            best = Suggestion(
                category_id=category_id,
                confidence=share,
                evidence=total,
                source="description",
                matched=token,
                votes=dict(counter),
            )
        return best


@dataclass(frozen=True)
class GradedTransaction:
    """One uncategorised transaction and what the memory would propose for it."""

    transaction_id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    confidence: float
    #: Decisions backing the proposal, and how many of them agree. The pair is
    #: what the UI shows as "2 of 3", which says more than a percentage.
    evidence: int
    agreed: int
    source: Literal["payee", "description"]
    matched: str


async def grade_uncategorised(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    transaction_ids: Optional[Iterable[uuid.UUID]] = None,
    limit: int = 50,
    min_evidence: int = MIN_EVIDENCE,
    min_share: float = MIN_SHARE,
) -> list[GradedTransaction]:
    """Propose a category for uncategorised transactions in a workspace.

    ``transaction_ids`` grades exactly those rows (the page in front of the
    user); without it the workspace's newest uncategorised rows are graded, up
    to ``limit``. Rows the memory is not sure about are simply absent from the
    result - the caller shows a chip for what came back and nothing otherwise.
    """
    stmt = select(
        Transaction.id,
        Transaction.payee_id,
        Transaction.description,
        Transaction.payee,
    ).where(
        Transaction.workspace_id == workspace_id,
        Transaction.category_id.is_(None),
        Transaction.is_ignored.is_(False),
        Transaction.source != "opening_balance",
    )
    if transaction_ids is not None:
        ids = list(transaction_ids)
        if not ids:
            return []
        stmt = stmt.where(Transaction.id.in_(ids))
    else:
        stmt = stmt.order_by(Transaction.date.desc(), Transaction.id).limit(limit)

    candidates = (await session.execute(stmt)).all()
    if not candidates:
        return []

    memory = await load_memory(session, workspace_id)

    graded: list[GradedTransaction] = []
    for row in candidates:
        suggestion = memory.suggest(
            payee_id=row.payee_id,
            description=row.description,
            payee_name=row.payee,
            min_evidence=min_evidence,
            min_share=min_share,
        )
        if suggestion is None:
            continue
        graded.append(
            GradedTransaction(
                transaction_id=row.id,
                category_id=suggestion.category_id,
                category_name="",
                confidence=suggestion.confidence,
                evidence=suggestion.evidence,
                agreed=suggestion.votes.get(suggestion.category_id, 0),
                source=suggestion.source,
                matched=suggestion.matched,
            )
        )
    if not graded:
        return []

    names = {
        row.id: row.name
        for row in await session.execute(
            select(Category.id, Category.name).where(
                Category.id.in_({g.category_id for g in graded})
            )
        )
    }
    return [
        GradedTransaction(
            transaction_id=g.transaction_id,
            category_id=g.category_id,
            category_name=names.get(g.category_id, ""),
            confidence=g.confidence,
            evidence=g.evidence,
            agreed=g.agreed,
            source=g.source,
            matched=g.matched,
        )
        for g in graded
    ]


@dataclass(frozen=True)
class QueueItem:
    """One row of the review queue: the transaction and its proposal."""

    transaction_id: uuid.UUID
    description: str
    date: object
    amount: object
    currency: str
    account_name: str
    category_id: uuid.UUID
    category_name: str
    confidence: float
    evidence: int
    agreed: int
    source: Literal["payee", "description"]
    matched: str


async def grade_queue(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    limit: int = 200,
    min_evidence: int = MIN_EVIDENCE,
    min_share: float = MIN_SHARE,
) -> list[QueueItem]:
    """Everything the workspace could categorise now, best-supported first.

    The same grading as :func:`grade_uncategorised`, but it returns the whole
    row so a review page can render it without a second query, and it sorts by
    evidence so the merchants with the most history come first - that is the
    order a person clears a backlog in, one merchant at a time.
    """
    candidates = (
        await session.execute(
            select(
                Transaction.id,
                Transaction.description,
                Transaction.date,
                Transaction.amount,
                Transaction.currency,
                Transaction.payee_id,
                Transaction.payee,
                Account.name,
            )
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.category_id.is_(None),
                Transaction.is_ignored.is_(False),
                Transaction.source != "opening_balance",
            )
            .order_by(Transaction.date.desc(), Transaction.id)
            .limit(limit)
        )
    ).all()
    if not candidates:
        return []

    memory = await load_memory(session, workspace_id)

    proposed: list[tuple[object, Suggestion]] = []
    for row in candidates:
        suggestion = memory.suggest(
            payee_id=row.payee_id,
            description=row.description,
            payee_name=row.payee,
            min_evidence=min_evidence,
            min_share=min_share,
        )
        if suggestion is not None:
            proposed.append((row, suggestion))
    if not proposed:
        return []

    names = {
        category.id: category.name
        for category in await session.execute(
            select(Category.id, Category.name).where(
                Category.id.in_({s.category_id for _, s in proposed})
            )
        )
    }
    items = [
        QueueItem(
            transaction_id=row.id,
            description=row.description,
            date=row.date,
            amount=row.amount,
            currency=row.currency,
            account_name=row.name,
            category_id=suggestion.category_id,
            category_name=names.get(suggestion.category_id, ""),
            confidence=suggestion.confidence,
            evidence=suggestion.evidence,
            agreed=suggestion.votes.get(suggestion.category_id, 0),
            source=suggestion.source,
            matched=suggestion.matched,
        )
        for row, suggestion in proposed
    ]
    # Most-supported first, then the strongest agreement, then newest.
    return sorted(
        items,
        key=lambda item: (item.evidence, item.confidence, item.date),
        reverse=True,
    )


async def load_memory(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    before: Optional[datetime] = None,
) -> CategoryMemory:
    """Build the memory from a workspace's existing categorised transactions.

    ``before`` (a datetime) excludes later decisions, which is what makes the
    backtest honest: a row is graded only against what was known at the time.
    """
    stmt = (
        select(
            Transaction.id,
            Transaction.category_id,
            Transaction.payee_id,
            Transaction.description,
            Transaction.created_at,
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.workspace_id == workspace_id,
            Transaction.category_id.is_not(None),
            Transaction.is_ignored.is_(False),
            Transaction.source != "opening_balance",
            Category.is_ignored.is_(False),
            Category.is_hidden.is_(False),
        )
        .order_by(Transaction.created_at, Transaction.id)
    )
    if before is not None:
        stmt = stmt.where(Transaction.created_at < before)

    memory = CategoryMemory()
    for row in await session.execute(stmt):
        memory.add(
            row.category_id,
            payee_id=row.payee_id,
            description=row.description,
        )

    # Second pass over every descriptor in the workspace, categorised or not,
    # so token ambiguity reflects the real merchant vocabulary rather than the
    # subset that happens to have a category.
    seen = (
        await session.execute(
            select(Transaction.payee_id, Transaction.description).where(
                Transaction.workspace_id == workspace_id,
                Transaction.source != "opening_balance",
            )
        )
    ).all()
    for row in seen:
        memory.observe(payee_id=row.payee_id, description=row.description)

    return memory


@dataclass
class BacktestResult:
    """What the memory would have said about history it had not yet seen."""

    min_evidence: int
    min_share: float
    graded: int = 0
    suggested: int = 0
    correct: int = 0
    by_payee: int = 0
    by_description: int = 0
    mismatches: list[tuple[str, str, str, str, str]] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        return self.suggested / self.graded if self.graded else 0.0

    @property
    def precision(self) -> float:
        return self.correct / self.suggested if self.suggested else 0.0


async def backtest(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    thresholds: Iterable[tuple[int, float]] = BACKTEST_THRESHOLDS,
    sample_mismatches: int = 10,
) -> list[BacktestResult]:
    """Replay the workspace's decisions in order and score the memory.

    Each categorised transaction is graded against decisions made *before* it,
    then added to the memory. That is the same order production sees: history
    first, then each new categorisation becoming training data for the next.
    """
    rows = (
        await session.execute(
            select(
                Transaction.category_id,
                Transaction.payee_id,
                Transaction.description,
                Transaction.payee,
                Transaction.created_at,
                Transaction.id,
            )
            .join(Category, Category.id == Transaction.category_id)
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.category_id.is_not(None),
                Transaction.is_ignored.is_(False),
                Transaction.source != "opening_balance",
                Category.is_ignored.is_(False),
                Category.is_hidden.is_(False),
            )
            .order_by(Transaction.created_at, Transaction.id)
        )
    ).all()

    results = {
        (min_evidence, min_share): BacktestResult(min_evidence, min_share)
        for min_evidence, min_share in thresholds
    }
    memory = CategoryMemory()

    for row in rows:
        for result in results.values():
            result.graded += 1
            suggestion = memory.suggest(
                payee_id=row.payee_id,
                description=row.description,
                payee_name=row.payee,
                min_evidence=result.min_evidence,
                min_share=result.min_share,
            )
            if suggestion is None:
                continue
            result.suggested += 1
            if suggestion.source == "payee":
                result.by_payee += 1
            else:
                result.by_description += 1
            if suggestion.category_id == row.category_id:
                result.correct += 1
            elif len(result.mismatches) < sample_mismatches:
                result.mismatches.append(
                    (
                        (row.payee or row.description or "")[:60],
                        str(suggestion.category_id),
                        str(row.category_id),
                        suggestion.source,
                        suggestion.matched,
                    )
                )
        # The decision is only visible to later rows.
        memory.add(row.category_id, payee_id=row.payee_id, description=row.description)

    return sorted(results.values(), key=lambda r: (r.min_evidence, r.min_share))

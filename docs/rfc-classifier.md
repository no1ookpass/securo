# RFC: a classifier trained on our own decisions

Status: draft, not implemented. Branch `feature/ai-classifier` (fork-only, not for
upstream).

Goal: a per-workspace classifier that learns from what we actually do — categorising,
tagging, reconciling — starting from knowing nothing. It only ever produces
suggestions; a human confirms every write. No change to a transaction's category,
tags or payee may happen because the model said so.

## What exists today

There is no ML in the categorisation path. It is one deterministic rules engine plus
three silent fallbacks, none of which ask for confirmation.

```
arrival (manual create / import / bank sync)
   |
   +- apply_rules_to_transaction()        user-authored rules, priority order
   |     conditions: description, payee, notes, amount, type, account, date, status
   |     actions:    set_category, set_payee, set_description, append_notes, ignore
   |     writes category_id directly on the row
   |
   +- if still uncategorised, silent fallbacks:
   |     CSV "category" column            import_service.py:1213
   |     bank's own category (Pluggy)     connection_service.py:822 (on by default)
   |     previous instalment's category   connection_service.py:887
   |
   +- reconciliation matching: confident matches link themselves; doubtful ones
      become ReconciliationSuggestion rows the user accepts or declines
```

Key files:

| Concern | Location |
|---|---|
| Rule model | `backend/app/models/rule.py` |
| Rule evaluation | `backend/app/services/rule_engine.py:202` |
| Rule validation / packs | `backend/app/services/rule_service.py` |
| Rules run on create | `backend/app/services/transaction_service.py:818`, `:929` |
| Rules run on import | `backend/app/services/import_service.py:1207` |
| Rules run on sync | `backend/app/services/connection_service.py:1284`, `:2504` |
| Rule re-apply (destructive) | `api/rules.py:278` -> `rule_service.py:1448` |
| Import preview suggestion | `backend/app/services/import_service.py:887` |
| Suggestion lifecycle to copy | `backend/app/models/reconciliation.py:124`, `services/reconciliation_suggestion_service.py` |
| Description suggestions | `backend/app/services/transaction_service.py:2086` |
| Tags | `#word` inside `transactions.notes`; `transaction_service.py:1722` |

### The one suggestion-only path, and its two leaks

`enrich_with_category_suggestions` runs on the import preview only and persists
nothing. But:

1. `frontend/src/components/import-review-table.tsx:95` uses the suggestion as the
   row's default selection, so "not touching the dropdown" reads as consent.
2. `import_service.py:1095-1104` sets `category_id = user_category_id or
   suggested_category_id`, so a client that posts the preview payload back persists a
   suggestion as truth.

### Learned behaviour that already exists, badly

- Instalment inheritance copies the category from an earlier parcel of the same
  purchase, silently (`connection_service.py:887`).
- Description suggestions return the category of the most recent transaction with the
  exact same description, unscored and only on near-identical text
  (`transaction_service.py:2086`).

Both generalise from a single observation with no threshold and no confirmation.

### Why we cannot train on history yet

Nothing records who set `category_id`. It is impossible to tell a human decision from
a rule, a bank category, an instalment copy or an import column. There is no
suggestion store for categories, and no confidence gate anywhere.

## Design

### Phase 0 - record decisions (not yet built)

Schema only. Nothing changes for the user: a `category_source` column plus an
append-only decision log, so Phase 1 can be measured against human labels rather than
auto-written ones. The backtest below works without it, but its precision figure is
measured against whatever category is on the row, including rule-set ones.

### Phase 1 — merchant memory (implemented)

`backend/app/services/categorisation_memory.py`, plus `python -m app.cli
categorisation-backtest [workspace_id]`.

Instance-based learning: no authored pattern and no training step. Two indexes are
built from transactions that already carry a category - `payee -> category` counts and
`distinctive description token -> category` counts - and grading a row is a vote over
them. The payee index is consulted first and wins, because the aggregator has already
resolved the merchant entity (Akahu maps every Woolworths descriptor shape onto one
payee, and keeps Uber and Uber Eats apart). The token index is the fallback for rows
with no payee: imports, manual entries, pending rows.

Because the examples are the rows themselves, history is included automatically and a
category chosen now is part of the memory on the next build. There is nothing to
retrain or invalidate.

Guards, none of which were guesses:

- `MIN_EVIDENCE = 3` decisions and `MIN_SHARE = 0.8` agreement before anything is
  suggested. Below that the memory emits nothing rather than a coin toss.
- A token seen under more than one payee is not evidence (`MAX_TOKEN_PAYEES = 1`).
  Without it, `warehouse` voted Groceries for Bunnings because The Warehouse's history
  is mostly groceries.
- Noise tokens learned from the backtest, not from taste: `tfr` (suggested Education
  for rent transfers), `online` (Groceries for a DIY store), reference codes shaped
  like `fc02`, and plain English words.

Backtest on the live workspace on 2026-10-26, 499 graded categorised transactions:

| min evidence | min share | coverage | precision |
|---|---|---|---|
| 2 | 0.70 | 90% | 100% |
| 3 | 0.80 | 86% | 100% |
| 5 | 0.90 | 79% | 100% |

Coverage is the share of rows the memory was willing to grade; the remainder are
merchants with fewer than three decisions behind them. Precision was 96-97% before the
token gate and noise fixes, which is how those gaps were found.

### Phase 2 — a small model (not yet needed)

Features: description tokens, amount bucket, account, weekday, existing tags. Trained
per workspace on the Phase 0 labels. Start with multinomial Naive Bayes — it is a
counting problem, it is explainable, and it needs no new dependency. Reach for
`scikit-learn` only if measurements justify the install. Phase 1 already reaches 100%
precision on the live workspace, so this waits until coverage (86%) is the thing that
needs improving, not precision.

### Phase 3 — embeddings

`fastembed` (ONNX, model fetched on first use) and `pgvector` are already in the stack,
though today only the agents knowledge base uses them. Embed the merchant string and
use pgvector kNN to handle "same shop, different descriptor", which token overlap
misses. `text_similarity.token_overlap` exists but is only wired into reconciliation.
This is the natural answer to the coverage gap: merchants with one or two decisions.

### The contract, in every phase

- The classifier never writes `transactions.category_id`, `notes` or `payee_id`.
  Suggestions live only in `categorisation_suggestions`.
- Below the evidence threshold it emits nothing. "Knows nothing by default" means no
  guess, not a low-confidence guess.
- Accepting performs the normal user write and records a positive label. Declining
  records a negative. Picking a different category after a suggestion appeared is the
  most valuable label: suggestion -> correction.
- Rules always run first and always win; the classifier only sees rows rules left
  uncategorised.
- Tags and payee are suggested the same way and applied only on accept.
- Cold start is per workspace and per category.

### UI

- A suggestion chip on the transaction row: proposed category, confidence, and the
  evidence ("12 similar, 11 agreed"), with accept and dismiss.
- A review queue reusing the reconciliation queue pattern.
- A "learned merchants" list — merchant, category, vote counts — that can be corrected
  in one click. This is the audit surface, and it replaces per-merchant rules.
- The import preview shows suggestions as an unselected hint, never a default.

### Measurement

Acceptance rate overall and per category, precision at the display threshold, and how
often a suggestion is replaced by a different category (the correction rate). The
backtest command is the offline half of this and is what picked the thresholds above.

## Open decisions

1. Do the bank-category mapping and instalment inheritance stay as silent writes, or
   become suggestions too? `use_provider_categories` already exists as a kill switch.
2. v1 scope: categories only, or categories + tags + payee?
3. Does the model also learn from reconciliation accepts, or strictly from
   categorisation and tagging?
4. Next slice: wire the memory into arrival (suggestion rows + UI), or close the
   coverage gap first with embeddings for merchants that have one or two decisions?


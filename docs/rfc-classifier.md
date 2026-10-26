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

### Phase 0 — record decisions (no model)

Schema only. Nothing changes for the user.

- `transactions.category_source`: `rule | provider | import_column | installment | user | classifier | unknown`.
  Backfill existing rows as `unknown` rather than guessing.
- An append-only `category_decisions` audit row for every human change: transaction,
  from, to, endpoint, user, timestamp. This is the label source.
- `categorisation_suggestions` modelled on `ReconciliationSuggestion`:
  `(workspace_id, transaction_id, target_kind, target_id, scores JSONB, model_version,
  status, resolved_by, resolved_at)`, unique on the dedupe pair, statuses
  `pending | accepted | declined | expired`, declines remembered, stale rows expire lazily.

Nothing else can be measured without this phase, so it ships first and alone.

### Phase 1 — merchant memory (pure SQL, no new dependency)

Normalise the counterparty string into a stable key, then per workspace keep
`key -> category` counts built from confirmed history. Suggest only when there are at
least N observations and at least X purity. Emits nothing otherwise.

### Phase 2 — a small model

Features: description tokens, amount bucket, account, weekday, existing tags. Trained
per workspace on the Phase 0 labels. Start with multinomial Naive Bayes — it is a
counting problem, it is explainable, and it needs no new dependency. Reach for
`scikit-learn` only if measurements justify the install.

### Phase 3 — embeddings

`fastembed` (ONNX, model fetched on first use) and `pgvector` are already in the stack,
though today only the agents knowledge base uses them. Embed the merchant string and
use pgvector kNN to handle "same shop, different descriptor", which token overlap
misses. `text_similarity.token_overlap` exists but is only wired into reconciliation.

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
- The import preview shows suggestions as an unselected hint, never a default.

### Measurement

Acceptance rate overall and per category, precision at the display threshold, and how
often a suggestion is replaced by a different category (the correction rate). Without
these numbers the thresholds are guesses.

## Open decisions

1. Do the bank-category mapping and instalment inheritance stay as silent writes, or
   become suggestions too? `use_provider_categories` already exists as a kill switch.
2. v1 scope: categories only, or categories + tags + payee?
3. Cold-start thresholds (for example: 10 confirmed observations of a merchant and 80%
   agreement before suggesting).
4. Does the model also learn from reconciliation accepts, or strictly from
   categorisation and tagging?

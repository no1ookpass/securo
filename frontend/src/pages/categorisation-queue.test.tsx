import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'

import CategorisationQueuePage from '@/pages/categorisation-queue'
import type { CategorisationQueueItem } from '@/types'
import { renderWithProviders, t } from '@/test/utils'

const api = vi.hoisted(() => ({
  categorisation: { queue: vi.fn(), suggestions: vi.fn() },
  transactions: { update: vi.fn(), bulkCategorize: vi.fn() },
}))

vi.mock('@/lib/api', () => ({
  categorisation: api.categorisation,
  transactions: api.transactions,
}))

vi.mock('@/hooks/use-display-locale', () => ({
  useDisplayLocale: () => 'en-US',
  useDateLocale: () => 'en-US',
}))

function item(overrides: Partial<CategorisationQueueItem> = {}): CategorisationQueueItem {
  return {
    transaction_id: 'txn-1',
    category_id: 'cat-rent',
    category_name: 'Rent',
    confidence: 1,
    evidence: 12,
    agreed: 12,
    source: 'payee',
    matched: 'Rothbury',
    description: 'ROTHBURY INSTALMENTS 095268342EXTN',
    date: '2026-11-01',
    amount: -450,
    currency: 'NZD',
    account_name: 'ASB',
    ...overrides,
  }
}

const acceptLabel = () => t('transactions.categorySuggestionAccept')
const dismissLabel = () => t('transactions.categorySuggestionDismiss')

describe('CategorisationQueuePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.transactions.update.mockResolvedValue({})
    api.transactions.bulkCategorize.mockResolvedValue({ updated: 2 })
  })

  it('files a whole merchant in one click, sending every row in the group', async () => {
    api.categorisation.queue.mockResolvedValue([
      item({ transaction_id: 'txn-1' }),
      item({ transaction_id: 'txn-2' }),
      item({ transaction_id: 'txn-3' }),
    ])

    const { user } = renderWithProviders(<CategorisationQueuePage />, {
      route: '/transactions/review-categories',
    })

    expect(await screen.findAllByText('ROTHBURY INSTALMENTS 095268342EXTN')).toHaveLength(3)

    // One group, so exactly one accept-all, and it knows how many it covers.
    const acceptAll = screen.getAllByRole('button', { name: t('categorisation.acceptAll', { count: 3 }) })
    expect(acceptAll).toHaveLength(1)

    await user.click(acceptAll[0])

    await waitFor(() =>
      expect(api.transactions.bulkCategorize).toHaveBeenCalledWith(
        ['txn-1', 'txn-2', 'txn-3'],
        'cat-rent',
      ),
    )
    // Grouping must not quietly fall back to filing rows one at a time.
    expect(api.transactions.update).not.toHaveBeenCalled()
  })

  it('keeps two proposals for the same merchant apart', async () => {
    // Same merchant and same match source, but the history favours a different
    // category. Offering one accept-all here would file half of them wrongly,
    // so the grouping key has to include the proposal itself.
    api.categorisation.queue.mockResolvedValue([
      item({ transaction_id: 'txn-1', category_id: 'cat-rent', category_name: 'Rent' }),
      item({
        transaction_id: 'txn-2',
        category_id: 'cat-insurance',
        category_name: 'Insurance',
        description: 'ROTHBURY INSTALMENTS 095268343EXTN',
      }),
    ])

    renderWithProviders(<CategorisationQueuePage />, {
      route: '/transactions/review-categories',
    })

    // Both chips are on screen, each standing alone.
    expect(await screen.findByText('Rent · 12/12')).toBeInTheDocument()
    expect(screen.getByText('Insurance · 12/12')).toBeInTheDocument()

    expect(screen.queryByRole('button', { name: /^Accept all/ })).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: acceptLabel() })).toHaveLength(2)
  })

  it('accepts a single row as an ordinary transaction update', async () => {
    api.categorisation.queue.mockResolvedValue([item({ transaction_id: 'txn-9' })])

    const { user } = renderWithProviders(<CategorisationQueuePage />, {
      route: '/transactions/review-categories',
    })

    await screen.findByText('ROTHBURY INSTALMENTS 095268342EXTN')
    await user.click(screen.getByRole('button', { name: acceptLabel() }))

    await waitFor(() =>
      expect(api.transactions.update).toHaveBeenCalledWith('txn-9', { category_id: 'cat-rent' }),
    )
  })

  it('hides a dismissed row without writing anything', async () => {
    api.categorisation.queue.mockResolvedValue([
      item({ transaction_id: 'txn-1' }),
      item({
        transaction_id: 'txn-2',
        matched: "McDonald's",
        category_id: 'cat-junk',
        category_name: 'Junk Food',
        description: "MCDONALD'S MTR10 WELLINGTON",
      }),
    ])

    const { user } = renderWithProviders(<CategorisationQueuePage />, {
      route: '/transactions/review-categories',
    })

    await screen.findByText('ROTHBURY INSTALMENTS 095268342EXTN')
    expect(screen.getByText("MCDONALD'S MTR10 WELLINGTON")).toBeInTheDocument()
    expect(screen.getByText('Junk Food · 12/12')).toBeInTheDocument()

    await user.click(screen.getAllByRole('button', { name: dismissLabel() })[0])

    // Only the row that was dismissed goes away, and dismissing is not a
    // decision: it must never reach the API.
    expect(screen.queryByText('ROTHBURY INSTALMENTS 095268342EXTN')).not.toBeInTheDocument()
    expect(screen.getByText("MCDONALD'S MTR10 WELLINGTON")).toBeInTheDocument()
    expect(api.transactions.update).not.toHaveBeenCalled()
    expect(api.transactions.bulkCategorize).not.toHaveBeenCalled()
  })

  it('says so when there is nothing to review', async () => {
    api.categorisation.queue.mockResolvedValue([])

    renderWithProviders(<CategorisationQueuePage />, {
      route: '/transactions/review-categories',
    })

    expect(await screen.findByText(t('categorisation.empty'))).toBeInTheDocument()
  })
})

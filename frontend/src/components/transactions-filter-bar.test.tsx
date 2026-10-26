import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'

import { TransactionsFilterBar } from '@/components/transactions-filter-bar'
import { renderWithProviders, t } from '@/test/utils'

// The bar formats and test-drives nothing financial; it only needs a user to
// resolve the display locale and currency.
vi.mock('@/contexts/auth-context', () => ({
  useAuth: () => ({ user: { preferences: { currency_display: 'USD' } } }),
}))

/**
 * The filter bar is a controlled component: the page owns the state and the
 * URL. These assertions are about the wiring in between, which TypeScript
 * cannot check - that the toggle asks the page to turn the filter on, that an
 * active filter is visible as a chip, and that the chip clears it again.
 */
function renderBar(overrides: { hasSuggestion?: boolean } = {}) {
  const onHasSuggestionChange = vi.fn()
  const utils = renderWithProviders(
    <TransactionsFilterBar
      searchInput=""
      onSearchChange={() => {}}
      filterAccountIds={[]}
      onAccountIdsChange={() => {}}
      filterCategoryIds={[]}
      onCategoryIdsChange={() => {}}
      filterUncategorized={false}
      onUncategorizedChange={() => {}}
      filterPayee=""
      onPayeeChange={() => {}}
      filterGroupId=""
      onGroupIdChange={() => {}}
      filterType=""
      onTypeChange={() => {}}
      filterStatus=""
      onStatusChange={() => {}}
      hideIgnored={false}
      onHideIgnoredChange={() => {}}
      filterHasSuggestion={overrides.hasSuggestion ?? false}
      onHasSuggestionChange={onHasSuggestionChange}
      filterFrom=""
      filterTo=""
      onDateRangeChange={() => {}}
      filterMinAmount=""
      filterMaxAmount=""
      onAmountRangeChange={() => {}}
      onClearAll={() => {}}
      accounts={[]}
      categories={[]}
      categoryGroups={[]}
      payees={[]}
      groups={[]}
    />,
  )
  return { ...utils, onHasSuggestionChange }
}

const label = () => t('transactions.hasSuggestion')

describe('TransactionsFilterBar has-suggestion filter', () => {
  it('offers the filter in the menu and asks the page to apply it', async () => {
    const { user, onHasSuggestionChange } = renderBar()

    await user.click(screen.getByRole('button', { name: t('transactions.filtersBar.filters') }))
    // The same menu serves desktop and mobile, so the option is rendered once
    // per layout; jsdom applies no media queries and keeps both. Either one
    // reaching the same callback is what matters.
    const options = await screen.findAllByText(label())

    await user.click(options[options.length - 1])

    expect(onHasSuggestionChange).toHaveBeenCalledWith(true)
  })

  it('shows the active filter as a chip that clears it', async () => {
    const { user, onHasSuggestionChange } = renderBar({ hasSuggestion: true })

    // The chip names the filter and its state, so "suggestions only" is
    // distinguishable from "has a suggestion column".
    const chip = screen
      .getByText(`${label()}:`)
      .closest('button') as HTMLElement
    expect(chip).toHaveTextContent(t('transactions.hasSuggestionOnly'))

    await user.click(chip)

    expect(onHasSuggestionChange).toHaveBeenCalledWith(false)
  })

  it('shows no chip while the filter is off', () => {
    renderBar()

    expect(screen.queryByText(`${label()}:`)).not.toBeInTheDocument()
  })
})

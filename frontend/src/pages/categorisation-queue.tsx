import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Check, Sparkles, X } from 'lucide-react'

import { categorisation, transactions } from '@/lib/api'
import { extractApiError } from '@/lib/api-errors'
import { invalidateFinancialQueries } from '@/lib/invalidate-queries'
import { formatCurrency } from '@/lib/format'
import { useDisplayLocale, useDateLocale } from '@/hooks/use-display-locale'
import type { CategorisationQueueItem } from '@/types'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

/**
 * The review queue: every uncategorised row this workspace's own history can
 * file, with the evidence and a one-click accept.
 *
 * Suggestions still decide nothing. Accepting calls the ordinary transaction
 * update, exactly as picking the category by hand would, and dismissing only
 * hides the row for this session.
 */
export function CategorisationQueuePage() {
  const { t } = useTranslation()
  const locale = useDisplayLocale()
  const dateLocale = useDateLocale()
  const queryClient = useQueryClient()
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['categorisation-queue'],
    queryFn: () => categorisation.queue(500),
  })

  const acceptOne = useMutation({
    mutationFn: (item: CategorisationQueueItem) =>
      transactions.update(item.transaction_id, { category_id: item.category_id }),
    onSuccess: () => {
      invalidateFinancialQueries(queryClient)
      queryClient.invalidateQueries({ queryKey: ['categorisation-queue'] })
    },
    onError: (error) => toast.error(extractApiError(error)),
  })

  const acceptGroup = useMutation({
    mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string }) =>
      transactions.bulkCategorize(ids, categoryId),
    onSuccess: (result) => {
      invalidateFinancialQueries(queryClient)
      queryClient.invalidateQueries({ queryKey: ['categorisation-queue'] })
      toast.success(t('categorisation.accepted', { count: result.updated }))
    },
    onError: (error) => toast.error(extractApiError(error)),
  })

  const items = useMemo(
    () => (data ?? []).filter((item) => !dismissed.has(item.transaction_id)),
    [data, dismissed],
  )

  /**
   * Rows that share a merchant and a proposal: clearing nine Rothbury rows is
   * one decision, not nine. Keyed on what actually carried the suggestion so a
   * token match groups the same way a payee match does.
   */
  const groups = useMemo(() => {
    const byKey = new Map<string, CategorisationQueueItem[]>()
    for (const item of items) {
      const key = `${item.source}:${item.matched}:${item.category_id}`
      const bucket = byKey.get(key)
      if (bucket) bucket.push(item)
      else byKey.set(key, [item])
    }
    return byKey
  }, [items])

  const dismiss = (item: CategorisationQueueItem) => {
    setDismissed((prev) => new Set(prev).add(item.transaction_id))
  }

  return (
    <div className="space-y-4">
      <PageHeader section={t('categorisation.title')} title={t('categorisation.title')} />
      <p className="text-sm text-muted-foreground">{t('categorisation.subtitle')}</p>

      {isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
          {t('categorisation.empty')}
        </div>
      )}

      <div className="space-y-2">
        {items.map((item) => {
          const key = `${item.source}:${item.matched}:${item.category_id}`
          const group = groups.get(key) ?? [item]
          const isFirstOfGroup = group[0]?.transaction_id === item.transaction_id
          const isBusy = busy === item.transaction_id
          return (
            <div
              key={item.transaction_id}
              className="flex flex-col gap-2 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{item.description}</p>
                <p className="text-xs text-muted-foreground">
                  {item.account_name} ·{' '}
                  {new Date(item.date).toLocaleDateString(dateLocale)} ·{' '}
                  {formatCurrency(Math.abs(Number(item.amount)), item.currency, locale)}
                </p>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <span
                  className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
                  title={t('transactions.categorySuggestionTooltip', {
                    category: item.category_name,
                    count: item.evidence,
                    matched: item.matched,
                  })}
                >
                  <Sparkles className="h-3 w-3" />
                  {t('transactions.categorySuggestion', {
                    category: item.category_name,
                    agreed: item.agreed,
                    evidence: item.evidence,
                  })}
                </span>

                {isFirstOfGroup && group.length > 1 && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={acceptGroup.isPending}
                    onClick={() =>
                      acceptGroup.mutate({
                        ids: group.map((g) => g.transaction_id),
                        categoryId: item.category_id,
                      })
                    }
                  >
                    {t('categorisation.acceptAll', { count: group.length })}
                  </Button>
                )}

                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={t('transactions.categorySuggestionAccept')}
                  title={t('transactions.categorySuggestionAccept')}
                  disabled={isBusy}
                  onClick={() => {
                    setBusy(item.transaction_id)
                    acceptOne.mutate(item, { onSettled: () => setBusy(null) })
                  }}
                >
                  <Check className="h-4 w-4 text-emerald-600" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={t('transactions.categorySuggestionDismiss')}
                  title={t('transactions.categorySuggestionDismiss')}
                  onClick={() => dismiss(item)}
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </Button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default CategorisationQueuePage

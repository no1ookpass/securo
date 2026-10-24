import { afterEach, describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'

import { IconPicker } from '@/components/icon-picker'
import { i18n, renderWithProviders } from '@/test/utils'

describe('IconPicker', () => {
  afterEach(() => {
    void i18n.changeLanguage('en')
  })

  it('shows icon tooltips in the active language (en)', async () => {
    await i18n.changeLanguage('en')
    renderWithProviders(<IconPicker value="" color="" onChange={() => {}} />)
    expect(screen.getByTitle('Health / Wellbeing')).toBeInTheDocument()
    expect(screen.queryByTitle('Saúde / Bem-estar')).not.toBeInTheDocument()
  })

  it('shows icon tooltips in the active language (pt-BR)', async () => {
    await i18n.changeLanguage('pt-BR')
    renderWithProviders(<IconPicker value="" color="" onChange={() => {}} />)
    expect(screen.getByTitle('Saúde / Bem-estar')).toBeInTheDocument()
    expect(screen.queryByTitle('Health / Wellbeing')).not.toBeInTheDocument()
  })

  it('finds icons by the translated label when searching (en)', async () => {
    await i18n.changeLanguage('en')
    const { user } = renderWithProviders(
      <IconPicker value="" color="" onChange={() => {}} />
    )
    await user.type(
      screen.getByPlaceholderText(i18n.t('common.searchIcon')),
      'health'
    )
    expect(screen.getByTitle('Health / Wellbeing')).toBeInTheDocument()
  })

  it('finds icons by the translated label when searching (pt-BR)', async () => {
    await i18n.changeLanguage('pt-BR')
    const { user } = renderWithProviders(
      <IconPicker value="" color="" onChange={() => {}} />
    )
    await user.type(
      screen.getByPlaceholderText(i18n.t('common.searchIcon')),
      'saúde'
    )
    expect(screen.getByTitle('Saúde / Bem-estar')).toBeInTheDocument()
  })

  it('hides translated icons that do not match a current-language search', async () => {
    await i18n.changeLanguage('en')
    const { user } = renderWithProviders(
      <IconPicker value="" color="" onChange={() => {}} />
    )
    await user.type(
      screen.getByPlaceholderText(i18n.t('common.searchIcon')),
      'saúde'
    )
    // A translated icon is searched by its English label, so 'heart' drops out
    // even though its Portuguese label contains the term.
    expect(screen.queryByTitle('Health / Wellbeing')).not.toBeInTheDocument()
    // Fork note: icons that have no translation in the active locale fall back
    // to their Portuguese label by design (see CATEGORY_ICONS), so the grid is
    // not necessarily empty - 'activity' still matches on its fallback.
    expect(screen.getByTitle('Atividade / Saúde')).toBeInTheDocument()
  })
})

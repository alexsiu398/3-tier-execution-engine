/**
 * ExecutionSettings component tests
 * RED: drives the ExecutionSettings component implementation.
 *
 * Tests:
 * - renders all three strategy options (Option A/B/C)
 * - current strategy radio is checked
 * - clicking a different strategy calls updateSettings
 * - shows flow description for each option
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { ExecutionSettings as ExecutionSettingsType } from '../types'

vi.mock('../services/api', () => ({
  updateSettings: vi.fn(),
}))

const defaultSettings: ExecutionSettingsType = {
  id: 1,
  fallback_strategy: 'option_c',
  timeout_per_tier_seconds: 10,
  max_retry_per_tier: 2,
}

describe('ExecutionSettings', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders three strategy radio inputs', async () => {
    const { ExecutionSettings } = await import('../components/ExecutionSettings')
    render(<ExecutionSettings settings={defaultSettings} onUpdate={vi.fn()} />)

    const radios = screen.getAllByRole('radio')
    expect(radios).toHaveLength(3)
  })

  it('renders Option A, Option B, Option C labels', async () => {
    const { ExecutionSettings } = await import('../components/ExecutionSettings')
    render(<ExecutionSettings settings={defaultSettings} onUpdate={vi.fn()} />)

    expect(screen.getByText(/Option A/i)).toBeInTheDocument()
    expect(screen.getByText(/Option B/i)).toBeInTheDocument()
    expect(screen.getByText(/Option C/i)).toBeInTheDocument()
  })

  it('checks the current strategy radio', async () => {
    const { ExecutionSettings } = await import('../components/ExecutionSettings')
    render(<ExecutionSettings settings={{ ...defaultSettings, fallback_strategy: 'option_a' }} onUpdate={vi.fn()} />)

    const radios = screen.getAllByRole('radio')
    const optionARadio = radios.find((r) => (r as HTMLInputElement).value === 'option_a')
    expect(optionARadio).toBeChecked()
  })

  it('calls updateSettings and onUpdate when a different strategy is selected', async () => {
    const { updateSettings } = await import('../services/api')
    const mockedUpdate = vi.mocked(updateSettings)
    const newSettings = { ...defaultSettings, fallback_strategy: 'option_b' as const }
    mockedUpdate.mockResolvedValue(newSettings)

    const onUpdate = vi.fn()
    const { ExecutionSettings } = await import('../components/ExecutionSettings')
    render(<ExecutionSettings settings={defaultSettings} onUpdate={onUpdate} />)

    const radios = screen.getAllByRole('radio')
    const optionBRadio = radios.find((r) => (r as HTMLInputElement).value === 'option_b')!
    fireEvent.click(optionBRadio)

    await waitFor(() => {
      expect(mockedUpdate).toHaveBeenCalledWith({ fallback_strategy: 'option_b' })
      expect(onUpdate).toHaveBeenCalledWith(newSettings)
    })
  })

  it('shows fallback flow description for each option', async () => {
    const { ExecutionSettings } = await import('../components/ExecutionSettings')
    render(<ExecutionSettings settings={defaultSettings} onUpdate={vi.fn()} />)

    // All three options' flows should be present
    expect(screen.getByText('Playwright → XPath Cache')).toBeInTheDocument()
    expect(screen.getByText('Playwright → Stagehand AI')).toBeInTheDocument()
    expect(screen.getByText('Playwright → XPath Cache → Stagehand AI')).toBeInTheDocument()
  })

  it('disables radios while saving', async () => {
    const { updateSettings } = await import('../services/api')
    const mockedUpdate = vi.mocked(updateSettings)
    // Never resolve so it stays in saving state
    mockedUpdate.mockReturnValue(new Promise(() => {}))

    const { ExecutionSettings } = await import('../components/ExecutionSettings')
    render(<ExecutionSettings settings={defaultSettings} onUpdate={vi.fn()} />)

    const radios = screen.getAllByRole('radio')
    const optionARadio = radios.find((r) => (r as HTMLInputElement).value === 'option_a')!
    fireEvent.click(optionARadio)

    await waitFor(() => {
      const allRadios = screen.getAllByRole('radio')
      allRadios.forEach((r) => expect(r).toBeDisabled())
    })
  })
})

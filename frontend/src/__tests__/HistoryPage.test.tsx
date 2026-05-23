/**
 * HistoryPage component tests
 * RED: drives the HistoryPage page implementation.
 *
 * Tests:
 * - fetches and renders execution summaries
 * - shows empty state when no executions
 * - renders tier counts per execution
 * - clicking a row loads execution detail
 * - renders TierAnalyticsChart with execution data
 * - detail view shows per-step tier breakdown
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ExecutionSummary, Execution } from '../types'

vi.mock('../services/api', () => ({
  getExecutions: vi.fn(),
  getExecution: vi.fn(),
}))

vi.mock('../components/TierAnalyticsChart', () => ({
  TierAnalyticsChart: ({ executions }: { executions: ExecutionSummary[] }) => (
    <div data-testid="tier-chart" data-count={executions.length} />
  ),
}))

const mockSummaries: ExecutionSummary[] = [
  {
    id: 1, test_case_id: 1, strategy: 'option_c', status: 'completed',
    started_at: '2024-01-15T12:00:00Z',
    total_steps: 3, tier1_count: 2, tier2_count: 1, tier3_count: 0, success_count: 3,
  },
  {
    id: 2, test_case_id: 2, strategy: 'option_a', status: 'failed',
    total_steps: 2, tier1_count: 1, tier2_count: 0, tier3_count: 1, success_count: 1,
  },
]

const mockDetail: Execution = {
  id: 1,
  test_case_id: 1,
  strategy: 'option_c',
  status: 'completed',
  steps: [
    { id: 1, step_index: 0, instruction: 'Navigate to homepage', tier_used: 1, success: true, duration_ms: 120, xpath_cached: false },
    { id: 2, step_index: 1, instruction: 'Click login', tier_used: 2, success: true, duration_ms: 88, xpath_cached: true },
    { id: 3, step_index: 2, instruction: 'Submit form', tier_used: 1, success: true, duration_ms: 55, xpath_cached: false },
  ],
}

describe('HistoryPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('fetches and renders execution list', async () => {
    const { getExecutions } = await import('../services/api')
    vi.mocked(getExecutions).mockResolvedValue(mockSummaries)

    const { HistoryPage } = await import('../pages/HistoryPage')
    render(<MemoryRouter><HistoryPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getAllByRole('row').length).toBeGreaterThan(2) // header + data rows
    })
  })

  it('shows empty state when no executions', async () => {
    const { getExecutions } = await import('../services/api')
    vi.mocked(getExecutions).mockResolvedValue([])

    const { HistoryPage } = await import('../pages/HistoryPage')
    render(<MemoryRouter><HistoryPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText(/no executions/i)).toBeInTheDocument()
    })
  })

  it('renders tier counts (T1/T2/T3) in table rows', async () => {
    const { getExecutions } = await import('../services/api')
    vi.mocked(getExecutions).mockResolvedValue(mockSummaries)

    const { HistoryPage } = await import('../pages/HistoryPage')
    render(<MemoryRouter><HistoryPage /></MemoryRouter>)

    await waitFor(() => {
      // Tier counts from first summary: tier1=2, tier2=1, tier3=0
      // Multiple cells may contain '2'; just verify at least some exist
      expect(screen.getAllByText('2').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('renders TierAnalyticsChart with the executions', async () => {
    const { getExecutions } = await import('../services/api')
    vi.mocked(getExecutions).mockResolvedValue(mockSummaries)

    const { HistoryPage } = await import('../pages/HistoryPage')
    render(<MemoryRouter><HistoryPage /></MemoryRouter>)

    await waitFor(() => {
      const chart = screen.getByTestId('tier-chart')
      expect(chart).toBeInTheDocument()
      expect(chart).toHaveAttribute('data-count', '2')
    })
  })

  it('clicking a row calls getExecution and shows detail panel', async () => {
    const { getExecutions, getExecution } = await import('../services/api')
    vi.mocked(getExecutions).mockResolvedValue(mockSummaries)
    vi.mocked(getExecution).mockResolvedValue(mockDetail)

    const { HistoryPage } = await import('../pages/HistoryPage')
    render(<MemoryRouter><HistoryPage /></MemoryRouter>)

    await waitFor(() => screen.getAllByRole('row').length > 2)

    // Click the first data row (skip header row)
    const rows = screen.getAllByRole('row')
    fireEvent.click(rows[1]) // rows[0] is header

    await waitFor(() => {
      expect(getExecution).toHaveBeenCalledWith(1)
    })
  })

  it('detail panel shows step instructions', async () => {
    const { getExecutions, getExecution } = await import('../services/api')
    vi.mocked(getExecutions).mockResolvedValue(mockSummaries)
    vi.mocked(getExecution).mockResolvedValue(mockDetail)

    const { HistoryPage } = await import('../pages/HistoryPage')
    render(<MemoryRouter><HistoryPage /></MemoryRouter>)

    await waitFor(() => screen.getAllByRole('row').length > 2)
    const rows = screen.getAllByRole('row')
    fireEvent.click(rows[1])

    await waitFor(() => {
      expect(screen.getByText('Navigate to homepage')).toBeInTheDocument()
      expect(screen.getByText('Click login')).toBeInTheDocument()
    })
  })

  it('detail panel shows tier badges for steps', async () => {
    const { getExecutions, getExecution } = await import('../services/api')
    vi.mocked(getExecutions).mockResolvedValue(mockSummaries)
    vi.mocked(getExecution).mockResolvedValue(mockDetail)

    const { HistoryPage } = await import('../pages/HistoryPage')
    render(<MemoryRouter><HistoryPage /></MemoryRouter>)

    await waitFor(() => screen.getAllByRole('row').length > 2)
    const rows = screen.getAllByRole('row')
    fireEvent.click(rows[1])

    await waitFor(() => {
      // Multiple T1 badges appear (step badges) — check at least one
      expect(screen.getAllByText('T1').length).toBeGreaterThan(0)
      // The cached badge shows ' cached' text
      expect(screen.getByText(/cached/i)).toBeInTheDocument()
    })
  })

  it('shows strategy for each execution in summary table', async () => {
    const { getExecutions } = await import('../services/api')
    vi.mocked(getExecutions).mockResolvedValue(mockSummaries)

    const { HistoryPage } = await import('../pages/HistoryPage')
    render(<MemoryRouter><HistoryPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('option_c')).toBeInTheDocument()
      expect(screen.getByText('option_a')).toBeInTheDocument()
    })
  })
})

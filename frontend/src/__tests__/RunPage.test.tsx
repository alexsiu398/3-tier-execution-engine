/**
 * RunPage component tests
 * RED: drives the RunPage page implementation.
 *
 * Tests:
 * - renders test selector dropdown
 * - Run button is disabled when no test selected
 * - Run button enabled after selecting a test
 * - clicking Run starts execution and opens SSE stream
 * - progress steps are updated as SSE events arrive
 * - shows "complete" message when execution done
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { TestCase, ExecutionSettings } from '../types'

vi.mock('../services/api', () => ({
  getTestCases: vi.fn(),
  getSettings: vi.fn(),
  startExecution: vi.fn(),
  subscribeToExecution: vi.fn(),
  updateSettings: vi.fn(),
}))

vi.mock('../components/ExecutionSettings', () => ({
  ExecutionSettings: ({ settings }: { settings: ExecutionSettings }) => (
    <div data-testid="execution-settings">Strategy: {settings.fallback_strategy}</div>
  ),
}))

vi.mock('../components/ExecutionProgress', () => ({
  ExecutionProgress: ({ steps, totalSteps }: { steps: unknown[]; totalSteps: number }) => (
    <div data-testid="execution-progress">
      {steps.length} / {totalSteps} steps rendered
    </div>
  ),
}))

const mockTests: TestCase[] = [
  {
    id: 1,
    title: 'Login Flow',
    url: 'https://example.com',
    steps: [
      { action: 'click', instruction: 'Click login' },
      { action: 'fill', instruction: 'Fill email' },
    ],
    created_at: '',
  },
]

const mockSettings: ExecutionSettings = {
  id: 1,
  fallback_strategy: 'option_c',
  timeout_per_tier_seconds: 10,
  max_retry_per_tier: 2,
}

describe('RunPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders test selector dropdown', async () => {
    const { getTestCases, getSettings } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)
    vi.mocked(getSettings).mockResolvedValue(mockSettings)

    const { RunPage } = await import('../pages/RunPage')
    render(<MemoryRouter><RunPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })
  })

  it('Run button is disabled when no test selected', async () => {
    const { getTestCases, getSettings } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)
    vi.mocked(getSettings).mockResolvedValue(mockSettings)

    const { RunPage } = await import('../pages/RunPage')
    render(<MemoryRouter><RunPage /></MemoryRouter>)

    await waitFor(() => screen.getByRole('button', { name: /run test/i }))
    expect(screen.getByRole('button', { name: /run test/i })).toBeDisabled()
  })

  it('Run button is enabled after selecting a test', async () => {
    const { getTestCases, getSettings } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)
    vi.mocked(getSettings).mockResolvedValue(mockSettings)

    const { RunPage } = await import('../pages/RunPage')
    render(<MemoryRouter><RunPage /></MemoryRouter>)

    await waitFor(() => screen.getByRole('combobox'))
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /run test/i })).not.toBeDisabled()
    })
  })

  it('clicking Run calls startExecution with selected test', async () => {
    const { getTestCases, getSettings, startExecution, subscribeToExecution } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)
    vi.mocked(getSettings).mockResolvedValue(mockSettings)
    vi.mocked(startExecution).mockResolvedValue({ execution_id: 42, status: 'running' })
    vi.mocked(subscribeToExecution).mockReturnValue({ close: vi.fn() } as unknown as EventSource)

    const { RunPage } = await import('../pages/RunPage')
    render(<MemoryRouter><RunPage /></MemoryRouter>)

    await waitFor(() => screen.getByRole('combobox'))
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })

    await waitFor(() => screen.getByRole('button', { name: /run test/i }))
    fireEvent.click(screen.getByRole('button', { name: /run test/i }))

    await waitFor(() => {
      expect(startExecution).toHaveBeenCalledWith({
        test_case_id: 1,
        strategy: 'option_c',
      })
    })
  })

  it('renders execution progress after starting run', async () => {
    const { getTestCases, getSettings, startExecution, subscribeToExecution } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)
    vi.mocked(getSettings).mockResolvedValue(mockSettings)
    vi.mocked(startExecution).mockResolvedValue({ execution_id: 42, status: 'running' })
    vi.mocked(subscribeToExecution).mockReturnValue({ close: vi.fn() } as unknown as EventSource)

    const { RunPage } = await import('../pages/RunPage')
    render(<MemoryRouter><RunPage /></MemoryRouter>)

    await waitFor(() => screen.getByRole('combobox'))
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })

    await waitFor(() => screen.getByRole('button', { name: /run test/i }))
    fireEvent.click(screen.getByRole('button', { name: /run test/i }))

    await waitFor(() => {
      expect(screen.getByTestId('execution-progress')).toBeInTheDocument()
    })
  })

  it('calls subscribeToExecution with the execution_id', async () => {
    const { getTestCases, getSettings, startExecution, subscribeToExecution } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)
    vi.mocked(getSettings).mockResolvedValue(mockSettings)
    vi.mocked(startExecution).mockResolvedValue({ execution_id: 42, status: 'running' })
    vi.mocked(subscribeToExecution).mockReturnValue({ close: vi.fn() } as unknown as EventSource)

    const { RunPage } = await import('../pages/RunPage')
    render(<MemoryRouter><RunPage /></MemoryRouter>)

    await waitFor(() => screen.getByRole('combobox'))
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: /run test/i }))

    await waitFor(() => {
      expect(subscribeToExecution).toHaveBeenCalledWith(42, expect.any(Function), expect.any(Function))
    })
  })

  it('shows execution settings panel', async () => {
    const { getTestCases, getSettings } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)
    vi.mocked(getSettings).mockResolvedValue(mockSettings)

    const { RunPage } = await import('../pages/RunPage')
    render(<MemoryRouter><RunPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByTestId('execution-settings')).toBeInTheDocument()
    })
  })
})

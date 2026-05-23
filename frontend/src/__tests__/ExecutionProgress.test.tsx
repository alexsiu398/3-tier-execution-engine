/**
 * ExecutionProgress component tests
 * RED: drives the ExecutionProgress component implementation.
 *
 * Tests:
 * - renders each step in the list
 * - shows spinner for in-progress step
 * - renders TierBadge for completed steps
 * - shows duration for completed steps
 * - shows summary bar with counts and timing
 * - shows error message for failed steps
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

const completedStep = {
  index: 0,
  instruction: 'Click login',
  tier: 1 as const,
  success: true,
  duration_ms: 45,
  xpath_cached: false,
  inProgress: false,
}

const inProgressStep = {
  index: 1,
  instruction: 'Fill username',
  inProgress: true,
}

const failedStep = {
  index: 2,
  instruction: 'Click submit',
  tier: 3 as const,
  success: false,
  duration_ms: 1200,
  error: 'Element not found',
  xpath_cached: false,
  inProgress: false,
}

describe('ExecutionProgress', () => {
  it('renders step instructions', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(<ExecutionProgress steps={[completedStep]} totalSteps={1} />)

    expect(screen.getByText('Click login')).toBeInTheDocument()
  })

  it('renders spinner for in-progress step', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(<ExecutionProgress steps={[inProgressStep]} totalSteps={3} />)

    expect(screen.getByLabelText(/running/i)).toBeInTheDocument()
  })

  it('renders T1 tier badge for completed Tier 1 step', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(<ExecutionProgress steps={[completedStep]} totalSteps={1} />)

    expect(screen.getByText('T1')).toBeInTheDocument()
  })

  it('renders T3 badge for Tier 3 failed step', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(<ExecutionProgress steps={[failedStep]} totalSteps={3} />)

    expect(screen.getByText('T3')).toBeInTheDocument()
  })

  it('shows duration for completed step', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(<ExecutionProgress steps={[completedStep]} totalSteps={1} />)

    // Duration appears in the step info and in the summary; use getAllByText
    expect(screen.getAllByText(/45\s*ms/i).length).toBeGreaterThan(0)
  })

  it('shows error message for failed step', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(<ExecutionProgress steps={[failedStep]} totalSteps={3} />)

    expect(screen.getByText('Element not found')).toBeInTheDocument()
  })

  it('shows summary bar when there are completed steps', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(
      <ExecutionProgress steps={[completedStep, failedStep]} totalSteps={3} />
    )

    // Should show step counts
    expect(screen.getByText(/2\s*\/\s*3/)).toBeInTheDocument()
  })

  it('shows 100% Tier 1 when all steps use Tier 1', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(<ExecutionProgress steps={[completedStep]} totalSteps={1} />)

    expect(screen.getByText(/100%/)).toBeInTheDocument()
  })

  it('hides summary bar when no steps are completed', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    const { container } = render(
      <ExecutionProgress steps={[inProgressStep]} totalSteps={3} />
    )

    // Summary should not be present
    expect(container.querySelector('.execution-progress__summary')).toBeNull()
  })

  it('renders multiple steps in order', async () => {
    const { ExecutionProgress } = await import('../components/ExecutionProgress')
    render(
      <ExecutionProgress
        steps={[completedStep, inProgressStep, failedStep]}
        totalSteps={3}
      />
    )

    expect(screen.getByText('Click login')).toBeInTheDocument()
    expect(screen.getByText('Fill username')).toBeInTheDocument()
    expect(screen.getByText('Click submit')).toBeInTheDocument()
  })
})

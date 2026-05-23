/**
 * StepEditor component tests
 * RED: drives the StepEditor component implementation.
 *
 * Tests:
 * - renders empty state with Add Step button
 * - clicking Add Step adds a row
 * - can update action dropdown
 * - can update instruction textarea
 * - clicking × removes a step
 * - shows step numbers
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { TestStep } from '../types'

const sampleSteps: TestStep[] = [
  { action: 'navigate', instruction: 'Go to homepage' },
  { action: 'click', instruction: 'Click login button', selector: '#login' },
]

describe('StepEditor', () => {
  it('renders "Add Step" button', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={vi.fn()} />)
    expect(screen.getByText(/add step/i)).toBeInTheDocument()
  })

  it('renders one row per step', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={sampleSteps} onChange={vi.fn()} />)

    // Each row shows instruction
    expect(screen.getByDisplayValue('Go to homepage')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Click login button')).toBeInTheDocument()
  })

  it('clicking Add Step calls onChange with one more step', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={onChange} />)

    fireEvent.click(screen.getByText(/add step/i))

    expect(onChange).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ instruction: '' })])
    )
    const [newSteps] = onChange.mock.calls[0]
    expect(newSteps).toHaveLength(1)
  })

  it('appends new step to existing steps when Add Step is clicked', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={sampleSteps} onChange={onChange} />)

    fireEvent.click(screen.getByText(/add step/i))

    const [newSteps] = onChange.mock.calls[0]
    expect(newSteps).toHaveLength(3)
  })

  it('clicking remove (×) button calls onChange without that step', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={sampleSteps} onChange={onChange} />)

    const removeButtons = screen.getAllByRole('button', { name: /remove step/i })
    fireEvent.click(removeButtons[0])

    const [newSteps] = onChange.mock.calls[0]
    expect(newSteps).toHaveLength(1)
    expect(newSteps[0].instruction).toBe('Click login button')
  })

  it('updating instruction textarea calls onChange with updated step', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={sampleSteps} onChange={onChange} />)

    const textarea = screen.getByDisplayValue('Go to homepage')
    fireEvent.change(textarea, { target: { value: 'Navigate to /about' } })

    const [newSteps] = onChange.mock.calls[0]
    expect(newSteps[0].instruction).toBe('Navigate to /about')
  })

  it('updating action dropdown calls onChange with updated action', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'navigate', instruction: 'test' }]} onChange={onChange} />)

    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'click' } })

    const [newSteps] = onChange.mock.calls[0]
    expect(newSteps[0].action).toBe('click')
  })

  it('renders selector input for each step', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={sampleSteps} onChange={vi.fn()} />)

    // The second step has selector #login
    expect(screen.getByDisplayValue('#login')).toBeInTheDocument()
  })

  it('renders step numbers starting from 1', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={sampleSteps} onChange={vi.fn()} />)

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })
})

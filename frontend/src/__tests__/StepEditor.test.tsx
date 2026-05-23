/**
 * StepEditor component tests — per-step form editor
 *
 * Tests:
 * - renders a row per step (not a single textarea)
 * - shows action dropdown, instruction, selector, value inputs per step
 * - initialises selector input from step.selector
 * - preserves selector in onChange output (does NOT drop it)
 * - preserves selector when instruction is changed
 * - adding a step appends a blank click row
 * - removing a step fires onChange without that step
 * - changing action fires onChange with new action
 * - changing instruction fires onChange with new instruction
 * - changing selector fires onChange with new selector (as step.selector)
 * - changing value fires onChange with new value
 * - renders "Add step" button
 * - renders no rows when steps is empty
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { TestStep } from '../types'

const ACTIONS = ['navigate', 'click', 'fill', 'press', 'assert_text', 'assert_url']

describe('StepEditor', () => {
  it('renders no rows when steps is empty', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={vi.fn()} />)
    expect(screen.queryAllByRole('row')).toHaveLength(0)
  })

  it('renders one row per step', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    const steps: TestStep[] = [
      { action: 'click', instruction: 'Click login' },
      { action: 'navigate', instruction: 'Go home' },
    ]
    render(<StepEditor steps={steps} onChange={vi.fn()} />)
    expect(screen.getAllByRole('row')).toHaveLength(2)
  })

  it('shows an action dropdown for each step', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'click', instruction: 'Click btn' }]} onChange={vi.fn()} />)
    const selects = screen.getAllByRole('combobox')
    expect(selects).toHaveLength(1)
    expect(selects[0]).toHaveValue('click')
  })

  it('shows an instruction input for each step', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'click', instruction: 'Click btn' }]} onChange={vi.fn()} />)
    expect(screen.getByPlaceholderText(/instruction/i)).toHaveValue('Click btn')
  })

  it('shows a selector/XPath input for each step', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'click', instruction: 'Click btn' }]} onChange={vi.fn()} />)
    expect(screen.getByPlaceholderText(/xpath|selector/i)).toBeInTheDocument()
  })

  it('initialises selector input from step.selector', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(
      <StepEditor
        steps={[{ action: 'click', instruction: 'Click submit', selector: "//button[@id='submit']" }]}
        onChange={vi.fn()}
      />
    )
    expect(screen.getByPlaceholderText(/xpath|selector/i)).toHaveValue("//button[@id='submit']")
  })

  it('preserves selector in onChange when instruction changes', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(
      <StepEditor
        steps={[{ action: 'click', instruction: 'Click submit', selector: "//button[@id='submit']" }]}
        onChange={onChange}
      />
    )
    fireEvent.change(screen.getByPlaceholderText(/instruction/i), {
      target: { value: 'Click the submit button' },
    })
    const [updatedSteps] = onChange.mock.calls[onChange.mock.calls.length - 1]
    expect(updatedSteps[0].selector).toBe("//button[@id='submit']")
  })

  it('includes selector in onChange output when typed', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'click', instruction: 'Click btn' }]} onChange={onChange} />)
    fireEvent.change(screen.getByPlaceholderText(/xpath|selector/i), {
      target: { value: "//button[@type='submit']" },
    })
    const [updatedSteps] = onChange.mock.calls[onChange.mock.calls.length - 1]
    expect(updatedSteps[0].selector).toBe("//button[@type='submit']")
  })

  it('includes value in onChange output when typed', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'fill', instruction: 'Enter email' }]} onChange={onChange} />)
    fireEvent.change(screen.getByPlaceholderText(/text to type/i), {
      target: { value: 'test@example.com' },
    })
    const [updatedSteps] = onChange.mock.calls[onChange.mock.calls.length - 1]
    expect(updatedSteps[0].value).toBe('test@example.com')
  })

  it('changing action fires onChange with new action', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'click', instruction: 'Click btn' }]} onChange={onChange} />)
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'navigate' } })
    const [updatedSteps] = onChange.mock.calls[0]
    expect(updatedSteps[0].action).toBe('navigate')
  })

  it('renders an Add Step button', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: /add step/i })).toBeInTheDocument()
  })

  it('add step appends a blank row and calls onChange', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'click', instruction: 'Step 1' }]} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: /add step/i }))
    const [updatedSteps] = onChange.mock.calls[0]
    expect(updatedSteps).toHaveLength(2)
    expect(updatedSteps[1].action).toBe('click')
    expect(updatedSteps[1].instruction).toBe('')
  })

  it('remove button deletes the step and calls onChange', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(
      <StepEditor
        steps={[
          { action: 'click', instruction: 'Step 1' },
          { action: 'navigate', instruction: 'Step 2' },
        ]}
        onChange={onChange}
      />
    )
    fireEvent.click(screen.getAllByRole('button', { name: /remove|delete|×/i })[0])
    const [updatedSteps] = onChange.mock.calls[0]
    expect(updatedSteps).toHaveLength(1)
    expect(updatedSteps[0].instruction).toBe('Step 2')
  })

  it('action dropdown contains all valid actions', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[{ action: 'click', instruction: 'x' }]} onChange={vi.fn()} />)
    const select = screen.getAllByRole('combobox')[0]
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.value)
    ACTIONS.forEach((a) => expect(options).toContain(a))
  })
})

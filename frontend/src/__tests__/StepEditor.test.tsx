/**
 * StepEditor component tests — plain-text editor
 *
 * Tests:
 * - renders a single textarea for all steps
 * - serializes click steps as bare instruction lines
 * - serializes non-click steps as "action: instruction"
 * - onChange called when textarea content changes
 * - parses bare lines as click action
 * - parses "action: instruction" prefixed lines
 * - parses lines with space-separated action prefix
 * - filters empty lines from parsed output
 * - renders placeholder text
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { TestStep } from '../types'

const sampleSteps: TestStep[] = [
  { action: 'navigate', instruction: 'Go to homepage' },
  { action: 'click', instruction: 'Click login button' },
]

describe('StepEditor', () => {
  it('renders a single textarea', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={vi.fn()} />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('serializes click steps as bare instruction lines', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    const steps: TestStep[] = [{ action: 'click', instruction: 'Click login' }]
    render(<StepEditor steps={steps} onChange={vi.fn()} />)
    expect(screen.getByRole('textbox')).toHaveValue('Click login')
  })

  it('serializes non-click steps with action prefix', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={sampleSteps} onChange={vi.fn()} />)
    const text = (screen.getByRole('textbox') as HTMLTextAreaElement).value
    expect(text).toContain('navigate: Go to homepage')
    expect(text).toContain('Click login button')
  })

  it('onChange called when textarea changes', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Do something' } })
    expect(onChange).toHaveBeenCalledTimes(1)
  })

  it('parses a bare line as a click step', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Click the button' } })
    const [steps] = onChange.mock.calls[0]
    expect(steps).toHaveLength(1)
    expect(steps[0]).toMatchObject({ action: 'click', instruction: 'Click the button' })
  })

  it('parses "action: instruction" prefixed lines', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'navigate: https://example.com\nfill: username field with admin' },
    })
    const [steps] = onChange.mock.calls[0]
    expect(steps).toHaveLength(2)
    expect(steps[0]).toMatchObject({ action: 'navigate', instruction: 'https://example.com' })
    expect(steps[1]).toMatchObject({ action: 'fill', instruction: 'username field with admin' })
  })

  it('parses space-separated action prefix without colon', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'navigate https://example.com' },
    })
    const [steps] = onChange.mock.calls[0]
    expect(steps[0]).toMatchObject({ action: 'navigate', instruction: 'https://example.com' })
  })

  it('filters empty lines', async () => {
    const onChange = vi.fn()
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'Step one\n\n  \nStep two' },
    })
    const [steps] = onChange.mock.calls[0]
    expect(steps).toHaveLength(2)
  })

  it('shows helpful placeholder text', async () => {
    const { StepEditor } = await import('../components/StepEditor')
    render(<StepEditor steps={[]} onChange={vi.fn()} />)
    expect(screen.getByPlaceholderText(/navigate/i)).toBeInTheDocument()
  })
})

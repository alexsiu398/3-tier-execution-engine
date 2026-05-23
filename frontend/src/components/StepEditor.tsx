import { useState } from 'react'
import type { TestStep, StepAction } from '../types'

const ACTIONS: StepAction[] = ['navigate', 'click', 'fill', 'press', 'assert_text', 'assert_url']

function stepsToText(steps: TestStep[]): string {
  return steps
    .map((step) => (step.action === 'click' ? step.instruction : `${step.action}: ${step.instruction}`))
    .join('\n')
}

function textToSteps(text: string): TestStep[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line): TestStep => {
      // Try "action: rest" format
      const colonIdx = line.indexOf(': ')
      if (colonIdx > 0) {
        const maybeAction = line.slice(0, colonIdx) as StepAction
        if (ACTIONS.includes(maybeAction)) {
          return { action: maybeAction, instruction: line.slice(colonIdx + 2) }
        }
      }
      // Try "action rest" (space-separated, no colon)
      const spaceIdx = line.indexOf(' ')
      if (spaceIdx > 0) {
        const maybeAction = line.slice(0, spaceIdx) as StepAction
        if (ACTIONS.includes(maybeAction)) {
          return { action: maybeAction, instruction: line.slice(spaceIdx + 1) }
        }
      }
      return { action: 'click', instruction: line }
    })
}

interface StepEditorProps {
  steps: TestStep[]
  onChange: (steps: TestStep[]) => void
}

export function StepEditor({ steps, onChange }: StepEditorProps) {
  // Local text state so the textarea is never reset mid-edit.
  // Spaces, newlines, and partial words all stay intact while typing.
  // The parent receives parsed steps via onChange, but doesn't drive the textarea value.
  const [text, setText] = useState(() => stepsToText(steps))

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value
    setText(newText)
    onChange(textToSteps(newText))
  }

  return (
    <div className="step-editor">
      <label htmlFor="steps-text">
        Steps
        <textarea
          id="steps-text"
          className="step-editor__textarea"
          value={text}
          onChange={handleChange}
          placeholder={`navigate https://example.com\nclick Login button\nfill Username with admin@test.com`}
          rows={8}
        />
      </label>
      <p className="step-editor__hint">
        One step per line. Optionally prefix with action:{' '}
        {ACTIONS.join(', ')}
      </p>
    </div>
  )
}

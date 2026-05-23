import { useState } from 'react'
import type { TestStep, StepAction } from '../types'

const ACTIONS: StepAction[] = ['navigate', 'click', 'fill', 'press', 'assert_text', 'assert_url']

function getValuePlaceholder(action: StepAction): string {
  switch (action) {
    case 'fill':
      return 'Text to type, e.g. standard_user'
    case 'press':
      return 'Key to press, e.g. Enter'
    case 'assert_text':
      return 'Expected text'
    case 'assert_url':
      return 'Expected URL fragment'
    case 'navigate':
      return 'Optional URL override'
    default:
      return 'Usually empty for click'
  }
}

interface StepEditorProps {
  steps: TestStep[]
  onChange: (steps: TestStep[]) => void
}

export function StepEditor({ steps, onChange }: StepEditorProps) {
  const [localSteps, setLocalSteps] = useState<TestStep[]>(steps)

  const update = (updated: TestStep[]) => {
    setLocalSteps(updated)
    onChange(updated)
  }

  const handleFieldChange = (index: number, field: keyof TestStep, value: string) => {
    update(
      localSteps.map((s, i) =>
        i === index ? { ...s, [field]: value || undefined } : s
      )
    )
  }

  const addStep = () => {
    update([...localSteps, { action: 'click', instruction: '' }])
  }

  const removeStep = (index: number) => {
    update(localSteps.filter((_, i) => i !== index))
  }

  return (
    <div className="step-editor">
      <p className="step-editor__hint">
        Put the full XPath or CSS selector in Selector. Do not type only <strong>XPath</strong>. For{' '}
        <strong>fill</strong>, Value is the text to enter.
      </p>
      <table className="step-editor__table">
        <tbody>
          {localSteps.map((step, i) => (
            <tr key={i}>
              <td>
                <select
                  value={step.action}
                  onChange={(e) => handleFieldChange(i, 'action', e.target.value)}
                >
                  {ACTIONS.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  placeholder="Instruction"
                  value={step.instruction}
                  onChange={(e) => handleFieldChange(i, 'instruction', e.target.value)}
                />
              </td>
              <td>
                <input
                  placeholder="Full XPath / CSS selector"
                  value={step.selector ?? ''}
                  onChange={(e) => handleFieldChange(i, 'selector', e.target.value)}
                />
              </td>
              <td>
                <input
                  placeholder={getValuePlaceholder(step.action)}
                  value={step.value ?? ''}
                  onChange={(e) => handleFieldChange(i, 'value', e.target.value)}
                />
              </td>
              <td>
                <button
                  type="button"
                  aria-label="Remove step"
                  onClick={() => removeStep(i)}
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" className="step-editor__add" onClick={addStep}>
        Add Step
      </button>
    </div>
  )
}

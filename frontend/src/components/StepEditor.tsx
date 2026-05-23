import type { TestStep, StepAction } from '../types'

const ACTIONS: StepAction[] = ['navigate', 'click', 'fill', 'press', 'assert_text', 'assert_url']

interface StepEditorProps {
  steps: TestStep[]
  onChange: (steps: TestStep[]) => void
}

export function StepEditor({ steps, onChange }: StepEditorProps) {
  const addStep = () => {
    onChange([...steps, { action: 'click', instruction: '' }])
  }

  const removeStep = (index: number) => {
    onChange(steps.filter((_, i) => i !== index))
  }

  const updateStep = (index: number, field: keyof TestStep, value: string) => {
    const updated = steps.map((step, i) =>
      i === index ? { ...step, [field]: value } : step
    )
    onChange(updated)
  }

  return (
    <div className="step-editor">
      <table className="step-editor__table">
        <thead>
          <tr>
            <th>#</th>
            <th>Action</th>
            <th>Instruction</th>
            <th>Selector (optional)</th>
            <th>Value (optional)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step, i) => (
            <tr key={i}>
              <td>{i + 1}</td>
              <td>
                <select
                  value={step.action}
                  onChange={(e) => updateStep(i, 'action', e.target.value)}
                >
                  {ACTIONS.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </td>
              <td>
                <textarea
                  value={step.instruction}
                  onChange={(e) => updateStep(i, 'instruction', e.target.value)}
                  placeholder="Step instruction…"
                />
              </td>
              <td>
                <input
                  type="text"
                  value={step.selector ?? ''}
                  onChange={(e) => updateStep(i, 'selector', e.target.value)}
                  placeholder="Optional CSS selector"
                />
              </td>
              <td>
                <input
                  type="text"
                  value={step.value ?? ''}
                  onChange={(e) => updateStep(i, 'value', e.target.value)}
                  placeholder="Optional value"
                />
              </td>
              <td>
                <button
                  type="button"
                  onClick={() => removeStep(i)}
                  aria-label="Remove step"
                  className="btn-icon"
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" onClick={addStep} className="step-editor__add">
        + Add Step
      </button>
    </div>
  )
}

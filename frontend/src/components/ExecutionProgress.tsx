import { TierBadge } from './TierBadge'

interface ProgressStep {
  index: number
  instruction?: string
  tier?: 1 | 2 | 3
  success?: boolean
  duration_ms?: number
  error?: string
  xpath_cached?: boolean
  inProgress?: boolean
}

interface ExecutionProgressProps {
  steps: ProgressStep[]
  totalSteps: number
}

export function ExecutionProgress({ steps, totalSteps }: ExecutionProgressProps) {
  const completedSteps = steps.filter((s) => !s.inProgress && s.tier !== undefined)
  const tier1Count = completedSteps.filter((s) => s.tier === 1).length
  const tier1Pct = completedSteps.length > 0
    ? Math.round((tier1Count / completedSteps.length) * 100)
    : 0
  const totalMs = completedSteps.reduce((sum, s) => sum + (s.duration_ms ?? 0), 0)

  return (
    <div className="execution-progress">
      <div className="execution-progress__timeline">
        {steps.map((step) => (
          <div
            key={step.index}
            className={[
              'execution-progress__step',
              step.inProgress ? 'execution-progress__step--running' : '',
              step.success === false ? 'execution-progress__step--failed' : '',
            ].filter(Boolean).join(' ')}
          >
            <span className="execution-progress__step-num">{step.index + 1}</span>
            <div className="execution-progress__step-info">
              <span className="execution-progress__instruction">
                {step.instruction ?? `Step ${step.index + 1}`}
              </span>
              {step.inProgress && (
                <span className="execution-progress__spinner" aria-label="Running" />
              )}
              {step.tier !== undefined && (
                <TierBadge tier={step.tier} xpath_cached={step.xpath_cached} />
              )}
              {step.duration_ms !== undefined && (
                <span className="execution-progress__duration">{step.duration_ms} ms</span>
              )}
              {step.error && (
                <span className="execution-progress__error">{step.error}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {completedSteps.length > 0 && (
        <div className="execution-progress__summary">
          <span>{completedSteps.length} / {totalSteps} steps</span>
          <span>{totalMs} ms total</span>
          <span>{tier1Pct}% Tier 1</span>
        </div>
      )}
    </div>
  )
}

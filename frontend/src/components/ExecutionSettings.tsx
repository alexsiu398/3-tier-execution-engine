import { useState } from 'react'
import type { ExecutionSettings as ExecutionSettingsType } from '../types'
import { updateSettings } from '../services/api'

const STRATEGY_OPTIONS = [
  {
    value: 'option_a' as const,
    label: 'Option A',
    description: 'Tier 1 → Tier 2',
    flow: 'Playwright → XPath Cache',
    costProfile: 'Low cost',
  },
  {
    value: 'option_b' as const,
    label: 'Option B',
    description: 'Tier 1 → Tier 3',
    flow: 'Playwright → Stagehand AI',
    costProfile: 'High cost',
  },
  {
    value: 'option_c' as const,
    label: 'Option C',
    description: 'Tier 1 → Tier 2 → Tier 3',
    flow: 'Playwright → XPath Cache → Stagehand AI',
    costProfile: 'Balanced',
  },
]

interface ExecutionSettingsProps {
  settings: ExecutionSettingsType
  onUpdate: (settings: ExecutionSettingsType) => void
}

export function ExecutionSettings({ settings, onUpdate }: ExecutionSettingsProps) {
  const [saving, setSaving] = useState(false)

  const handleStrategyChange = async (strategy: ExecutionSettingsType['fallback_strategy']) => {
    setSaving(true)
    try {
      const updated = await updateSettings({ fallback_strategy: strategy })
      onUpdate(updated)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="execution-settings">
      <h3>Fallback Strategy</h3>
      <div className="execution-settings__cards">
        {STRATEGY_OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className={`execution-settings__card ${
              settings.fallback_strategy === opt.value ? 'execution-settings__card--selected' : ''
            }`}
          >
            <input
              type="radio"
              name="fallback_strategy"
              value={opt.value}
              checked={settings.fallback_strategy === opt.value}
              onChange={() => handleStrategyChange(opt.value)}
              disabled={saving}
            />
            <div className="execution-settings__card-body">
              <strong>{opt.label}</strong>
              <p>{opt.description}</p>
              <small>{opt.flow}</small>
              <span className="execution-settings__cost">{opt.costProfile}</span>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}

import { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { TestCase, ExecutionSettings, SSEProgressEvent } from '../types'
import { getTestCases, getSettings, startExecution, subscribeToExecution } from '../services/api'
import { ExecutionProgress } from '../components/ExecutionProgress'
import { ExecutionSettings as ExecutionSettingsPanel } from '../components/ExecutionSettings'

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

export function RunPage() {
  const [searchParams] = useSearchParams()
  const [tests, setTests] = useState<TestCase[]>([])
  const [selectedTestId, setSelectedTestId] = useState<number | null>(null)
  const [settings, setSettings] = useState<ExecutionSettings | null>(null)
  const [running, setRunning] = useState(false)
  const [steps, setSteps] = useState<ProgressStep[]>([])
  const [done, setDone] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const preselect = searchParams.get('test')
    Promise.all([getTestCases(), getSettings()]).then(([cases, s]) => {
      setTests(cases)
      setSettings(s)
      if (preselect) setSelectedTestId(Number(preselect))
    })
    return () => {
      esRef.current?.close()
    }
  }, [searchParams])

  const selectedTest = tests.find((t) => t.id === selectedTestId) ?? null

  const handleRun = async () => {
    if (!selectedTestId || !settings) return
    esRef.current?.close()
    setRunning(true)
    setDone(false)

    const initialSteps: ProgressStep[] = (selectedTest?.steps ?? []).map((s, i) => ({
      index: i,
      instruction: s.instruction,
      inProgress: i === 0,
    }))
    setSteps(initialSteps)

    const { execution_id } = await startExecution({
      test_case_id: selectedTestId,
      strategy: settings.fallback_strategy,
    })

    const handleEvent = (event: SSEProgressEvent) => {
      setSteps((prev) =>
        prev.map((s) => {
          if (s.index === event.step_index) {
            return {
              ...s,
              tier: event.tier,
              success: event.success,
              duration_ms: event.duration_ms,
              error: event.error,
              xpath_cached: event.xpath_cached,
              inProgress: false,
            }
          }
          if (s.index === event.step_index + 1) {
            return { ...s, inProgress: true }
          }
          return s
        })
      )
    }

    const handleDone = () => {
      setRunning(false)
      setDone(true)
      esRef.current?.close()
    }

    const es = subscribeToExecution(execution_id, handleEvent, handleDone)
    esRef.current = es
  }

  return (
    <div className="page">
      <h2>Run Execution</h2>
      <div className="run-layout">
        <div className="run-controls">
          <label htmlFor="test-select">Test Case</label>
          <select
            id="test-select"
            value={selectedTestId ?? ''}
            onChange={(e) => setSelectedTestId(Number(e.target.value) || null)}
          >
            <option value="">Select a test…</option>
            {tests.map((t) => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>

          {settings && (
            <ExecutionSettingsPanel settings={settings} onUpdate={setSettings} />
          )}

          <button
            type="button"
            onClick={handleRun}
            disabled={running || !selectedTestId}
            className="btn-primary"
          >
            {running ? 'Running…' : 'Run Test'}
          </button>
        </div>

        <div className="run-progress">
          {steps.length > 0 && (
            <ExecutionProgress
              steps={steps}
              totalSteps={selectedTest?.steps.length ?? 0}
            />
          )}
          {done && <p className="run-done">Execution complete.</p>}
        </div>
      </div>
    </div>
  )
}

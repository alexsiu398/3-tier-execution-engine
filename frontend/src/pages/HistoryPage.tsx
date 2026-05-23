import { useEffect, useState } from 'react'
import type { ExecutionSummary, Execution } from '../types'
import { getExecutions, getExecution } from '../services/api'
import { TierBadge } from '../components/TierBadge'
import { TierAnalyticsChart } from '../components/TierAnalyticsChart'

export function HistoryPage() {
  const [executions, setExecutions] = useState<ExecutionSummary[]>([])
  const [selected, setSelected] = useState<Execution | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getExecutions()
      .then(setExecutions)
      .finally(() => setLoading(false))
  }, [])

  const handleSelect = async (id: number) => {
    setSelectedId(id)
    const detail = await getExecution(id)
    setSelected(detail)
  }

  return (
    <div className="page">
      <h2>Execution History</h2>

      {loading && <p>Loading…</p>}

      {!loading && executions.length === 0 && (
        <p className="empty-state">No executions yet.</p>
      )}

      {executions.length > 0 && (
        <div className="history-layout">
          <div className="history-main">
            <TierAnalyticsChart executions={executions} />

            <div className="history-table-wrap">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Test ID</th>
                    <th>Strategy</th>
                    <th>Status</th>
                    <th>Steps</th>
                    <th>T1</th>
                    <th>T2</th>
                    <th>T3</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {executions.map((e) => (
                    <tr
                      key={e.id}
                      onClick={() => handleSelect(e.id)}
                      className={`history-table__row${selectedId === e.id ? ' history-table__row--selected' : ''}`}
                    >
                      <td>{e.id}</td>
                      <td>{e.test_case_id}</td>
                      <td>{e.strategy}</td>
                      <td className={`status-${e.status}`}>{e.status}</td>
                      <td>{e.total_steps}</td>
                      <td>{e.tier1_count}</td>
                      <td>{e.tier2_count}</td>
                      <td>{e.tier3_count}</td>
                      <td>{e.started_at ? new Date(e.started_at).toLocaleDateString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="execution-detail">
            <div className="execution-detail__header">
              <h3>
                {selected ? `Execution #${selected.id} — Steps` : 'Select a row to inspect'}
              </h3>
            </div>
            {!selected && (
              <p className="execution-detail__empty">Click any execution row to see step details.</p>
            )}
            {selected && (
              <table className="step-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Instruction</th>
                    <th>Tier</th>
                    <th>OK</th>
                    <th>ms</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.steps.map((step) => (
                    <tr key={step.id}>
                      <td>{step.step_index + 1}</td>
                      <td>{step.instruction}</td>
                      <td>
                        {step.tier_used !== undefined
                          ? <TierBadge tier={step.tier_used} xpath_cached={step.xpath_cached} />
                          : '—'}
                      </td>
                      <td>{step.success === true ? '✓' : step.success === false ? '✗' : '—'}</td>
                      <td>{step.duration_ms !== undefined ? step.duration_ms : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

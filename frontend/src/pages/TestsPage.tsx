import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { TestCase, TestCaseCreate } from '../types'
import { getTestCases, createTestCase, deleteTestCase } from '../services/api'
import { StepEditor } from '../components/StepEditor'

export function TestsPage() {
  const [tests, setTests] = useState<TestCase[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<TestCaseCreate>({ title: '', url: '', steps: [] })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    getTestCases()
      .then(setTests)
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async () => {
    setSaving(true)
    try {
      const created = await createTestCase(form)
      setTests((prev) => [...prev, created])
      setShowForm(false)
      setForm({ title: '', url: '', steps: [] })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    await deleteTestCase(id)
    setTests((prev) => prev.filter((t) => t.id !== id))
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Test Cases</h2>
        <button type="button" onClick={() => setShowForm(true)} className="btn-primary">
          + New Test
        </button>
      </div>

      {loading && <p>Loading…</p>}

      {!loading && tests.length === 0 && !showForm && (
        <p className="empty-state">No test cases yet. Create one to get started.</p>
      )}

      <div className="test-list">
        {tests.map((tc) => (
          <div key={tc.id} className="test-card">
            <div className="test-card__header">
              <strong>{tc.title}</strong>
              <span className="test-card__url">{tc.url}</span>
            </div>
            <p className="test-card__steps">{tc.steps.length} step{tc.steps.length !== 1 ? 's' : ''}</p>
            <div className="test-card__actions">
              <button type="button" onClick={() => navigate(`/run?test=${tc.id}`)}>Run</button>
              <button
                type="button"
                onClick={() => handleDelete(tc.id)}
                className="btn-danger"
                aria-label={`Delete ${tc.title}`}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal">
            <h3>New Test Case</h3>
            <label htmlFor="new-test-title">
              Title
              <input
                id="new-test-title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </label>
            <label htmlFor="new-test-url">
              URL
              <input
                id="new-test-url"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
              />
            </label>
            <StepEditor
              steps={form.steps}
              onChange={(steps) => setForm({ ...form, steps })}
            />
            <div className="modal__actions">
              <button type="button" onClick={() => setShowForm(false)}>Cancel</button>
              <button
                type="button"
                onClick={handleCreate}
                disabled={saving || !form.title || !form.url}
                className="btn-primary"
              >
                {saving ? 'Saving…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

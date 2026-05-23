import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { TestCase, TestCaseCreate } from '../types'
import { getTestCases, createTestCase, updateTestCase, deleteTestCase } from '../services/api'
import { StepEditor } from '../components/StepEditor'

type ModalMode = 'create' | 'edit'

const emptyForm = (): TestCaseCreate => ({ title: '', url: '', steps: [] })

export function TestsPage() {
  const [tests, setTests] = useState<TestCase[]>([])
  const [modal, setModal] = useState<{ mode: ModalMode; id?: number } | null>(null)
  const [form, setForm] = useState<TestCaseCreate>(emptyForm())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    getTestCases()
      .then(setTests)
      .finally(() => setLoading(false))
  }, [])

  const openCreate = () => {
    setForm(emptyForm())
    setModal({ mode: 'create' })
  }

  const openEdit = (tc: TestCase) => {
    setForm({ title: tc.title, url: tc.url, steps: tc.steps })
    setModal({ mode: 'edit', id: tc.id })
  }

  const closeModal = () => setModal(null)

  const handleSave = async () => {
    setSaving(true)
    try {
      if (modal?.mode === 'edit' && modal.id !== undefined) {
        const updated = await updateTestCase(modal.id, form)
        setTests((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
      } else {
        const created = await createTestCase(form)
        setTests((prev) => [...prev, created])
      }
      closeModal()
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    await deleteTestCase(id)
    setTests((prev) => prev.filter((t) => t.id !== id))
  }

  const isEdit = modal?.mode === 'edit'

  return (
    <div className="page">
      <div className="page-header">
        <h2>Test Cases</h2>
        <button type="button" onClick={openCreate} className="btn-primary">
          + New Test
        </button>
      </div>

      {loading && <p>Loading…</p>}

      {!loading && tests.length === 0 && !modal && (
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
                onClick={() => openEdit(tc)}
                aria-label={`Edit ${tc.title}`}
              >
                Edit
              </button>
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

      {modal && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal">
            <h3>{isEdit ? 'Edit Test Case' : 'New Test Case'}</h3>
            <label htmlFor="test-title">
              Title
              <input
                id="test-title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </label>
            <label htmlFor="test-url">
              URL
              <input
                id="test-url"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
              />
            </label>
            <StepEditor
              steps={form.steps}
              onChange={(steps) => setForm({ ...form, steps })}
            />
            <div className="modal__actions">
              <button type="button" onClick={closeModal}>Cancel</button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !form.title || !form.url}
                className="btn-primary"
              >
                {saving ? 'Saving…' : isEdit ? 'Save' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

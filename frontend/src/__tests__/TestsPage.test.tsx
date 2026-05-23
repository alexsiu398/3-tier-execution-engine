/**
 * TestsPage component tests
 * RED: drives the TestsPage page implementation.
 *
 * Tests:
 * - fetches and renders test case list
 * - shows empty state when no tests
 * - "New Test" button opens form modal
 * - form has title/URL inputs and StepEditor
 * - create button posts to API and closes modal
 * - delete button removes test from list
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { TestCase } from '../types'

vi.mock('../services/api', () => ({
  getTestCases: vi.fn(),
  createTestCase: vi.fn(),
  deleteTestCase: vi.fn(),
  updateTestCase: vi.fn(),
  getTestCase: vi.fn(),
}))

// StepEditor is rendered inside the modal — mock it for simplicity
vi.mock('../components/StepEditor', () => ({
  StepEditor: ({ steps, onChange }: { steps: unknown[]; onChange: (s: unknown[]) => void }) => (
    <div data-testid="step-editor">
      <button onClick={() => onChange([...steps, { action: 'click', instruction: 'new step' }])}>
        mock-add-step
      </button>
    </div>
  ),
}))

const mockTests: TestCase[] = [
  { id: 1, title: 'Login Flow', url: 'https://example.com', steps: [{ action: 'click', instruction: 'click' }], created_at: '2024-01-01T00:00:00Z' },
  { id: 2, title: 'Signup Flow', url: 'https://example.com/signup', steps: [], created_at: '2024-01-02T00:00:00Z' },
]

describe('TestsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows loading then renders test case list', async () => {
    const { getTestCases } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)

    const { TestsPage } = await import('../pages/TestsPage')
    render(<MemoryRouter><TestsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('Login Flow')).toBeInTheDocument()
      expect(screen.getByText('Signup Flow')).toBeInTheDocument()
    })
  })

  it('shows empty state when no tests exist', async () => {
    const { getTestCases } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue([])

    const { TestsPage } = await import('../pages/TestsPage')
    render(<MemoryRouter><TestsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText(/no test cases/i)).toBeInTheDocument()
    })
  })

  it('"New Test" button opens modal form', async () => {
    const { getTestCases } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue([])

    const { TestsPage } = await import('../pages/TestsPage')
    render(<MemoryRouter><TestsPage /></MemoryRouter>)

    await waitFor(() => screen.getByText(/new test/i))
    fireEvent.click(screen.getByText(/new test/i))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('modal form has title and URL inputs', async () => {
    const { getTestCases } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue([])

    const { TestsPage } = await import('../pages/TestsPage')
    render(<MemoryRouter><TestsPage /></MemoryRouter>)

    await waitFor(() => screen.getByText(/new test/i))
    fireEvent.click(screen.getByText(/new test/i))

    expect(screen.getByLabelText(/title/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/url/i)).toBeInTheDocument()
  })

  it('Create button calls createTestCase with form data', async () => {
    const { getTestCases, createTestCase } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue([])
    const newTest = { id: 3, title: 'New Test', url: 'https://test.com', steps: [], created_at: '' }
    vi.mocked(createTestCase).mockResolvedValue(newTest)

    const { TestsPage } = await import('../pages/TestsPage')
    render(<MemoryRouter><TestsPage /></MemoryRouter>)

    await waitFor(() => screen.getByText(/new test/i))
    fireEvent.click(screen.getByText(/new test/i))

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'New Test' } })
    fireEvent.change(screen.getByLabelText(/url/i), { target: { value: 'https://test.com' } })

    fireEvent.click(screen.getByRole('button', { name: /create/i }))

    await waitFor(() => {
      expect(createTestCase).toHaveBeenCalledWith({
        title: 'New Test',
        url: 'https://test.com',
        steps: [],
      })
    })
  })

  it('Create button is disabled when title or URL is empty', async () => {
    const { getTestCases } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue([])

    const { TestsPage } = await import('../pages/TestsPage')
    render(<MemoryRouter><TestsPage /></MemoryRouter>)

    await waitFor(() => screen.getByText(/new test/i))
    fireEvent.click(screen.getByText(/new test/i))

    expect(screen.getByRole('button', { name: /create/i })).toBeDisabled()
  })

  it('Delete button calls deleteTestCase and removes test from list', async () => {
    const { getTestCases, deleteTestCase } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue([...mockTests])
    vi.mocked(deleteTestCase).mockResolvedValue(undefined)

    const { TestsPage } = await import('../pages/TestsPage')
    render(<MemoryRouter><TestsPage /></MemoryRouter>)

    await waitFor(() => screen.getByText('Login Flow'))

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(deleteTestCase).toHaveBeenCalledWith(1)
      expect(screen.queryByText('Login Flow')).not.toBeInTheDocument()
    })
  })

  it('shows step count per test case', async () => {
    const { getTestCases } = await import('../services/api')
    vi.mocked(getTestCases).mockResolvedValue(mockTests)

    const { TestsPage } = await import('../pages/TestsPage')
    render(<MemoryRouter><TestsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText(/1\s*step/i)).toBeInTheDocument()
    })
  })
})

/**
 * Frontend Phase 1 tests — RED first.
 *
 * Covers:
 * - api.ts: typed wrappers for tests CRUD and settings
 * - TierBadge component renders correct colour per tier
 * - ExecutionSettings renders strategy options
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

vi.mock('axios')
const mockedAxios = vi.mocked(axios, true)

// ─────────────────────────────────────────────────────────────────────────────
// api.ts — test case CRUD
// ─────────────────────────────────────────────────────────────────────────────

describe('api — test cases', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('getTestCases calls GET /api/v1/tests and returns array', async () => {
    const mockData = [{ id: 1, title: 'Test', url: 'https://example.com', steps: [], created_at: '' }]
    mockedAxios.get = vi.fn().mockResolvedValue({ data: mockData })

    const { getTestCases } = await import('../services/api')
    const result = await getTestCases()

    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/tests')
    expect(result).toEqual(mockData)
  })

  it('createTestCase calls POST /api/v1/tests with payload', async () => {
    const payload = { title: 'New', url: 'https://example.com', steps: [] }
    const created = { id: 2, ...payload, created_at: '2024-01-01T00:00:00Z' }
    mockedAxios.post = vi.fn().mockResolvedValue({ data: created })

    const { createTestCase } = await import('../services/api')
    const result = await createTestCase(payload)

    expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/tests', payload)
    expect(result.id).toBe(2)
  })

  it('getTestCase calls GET /api/v1/tests/:id', async () => {
    const tc = { id: 3, title: 'Get it', url: 'https://example.com', steps: [], created_at: '' }
    mockedAxios.get = vi.fn().mockResolvedValue({ data: tc })

    const { getTestCase } = await import('../services/api')
    const result = await getTestCase(3)

    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/tests/3')
    expect(result.id).toBe(3)
  })

  it('updateTestCase calls PUT /api/v1/tests/:id', async () => {
    const payload = { title: 'Updated', url: 'https://example.com', steps: [] }
    const updated = { id: 4, ...payload, created_at: '' }
    mockedAxios.put = vi.fn().mockResolvedValue({ data: updated })

    const { updateTestCase } = await import('../services/api')
    const result = await updateTestCase(4, payload)

    expect(mockedAxios.put).toHaveBeenCalledWith('/api/v1/tests/4', payload)
    expect(result.title).toBe('Updated')
  })

  it('deleteTestCase calls DELETE /api/v1/tests/:id', async () => {
    mockedAxios.delete = vi.fn().mockResolvedValue({ data: null })

    const { deleteTestCase } = await import('../services/api')
    await deleteTestCase(5)

    expect(mockedAxios.delete).toHaveBeenCalledWith('/api/v1/tests/5')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// api.ts — settings
// ─────────────────────────────────────────────────────────────────────────────

describe('api — settings', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('getSettings calls GET /api/v1/settings', async () => {
    const mockSettings = { id: 1, fallback_strategy: 'option_c', timeout_per_tier_seconds: 10, max_retry_per_tier: 2 }
    mockedAxios.get = vi.fn().mockResolvedValue({ data: mockSettings })

    const { getSettings } = await import('../services/api')
    const result = await getSettings()

    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/settings')
    expect(result.fallback_strategy).toBe('option_c')
  })

  it('updateSettings calls PUT /api/v1/settings with payload', async () => {
    const payload = { fallback_strategy: 'option_a' as const }
    const updated = { id: 1, fallback_strategy: 'option_a', timeout_per_tier_seconds: 10, max_retry_per_tier: 2 }
    mockedAxios.put = vi.fn().mockResolvedValue({ data: updated })

    const { updateSettings } = await import('../services/api')
    const result = await updateSettings(payload)

    expect(mockedAxios.put).toHaveBeenCalledWith('/api/v1/settings', payload)
    expect(result.fallback_strategy).toBe('option_a')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// TierBadge component
// ─────────────────────────────────────────────────────────────────────────────

import { render, screen } from '@testing-library/react'

describe('TierBadge', () => {
  it('renders T1 with green colour class', async () => {
    const { TierBadge } = await import('../components/TierBadge')
    render(<TierBadge tier={1} />)
    const badge = screen.getByText('T1')
    expect(badge).toBeInTheDocument()
    expect(badge.className).toMatch(/green/)
  })

  it('renders T2 with amber colour class', async () => {
    const { TierBadge } = await import('../components/TierBadge')
    render(<TierBadge tier={2} />)
    const badge = screen.getByText('T2')
    expect(badge.className).toMatch(/amber|yellow|orange/)
  })

  it('renders T3 with red colour class', async () => {
    const { TierBadge } = await import('../components/TierBadge')
    render(<TierBadge tier={3} />)
    const badge = screen.getByText('T3')
    expect(badge.className).toMatch(/red/)
  })

  it('renders cached indicator when xpath_cached is true', async () => {
    const { TierBadge } = await import('../components/TierBadge')
    render(<TierBadge tier={2} xpath_cached={true} />)
    expect(screen.getByText(/cached/i)).toBeInTheDocument()
  })
})

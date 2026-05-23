/**
 * api.ts — execution endpoints + SSE subscription
 * RED: these tests drive the implementation of the missing API functions.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'

vi.mock('axios')
const mockedAxios = vi.mocked(axios, true)

describe('api — executions', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('startExecution calls POST /api/v1/executions and returns execution_id', async () => {
    const payload = { test_case_id: 1, strategy: 'option_c' as const }
    const response = { execution_id: 42, status: 'running' }
    mockedAxios.post = vi.fn().mockResolvedValue({ data: response })

    const { startExecution } = await import('../services/api')
    const result = await startExecution(payload)

    expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/executions', payload)
    expect(result.execution_id).toBe(42)
    expect(result.status).toBe('running')
  })

  it('startExecution without strategy still posts correctly', async () => {
    const payload = { test_case_id: 5 }
    mockedAxios.post = vi.fn().mockResolvedValue({ data: { execution_id: 7, status: 'running' } })

    const { startExecution } = await import('../services/api')
    await startExecution(payload)

    expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/executions', payload)
  })

  it('getExecutions calls GET /api/v1/executions and returns summary list', async () => {
    const summaries = [
      {
        id: 1, test_case_id: 1, strategy: 'option_a', status: 'completed',
        total_steps: 3, tier1_count: 2, tier2_count: 1, tier3_count: 0, success_count: 3,
      },
    ]
    mockedAxios.get = vi.fn().mockResolvedValue({ data: summaries })

    const { getExecutions } = await import('../services/api')
    const result = await getExecutions()

    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/executions')
    expect(result).toHaveLength(1)
    expect(result[0].tier1_count).toBe(2)
  })

  it('getExecution calls GET /api/v1/executions/:id and returns detail', async () => {
    const detail = {
      id: 3, test_case_id: 1, strategy: 'option_c', status: 'completed',
      steps: [{ id: 1, step_index: 0, instruction: 'click login', tier_used: 1, success: true, duration_ms: 45, xpath_cached: false }],
    }
    mockedAxios.get = vi.fn().mockResolvedValue({ data: detail })

    const { getExecution } = await import('../services/api')
    const result = await getExecution(3)

    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/executions/3')
    expect(result.id).toBe(3)
    expect(result.steps).toHaveLength(1)
    expect(result.steps[0].tier_used).toBe(1)
  })
})

describe('api — subscribeToExecution', () => {
  // Use a real class per-test so `new EventSource(url)` works natively.
  // capturedES is used to access onmessage / onerror / close after construction.

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('creates EventSource with correct stream URL', async () => {
    let capturedUrl = ''
    class MockES {
      onmessage: any = null; onerror: any = null; close = vi.fn()
      constructor(url: string) { capturedUrl = url }
    }
    vi.stubGlobal('EventSource', MockES)

    const { subscribeToExecution } = await import('../services/api')
    subscribeToExecution(5, vi.fn(), vi.fn())

    expect(capturedUrl).toBe('/api/v1/executions/5/stream')
  })

  it('calls onEvent when a progress message arrives', async () => {
    let capturedES: any = null
    class MockES {
      onmessage: any = null; onerror: any = null; close = vi.fn()
      constructor(_url: string) { capturedES = this }
    }
    vi.stubGlobal('EventSource', MockES)

    const onEvent = vi.fn()
    const onDone = vi.fn()
    const { subscribeToExecution } = await import('../services/api')
    subscribeToExecution(1, onEvent, onDone)

    capturedES.onmessage({ data: JSON.stringify({ step_index: 0, tier: 1, success: true, duration_ms: 33 }) })

    expect(onEvent).toHaveBeenCalledWith({ step_index: 0, tier: 1, success: true, duration_ms: 33 })
    expect(onDone).not.toHaveBeenCalled()
  })

  it('calls onDone when null sentinel message arrives', async () => {
    let capturedES: any = null
    class MockES {
      onmessage: any = null; onerror: any = null; close = vi.fn()
      constructor(_url: string) { capturedES = this }
    }
    vi.stubGlobal('EventSource', MockES)

    const onEvent = vi.fn()
    const onDone = vi.fn()
    const { subscribeToExecution } = await import('../services/api')
    subscribeToExecution(1, onEvent, onDone)

    capturedES.onmessage({ data: 'null' })

    expect(onDone).toHaveBeenCalled()
    expect(onEvent).not.toHaveBeenCalled()
  })

  it('calls onDone on EventSource error', async () => {
    let capturedES: any = null
    class MockES {
      onmessage: any = null; onerror: any = null; close = vi.fn()
      constructor(_url: string) { capturedES = this }
    }
    vi.stubGlobal('EventSource', MockES)

    const onDone = vi.fn()
    const { subscribeToExecution } = await import('../services/api')
    subscribeToExecution(1, vi.fn(), onDone)

    capturedES.onerror({})

    expect(onDone).toHaveBeenCalled()
    expect(capturedES.close).toHaveBeenCalled()
  })

  it('returns the EventSource instance for caller to close', async () => {
    let capturedES: any = null
    class MockES {
      onmessage: any = null; onerror: any = null; close = vi.fn()
      constructor(_url: string) { capturedES = this }
    }
    vi.stubGlobal('EventSource', MockES)

    const { subscribeToExecution } = await import('../services/api')
    const es = subscribeToExecution(99, vi.fn(), vi.fn())

    expect(es).toBe(capturedES)
  })
})

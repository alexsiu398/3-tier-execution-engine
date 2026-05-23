import axios from 'axios'
import type {
  TestCase,
  TestCaseCreate,
  ExecutionSettings,
  ExecutionSettingsUpdate,
  ExecutionCreate,
  ExecutionStartResponse,
  ExecutionSummary,
  Execution,
  SSEProgressEvent,
} from '../types'

export async function getTestCases(): Promise<TestCase[]> {
  const { data } = await axios.get<TestCase[]>('/api/v1/tests')
  return data
}

export async function createTestCase(payload: TestCaseCreate): Promise<TestCase> {
  const { data } = await axios.post<TestCase>('/api/v1/tests', payload)
  return data
}

export async function getTestCase(id: number): Promise<TestCase> {
  const { data } = await axios.get<TestCase>(`/api/v1/tests/${id}`)
  return data
}

export async function updateTestCase(id: number, payload: TestCaseCreate): Promise<TestCase> {
  const { data } = await axios.put<TestCase>(`/api/v1/tests/${id}`, payload)
  return data
}

export async function deleteTestCase(id: number): Promise<void> {
  await axios.delete(`/api/v1/tests/${id}`)
}

export async function getSettings(): Promise<ExecutionSettings> {
  const { data } = await axios.get<ExecutionSettings>('/api/v1/settings')
  return data
}

export async function updateSettings(payload: ExecutionSettingsUpdate): Promise<ExecutionSettings> {
  const { data } = await axios.put<ExecutionSettings>('/api/v1/settings', payload)
  return data
}

export async function startExecution(payload: ExecutionCreate): Promise<ExecutionStartResponse> {
  const { data } = await axios.post<ExecutionStartResponse>('/api/v1/executions', payload)
  return data
}

export async function getExecutions(): Promise<ExecutionSummary[]> {
  const { data } = await axios.get<ExecutionSummary[]>('/api/v1/executions')
  return data
}

export async function getExecution(id: number): Promise<Execution> {
  const { data } = await axios.get<Execution>(`/api/v1/executions/${id}`)
  return data
}

export function subscribeToExecution(
  executionId: number,
  onEvent: (event: SSEProgressEvent) => void,
  onDone: () => void,
): EventSource {
  const es = new EventSource(`/api/v1/executions/${executionId}/stream`)
  es.onmessage = (e: MessageEvent) => {
    const data = JSON.parse(e.data as string)
    if (data === null) {
      onDone()
      return
    }
    onEvent(data as SSEProgressEvent)
  }
  es.onerror = () => {
    onDone()
    es.close()
  }
  return es
}

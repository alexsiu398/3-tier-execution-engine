import axios from 'axios'
import type { TestCase, TestCaseCreate, ExecutionSettings, ExecutionSettingsUpdate } from '../types'

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

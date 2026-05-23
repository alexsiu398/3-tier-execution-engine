export type StepAction =
  | 'navigate'
  | 'click'
  | 'fill'
  | 'press'
  | 'assert_text'
  | 'assert_url'

export interface TestStep {
  action: StepAction
  instruction: string
  selector?: string
  value?: string
}

export interface TestCase {
  id: number
  title: string
  url: string
  steps: TestStep[]
  created_at: string
}

export interface TestCaseCreate {
  title: string
  url: string
  steps: TestStep[]
}

export interface ExecutionSettings {
  id: number
  fallback_strategy: 'option_a' | 'option_b' | 'option_c'
  timeout_per_tier_seconds: number
  max_retry_per_tier: number
}

export interface ExecutionSettingsUpdate {
  fallback_strategy: 'option_a' | 'option_b' | 'option_c'
  timeout_per_tier_seconds?: number
  max_retry_per_tier?: number
}

export interface ExecutionCreate {
  test_case_id: number
  strategy?: 'option_a' | 'option_b' | 'option_c'
}

export interface ExecutionStartResponse {
  execution_id: number
  status: string
}

export interface ExecutionStep {
  id: number
  step_index: number
  instruction: string
  tier_used?: 1 | 2 | 3
  success?: boolean
  duration_ms?: number
  error?: string
  xpath_cached: boolean
}

export interface Execution {
  id: number
  test_case_id: number
  strategy: 'option_a' | 'option_b' | 'option_c'
  status: string
  started_at?: string
  finished_at?: string
  steps: ExecutionStep[]
}

export interface ExecutionSummary {
  id: number
  test_case_id: number
  strategy: 'option_a' | 'option_b' | 'option_c'
  status: string
  started_at?: string
  finished_at?: string
  total_steps: number
  tier1_count: number
  tier2_count: number
  tier3_count: number
  success_count: number
}

export interface SSEProgressEvent {
  step_index: number
  tier: 1 | 2 | 3
  success: boolean
  duration_ms: number
  instruction?: string
  error?: string
  xpath_cached?: boolean
}

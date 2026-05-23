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

/**
 * TierAnalyticsChart component tests
 * RED: drives the TierAnalyticsChart component implementation.
 *
 * recharts is mocked to avoid SVG/ResizeObserver issues in jsdom.
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { ExecutionSummary } from '../types'

// Mock recharts modules to avoid SVG measurement errors in jsdom
vi.mock('recharts', () => ({
  BarChart: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
    <div data-testid="bar-chart" data-items={data.length}>{children}</div>
  ),
  Bar: ({ dataKey, fill }: { dataKey: string; fill: string }) => (
    <div data-testid={`bar-${dataKey}`} data-fill={fill} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}))

const sampleExecutions: ExecutionSummary[] = [
  {
    id: 1, test_case_id: 1, strategy: 'option_c', status: 'completed',
    total_steps: 4, tier1_count: 3, tier2_count: 1, tier3_count: 0, success_count: 4,
  },
  {
    id: 2, test_case_id: 2, strategy: 'option_a', status: 'completed',
    total_steps: 2, tier1_count: 1, tier2_count: 0, tier3_count: 1, success_count: 1,
  },
]

describe('TierAnalyticsChart', () => {
  it('renders the responsive container wrapper', async () => {
    const { TierAnalyticsChart } = await import('../components/TierAnalyticsChart')
    render(<TierAnalyticsChart executions={sampleExecutions} />)

    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('renders BarChart with correct number of data points', async () => {
    const { TierAnalyticsChart } = await import('../components/TierAnalyticsChart')
    render(<TierAnalyticsChart executions={sampleExecutions} />)

    const chart = screen.getByTestId('bar-chart')
    expect(chart).toHaveAttribute('data-items', '2')
  })

  it('renders three Bar elements (Tier 1, 2, 3)', async () => {
    const { TierAnalyticsChart } = await import('../components/TierAnalyticsChart')
    render(<TierAnalyticsChart executions={sampleExecutions} />)

    expect(screen.getByTestId('bar-Tier 1')).toBeInTheDocument()
    expect(screen.getByTestId('bar-Tier 2')).toBeInTheDocument()
    expect(screen.getByTestId('bar-Tier 3')).toBeInTheDocument()
  })

  it('uses green fill for Tier 1 bar', async () => {
    const { TierAnalyticsChart } = await import('../components/TierAnalyticsChart')
    render(<TierAnalyticsChart executions={sampleExecutions} />)

    const tier1Bar = screen.getByTestId('bar-Tier 1')
    expect(tier1Bar.getAttribute('data-fill')).toMatch(/#22c55e|green/i)
  })

  it('uses amber/yellow fill for Tier 2 bar', async () => {
    const { TierAnalyticsChart } = await import('../components/TierAnalyticsChart')
    render(<TierAnalyticsChart executions={sampleExecutions} />)

    const tier2Bar = screen.getByTestId('bar-Tier 2')
    expect(tier2Bar.getAttribute('data-fill')).toMatch(/#f59e0b|amber|yellow|orange/i)
  })

  it('uses red fill for Tier 3 bar', async () => {
    const { TierAnalyticsChart } = await import('../components/TierAnalyticsChart')
    render(<TierAnalyticsChart executions={sampleExecutions} />)

    const tier3Bar = screen.getByTestId('bar-Tier 3')
    expect(tier3Bar.getAttribute('data-fill')).toMatch(/#ef4444|red/i)
  })

  it('renders empty chart with no executions', async () => {
    const { TierAnalyticsChart } = await import('../components/TierAnalyticsChart')
    render(<TierAnalyticsChart executions={[]} />)

    const chart = screen.getByTestId('bar-chart')
    expect(chart).toHaveAttribute('data-items', '0')
  })
})

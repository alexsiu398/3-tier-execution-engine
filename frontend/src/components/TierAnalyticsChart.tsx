import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { ExecutionSummary } from '../types'

interface TierAnalyticsChartProps {
  executions: ExecutionSummary[]
}

export function TierAnalyticsChart({ executions }: TierAnalyticsChartProps) {
  const data = executions.map((e) => ({
    id: `#${e.id}`,
    'Tier 1': e.tier1_count,
    'Tier 2': e.tier2_count,
    'Tier 3': e.tier3_count,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <XAxis dataKey="id" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="Tier 1" fill="#22c55e" stackId="tiers" />
        <Bar dataKey="Tier 2" fill="#f59e0b" stackId="tiers" />
        <Bar dataKey="Tier 3" fill="#ef4444" stackId="tiers" />
      </BarChart>
    </ResponsiveContainer>
  )
}

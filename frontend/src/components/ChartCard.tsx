import ReactECharts from 'echarts-for-react'
import type { ChartSpec } from '../types'

function toOption(spec: ChartSpec) {
  const xAxis = spec.xAxis ?? []
  const series = spec.series ?? []
  const base = {
    title: spec.title ? { text: spec.title } : undefined,
    tooltip: {},
  }
  if (spec.type === 'pie') {
    return {
      ...base,
      series: [
        {
          type: 'pie',
          radius: '60%',
          data: xAxis.map((name, index) => ({ name, value: series[index] })),
        },
      ],
    }
  }
  return {
    ...base,
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: xAxis },
    yAxis: { type: 'value' },
    series: [{ type: spec.type, data: series }],
  }
}

export default function ChartCard({ spec }: { spec: ChartSpec }) {
  return <ReactECharts option={toOption(spec)} style={{ height: 320 }} notMerge />
}

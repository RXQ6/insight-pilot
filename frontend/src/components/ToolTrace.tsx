import { Collapse } from 'antd'
import type { ToolCallEvent } from '../types'

export default function ToolTrace({ items }: { items: ToolCallEvent[] }) {
  if (items.length === 0) {
    return null
  }
  return (
    <Collapse
      size="small"
      items={items.map((item, index) => ({
        key: index,
        label: `${item.name ?? 'tool'} ${item.status ?? ''}`,
        children: <pre>{JSON.stringify(item.arguments ?? {}, null, 2)}</pre>,
      }))}
    />
  )
}

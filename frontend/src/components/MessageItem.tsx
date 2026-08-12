import { Tag } from 'antd'
import ReactMarkdown from 'react-markdown'
import type { Message } from '../types'
import ChartCard from './ChartCard'

export default function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`message-row ${message.role}`}>
      <Tag color={isUser ? 'blue' : 'green'}>{isUser ? '用户' : 'Agent'}</Tag>
      <div className="message-content">
        <ReactMarkdown>{message.content}</ReactMarkdown>
        {message.chart ? <ChartCard spec={message.chart} /> : null}
      </div>
    </div>
  )
}

import { Spin } from 'antd'
import type { Message } from '../types'
import MessageItem from './MessageItem'

interface MessageListProps {
  messages: Message[]
  streaming: string
  running: boolean
}

export default function MessageList({ messages, streaming, running }: MessageListProps) {
  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <MessageItem key={`${message.createdAt}-${index}`} message={message} />
      ))}
      {running && streaming ? (
        <div className="message-row assistant">
          <span className="streaming-text">{streaming}</span>
          <Spin size="small" />
        </div>
      ) : null}
      {messages.length === 0 && !running ? (
        <div className="empty-tip">输入一个问题，InsightPilot 会自主查数、分析并生成图表</div>
      ) : null}
    </div>
  )
}

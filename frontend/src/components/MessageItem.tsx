import { Button, Tag } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import type { Message } from '../types'
import ChartCard from './ChartCard'

function fileHref(file: { mime: string; contentBase64: string }): string {
  return `data:${file.mime};base64,${file.contentBase64}`
}

export default function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`message-row ${message.role}`}>
      <Tag color={isUser ? 'blue' : 'green'}>{isUser ? '用户' : 'Agent'}</Tag>
      <div className="message-content">
        <ReactMarkdown>{message.content}</ReactMarkdown>
        {message.chart ? <ChartCard spec={message.chart} /> : null}
        {message.file ? (
          <div className="file-download">
            <Button
              type="primary"
              size="small"
              icon={<DownloadOutlined />}
              href={fileHref(message.file)}
              download={message.file.filename}
            >
              下载 {message.file.filename}
              {message.file.rowCount ? `（${message.file.rowCount} 行）` : ''}
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  )
}

import { Button, Tag, message as antdMessage } from 'antd'
import { DownloadOutlined, LikeOutlined, DislikeOutlined } from '@ant-design/icons'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { taskApi } from '../api/tasks'
import type { Message } from '../types'
import ChartCard from './ChartCard'

function fileHref(file: { mime: string; contentBase64: string }): string {
  return `data:${file.mime};base64,${file.contentBase64}`
}

export default function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const [feedbackSent, setFeedbackSent] = useState<boolean | null>(null)

  const sendFeedback = async (helpful: boolean) => {
    if (!message.taskId || feedbackSent !== null) {
      return
    }
    try {
      await taskApi.feedback(message.taskId, helpful)
      setFeedbackSent(helpful)
      antdMessage.success(helpful ? '已标记为有用' : '已标记为需要改进')
    } catch {
      antdMessage.error('反馈提交失败')
    }
  }

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
        {!isUser && message.taskId ? (
          <div className="feedback-buttons">
            <Button
              size="small"
              type={feedbackSent === true ? 'primary' : 'text'}
              icon={<LikeOutlined />}
              onClick={() => sendFeedback(true)}
              disabled={feedbackSent !== null}
            >
              有用
            </Button>
            <Button
              size="small"
              type={feedbackSent === false ? 'primary' : 'text'}
              icon={<DislikeOutlined />}
              onClick={() => sendFeedback(false)}
              disabled={feedbackSent !== null}
            >
              不准确
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  )
}

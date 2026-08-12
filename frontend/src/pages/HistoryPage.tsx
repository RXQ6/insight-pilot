import { Button, List, Typography, message } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { sessionApi } from '../api/sessions'
import type { Session } from '../types'

export default function HistoryPage() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<Session[]>([])

  const load = async () => {
    setSessions(await sessionApi.list())
  }

  useEffect(() => {
    load()
  }, [])

  const remove = async (sessionId: number) => {
    await sessionApi.remove(sessionId)
    message.success('已删除')
    await load()
  }

  return (
    <div className="plain-page">
      <Typography.Title level={4}>历史会话</Typography.Title>
      <Button onClick={() => navigate('/')} style={{ marginBottom: 16 }}>
        返回工作台
      </Button>
      <List
        bordered
        dataSource={sessions}
        renderItem={(session) => (
          <List.Item
            actions={[
              <Button key="open" type="link" onClick={() => navigate(`/?session=${session.sessionId}`)}>
                打开
              </Button>,
              <Button key="delete" danger type="link" onClick={() => remove(session.sessionId)}>
                删除
              </Button>,
            ]}
          >
            <Typography.Text>{session.title}</Typography.Text>
            <Typography.Text type="secondary">
              {session.messageCount} 条消息
            </Typography.Text>
          </List.Item>
        )}
      />
    </div>
  )
}

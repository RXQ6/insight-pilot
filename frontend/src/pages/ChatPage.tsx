import { Layout, Typography } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { sessionApi } from '../api/sessions'
import ApprovalModal from '../components/ApprovalModal'
import ChatInput from '../components/ChatInput'
import MessageList from '../components/MessageList'
import Sidebar from '../components/Sidebar'
import ToolTrace from '../components/ToolTrace'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import type { Session } from '../types'

const EXAMPLES = [
  '2026年4月订单总数是多少？',
  '用柱状图展示各区域销售额',
  '退款订单怎么排查',
]

export default function ChatPage() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const chat = useChatStore()
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)

  const loadSessions = async () => {
    setSessions(await sessionApi.list())
  }

  useEffect(() => {
    loadSessions()
  }, [])

  const openSession = async (sessionId: number) => {
    setActiveId(sessionId)
    await chat.loadMessages(sessionId)
  }

  const createSession = async () => {
    const session = await sessionApi.create(`会话 ${sessions.length + 1}`)
    setSessions([session, ...sessions])
    await openSession(session.sessionId)
  }

  const deleteSession = async (sessionId: number) => {
    await sessionApi.remove(sessionId)
    if (activeId === sessionId) {
      chat.clear()
      setActiveId(null)
    }
    await loadSessions()
  }

  const activeSession = useMemo(
    () => sessions.find((session) => session.sessionId === activeId) ?? null,
    [sessions, activeId],
  )
  const running = chat.status === 'running' || chat.status === 'pending' || chat.status === 'waiting_approval'

  return (
    <Layout className="app-layout">
      <Layout.Sider width={260} theme="light">
        <Sidebar
          sessions={sessions}
          activeId={activeId}
          onSelect={openSession}
          onCreate={createSession}
          onDelete={deleteSession}
        />
      </Layout.Sider>
      <Layout.Content className="chat-content">
        <div className="chat-header">
          <Typography.Title level={4} style={{ margin: 0 }}>
            {activeSession?.title ?? '数据分析工作台'}
          </Typography.Title>
          <Typography.Text type="secondary">状态：{chat.status}</Typography.Text>
          <Typography.Link onClick={() => navigate('/history')}>历史</Typography.Link>
          <Typography.Link onClick={() => navigate('/eval')}>评测</Typography.Link>
          <Typography.Link onClick={logout}>退出</Typography.Link>
        </div>
        {chat.messages.length === 0 ? (
          <div className="example-grid">
            {EXAMPLES.map((question) => (
              <button
                key={question}
                className="example-chip"
                disabled={!activeId || running}
                onClick={() => activeId && chat.send(activeId, question)}
              >
                {question}
              </button>
            ))}
          </div>
        ) : null}
        <MessageList
          messages={chat.messages}
          streaming={chat.streaming}
          running={running && !!chat.streaming}
        />
        <ToolTrace items={chat.toolCalls} />
        <ChatInput
          disabled={!activeId || running}
          onSend={(text) => activeId && chat.send(activeId, text)}
        />
      </Layout.Content>
      <ApprovalModal
        open={!!chat.approval}
        reason={chat.approval?.reason ?? ''}
        onResolve={chat.resolveApproval}
      />
    </Layout>
  )
}

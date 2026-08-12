import { Button, List, Typography } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import type { Session } from '../types'

interface SidebarProps {
  sessions: Session[]
  activeId: number | null
  onSelect: (sessionId: number) => void
  onCreate: () => void
  onDelete: (sessionId: number) => void
}

export default function Sidebar({ sessions, activeId, onSelect, onCreate, onDelete }: SidebarProps) {
  return (
    <div className="sidebar">
      <Button
        type="primary"
        block
        icon={<PlusOutlined />}
        onClick={onCreate}
        style={{ marginBottom: 12 }}
      >
        新建会话
      </Button>
      <List
        size="small"
        dataSource={sessions}
        renderItem={(session) => (
          <List.Item
            className={session.sessionId === activeId ? 'session-item active' : 'session-item'}
            onClick={() => onSelect(session.sessionId)}
            actions={[
              <Button
                key="delete"
                size="small"
                danger
                type="text"
                onClick={(event) => {
                  event.stopPropagation()
                  onDelete(session.sessionId)
                }}
              >
                删除
              </Button>,
            ]}
          >
            <Typography.Text ellipsis>{session.title}</Typography.Text>
          </List.Item>
        )}
      />
    </div>
  )
}

import { Button, Input } from 'antd'
import { useState } from 'react'

interface ChatInputProps {
  disabled: boolean
  onSend: (text: string) => void
}

export default function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [text, setText] = useState('')

  const submit = () => {
    const value = text.trim()
    if (!value || disabled) {
      return
    }
    onSend(value)
    setText('')
  }

  return (
    <div className="chat-input">
      <Input.TextArea
        value={text}
        onChange={(event) => setText(event.target.value)}
        onPressEnter={(event) => {
          if (!event.shiftKey) {
            event.preventDefault()
            submit()
          }
        }}
        placeholder="例如：对比 7 月华东和华南的销售额并给出图表"
        autoSize={{ minRows: 2, maxRows: 6 }}
      />
      <Button type="primary" onClick={submit} disabled={disabled || !text.trim()}>
        发送
      </Button>
    </div>
  )
}

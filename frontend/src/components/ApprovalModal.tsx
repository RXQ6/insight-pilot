import { Modal } from 'antd'

interface ApprovalModalProps {
  open: boolean
  reason: string
  onResolve: (approved: boolean) => void
}

export default function ApprovalModal({ open, reason, onResolve }: ApprovalModalProps) {
  return (
    <Modal
      open={open}
      title="需要人工确认"
      okText="允许执行"
      cancelText="拒绝"
      onOk={() => onResolve(true)}
      onCancel={() => onResolve(false)}
    >
      <p>{reason}</p>
    </Modal>
  )
}

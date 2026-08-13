import { Button, Card, List, Modal, Switch, Table, Typography, Upload, message } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { datasetApi } from '../api/datasets'
import type { Dataset, PreviewResponse } from '../types'

export default function DataPage() {
  const navigate = useNavigate()
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [demoEnabled, setDemoEnabled] = useState(false)
  const [preview, setPreview] = useState<PreviewResponse | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [uploading, setUploading] = useState(false)

  const load = async () => {
    setDatasets(await datasetApi.list())
    setDemoEnabled(await datasetApi.demo.get())
  }

  useEffect(() => {
    load()
  }, [])

  const toggleDemo = async (enabled: boolean) => {
    setDemoEnabled(await datasetApi.demo.set(enabled))
    message.success(enabled ? '示例数据集已启用' : '示例数据集已关闭')
  }

  const beforeUpload = async (file: File) => {
    setUploading(true)
    try {
      await datasetApi.upload(file)
      message.success('上传成功')
      await load()
    } catch {
      message.error('上传失败')
    } finally {
      setUploading(false)
    }
    return false
  }

  const openPreview = async (id: number) => {
    setPreview(await datasetApi.preview(id))
    setPreviewOpen(true)
  }

  const remove = async (id: number) => {
    await datasetApi.remove(id)
    message.success('已删除')
    await load()
  }

  const columns = (preview?.columns ?? []).map((col) => ({ title: col, dataIndex: col, key: col }))
  const rows = preview?.rows ?? []

  return (
    <div className="plain-page">
      <Typography.Title level={4}>我的数据</Typography.Title>
      <Button onClick={() => navigate('/')} style={{ marginBottom: 16 }}>
        返回工作台
      </Button>

      <Card title="示例数据集" style={{ marginBottom: 16 }}>
        <Typography.Paragraph>
          内置的演示订单数据，启用后可用于体验。关闭后 Agent 不再查询示例数据。
        </Typography.Paragraph>
        <Switch checked={demoEnabled} onChange={toggleDemo} checkedChildren="已启用" unCheckedChildren="已关闭" />
        <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
          {demoEnabled ? '示例数据可用' : '示例数据不可用，上传 CSV 后使用自己的数据'}
        </Typography.Text>
      </Card>

      <Card title="上传自己的数据" style={{ marginBottom: 16 }}>
        <Upload.Dragger beforeUpload={beforeUpload} showUploadList={false} disabled={uploading} accept=".csv">
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽 CSV 文件上传</p>
          <p className="ant-upload-hint">上传后可以用自然语言分析自己的数据</p>
        </Upload.Dragger>
      </Card>

      <List
        bordered
        dataSource={datasets}
        renderItem={(item) => (
          <List.Item
            actions={[
              <Button key="preview" type="link" onClick={() => openPreview(item.id)}>
                预览
              </Button>,
              <Button key="delete" danger type="link" onClick={() => remove(item.id)}>
                删除
              </Button>,
            ]}
          >
            <Typography.Text>{item.name}</Typography.Text>
            <Typography.Text type="secondary">{item.rowCount} 行</Typography.Text>
          </List.Item>
        )}
      />
      <Modal open={previewOpen} title="数据预览" footer={null} onCancel={() => setPreviewOpen(false)} width={800}>
        <Table columns={columns} dataSource={rows.map((row, index) => ({ key: index, ...row }))} pagination={false} scroll={{ x: true }} />
      </Modal>
    </div>
  )
}
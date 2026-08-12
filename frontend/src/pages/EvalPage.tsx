import { Button, Card, Col, Row, Statistic, Typography, message } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { EvalSummary } from '../types'

export default function EvalPage() {
  const navigate = useNavigate()
  const [summary, setSummary] = useState<EvalSummary | null>(null)

  useEffect(() => {
    api
      .get<EvalSummary>('/eval/summary')
      .then((response) => setSummary(response.data))
      .catch(() => message.error('评测数据加载失败'))
  }, [])

  return (
    <div className="plain-page">
      <Typography.Title level={4}>评测看板</Typography.Title>
      <Button onClick={() => navigate('/')} style={{ marginBottom: 16 }}>
        返回工作台
      </Button>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="用例总数" value={summary?.total ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="通过数" value={summary?.passed ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="SQL 准确率" value={summary?.sqlAccuracy ?? 0} precision={2} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="平均成本（元）" value={summary?.avgCostCny ?? 0} precision={4} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

import { Button, Form, Input, Tabs, Typography, message } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const register = useAuthStore((state) => state.register)
  const [loading, setLoading] = useState(false)

  const submit = async (mode: 'login' | 'register', values: { username: string; password: string }) => {
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(values.username, values.password)
        navigate('/')
      } else {
        await register(values.username, values.password)
        message.success('注册成功，请登录')
      }
    } catch {
      message.error('操作失败，请检查输入')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <Typography.Title level={2}>InsightPilot</Typography.Title>
        <Typography.Paragraph type="secondary">数据分析 Agent 工作台</Typography.Paragraph>
        <Tabs
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form layout="vertical" onFinish={(values) => submit('login', values)}>
                  <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                    <Input.Password />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    登录
                  </Button>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form layout="vertical" onFinish={(values) => submit('register', values)}>
                  <Form.Item name="username" label="用户名" rules={[{ required: true, min: 3 }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    label="密码"
                    rules={[{ required: true, min: 8 }]}
                  >
                    <Input.Password />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    注册
                  </Button>
                </Form>
              ),
            },
          ]}
        />
      </div>
    </div>
  )
}

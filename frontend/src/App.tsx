import { Navigate, Route, Routes } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import DataPage from './pages/DataPage'
import EvalPage from './pages/EvalPage'
import HistoryPage from './pages/HistoryPage'
import LoginPage from './pages/LoginPage'
import { useAuthStore } from './stores/auth'

function Protected({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((state) => state.token)
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <ChatPage />
          </Protected>
        }
      />
      <Route path="/data" element={<Protected><DataPage /></Protected>} />
      <Route
        path="/history"
        element={
          <Protected>
            <HistoryPage />
          </Protected>
        }
      />
      <Route
        path="/eval"
        element={
          <Protected>
            <EvalPage />
          </Protected>
        }
      />
    </Routes>
  )
}

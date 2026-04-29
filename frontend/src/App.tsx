import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import JobsPage from './pages/JobsPage'
import EvalPage from './pages/EvalPage'
import MemoryPage from './pages/MemoryPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/jobs" replace />} />
          <Route path="jobs"   element={<JobsPage />} />
          <Route path="eval"   element={<EvalPage />} />
          <Route path="memory" element={<MemoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

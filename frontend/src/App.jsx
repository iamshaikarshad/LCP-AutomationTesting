import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('user')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })

  const handleLogin = (userData) => {
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/projects" replace /> : <Login onLogin={handleLogin} />}
        />
        <Route
          path="/projects"
          element={user ? <Projects user={user} onLogout={handleLogout} /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/projects/:id"
          element={user ? <ProjectDetail user={user} onLogout={handleLogout} /> : <Navigate to="/login" replace />}
        />
        <Route path="*" element={<Navigate to={user ? '/projects' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

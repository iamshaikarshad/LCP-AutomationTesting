import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Projects({ user, onLogout }) {
  const [projects, setProjects] = useState([])
  const [newName, setNewName] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    setLoading(true)
    try {
      const data = await api.listProjects(user.id)
      setProjects(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    setError('')
    try {
      await api.createProject(newName.trim(), user.id)
      setNewName('')
      await loadProjects()
    } catch (e) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="container">
      <header>
        <h1>PDF Manager</h1>
        <div className="user-info">
          <span>Hello, <strong>{user.name}</strong></span>
          <button className="secondary" onClick={onLogout}>Log Out</button>
        </div>
      </header>

      <section>
        <h2>Projects</h2>

        <div className="create-row">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="New project name…"
            maxLength={200}
          />
          <button onClick={handleCreate} disabled={creating || !newName.trim()}>
            {creating ? 'Creating…' : 'Create Project'}
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        {loading ? (
          <p className="muted">Loading…</p>
        ) : projects.length === 0 ? (
          <p className="empty">No projects yet. Create one above.</p>
        ) : (
          <ul className="project-list">
            {projects.map((p) => (
              <li key={p.id} onClick={() => navigate(`/projects/${p.id}`)}>
                <span className="project-name">{p.name}</span>
                <span className="project-date">
                  {new Date(p.created_at).toLocaleDateString()}
                </span>
                {p.owner_id === user.id && <span className="badge">Owner</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

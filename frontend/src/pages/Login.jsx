import { useState } from 'react'
import { api } from '../api'

export default function Login({ onLogin }) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const withLoading = async (fn) => {
    setLoading(true)
    setError('')
    try {
      await fn()
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = () =>
    withLoading(async () => {
      try {
        const user = await api.searchUser(name.trim())
        onLogin(user)
      } catch (e) {
        setError(e.message === 'User not found'
          ? 'No user found with that name. Try creating a new account.'
          : e.message)
      }
    })

  const handleCreate = () =>
    withLoading(async () => {
      try {
        const user = await api.createUser(name.trim())
        onLogin(user)
      } catch (e) {
        setError(e.message)
      }
    })

  const disabled = loading || !name.trim()

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>PDF Manager</h1>
        <p className="subtitle">Enter your name to continue</p>

        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !disabled && handleLogin()}
          placeholder="Your name"
          autoFocus
          maxLength={100}
        />

        {error && <p className="error">{error}</p>}

        <div className="button-row">
          <button onClick={handleLogin} disabled={disabled}>
            Log In
          </button>
          <button onClick={handleCreate} disabled={disabled} className="secondary">
            Create Account
          </button>
        </div>
      </div>
    </div>
  )
}

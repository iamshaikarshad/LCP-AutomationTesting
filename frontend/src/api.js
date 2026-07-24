const BASE = 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  // ── Users ──────────────────────────────────────────────────────────────
  searchUser: (name) =>
    request(`/users/search?name=${encodeURIComponent(name)}`),

  createUser: (name) =>
    request('/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }),

  listUsers: () => request('/users'),

  // ── Projects ───────────────────────────────────────────────────────────
  listProjects: (userId) =>
    request(`/projects?user_id=${userId}`),

  createProject: (name, userId) =>
    request('/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, user_id: userId }),
    }),

  getProject: (projectId, userId) =>
    request(`/projects/${projectId}?user_id=${userId}`),

  getMembers: (projectId) =>
    request(`/projects/${projectId}/members`),

  addMember: (projectId, userId) =>
    request(`/projects/${projectId}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    }),

  // ── Documents ──────────────────────────────────────────────────────────
  listDocuments: (projectId) =>
    request(`/projects/${projectId}/documents`),

  uploadDocument: (projectId, userId, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/projects/${projectId}/documents?user_id=${userId}`, {
      method: 'POST',
      body: form,
    })
  },

  downloadDocument: (docId) => {
    window.location.href = `${BASE}/documents/${docId}/download`
  },

  // Add additional api endpoints here
}

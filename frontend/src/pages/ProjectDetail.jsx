import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function ProjectDetail({ user, onLogout }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const fileInputRef = useRef()

  const [project, setProject] = useState(null)
  const [members, setMembers] = useState([])
  const [documents, setDocuments] = useState([])
  const [allUsers, setAllUsers] = useState([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [memberError, setMemberError] = useState('')

  const projectId = parseInt(id, 10)

  useEffect(() => {
    loadAll()
  }, [id])

  const loadAll = async () => {
    try {
      const [proj, mems, docs, users] = await Promise.all([
        api.getProject(projectId, user.id),
        api.getMembers(projectId),
        api.listDocuments(projectId),
        api.listUsers(),
      ])
      setProject(proj)
      setMembers(mems)
      setDocuments(docs)
      setAllUsers(users)
    } catch {
      navigate('/projects', { replace: true })
    }
  }

  const handleAddMember = async () => {
    if (!selectedUserId) return
    setMemberError('')
    try {
      await api.addMember(projectId, parseInt(selectedUserId, 10))
      setSelectedUserId('')
      const mems = await api.getMembers(projectId)
      setMembers(mems)
    } catch (e) {
      setMemberError(e.message)
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setUploadError('')
    try {
      await api.uploadDocument(projectId, user.id, file)
      const docs = await api.listDocuments(projectId)
      setDocuments(docs)
    } catch (e) {
      setUploadError(e.message)
    } finally {
      setUploading(false)
      fileInputRef.current.value = ''
    }
  }

  if (!project) return <div className="container"><p className="muted">Loading…</p></div>

  const memberIdSet = new Set(members.map((m) => m.id))
  const nonMembers = allUsers.filter((u) => !memberIdSet.has(u.id))
  const isOwner = project.owner_id === user.id

  return (
    <div className="container">
      <header>
        <div className="header-left">
          <button className="back-btn" onClick={() => navigate('/projects')}>← Back</button>
          <h1>{project.name}</h1>
        </div>
        <div className="user-info">
          <span><strong>{user.name}</strong></span>
          <button className="secondary" onClick={onLogout}>Log Out</button>
        </div>
      </header>

      <div className="two-col">
        {/* ── Members ── */}
        <section>
          <h2>Members</h2>
          <ul className="member-list">
            {members.map((m) => (
              <li key={m.id}>
                <span>{m.name}</span>
                {m.id === project.owner_id && <span className="badge">Owner</span>}
              </li>
            ))}
          </ul>

          {isOwner && (
            <>
              <div className="create-row" style={{ marginTop: '1rem' }}>
                <select
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                >
                  <option value="">Add a user…</option>
                  {nonMembers.map((u) => (
                    <option key={u.id} value={u.id}>{u.name}</option>
                  ))}
                </select>
                <button onClick={handleAddMember} disabled={!selectedUserId}>
                  Add
                </button>
              </div>
              {memberError && <p className="error">{memberError}</p>}
            </>
          )}
        </section>

        {/* ── Documents ── */}
        <section>
          <h2>Documents</h2>

          <div className="upload-area">
            <input
              type="file"
              accept=".pdf,application/pdf"
              ref={fileInputRef}
              onChange={handleFileChange}
              disabled={uploading}
              id="pdf-upload"
              style={{ display: 'none' }}
            />
            <label htmlFor="pdf-upload" className={`upload-btn${uploading ? ' disabled' : ''}`}>
              {uploading ? 'Uploading…' : '↑ Upload PDF'}
            </label>
            {uploadError && <p className="error" style={{ marginTop: '0.5rem' }}>{uploadError}</p>}
          </div>

          {documents.length === 0 ? (
            <p className="empty">No documents yet. Upload a PDF above.</p>
          ) : (
            <ul className="doc-list">
              {documents.map((doc) => (
                <li key={doc.id}>
                  <div className="doc-info">
                    <span className="doc-name">{doc.filename}</span>
                    <span className="doc-meta">
                      {doc.uploaded_by_name} · {new Date(doc.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                  <button
                    className="download-btn"
                    onClick={() => api.downloadDocument(doc.id)}
                  >
                    ↓ Download
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
    //Add a button to stitch documents
  )
}

import re
import sqlite3
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from database import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PDF Manager", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ──────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str

class ProjectCreate(BaseModel):
    name: str
    user_id: int

class MemberAdd(BaseModel):
    user_id: int


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Strip path separators and control chars from a filename."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


# ── Users ────────────────────────────────────────────────────────────────────

@app.get("/users/search")
def search_user(name: str):
    db = get_db()
    row = db.execute(
        "SELECT id, name, created_at FROM users WHERE name = ?", (name.strip(),)
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@app.post("/users", status_code=201)
def create_user(body: UserCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    db = get_db()
    try:
        cur = db.execute("INSERT INTO users (name) VALUES (?)", (name,))
        db.commit()
        row = db.execute(
            "SELECT id, name, created_at FROM users WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A user with that name already exists")
    finally:
        db.close()


@app.get("/users")
def list_users():
    db = get_db()
    rows = db.execute("SELECT id, name FROM users ORDER BY name").fetchall()
    db.close()
    return [dict(r) for r in rows]


# ── Projects ─────────────────────────────────────────────────────────────────

@app.get("/projects")
def list_projects(user_id: int):
    db = get_db()
    rows = db.execute(
        """
        SELECT p.id, p.name, p.owner_id, p.created_at
        FROM projects p
        JOIN project_members pm ON pm.project_id = p.id
        WHERE pm.user_id = ?
        ORDER BY p.created_at DESC
        """,
        (user_id,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.post("/projects", status_code=201)
def create_project(body: ProjectCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty")
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO projects (name, owner_id) VALUES (?, ?)", (name, body.user_id)
        )
        project_id = cur.lastrowid
        # owner is automatically a member
        db.execute(
            "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?, ?)",
            (project_id, body.user_id),
        )
        db.commit()
        row = db.execute(
            "SELECT id, name, owner_id, created_at FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row)
    finally:
        db.close()


@app.get("/projects/{project_id}")
def get_project(project_id: int, user_id: int):
    db = get_db()
    access = db.execute(
        """
        SELECT 1 FROM project_members
        WHERE project_id = ? AND user_id = ?
        """,
        (project_id, user_id),
    ).fetchone()
    if not access:
        db.close()
        raise HTTPException(status_code=403, detail="Access denied")
    row = db.execute(
        "SELECT id, name, owner_id, created_at FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@app.get("/projects/{project_id}/members")
def get_members(project_id: int):
    db = get_db()
    rows = db.execute(
        """
        SELECT u.id, u.name
        FROM users u
        JOIN project_members pm ON pm.user_id = u.id
        WHERE pm.project_id = ?
        ORDER BY u.name
        """,
        (project_id,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.post("/projects/{project_id}/members", status_code=201)
def add_member(project_id: int, body: MemberAdd):
    db = get_db()
    try:
        if not db.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        if not db.execute("SELECT 1 FROM users WHERE id = ?", (body.user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        db.execute(
            "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?, ?)",
            (project_id, body.user_id),
        )
        db.commit()
        return {"message": "Member added"}
    finally:
        db.close()


# ── Documents ────────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/documents")
def list_documents(project_id: int):
    db = get_db()
    rows = db.execute(
        """
        SELECT d.id, d.filename, d.uploaded_at, u.name AS uploaded_by_name
        FROM documents d
        JOIN users u ON u.id = d.uploaded_by
        WHERE d.project_id = ?
        ORDER BY d.uploaded_at DESC
        """,
        (project_id,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.post("/projects/{project_id}/documents", status_code=201)
async def upload_document(project_id: int, user_id: int, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    safe_name = _safe_filename(file.filename)
    content = await file.read()
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO documents (project_id, filename, content, uploaded_by) VALUES (?, ?, ?, ?)",
            (project_id, safe_name, content, user_id),
        )
        db.commit()
        return {"id": cur.lastrowid, "filename": safe_name}
    finally:
        db.close()


@app.get("/documents/{doc_id}/download")
def download_document(doc_id: int):
    db = get_db()
    row = db.execute(
        "SELECT filename, content FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    encoded_name = quote(row["filename"])
    return Response(
        content=bytes(row["content"]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{row['filename']}\"; filename*=UTF-8''{encoded_name}"
        },
    )

### Implement the stitch documents endpoint

### Implement the list stitched documents endpoint

## Implement the download stitched document endpoint
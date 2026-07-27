import io
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from pypdf import PdfReader, PdfWriter

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

class StitchCreate(BaseModel):
    user_id: int
    document_ids: List[int]
    name: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Strip path separators and control chars from a filename."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def _merge_pdfs(pdf_blobs: list[bytes]) -> bytes:
    """Merge a list of PDF byte-strings, in order, into one PDF's bytes."""
    writer = PdfWriter()
    try:
        for blob in pdf_blobs:
            reader = PdfReader(io.BytesIO(bytes(blob)))
            for page in reader.pages:
                writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    finally:
        writer.close()


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

@app.post("/projects/{project_id}/stitch", status_code=201)
def stitch_documents(project_id: int, body: StitchCreate):
    if len(body.document_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least two documents to combine")

    db = get_db()
    try:
        project = db.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        member = db.execute(
            "SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, body.user_id),
        ).fetchone()
        if not member:
            raise HTTPException(status_code=403, detail="Access denied")

        # fetch the requested documents, keeping the order the caller asked for
        placeholders = ",".join("?" for _ in body.document_ids)
        rows = db.execute(
            f"""
            SELECT id, filename, content
            FROM documents
            WHERE project_id = ? AND id IN ({placeholders})
            """,
            (project_id, *body.document_ids),
        ).fetchall()

        rows_by_id = {row["id"]: row for row in rows}
        missing = [doc_id for doc_id in body.document_ids if doc_id not in rows_by_id]
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Document(s) not found in this project: {missing}",
            )

        ordered_blobs = [rows_by_id[doc_id]["content"] for doc_id in body.document_ids]
        merged_bytes = _merge_pdfs(ordered_blobs)

        if body.name and body.name.strip():
            filename = _safe_filename(body.name.strip())
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
        else:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            filename = f"stitched-{stamp}.pdf"

        cur = db.execute(
            """
            INSERT INTO stitched_documents
                (project_id, filename, content, source_document_ids, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                project_id,
                filename,
                merged_bytes,
                ",".join(str(i) for i in body.document_ids),
                body.user_id,
            ),
        )
        db.commit()

        row = db.execute(
            """
            SELECT id, project_id, filename, source_document_ids, created_by, created_at
            FROM stitched_documents WHERE id = ?
            """,
            (cur.lastrowid,),
        ).fetchone()
        return dict(row)
    finally:
        db.close()

### Implement the list stitched documents endpoint
@app.get("/projects/{project_id}/stitched")
def list_stitched_documents(project_id: int):
    db = get_db()
    rows = db.execute(
        """
        SELECT sd.id, sd.filename, sd.source_document_ids, sd.created_at,
               u.name AS created_by_name
        FROM stitched_documents sd
        JOIN users u ON u.id = sd.created_by
        WHERE sd.project_id = ?
        ORDER BY sd.created_at DESC
        """,
        (project_id,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

## Implement the download stitched document endpoint
@app.get("/stitched/{stitch_id}/download")
def download_stitched_document(stitch_id: int):
    db = get_db()
    row = db.execute(
        "SELECT filename, content FROM stitched_documents WHERE id = ?", (stitch_id,)
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Stitched document not found")
    encoded_name = quote(row["filename"])
    return Response(
        content=bytes(row["content"]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{row['filename']}\"; filename*=UTF-8''{encoded_name}"
        },
    )